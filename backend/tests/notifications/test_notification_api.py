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


def _create_user(session: Session, user_id: str, sid: int, role: str) -> None:
    session.add(
        User(
            id=user_id,
            sid=sid,
            ps=AuthService.get_password_hash("password"),
            name=user_id,
            phone="010-0000-0000",
            email=f"{user_id}@example.com",
            user_group=role,
        )
    )
    session.commit()


def _login(client: TestClient, user_id: str) -> str:
    response = client.post("/api/auth/login", json={"id": user_id, "ps": "password"})
    assert response.status_code == 200
    return response.json()["access_token"]


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_notice_publication_creates_notification():
    with Session(engine) as session:
        _create_user(session, "notice-admin", 10054001, "admin")
        _create_user(session, "notice-student", 20254001, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "notice-admin")
        student_token = _login(client, "notice-student")

        create_response = client.post(
            "/api/admin/notices",
            json={
                "title": "Class Update",
                "author": "Admin",
                "content": "Please review the new deadline.",
                "date": None,
                "is_pinned": False,
                "is_published": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        list_response = client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    notification = list_response.json()[0]
    assert notification["kind"] == "notice"
    assert notification["reference_type"] == "notice"
    assert notification["title"] == "새 공지: Class Update"


def test_notice_update_does_not_duplicate_publication_notifications():
    with Session(engine) as session:
        _create_user(session, "notice-admin-2", 10054002, "admin")
        _create_user(session, "notice-student-2", 20254002, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "notice-admin-2")
        student_token = _login(client, "notice-student-2")

        create_response = client.post(
            "/api/admin/notices",
            json={
                "title": "Original Notice",
                "author": "Admin",
                "content": "Initial content",
                "date": None,
                "is_pinned": False,
                "is_published": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        notice_num = create_response.json()["num"]
        update_response = client.patch(
            f"/api/admin/notices/{notice_num}",
            json={
                "title": "Original Notice (Edited)",
                "author": "Admin",
                "content": "Edited content",
                "date": None,
                "is_pinned": True,
                "is_published": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        list_response = client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
