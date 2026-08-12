from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models.schemas import Homework, Submission, SubmissionResult, User
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


def _create_submission(session: Session, homework_num: int, user_id: str, code_text: str) -> None:
    submission = Submission(
        homework_num=homework_num,
        user_id=user_id,
        submission_mode="official",
        attempt_no=1,
        language="python",
        status="graded",
        code_text=code_text,
        original_filename="main.py",
    )
    session.add(submission)
    session.flush()
    session.add(SubmissionResult(submission_id=submission.id or 0, status="graded"))
    session.commit()


def _login(client: TestClient, user_id: str) -> str:
    response = client.post("/api/auth/login", json={"id": user_id, "ps": "password"})
    assert response.status_code == 200
    return response.json()["access_token"]


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_admin_can_list_plagiarism_results():
    with Session(engine) as session:
        session.add(
            Homework(
                num=1,
                title="Plagiarism Homework",
                intro="Compare code",
                starttime=_dt_string(-1),
                deadline=_dt_string(2),
                codeName="main",
            )
        )
        session.commit()
        _create_user(session, "plag-admin", 10050001, "admin")
        _create_user(session, "plag-a", 20250021, "student")
        _create_user(session, "plag-b", 20250022, "student")
        _create_submission(session, 1, "plag-a", "print('same output')\n")
        _create_submission(session, 1, "plag-b", "print('same output')\n")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "plag-admin")
        run_response = client.post(
            "/api/admin/homeworks/1/plagiarism/run",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        list_response = client.get(
            "/api/admin/plagiarism/pairs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        detail_response = client.get(
            f"/api/admin/plagiarism/pairs/{list_response.json()[0]['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        app.dependency_overrides.clear()

    assert run_response.status_code == 200
    assert run_response.json()["flagged_pair_count"] == 1
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["left_user_id"] == "plag-a"
    assert detail_response.status_code == 200
    assert detail_response.json()["left_code"] == "print('same output')\n"
    assert detail_response.json()["right_code"] == "print('same output')\n"
