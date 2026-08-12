from fastapi import APIRouter, Depends
from sqlmodel import Session

from ...api.dependencies import get_current_active_user
from ...api.runtime import notification_service
from ...core.db import get_session
from ...models.schemas import NotificationMarkReadRequest, NotificationRead, User


router = APIRouter()


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    return notification_service.list_for_user(session, current_user.id)


@router.post("/notifications/read", response_model=list[NotificationRead])
def mark_notifications_read(
    payload: NotificationMarkReadRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    if not payload.notification_ids:
        return []
    return notification_service.mark_read(session, current_user.id, payload.notification_ids)
