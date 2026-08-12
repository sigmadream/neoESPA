def test_problem_validation_job_api(
    client,
    create_user,
    login_user,
    auth_headers,
):
    create_user("job-admin", 20259202, "password", role="admin")
    headers = auth_headers(login_user("job-admin"))
    problem = client.post(
        "/api/admin/problems",
        json={"code": "job-api", "title": "Job API", "statement": "Statement"},
        headers=headers,
    ).json()
    revision = client.get(
        f"/api/admin/problems/{problem['id']}/revisions", headers=headers
    ).json()[0]

    created = client.post(
        f"/api/admin/problems/{problem['id']}/revisions/{revision['id']}/validation-jobs",
        params={"idempotency_key": "job-api-once"},
        headers=headers,
    )

    assert created.status_code == 202
    assert created.json()["status"] == "queued"
    job_id = created.json()["id"]
    fetched = client.get(f"/api/admin/problem-jobs/{job_id}", headers=headers)
    events = client.get(
        f"/api/admin/problem-jobs/{job_id}/events", headers=headers
    )
    assert fetched.status_code == 200
    assert events.json()[0]["event_type"] == "queued"
