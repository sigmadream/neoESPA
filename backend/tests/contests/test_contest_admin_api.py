from datetime import UTC, datetime, timedelta

from app.models.schemas import (
    Contest,
    ContestParticipation,
    ContestProblem,
    ContestResultEvent,
    Homework,
    Problem,
    ProblemRevision,
    Submission,
    User,
)


def test_contest_pins_published_revision(
    client, create_user, login_user, auth_headers
):
    create_user("contest-admin", 20259801, "password", role="admin")
    headers = auth_headers(login_user("contest-admin"))
    problem = client.post(
        "/api/admin/problems",
        json={
            "code": "contest-problem",
            "title": "Contest Problem",
            "statement": "Solve",
        },
        headers=headers,
    ).json()
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
    now = datetime.now(UTC)
    contest = client.post(
        "/api/admin/contests",
        json={
            "code": "fall-final",
            "title": "Fall Final",
            "starts_at": (now + timedelta(days=1)).isoformat(),
            "ends_at": (now + timedelta(days=1, hours=3)).isoformat(),
            "freeze_at": (now + timedelta(days=1, hours=2)).isoformat(),
            "scoring_format": "icpc",
        },
        headers=headers,
    )
    assert contest.status_code == 201
    contest_id = contest.json()["id"]
    attached = client.post(
        f"/api/admin/contests/{contest_id}/problems",
        json={"revision_id": revision["id"], "label": "A", "position": 1},
        headers=headers,
    )
    published = client.post(
        f"/api/admin/contests/{contest_id}/publish", headers=headers
    )
    second_attach = client.post(
        f"/api/admin/contests/{contest_id}/problems",
        json={"revision_id": revision["id"], "label": "B", "position": 2},
        headers=headers,
    )

    assert attached.status_code == 201
    assert attached.json()["revision_id"] == revision["id"]
    assert published.json()["status"] == "published"
    assert second_attach.status_code == 409


def test_participant_can_join_and_use_clarifications_and_announcements(
    client, session, create_user, login_user, auth_headers
):
    create_user("contest-admin", 20259802, "password", role="admin")
    create_user("contest-student", 20259803, "password", role="student")
    now = datetime.now(UTC)
    contest = Contest(
        code="live-contest",
        title="Live Contest",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=2),
        status="published",
        visibility="public",
        scoring_format="icpc",
        allow_virtual=True,
        created_by="contest-admin",
    )
    session.add(contest)
    session.commit()
    session.refresh(contest)
    admin_headers = auth_headers(login_user("contest-admin"))
    student_headers = auth_headers(login_user("contest-student"))
    joined = client.post(
        f"/api/contests/{contest.id}/participations",
        json={"participation_type": "official"},
        headers=student_headers,
    )
    announcement = client.post(
        f"/api/admin/contests/{contest.id}/announcements",
        json={"title": "Correction", "message": "Read sample 2 again."},
        headers=admin_headers,
    )
    asked = client.post(
        f"/api/contests/{contest.id}/clarifications",
        json={"question": "Is input sorted?"},
        headers=student_headers,
    )
    answered = client.patch(
        f"/api/admin/contests/{contest.id}/clarifications/{asked.json()['id']}",
        json={"answer": "Yes."},
        headers=admin_headers,
    )
    visible = client.get(
        f"/api/contests/{contest.id}/announcements",
        headers=student_headers,
    )
    assert joined.status_code == 201
    assert announcement.status_code == 201
    assert asked.status_code == 201
    assert answered.json()["status"] == "answered"
    assert visible.json()[0]["title"] == "Correction"


def test_scoreboard_can_replay_live_and_system_testing_results(
    client, session, create_user, login_user, auth_headers
):
    create_user("replay-admin", 20259804, "password", role="admin")
    create_user("replay-student", 20259805, "password", role="student")
    now = datetime.now(UTC)
    homework = Homework(
        num=990, title="Replay", intro="Replay", codeName="main"
    )
    problem = Problem(
        code="replay-problem", title="Replay", owner_id="replay-admin"
    )
    contest = Contest(
        code="replay-contest",
        title="Replay",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
        status="published",
        visibility="public",
        system_testing=True,
        created_by="replay-admin",
    )
    session.add(homework)
    session.add(problem)
    session.add(contest)
    session.flush()
    revision = ProblemRevision(
        problem_id=problem.id,
        revision_no=1,
        status="published",
        created_by="replay-admin",
    )
    participation = ContestParticipation(
        contest_id=contest.id,
        user_id="replay-student",
        started_at=now - timedelta(minutes=30),
    )
    submission = Submission(
        homework_num=990,
        user_id="replay-student",
        language="python",
        code_text="print(1)",
    )
    session.add(revision)
    session.add(participation)
    session.add(submission)
    session.flush()
    contest_problem = ContestProblem(
        contest_id=contest.id, revision_id=revision.id, label="A", position=1
    )
    session.add(contest_problem)
    session.flush()
    session.add(
        ContestResultEvent(
            contest_id=contest.id,
            sequence_no=1,
            participation_id=participation.id,
            contest_problem_id=contest_problem.id,
            submission_id=submission.id,
            verdict="WA",
            score=0,
            result_phase="live",
            occurred_at=now - timedelta(minutes=10),
        )
    )
    session.add(
        ContestResultEvent(
            contest_id=contest.id,
            sequence_no=2,
            participation_id=participation.id,
            contest_problem_id=contest_problem.id,
            submission_id=submission.id,
            verdict="AC",
            score=100,
            result_phase="system",
            occurred_at=now,
        )
    )
    session.commit()
    headers = auth_headers(login_user("replay-student"))

    live = client.get(
        f"/api/contests/{contest.id}/scoreboard?phase=live", headers=headers
    )
    system = client.get(
        f"/api/contests/{contest.id}/scoreboard?phase=system", headers=headers
    )

    assert live.json()[0]["score"] == 0
    assert live.json()[0]["solved"] == 0
    assert system.json()[0]["score"] == 100
    assert system.json()[0]["solved"] == 1


def test_contest_organization_scope_is_enforced(
    client, session, create_user, login_user, auth_headers
):
    create_user("org-student", 20259806, "password", role="student")
    student = session.get(User, "org-student")
    student.organization_id = "org-b"
    contest = Contest(
        code="org-contest",
        title="Organization Contest",
        starts_at=datetime.now(UTC) - timedelta(minutes=5),
        ends_at=datetime.now(UTC) + timedelta(hours=1),
        status="published",
        visibility="restricted",
        allowed_organizations_json='["org-a"]',
        created_by="org-student",
    )
    session.add(student)
    session.add(contest)
    session.commit()
    headers = auth_headers(login_user("org-student"))

    denied = client.post(
        f"/api/contests/{contest.id}/participations",
        json={"participation_type": "official"},
        headers=headers,
    )

    assert denied.status_code == 403
    assert (
        denied.json()["detail"]
        == "Contest is restricted to selected organizations"
    )
