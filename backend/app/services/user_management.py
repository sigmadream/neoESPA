import re
from datetime import UTC, datetime

from sqlmodel import Session, select

from ..models.schemas import AdminUserWrite, User
from .auth_service import AuthService

VALID_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ADMIN_ROLES = {
    "super_admin",
    "admin",
    "instructor",
    "ta",
    "problem_setter",
    "reviewer",
    "judge_operator",
    "support",
    "viewer",
}
MANAGEABLE_USER_ROLES = ADMIN_ROLES | {"student"}


class UserManagementError(ValueError):
    pass


def validate_email_policy(email: str) -> None:
    if not VALID_EMAIL_PATTERN.match(email):
        raise UserManagementError(
            "Email does not satisfy the registration policy"
        )


def ensure_unique_sid(session: Session, sid: int) -> None:
    existing_user = session.exec(select(User).where(User.sid == sid)).first()
    if existing_user:
        raise UserManagementError("Student ID already exists")


def normalize_user_group(user_group: str) -> str:
    normalized_group = (user_group or "").strip().lower()
    if normalized_group not in MANAGEABLE_USER_ROLES:
        raise UserManagementError("Unsupported user role")
    return normalized_group


def get_user_by_sid(session: Session, sid: int) -> User | None:
    return session.exec(select(User).where(User.sid == sid)).first()


def create_managed_user(
    session: Session,
    payload: AdminUserWrite,
    *,
    default_password: str | None = None,
) -> User:
    existing_user = session.get(User, payload.id)
    if existing_user is not None:
        raise UserManagementError(f"User already exists: {payload.id}")

    if get_user_by_sid(session, payload.sid) is not None:
        raise UserManagementError(f"Student ID already exists: {payload.sid}")

    validate_email_policy(payload.email)
    normalized_role = normalize_user_group(payload.user_group)
    password = (payload.ps or default_password or "").strip()
    if not password:
        raise UserManagementError(f"Password is required for user {payload.id}")

    now = datetime.now(UTC)
    return User(
        id=payload.id,
        sid=payload.sid,
        ps=AuthService.get_password_hash(password),
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        user_group=normalized_role,
        is_active=payload.is_active,
        created_at=now,
        updated_at=now,
    )


def create_admin_user(
    session: Session,
    *,
    user_id: str,
    sid: int,
    password: str,
    name: str,
    phone: str,
    email: str,
    is_active: bool = True,
) -> User:
    return create_managed_user(
        session,
        AdminUserWrite(
            id=user_id,
            sid=sid,
            ps=password,
            name=name,
            phone=phone,
            email=email,
            user_group="admin",
            is_active=is_active,
        ),
    )
