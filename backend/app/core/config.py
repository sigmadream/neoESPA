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
    ENVIRONMENT: str = os.getenv("APP_ENV", "dev").lower()
    SQLITE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{_default_db_path}")
    SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() == "true"
    
    # Security: Require a 32-byte-or-longer secret for non-dev environments
    _RAW_SECRET_KEY = os.getenv("JWT_SECRET")
    SECRET_KEY: str = _RAW_SECRET_KEY or "super-secret-key-must-be-changed-in-production-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    SNAPSHOT_RATE_LIMIT_COUNT: int = int(os.getenv("SNAPSHOT_RATE_LIMIT_COUNT", "20"))
    SNAPSHOT_RATE_LIMIT_WINDOW_SECONDS: int = int(
        os.getenv("SNAPSHOT_RATE_LIMIT_WINDOW_SECONDS", "60")
    )

    def validate_security(self):
        is_dev_or_test = self.ENVIRONMENT in ("dev", "test")
        secret_len = len(self.SECRET_KEY)
        
        if not self._RAW_SECRET_KEY and not is_dev_or_test:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: JWT_SECRET environment variable is not set in production!"
            )
            
        if secret_len < 32:
            msg = f"JWT_SECRET is too short ({secret_len} chars). Minimum recommended is 32."
            if not is_dev_or_test:
                raise RuntimeError(f"CRITICAL SECURITY ERROR: {msg}")
            logging.warning(f"SECURITY WARNING: {msg}")

settings = Settings()
