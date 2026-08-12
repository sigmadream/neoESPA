import pytest

from app.core.system_settings import (
    DEFAULT_LINT_SETTINGS,
    LINT_SETTING_KEYS,
    SYSTEM_SETTING_DEFINITIONS,
    normalize_setting_value,
    parse_boolean_setting,
)
from app.services.auth_service import AuthService


def test_password_hashing():
    """
    완료 조건 테스트: 
    1. 평문 비밀번호와 해시값이 달라야 함.
    2. AuthService.verify_password를 통해서만 검증이 가능해야 함.
    """
    password = "secure_password123"
    hashed_password = AuthService.get_password_hash(password)
    
    # 1. 평문 저장 여부 확인 (다름을 확인)
    assert password != hashed_password
    
    # 2. 올바른 비밀번호 검증
    assert AuthService.verify_password(password, hashed_password) is True
    
    # 3. 잘못된 비밀번호 검증
    assert AuthService.verify_password("wrong_password", hashed_password) is False

def test_auth_service_token_creation():
    data = {"sub": "user123", "role": "admin"}
    token = AuthService.create_access_token(data)
    assert isinstance(token, str)
    assert len(token) > 0

def test_system_setting_parsing_and_normalization(monkeypatch):
    assert parse_boolean_setting(True) is True
    assert parse_boolean_setting("yes") is True
    assert parse_boolean_setting("off") is False

    with pytest.raises(ValueError, match="Boolean setting must be true/false"):
        parse_boolean_setting("maybe")

    assert normalize_setting_value("lint_calc_weight", 5.0) == ("5", "number")
    assert normalize_setting_value("lint_calc_panalty", 0.75) == ("0.75", "number")
    assert normalize_setting_value("lint_set_default", "on") == ("true", "boolean")

    monkeypatch.setitem(
        SYSTEM_SETTING_DEFINITIONS,
        "custom_string_setting",
        {
            "value_type": "string",
            "default_value": "demo",
            "description": "Custom string setting for tests.",
        },
    )
    assert normalize_setting_value("custom_string_setting", "  value  ") == (
        "value",
        "string",
    )

    with pytest.raises(ValueError, match="String setting must not be empty"):
        normalize_setting_value("custom_string_setting", "   ")

    with pytest.raises(KeyError):
        normalize_setting_value("missing_setting", 1)

    assert "lint_set_default" in LINT_SETTING_KEYS
    assert DEFAULT_LINT_SETTINGS["lint_calc_weight"] == 50.0
