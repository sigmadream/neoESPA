from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.domains.homework import router as homework_router
from app.main import app
from app.models.schemas import User
from app.services.auth_service import AuthService

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def _dt_string(offset_days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=offset_days)).strftime(
        "%Y-%m-%d %H:%M:%S"
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
    response = client.post(
        "/api/auth/login", json={"id": user_id, "ps": "password"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _read_homework_import_fixture(name: str) -> bytes:
    with open(
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "homework_import"
        / name,
        "rb",
    ) as fixture:
        return fixture.read()


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_student_submission_happy_path():
    with Session(engine) as session:
        _create_user(session, "e2e-admin", 10055001, "admin")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "e2e-admin")
        register_response = client.post(
            "/api/auth/register",
            json={
                "id": "happy-student",
                "sid": 20255001,
                "ps": "student-pass",
                "name": "Happy Student",
                "phone": "010-1234-5678",
                "email": "happy-student@example.com",
            },
        )
        student_token = client.post(
            "/api/auth/login",
            json={"id": "happy-student", "ps": "student-pass"},
        ).json()["access_token"]
        create_homework = client.post(
            "/api/admin/homeworks",
            json={
                "title": "Happy Path Homework",
                "intro": "Solve A+B",
                "deadline": _dt_string(2),
                "starttime": _dt_string(-1),
                "codeName": "main",
                "allowed_languages": ["python"],
                "testcases": [
                    {
                        "name": "sample",
                        "input": "1 2\n",
                        "expected_output": "3\n",
                        "score": 100,
                        "is_hidden": False,
                    }
                ],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        homework_num = create_homework.json()["num"]
        homework_list = client.get(
            "/api/homework",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        submit_response = client.post(
            "/api/submissions",
            json={
                "homework_num": homework_num,
                "language": "python",
                "code_text": "a, b = map(int, input().split())\nprint(a + b)\n",
                "original_filename": "main.py",
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )
        submission_id = submit_response.json()["id"]
        grade_response = client.post(
            f"/api/admin/submissions/{submission_id}/grade",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        submission_detail = client.get(
            f"/api/submissions/{submission_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        dashboard_response = client.get(
            "/api/dashboard/me",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        app.dependency_overrides.clear()

    assert register_response.status_code == 200
    assert create_homework.status_code == 200
    assert homework_list.status_code == 200
    assert len(homework_list.json()) == 1
    assert submit_response.status_code == 201
    assert grade_response.status_code == 200
    assert grade_response.json()["status"] == "graded"
    assert grade_response.json()["total_score"] == 100.0
    assert submission_detail.status_code == 200
    assert submission_detail.json()["grader_summary"].startswith("Passed 1/1")
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["overview"]["submitted_homeworks"] == 1


def test_imported_homework_submission_happy_path(tmp_path, monkeypatch):
    with Session(engine) as session:
        _create_user(session, "import-e2e-admin", 10055002, "admin")

        artifact_root = tmp_path / "supportFiles" / "homeworks"
        monkeypatch.setattr(
            homework_router,
            "_get_homework_artifact_root",
            lambda: artifact_root,
        )

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "import-e2e-admin")
        register_response = client.post(
            "/api/auth/register",
            json={
                "id": "import-happy-student",
                "sid": 20255002,
                "ps": "student-pass",
                "name": "Import Happy Student",
                "phone": "010-9876-5432",
                "email": "import-happy-student@example.com",
            },
        )
        student_token = client.post(
            "/api/auth/login",
            json={"id": "import-happy-student", "ps": "student-pass"},
        ).json()["access_token"]
        import_homework = client.post(
            "/api/admin/homeworks/import",
            data={
                "title": "Imported Happy Path Homework",
                "intro": "Imported homework should still support submission and grading.",
                "deadline": _dt_string(2),
                "starttime": _dt_string(-1),
                "codeName": "imported-happy",
                "allowed_languages": '["python"]',
                "isLint": "false",
                "lint_week": "",
            },
            files={
                "problem_file": (
                    "problem.pdf",
                    _read_homework_import_fixture("problem.pdf"),
                    "application/pdf",
                ),
                "input_zip": (
                    "inputs.zip",
                    _read_homework_import_fixture("inputs.zip"),
                    "application/zip",
                ),
                "output_zip": (
                    "outputs.zip",
                    _read_homework_import_fixture("outputs.zip"),
                    "application/zip",
                ),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        homework_num = import_homework.json()["num"]
        homework_list = client.get(
            "/api/homework",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        submit_response = client.post(
            "/api/submissions",
            json={
                "homework_num": homework_num,
                "language": "python",
                "code_text": "a = int(input())\nprint(a)\n",
                "original_filename": "main.py",
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )
        submission_id = submit_response.json()["id"]
        grade_response = client.post(
            f"/api/admin/submissions/{submission_id}/grade",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        submission_detail = client.get(
            f"/api/submissions/{submission_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        admin_detail = client.get(
            f"/api/admin/homeworks/{homework_num}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        delete_response = client.delete(
            f"/api/admin/homeworks/{homework_num}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        app.dependency_overrides.clear()

    assert register_response.status_code == 200
    assert import_homework.status_code == 200
    assert import_homework.json()["parsed_testcase_count"] == 2
    assert import_homework.json()["problem_file_name"] == "problem.pdf"
    assert homework_list.status_code == 200
    assert len(homework_list.json()) == 1
    assert homework_list.json()[0]["num"] == homework_num
    assert submit_response.status_code == 201
    assert grade_response.status_code == 200
    assert grade_response.json()["status"] == "graded"
    assert submission_detail.status_code == 200
    assert submission_detail.json()["status"] == "graded"
    assert submission_detail.json()["grader_summary"].startswith("Passed ")
    assert admin_detail.status_code == 200
    assert admin_detail.json()["testcases"]
    assert admin_detail.json()["parsed_testcase_count"] == 2
    assert admin_detail.json()["problem_file_name"] == "problem.pdf"
    assert admin_detail.json()["input_zip_name"] == "inputs.zip"
    assert admin_detail.json()["output_zip_name"] == "outputs.zip"
    assert delete_response.status_code == 400
    assert (
        delete_response.json()["detail"]
        == "Cannot delete homework with submissions"
    )
