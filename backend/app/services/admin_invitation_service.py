from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from ..models.schemas import AdminInvitation, User
from .auth_service import AuthService

ADMIN_INVITABLE_ROLES = {
    "admin",
    "problem_setter",
    "reviewer",
    "judge_operator",
    "support",
    "viewer",
}


class AdminInvitationError(ValueError):
    pass


def issue_admin_invitation(
    session: Session,
    *,
    email: str,
    role_name: str,
    created_by: str,
    ttl_minutes: int,
) -> tuple[AdminInvitation, str]:
    normalized_email = email.strip().lower()
    if "@" not in normalized_email:
        raise AdminInvitationError("A valid email is required")
    if role_name not in ADMIN_INVITABLE_ROLES:
        raise AdminInvitationError(
            "Role cannot be assigned through an invitation"
        )
    raw = secrets.token_urlsafe(32)
    invitation = AdminInvitation(
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        email=normalized_email,
        role_name=role_name,
        created_by=created_by,
        expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
    )
    session.add(invitation)
    session.flush()
    return invitation, raw


def accept_admin_invitation(
    session: Session,
    *,
    token: str,
    user_id: str,
    sid: int,
    name: str,
    phone: str,
    password: str,
) -> User:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    invitation = session.exec(
        select(AdminInvitation).where(AdminInvitation.token_hash == token_hash)
    ).first()
    now = datetime.now(UTC)
    if invitation is None or invitation.used_at is not None:
        raise AdminInvitationError("Invitation token is invalid")
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        raise AdminInvitationError("Invitation token has expired")
    user = User(
        id=user_id,
        sid=sid,
        name=name.strip(),
        phone=phone.strip(),
        email=invitation.email,
        ps=AuthService.get_password_hash(password),
        user_group=invitation.role_name,
        is_active=True,
    )
    session.add(user)
    session.flush()
    invitation.used_at = now
    session.add(invitation)
    session.commit()
    session.refresh(user)
    return user
