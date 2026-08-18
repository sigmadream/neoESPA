from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlmodel import Session, select

from ...api.dependencies import get_current_active_user, require_capability
from ...api.runtime import collab_ws_manager, observability_service
from ...core.db import get_session
from ...core.config import settings
from ...models.schemas import (
    CollabChatWrite,
    CollabCodeSnapshot,
    CollabCodeUpdate,
    CollabHistoryRead,
    CollabMessage,
    CollabMessageRead,
    CollabParticipant,
    CollabSession,
    CollabSessionCreate,
    CollabSessionRead,
    Homework,
    User,
)
from ...services.auth_service import AuthService
from ..collab.helpers import (
    active_collab_participant,
    ensure_collab_snapshot,
    require_collab_member,
    to_collab_message_read,
    to_collab_session_read,
    to_collab_snapshot_read,
)
from ..settings.helpers import get_system_setting_value
from ..users.serializers import is_staff

router = APIRouter()
ws_router = APIRouter()


def _enforce_collab_code_size(session: Session, code: str) -> None:
    max_source_bytes = int(
        float(get_system_setting_value(session, "submission_max_source_bytes"))
    )
    if len(code.encode("utf-8")) > max_source_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Collaboration code exceeds {max_source_bytes} byte limit",
        )


@router.get("/collab/sessions", response_model=list[CollabSessionRead])
def list_collab_sessions(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    statement = (
        select(CollabSession)
        .join(
            CollabParticipant,
            CollabParticipant.session_id == CollabSession.id,
        )
        .where(
            CollabParticipant.user_id == current_user.id,
            CollabParticipant.left_at.is_(None),
        )
        .order_by(CollabSession.created_at.desc(), CollabSession.id.desc())
    )
    sessions = session.exec(statement).all()
    return [
        to_collab_session_read(session, collab_session)
        for collab_session in sessions
        if collab_session.status == "active" or is_staff(current_user)
    ]


@router.post("/collab/sessions", response_model=CollabSessionRead)
def create_collab_session(
    payload: CollabSessionCreate,
    current_user: User = Depends(require_capability("collaboration:manage")),
    session: Session = Depends(get_session),
):
    _enforce_collab_code_size(session, payload.initial_code)
    if (
        payload.homework_num is not None
        and session.get(Homework, payload.homework_num) is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found"
        )

    collab_session = CollabSession(
        title=payload.title,
        homework_num=payload.homework_num,
        mentor_id=current_user.id,
        status="active",
        current_code=payload.initial_code,
    )
    session.add(collab_session)
    session.flush()
    session.add(
        CollabParticipant(
            session_id=collab_session.id or 0,
            user_id=current_user.id,
            role="mentor",
            can_edit=True,
        )
    )
    for participant_id in payload.participant_ids:
        if participant_id == current_user.id:
            continue
        if session.get(User, participant_id) is None:
            continue
        session.add(
            CollabParticipant(
                session_id=collab_session.id or 0,
                user_id=participant_id,
                role="member",
                can_edit=True,
            )
        )
    ensure_collab_snapshot(session, collab_session, user_id=current_user.id)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="create_collab_session",
        target_type="collab_session",
        target_id=str(collab_session.id or 0),
        payload=payload.model_dump(),
    )
    session.commit()
    session.refresh(collab_session)
    return to_collab_session_read(session, collab_session)


@router.post(
    "/collab/sessions/{session_id}/join", response_model=CollabSessionRead
)
def join_collab_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    collab_session = session.get(CollabSession, session_id)
    if collab_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    if collab_session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Session is closed"
        )

    participant = active_collab_participant(
        session, session_id, current_user.id
    )
    if participant is None:
        participant = session.exec(
            select(CollabParticipant).where(
                CollabParticipant.session_id == session_id,
                CollabParticipant.user_id == current_user.id,
            )
        ).first()
        if participant is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="An invitation is required to join this session",
            )
        participant.left_at = None
        participant.joined_at = datetime.now(UTC)
        session.add(participant)
        session.commit()

    return to_collab_session_read(session, collab_session)


@router.patch(
    "/collab/sessions/{session_id}/code", response_model=CollabSessionRead
)
def update_collab_code(
    session_id: int,
    payload: CollabCodeUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    _enforce_collab_code_size(session, payload.code)
    collab_session = session.get(CollabSession, session_id)
    if collab_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    participant = require_collab_member(session, session_id, current_user.id)
    if not participant.can_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Participant cannot edit this session",
        )

    collab_session.current_code = payload.code
    session.add(collab_session)
    ensure_collab_snapshot(session, collab_session, user_id=current_user.id)
    session.commit()
    session.refresh(collab_session)
    return to_collab_session_read(session, collab_session)


