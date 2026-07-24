from datetime import UTC, datetime, timedelta

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


def _dt_string(offset_days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=offset_days)).strftime("%Y-%m-%d %H:%M:%S")


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


def test_student_can_submit_exam_within_schedule():
    with Session(engine) as session:
        _create_user(session, "exam-admin", 10053001, "admin")
        _create_user(session, "exam-student", 20253001, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "exam-admin")
        student_token = _login(client, "exam-student")
        create_response = client.post(
            "/api/admin/exams",
            json={
                "title": "Midterm Practice",
                "intro": "Exam intro",
                "codeName": "main",
                "starttime": _dt_string(-1),
                "deadline": _dt_string(1),
                "allowed_languages": ["python"],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        submit_response = client.post(
            f"/api/exams/{create_response.json()['id']}/submit",
            json={
                "language": "python",
                "code_text": "print('answer')\n",
                "original_filename": "main.py",
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert submit_response.status_code == 201
    assert submit_response.json()["status"] == "submitted"


def test_exam_submission_is_locked_after_deadline():
    with Session(engine) as session:
        _create_user(session, "exam-admin", 10053002, "admin")
        _create_user(session, "exam-student", 20253002, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "exam-admin")
        student_token = _login(client, "exam-student")
        create_response = client.post(
            "/api/admin/exams",
            json={
                "title": "Closed Exam",
                "intro": "Exam intro",
                "codeName": "main",
                "starttime": _dt_string(-3),
                "deadline": _dt_string(-1),
                "allowed_languages": ["python"],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        submit_response = client.post(
            f"/api/exams/{create_response.json()['id']}/submit",
            json={
                "language": "python",
                "code_text": "print('late')\n",
                "original_filename": "main.py",
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert submit_response.status_code == 400
    assert submit_response.json()["detail"] == "Exam submission deadline has passed"


def test_get_exam_and_submissions():
    with Session(engine) as session:
        _create_user(session, "exam-admin", 10053003, "admin")
        _create_user(session, "exam-student", 20253003, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "exam-admin")
        student_token = _login(client, "exam-student")
        create_response = client.post(
            "/api/admin/exams",
            json={
                "title": "Detail Exam",
                "intro": "Detail intro",
                "codeName": "main",
                "starttime": _dt_string(-1),
                "deadline": _dt_string(1),
                "allowed_languages": ["python"],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        exam_id = create_response.json()["id"]

        get_resp = client.get(f"/api/exams/{exam_id}", headers={"Authorization": f"Bearer {student_token}"})
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Detail Exam"

        client.post(
            f"/api/exams/{exam_id}/submit",
            json={
                "language": "python",
                "code_text": "print('test')\n",
                "original_filename": "main.py",
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )

        subs_resp = client.get(f"/api/exams/{exam_id}/submissions", headers={"Authorization": f"Bearer {student_token}"})
        assert subs_resp.status_code == 200
        assert len(subs_resp.json()) == 1

        app.dependency_overrides.clear()
