from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import configure_sqlite_foreign_keys, get_session
from app.main import app
from tests.factories import (
    create_homework as build_homework,
    create_submission as build_submission,
    create_submission_result as build_submission_result,
    create_user as build_user,
)


@pytest.fixture(name="engine")
def engine_fixture():
    engine = configure_sqlite_foreign_keys(
        create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session
        session.close()


@pytest.fixture(name="client")
def client_fixture(session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def create_user(session):
    def _create(
        user_id: str,
        sid: int,
        password: str = "password",
        role: str = "student",
        is_active: bool = True,
    ):
        return build_user(session, user_id, sid, password, role, is_active)

    return _create


@pytest.fixture
def create_homework(session):
    def _create(
        num: int,
        title: str,
        start_offset_days: int = -1,
        deadline_offset_days: int = 2,
    ):
        return build_homework(
            session,
            num,
            title,
            start_offset_days=start_offset_days,
            deadline_offset_days=deadline_offset_days,
        )

    return _create


@pytest.fixture
def create_submission(session):
    def _create(**kwargs):
        return build_submission(session, **kwargs)

    return _create


@pytest.fixture
def create_submission_result(session):
    def _create(submission_id: int, **kwargs):
        return build_submission_result(session, submission_id, **kwargs)

    return _create


@pytest.fixture
def login_user(client):
    def _login(user_id: str, password: str = "password"):
        response = client.post("/api/auth/login", json={"id": user_id, "ps": password})
        if response.status_code == 200:
            return response.json()["access_token"]
        return None

    return _login


@pytest.fixture
def dt_string():
    def _dt(offset_days: int, offset_hours: int = 0) -> str:
        return (
            datetime.now(UTC) + timedelta(days=offset_days, hours=offset_hours)
        ).strftime("%Y-%m-%d %H:%M:%S")

    return _dt


@pytest.fixture
def auth_headers():
    def _headers(token: str):
        return {"Authorization": f"Bearer {token}"}

    return _headers
