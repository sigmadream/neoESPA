from fastapi.testclient import TestClient
from sqlmodel import Session, select
from datetime import UTC, datetime

from app.models.schemas import CodeSnapshot, User, Homework


def create_test_homework(session: Session, num: int):
    now = datetime.now(UTC)
    homework = Homework(
        num=num,
        title=f"Test Homework {num}",
        intro="Test Intro",
        codeName=f"test_{num}",
        created_at=now,
        updated_at=now
    )
    session.add(homework)
    session.commit()
    session.refresh(homework)
    return homework


def test_save_code_snapshot(client: TestClient, create_user, login_user, auth_headers, session: Session):
    create_test_homework(session, 1)
    create_user("student1", 20240001, "password")
    token = login_user("student1", "password")
    headers = auth_headers(token)

    response = client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 1,
            "language": "python",
            "code_text": "print('hello')",
            "snapshot_type": "auto_save"
        },
        headers=headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["code_text"] == "print('hello')"
    assert data["user_id"] == "student1"
    assert data["snapshot_type"] == "auto_save"


def test_save_duplicate_snapshot_optimization(client: TestClient, create_user, login_user, auth_headers, session: Session):
    create_test_homework(session, 2)
    create_user("student2", 20240002, "password")
    token = login_user("student2", "password")
    headers = auth_headers(token)

    # First save
    client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 2,
            "language": "python",
            "code_text": "same code",
        },
        headers=headers
    )

    # Second save with identical code
    response = client.post(
        "/api/submissions/snapshots",
        json={
            "homework_num": 2,
            "language": "python",
            "code_text": "same code",
        },
        headers=headers
    )

    assert response.status_code == 201
    
    # Check DB count - should be only 1
    snapshots = session.exec(
        select(CodeSnapshot).where(CodeSnapshot.user_id == "student2")
    ).all()
    assert len(snapshots) == 1


def test_get_latest_snapshot(client: TestClient, create_user, login_user, auth_headers, session: Session):
    create_test_homework(session, 3)
    create_user("student3", 20240003, "password")
    token = login_user("student3", "password")
    headers = auth_headers(token)

    # Save first
    client.post(
        "/api/submissions/snapshots",
        json={"homework_num": 3, "language": "python", "code_text": "first version"},
        headers=headers
    )
    # Save second (latest)
    client.post(
        "/api/submissions/snapshots",
        json={"homework_num": 3, "language": "python", "code_text": "latest version"},
        headers=headers
    )

    response = client.get("/api/homeworks/3/snapshots/latest", headers=headers)
    
    assert response.status_code == 200
    assert response.json()["code_text"] == "latest version"


def test_admin_can_list_student_snapshots(client: TestClient, create_user, login_user, auth_headers, session: Session):
    create_test_homework(session, 4)
    create_user("student4", 20240004, "password")
    create_user("admin1", 10000001, "admin-pass", role="admin")
    
    student_token = login_user("student4", "password")
    admin_token = login_user("admin1", "admin-pass")
    
    student_headers = auth_headers(student_token)
    admin_headers = auth_headers(admin_token)

    # Student saves code
    client.post(
        "/api/submissions/snapshots",
        json={"homework_num": 4, "language": "python", "code_text": "working code"},
        headers=student_headers
    )

    # Admin checks history
    response = client.get("/api/admin/homeworks/4/snapshots/student4", headers=admin_headers)
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["code_text"] == "working code"


def test_non_admin_cannot_list_student_snapshots(client: TestClient, create_user, login_user, auth_headers, session: Session):
    create_test_homework(session, 5)
    create_user("student5", 20240005, "password")
    create_user("student6", 20240006, "password")
    
    token5 = login_user("student5", "password")
    headers5 = auth_headers(token5)

    response = client.get("/api/admin/homeworks/5/snapshots/student6", headers=headers5)
    
    assert response.status_code == 403
