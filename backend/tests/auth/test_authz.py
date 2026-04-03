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
    response = client.post("/api/auth/login", json={"id": user_id, "ps": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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
        response = client.post(
            "/api/admin/homeworks",
            json={
                "title": "Restricted Homework",
                "intro": "Students must not create this.",
                "deadline": "2026-12-31 23:59:59",
                "codeName": "restricted",
            },
            headers=_auth_headers(token),
        )

        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_admin_can_manage_homeworks():
    with Session(engine) as session:
        _create_user(session, "admin1", 10000011, "admin-pass", "admin")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = _login(client, "admin1", "admin-pass")
        response = client.post(
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

        app.dependency_overrides.clear()

        created_homework = response.json()

    assert response.status_code == 200
    assert created_homework["title"] == "Admin Managed Homework"
    assert created_homework["sbnum"] == 5
    assert created_homework["isLint"] is True
