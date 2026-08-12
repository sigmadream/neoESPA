import pytest

from app.models.schemas import User
from app.services.admin_invitation_service import (
    AdminInvitationError,
    accept_admin_invitation,
    issue_admin_invitation,
)


def _admin() -> User:
    return User(
        id="root",
        sid=1,
        ps="hash",
        name="Root",
        phone="",
        email="root@test",
        user_group="super_admin",
    )


def test_admin_invitation_is_single_use_and_pins_email_and_role(session):
    session.add(_admin())
    session.commit()
    invitation, token = issue_admin_invitation(
        session,
        email="New.Admin@Test.EXAMPLE",
        role_name="reviewer",
        created_by="root",
        ttl_minutes=15,
    )
    session.commit()
    user = accept_admin_invitation(
        session,
        token=token,
        user_id="reviewer",
        sid=2,
        name="Reviewer",
        phone="010",
        password="strong-password",
    )
    assert invitation.id is not None
    assert user.email == "new.admin@test.example"
    assert user.user_group == "reviewer"
    with pytest.raises(AdminInvitationError, match="invalid"):
        accept_admin_invitation(
            session,
            token=token,
            user_id="other",
            sid=3,
            name="Other",
            phone="",
            password="strong-password",
        )


def test_admin_invitation_rejects_super_admin_role(session):
    session.add(_admin())
    session.commit()
    with pytest.raises(AdminInvitationError, match="cannot be assigned"):
        issue_admin_invitation(
            session,
            email="other@test",
            role_name="super_admin",
            created_by="root",
            ttl_minutes=15,
        )
