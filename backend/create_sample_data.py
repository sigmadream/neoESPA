import os
from pathlib import Path
import logging

# Ensure the script connects to the local SQLite database instead of the docker path defined in .env
db_path = Path(__file__).resolve().parent.parent / "database" / "database.sqlite"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

from app.core.db import engine
from app.core.seed import seed_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sample_data():
    seed_database(engine)
    logger.info("Seeded admin, sample student, homework, notice, and default settings.")

if __name__ == "__main__":
    create_sample_data()
