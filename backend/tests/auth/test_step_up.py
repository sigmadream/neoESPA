from app.models.schemas import AdminAuthAssurance
from app.services.auth_service import AuthService


def test_password_step_up_issues_short_lived_assurance_token(
    client, session, create_user, login_user, auth_headers
):
    create_user("admin-step", 9001, "admin-password", role="admin")
    token = login_user("admin-step", "admin-password")
    response = client.post(
        "/api/auth/step-up",
        json={"password": "admin-password"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    claims = AuthService.decode_token(response.json()["access_token"])
    assert claims is not None
    assert claims["amr"] == ["pwd"]
    assert claims["step_up_until"] > claims["auth_time"]


def test_required_mfa_fails_closed_until_provider_verifies_factor(
    client, session, create_user, login_user, auth_headers
):
    create_user("admin-mfa", 9002, "admin-password", role="admin")
    session.add(
        AdminAuthAssurance(
            user_id="admin-mfa",
            mfa_required=True,
            mfa_enrolled=True,
            mfa_method="totp",
        )
    )
    session.commit()
    token = login_user("admin-mfa", "admin-password")
    response = client.post(
        "/api/auth/step-up",
        json={"password": "admin-password"},
        headers=auth_headers(token),
    )
    assert response.status_code == 403
    assert "provider" in response.json()["detail"]
