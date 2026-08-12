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


def _create_user(session: Session, user_id: str, sid: int, password: str, role: str) -> None:
    session.add(
        User(
            id=user_id,
            sid=sid,
            ps=AuthService.get_password_hash(password),
            name=user_id,
            phone="010-0000-0000",
            email=f"{user_id}@example.com",
            user_group=role,
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


def test_admin_can_create_update_delete_notice():
    with Session(engine) as session:
        _create_user(session, "notice-admin", 20243001, "admin-pass", "admin")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = _login(client, "notice-admin", "admin-pass")
        headers = {"Authorization": f"Bearer {token}"}

        create_response = client.post(
            "/api/admin/notices",
            json={
                "title": "Initial Notice",
                "author": "Admin",
                "content": "Initial content",
                "date": "2026-03-12 09:00:00",
                "is_pinned": True,
                "is_published": False,
            },
            headers=headers,
        )
        created_notice = create_response.json()

        update_response = client.patch(
            f"/api/admin/notices/{created_notice['num']}",
            json={
                "title": "Updated Notice",
                "author": "Admin Team",
                "content": "Updated content",
                "date": "2026-03-13 10:30:00",
                "is_pinned": False,
                "is_published": True,
            },
            headers=headers,
        )

        list_response = client.get("/api/admin/notices", headers=headers)
        delete_response = client.delete(
            f"/api/admin/notices/{created_notice['num']}",
            headers=headers,
        )
        missing_response = client.get(
            f"/api/notice/{created_notice['num']}",
            headers=headers,
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert created_notice["title"] == "Initial Notice"
    assert created_notice["is_published"] is False
    assert created_notice["is_pinned"] is True

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Notice"
    assert update_response.json()["author"] == "Admin Team"
    assert update_response.json()["is_published"] is True
    assert update_response.json()["is_pinned"] is False

    assert list_response.status_code == 200
    assert [notice["title"] for notice in list_response.json()] == ["Updated Notice"]

    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Notice deleted successfully"
    assert missing_response.status_code == 404
