from sqlmodel import select

from app.models.schemas import User
from app.services.bootstrap_service import issue_bootstrap_token


def test_first_admin_bootstrap_is_one_time(client, session):
    token = issue_bootstrap_token(session, ttl_minutes=5)
    payload = {
        "token": token,
        "id": "first-admin",
        "sid": 20259701,
        "name": "First Admin",
        "phone": "010-0000-0000",
        "email": "first@example.com",
        "password": "secure-password-123",
    }

    created = client.post("/api/admin-auth/bootstrap", json=payload)
    repeated = client.post("/api/admin-auth/bootstrap", json=payload)

    assert created.status_code == 201
    assert created.json()["user_group"] == "super_admin"
    assert repeated.status_code == 403
    assert session.exec(select(User)).one().id == "first-admin"
