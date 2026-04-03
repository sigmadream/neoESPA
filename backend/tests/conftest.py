import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import configure_sqlite_foreign_keys, get_session
from app.main import app
from app.models.schemas import User
from app.services.auth_service import AuthService

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

@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session

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
    ) -> User:
        user = User(
            id=user_id,
            sid=sid,
            ps=AuthService.get_password_hash(password),
            name=user_id,
            phone="010-0000-0000",
            email=f"{user_id}@example.com",
            user_group=role,
            is_active=is_active,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    return _create

@pytest.fixture
def login_user(client):
    def _login(user_id: str, password: str = "password"):
        response = client.post("/api/auth/login", json={"id": user_id, "ps": password})
        if response.status_code == 200:
            return response.json()["access_token"]
        return None
    return _login

from datetime import UTC, datetime, timedelta

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
