import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models.schemas import (
    GradingRule,
    Homework,
    Submission,
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
    role: str = "student",
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
    session: Session,
    *,
    num: int,
    title: str,
    start_offset_days: int,
    deadline_offset_days: int,
    deadline_offset_hours: int = 0,
    testcase_expected_output: str | None = None,
) -> None:
    session.add(
        Homework(
            num=num,
            title=title,
            intro=f"{title} intro",
            starttime=_dt_string(start_offset_days),
            deadline=_dt_string(deadline_offset_days, deadline_offset_hours),
            codeName="main",
        )
    )
    session.commit()
    if testcase_expected_output is None:
        return

    session.add(
        GradingRule(
            scope="homework",
            homework_num=num,
            rule_name="testcases",
            rule_value=json.dumps(
                {
                    "cases": [
                        {
                            "name": "main",
                            "input": "",
                            "expected_output": testcase_expected_output,
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


def _create_submission(
    session: Session,
    *,
    homework_num: int,
    user_id: str,
    status: str,
    submitted_offset_hours: int,
    total_score: float = 0.0,
) -> None:
    submitted_at = datetime.now(UTC) + timedelta(hours=submitted_offset_hours)
    submission = Submission(
        homework_num=homework_num,
        user_id=user_id,
        submission_mode="official",
        attempt_no=1,
        language="python",
        status=status,
        code_text="print('dashboard')",
        original_filename="main.py",
        deadline_snapshot=_dt_string(1),
        submitted_at=submitted_at,
    )
    session.add(submission)
    session.flush()

    result_status = "pending" if status == "pending" else "graded"
    session.add(
        SubmissionResult(
            submission_id=submission.id or 0,
            status=result_status,
            compile_status="success" if status != "pending" else "not_started",
            run_status="success" if status != "pending" else "not_started",
            total_score=total_score,
            submission_score=total_score,
            quality_score=0.0,
            grader_summary=(
                "Graded" if status != "pending" else "Waiting for grading."
            ),
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


def test_student_dashboard_returns_submission_summary():
    with Session(engine) as session:
        _create_user(session, "dashboard-student", 20243001, "student-pass")
        _create_homework(
            session,
            num=1,
            title="Closing Soon Homework",
            start_offset_days=-2,
            deadline_offset_days=0,
            deadline_offset_hours=8,
        )
        _create_homework(
            session,
            num=2,
            title="Graded Homework",
            start_offset_days=-5,
            deadline_offset_days=-1,
        )
        _create_homework(
            session,
            num=3,
            title="Pending Homework",
            start_offset_days=-2,
            deadline_offset_days=2,
        )
        _create_homework(
            session,
            num=4,
            title="Missed Homework",
            start_offset_days=-4,
            deadline_offset_days=-2,
        )
        _create_homework(
            session,
            num=5,
            title="Future Homework",
            start_offset_days=2,
            deadline_offset_days=4,
        )
        _create_submission(
            session,
            homework_num=2,
            user_id="dashboard-student",
            status="graded",
            submitted_offset_hours=-5,
            total_score=96.0,
        )
        _create_submission(
            session,
            homework_num=3,
            user_id="dashboard-student",
            status="pending",
            submitted_offset_hours=-1,
        )

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = _login(client, "dashboard-student", "student-pass")
        response = client.get(
            "/api/dashboard/me",
            headers=_auth_headers(token),
        )

        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()

    assert payload["overview"] == {
        "total_homeworks": 4,
        "submitted_homeworks": 2,
        "graded_homeworks": 1,
        "pending_homeworks": 1,
        "missing_homeworks": 1,
        "closing_soon_homeworks": 1,
        "average_latest_score": 96.0,
    }

    homework_items = {
        item["homework_num"]: item for item in payload["homework_items"]
    }
    assert 5 not in homework_items
    assert homework_items[1]["schedule_status"] == "closing_soon"
    assert homework_items[1]["submission_count"] == 0
    assert homework_items[1]["remaining_seconds"] > 0
    assert homework_items[2]["latest_submission_status"] == "graded"
    assert homework_items[2]["latest_score"] == 96.0
    assert homework_items[3]["latest_submission_status"] == "pending"
    assert homework_items[3]["latest_score"] is None
    assert homework_items[4]["schedule_status"] == "closed"
    assert homework_items[4]["submission_count"] == 0

    assert [item["homework_num"] for item in payload["recent_submissions"]] == [
        3,
        2,
    ]


def test_admin_dashboard_returns_assignment_metrics():
    with Session(engine) as session:
        _create_user(
            session, "dashboard-admin", 10043001, "admin-pass", role="admin"
        )
        _create_user(session, "student-one", 20243011, "student-pass")
        _create_user(session, "student-two", 20243012, "student-pass")
        _create_homework(
            session,
            num=1,
            title="Metric Homework",
            start_offset_days=-3,
            deadline_offset_days=2,
            testcase_expected_output="ok\n",
        )
        _create_homework(
            session,
            num=2,
            title="Queue Homework",
            start_offset_days=-2,
            deadline_offset_days=3,
            testcase_expected_output="pending\n",
        )

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "dashboard-admin", "admin-pass")
        student_one_token = _login(client, "student-one", "student-pass")
        student_two_token = _login(client, "student-two", "student-pass")

        graded_submission = client.post(
            "/api/submissions",
            json={
                "homework_num": 1,
                "language": "python",
                "code_text": "print('ok')\n",
                "original_filename": "main.py",
            },
            headers=_auth_headers(student_one_token),
        )
        failed_submission = client.post(
            "/api/submissions",
            json={
                "homework_num": 1,
                "language": "python",
                "code_text": "def broken(:\n    pass\n",
                "original_filename": "broken.py",
            },
            headers=_auth_headers(student_two_token),
        )
        queued_submission = client.post(
            "/api/submissions",
            json={
                "homework_num": 2,
                "language": "python",
                "code_text": "print('pending')\n",
                "original_filename": "pending.py",
            },
            headers=_auth_headers(student_one_token),
        )

        grade_good = client.post(
            f"/api/admin/submissions/{graded_submission.json()['id']}/grade",
            headers=_auth_headers(admin_token),
        )
        grade_bad = client.post(
            f"/api/admin/submissions/{failed_submission.json()['id']}/grade",
            headers=_auth_headers(admin_token),
        )
        queue_response = client.post(
            f"/api/admin/submissions/{queued_submission.json()['id']}/queue",
            headers=_auth_headers(admin_token),
        )
        dashboard_response = client.get(
            "/api/admin/dashboard",
            headers=_auth_headers(admin_token),
        )

        app.dependency_overrides.clear()

    assert graded_submission.status_code == 201
    assert failed_submission.status_code == 201
    assert queued_submission.status_code == 201
    assert grade_good.status_code == 200
    assert grade_bad.status_code == 200
    assert queue_response.status_code == 200
    assert dashboard_response.status_code == 200

    payload = dashboard_response.json()
    assert payload["total_homeworks"] == 2
    assert payload["active_students"] == 2
    assert payload["total_submissions"] == 3
    assert payload["queue"]["queue_size"] == 1
    assert payload["queue"]["queued_submission_ids"] == [
        queued_submission.json()["id"]
    ]

    homework_metrics = {
        item["homework_num"]: item for item in payload["homework_metrics"]
    }
    assert homework_metrics[1]["submitted_students"] == 2
    assert homework_metrics[1]["submission_rate"] == 100.0
    assert homework_metrics[1]["failed_submission_count"] == 1
    assert homework_metrics[2]["submitted_students"] == 1
    assert homework_metrics[2]["submission_rate"] == 50.0
    assert homework_metrics[2]["pending_submission_count"] == 1

    failure_metrics = {
        item["failure_type"]: item["count"]
        for item in payload["failure_metrics"]
    }
    assert failure_metrics["compile_failed"] == 1
