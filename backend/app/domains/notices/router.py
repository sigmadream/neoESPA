from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ...api.dependencies import get_optional_current_user, require_capability
from ...api.runtime import notification_service, observability_service
from ...core.db import get_session
from ...models.schemas import Notice, NoticeAdminWrite, NoticeRead, User
from ..notices.helpers import (
    notice_is_publicly_visible,
    notice_sort_key,
    normalize_notice_date,
    to_notice_read,
)
from ..users.serializers import is_staff

router = APIRouter()


@router.get("/notice", response_model=list[NoticeRead])
def get_notices(
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
):
    notices = session.exec(select(Notice)).all()
    visible_notices = (
        notices
        if is_staff(current_user)
        else [
            notice for notice in notices if notice_is_publicly_visible(notice)
        ]
    )
    visible_notices.sort(key=notice_sort_key, reverse=True)
    return [to_notice_read(notice) for notice in visible_notices]


@router.get("/notice/{notice_num}", response_model=NoticeRead)
def get_notice_detail(
    notice_num: int,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
):
    notice = session.get(Notice, notice_num)
    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    if not is_staff(current_user) and not notice_is_publicly_visible(notice):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )
    return to_notice_read(notice)


@router.get("/admin/notices", response_model=list[NoticeRead])
def get_admin_notices(
    _: User = Depends(require_capability("content:manage")),
    session: Session = Depends(get_session),
):
    notices = session.exec(select(Notice)).all()
    notices.sort(key=notice_sort_key, reverse=True)
    return [to_notice_read(notice) for notice in notices]


@router.post(
    "/admin/notices",
    response_model=NoticeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_notice(
    payload: NoticeAdminWrite,
    current_user: User = Depends(require_capability("content:manage")),
    session: Session = Depends(get_session),
):
    notice = Notice(
        title=payload.title,
        author=payload.author,
        content=payload.content,
        date=normalize_notice_date(payload.date),
        is_pinned=payload.is_pinned,
        is_published=payload.is_published,
        updated_at=datetime.now(UTC),
    )
    session.add(notice)
    session.flush()
    if notice_is_publicly_visible(notice):
        notification_service.notify_notice_publication(session, notice)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="create_notice",
        target_type="notice",
        target_id=str(notice.num or 0),
        payload=payload.model_dump(),
    )
    session.commit()
    session.refresh(notice)
    return to_notice_read(notice)


@router.patch("/admin/notices/{notice_num}", response_model=NoticeRead)
def update_notice(
    notice_num: int,
    payload: NoticeAdminWrite,
    current_user: User = Depends(require_capability("content:manage")),
    session: Session = Depends(get_session),
):
    notice = session.get(Notice, notice_num)
    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    was_public = notice_is_publicly_visible(notice)
    notice.title = payload.title
    notice.author = payload.author
    notice.content = payload.content
    notice.date = normalize_notice_date(payload.date)
    notice.is_pinned = payload.is_pinned
    notice.is_published = payload.is_published
    notice.updated_at = datetime.now(UTC)
    session.add(notice)
    if not was_public and notice_is_publicly_visible(notice):
        notification_service.notify_notice_publication(session, notice)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="update_notice",
        target_type="notice",
        target_id=str(notice_num),
        payload=payload.model_dump(),
    )
    session.commit()
    session.refresh(notice)
    return to_notice_read(notice)


@router.delete("/admin/notices/{notice_num}")
def delete_notice(
    notice_num: int,
    current_user: User = Depends(require_capability("content:manage")),
    session: Session = Depends(get_session),
):
    notice = session.get(Notice, notice_num)
    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found"
        )

    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="delete_notice",
        target_type="notice",
        target_id=str(notice_num),
        payload={"title": notice.title},
    )
    session.delete(notice)
    session.commit()
    return {"message": "Notice deleted successfully"}
