import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

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


def test_code_changes_broadcast_to_participants():
    with Session(engine) as session:
        _create_user(session, "mentor", 10052001, "admin")
        _create_user(session, "student-a", 20252001, "student")
        _create_user(session, "student-b", 20252002, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        mentor_token = _login(client, "mentor")
        student_a_token = _login(client, "student-a")
        student_b_token = _login(client, "student-b")

        create_response = client.post(
            "/api/collab/sessions",
            json={
                "title": "WS Session",
                "participant_ids": ["student-a", "student-b"],
                "initial_code": "print('seed')\n",
            },
            headers={"Authorization": f"Bearer {mentor_token}"},
        )
        session_id = create_response.json()["id"]

        with client.websocket_connect(
            f"/ws/collab/sessions/{session_id}?token={student_a_token}"
        ) as first_socket, client.websocket_connect(
            f"/ws/collab/sessions/{session_id}?token={student_b_token}"
        ) as second_socket:
            assert first_socket.receive_json()["type"] == "session_state"
            assert second_socket.receive_json()["type"] == "session_state"

            first_socket.send_json({"type": "code_update", "code": "print('shared')\n"})
            first_broadcast = first_socket.receive_json()
            second_broadcast = second_socket.receive_json()

        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert first_broadcast["type"] == "code_update"
    assert second_broadcast["type"] == "code_update"
    assert second_broadcast["code"] == "print('shared')\n"


def test_create_collab_session_rejects_unknown_homework():
    with Session(engine) as session:
        _create_user(session, "mentor-homework-check", 10052003, "admin")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        mentor_token = _login(client, "mentor-homework-check")
        create_response = client.post(
            "/api/collab/sessions",
            json={
                "title": "Missing Homework Session",
                "homework_num": 999,
                "participant_ids": [],
                "initial_code": "",
            },
            headers={"Authorization": f"Bearer {mentor_token}"},
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 404
    assert create_response.json()["detail"] == "Homework not found"


def test_inactive_participant_cannot_connect_to_collab_websocket():
    with Session(engine) as session:
        _create_user(session, "mentor-inactive", 10052004, "admin")
        _create_user(session, "student-inactive", 20252003, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        mentor_token = _login(client, "mentor-inactive")
        student_token = _login(client, "student-inactive")

        create_response = client.post(
            "/api/collab/sessions",
            json={
                "title": "Inactive Student Session",
                "participant_ids": ["student-inactive"],
                "initial_code": "print('seed')\n",
            },
            headers={"Authorization": f"Bearer {mentor_token}"},
        )
        session_id = create_response.json()["id"]

        inactive_student = session.get(User, "student-inactive")
        assert inactive_student is not None
        inactive_student.is_active = False
        session.add(inactive_student)
        session.commit()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(
                f"/ws/collab/sessions/{session_id}?token={student_token}"
            ) as socket:
                socket.receive_json()

        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert exc_info.value.code == 4403
