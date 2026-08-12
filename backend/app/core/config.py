import os
import logging
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project root directory (the parent directory of 'backend/')
_BASE_DIR = Path(__file__).resolve().parents[3]
_default_db_path = _BASE_DIR / "database" / "database.sqlite"


class Settings:
    PROJECT_NAME: str = "neoESPA API"
    PROJECT_VERSION: str = "3.0.0"

    BASE_DIR: Path = _BASE_DIR
    ALLOWED_ENVIRONMENTS = {"development", "dev", "test", "production", "prod"}

    def __init__(self):
        self.SNAPSHOT_RATE_LIMIT_COUNT = int(
            os.getenv("SNAPSHOT_RATE_LIMIT_COUNT", "20")
        )
        self.SNAPSHOT_RATE_LIMIT_WINDOW_SECONDS = int(
            os.getenv("SNAPSHOT_RATE_LIMIT_WINDOW_SECONDS", "60")
        )

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        normalized = raw.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise RuntimeError(f"{name} must be a boolean value")

    @property
    def ENVIRONMENT(self) -> str:
        raw = os.getenv("APP_ENV", "development").lower()
        if raw in ("development", "dev"):
            return "development"
        if raw == "test":
            return "test"
        return "production"

    @property
    def SQLITE_URL(self) -> str:
        return os.getenv("DATABASE_URL", f"sqlite:///{_default_db_path}")

    @property
    def SQL_ECHO(self) -> bool:
        return os.getenv("SQL_ECHO", "false").lower() == "true"

    @property
    def AUTO_GRADING_ENABLED(self) -> bool:
        """Whether automatic grading is requested for this environment.

        Development and tests keep the legacy behavior by default. Production
        is fail-closed until the isolated runner introduced by the judge phase
        is available.
        """
        return self._env_bool(
            "AUTO_GRADING_ENABLED",
            default=self.ENVIRONMENT in {"development", "test"},
        )

    @property
    def HOST_CODE_EXECUTION_ALLOWED(self) -> bool:
        """Host subprocess execution is never permitted in production."""
        return (
            self.ENVIRONMENT in {"development", "test"}
            and self.AUTO_GRADING_ENABLED
        )

    @property
    def SANDBOX_READY(self) -> bool:
        if not self._env_bool("SANDBOX_READY", default=False):
            return False
        attestation_path = os.getenv("SANDBOX_ATTESTATION_PATH")
        policy_path = os.getenv("NSJAIL_CONFIG_PATH")
        if not attestation_path or not policy_path:
            return False
        try:
            attestation = json.loads(
                Path(attestation_path).read_text(encoding="utf-8")
            )
            policy_hash = hashlib.sha256(
                Path(policy_path).read_bytes()
            ).hexdigest()
        except OSError, ValueError:
            return False
        return (
            attestation.get("passed") is True
            and attestation.get("policy_sha256") == policy_hash
            and attestation.get("runtime_version") == self.JUDGE_RUNTIME_VERSION
            and set(attestation.get("fixtures", []))
            >= {
                "basic",
                "network",
                "root_write",
                "fork_bomb",
                "timeout",
                "output",
            }
            and attestation.get("results")
            == {
                "basic": "passed",
                "network": "runtime_error",
                "root_write": "runtime_error",
                "fork_bomb": "runtime_error",
                "timeout": "timeout",
                "output": "output_limit",
            }
        )

    @property
    def AUTOMATIC_GRADING_AVAILABLE(self) -> bool:
        return self.AUTO_GRADING_ENABLED and (
            self.HOST_CODE_EXECUTION_ALLOWED or self.SANDBOX_READY
        )

    @property
    def CORS_ORIGINS(self) -> list[str]:
        raw_cors = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:3101,http://127.0.0.1:3101",
        )
        return [
            origin.strip() for origin in raw_cors.split(",") if origin.strip()
        ]

    @property
    def COURSE_BUNDLE_ROOT(self) -> Path:
        configured = os.getenv("COURSE_BUNDLE_ROOT")
        if configured:
            root = Path(configured).expanduser()
            if not root.is_absolute():
                raise RuntimeError(
                    "COURSE_BUNDLE_ROOT must be an absolute path"
                )
            return root.resolve()
        if self.ENVIRONMENT == "production":
            raise RuntimeError("COURSE_BUNDLE_ROOT is required in production")
        return (_BASE_DIR / "database" / "course_bundle").resolve()

    @property
    def COURSE_ID(self) -> str:
        return os.getenv("COURSE_ID", "development-course")

    @property
    def COURSE_TERM(self) -> str:
        return os.getenv("COURSE_TERM", "development-term")

    @property
    def SECRET_KEY(self) -> str:
        return (
            os.getenv("JWT_SECRET")
            or "super-secret-key-must-be-changed-in-production-32-chars"
        )

    @property
    def ANALYTICS_HMAC_SECRET(self) -> str | None:
        return os.getenv("ANALYTICS_HMAC_SECRET")

    @property
    def JUDGE_RUNTIME_VERSION(self) -> str:
        return os.getenv("JUDGE_RUNTIME_VERSION", "development-host-v1")

    @property
    def INTERACTIVE_JUDGING_ENABLED(self) -> bool:
        return self._env_bool("INTERACTIVE_JUDGING_ENABLED", default=False)

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    def validate_security(self):
        is_dev_or_test = self.ENVIRONMENT in ("development", "test")
        raw_secret = os.getenv("JWT_SECRET")
        secret_len = len(self.SECRET_KEY)

        if not raw_secret and not is_dev_or_test:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: JWT_SECRET environment variable is not set in production!"
            )

        if secret_len < 32:
            msg = f"JWT_SECRET is too short ({secret_len} chars). Minimum recommended is 32."
            if not is_dev_or_test:
                raise RuntimeError(f"CRITICAL SECURITY ERROR: {msg}")
            logging.warning(f"SECURITY WARNING: {msg}")


settings = Settings()
