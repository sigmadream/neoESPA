import pytest
from app.services.auth_service import AuthService

def test_password_hashing():
    """
    완료 조건 테스트: 
    1. 평문 비밀번호와 해시값이 달라야 함.
    2. AuthService.verify_password를 통해서만 검증이 가능해야 함.
    """
    password = "secure_password123"
    hashed_password = AuthService.get_password_hash(password)
    
    # 1. 평문 저장 여부 확인 (다름을 확인)
    assert password != hashed_password
    
    # 2. 올바른 비밀번호 검증
    assert AuthService.verify_password(password, hashed_password) is True
    
    # 3. 잘못된 비밀번호 검증
    assert AuthService.verify_password("wrong_password", hashed_password) is False

def test_auth_service_token_creation():
    data = {"sub": "user123", "role": "admin"}
    token = AuthService.create_access_token(data)
    assert isinstance(token, str)
    assert len(token) > 0
