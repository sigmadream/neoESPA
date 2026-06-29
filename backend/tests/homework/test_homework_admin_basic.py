from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.domains.homework import router as homework_router
from app.models.schemas import GradingRule, Homework


def test_admin_can_create_homework_with_schedule(client: TestClient, create_user, login_user, auth_headers, dt_string):
    create_user("homework-admin", 20245001, "admin-pass", "admin")
    token = login_user("homework-admin", "admin-pass")

    response = client.post(
        "/api/admin/homeworks",
        json={
            "title": "Scheduled Homework",
            "intro": "Managed through the admin API.",
            "deadline": dt_string(7),
            "starttime": dt_string(2),
            "codeName": "scheduled",
            "isLint": True,
            "allowed_languages": ["python", "cpp"],
            "lint_week": "4",
            "testcases": [
                {"name": "p1", "input": "1", "expected_output": "3", "score": 40, "is_hidden": False},
                {"name": "h1", "input": "2", "expected_output": "5", "score": 60, "is_hidden": True},
            ],
        },
        headers=auth_headers(token),
    )
    
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Scheduled Homework"
    assert payload["schedule_status"] == "upcoming"
    assert len(payload["testcases"]) == 2

def test_admin_can_update_testcase_policy(client: TestClient, session: Session, create_user, login_user, auth_headers, dt_string):
    create_user("homework-admin", 20245002, "admin-pass", "admin")
    create_user("homework-student", 20245003, "student-pass", "student")
    admin_token = login_user("homework-admin", "admin-pass")
    student_token = login_user("homework-student", "student-pass")

    create_res = client.post(
        "/api/admin/homeworks",
        json={"title": "Policy HW", "intro": "init", "deadline": dt_string(3), "starttime": dt_string(-1), "codeName": "policy"},
        headers=auth_headers(admin_token),
    )
    homework_num = create_res.json()["num"]

    update_res = client.patch(
        f"/api/admin/homeworks/{homework_num}",
        json={
            "title": "Updated Policy",
            "intro": "updated",
            "deadline": dt_string(5),
            "starttime": dt_string(-2),
            "codeName": "policy",
            "isLint": True,
            "allowed_languages": ["python"],
            "testcases": [{"name": "case1", "input": "3", "expected_output": "3", "score": 100, "is_hidden": False}],
        },
        headers=auth_headers(admin_token),
    )
    
    assert update_res.status_code == 200
    assert update_res.json()["allowed_languages"] == ["python"]

    # 학생 API에서 언어 제한 확인
    sub_res = client.post(
        "/api/submissions",
        json={"homework_num": homework_num, "language": "cpp", "code_text": "int main(){}"},
        headers=auth_headers(student_token),
    )
    assert sub_res.status_code == 400
    assert "language is not allowed" in sub_res.json()["detail"]

def test_admin_can_delete_homework_without_submissions(client: TestClient, session: Session, create_user, login_user, auth_headers, dt_string):
    create_user("homework-admin", 20245004, "admin-pass", "admin")
    token = login_user("homework-admin", "admin-pass")

    create_res = client.post(
        "/api/admin/homeworks",
        json={"title": "Delete HW", "intro": "...", "deadline": dt_string(2), "starttime": dt_string(-1), "codeName": "del"},
        headers=auth_headers(token),
    )
    homework_num = create_res.json()["num"]

    del_res = client.delete(f"/api/admin/homeworks/{homework_num}", headers=auth_headers(token))
    assert del_res.status_code == 200
    
    assert session.get(Homework, homework_num) is None
    rules = session.exec(select(GradingRule).where(GradingRule.homework_num == homework_num)).all()
    assert len(rules) == 0

def test_delete_homework_preserves_submission_protection(client: TestClient, create_user, login_user, auth_headers, dt_string):
    create_user("admin", 20245027, "admin-pass", "admin")
    create_user("student", 20245028, "student-pass", "student")
    admin_token = login_user("admin", "admin-pass")
    student_token = login_user("student", "student-pass")

    create_res = client.post(
        "/api/admin/homeworks",
        json={"title": "Protected HW", "intro": "...", "deadline": dt_string(7), "starttime": dt_string(-1), "codeName": "protected"},
        headers=auth_headers(admin_token),
    )
    homework_num = create_res.json()["num"]

    client.post(
        "/api/submissions",
        json={"homework_num": homework_num, "language": "python", "code_text": "print('hi')"},
        headers=auth_headers(student_token),
    )

    del_res = client.delete(f"/api/admin/homeworks/{homework_num}", headers=auth_headers(admin_token))
    assert del_res.status_code == 400
    assert "Cannot delete homework with submissions" in del_res.json()["detail"]

def test_admin_cannot_update_or_delete_missing_homework(client: TestClient, create_user, login_user, auth_headers, dt_string):
    create_user("missing-homework-admin", 20245029, "admin-pass", "admin")
    token = login_user("missing-homework-admin", "admin-pass")

    update_res = client.patch(
        "/api/admin/homeworks/99999",
        json={
            "title": "Missing HW",
            "intro": "...",
            "deadline": dt_string(2),
            "starttime": dt_string(-1),
            "codeName": "missing",
        },
        headers=auth_headers(token),
    )
    delete_res = client.delete(
        "/api/admin/homeworks/99999",
        headers=auth_headers(token),
    )

    assert update_res.status_code == 404
    assert delete_res.status_code == 404
    assert update_res.json()["detail"] == "Homework not found"
    assert delete_res.json()["detail"] == "Homework not found"


def test_delete_homework_removes_artifacts_and_metadata_rules(
    client: TestClient,
    session: Session,
    create_user,
    login_user,
    auth_headers,
    dt_string,
    tmp_path,
    monkeypatch,
):
    create_user("artifact-homework-admin", 20245030, "admin-pass", "admin")
    token = login_user("artifact-homework-admin", "admin-pass")

    artifact_root = tmp_path / "supportFiles" / "homeworks"
    monkeypatch.setattr(homework_router, "_get_homework_artifact_root", lambda: artifact_root)

    create_res = client.post(
        "/api/admin/homeworks",
        json={
            "title": "Artifact HW",
            "intro": "...",
            "deadline": dt_string(2),
            "starttime": dt_string(-1),
            "codeName": "artifact",
        },
        headers=auth_headers(token),
    )
    homework_num = create_res.json()["num"]

    homework_root = artifact_root / str(homework_num)
    (homework_root / "problem").mkdir(parents=True)
    (homework_root / "archives").mkdir()
    (homework_root / "problem" / "problem.pdf").write_bytes(b"problem")
    (homework_root / "archives" / "inputs.zip").write_bytes(b"inputs")
    (homework_root / "archives" / "outputs.zip").write_bytes(b"outputs")

    session.add_all(
        [
            GradingRule(
                scope="homework",
                homework_num=homework_num,
                rule_name="problem_file_meta",
                rule_value="{}",
                is_active=True,
            ),
            GradingRule(
                scope="homework",
                homework_num=homework_num,
                rule_name="input_zip_meta",
                rule_value="{}",
                is_active=True,
            ),
            GradingRule(
                scope="homework",
                homework_num=homework_num,
                rule_name="output_zip_meta",
                rule_value="{}",
                is_active=True,
            ),
        ]
    )
    session.commit()

    delete_res = client.delete(
        f"/api/admin/homeworks/{homework_num}",
        headers=auth_headers(token),
    )

    assert delete_res.status_code == 200
    assert session.get(Homework, homework_num) is None
    assert session.exec(select(GradingRule).where(GradingRule.homework_num == homework_num)).all() == []
    assert not homework_root.exists()
