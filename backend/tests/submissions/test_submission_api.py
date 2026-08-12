import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models.schemas import (
    GradingRule,
    Homework,
    JudgeJob,
    Submission,
    SubmissionResult,
    User,
)
from app.services.auth_service import AuthService
from app.core.compression import decompress_text

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
    is_active: bool = True,
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
            is_active=is_active,
        )
    )
    session.commit()


def _create_allowed_languages_rule(
    session: Session, homework_num: int, languages: list[str]
) -> None:
    session.add(
        GradingRule(
            scope="homework",
            homework_num=homework_num,
            rule_name="allowed_languages",
            rule_value=json.dumps(languages),
            is_active=True,
        )
    )
    session.commit()


def _create_homework(
    session: Session,
    num: int,
    title: str,
    start_offset_days: int,
    deadline_offset_days: int,
) -> None:
    session.add(
        Homework(
            num=num,
            title=title,
            intro=f"{title} intro",
            starttime=_dt_string(start_offset_days),
            deadline=_dt_string(deadline_offset_days),
            codeName="main",
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


def test_create_submission_with_code_body(
    client,
    session,
    create_user,
    create_homework,
    login_user,
    auth_headers,
):
    create_homework(
        1, "Open Homework", start_offset_days=-1, deadline_offset_days=2
    )
    create_user("submitter", 20242001, "student-pass")

    token = login_user("submitter", "student-pass")
    response = client.post(
        "/api/submissions",
        json={
            "homework_num": 1,
            "language": "python",
            "code_text": "print('hello world')",
            "original_filename": "main.py",
        },
        headers=auth_headers(token),
    )
    saved_submissions = session.exec(select(Submission)).all()
    saved_results = session.exec(select(SubmissionResult)).all()

    assert response.status_code == 201
    payload = response.json()
    assert payload["homework_num"] == 1
    assert payload["homework_title"] == "Open Homework"
    assert payload["attempt_no"] == 1
    assert payload["status"] == "pending"
    assert payload["compile_status"] == "not_started"
    assert payload["run_status"] == "not_started"
    assert len(saved_submissions) == 1
    assert saved_submissions[0].code_text != "print('hello world')"
    assert (
        decompress_text(saved_submissions[0].code_text)
        == "print('hello world')"
    )
    assert len(saved_results) == 1
    assert (
        saved_results[0].grader_summary
        == "Submission accepted. Waiting for grading."
    )
    job = session.exec(select(JudgeJob)).one()
    assert job.job_type == "grade_submission"
    assert job.submission_id == saved_submissions[0].id


def test_production_submission_is_saved_without_host_execution(
    client,
    session,
    create_user,
    create_homework,
    login_user,
    auth_headers,
    monkeypatch,
):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTO_GRADING_ENABLED", "true")
    create_homework(
        101,
        "Production Safe Homework",
        start_offset_days=-1,
        deadline_offset_days=2,
    )
    create_user("safe-submitter", 20242101, "student-pass")

    token = login_user("safe-submitter", "student-pass")
    response = client.post(
        "/api/submissions",
        json={
            "homework_num": 101,
            "language": "python",
            "code_text": "print('never executed on host')",
            "original_filename": "main.py",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending_manual"
    stored_result = session.exec(select(SubmissionResult)).one()
    assert stored_result.status == "pending_manual"
    assert "isolated judge runner" in (stored_result.grader_summary or "")


def test_reject_submission_after_deadline(
    client,
    create_user,
    create_homework,
    login_user,
    auth_headers,
):
    create_homework(
        2, "Closed Homework", start_offset_days=-3, deadline_offset_days=-1
    )
    create_user("late-student", 20242002, "student-pass")

    token = login_user("late-student", "student-pass")
    response = client.post(
        "/api/submissions",
        json={
            "homework_num": 2,
            "language": "python",
            "code_text": "print('too late')",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Submission deadline has passed"


def test_reject_submission_before_opening(
    client,
    create_user,
    create_homework,
    login_user,
    auth_headers,
):
    create_homework(
        6, "Upcoming Homework", start_offset_days=2, deadline_offset_days=5
    )
    create_user("early-student", 20242008, "student-pass")

    token = login_user("early-student", "student-pass")
    response = client.post(
        "/api/submissions",
        json={
            "homework_num": 6,
            "language": "python",
            "code_text": "print('too early')",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Submission window has not opened"


def test_reject_submission_for_missing_homework():
    with Session(engine) as session:
        _create_user(session, "missing-homework", 20242009, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = _login(client, "missing-homework", "student-pass")
        response = client.post(
            "/api/submissions",
            json={
                "homework_num": 999,
                "language": "python",
                "code_text": "print('missing')",
            },
            headers=_auth_headers(token),
        )

        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Homework not found"


def test_reject_submission_for_unsupported_language():
    with Session(engine) as session:
        _create_homework(session, 7, "Language Homework", -1, 2)
        _create_user(session, "language-student", 20242010, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = _login(client, "language-student", "student-pass")
        response = client.post(
            "/api/submissions",
            json={
                "homework_num": 7,
                "language": "javascript",
                "code_text": "console.log('unsupported')",
            },
            headers=_auth_headers(token),
        )

        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported submission language"


def test_reject_submission_for_disallowed_language():
    with Session(engine) as session:
        _create_homework(session, 8, "Restricted Language Homework", -1, 2)
        _create_allowed_languages_rule(session, 8, ["python"])
        _create_user(session, "restricted-student", 20242011, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = _login(client, "restricted-student", "student-pass")
        response = client.post(
            "/api/submissions",
            json={
                "homework_num": 8,
                "language": "cpp",
                "code_text": "int main(){}",
            },
            headers=_auth_headers(token),
        )

        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Submission language is not allowed for this homework"
    )


def test_reject_submission_with_blank_code():
    with Session(engine) as session:
        _create_homework(session, 9, "Blank Homework", -1, 2)
        _create_user(session, "blank-student", 20242012, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = _login(client, "blank-student", "student-pass")
        response = client.post(
            "/api/submissions",
            json={
                "homework_num": 9,
                "language": "python",
                "code_text": "   ",
            },
            headers=_auth_headers(token),
        )

        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Submission must include code text"


def test_submission_persists_deadline_snapshot():
    with Session(engine) as session:
        _create_homework(session, 10, "Deadline Snapshot Homework", -1, 3)
        _create_user(session, "snapshot-owner", 20242013, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = _login(client, "snapshot-owner", "student-pass")
        response = client.post(
            "/api/submissions",
            json={
                "homework_num": 10,
                "language": "python",
                "code_text": "print('deadline snapshot')",
            },
            headers=_auth_headers(token),
        )
        stored_submission = session.exec(
            select(Submission).where(Submission.user_id == "snapshot-owner")
        ).one()
        homework = session.get(Homework, 10)

        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert homework is not None
    assert stored_submission.deadline_snapshot == homework.deadline
    assert response.json()["deadline_snapshot"] == homework.deadline


def test_owner_and_admin_can_read_submission_detail_and_feedback():
    with Session(engine) as session:
        _create_homework(session, 11, "Feedback Homework", -1, 2)
        _create_user(session, "feedback-owner", 20242014, "student-pass")
        _create_user(
            session, "feedback-admin", 10002014, "admin-pass", role="admin"
        )

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        owner_token = _login(client, "feedback-owner", "student-pass")
        admin_token = _login(client, "feedback-admin", "admin-pass")
        create_response = client.post(
            "/api/submissions",
            json={
                "homework_num": 11,
                "language": "python",
                "code_text": "print('feedback')",
            },
            headers=_auth_headers(owner_token),
        )
        submission_id = create_response.json()["id"]

        owner_detail = client.get(
            f"/api/submissions/{submission_id}",
            headers=_auth_headers(owner_token),
        )
        owner_feedback = client.get(
            f"/api/submissions/{submission_id}/feedback",
            headers=_auth_headers(owner_token),
        )
        admin_detail = client.get(
            f"/api/submissions/{submission_id}",
            headers=_auth_headers(admin_token),
        )
        admin_feedback = client.get(
            f"/api/submissions/{submission_id}/feedback",
            headers=_auth_headers(admin_token),
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert owner_detail.status_code == 200
    assert owner_feedback.status_code == 200
    assert admin_detail.status_code == 200
    assert admin_feedback.status_code == 200


def test_student_cannot_read_others_feedback():
    with Session(engine) as session:
        _create_homework(session, 12, "Protected Feedback Homework", -1, 2)
        _create_user(session, "feedback-owner", 20242015, "student-pass")
        _create_user(session, "feedback-viewer", 20242016, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        owner_token = _login(client, "feedback-owner", "student-pass")
        viewer_token = _login(client, "feedback-viewer", "student-pass")
        create_response = client.post(
            "/api/submissions",
            json={
                "homework_num": 12,
                "language": "python",
                "code_text": "print('feedback secret')",
            },
            headers=_auth_headers(owner_token),
        )
        submission_id = create_response.json()["id"]
        response = client.get(
            f"/api/submissions/{submission_id}/feedback",
            headers=_auth_headers(viewer_token),
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert response.status_code == 403
    assert response.json()["detail"] == "You cannot access this submission"


def test_student_can_list_own_submissions():
    with Session(engine) as session:
        _create_homework(session, 3, "List Homework", -1, 2)
        _create_user(session, "student-a", 20242003, "student-pass")
        _create_user(session, "student-b", 20242004, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        student_a_token = _login(client, "student-a", "student-pass")
        student_b_token = _login(client, "student-b", "student-pass")

        first_submission = client.post(
            "/api/submissions",
            json={
                "homework_num": 3,
                "language": "python",
                "code_text": "print('first')",
            },
            headers=_auth_headers(student_a_token),
        )
        second_submission = client.post(
            "/api/submissions",
            json={
                "homework_num": 3,
                "language": "python",
                "code_text": "print('second')",
            },
            headers=_auth_headers(student_a_token),
        )
        other_submission = client.post(
            "/api/submissions",
            json={
                "homework_num": 3,
                "language": "python",
                "code_text": "print('other')",
            },
            headers=_auth_headers(student_b_token),
        )
        response = client.get(
            "/api/submissions?homework_num=3",
            headers=_auth_headers(student_a_token),
        )

        app.dependency_overrides.clear()

    assert first_submission.status_code == 201
    assert second_submission.status_code == 201
    assert other_submission.status_code == 201
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert [item["user_id"] for item in payload] == ["student-a", "student-a"]
    assert [item["attempt_no"] for item in payload] == [2, 1]


def test_student_cannot_read_others_submission():
    with Session(engine) as session:
        _create_homework(session, 4, "Protected Homework", -1, 2)
        _create_user(session, "owner", 20242005, "student-pass")
        _create_user(session, "viewer", 20242006, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        owner_token = _login(client, "owner", "student-pass")
        viewer_token = _login(client, "viewer", "student-pass")
        create_response = client.post(
            "/api/submissions",
            json={
                "homework_num": 4,
                "language": "python",
                "code_text": "print('secret')",
            },
            headers=_auth_headers(owner_token),
        )
        submission_id = create_response.json()["id"]
        response = client.get(
            f"/api/submissions/{submission_id}",
            headers=_auth_headers(viewer_token),
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert response.status_code == 403
    assert response.json()["detail"] == "You cannot access this submission"


def test_create_submission_retries_after_attempt_conflict(tmp_path):
    race_engine = create_engine(
        f"sqlite:///{tmp_path / 'submission-race.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(race_engine)

    with Session(race_engine) as session:
        _create_homework(session, 5, "Race Homework", -1, 2)
        _create_user(session, "race-student", 20242007, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        token = _login(client, "race-student", "student-pass")

        original_flush = session.flush
        conflict_state = {"triggered": False}

        def flush_with_conflict(*args, **kwargs):
            pending_submission = any(
                isinstance(instance, Submission)
                and instance.user_id == "race-student"
                for instance in session.new
            )
            if conflict_state["triggered"] or not pending_submission:
                return original_flush(*args, **kwargs)

            conflict_state["triggered"] = True
            with Session(race_engine) as competing_session:
                competing_submission = Submission(
                    homework_num=5,
                    user_id="race-student",
                    submission_mode="official",
                    attempt_no=1,
                    language="python",
                    status="pending",
                    code_text="print('competing')\n",
                    original_filename="main.py",
                )
                competing_session.add(competing_submission)
                competing_session.commit()

            raise IntegrityError(
                "INSERT INTO submissions", {}, Exception("attempt conflict")
            )

        with patch.object(session, "flush", side_effect=flush_with_conflict):
            response = client.post(
                "/api/submissions",
                json={
                    "homework_num": 5,
                    "language": "python",
                    "code_text": "print('retry path')\n",
                    "original_filename": "main.py",
                },
                headers=_auth_headers(token),
            )

        stored_submissions = session.exec(
            select(Submission)
            .where(Submission.homework_num == 5)
            .order_by(Submission.attempt_no.asc())
        ).all()
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["attempt_no"] == 2
    assert [submission.attempt_no for submission in stored_submissions] == [
        1,
        2,
    ]


def test_create_submission_returns_conflict_after_retry_limit_exhausted(
    tmp_path,
):
    race_engine = create_engine(
        f"sqlite:///{tmp_path / 'submission-race-exhausted.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(race_engine)

    with Session(race_engine) as session:
        _create_homework(session, 13, "Exhausted Race Homework", -1, 2)
        _create_user(session, "race-exhausted", 20242017, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        token = _login(client, "race-exhausted", "student-pass")

        def always_conflict_flush(*args, **kwargs):
            pending_submission = any(
                isinstance(instance, Submission)
                and instance.user_id == "race-exhausted"
                for instance in session.new
            )
            if pending_submission:
                raise IntegrityError(
                    "INSERT INTO submissions", {}, Exception("attempt conflict")
                )
            return None

        with patch.object(session, "flush", side_effect=always_conflict_flush):
            response = client.post(
                "/api/submissions",
                json={
                    "homework_num": 13,
                    "language": "python",
                    "code_text": "print('retry exhausted')\n",
                    "original_filename": "main.py",
                },
                headers=_auth_headers(token),
            )

        stored_submissions = session.exec(
            select(Submission).where(Submission.homework_num == 13)
        ).all()
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "Submission attempt conflicted with another request. Please retry."
    )
    assert stored_submissions == []
