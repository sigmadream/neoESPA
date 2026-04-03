from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models.schemas import Homework, Submission, SubmissionResult, User
from app.services.auth_service import AuthService


engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def _dt_string(offset_days: int, offset_hours: int = 0) -> str:
    return (
        datetime.now(UTC) + timedelta(days=offset_days, hours=offset_hours)
    ).strftime("%Y-%m-%d %H:%M:%S")


def _create_user(session: Session, user_id: str, sid: int, password: str) -> None:
    session.add(
        User(
            id=user_id,
            sid=sid,
            ps=AuthService.get_password_hash(password),
            name=user_id,
            phone="010-0000-0000",
            email=f"{user_id}@example.com",
            user_group="student",
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
    response = client.post("/api/auth/login", json={"id": user_id, "ps": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_create_submission_with_code_body():
    with Session(engine) as session:
        _create_homework(session, 1, "Open Homework", -1, 2)
        _create_user(session, "submitter", 20242001, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = _login(client, "submitter", "student-pass")
        response = client.post(
            "/api/submissions",
            json={
                "homework_num": 1,
                "language": "python",
                "code_text": "print('hello world')",
                "original_filename": "main.py",
            },
            headers=_auth_headers(token),
        )
        saved_submissions = session.exec(select(Submission)).all()
        saved_results = session.exec(select(SubmissionResult)).all()

        app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["homework_num"] == 1
    assert payload["homework_title"] == "Open Homework"
    assert payload["attempt_no"] == 1
    assert payload["status"] == "retryable"
    assert payload["compile_status"] == "not_started"
    assert payload["run_status"] == "not_started"
    assert len(saved_submissions) == 1
    assert saved_submissions[0].code_text == "print('hello world')"
    assert len(saved_results) == 1
    assert (
        saved_results[0].grader_summary
        == "Auto-grading failed: Homework has no active test cases configured"
    )


def test_reject_submission_after_deadline():
    with Session(engine) as session:
        _create_homework(session, 2, "Closed Homework", -3, -1)
        _create_user(session, "late-student", 20242002, "student-pass")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = _login(client, "late-student", "student-pass")
        response = client.post(
            "/api/submissions",
            json={
                "homework_num": 2,
                "language": "python",
                "code_text": "print('too late')",
            },
            headers=_auth_headers(token),
        )

        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Submission deadline has passed"


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
                isinstance(instance, Submission) and instance.user_id == "race-student"
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

            raise IntegrityError("INSERT INTO submissions", {}, Exception("attempt conflict"))

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
    assert [submission.attempt_no for submission in stored_submissions] == [1, 2]
