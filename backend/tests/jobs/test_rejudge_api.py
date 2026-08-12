from sqlmodel import select

from app.models.schemas import JudgeJob, Submission


def test_rejudge_preview_batch_idempotency_and_cancel(
    client,
    session,
    create_user,
    create_homework,
    create_submission,
    login_user,
    auth_headers,
):
    create_user("rejudge-admin", 20259401, "password", role="admin")
    create_user("rejudge-student", 20259402, "password", role="student")
    create_homework(401, "Rejudge Homework")
    first = create_submission(
        homework_num=401, user_id="rejudge-student", attempt_no=1
    )
    second = create_submission(
        homework_num=401, user_id="rejudge-student", attempt_no=2
    )
    headers = auth_headers(login_user("rejudge-admin"))

    preview = client.post(
        "/api/admin/rejudge-jobs/preview",
        json={"homework_num": 401},
        headers=headers,
    )
    assert preview.status_code == 200
    assert preview.json()["target_count"] == 2
    assert preview.json()["submission_ids"] == [first.id, second.id]

    request = {
        "homework_num": 401,
        "reason": "Checker policy corrected",
        "idempotency_key": "rejudge-homework-401-v1",
    }
    created = client.post(
        "/api/admin/rejudge-jobs", json=request, headers=headers
    )
    repeated = client.post(
        "/api/admin/rejudge-jobs", json=request, headers=headers
    )
    assert created.status_code == 202
    assert repeated.status_code == 202
    assert repeated.json()["id"] == created.json()["id"]

    parent_id = created.json()["id"]
    children = session.exec(
        select(JudgeJob).where(JudgeJob.parent_job_id == parent_id)
    ).all()
    assert len(children) == 2
    assert {child.submission_id for child in children} == {first.id, second.id}

    cancelled = client.post(
        f"/api/admin/rejudge-jobs/{parent_id}/cancel", headers=headers
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    session.expire_all()
    assert all(
        child.status == "cancelled"
        for child in session.exec(
            select(JudgeJob).where(JudgeJob.parent_job_id == parent_id)
        ).all()
    )


def test_student_cannot_create_rejudge_job(
    client, create_user, login_user, auth_headers
):
    create_user("no-rejudge", 20259403, "password", role="student")
    response = client.post(
        "/api/admin/rejudge-jobs/preview",
        json={},
        headers=auth_headers(login_user("no-rejudge")),
    )
    assert response.status_code == 403


def test_rejudge_preview_and_creation_support_more_than_one_thousand_targets(
    client, session, create_user, create_homework, login_user, auth_headers
):
    create_user("bulk-admin", 20259410, "password", role="admin")
    create_user("bulk-student", 20259411, "password", role="student")
    create_homework(410, "Bulk Rejudge")
    session.add_all(
        [
            Submission(
                homework_num=410,
                user_id="bulk-student",
                submission_mode="official",
                attempt_no=index,
                language="python",
                status="graded",
                code_text="print(1)",
            )
            for index in range(1, 1002)
        ]
    )
    session.commit()
    headers = auth_headers(login_user("bulk-admin"))
    preview = client.post(
        "/api/admin/rejudge-jobs/preview",
        json={"homework_num": 410},
        headers=headers,
    )
    assert preview.status_code == 200
    assert preview.json()["target_count"] == 1001
    assert preview.json()["truncated"] is True
    created = client.post(
        "/api/admin/rejudge-jobs",
        json={
            "homework_num": 410,
            "reason": "Bulk verification",
            "idempotency_key": "bulk-410-v1",
        },
        headers=headers,
    )
    assert created.status_code == 202
    child_count = len(
        session.exec(
            select(JudgeJob).where(
                JudgeJob.parent_job_id == created.json()["id"]
            )
        ).all()
    )
    assert child_count == 1001
