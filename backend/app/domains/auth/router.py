from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from ...api.dependencies import get_current_active_user
from ...api.runtime import observability_service
from ...core.db import get_session
from ...models.schemas import (
    PasswordChangeRequest,
    TokenResponse,
    User,
    UserCreate,
    UserLogin,
    UserRead,
)
from ...services.auth_service import AuthService
from ...services.user_management import (
    UserManagementError,
    ensure_unique_sid,
    validate_email_policy,
)
from ..users.serializers import to_user_read, user_management_bad_request


router = APIRouter()


@router.post("/auth/register", response_model=UserRead)
async def register(user_in: UserCreate, session: Session = Depends(get_session)):
    existing_user = session.get(User, user_in.id)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    try:
        ensure_unique_sid(session, user_in.sid)
        validate_email_policy(user_in.email)
    except UserManagementError as error:
        raise user_management_bad_request(error) from error

    hashed_password = AuthService.get_password_hash(user_in.ps)

    now = datetime.now(UTC)
    db_user = User(
        id=user_in.id,
        sid=user_in.sid,
        ps=hashed_password,
        name=user_in.name,
        phone=user_in.phone,
        email=user_in.email,
        user_group="student",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    session.add(db_user)
    session.flush()
    observability_service.log_event(
        session,
        category="auth",
        level="info",
        event_type="register_success",
        message=f"User registered: {db_user.id}",
        user_id=db_user.id,
        request_path="/auth/register",
    )
    session.commit()
    session.refresh(db_user)
    return to_user_read(db_user)


@router.post("/auth/login", response_model=TokenResponse)
async def login(login_data: UserLogin, session: Session = Depends(get_session)):
    user = session.get(User, login_data.id)
    if not user or not AuthService.verify_password(login_data.ps, user.ps):
        observability_service.log_event(
            session,
            category="auth",
            level="warning",
            event_type="login_failed",
            message="Incorrect ID or password",
            user_id=user.id if user else None,
            request_path="/auth/login",
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect ID or password",
        )

    if not user.is_active:
        observability_service.log_event(
            session,
            category="auth",
            level="warning",
            event_type="login_blocked_inactive",
            message="Inactive user attempted login",
            user_id=user.id,
            request_path="/auth/login",
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user cannot log in",
        )

    observability_service.log_event(
        session,
        category="auth",
        level="info",
        event_type="login_success",
        message="Login succeeded",
        user_id=user.id,
        request_path="/auth/login",
    )
    session.commit()
    access_token = AuthService.create_access_token(
        data={"sub": user.id, "role": user.user_group}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/change-password")
async def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    if not AuthService.verify_password(payload.current_password, current_user.ps):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    current_user.ps = AuthService.get_password_hash(payload.new_password)
    current_user.updated_at = datetime.now(UTC)
    session.add(current_user)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="change_password",
        target_type="user",
        target_id=current_user.id,
    )
    session.commit()
    return {"message": "Password updated successfully"}
