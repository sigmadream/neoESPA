from datetime import UTC, datetime

from ...models.schemas import User, UserRead
from ...services.user_management import ADMIN_ROLES, UserManagementError


def to_user_read(user: User) -> UserRead:
    fallback_timestamp = user.updated_at or user.created_at or datetime.now(UTC)
    return UserRead(
        id=user.id,
        sid=user.sid,
        name=user.name,
        phone=user.phone,
        email=user.email,
        user_group=user.user_group,
        is_active=user.is_active,
        created_at=user.created_at or fallback_timestamp,
        updated_at=user.updated_at or user.created_at or fallback_timestamp,
    )


def is_staff(user: User | None) -> bool:
    return user is not None and user.user_group in ADMIN_ROLES


def user_management_bad_request(error: UserManagementError):
    from fastapi import HTTPException, status

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    )
