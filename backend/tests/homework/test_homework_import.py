import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models.schemas import AuditLog, GradingRule, Homework
from app.domains.homework import router as homework_router

def _read_fixture(name: str) -> bytes:
    path = Path(__file__).resolve().parents[1] / "fixtures" / "homework_import" / name
    return path.read_bytes()

def test_import_auth_requires_admin(client: TestClient, create_user, login_user, auth_headers):
    create_user("student", 20245021, "pass", "student")
    token = login_user("student", "pass")
    
    res = client.post("/api/admin/homeworks/import", headers=auth_headers(token))
    assert res.status_code == 403

def test_admin_can_import_homework(client: TestClient, session: Session, create_user, login_user, auth_headers, dt_string, tmp_path, monkeypatch):
    create_user("admin", 20245023, "pass", "admin")
    token = login_user("admin", "pass")

    artifact_root = tmp_path / "supportFiles" / "homeworks"
    monkeypatch.setattr(homework_router, "_get_homework_artifact_root", lambda: artifact_root)

    response = client.post(
        "/api/admin/homeworks/import",
        data={
            "title": "Imported HW",
            "intro": "...",
            "deadline": dt_string(7),
            "starttime": dt_string(2),
            "codeName": "imp",
            "allowed_languages": '["python"]',
            "isLint": "false",
        },
        files={
            "problem_file": ("problem.pdf", _read_fixture("problem.pdf"), "application/pdf"),
            "input_zip": ("inputs.zip", _read_fixture("inputs.zip"), "application/zip"),
            "output_zip": ("outputs.zip", _read_fixture("outputs.zip"), "application/zip"),
        },
        headers=auth_headers(token),
    )
    
    assert response.status_code == 200
    homework_num = response.json()["num"]
    
    assert session.get(Homework, homework_num) is not None
    audit = session.exec(select(AuditLog).where(AuditLog.target_id == str(homework_num))).first()
    assert audit is not None
    assert (artifact_root / str(homework_num)).exists()

def test_import_validation_zip_errors(client: TestClient, create_user, login_user, auth_headers, dt_string):
    create_user("admin-v", 20245026, "pass", "admin")
    token = login_user("admin-v", "pass")

    # 부식된 ZIP 파일 테스트
    response = client.post(
        "/api/admin/homeworks/import",
        data={
            "title": "V", 
            "intro": "V", 
            "deadline": dt_string(7), 
            "starttime": dt_string(2), 
            "codeName": "v",
            "isLint": "false",
        },
        files={
            "problem_file": ("p.pdf", _read_fixture("problem.pdf"), "application/pdf"),
            "input_zip": ("i.zip", _read_fixture("corrupt.zip"), "application/zip"),
            "output_zip": ("o.zip", _read_fixture("outputs.zip"), "application/zip"),
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 400
    assert "corrupt" in response.json()["detail"].lower()
