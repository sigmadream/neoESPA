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
