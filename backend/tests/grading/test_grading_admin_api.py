import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models.schemas import (
    GradingRule,
    Homework,
    Submission,
    SubmissionCaseResult,
    SubmissionResult,
    User,
)
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


def _create_homework(session: Session, num: int, title: str) -> None:
    session.add(
        Homework(
            num=num,
            title=title,
            intro=f"{title} intro",
            starttime=_dt_string(-1),
            deadline=_dt_string(2),
            codeName="main",
            sec=2,
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
    response = client.post("/api/auth/login", json={"id": user_id, "ps": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_admin_can_requeue_failed_submission():
    with Session(engine) as session:
        _create_homework(session, 1, "Requeue Homework")
        _create_testcase_rule(session, 1, expected_output="ok\n")
        _create_user(session, "student-requeue", 20248001, "student-pass", "student")
        _create_user(session, "admin-requeue", 10008001, "admin-pass", "admin")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        student_token = _login(client, "student-requeue", "student-pass")
        admin_token = _login(client, "admin-requeue", "admin-pass")

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
        requeue_response = client.post(
            f"/api/admin/submissions/{submission_id}/requeue",
            headers=_auth_headers(admin_token),
        )
        stored_result = session.exec(
            select(SubmissionResult).where(SubmissionResult.submission_id == submission_id)
        ).first()

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert grade_response.status_code == 200
    assert grade_response.json()["status"] == "failed"
    assert requeue_response.status_code == 200
    assert requeue_response.json()["status"] == "pending"
    assert requeue_response.json()["compile_status"] == "not_started"
    assert requeue_response.json()["run_status"] == "not_started"
    assert requeue_response.json()["total_score"] == 0.0
    assert stored_result is not None
    assert stored_result.status == "pending"
    assert stored_result.compile_status == "not_started"
    assert stored_result.grader_summary == "Submission queued for grading."


def test_admin_can_adjust_submission_score():
    with Session(engine) as session:
        _create_homework(session, 2, "Adjust Homework")
        _create_testcase_rule(session, 2, expected_output="ok\n")
        _create_user(session, "student-adjust", 20248002, "student-pass", "student")
        _create_user(session, "admin-adjust", 10008002, "admin-pass", "admin")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        student_token = _login(client, "student-adjust", "student-pass")
        admin_token = _login(client, "admin-adjust", "admin-pass")

        create_response = client.post(
            "/api/submissions",
            json={
                "homework_num": 2,
                "language": "python",
                "code_text": "print('ok')\n",
                "original_filename": "answer.py",
            },
            headers=_auth_headers(student_token),
        )
        submission_id = create_response.json()["id"]
        grade_response = client.post(
            f"/api/admin/submissions/{submission_id}/grade",
            headers=_auth_headers(admin_token),
        )
        adjust_response = client.patch(
            f"/api/admin/submissions/{submission_id}/score",
            json={
                "manual_total_score": 87.5,
                "adjustment_note": "Late penalty applied",
            },
            headers=_auth_headers(admin_token),
        )
        student_detail = client.get(
            f"/api/submissions/{submission_id}",
            headers=_auth_headers(student_token),
        )
        stored_result = session.exec(
            select(SubmissionResult).where(SubmissionResult.submission_id == submission_id)
        ).first()

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert grade_response.status_code == 200
    assert adjust_response.status_code == 200
    assert adjust_response.json()["total_score"] == 87.5
    assert adjust_response.json()["manual_total_score"] == 87.5
    assert adjust_response.json()["score_adjustment_note"] == "Late penalty applied"
    assert adjust_response.json()["score_adjusted_by"] == "admin-adjust"
    assert student_detail.status_code == 200
    assert student_detail.json()["total_score"] == 87.5
    assert stored_result is not None
    assert stored_result.manual_total_score == 87.5
    assert stored_result.adjustment_note == "Late penalty applied"
    assert stored_result.adjusted_by == "admin-adjust"


def test_admin_cannot_grade_homework_without_testcases():
    with Session(engine) as session:
        _create_homework(session, 4, "Missing Testcase Homework")
        _create_user(session, "student-missing", 20248004, "student-pass", "student")
        _create_user(session, "admin-missing", 10008004, "admin-pass", "admin")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        student_token = _login(client, "student-missing", "student-pass")
        admin_token = _login(client, "admin-missing", "admin-pass")

        create_response = client.post(
            "/api/submissions",
            json={
                "homework_num": 4,
                "language": "python",
                "code_text": "print('ok')\n",
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
            select(SubmissionResult).where(SubmissionResult.submission_id == submission_id)
        ).first()

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert grade_response.status_code == 400
    assert grade_response.json()["detail"] == "Homework has no active test cases configured"
    assert stored_result is not None
    assert stored_result.status == "retryable"
    assert stored_result.grader_summary == (
        "Auto-grading failed: Homework has no active test cases configured"
    )


def test_failed_regrade_preserves_existing_result_data():
    with Session(engine) as session:
        _create_homework(session, 3, "Rollback Homework")
        _create_user(session, "student-rollback", 20248003, "student-pass", "student")
        _create_user(session, "admin-rollback", 10008003, "admin-pass", "admin")

        submission = Submission(
            homework_num=3,
            user_id="student-rollback",
            submission_mode="official",
            attempt_no=1,
            language="python",
            status="graded",
            code_text="print('ok')\n",
            original_filename="answer.py",
        )
        session.add(submission)
        session.flush()
        submission_id = submission.id or 0
        session.add(
            SubmissionResult(
                submission_id=submission_id,
                status="graded",
                compile_status="passed",
                run_status="passed",
                total_score=91.0,
                submission_score=91.0,
                manual_total_score=91.0,
                adjustment_note="Manual override",
                adjusted_by="admin-rollback",
            )
        )
        session.add(
            SubmissionCaseResult(
                submission_id=submission_id,
                case_index=1,
                case_name="sample",
                passed=True,
                score_awarded=91.0,
                message="Passed.",
            )
        )
        session.add(
            GradingRule(
                scope="homework",
                homework_num=3,
                rule_name="testcases",
                rule_value="{bad json",
                is_active=True,
            )
        )
        session.commit()

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "admin-rollback", "admin-pass")
        grade_response = client.post(
            f"/api/admin/submissions/{submission_id}/grade",
            headers=_auth_headers(admin_token),
        )
        stored_result = session.exec(
            select(SubmissionResult).where(SubmissionResult.submission_id == submission_id)
        ).first()
        stored_case_results = session.exec(
            select(SubmissionCaseResult).where(
                SubmissionCaseResult.submission_id == submission_id
            )
        ).all()

        app.dependency_overrides.clear()

    assert grade_response.status_code == 400
    assert grade_response.json()["detail"] == "Invalid testcase configuration"
    assert stored_result is not None
    assert stored_result.manual_total_score == 91.0
    assert stored_result.adjustment_note == "Manual override"
    assert stored_result.adjusted_by == "admin-rollback"
    assert len(stored_case_results) == 1
    assert stored_case_results[0].case_name == "sample"
