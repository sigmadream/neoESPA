from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from sqlmodel import Session

from ..core.db import get_session
from ..core.config import settings
from ..models.schemas import User
from ..services.auth_service import AuthService
from ..services.authorization_service import AuthorizationService
from ..services.user_management import STAFF_ROLES

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/auth/login", auto_error=False
)
optional_bearer_scheme = HTTPBearer(auto_error=False)
authorization_service = AuthorizationService()


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    resolved_token = token or request.cookies.get(settings.AUTH_COOKIE_NAME)
    payload = (
        AuthService.decode_token(resolved_token) if resolved_token else None
    )

    if payload is None:
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception
    if int(payload.get("ver", 0)) != user.token_version:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user cannot access this resource",
        )
    return current_user


def require_roles(*roles: str) -> Callable[[User], User]:
    async def dependency(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.user_group not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency


def require_capability(capability: str) -> Callable[[User], User]:
    async def dependency(
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session),
    ) -> User:
        if not authorization_service.has_capability(
            session, current_user, capability
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing capability: {capability}",
            )
        return current_user

    dependency.required_capability = capability  # type: ignore[attr-defined]
    return dependency


async def require_staff(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.user_group not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff privileges required",
        )
    return current_user


def require_step_up(capability: str) -> Callable[[User], User]:
    async def dependency(
        token: str | None = Depends(oauth2_scheme),
        current_user: User = Depends(require_capability(capability)),
        session: Session = Depends(get_session),
    ) -> User:
        from datetime import UTC, datetime

        payload = AuthService.decode_token(token)
        step_up_until = payload.get("step_up_until") if payload else None
        if (
            not isinstance(step_up_until, (int, float))
            or step_up_until < datetime.now(UTC).timestamp()
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Recent step-up authentication is required",
            )
        return current_user

    dependency.required_capability = capability  # type: ignore[attr-defined]
    return dependency


async def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        optional_bearer_scheme
    ),
    session: Session = Depends(get_session),
) -> User | None:
    resolved_token = (
        credentials.credentials
        if credentials is not None
        else request.cookies.get(settings.AUTH_COOKIE_NAME)
    )
    if resolved_token is None:
        return None

    payload = AuthService.decode_token(resolved_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if int(payload.get("ver", 0)) != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        return None
    return user
