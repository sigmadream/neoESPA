import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project root directory (the parent directory of 'backend/')
_BASE_DIR = Path(__file__).resolve().parents[3]
_default_db_path = _BASE_DIR / "database" / "database.sqlite"

class Settings:
    PROJECT_NAME: str = "neoESPA Modernized API"
    PROJECT_VERSION: str = "1.0.0"
    
    BASE_DIR: Path = _BASE_DIR
    ALLOWED_ENVIRONMENTS = {"development", "dev", "test", "production", "prod"}
    
    def __init__(self):
        self.SNAPSHOT_RATE_LIMIT_COUNT = int(os.getenv("SNAPSHOT_RATE_LIMIT_COUNT", "20"))
        self.SNAPSHOT_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("SNAPSHOT_RATE_LIMIT_WINDOW_SECONDS", "60"))

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
    def CORS_ORIGINS(self) -> list[str]:
        raw_cors = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:3101,http://127.0.0.1:3101",
        )
        return [origin.strip() for origin in raw_cors.split(",") if origin.strip()]

    @property
    def SECRET_KEY(self) -> str:
        return os.getenv("JWT_SECRET") or "super-secret-key-must-be-changed-in-production-32-chars"

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
