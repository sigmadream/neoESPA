from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models.schemas import User
from app.services.auth_service import AuthService

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def _create_user(
    session: Session,
    user_id: str,
    sid: int,
    password: str,
    role: str,
    is_active: bool = True,
) -> User:
    user = User(
        id=user_id,
        sid=sid,
        ps=AuthService.get_password_hash(password),
        name=user_id,
        phone="010-0000-0000",
        email=f"{user_id}@example.com",
        user_group=role,
        is_active=is_active,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _login(client: TestClient, user_id: str, password: str) -> str:
    response = client.post(
        "/api/auth/login", json={"id": user_id, "ps": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_admin_homework_response(client: TestClient, token: str):
    return client.post(
        "/api/admin/homeworks",
        json={
            "title": "Admin Managed Homework",
            "intro": "Created through the admin API.",
            "deadline": "2026-12-31 23:59:59",
            "codeName": "managed",
            "sbnum": 5,
            "sec": 2,
            "isLint": True,
        },
        headers=_auth_headers(token),
    )


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_student_cannot_access_admin_routes():
    with Session(engine) as session:
        _create_user(session, "student1", 20240101, "student-pass", "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = _login(client, "student1", "student-pass")
        response = _create_admin_homework_response(client, token)

        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing capability: homework:manage"


def test_staff_roles_can_manage_homeworks():
    with Session(engine) as session:
        for idx, role in enumerate(["admin", "instructor", "ta"], start=1):
            _create_user(
                session, f"staff-{role}", 10000010 + idx, "staff-pass", role
            )

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        responses = []
        for role in ["admin", "instructor", "ta"]:
            token = _login(client, f"staff-{role}", "staff-pass")
            responses.append(
                (role, _create_admin_homework_response(client, token))
            )

        app.dependency_overrides.clear()

    for role, response in responses:
        assert response.status_code == 200, role
        payload = response.json()
        assert payload["title"] == "Admin Managed Homework"
        assert payload["sbnum"] == 5
        assert payload["isLint"] is True


def test_inactive_staff_user_cannot_access_admin_routes_with_valid_token():
    with Session(engine) as session:
        _create_user(
            session,
            "inactive-admin",
            10000021,
            "admin-pass",
            "admin",
            is_active=False,
        )

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = AuthService.create_access_token({"sub": "inactive-admin"})
        response = _create_admin_homework_response(client, token)

        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert (
        response.json()["detail"] == "Inactive user cannot access this resource"
    )
