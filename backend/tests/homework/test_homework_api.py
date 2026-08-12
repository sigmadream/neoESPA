from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models.schemas import Homework, User
from app.services.auth_service import AuthService


engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def _dt_string(offset_days: int, offset_hours: int = 0) -> str:
    return (
        datetime.now(UTC) + timedelta(days=offset_days, hours=offset_hours)
    ).strftime("%Y-%m-%d %H:%M:%S")


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


def test_list_homeworks_for_student():
    with Session(engine) as session:
        session.add(
            Homework(
                num=1,
                title="Visible Homework",
                intro="Available to students.",
                deadline=_dt_string(3),
                starttime=_dt_string(-2),
                codeName="main",
                sec=2,
                sbnum=5,
                isLint=True,
            )
        )
        session.commit()
        _create_user(session, "student-homework", 20241001, "student-pass", "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = _login(client, "student-homework", "student-pass")
        response = client.get(
            "/api/homework",
            headers={"Authorization": f"Bearer {token}"},
        )

        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["title"] == "Visible Homework"
    assert payload[0]["schedule_status"] == "open"
    assert payload[0]["can_submit"] is True


def test_homework_detail_returns_assignment_metadata():
    with Session(engine) as session:
        session.add(
            Homework(
                num=7,
                title="Metadata Homework",
                intro="Detailed metadata must be returned.",
                deadline=_dt_string(0, 12),
                starttime=_dt_string(-1),
                codeName="solution",
                filename="guide.pdf",
                ratedatanum=8,
                sec=3,
                sbnum=4,
                isLint=True,
                vitalSpace=True,
                disorderedOutput=False,
            )
        )
        session.commit()

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        response = client.get("/api/homework/7")
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["num"] == 7
    assert payload["filename"] == "guide.pdf"
    assert payload["ratedatanum"] == 8
    assert payload["sec"] == 3
    assert payload["sbnum"] == 4
    assert payload["isLint"] is True


def test_future_homework_is_hidden_from_student():
    with Session(engine) as session:
        session.add(
            Homework(
                num=9,
                title="Future Homework",
                intro="Should stay hidden from students.",
                deadline=_dt_string(10),
                starttime=_dt_string(3),
                codeName="future",
            )
        )
        session.commit()
        _create_user(session, "student-hidden", 20241002, "student-pass", "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        token = _login(client, "student-hidden", "student-pass")
        list_response = client.get(
            "/api/homework",
            headers={"Authorization": f"Bearer {token}"},
        )
        detail_response = client.get(
            "/api/homework/9",
            headers={"Authorization": f"Bearer {token}"},
        )

        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert list_response.json() == []
    assert detail_response.status_code == 404
