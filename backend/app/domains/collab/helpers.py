from fastapi import HTTPException, status
from sqlmodel import Session, select

from ...core.compression import compress_text, decompress_text
from ...models.schemas import (
    CollabCodeSnapshot,
    CollabCodeSnapshotRead,
    CollabMessage,
    CollabMessageRead,
    CollabParticipant,
    CollabParticipantRead,
    CollabSession,
    CollabSessionRead,
)


def load_collab_participants(
    session: Session,
    session_id: int,
) -> list[CollabParticipant]:
    return session.exec(
        select(CollabParticipant)
        .where(CollabParticipant.session_id == session_id)
        .order_by(CollabParticipant.joined_at.asc(), CollabParticipant.id.asc())
    ).all()


def to_collab_participant_read(participant: CollabParticipant) -> CollabParticipantRead:
    return CollabParticipantRead(
        user_id=participant.user_id,
        role=participant.role,
        can_edit=participant.can_edit,
        joined_at=participant.joined_at,
        left_at=participant.left_at,
    )


def to_collab_session_read(
    session: Session,
    collab_session: CollabSession,
) -> CollabSessionRead:
    participants = load_collab_participants(session, collab_session.id or 0)
    return CollabSessionRead(
        id=collab_session.id or 0,
        title=collab_session.title,
        homework_num=collab_session.homework_num,
        mentor_id=collab_session.mentor_id,
        status=collab_session.status,
        current_code=collab_session.current_code,
        participants=[
            to_collab_participant_read(participant) for participant in participants
        ],
        created_at=collab_session.created_at,
        closed_at=collab_session.closed_at,
    )


def to_collab_message_read(message: CollabMessage) -> CollabMessageRead:
    return CollabMessageRead(
        id=message.id or 0,
        session_id=message.session_id,
        user_id=message.user_id,
        content=message.content,
        created_at=message.created_at,
    )


def to_collab_snapshot_read(snapshot: CollabCodeSnapshot) -> CollabCodeSnapshotRead:
    return CollabCodeSnapshotRead(
        id=snapshot.id or 0,
        session_id=snapshot.session_id,
        user_id=snapshot.user_id,
        code_text=decompress_text(snapshot.code_text),
        created_at=snapshot.created_at,
    )


def active_collab_participant(
    session: Session,
    session_id: int,
    user_id: str,
) -> CollabParticipant | None:
    return session.exec(
        select(CollabParticipant).where(
            CollabParticipant.session_id == session_id,
            CollabParticipant.user_id == user_id,
            CollabParticipant.left_at.is_(None),
        )
    ).first()


def require_collab_member(
    session: Session,
    session_id: int,
    user_id: str,
) -> CollabParticipant:
    participant = active_collab_participant(session, session_id, user_id)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this session",
        )
    return participant


def ensure_collab_snapshot(
    session: Session,
    collab_session: CollabSession,
    *,
    user_id: str | None,
) -> None:
    session.add(
        CollabCodeSnapshot(
            session_id=collab_session.id or 0,
            user_id=user_id,
            code_text=compress_text(collab_session.current_code),
        )
    )
