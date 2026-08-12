from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlmodel import Session, select

from app.core.compression import compress_text, decompress_text
from app.core.config import settings as app_settings
from app.models.schemas import CodeSnapshot, Homework


def create_test_homework(session: Session, num: int):
    now = datetime.now(UTC)
    homework = Homework(
        num=num,
        title=f"Test Homework {num}",
        intro="Test Intro",
        codeName=f"test_{num}",
        created_at=now,
        updated_at=now,
    )
    session.add(homework)
    session.commit()
    session.refresh(homework)
    return homework


def test_compress_text_round_trip_handles_unicode_and_multiline():
    original = "print('안녕하세요')\nprint('second line')\n"

    compressed = compress_text(original)

    assert compressed != original
    assert decompress_text(compressed) == original


def test_decompress_text_falls_back_to_plain_text_for_legacy_or_invalid_input():
    legacy_plain_text = "legacy plain text"
    invalid_payload = "%%%not-base64%%%"

    assert decompress_text(legacy_plain_text) == legacy_plain_text
    assert decompress_text(invalid_payload) == invalid_payload


@settings(max_examples=30, deadline=None)
@given(
    original=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n\t()[]{}+-=*/'\"_,.;:안녕하세요",
        min_size=0,
        max_size=200,
    )
)
def test_compress_text_round_trip_property(original: str):
    compressed = compress_text(original)

    assert decompress_text(compressed) == original
    if original:
        assert compressed != original


def test_save_code_snapshot_stores_compressed_text_and_returns_plain_text(
    client: TestClient, create_user, login_user, auth_headers, session: Session
):
    create_test_homework(session, 1)
    create_user("student1", 20240001, "password")
    token = login_user("student1", "password")
    headers = auth_headers(token)
    original_code = "print('hello')\nprint('snapshot')"

    response = client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 1,
            "language": "python",
            "code_text": original_code,
            "snapshot_type": "auto_save",
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["code_text"] == original_code
    assert data["user_id"] == "student1"
    assert data["snapshot_type"] == "auto_save"

    stored_snapshot = session.exec(
        select(CodeSnapshot).where(CodeSnapshot.user_id == "student1")
    ).one()
    assert stored_snapshot.code_text != original_code
    assert decompress_text(stored_snapshot.code_text) == original_code


def test_save_duplicate_snapshot_keeps_single_compressed_record(
    client: TestClient, create_user, login_user, auth_headers, session: Session
):
    create_test_homework(session, 2)
    create_user("student2", 20240002, "password")
    token = login_user("student2", "password")
    headers = auth_headers(token)
    original_code = "same code\nwith newline"

    first_response = client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 2,
            "language": "python",
            "code_text": original_code,
            "snapshot_type": "auto_save",
        },
        headers=headers,
    )
    second_response = client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 2,
            "language": "python",
            "code_text": original_code,
            "snapshot_type": "manual_save",
        },
        headers=headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["id"] == second_response.json()["id"]
    assert second_response.json()["code_text"] == original_code

    session.expire_all()
    snapshots = session.exec(
        select(CodeSnapshot).where(CodeSnapshot.user_id == "student2")
    ).all()
    assert len(snapshots) == 1
    assert snapshots[0].snapshot_type == "auto_save"
    assert snapshots[0].code_text != original_code
    assert decompress_text(snapshots[0].code_text) == original_code

    latest_response = client.get(
        "/api/homeworks/2/snapshots/latest", headers=headers
    )
    assert latest_response.status_code == 200
    assert latest_response.json()["id"] == first_response.json()["id"]
    assert latest_response.json()["code_text"] == original_code


def test_save_code_snapshot_returns_404_for_missing_homework(
    client: TestClient, create_user, login_user, auth_headers
):
    create_user("student404", 20240404, "password")
    token = login_user("student404", "password")
    headers = auth_headers(token)

    response = client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 999,
            "language": "python",
            "code_text": "print('missing homework')",
        },
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Homework not found"


def test_get_latest_snapshot(
    client: TestClient, create_user, login_user, auth_headers, session: Session
):
    create_test_homework(session, 3)
    create_user("student3", 20240003, "password")
    token = login_user("student3", "password")
    headers = auth_headers(token)

    client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 3,
            "language": "python",
            "code_text": "first version",
        },
        headers=headers,
    )
    client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 3,
            "language": "python",
            "code_text": "latest version",
        },
        headers=headers,
    )

    response = client.get("/api/homeworks/3/snapshots/latest", headers=headers)

    assert response.status_code == 200
    assert response.json()["code_text"] == "latest version"


