from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import _to_user_read, app
from sqlmodel import select

from app.models.schemas import AuditLog, User
from app.services.auth_service import AuthService


engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def _create_user(
    session: Session,
    user_id: str,
    sid: int,
    password: str,
    role: str = "student",
    is_active: bool = True,
) -> None:
    session.add(
        User(
            id=user_id,
            sid=sid,
            ps=AuthService.get_password_hash(password),
            name=user_id,
            phone="010-0000-0000",
            email=f"{user_id}@example.com",
            user_group=role,
            is_active=is_active,
        )
    )
    session.commit()


def _login(client: TestClient, user_id: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"id": user_id, "ps": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_admin_can_change_user_role():
    with Session(engine) as session:
        _create_user(session, "role-admin", 20246001, "admin-pass", role="admin")
        _create_user(session, "managed-user", 20246002, "student-pass")
        _create_user(session, "other-user", 20246003, "student-pass", role="ta")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        token = _login(client, "role-admin", "admin-pass")
        headers = {"Authorization": f"Bearer {token}"}

        update_response = client.patch(
            "/api/admin/users/managed-user/role",
            json={"user_group": "instructor"},
            headers=headers,
        )
        search_response = client.get(
            "/api/admin/users?search=managed&role=instructor",
            headers=headers,
        )

        app.dependency_overrides.clear()

    assert update_response.status_code == 200
    assert update_response.json()["user_group"] == "instructor"
    assert search_response.status_code == 200
    assert [user["id"] for user in search_response.json()] == ["managed-user"]


def test_student_can_update_own_profile():
    with Session(engine) as session:
        _create_user(session, "profile-student", 20246021, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        token = _login(client, "profile-student", "student-pass")
        headers = {"Authorization": f"Bearer {token}"}

        update_response = client.patch(
            "/api/users/me",
            json={
                "name": "Updated Student",
                "phone": "010-9876-5432",
                "email": "updated-student@example.com",
            },
            headers=headers,
        )
        me_response = client.get("/api/users/me", headers=headers)
        audit_log = session.exec(
            select(AuditLog).where(AuditLog.action_type == "update_my_profile")
        ).first()

        app.dependency_overrides.clear()

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Student"
    assert update_response.json()["phone"] == "010-9876-5432"
    assert update_response.json()["email"] == "updated-student@example.com"
    assert me_response.status_code == 200
    assert me_response.json()["name"] == "Updated Student"
    assert audit_log is not None
    assert audit_log.actor_user_id == "profile-student"


def test_profile_update_rejects_invalid_email():
    with Session(engine) as session:
        _create_user(session, "invalid-profile", 20246023, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        token = _login(client, "invalid-profile", "student-pass")
        headers = {"Authorization": f"Bearer {token}"}

        update_response = client.patch(
            "/api/users/me",
            json={
                "name": "Invalid Profile",
                "phone": "010-1010-1010",
                "email": "invalid-email",
            },
            headers=headers,
        )
        current_user = session.get(User, "invalid-profile")

        app.dependency_overrides.clear()

    assert update_response.status_code == 400
    assert (
        update_response.json()["detail"]
        == "Email does not satisfy the registration policy"
    )
    assert current_user is not None
    assert current_user.email == "invalid-profile@example.com"


def test_admin_can_update_own_profile():
    with Session(engine) as session:
        _create_user(session, "profile-admin", 20246022, "admin-pass", role="admin")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        token = _login(client, "profile-admin", "admin-pass")
        headers = {"Authorization": f"Bearer {token}"}

        update_response = client.patch(
            "/api/users/me",
            json={
                "name": "Updated Admin",
                "phone": "010-2222-9999",
                "email": "updated-admin@example.com",
            },
            headers=headers,
        )

        app.dependency_overrides.clear()

    assert update_response.status_code == 200
    assert update_response.json()["user_group"] == "admin"
    assert update_response.json()["name"] == "Updated Admin"
    assert update_response.json()["email"] == "updated-admin@example.com"


def test_admin_can_deactivate_user():
    with Session(engine) as session:
        _create_user(session, "status-admin", 20246004, "admin-pass", role="admin")
        _create_user(session, "status-user", 20246005, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        token = _login(client, "status-admin", "admin-pass")
        headers = {"Authorization": f"Bearer {token}"}

        deactivate_response = client.patch(
            "/api/admin/users/status-user/status",
            json={"is_active": False},
            headers=headers,
        )
        filtered_response = client.get(
            "/api/admin/users?search=status-user&is_active=false",
            headers=headers,
        )
        relogin_response = client.post(
            "/api/auth/login",
            json={"id": "status-user", "ps": "student-pass"},
        )

        app.dependency_overrides.clear()

    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False
    assert filtered_response.status_code == 200
    assert [user["id"] for user in filtered_response.json()] == ["status-user"]
    assert relogin_response.status_code == 403


def test_admin_can_bulk_register_users():
    with Session(engine) as session:
        _create_user(session, "bulk-admin", 20246010, "admin-pass", role="admin")
        _create_user(session, "existing-user", 20246011, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        token = _login(client, "bulk-admin", "admin-pass")
        headers = {"Authorization": f"Bearer {token}"}

        bulk_response = client.post(
            "/api/admin/users/bulk",
            json={
                "default_password": "welcome-pass",
                "skip_existing": True,
                "users": [
                    {
                        "id": "existing-user",
                        "sid": 20246011,
                        "name": "Existing User",
                        "phone": "010-1111-1111",
                        "email": "existing-user@example.com",
                        "user_group": "student",
                    },
                    {
                        "id": "new-student",
                        "sid": 20246012,
                        "name": "New Student",
                        "phone": "010-2222-2222",
                        "email": "new-student@example.com",
                        "user_group": "student",
                    },
                    {
                        "id": "new-ta",
                        "sid": 20246013,
                        "name": "New TA",
                        "phone": "010-3333-3333",
                        "email": "new-ta@example.com",
                        "user_group": "ta",
                        "ps": "ta-custom-pass",
                    },
                ],
            },
            headers=headers,
        )
        created_login = client.post(
            "/api/auth/login",
            json={"id": "new-student", "ps": "welcome-pass"},
        )
        custom_login = client.post(
            "/api/auth/login",
            json={"id": "new-ta", "ps": "ta-custom-pass"},
        )
        list_response = client.get("/api/admin/users?search=new-", headers=headers)

        app.dependency_overrides.clear()

    assert bulk_response.status_code == 200
    payload = bulk_response.json()
    assert payload["created_count"] == 2
    assert payload["skipped_count"] == 1
    assert payload["skipped_ids"] == ["existing-user"]
    assert [user["id"] for user in payload["created_users"]] == [
        "new-student",
        "new-ta",
    ]
    assert created_login.status_code == 200
    assert custom_login.status_code == 200
    assert list_response.status_code == 200
    assert [user["id"] for user in list_response.json()] == ["new-student", "new-ta"]


def test_user_read_serialization_backfills_missing_timestamps():
    user = User(
        id="legacy-user",
        sid=20246020,
        ps=AuthService.get_password_hash("legacy-pass"),
        name="Legacy User",
        phone="010-4444-4444",
        email="legacy-user@example.com",
        user_group="student",
        is_active=True,
    )
    user.created_at = None
    user.updated_at = None

    payload = _to_user_read(user)

    assert payload.id == "legacy-user"
    assert payload.created_at is not None
    assert payload.updated_at is not None
