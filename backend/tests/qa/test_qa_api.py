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


def test_qa_post_creation_and_visibility():
    with Session(engine) as session:
        _create_user(session, "qa-student1", 20258001, "student")
        _create_user(session, "qa-student2", 20258002, "student")
        _create_user(session, "qa-admin", 10058001, "admin")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        s1_token = _login(client, "qa-student1")
        s2_token = _login(client, "qa-student2")
        admin_token = _login(client, "qa-admin")

        # Create public & private posts
        pub_resp = client.post(
            "/api/qa",
            json={"title": "Public Question", "content": "How to use pointers?", "is_private": False},
            headers={"Authorization": f"Bearer {s1_token}"},
        )
        assert pub_resp.status_code == 201

        priv_resp = client.post(
            "/api/qa",
            json={"title": "Private Question", "content": "Grade check inquiry", "is_private": True},
            headers={"Authorization": f"Bearer {s1_token}"},
        )
        assert priv_resp.status_code == 201
        priv_id = priv_resp.json()["id"]

        # List posts for s2 (other student) -> should only see public
        s2_list = client.get("/api/qa", headers={"Authorization": f"Bearer {s2_token}"})
        assert s2_list.status_code == 200
        assert len(s2_list.json()) == 1
        assert s2_list.json()[0]["title"] == "Public Question"

        # List posts for admin -> sees both
        admin_list = client.get("/api/qa", headers={"Authorization": f"Bearer {admin_token}"})
        assert admin_list.status_code == 200
        assert len(admin_list.json()) == 2

        # Add answer by admin to private post
        ans_resp = client.post(
            f"/api/qa/{priv_id}/answers",
            json={"content": "Grade adjusted."},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert ans_resp.status_code == 200
        assert len(ans_resp.json()["answers"]) == 1

        app.dependency_overrides.clear()
