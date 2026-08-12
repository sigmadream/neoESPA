from sqlmodel import select

from app.models.schemas import Problem


def test_problem_setter_can_only_see_owned_problem(
    client, session, create_user, login_user, auth_headers
):
    create_user("setter-a", 20259301, "password", role="problem_setter")
    create_user("setter-b", 20259302, "password", role="problem_setter")
    headers_a = auth_headers(login_user("setter-a"))
    headers_b = auth_headers(login_user("setter-b"))

    created = client.post(
        "/api/admin/problems",
        json={"code": "owned", "title": "Owned", "statement": "Statement"},
        headers=headers_a,
    )
    assert created.status_code == 201
    problem_id = created.json()["id"]

    own_list = client.get("/api/admin/problems", headers=headers_a)
    other_list = client.get("/api/admin/problems", headers=headers_b)
    other_detail = client.get(f"/api/admin/problems/{problem_id}", headers=headers_b)

    assert [problem["id"] for problem in own_list.json()] == [problem_id]
    assert other_list.json() == []
    assert other_detail.status_code == 403
    assert session.exec(select(Problem)).one().owner_id == "setter-a"


def test_problem_setter_cannot_validate_or_publish(
    client, create_user, login_user, auth_headers
):
    create_user("setter-c", 20259303, "password", role="problem_setter")
    headers = auth_headers(login_user("setter-c"))
    problem = client.post(
        "/api/admin/problems",
        json={"code": "no-publish", "title": "No Publish", "statement": "Statement"},
        headers=headers,
    ).json()
    revision = client.get(
        f"/api/admin/problems/{problem['id']}/revisions", headers=headers
    ).json()[0]

    validate = client.post(
        f"/api/admin/problems/{problem['id']}/revisions/{revision['id']}/validate",
        headers=headers,
    )
    publish = client.post(
        f"/api/admin/problems/{problem['id']}/revisions/{revision['id']}/publish",
        headers=headers,
    )

    assert validate.status_code == 403
    assert publish.status_code == 403
