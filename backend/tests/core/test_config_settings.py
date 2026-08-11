import pytest
import os
from app.core.config import Settings

def test_settings_environment_normalization():
    # Dev / Development
    os.environ["APP_ENV"] = "dev"
    s1 = Settings()
    assert s1.ENVIRONMENT == "development"

    os.environ["APP_ENV"] = "DEVELOPMENT"
    s2 = Settings()
    assert s2.ENVIRONMENT == "development"

    # Test
    os.environ["APP_ENV"] = "test"
    s3 = Settings()
    assert s3.ENVIRONMENT == "test"

    # Production / Prod
    os.environ["APP_ENV"] = "prod"
    s4 = Settings()
    assert s4.ENVIRONMENT == "production"

    # Fallback to production for unknown
    os.environ["APP_ENV"] = "staging"
    s5 = Settings()
    assert s5.ENVIRONMENT == "production"

def test_cors_origins_parsing():
    os.environ["CORS_ORIGINS"] = "http://example.com , http://test.com "
    s = Settings()
    assert s.CORS_ORIGINS == ["http://example.com", "http://test.com"]

def test_validate_security_production_check():
    os.environ["APP_ENV"] = "production"
    if "JWT_SECRET" in os.environ:
        del os.environ["JWT_SECRET"]
    s = Settings()
    with pytest.raises(RuntimeError, match="CRITICAL SECURITY ERROR"):
        s.validate_security()


def test_auto_grading_defaults_fail_closed_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AUTO_GRADING_ENABLED", raising=False)

    configured = Settings()

    assert configured.AUTO_GRADING_ENABLED is False
    assert configured.HOST_CODE_EXECUTION_ALLOWED is False


def test_production_cannot_enable_legacy_host_runner(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTO_GRADING_ENABLED", "true")

    configured = Settings()

    assert configured.AUTO_GRADING_ENABLED is True
    assert configured.HOST_CODE_EXECUTION_ALLOWED is False


def test_invalid_auto_grading_boolean_is_rejected(monkeypatch):
    monkeypatch.setenv("AUTO_GRADING_ENABLED", "sometimes")

    with pytest.raises(RuntimeError, match="AUTO_GRADING_ENABLED must be a boolean"):
        _ = Settings().AUTO_GRADING_ENABLED


def test_sandbox_ready_requires_policy_bound_hostile_attestation(monkeypatch, tmp_path):
    import hashlib
    import json

    policy = tmp_path / "nsjail.cfg"
    policy.write_text("secure-policy", encoding="utf-8")
    attestation = tmp_path / "attestation.json"
    attestation.write_text(json.dumps({
        "passed": True,
        "fixtures": ["basic", "network", "root_write", "fork_bomb", "timeout", "output"],
        "results": {
            "basic": "passed", "network": "runtime_error",
            "root_write": "runtime_error", "fork_bomb": "runtime_error",
            "timeout": "timeout", "output": "output_limit",
        },
        "policy_sha256": hashlib.sha256(policy.read_bytes()).hexdigest(),
        "runtime_version": "runtime-v1",
    }), encoding="utf-8")
    monkeypatch.setenv("SANDBOX_READY", "true")
    monkeypatch.setenv("NSJAIL_CONFIG_PATH", str(policy))
    monkeypatch.setenv("SANDBOX_ATTESTATION_PATH", str(attestation))
    monkeypatch.setenv("JUDGE_RUNTIME_VERSION", "runtime-v1")
    assert Settings().SANDBOX_READY is True
    policy.write_text("changed-policy", encoding="utf-8")
    assert Settings().SANDBOX_READY is False
