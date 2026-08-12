from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from ..models.schemas import AdminBootstrapToken, User
from .auth_service import AuthService


class BootstrapError(ValueError):
    pass


def issue_bootstrap_token(session: Session, *, ttl_minutes: int = 15) -> str:
    if session.exec(select(User.id)).first() is not None:
        raise BootstrapError("Bootstrap token is unavailable after the first user exists")
    raw = secrets.token_urlsafe(32)
    session.add(
        AdminBootstrapToken(
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=datetime.now(UTC) + timedelta(minutes=max(ttl_minutes, 1)),
        )
    )
    session.commit()
    return raw


def consume_bootstrap_token(
    session: Session,
    *,
    token: str,
    user_id: str,
    sid: int,
    name: str,
    phone: str,
    email: str,
    password: str,
) -> User:
    if session.exec(select(User.id)).first() is not None:
        raise BootstrapError("Bootstrap is permanently closed")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    record = session.exec(
        select(AdminBootstrapToken).where(AdminBootstrapToken.token_hash == token_hash)
    ).first()
    now = datetime.now(UTC)
    if record is None or record.used_at is not None:
        raise BootstrapError("Bootstrap token is invalid")
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        raise BootstrapError("Bootstrap token has expired")
    user = User(
        id=user_id,
        sid=sid,
        name=name,
        phone=phone,
        email=email,
        ps=AuthService.get_password_hash(password),
        user_group="super_admin",
        is_active=True,
    )
    session.add(user)
    session.flush()
    record.used_at = now
    session.add(record)
    session.commit()
    session.refresh(user)
    return user
