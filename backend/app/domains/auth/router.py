from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session

from ...api.dependencies import get_current_active_user
from ...api.runtime import observability_service
from ...core.db import get_session
from ...core.config import settings
from ...models.schemas import (
    PasswordChangeRequest,
    AdminAuthAssurance,
    AdminAuthAssuranceRead,
    StepUpRequest,
    TokenResponse,
    User,
    UserCreate,
    UserLogin,
    UserRead,
)
from ...services.auth_service import AuthService
from ...services.login_rate_limiter import login_rate_limiter
from ...services.user_management import (
    UserManagementError,
    ensure_unique_sid,
    validate_email_policy,
)
from ..users.serializers import to_user_read, user_management_bad_request

router = APIRouter()

# Always perform one bcrypt verification, including for unknown account IDs, so
# login timing does not disclose whether an account exists.
_DUMMY_PASSWORD_HASH = (
    "$2b$12$JqK85n9lVznxg8X2VfNO8uSeTtdGRiK2sG7g6WGHgBmyYFZy8N2mq"
)


@router.post("/auth/register", response_model=UserRead)
async def register(
    user_in: UserCreate, session: Session = Depends(get_session)
):
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
async def login(
    login_data: UserLogin,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    client_host = request.client.host if request.client else "unknown"
    account_rate_limit_key = f"account:{login_data.id.strip().lower()}"
    client_rate_limit_key = f"client:{client_host}"
    rate_limit_keys = (account_rate_limit_key, client_rate_limit_key)
    if login_rate_limiter.is_blocked(
        rate_limit_keys,
        limit=settings.LOGIN_RATE_LIMIT_COUNT,
        window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
            headers={
                "Retry-After": str(settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS)
            },
        )

    user = session.get(User, login_data.id)
    password_matches = AuthService.verify_password(
        login_data.ps, user.ps if user else _DUMMY_PASSWORD_HASH
    )
    if not user or not password_matches:
        login_rate_limiter.record_failure(rate_limit_keys)
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

    login_rate_limiter.clear((account_rate_limit_key,))

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
        data={
            "sub": user.id,
            "role": user.user_group,
            "ver": user.token_version,
        }
    )
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        path="/",
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    response.delete_cookie(
        settings.AUTH_COOKIE_NAME,
        path="/",
        secure=settings.ENVIRONMENT == "production",
        httponly=True,
        samesite="strict",
    )


@router.get("/auth/assurance", response_model=AdminAuthAssuranceRead)
async def auth_assurance(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    assurance = session.get(AdminAuthAssurance, current_user.id)
    if assurance is None:
        return AdminAuthAssuranceRead(mfa_required=False, mfa_enrolled=False)
    return AdminAuthAssuranceRead.model_validate(assurance)


@router.post("/auth/step-up", response_model=TokenResponse)
async def step_up_authentication(
    payload: StepUpRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    if not AuthService.verify_password(payload.password, current_user.ps):
        raise HTTPException(
            status_code=401, detail="Password verification failed"
        )
    now = datetime.now(UTC)
    token = AuthService.create_access_token(
        {
            "sub": current_user.id,
            "role": current_user.user_group,
            "ver": current_user.token_version,
            "auth_time": int(now.timestamp()),
            "step_up_until": int((now + timedelta(minutes=10)).timestamp()),
            "amr": ["pwd"],
        },
        expires_delta=timedelta(minutes=10),
    )
    return TokenResponse(access_token=token)


@router.post("/auth/change-password")
async def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    if not AuthService.verify_password(
        payload.current_password, current_user.ps
    ):
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
    current_user.token_version += 1
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
