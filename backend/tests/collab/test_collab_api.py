from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models.schemas import User
from app.services.auth_service import AuthService


engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
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
    response = client.post("/api/auth/login", json={"id": user_id, "ps": "password"})
    assert response.status_code == 200
    return response.json()["access_token"]


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_user_can_join_live_session():
    with Session(engine) as session:
        _create_user(session, "mentor", 10051001, "admin")
        _create_user(session, "student-member", 20251001, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        mentor_token = _login(client, "mentor")
        student_token = _login(client, "student-member")

        create_response = client.post(
            "/api/collab/sessions",
            json={"title": "Mentoring Room", "initial_code": "print('hello')\n"},
            headers={"Authorization": f"Bearer {mentor_token}"},
        )
        session_id = create_response.json()["id"]
        join_response = client.post(
            f"/api/collab/sessions/{session_id}/join",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert join_response.status_code == 200
    participants = join_response.json()["participants"]
    assert {participant["user_id"] for participant in participants} == {
        "mentor",
        "student-member",
    }


def test_non_member_cannot_edit_session():
    with Session(engine) as session:
        _create_user(session, "mentor", 10051002, "admin")
        _create_user(session, "joined-student", 20251002, "student")
        _create_user(session, "outsider", 20251003, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        mentor_token = _login(client, "mentor")
        outsider_token = _login(client, "outsider")

        create_response = client.post(
            "/api/collab/sessions",
            json={
                "title": "Protected Session",
                "participant_ids": ["joined-student"],
                "initial_code": "print('initial')\n",
            },
            headers={"Authorization": f"Bearer {mentor_token}"},
        )
        update_response = client.patch(
            f"/api/collab/sessions/{create_response.json()['id']}/code",
            json={"code": "print('changed')\n"},
            headers={"Authorization": f"Bearer {outsider_token}"},
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert update_response.status_code == 403
    assert update_response.json()["detail"] == "User is not a member of this session"


def test_session_history_is_persisted_after_close():
    with Session(engine) as session:
        _create_user(session, "mentor", 10051003, "admin")
        _create_user(session, "student-history", 20251004, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        mentor_token = _login(client, "mentor")
        student_token = _login(client, "student-history")

        create_response = client.post(
            "/api/collab/sessions",
            json={
                "title": "History Session",
                "participant_ids": ["student-history"],
                "initial_code": "print('seed')\n",
            },
            headers={"Authorization": f"Bearer {mentor_token}"},
        )
        session_id = create_response.json()["id"]
        update_response = client.patch(
            f"/api/collab/sessions/{session_id}/code",
            json={"code": "print('history')\n"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        message_response = client.post(
            f"/api/collab/sessions/{session_id}/messages",
            json={"content": "Need help with loops"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        close_response = client.post(
            f"/api/collab/sessions/{session_id}/close",
            headers={"Authorization": f"Bearer {mentor_token}"},
        )
        history_response = client.get(
            f"/api/collab/sessions/{session_id}/history",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert update_response.status_code == 200
    assert message_response.status_code == 200
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"
    assert history_response.status_code == 200
    assert history_response.json()["messages"][0]["content"] == "Need help with loops"
    assert history_response.json()["code_snapshots"][-1]["code_text"] == "print('history')\n"
