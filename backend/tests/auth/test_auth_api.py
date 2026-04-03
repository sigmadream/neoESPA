from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.schemas import SystemEventLog, User

def test_password_change_invalidates_old_password(client: TestClient, create_user, login_user, auth_headers):
    create_user("pwuser", 20240201, "old-password")

    token = login_user("pwuser", "old-password")
    change_response = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "old-password",
            "new_password": "new-password",
        },
        headers=auth_headers(token),
    )
    
    # login_user returns None if login fails
    old_token = login_user("pwuser", "old-password")
    new_token = login_user("pwuser", "new-password")

    assert change_response.status_code == 200
    assert old_token is None
    assert new_token is not None


def test_inactive_user_cannot_login(client: TestClient, create_user, login_user, auth_headers):
    create_user("managed-user", 20240202, "student-pass")
    create_user("admin-user", 10000012, "admin-pass", role="admin")

    admin_token = login_user("admin-user", "admin-pass")
    deactivate_response = client.patch(
        "/api/admin/users/managed-user/status",
        json={"is_active": False},
        headers=auth_headers(admin_token),
    )
    inactive_token = login_user("managed-user", "student-pass")

    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False
    assert inactive_token is None


def test_register_rejects_duplicate_sid(client: TestClient):
    first_response = client.post(
        "/api/auth/register",
        json={
            "id": "dup-1",
            "sid": 20240203,
            "ps": "password-1",
            "name": "Duplicate One",
            "phone": "010-1111-1111",
            "email": "dup-1@example.com",
        },
    )
    second_response = client.post(
        "/api/auth/register",
        json={
            "id": "dup-2",
            "sid": 20240203,
            "ps": "password-2",
            "name": "Duplicate Two",
            "phone": "010-2222-2222",
            "email": "dup-2@example.com",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "Student ID already exists"


def test_register_creates_user_and_event_log(client: TestClient, session: Session):
    response = client.post(
        "/api/auth/register",
        json={
            "id": "fresh-user",
            "sid": 20240205,
            "ps": "password",
            "name": "Fresh User",
            "phone": "010-4444-4444",
            "email": "fresh-user@example.com",
        },
    )
    created_user = session.get(User, "fresh-user")
    logged_event = session.exec(
        select(SystemEventLog).where(SystemEventLog.user_id == "fresh-user")
    ).first()

    assert response.status_code == 200
    assert created_user is not None
    assert logged_event is not None
    assert logged_event.event_type == "register_success"
    assert logged_event.request_path == "/auth/register"

def test_register_rejects_invalid_email_policy(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={
            "id": "invalid-email",
            "sid": 20240204,
            "ps": "password",
            "name": "Invalid Email",
            "phone": "010-3333-3333",
            "email": "invalid-email-format",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Email does not satisfy the registration policy"
