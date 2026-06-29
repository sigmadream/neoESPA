import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models.schemas import GradingRule, Homework, SystemSetting, User
from app.services.auth_service import AuthService



engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def _dt_string(offset_days: int, offset_hours: int = 0) -> str:
    return (
        datetime.now(UTC) + timedelta(days=offset_days, hours=offset_hours)
    ).strftime("%Y-%m-%d %H:%M:%S")


def _create_user(
    session: Session,
    user_id: str,
    sid: int,
    password: str,
    role: str,
) -> None:
    session.add(
        User(
            id=user_id,
            sid=sid,
            ps=AuthService.get_password_hash(password),
            name=user_id,
            phone="010-0000-0000",
            email=f"{user_id}@example.com",
            user_group=role,
        )
    )
    session.commit()


def _create_homework(session: Session, homework_num: int) -> None:
    session.add(
        Homework(
            num=homework_num,
            title="Settings Homework",
            intro="Lint settings should affect grading.",
            starttime=_dt_string(-1),
            deadline=_dt_string(2),
            codeName="main",
            sec=2,
            isLint=True,
        )
    )
    session.commit()
    session.add(
        GradingRule(
            scope="homework",
            homework_num=homework_num,
            rule_name="testcases",
            rule_value=json.dumps(
                {
                    "cases": [
                        {
                            "name": "ok-output",
                            "input": "",
                            "expected_output": "ok\n",
                            "score": 100,
                            "is_hidden": False,
                        }
                    ]
                }
            ),
            is_active=True,
        )
    )
    session.commit()


def _login(client: TestClient, user_id: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"id": user_id, "ps": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_admin_can_update_lint_settings():
    with Session(engine) as session:
        _create_homework(session, 1)
        _create_user(session, "settings-admin", 10010001, "admin-pass", "admin")
        _create_user(session, "settings-student", 20250001, "student-pass", "student")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)

        admin_token = _login(client, "settings-admin", "admin-pass")
        student_token = _login(client, "settings-student", "student-pass")
        headers = _auth_headers(admin_token)

        default_response = client.get("/api/admin/settings?prefix=lint_", headers=headers)
        update_response = client.patch(
            "/api/admin/settings",
            json={
                "settings": [
                    {"key": "lint_calc_weight", "value": 20},
                    {"key": "lint_calc_panalty", "value": 5},
                    {"key": "lint_err_performance", "value": 2},
                    {"key": "lint_set_default", "value": True},
                ]
            },
            headers=headers,
        )
        updated_settings = client.get("/api/admin/settings?prefix=lint_", headers=headers)
        create_response = client.post(
            "/api/submissions",
            json={
                "homework_num": 1,
                "language": "python",
                "code_text": "name = 'ok'\nprint('{}'.format(name))\n",
                "original_filename": "answer.py",
            },
            headers=_auth_headers(student_token),
        )
        submission_id = create_response.json()["id"]
        grade_response = client.post(
            f"/api/admin/submissions/{submission_id}/grade",
            headers=headers,
        )

        app.dependency_overrides.clear()

    assert default_response.status_code == 200
    assert len(default_response.json()) == 7

    assert update_response.status_code == 200
    update_payload = {item["key"]: item["value"] for item in update_response.json()}
    assert update_payload["lint_calc_weight"] == "20"
    assert update_payload["lint_calc_panalty"] == "5"
    assert update_payload["lint_err_performance"] == "2"
    assert update_payload["lint_set_default"] == "true"

    assert updated_settings.status_code == 200
    settings_payload = {item["key"]: item["value"] for item in updated_settings.json()}
    assert settings_payload["lint_set_default"] == "true"

    assert create_response.status_code == 201
    assert grade_response.status_code == 200
    assert grade_response.json()["total_score"] == 110.0
    assert grade_response.json()["submission_score"] == 100.0
    assert grade_response.json()["quality_score"] == 10.0
    assert "Lint score 10.0/20" in (grade_response.json()["grader_summary"] or "")

def test_admin_settings_reject_empty_payload_and_unknown_key():
    with Session(engine) as session:
        _create_user(session, "settings-guard-admin", 10010002, "admin-pass", "admin")

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        admin_token = _login(client, "settings-guard-admin", "admin-pass")
        headers = _auth_headers(admin_token)

        empty_response = client.patch(
            "/api/admin/settings",
            json={"settings": []},
            headers=headers,
        )
        unknown_key_response = client.patch(
            "/api/admin/settings",
            json={"settings": [{"key": "unknown_key", "value": 1}]},
            headers=headers,
        )

        app.dependency_overrides.clear()

    assert empty_response.status_code == 400
    assert empty_response.json()["detail"] == "Settings update must include at least one item"
    assert unknown_key_response.status_code == 400
    assert unknown_key_response.json()["detail"] == "Unsupported setting key: unknown_key"


def test_admin_settings_reject_invalid_values_and_update_timestamp():
    with Session(engine) as session:
        _create_user(session, "settings-value-admin", 10010003, "admin-pass", "admin")
        existing_setting = SystemSetting(
            key="lint_calc_weight",
            value="50",
            value_type="number",
            description="original description",
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        session.add(existing_setting)
        session.commit()

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        admin_token = _login(client, "settings-value-admin", "admin-pass")
        headers = _auth_headers(admin_token)

        invalid_boolean_response = client.patch(
            "/api/admin/settings",
            json={"settings": [{"key": "lint_set_default", "value": "maybe"}]},
            headers=headers,
        )
        negative_number_response = client.patch(
            "/api/admin/settings",
            json={"settings": [{"key": "lint_calc_weight", "value": -1}]},
            headers=headers,
        )
        updated_response = client.patch(
            "/api/admin/settings",
            json={"settings": [{"key": "lint_calc_weight", "value": 75}]},
            headers=headers,
        )
        stored_setting = session.get(SystemSetting, "lint_calc_weight")

        app.dependency_overrides.clear()

    assert invalid_boolean_response.status_code == 400
    assert invalid_boolean_response.json()["detail"] == (
        "Invalid setting value for lint_set_default: Boolean setting must be true/false"
    )
    assert negative_number_response.status_code == 400
    assert negative_number_response.json()["detail"] == (
        "Invalid setting value for lint_calc_weight: Numeric setting must be non-negative"
    )
    assert updated_response.status_code == 200
    assert stored_setting is not None
    assert stored_setting.value == "75"
    assert stored_setting.updated_at.replace(tzinfo=UTC) > datetime(2024, 1, 1, tzinfo=UTC)
