from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from ...api.dependencies import require_roles
from ...core.db import get_session
from ...core.system_settings import SYSTEM_SETTING_DEFINITIONS, normalize_setting_value
from ...models.schemas import SystemSetting, SystemSettingRead, SystemSettingsUpdateRequest, User
from ..settings.helpers import load_known_system_settings, to_system_setting_read


router = APIRouter()


@router.get("/admin/settings", response_model=list[SystemSettingRead])
async def list_admin_settings(
    prefix: str | None = Query(default=None),
    _: User = Depends(require_roles("admin")),
    session: Session = Depends(get_session),
):
    settings = load_known_system_settings(session, prefix=prefix)
    return [to_system_setting_read(setting) for setting in settings]


@router.patch("/admin/settings", response_model=list[SystemSettingRead])
async def update_admin_settings(
    payload: SystemSettingsUpdateRequest,
    _: User = Depends(require_roles("admin")),
    session: Session = Depends(get_session),
):
    if not payload.settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Settings update must include at least one item",
        )

    updated_settings: list[SystemSetting] = []
    for item in payload.settings:
        if item.key not in SYSTEM_SETTING_DEFINITIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported setting key: {item.key}",
            )

        try:
            normalized_value, value_type = normalize_setting_value(item.key, item.value)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid setting value for {item.key}: {error}",
            ) from error

        definition = SYSTEM_SETTING_DEFINITIONS[item.key]
        setting = session.get(SystemSetting, item.key)
        if setting is None:
            setting = SystemSetting(
                key=item.key,
                value=normalized_value,
                value_type=value_type,
                description=definition["description"],
                updated_at=datetime.now(UTC),
            )
        else:
            setting.value = normalized_value
            setting.value_type = value_type
            setting.description = definition["description"]
            setting.updated_at = datetime.now(UTC)
        session.add(setting)
        updated_settings.append(setting)

    session.commit()
    for setting in updated_settings:
        session.refresh(setting)
    return [to_system_setting_read(setting) for setting in updated_settings]
