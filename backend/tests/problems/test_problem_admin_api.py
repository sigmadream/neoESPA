from sqlmodel import select

from app.models.schemas import AssignmentProblem, AuditLog, ProblemRevision


def _create_problem(
    client, headers, *, code="sum-two", statement="Add two integers"
):
    return client.post(
        "/api/admin/problems",
        json={
            "code": code,
            "title": "Sum Two",
            "statement": statement,
            "time_limit_ms": 1000,
            "memory_limit_mb": 128,
            "allowed_languages": ["python", "cpp"],
        },
        headers=headers,
    )


def test_problem_draft_validate_publish_and_revision_history(
    client, session, create_user, login_user, auth_headers
):
    create_user("problem-admin", 20259001, "password", role="admin")
    headers = auth_headers(login_user("problem-admin"))

    created = _create_problem(client, headers)
    assert created.status_code == 201
    problem = created.json()
    revisions = client.get(
        f"/api/admin/problems/{problem['id']}/revisions", headers=headers
    ).json()
    assert revisions[0]["status"] == "draft"

    revision_id = revisions[0]["id"]
    validated = client.post(
        f"/api/admin/problems/{problem['id']}/revisions/{revision_id}/validate",
        headers=headers,
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == "ready"

    published = client.post(
        f"/api/admin/problems/{problem['id']}/revisions/{revision_id}/publish",
        headers=headers,
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    second = client.post(
        f"/api/admin/problems/{problem['id']}/revisions",
        json={"statement": "Updated immutable statement"},
        headers=headers,
    )
    assert second.status_code == 201
    assert second.json()["revision_no"] == 2
    assert published.json()["statement"] == "Add two integers"

    audit_actions = {
        log.action_type for log in session.exec(select(AuditLog)).all()
    }
    assert {
        "create_problem",
        "validate_problem_revision",
        "publish_problem_revision",
    }.issubset(audit_actions)


def test_invalid_revision_cannot_publish(
    client, create_user, login_user, auth_headers
):
    create_user("problem-admin-2", 20259002, "password", role="admin")
    headers = auth_headers(login_user("problem-admin-2"))
    problem = _create_problem(
        client, headers, code="empty", statement=""
    ).json()
    revision = client.get(
        f"/api/admin/problems/{problem['id']}/revisions", headers=headers
    ).json()[0]

    validation = client.post(
        f"/api/admin/problems/{problem['id']}/revisions/{revision['id']}/validate",
        headers=headers,
    )
    publish = client.post(
        f"/api/admin/problems/{problem['id']}/revisions/{revision['id']}/publish",
        headers=headers,
    )

    assert validation.status_code == 400
    assert publish.status_code == 409


def test_student_cannot_use_problem_admin_api(
    client, create_user, login_user, auth_headers
):
    create_user("problem-student", 20259003, "password", role="student")
    headers = auth_headers(login_user("problem-student"))

    response = _create_problem(client, headers, code="forbidden")

    assert response.status_code == 403


def test_published_revision_can_be_attached_to_homework(
    client, session, create_user, create_homework, login_user, auth_headers
):
    create_user("problem-admin-3", 20259004, "password", role="admin")
    create_homework(88, "Assignment")
    headers = auth_headers(login_user("problem-admin-3"))
    problem = _create_problem(client, headers, code="assigned").json()
    revision = client.get(
        f"/api/admin/problems/{problem['id']}/revisions", headers=headers
    ).json()[0]
    client.post(
        f"/api/admin/problems/{problem['id']}/revisions/{revision['id']}/validate",
        headers=headers,
    )
    client.post(
        f"/api/admin/problems/{problem['id']}/revisions/{revision['id']}/publish",
        headers=headers,
    )

    attached = client.post(
        "/api/admin/homeworks/88/problems",
        json={"revision_id": revision["id"], "position": 1},
        headers=headers,
    )

    assert attached.status_code == 201
    assignment = session.exec(select(AssignmentProblem)).one()
    assert assignment.revision_id == revision["id"]
    stored_revision = session.get(ProblemRevision, revision["id"])
    assert stored_revision.status == "published"
