from sqlmodel import select

from app.api.runtime import observability_service
from app.models.schemas import AuditLog


def test_audit_context_and_filters(
    client, session, create_user, login_user, auth_headers
):
    create_user("audit-admin", 20259601, "password", role="admin")
    observability_service.record_audit(
        session,
        actor_user_id="audit-admin",
        action_type="publish_problem_revision",
        target_type="problem_revision",
        target_id="12",
        result="success",
        request_id="request-12",
        before={"status": "ready"},
        after={"status": "published"},
    )
    observability_service.record_audit(
        session,
        actor_user_id="audit-admin",
        action_type="other",
        target_type="problem",
        result="failed",
    )
    session.commit()
    headers = auth_headers(login_user("audit-admin"))

    response = client.get(
        "/api/admin/audit-logs",
        params={
            "action_type": "publish_problem_revision",
            "request_id": "request-12",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["before_json"] == '{"status": "ready"}'
    assert response.json()[0]["after_json"] == '{"status": "published"}'
    assert len(session.exec(select(AuditLog)).all()) == 2


def test_request_id_is_automatically_attached_to_audit(
    client, session, create_user, login_user, auth_headers
):
    create_user("audit-user", 20259602, "old-password")
    headers = auth_headers(login_user("audit-user", "old-password"))
    headers["X-Request-ID"] = "audit-correlation-1"
    response = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "old-password",
            "new_password": "new-password",
        },
        headers=headers,
    )
    audit = session.exec(
        select(AuditLog).where(AuditLog.action_type == "change_password")
    ).one()
    assert response.status_code == 200
    assert audit.request_id == "audit-correlation-1"
