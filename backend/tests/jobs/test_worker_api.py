def test_worker_heartbeat_drain_disable_enable_and_metrics(
    client, session, create_user, login_user, auth_headers
):
    from app.services.judge_job_service import JudgeJobService

    create_user("worker-admin", 20259501, "password", role="admin")
    headers = auth_headers(login_user("worker-admin"))
    service = JudgeJobService()
    assert service.claim_next(session, "worker-one", job_types=["none"]) is None

    workers = client.get("/api/admin/judge-workers", headers=headers)
    assert workers.status_code == 200
    assert workers.json()[0]["status"] == "online"

    drained = client.post("/api/admin/judge-workers/worker-one/drain", headers=headers)
    disabled = client.post("/api/admin/judge-workers/worker-one/disable", headers=headers)
    enabled = client.post("/api/admin/judge-workers/worker-one/enable", headers=headers)
    metrics = client.get("/api/admin/grading/metrics", headers=headers)

    assert drained.json()["status"] == "draining"
    assert disabled.json()["status"] == "disabled"
    assert enabled.json()["status"] == "online"
    assert metrics.status_code == 200
    assert metrics.json()["workers_online"] == 1
