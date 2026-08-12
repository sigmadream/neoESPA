from datetime import UTC, datetime

from ...core.system_settings import SYSTEM_SETTING_DEFINITIONS
from ...models.schemas import SystemSetting, SystemSettingRead


def to_system_setting_read(setting: SystemSetting) -> SystemSettingRead:
    return SystemSettingRead(
        key=setting.key,
        value=setting.value,
        value_type=setting.value_type,
        description=setting.description,
        updated_at=setting.updated_at,
    )


def load_known_system_settings(
    session,
    *,
    prefix: str | None = None,
) -> list[SystemSetting]:
    settings: list[SystemSetting] = []
    for key, definition in SYSTEM_SETTING_DEFINITIONS.items():
        if prefix and not key.startswith(prefix):
            continue

        setting = session.get(SystemSetting, key)
        if setting is None:
            setting = SystemSetting(
                key=key,
                value=definition["default_value"],
                value_type=definition["value_type"],
                description=definition["description"],
                updated_at=datetime.now(UTC),
            )
        elif setting.description is None:
            setting.description = definition["description"]
        settings.append(setting)

    return settings


def get_system_setting_value(session, key: str) -> str:
    definition = SYSTEM_SETTING_DEFINITIONS[key]
    setting = session.get(SystemSetting, key)
    return setting.value if setting is not None else definition["default_value"]
