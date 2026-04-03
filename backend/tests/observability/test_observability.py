from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models.schemas import Homework, Submission, SystemEventLog, User
from app.services.auth_service import AuthService


engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def _dt_string(offset_days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=offset_days)).strftime("%Y-%m-%d %H:%M:%S")


def _create_user(session: Session, user_id: str, sid: int, password: str, role: str) -> None:
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


def _login(client: TestClient, user_id: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"id": user_id, "ps": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_grading_failure_is_logged_with_submission_id():
    with Session(engine) as session:
        _create_user(session, "observer-admin", 10049001, "admin-pass", "admin")
        _create_user(session, "observer-student", 20249001, "student-pass", "student")
        session.add(
            Homework(
                num=1,
                title="Observed Homework",
                intro="Observe failures",
                starttime=_dt_string(-1),
                deadline=_dt_string(2),
                codeName="main",
            )
        )
        session.commit()
        submission = Submission(
            homework_num=1,
            user_id="observer-student",
            submission_mode="official",
            attempt_no=1,
            language="python",
            status="pending",
            code_text="",
            original_filename="main.py",
        )
        session.add(submission)
        session.commit()
        session.refresh(submission)

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "observer-admin", "admin-pass")
        response = client.post(
            f"/api/admin/submissions/{submission.id}/grade",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        logged_event = session.exec(
            select(SystemEventLog).where(SystemEventLog.submission_id == submission.id)
        ).first()

        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert logged_event is not None
    assert logged_event.category == "grading"
    assert logged_event.event_type == "grading_failed"
    assert logged_event.submission_id == submission.id
