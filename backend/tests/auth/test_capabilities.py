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
    other_detail = client.get(
        f"/api/admin/problems/{problem_id}", headers=headers_b
    )

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
        json={
            "code": "no-publish",
            "title": "No Publish",
            "statement": "Statement",
        },
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


def test_role_capabilities_can_be_replaced_with_overlapping_set(
    client, create_user, login_user, auth_headers
):
    """유지되는 권한이 있어도 저장이 실패하지 않아야 한다.

    삭제와 재삽입이 같은 flush 에 묶이면 (role_name, capability) UNIQUE 제약을
    위반해 500 이 발생했다.
    """
    create_user("role-admin", 10259401, "password", role="admin")
    headers = auth_headers(login_user("role-admin"))

    first = client.put(
        "/api/admin/roles/ta/capabilities",
        json={"capabilities": ["homework:manage", "grading:manual"]},
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["capabilities"] == ["grading:manual", "homework:manage"]

    # 기존 권한 하나를 그대로 두고 하나를 추가한다.
    second = client.put(
        "/api/admin/roles/ta/capabilities",
        json={"capabilities": ["homework:manage", "observability:read"]},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["capabilities"] == [
        "homework:manage",
        "observability:read",
    ]

    stored = client.get("/api/admin/roles/ta/capabilities", headers=headers)
    assert stored.json()["capabilities"] == [
        "homework:manage",
        "observability:read",
    ]
