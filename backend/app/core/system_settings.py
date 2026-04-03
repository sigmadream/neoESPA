from __future__ import annotations

from typing import Any


SYSTEM_SETTING_DEFINITIONS: dict[str, dict[str, str]] = {
    "lint_calc_weight": {
        "value_type": "number",
        "default_value": "50",
        "description": "Maximum quality score contribution from lint feedback.",
    },
    "lint_calc_panalty": {
        "value_type": "number",
        "default_value": "0.5",
        "description": "Penalty unit applied to each active lint issue.",
    },
    "lint_err_issue": {
        "value_type": "number",
        "default_value": "1",
        "description": "Severity weight for issue-level lint findings.",
    },
    "lint_err_style": {
        "value_type": "number",
        "default_value": "1",
        "description": "Severity weight for style-level lint findings.",
    },
    "lint_err_performance": {
        "value_type": "number",
        "default_value": "1",
        "description": "Severity weight for performance-level lint findings.",
    },
    "lint_err_information": {
        "value_type": "number",
        "default_value": "1",
        "description": "Severity weight for informational lint findings.",
    },
    "lint_set_default": {
        "value_type": "boolean",
        "default_value": "false",
        "description": "If enabled, all default lint rules stay active regardless of week-specific rule mapping.",
    },
}

LINT_SETTING_KEYS = tuple(SYSTEM_SETTING_DEFINITIONS.keys())

DEFAULT_LINT_SETTINGS = {
    key: float(definition["default_value"])
    for key, definition in SYSTEM_SETTING_DEFINITIONS.items()
    if definition["value_type"] == "number"
}


def parse_boolean_setting(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise ValueError("Boolean setting must be true/false")


def normalize_setting_value(key: str, raw_value: Any) -> tuple[str, str]:
    definition = SYSTEM_SETTING_DEFINITIONS.get(key)
    if definition is None:
        raise KeyError(key)

    value_type = definition["value_type"]
    if value_type == "number":
        numeric_value = float(raw_value)
        if numeric_value < 0:
            raise ValueError("Numeric setting must be non-negative")
        if numeric_value.is_integer():
            return str(int(numeric_value)), value_type
        return str(numeric_value), value_type

    if value_type == "boolean":
        return ("true" if parse_boolean_setting(raw_value) else "false"), value_type

    string_value = str(raw_value).strip()
    if not string_value:
        raise ValueError("String setting must not be empty")
    return string_value, value_type
