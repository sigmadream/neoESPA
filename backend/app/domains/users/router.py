from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from ...api.dependencies import get_current_active_user, require_roles
from ...api.runtime import observability_service
from ...core.db import get_session
from ...models.schemas import (
    AdminPasswordResetRequest,
    BulkUserCreateRequest,
    BulkUserCreateResult,
    User,
    UserProfileUpdate,
    UserRead,
    UserRoleUpdate,
    UserStatusUpdate,
)
from ...services.auth_service import AuthService
from ...services.user_management import (
    UserManagementError,
    create_managed_user,
    get_user_by_sid,
    normalize_user_group,
    validate_email_policy,
)
from ..users.serializers import to_user_read, user_management_bad_request


router = APIRouter()


@router.get("/users/me", response_model=UserRead)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return to_user_read(current_user)


@router.patch("/users/me", response_model=UserRead)
async def update_my_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    try:
        validate_email_policy(payload.email)
    except UserManagementError as error:
        raise user_management_bad_request(error) from error

    current_user.name = payload.name.strip()
    current_user.phone = payload.phone.strip()
    current_user.email = payload.email.strip()
    current_user.updated_at = datetime.now(UTC)
    session.add(current_user)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="update_my_profile",
        target_type="user",
        target_id=current_user.id,
        payload=payload.model_dump(),
    )
    session.commit()
    session.refresh(current_user)
    return to_user_read(current_user)


@router.get("/admin/users", response_model=list[UserRead])
async def list_admin_users(
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    _: User = Depends(require_roles("admin")),
    session: Session = Depends(get_session),
):
    users = session.exec(select(User).order_by(User.sid, User.id)).all()

    normalized_search = (search or "").strip().lower()
    try:
        normalized_role = normalize_user_group(role) if role else None
    except UserManagementError as error:
        raise user_management_bad_request(error) from error

    visible_users: list[User] = []
    for user in users:
        if normalized_role is not None and user.user_group != normalized_role:
            continue
        if is_active is not None and user.is_active != is_active:
            continue
        if normalized_search:
            haystack = " ".join(
                [
                    user.id.lower(),
                    user.name.lower(),
                    user.email.lower(),
                    user.phone.lower(),
                    str(user.sid),
                ]
            )
            if normalized_search not in haystack:
                continue
        visible_users.append(user)

    return [to_user_read(user) for user in visible_users]


@router.patch("/admin/users/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    current_user: User = Depends(require_roles("admin")),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    try:
        normalized_role = normalize_user_group(payload.user_group)
    except UserManagementError as error:
        raise user_management_bad_request(error) from error
    if user.id == current_user.id and normalized_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    user.user_group = normalized_role
    user.updated_at = datetime.now(UTC)
    session.add(user)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="update_user_role",
        target_type="user",
        target_id=user.id,
        payload={"user_group": normalized_role},
    )
    session.commit()
    session.refresh(user)
    return to_user_read(user)


@router.post("/admin/users/bulk", response_model=BulkUserCreateResult)
async def bulk_create_users(
    payload: BulkUserCreateRequest,
    current_user: User = Depends(require_roles("admin")),
    session: Session = Depends(get_session),
):
    if not payload.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bulk user request must include at least one user",
        )

    default_password = payload.default_password.strip()
    if not default_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Default password must not be empty",
        )

    seen_ids: set[str] = set()
    seen_sids: set[int] = set()
    created_users: list[User] = []
    skipped_ids: list[str] = []

    for user_payload in payload.users:
        if user_payload.id in seen_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate user id in request: {user_payload.id}",
            )
        if user_payload.sid in seen_sids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate student ID in request: {user_payload.sid}",
            )
        seen_ids.add(user_payload.id)
        seen_sids.add(user_payload.sid)

        if (
            session.get(User, user_payload.id) is not None
            or get_user_by_sid(session, user_payload.sid) is not None
        ):
            if not payload.skip_existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User already exists: {user_payload.id}",
                )
            skipped_ids.append(user_payload.id)
            continue

        try:
            managed_user = create_managed_user(
                session,
                user_payload,
                default_password=default_password,
            )
        except UserManagementError as error:
            raise user_management_bad_request(error) from error
        session.add(managed_user)
        created_users.append(managed_user)

    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="bulk_create_users",
        target_type="user_batch",
        payload={
            "created_count": len(created_users),
            "skipped_ids": skipped_ids,
        },
    )
    session.commit()
    for user in created_users:
        session.refresh(user)

    return BulkUserCreateResult(
        created_count=len(created_users),
        skipped_count=len(skipped_ids),
        created_users=created_users,
        skipped_ids=skipped_ids,
    )


@router.patch("/admin/users/{user_id}/status", response_model=UserRead)
async def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    current_user: User = Depends(require_roles("admin")),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user.id == current_user.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    user.is_active = payload.is_active
    user.updated_at = datetime.now(UTC)
    session.add(user)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="update_user_status",
        target_type="user",
        target_id=user.id,
        payload=payload.model_dump(),
    )
    session.commit()
    session.refresh(user)
    return to_user_read(user)


@router.post("/admin/users/{user_id}/reset-password", response_model=UserRead)
async def reset_user_password(
    user_id: str,
    payload: AdminPasswordResetRequest,
    current_user: User = Depends(require_roles("admin")),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.ps = AuthService.get_password_hash(payload.new_password)
    user.updated_at = datetime.now(UTC)
    session.add(user)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="reset_user_password",
        target_type="user",
        target_id=user.id,
    )
    session.commit()
    session.refresh(user)
    return to_user_read(user)
