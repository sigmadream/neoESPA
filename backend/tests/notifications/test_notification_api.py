from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.api.runtime import notification_service
from app.core.db import get_session
from app.main import app
from app.models.schemas import Notification, Submission, SubmissionResult, User
from app.services.auth_service import AuthService

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def _create_user(
    session: Session,
    user_id: str,
    sid: int,
    role: str,
    *,
    is_active: bool = True,
) -> None:
    session.add(
        User(
            id=user_id,
            sid=sid,
            ps=AuthService.get_password_hash("password"),
            name=user_id,
            phone="010-0000-0000",
            email=f"{user_id}@example.com",
            user_group=role,
            is_active=is_active,
        )
    )
    session.commit()


def _login(client: TestClient, user_id: str) -> str:
    response = client.post(
        "/api/auth/login", json={"id": user_id, "ps": "password"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_notice_publication_creates_notification():
    with Session(engine) as session:
        _create_user(session, "notice-admin", 10054001, "admin")
        _create_user(session, "notice-student", 20254001, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "notice-admin")
        student_token = _login(client, "notice-student")

        create_response = client.post(
            "/api/admin/notices",
            json={
                "title": "Class Update",
                "author": "Admin",
                "content": "Please review the new deadline.",
                "date": None,
                "is_pinned": False,
                "is_published": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        list_response = client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    notification = list_response.json()[0]
    assert notification["kind"] == "notice"
    assert notification["reference_type"] == "notice"
    assert notification["title"] == "새 공지: Class Update"


def test_notice_update_does_not_duplicate_publication_notifications():
    with Session(engine) as session:
        _create_user(session, "notice-admin-2", 10054002, "admin")
        _create_user(session, "notice-student-2", 20254002, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "notice-admin-2")
        student_token = _login(client, "notice-student-2")

        create_response = client.post(
            "/api/admin/notices",
            json={
                "title": "Original Notice",
                "author": "Admin",
                "content": "Initial content",
                "date": None,
                "is_pinned": False,
                "is_published": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        notice_num = create_response.json()["num"]
        update_response = client.patch(
            f"/api/admin/notices/{notice_num}",
            json={
                "title": "Original Notice (Edited)",
                "author": "Admin",
                "content": "Edited content",
                "date": None,
                "is_pinned": True,
                "is_published": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        list_response = client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_mark_notifications_read_returns_empty_list_for_empty_payload():
    with Session(engine) as session:
        _create_user(session, "notice-student-3", 20254003, "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        student_token = _login(client, "notice-student-3")
        response = client.post(
            "/api/notifications/read",
            json={"notification_ids": []},
            headers={"Authorization": f"Bearer {student_token}"},
        )

        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []


def test_mark_notifications_read_updates_only_current_user_notifications():
    with Session(engine) as session:
        _create_user(session, "notice-reader-a", 20254004, "student")
        _create_user(session, "notice-reader-b", 20254005, "student")
        session.add_all(
            [
                Notification(
                    user_id="notice-reader-a",
                    kind="notice",
                    title="A-1",
                    message="First notification",
                    reference_type="notice",
                    reference_id="1",
                ),
                Notification(
                    user_id="notice-reader-a",
                    kind="notice",
                    title="A-2",
                    message="Second notification",
                    reference_type="notice",
                    reference_id="2",
                ),
                Notification(
                    user_id="notice-reader-b",
                    kind="notice",
                    title="B-1",
                    message="Other user notification",
                    reference_type="notice",
                    reference_id="3",
                ),
            ]
        )
        session.commit()
        notifications = session.exec(
            select(Notification).order_by(Notification.id)
        ).all()

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        student_token = _login(client, "notice-reader-a")
        response = client.post(
            "/api/notifications/read",
            json={
                "notification_ids": [notifications[0].id, notifications[2].id]
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )

        refreshed_notifications = session.exec(
            select(Notification).order_by(Notification.id)
        ).all()
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [notifications[0].id]
    assert refreshed_notifications[0].is_read is True
    assert refreshed_notifications[1].is_read is False
    assert refreshed_notifications[2].is_read is False


def test_notice_publication_skips_inactive_students():
    with Session(engine) as session:
        _create_user(session, "notice-admin-3", 10054003, "admin")
        _create_user(session, "notice-student-active", 20254006, "student")
        _create_user(
            session,
            "notice-student-inactive",
            20254007,
            "student",
            is_active=False,
        )

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "notice-admin-3")
        create_response = client.post(
            "/api/admin/notices",
            json={
                "title": "Active Students Only",
                "author": "Admin",
                "content": "Only active students should receive this notice.",
                "date": None,
                "is_pinned": False,
                "is_published": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        created_notifications = session.exec(
            select(Notification).order_by(Notification.id)
        ).all()

        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert [notification.user_id for notification in created_notifications] == [
        "notice-student-active"
    ]


def test_grade_notification_uses_manual_score_when_present():
    with Session(engine) as session:
        _create_user(session, "graded-student", 20254008, "student")
        submission = Submission(
            homework_num=12,
            user_id="graded-student",
            submission_mode="official",
            attempt_no=1,
            language="python",
            status="graded",
            code_text="print('ok')\n",
            original_filename="answer.py",
        )
        session.add(submission)
        session.commit()
        session.refresh(submission)

        result = SubmissionResult(
            submission_id=submission.id or 0,
            status="graded",
            total_score=65.0,
            manual_total_score=87.5,
        )
        session.add(result)
        session.commit()
        submission_id = submission.id or 0

        notification = notification_service.notify_submission_graded(
            session, submission, result
        )
        session.commit()
        session.refresh(notification)

    assert notification.reference_type == "submission"
    assert notification.reference_id == str(submission_id)
    assert notification.title == "채점 완료: 과제 #12"
    assert "87.5점" in notification.message
