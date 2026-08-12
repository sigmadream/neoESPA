import pytest
from app.api.dependencies import (
    get_current_active_user,
    require_roles,
)
from app.models.schemas import User
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_require_roles_unauthorized():
    user = User(
        id="student-role",
        sid=20249999,
        ps="hash",
        name="student",
        phone="010",
        email="s@e.com",
        user_group="student",
    )
    checker = require_roles("admin", "instructor")
    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_active_user_inactive():
    inactive_user = User(
        id="inactive-user",
        sid=20249998,
        ps="hash",
        name="inactive",
        phone="010",
        email="i@e.com",
        user_group="student",
        is_active=False,
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(current_user=inactive_user)
    assert exc_info.value.status_code == 403
    assert "Inactive user" in exc_info.value.detail
