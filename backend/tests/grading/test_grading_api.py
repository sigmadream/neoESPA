import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models.schemas import GradingRule, Homework, SubmissionResult, User
from app.services.auth_service import AuthService

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def _dt_string(offset_days: int, offset_hours: int = 0) -> str:
    return (
        datetime.now(UTC) + timedelta(days=offset_days, hours=offset_hours)
    ).strftime("%Y-%m-%d %H:%M:%S")


def _create_user(
    session: Session,
    user_id: str,
    sid: int,
    password: str,
    role: str,
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
        )
    )
    session.commit()


def _create_homework(
    session: Session, num: int, title: str, sec: int = 2
) -> None:
    session.add(
        Homework(
            num=num,
            title=title,
            intro=f"{title} intro",
            starttime=_dt_string(-1),
            deadline=_dt_string(2),
            codeName="main",
            sec=sec,
        )
    )
    session.commit()


def _create_testcase_rule(
    session: Session,
    homework_num: int,
    *,
    expected_output: str,
) -> None:
    session.add(
        GradingRule(
            scope="homework",
            homework_num=homework_num,
            rule_name="testcases",
            rule_value=json.dumps(
                {
                    "cases": [
                        {
                            "name": "main",
                            "input": "",
                            "expected_output": expected_output,
                            "score": 100,
                            "is_hidden": False,
                        }
                    ]
                }
            ),
            is_active=True,
        )
    )
    session.commit()


def _login(client: TestClient, user_id: str, password: str) -> str:
    response = client.post(
        "/api/auth/login", json={"id": user_id, "ps": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_compile_error_is_persisted_in_submission_result():
    with Session(engine) as session:
        _create_homework(session, 1, "Compile Error Homework")
        _create_testcase_rule(session, 1, expected_output="hello grading\n")
        _create_user(
            session, "student-compile", 20243001, "student-pass", "student"
        )
        _create_user(session, "admin-compile", 10003001, "admin-pass", "admin")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        student_token = _login(client, "student-compile", "student-pass")
        admin_token = _login(client, "admin-compile", "admin-pass")

        create_response = client.post(
            "/api/submissions",
            json={
                "homework_num": 1,
                "language": "python",
                "code_text": "def broken(:\n    pass\n",
                "original_filename": "broken.py",
            },
            headers=_auth_headers(student_token),
        )
        submission_id = create_response.json()["id"]
        grade_response = client.post(
            f"/api/admin/submissions/{submission_id}/grade",
            headers=_auth_headers(admin_token),
        )
        stored_result = session.exec(
            select(SubmissionResult).where(
                SubmissionResult.submission_id == submission_id
            )
        ).first()

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert grade_response.status_code == 200
    assert grade_response.json()["status"] == "failed"
    assert stored_result is not None
    assert stored_result.compile_status == "failed"
    assert stored_result.run_status == "not_started"
    assert stored_result.total_score == 0.0
    assert stored_result.compile_log is not None
    assert "SyntaxError" in stored_result.compile_log


def test_runtime_output_and_score_are_saved():
    with Session(engine) as session:
        _create_homework(session, 2, "Runtime Homework")
        _create_testcase_rule(session, 2, expected_output="hello grading\n")
        _create_user(
            session, "student-runtime", 20243002, "student-pass", "student"
        )
        _create_user(session, "admin-runtime", 10003002, "admin-pass", "admin")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        student_token = _login(client, "student-runtime", "student-pass")
        admin_token = _login(client, "admin-runtime", "admin-pass")

        create_response = client.post(
            "/api/submissions",
            json={
                "homework_num": 2,
                "language": "python",
                "code_text": "print('hello grading')\n",
                "original_filename": "answer.py",
            },
            headers=_auth_headers(student_token),
        )
        submission_id = create_response.json()["id"]
        grade_response = client.post(
            f"/api/admin/submissions/{submission_id}/grade",
            headers=_auth_headers(admin_token),
        )
        stored_result = session.exec(
            select(SubmissionResult).where(
                SubmissionResult.submission_id == submission_id
            )
        ).first()

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert grade_response.status_code == 200
    assert grade_response.json()["status"] == "graded"
    assert grade_response.json()["total_score"] == 100.0
    assert stored_result is not None
    assert stored_result.compile_status == "passed"
    assert stored_result.run_status == "passed"
    assert stored_result.total_score == 100.0
    assert stored_result.submission_score == 100.0
    assert stored_result.runtime_log is not None
    assert "hello grading" in stored_result.runtime_log
    assert stored_result.exit_code == 0
