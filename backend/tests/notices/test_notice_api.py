from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models.schemas import Notice, User
from app.services.auth_service import AuthService


engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


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


def test_list_notices_sorted_by_date():
    with Session(engine) as session:
        session.add(
            Notice(
                num=1,
                title="Older Notice",
                author="Admin",
                content="Older content",
                date="2026-03-01 08:00:00",
                is_pinned=False,
            )
        )
        session.add(
            Notice(
                num=2,
                title="Pinned Notice",
                author="Instructor",
                content="Pinned content",
                date="2026-03-02 08:00:00",
                is_pinned=True,
            )
        )
        session.add(
            Notice(
                num=3,
                title="Newest Notice",
                author="Instructor",
                content="Newest content",
                date="2026-03-03 08:00:00",
                is_pinned=False,
            )
        )
        session.commit()

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        response = client.get("/api/notice")
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert [notice["num"] for notice in payload] == [2, 3, 1]


def test_notice_detail_returns_content():
    with Session(engine) as session:
        session.add(
            Notice(
                num=10,
                title="Homework Guidance",
                author="Instructor",
                content="Detailed notice body",
                date="2026-03-05 10:00:00",
            )
        )
        session.commit()

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        response = client.get("/api/notice/10")
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Homework Guidance"
    assert payload["content"] == "Detailed notice body"


def test_scheduled_notice_is_hidden_from_student_but_visible_to_admin():
    future_date = (datetime.now(UTC) + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")

    with Session(engine) as session:
        session.add(
            Notice(
                num=20,
                title="Scheduled Notice",
                author="Instructor",
                content="Visible after publish time.",
                date=future_date,
                is_published=True,
            )
        )
        session.commit()
        _create_user(session, "notice-admin", 20242001, "admin-pass", "admin")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        student_list_response = client.get("/api/notice")
        student_detail_response = client.get("/api/notice/20")
        admin_token = _login(client, "notice-admin", "admin-pass")
        admin_list_response = client.get(
            "/api/notice",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        admin_detail_response = client.get(
            "/api/notice/20",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        app.dependency_overrides.clear()

    assert student_list_response.status_code == 200
    assert student_list_response.json() == []
    assert student_detail_response.status_code == 404
    assert admin_list_response.status_code == 200
    assert [notice["num"] for notice in admin_list_response.json()] == [20]
    assert admin_detail_response.status_code == 200


def test_inactive_staff_token_is_treated_as_anonymous_for_optional_notice_routes():
    future_date = (datetime.now(UTC) + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")

    with Session(engine) as session:
        session.add(
            Notice(
                num=30,
                title="Inactive Staff Hidden Notice",
                author="Instructor",
                content="Should stay hidden.",
                date=future_date,
                is_published=True,
            )
        )
        _create_user(session, "inactive-admin", 20242002, "admin-pass", "admin")
        session.commit()

        token = AuthService.create_access_token(
            data={"sub": "inactive-admin", "role": "admin"}
        )
        inactive_admin = session.get(User, "inactive-admin")
        assert inactive_admin is not None
        inactive_admin.is_active = False
        session.add(inactive_admin)
        session.commit()

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        list_response = client.get(
            "/api/notice",
            headers={"Authorization": f"Bearer {token}"},
        )
        detail_response = client.get(
            "/api/notice/30",
            headers={"Authorization": f"Bearer {token}"},
        )

        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert list_response.json() == []
    assert detail_response.status_code == 404
