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


def test_admin_can_create_material_and_students_see_only_published_items():
    with Session(engine) as session:
        _create_user(session, "material-admin", 10057001, "admin")
        _create_user(session, "material-student", 20257001, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "material-admin")
        student_token = _login(client, "material-student")

        published_response = client.post(
            "/api/admin/materials",
            json={
                "title": "Week 6 Slides",
                "description": "Recursion lecture deck",
                "url": "https://example.com/week6.pdf",
                "is_published": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        draft_response = client.post(
            "/api/admin/materials",
            json={
                "title": "Week 7 Draft",
                "description": "Backtracking draft notes",
                "url": "https://example.com/week7.pdf",
                "is_published": False,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        student_list_response = client.get(
            "/api/materials",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        admin_list_response = client.get(
            "/api/materials",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        app.dependency_overrides.clear()

    assert published_response.status_code == 200
    assert draft_response.status_code == 200

    assert student_list_response.status_code == 200
    assert [item["title"] for item in student_list_response.json()] == ["Week 6 Slides"]

    assert admin_list_response.status_code == 200
    assert [item["title"] for item in admin_list_response.json()] == [
        "Week 7 Draft",
        "Week 6 Slides",
    ]
