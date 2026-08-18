import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.core.db import get_session
from app.models.schemas import User

# 테스트용 인메모리 SQLite 설정
engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_user_registration_password_is_hashed(
    client: TestClient, session: Session
):
    # 1. 회원가입 요청
    user_data = {
        "id": "testuser",
        "sid": 20240001,
        "ps": "plain_password",
        "name": "Test User",
        "phone": "010-1234-5678",
        "email": "test@example.com",
    }
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 200

    # 2. DB에서 직접 조회하여 비밀번호 확인
    db_user = session.get(User, "testuser")
    assert db_user is not None
    assert db_user.ps != "plain_password"  # 평문으로 저장되면 안 됨
    assert len(db_user.ps) > 20  # 해시된 값이어야 함 (bcrypt)


def test_login_success(client: TestClient):
    # 회원가입
    user_data = {
        "id": "loginuser",
        "sid": 20240002,
        "ps": "correct_password",
        "name": "Login User",
        "phone": "010-0000-0000",
        "email": "login@example.com",
    }
    client.post("/api/auth/register", json=user_data)

    # 로그인 시도
    login_response = client.post(
        "/api/auth/login", json={"id": "loginuser", "ps": "correct_password"}
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


def test_login_failure(client: TestClient):
    # 회원가입
    user_data = {
        "id": "failuser",
        "sid": 20240003,
        "ps": "password-1",
        "name": "Fail User",
        "phone": "010-1111-1111",
        "email": "fail@example.com",
    }
    client.post("/api/auth/register", json=user_data)

    # 잘못된 비밀번호로 로그인
    login_response = client.post(
        "/api/auth/login", json={"id": "failuser", "ps": "wrong_password"}
    )
    assert login_response.status_code == 401


def test_protected_route_access(client: TestClient):
    # 1. 회원가입 및 로그인하여 토큰 획득
    user_data = {
        "id": "protecteduser",
        "sid": 20240004,
        "ps": "test-password",
        "name": "Protected User",
        "phone": "010-9999-9999",
        "email": "protected@example.com",
    }
    client.post("/api/auth/register", json=user_data)

    login_response = client.post(
        "/api/auth/login",
        json={"id": "protecteduser", "ps": "test-password"},
    )
    token = login_response.json()["access_token"]

    # 2. 유효한 토큰으로 접근 (성공)
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/api/users/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["id"] == "protecteduser"

    # 3. 토큰 없이 접근 (실패)
    client.cookies.clear()
    no_token_response = client.get("/api/users/me")
    assert no_token_response.status_code == 401

    # 4. 잘못된 토큰으로 접근 (실패)
    wrong_token_headers = {"Authorization": "Bearer invalid_token_here"}
    invalid_token_response = client.get(
        "/api/users/me", headers=wrong_token_headers
    )
    assert invalid_token_response.status_code == 401


def test_public_judge_health_omits_internal_details(client: TestClient):
    response = client.get("/health/judge")

    assert response.status_code in {200, 503}
    assert set(response.json()) == {"status"}


def test_detailed_judge_health_requires_authentication(client: TestClient):
    response = client.get("/api/admin/health/judge")

    assert response.status_code == 401
