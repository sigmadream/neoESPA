import os
import subprocess
import sys
from pathlib import Path

from sqlmodel import Session, create_engine

from app.models.schemas import User


BACKEND_DIR = Path(__file__).resolve().parents[2]


def _run_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    db_path = tmp_path / "cli.sqlite"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"

    return subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_create_admin_cli_creates_user(tmp_path: Path):
    response = _run_cli(
        tmp_path,
        "create-admin",
        "--id",
        "ops-admin",
        "--sid",
        "10050001",
        "--name",
        "Operations Admin",
        "--phone",
        "010-5555-0001",
        "--email",
        "ops-admin@example.com",
        "--password",
        "change-me-now",
    )

    assert response.returncode == 0
    assert "Created admin user 'ops-admin'" in response.stdout

    engine = create_engine(f"sqlite:///{tmp_path / 'cli.sqlite'}")
    with Session(engine) as session:
        user = session.get(User, "ops-admin")

    assert user is not None
    assert user.user_group == "admin"
    assert user.is_active is True
    assert user.sid == 10050001


def test_create_admin_cli_rejects_duplicate_user(tmp_path: Path):
    first_response = _run_cli(
        tmp_path,
        "create-admin",
        "--id",
        "duplicate-admin",
        "--sid",
        "10050002",
        "--name",
        "Duplicate Admin",
        "--phone",
        "010-5555-0002",
        "--email",
        "duplicate-admin@example.com",
        "--password",
        "change-me-now",
    )
    second_response = _run_cli(
        tmp_path,
        "create-admin",
        "--id",
        "duplicate-admin",
        "--sid",
        "10050002",
        "--name",
        "Duplicate Admin",
        "--phone",
        "010-5555-0002",
        "--email",
        "duplicate-admin@example.com",
        "--password",
        "change-me-now",
    )

    assert first_response.returncode == 0
    assert second_response.returncode == 1
    assert "Error: User already exists: duplicate-admin" in second_response.stderr
