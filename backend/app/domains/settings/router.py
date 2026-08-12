from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from ...api.dependencies import require_capability
from ...api.runtime import observability_service
from ...core.db import get_session
from ...core.system_settings import SYSTEM_SETTING_DEFINITIONS, normalize_setting_value
from ...models.schemas import (
    SystemSetting, SystemSettingHistory, SystemSettingRead, SystemSettingsUpdateRequest, User,
)
from ..settings.helpers import load_known_system_settings, to_system_setting_read


router = APIRouter()


@router.get("/admin/settings", response_model=list[SystemSettingRead])
async def list_admin_settings(
    prefix: str | None = Query(default=None),
    _: User = Depends(require_capability("settings:manage")),
    session: Session = Depends(get_session),
):
    settings = load_known_system_settings(session, prefix=prefix)
    return [to_system_setting_read(setting) for setting in settings]


@router.patch("/admin/settings", response_model=list[SystemSettingRead])
async def update_admin_settings(
    payload: SystemSettingsUpdateRequest,
    current_user: User = Depends(require_capability("settings:manage")),
    session: Session = Depends(get_session),
):
    if not payload.settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Settings update must include at least one item",
        )

    updated_settings: list[SystemSetting] = []
    before_values: dict[str, str | None] = {}
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
        before_values[item.key] = (
            setting.value if setting is not None else definition["default_value"]
        )
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
        session.add(SystemSettingHistory(
            setting_key=item.key, previous_value=before_values[item.key],
            new_value=normalized_value, changed_by=current_user.id,
        ))
        updated_settings.append(setting)

    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="update_system_settings",
        target_type="system_settings",
        target_id=",".join(sorted(before_values)),
        before=before_values,
        after={setting.key: setting.value for setting in updated_settings},
    )

    session.commit()
    for setting in updated_settings:
        session.refresh(setting)
    return [to_system_setting_read(setting) for setting in updated_settings]


@router.post("/admin/settings/{key}/rollback", response_model=SystemSettingRead)
async def rollback_admin_setting(
    key: str,
    current_user: User = Depends(require_capability("settings:manage")),
    session: Session = Depends(get_session),
):
    setting = session.get(SystemSetting, key)
    if setting is None:
        raise HTTPException(status_code=404, detail="Setting has no stored value")
    history = session.exec(
        select(SystemSettingHistory).where(
            SystemSettingHistory.setting_key == key,
            SystemSettingHistory.rolled_back_at.is_(None),
        ).order_by(SystemSettingHistory.id.desc())
    ).first()
    if history is None or history.previous_value is None:
        raise HTTPException(status_code=409, detail="Setting has no rollback value")
    current_value = setting.value
    setting.value = history.previous_value
    setting.updated_at = datetime.now(UTC)
    history.rolled_back_at = setting.updated_at
    session.add(setting)
    session.add(history)
    observability_service.record_audit(
        session, actor_user_id=current_user.id, action_type="rollback_system_setting",
        target_type="system_setting", target_id=key,
        before={"value": current_value}, after={"value": setting.value},
    )
    session.commit()
    session.refresh(setting)
    return to_system_setting_read(setting)
