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


def test_material_update_delete_and_comments():
    with Session(engine) as session:
        _create_user(session, "mat-admin", 10057002, "admin")
        _create_user(session, "mat-student", 20257002, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "mat-admin")
        student_token = _login(client, "mat-student")

        create_resp = client.post(
            "/api/admin/materials",
            json={
                "title": "C Programming Guide",
                "description": "Pointers and memory",
                "url": "https://example.com/c.pdf",
                "content": "Detailed article content here",
                "is_published": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        mat_id = create_resp.json()["id"]

        get_resp = client.get(f"/api/materials/{mat_id}", headers={"Authorization": f"Bearer {student_token}"})
        assert get_resp.status_code == 200
        assert get_resp.json()["content"] == "Detailed article content here"

        comment_resp = client.post(
            f"/api/materials/{mat_id}/comments",
            json={"content": "Great guide!"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert comment_resp.status_code == 200
        assert len(comment_resp.json()["comments"]) == 1
        assert comment_resp.json()["comments"][0]["content"] == "Great guide!"

        update_resp = client.patch(
            f"/api/admin/materials/{mat_id}",
            json={
                "title": "C Programming Guide (Updated)",
                "description": "Updated description",
                "url": "https://example.com/c_v2.pdf",
                "content": "Updated content",
                "is_published": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "C Programming Guide (Updated)"

        del_resp = client.delete(f"/api/admin/materials/{mat_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert del_resp.status_code == 200

        app.dependency_overrides.clear()


def test_material_attachment_upload_and_download(tmp_path, monkeypatch):
    from app.domains.materials import router as materials_router

    monkeypatch.setattr(
        materials_router,
        "_get_material_attachment_root",
        lambda: tmp_path,
    )

    with Session(engine) as session:
        _create_user(session, "att-admin", 10057003, "admin")
        _create_user(session, "att-student", 20257003, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "att-admin")
        student_token = _login(client, "att-student")

        create_resp = client.post(
            "/api/admin/materials",
            json={
                "title": "Slides with attachment",
                "description": "Week 1 slides",
                "url": "",
                "is_published": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert create_resp.status_code == 200
        mat_id = create_resp.json()["id"]

        upload_resp = client.post(
            f"/api/admin/materials/{mat_id}/attachment",
            files={"upload": ("week1.pdf", b"%PDF-1.4 fake-content", "application/pdf")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert upload_resp.status_code == 200
        assert upload_resp.json()["attachment_name"] == "week1.pdf"
        assert upload_resp.json()["attachment_relpath"] == f"{mat_id}/week1.pdf"

        student_upload_resp = client.post(
            f"/api/admin/materials/{mat_id}/attachment",
            files={"upload": ("week1.pdf", b"nope", "application/pdf")},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert student_upload_resp.status_code == 403

        download_resp = client.get(
            f"/api/materials/{mat_id}/attachment",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert download_resp.status_code == 200
        assert download_resp.content == b"%PDF-1.4 fake-content"

        missing_resp = client.get(
            "/api/materials/999999/attachment",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert missing_resp.status_code == 404

        app.dependency_overrides.clear()
