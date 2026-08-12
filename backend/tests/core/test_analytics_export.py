import json

import pytest

from app.models.schemas import AnalyticsConsent, Homework, Submission, User
from app.services.analytics_export import AnalyticsExportError, AnalyticsExportService


def _user(user_id: str, sid: int) -> User:
    return User(
        id=user_id, sid=sid, ps="hash", name=user_id, phone="", email=f"{user_id}@test",
        user_group="student",
    )


def test_analytics_export_only_includes_latest_consented_learners(session, tmp_path):
    session.add(Homework(num=1, title="H", intro="", starttime="", deadline="", codeName="main"))
    session.add(_user("allowed", 1001))
    session.add(_user("denied", 1002))
    session.commit()
    session.add(AnalyticsConsent(
        user_id="allowed", granted=True, purpose="research", policy_version="v1",
        scope_json='["submissions"]',
    ))
    session.add(AnalyticsConsent(
        user_id="denied", granted=False, purpose="research", policy_version="v1",
        scope_json='["submissions"]',
    ))
    session.add(Submission(
        homework_num=1, user_id="allowed", language="python", code_text="secret source",
    ))
    session.add(Submission(
        homework_num=1, user_id="denied", language="python", code_text="other source",
    ))
    session.commit()
    service = AnalyticsExportService("x" * 32, tmp_path)
    counts = service.export_jsonl(session, purpose="research", policy_version="v1")
    rows = [json.loads(line) for line in (tmp_path / "exports/submissions.jsonl").read_text().splitlines()]
    assert counts["submissions"] == 1
    assert rows[0]["learner_id"] == service.pseudonym(1001)
    assert "user_id" not in rows[0]
    assert "code_text" not in rows[0]


def test_analytics_export_rejects_weak_secret(tmp_path):
    with pytest.raises(AnalyticsExportError, match="at least 32"):
        AnalyticsExportService("weak", tmp_path)