@router.post(
    "/collab/sessions/{session_id}/messages", response_model=CollabMessageRead
)
def create_collab_message(
    session_id: int,
    payload: CollabChatWrite,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_collab_member(session, session_id, current_user.id)
    message = CollabMessage(
        session_id=session_id,
        user_id=current_user.id,
        content=payload.content,
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    return to_collab_message_read(message)


@router.post(
    "/collab/sessions/{session_id}/close", response_model=CollabSessionRead
)
def close_collab_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    collab_session = session.get(CollabSession, session_id)
    if collab_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    if collab_session.mentor_id != current_user.id and not is_staff(
        current_user
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the mentor or staff can close this session",
        )

    collab_session.status = "closed"
    collab_session.closed_at = datetime.now(UTC)
    session.add(collab_session)
    ensure_collab_snapshot(session, collab_session, user_id=current_user.id)
    session.commit()
    session.refresh(collab_session)
    return to_collab_session_read(session, collab_session)


@router.get(
    "/collab/sessions/{session_id}/history", response_model=CollabHistoryRead
)
def get_collab_session_history(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    collab_session = session.get(CollabSession, session_id)
    if collab_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    require_collab_member(session, session_id, current_user.id)

    messages = session.exec(
        select(CollabMessage)
        .where(CollabMessage.session_id == session_id)
        .order_by(CollabMessage.created_at.asc(), CollabMessage.id.asc())
    ).all()
    snapshots = session.exec(
        select(CollabCodeSnapshot)
        .where(CollabCodeSnapshot.session_id == session_id)
        .order_by(
            CollabCodeSnapshot.created_at.asc(), CollabCodeSnapshot.id.asc()
        )
    ).all()
    return CollabHistoryRead(
        session=to_collab_session_read(session, collab_session),
        messages=[to_collab_message_read(message) for message in messages],
        code_snapshots=[
            to_collab_snapshot_read(snapshot) for snapshot in snapshots
        ],
    )


@ws_router.websocket("/ws/collab/sessions/{session_id}")
async def collab_session_websocket(
    websocket: WebSocket,
    session_id: int,
    session: Session = Depends(get_session),
):
    token = websocket.query_params.get("token") or websocket.cookies.get(
        settings.AUTH_COOKIE_NAME
    )
    if not token:
        await websocket.close(code=4401)
        return

    payload = AuthService.decode_token(token)
    user_id = payload.get("sub") if payload else None
    if user_id is None:
        await websocket.close(code=4401)
        return

    user = session.get(User, user_id)
    if user is None:
        await websocket.close(code=4401)
        return
    if int(payload.get("ver", 0)) != user.token_version:
        await websocket.close(code=4401)
        return
    if not user.is_active:
        await websocket.close(code=4403)
        return

    participant = active_collab_participant(session, session_id, user.id)
    if participant is None:
        await websocket.close(code=4403)
        return

    collab_session = session.get(CollabSession, session_id)
    if collab_session is None or collab_session.status != "active":
        await websocket.close(code=4404)
        return

    database_bind = session.get_bind()
    initial_code = collab_session.current_code
    session.close()

    await collab_ws_manager.connect(session_id, websocket)
    await websocket.send_json(
        {
            "type": "session_state",
            "code": initial_code,
            "user_id": user.id,
        }
    )

    try:
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")
            broadcast_payload = None
            with Session(database_bind) as message_session:
                current_user = message_session.get(User, user_id)
                current_participant = active_collab_participant(
                    message_session, session_id, user_id
                )
                current_collab_session = message_session.get(
                    CollabSession, session_id
                )
                if current_user is None or not current_user.is_active:
                    await websocket.close(code=4403)
                    break
                if current_participant is None:
                    await websocket.close(code=4403)
                    break
                if (
                    current_collab_session is None
                    or current_collab_session.status != "active"
                ):
                    await websocket.close(code=4404)
                    break

                if message_type == "code_update":
                    if not current_participant.can_edit:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "detail": "Editing is not allowed.",
                            }
                        )
                        continue
                    code = str(message.get("code", ""))
                    try:
                        _enforce_collab_code_size(message_session, code)
                    except HTTPException as error:
                        await websocket.send_json(
                            {"type": "error", "detail": error.detail}
                        )
                        continue
                    current_collab_session.current_code = code
                    message_session.add(current_collab_session)
                    ensure_collab_snapshot(
                        message_session,
                        current_collab_session,
                        user_id=user_id,
                        min_interval_seconds=5,
                    )
                    message_session.commit()
                    broadcast_payload = {
                        "type": "code_update",
                        "code": code,
                        "user_id": user_id,
                    }
                elif message_type == "chat":
                    content = str(message.get("content", ""))
                    message_session.add(
                        CollabMessage(
                            session_id=session_id,
                            user_id=user_id,
                            content=content,
                        )
                    )
                    message_session.commit()
                    broadcast_payload = {
                        "type": "chat",
                        "user_id": user_id,
                        "content": content,
                    }
                else:
                    await websocket.send_json(
                        {"type": "error", "detail": "Unknown message type."}
                    )

            if broadcast_payload is not None:
                await collab_ws_manager.broadcast(session_id, broadcast_payload)
    except WebSocketDisconnect:
        pass
    except TypeError, ValueError:
        await websocket.close(code=4400)
    finally:
        collab_ws_manager.disconnect(session_id, websocket)
