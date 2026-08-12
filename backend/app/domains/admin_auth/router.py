from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from ...core.db import get_session
from ...api.dependencies import get_current_active_user, require_step_up
from ...api.runtime import observability_service
from ...models.schemas import (
    AdminBootstrapCreate, AdminInvitationAccept, AdminInvitationCreate,
    AdminInvitationIssued, User, UserRead,
)
from ...services.bootstrap_service import BootstrapError, consume_bootstrap_token
from ...services.admin_invitation_service import (
    AdminInvitationError, accept_admin_invitation, issue_admin_invitation,
)
from ..users.serializers import to_user_read


router = APIRouter(prefix="/admin-auth")


@router.post("/bootstrap", response_model=UserRead, status_code=201)
def bootstrap_first_admin(
    payload: AdminBootstrapCreate,
    session: Session = Depends(get_session),
):
    try:
        user = consume_bootstrap_token(
            session,
            token=payload.token,
            user_id=payload.id,
            sid=payload.sid,
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
            password=payload.password,
        )
        return to_user_read(user)
    except BootstrapError as error:
        session.rollback()
        raise HTTPException(status_code=403, detail=str(error)) from error
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Admin identity already exists") from error


@router.post("/invitations", response_model=AdminInvitationIssued, status_code=201)
def create_admin_invitation(
    payload: AdminInvitationCreate,
    current_user: User = Depends(require_step_up("user:manage")),
    session: Session = Depends(get_session),
):
    try:
        invitation, token = issue_admin_invitation(
            session, email=payload.email, role_name=payload.role_name,
            created_by=current_user.id, ttl_minutes=payload.ttl_minutes,
        )
        observability_service.record_audit(
            session, actor_user_id=current_user.id,
            action_type="issue_admin_invitation", target_type="admin_invitation",
            target_id=str(invitation.id),
            payload={"email": invitation.email, "role_name": invitation.role_name},
        )
        session.commit()
        session.refresh(invitation)
        return AdminInvitationIssued(
            id=invitation.id or 0, token=token, email=invitation.email,
            role_name=invitation.role_name, expires_at=invitation.expires_at,
        )
    except AdminInvitationError as error:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/invitations/accept", response_model=UserRead, status_code=201)
def accept_invitation(
    payload: AdminInvitationAccept,
    session: Session = Depends(get_session),
):
    try:
        user = accept_admin_invitation(
            session, token=payload.token, user_id=payload.id, sid=payload.sid,
            name=payload.name, phone=payload.phone, password=payload.password,
        )
        return to_user_read(user)
    except AdminInvitationError as error:
        session.rollback()
        raise HTTPException(status_code=403, detail=str(error)) from error
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Admin identity already exists") from error
