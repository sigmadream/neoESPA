import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

from app.core.db import get_session
from app.main import app
from app.models.schemas import CollabParticipant, User
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
    response = client.post(
        "/api/auth/login", json={"id": user_id, "ps": "password"}
    )
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

        with (
            client.websocket_connect(
                f"/ws/collab/sessions/{session_id}?token={student_a_token}"
            ) as first_socket,
            client.websocket_connect(
                f"/ws/collab/sessions/{session_id}?token={student_b_token}"
            ) as second_socket,
        ):
            assert first_socket.receive_json()["type"] == "session_state"
            assert second_socket.receive_json()["type"] == "session_state"

            first_socket.send_json(
                {"type": "code_update", "code": "print('shared')\n"}
            )
            first_broadcast = first_socket.receive_json()
            second_broadcast = second_socket.receive_json()

        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert first_broadcast["type"] == "code_update"
    assert second_broadcast["type"] == "code_update"
    assert second_broadcast["code"] == "print('shared')\n"


@pytest.mark.asyncio
async def test_async_history_read_reflects_websocket_updates():
    with Session(engine) as session:
        _create_user(session, "mentor-async", 10052005, "admin")
        _create_user(session, "student-async", 20252005, "student")

    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            mentor_login = await client.post(
                "/api/auth/login", json={"id": "mentor-async", "ps": "password"}
            )
            student_login = await client.post(
                "/api/auth/login",
                json={"id": "student-async", "ps": "password"},
            )
            assert mentor_login.status_code == 200
            assert student_login.status_code == 200
            mentor_token = mentor_login.json()["access_token"]
            student_token = student_login.json()["access_token"]

            create_response = await client.post(
                "/api/collab/sessions",
                json={
                    "title": "Async WS Session",
                    "participant_ids": ["student-async"],
                    "initial_code": "print('seed')\n",
                },
                headers={"Authorization": f"Bearer {mentor_token}"},
            )
            assert create_response.status_code == 200
            session_id = create_response.json()["id"]

            join_response = await client.post(
                f"/api/collab/sessions/{session_id}/join",
                headers={"Authorization": f"Bearer {student_token}"},
            )
            assert join_response.status_code == 200

            with TestClient(app) as ws_client:
                with ws_client.websocket_connect(
                    f"/ws/collab/sessions/{session_id}?token={student_token}"
                ) as socket:
                    session_state = socket.receive_json()
                    socket.send_json(
                        {"type": "chat", "content": "Need async help"}
                    )
                    chat_broadcast = socket.receive_json()
                    socket.send_json(
                        {
                            "type": "code_update",
                            "code": "print('async-shared')\n",
                        }
                    )
                    code_broadcast = socket.receive_json()

            history_response = await client.get(
                f"/api/collab/sessions/{session_id}/history",
                headers={"Authorization": f"Bearer {student_token}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert session_state["type"] == "session_state"
    assert session_state["code"] == "print('seed')\n"
    assert chat_broadcast == {
        "type": "chat",
        "user_id": "student-async",
        "content": "Need async help",
    }
    assert code_broadcast["type"] == "code_update"
    assert code_broadcast["code"] == "print('async-shared')\n"
    assert history_response.status_code == 200
    assert (
        history_response.json()["messages"][-1]["content"] == "Need async help"
    )
    assert (
        history_response.json()["code_snapshots"][-1]["code_text"]
        == "print('async-shared')\n"
    )


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


def test_websocket_requires_token():
    with Session(engine) as session:

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/collab/sessions/1") as socket:
                socket.receive_json()

        app.dependency_overrides.clear()

    assert exc_info.value.code == 4401


def test_closed_session_returns_4404_on_websocket_connect():
    with Session(engine) as session:
        _create_user(session, "mentor-closed-ws", 10052006, "admin")
        _create_user(session, "student-closed-ws", 20252006, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        mentor_token = _login(client, "mentor-closed-ws")
        student_token = _login(client, "student-closed-ws")
        create_response = client.post(
            "/api/collab/sessions",
            json={
                "title": "Closed WS Session",
                "participant_ids": ["student-closed-ws"],
                "initial_code": "print('seed')\n",
            },
            headers={"Authorization": f"Bearer {mentor_token}"},
        )
        session_id = create_response.json()["id"]
        close_response = client.post(
            f"/api/collab/sessions/{session_id}/close",
            headers={"Authorization": f"Bearer {mentor_token}"},
        )

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(
                f"/ws/collab/sessions/{session_id}?token={student_token}"
            ) as socket:
                socket.receive_json()

        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert close_response.status_code == 200
    assert exc_info.value.code == 4404


def test_non_editor_receives_websocket_error_frame():
    with Session(engine) as session:
        _create_user(session, "mentor-non-editor", 10052007, "admin")
        _create_user(session, "student-non-editor", 20252007, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        mentor_token = _login(client, "mentor-non-editor")
        student_token = _login(client, "student-non-editor")
        create_response = client.post(
            "/api/collab/sessions",
            json={
                "title": "Readonly WS Session",
                "participant_ids": ["student-non-editor"],
                "initial_code": "print('seed')\n",
            },
            headers={"Authorization": f"Bearer {mentor_token}"},
        )
        session_id = create_response.json()["id"]

        participant = session.exec(
            select(CollabParticipant).where(
                CollabParticipant.session_id == session_id,
                CollabParticipant.user_id == "student-non-editor",
            )
        ).one()
        participant.can_edit = False
        session.add(participant)
        session.commit()

        with client.websocket_connect(
            f"/ws/collab/sessions/{session_id}?token={student_token}"
        ) as socket:
            assert socket.receive_json()["type"] == "session_state"
            socket.send_json(
                {"type": "code_update", "code": "print('blocked')\n"}
            )
            error_response = socket.receive_json()

        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert error_response == {
        "type": "error",
        "detail": "Editing is not allowed.",
    }