def test_admin_can_list_student_snapshots(
    client: TestClient, create_user, login_user, auth_headers, session: Session
):
    create_test_homework(session, 4)
    create_user("student4", 20240004, "password")
    create_user("admin1", 10000001, "admin-pass", role="admin")

    student_token = login_user("student4", "password")
    admin_token = login_user("admin1", "admin-pass")

    student_headers = auth_headers(student_token)
    admin_headers = auth_headers(admin_token)

    client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 4,
            "language": "python",
            "code_text": "working code",
        },
        headers=student_headers,
    )

    response = client.get(
        "/api/admin/homeworks/4/snapshots/student4", headers=admin_headers
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["code_text"] == "working code"


def test_non_admin_cannot_list_student_snapshots(
    client: TestClient, create_user, login_user, auth_headers, session: Session
):
    create_test_homework(session, 5)
    create_user("student5", 20240005, "password")
    create_user("student6", 20240006, "password")

    token5 = login_user("student5", "password")
    headers5 = auth_headers(token5)

    response = client.get(
        "/api/admin/homeworks/5/snapshots/student6", headers=headers5
    )

    assert response.status_code == 403


def test_staff_roles_can_list_student_snapshots(
    client: TestClient, create_user, login_user, auth_headers, session: Session
):
    create_test_homework(session, 6)
    create_user("snapshot-student", 20240007, "password")
    create_user("snapshot-admin", 10000007, "staff-pass", role="admin")
    create_user(
        "snapshot-instructor", 10000008, "staff-pass", role="instructor"
    )
    create_user("snapshot-ta", 10000009, "staff-pass", role="ta")

    student_token = login_user("snapshot-student", "password")
    student_headers = auth_headers(student_token)
    client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 6,
            "language": "python",
            "code_text": "staff visible code",
        },
        headers=student_headers,
    )

    for user_id in ["snapshot-admin", "snapshot-instructor", "snapshot-ta"]:
        token = login_user(user_id, "staff-pass")
        response = client.get(
            "/api/admin/homeworks/6/snapshots/snapshot-student",
            headers=auth_headers(token),
        )
        assert response.status_code == 200
        assert response.json()[0]["code_text"] == "staff visible code"


def test_save_code_snapshot_rate_limit_blocks_excess_requests(
    client: TestClient,
    create_user,
    login_user,
    auth_headers,
    session: Session,
    monkeypatch,
):
    monkeypatch.setattr(app_settings, "SNAPSHOT_RATE_LIMIT_COUNT", 2)
    monkeypatch.setattr(
        app_settings, "SNAPSHOT_RATE_LIMIT_WINDOW_SECONDS", 3600
    )

    create_test_homework(session, 7)
    create_user("rate-limit-student", 20240010, "password")
    token = login_user("rate-limit-student", "password")
    headers = auth_headers(token)

    first_response = client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 7,
            "language": "python",
            "code_text": "print('one')",
        },
        headers=headers,
    )
    second_response = client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 7,
            "language": "python",
            "code_text": "print('two')",
        },
        headers=headers,
    )
    third_response = client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 7,
            "language": "python",
            "code_text": "print('three')",
        },
        headers=headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert third_response.status_code == 429
    assert third_response.json()["detail"] == (
        "Snapshot save limit exceeded. Up to 2 saves are allowed per 3600 seconds."
    )

    stored_snapshots = session.exec(
        select(CodeSnapshot).where(CodeSnapshot.user_id == "rate-limit-student")
    ).all()
    assert len(stored_snapshots) == 2


def test_save_code_snapshot_rate_limit_allows_new_snapshot_after_window(
    client: TestClient,
    create_user,
    login_user,
    auth_headers,
    session: Session,
    monkeypatch,
):
    monkeypatch.setattr(app_settings, "SNAPSHOT_RATE_LIMIT_COUNT", 1)
    monkeypatch.setattr(app_settings, "SNAPSHOT_RATE_LIMIT_WINDOW_SECONDS", 60)

    create_test_homework(session, 8)
    create_user("rate-limit-window", 20240011, "password")
    session.add(
        CodeSnapshot(
            homework_num=8,
            user_id="rate-limit-window",
            language="python",
            code_text=compress_text("print('old')"),
            snapshot_type="auto_save",
            created_at=datetime.now(UTC) - timedelta(seconds=120),
        )
    )
    session.commit()

    token = login_user("rate-limit-window", "password")
    headers = auth_headers(token)
    response = client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 8,
            "language": "python",
            "code_text": "print('new')",
        },
        headers=headers,
    )

    assert response.status_code == 201
    latest_response = client.get(
        "/api/homeworks/8/snapshots/latest", headers=headers
    )
    assert latest_response.status_code == 200
    assert latest_response.json()["code_text"] == "print('new')"


def test_save_code_snapshot_rate_limit_is_scoped_per_user(
    client: TestClient,
    create_user,
    login_user,
    auth_headers,
    session: Session,
    monkeypatch,
):
    monkeypatch.setattr(app_settings, "SNAPSHOT_RATE_LIMIT_COUNT", 1)
    monkeypatch.setattr(
        app_settings, "SNAPSHOT_RATE_LIMIT_WINDOW_SECONDS", 3600
    )

    create_test_homework(session, 9)
    create_user("rate-limit-user-a", 20240012, "password")
    create_user("rate-limit-user-b", 20240013, "password")

    headers_a = auth_headers(login_user("rate-limit-user-a", "password"))
    headers_b = auth_headers(login_user("rate-limit-user-b", "password"))

    first_user_first_response = client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 9,
            "language": "python",
            "code_text": "print('a1')",
        },
        headers=headers_a,
    )
    first_user_second_response = client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 9,
            "language": "python",
            "code_text": "print('a2')",
        },
        headers=headers_a,
    )
    second_user_response = client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 9,
            "language": "python",
            "code_text": "print('b1')",
        },
        headers=headers_b,
    )

    assert first_user_first_response.status_code == 201
    assert first_user_second_response.status_code == 429
    assert second_user_response.status_code == 201
