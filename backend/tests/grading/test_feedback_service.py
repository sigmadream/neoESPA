import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.models.schemas import GradingRule, Homework, Notice, Submission, SubmissionResult
from app.services.feedback_service import FeedbackService

@pytest.fixture
def mock_support_dir(tmp_path):
    support = tmp_path / "supportFiles"
    support.mkdir()
    (support / "week_rules.json").write_text(json.dumps({"pylint": {"1": ["rule1"]}}), encoding="utf-8")
    (support / "pylint_message.json").write_text(json.dumps({"rule1": {"kor": "규칙1"}}), encoding="utf-8")
    (support / "lint_rule_manual.json").write_text(json.dumps({"pylint": {"rule1": {"kor": "규칙1 상세"}}}), encoding="utf-8")
    return support

@pytest.fixture
def feedback_service(mock_support_dir):
    return FeedbackService(support_dir=mock_support_dir)

def test_deadline_feedback_logic(feedback_service):
    # 1. 마감 전 (open)
    hw_open = Homework(
        title="Open HW",
        intro="...",
        codeName="main",
        starttime=(datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        deadline=(datetime.now(UTC) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    )
    status, _ = feedback_service._deadline_feedback(hw_open)
    assert status == "open"

    # 2. 마감 임박 (closing_soon) - 24시간 이내
    hw_soon = Homework(
        title="Soon HW",
        intro="...",
        codeName="main",
        starttime=(datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        deadline=(datetime.now(UTC) + timedelta(hours=23)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    )
    status, _ = feedback_service._deadline_feedback(hw_soon)
    assert status == "closing_soon"

    # 3. 마감 후 (closed)
    hw_closed = Homework(
        title="Closed HW",
        intro="...",
        codeName="main",
        starttime=(datetime.now(UTC) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        deadline=(datetime.now(UTC) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    )
    status, _ = feedback_service._deadline_feedback(hw_closed)
    assert status == "closed"

    # 4. 시작 전 (upcoming)
    hw_upcoming = Homework(
        title="Upcoming HW",
        intro="...",
        codeName="main",
        starttime=(datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        deadline=(datetime.now(UTC) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    )
    status, _ = feedback_service._deadline_feedback(hw_upcoming)
    assert status == "upcoming"

def test_build_hints_mapping(feedback_service):
    # 컴파일 실패 시 힌트
    res_compile_fail = SubmissionResult(submission_id=1, compile_status="failed", status="graded")
    hints = feedback_service._build_hints(res_compile_fail, "open", None, lint_enabled=True)
    assert any("컴파일 오류" in h for h in hints)

    # 타임아웃 시 힌트
    res_timeout = SubmissionResult(submission_id=1, run_status="timeout", status="graded")
    hints = feedback_service._build_hints(res_timeout, "open", None, lint_enabled=True)
    assert any("시간 초과" in h for h in hints)

    # 낮은 코드 품질 점수 힌트
    res_low_quality = SubmissionResult(submission_id=1, run_status="passed", quality_score=10, status="graded")
    hints = feedback_service._build_hints(res_low_quality, "open", None, lint_enabled=True)
    assert any("코드 품질 점수" in h for h in hints)

    # 린트가 꺼진 과제에서는 품질 점수 힌트를 보여주지 않는다
    hints = feedback_service._build_hints(res_low_quality, "open", None, lint_enabled=False)
    assert not any("코드 품질 점수" in h for h in hints)

def test_latest_notice_filtering(feedback_service, session: Session):
    # 공지사항이 없는 경우
    assert feedback_service._latest_notice(session) is None

    # 발행된 공지사항과 미발행 공지사항 혼합
    session.add(Notice(title="Not Published", author="admin", content="...", is_published=False))
    session.add(Notice(title="Old Published", author="admin", content="...", is_published=True, date="2020-01-01 00:00:00"))
    session.add(Notice(title="New Published", author="admin", content="...", is_published=True, date="2026-01-01 00:00:00"))
    session.commit()

    latest = feedback_service._latest_notice(session)
    assert latest.title == "New Published"

    # 고정(pinned) 공지사항 우선순위 확인
    session.add(Notice(title="Pinned Notice", author="admin", content="...", is_published=True, is_pinned=True, date="2025-01-01 00:00:00"))
    session.commit()
    
    latest_pinned = feedback_service._latest_notice(session)
    assert latest_pinned.title == "Pinned Notice"


def test_build_submission_feedback_combines_deadline_notice_and_result_hints(
    feedback_service, session: Session
):
    homework = Homework(
        num=7,
        title="Feedback HW",
        intro="...",
        codeName="main",
        starttime=(datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        deadline=(datetime.now(UTC) + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
        isLint=False,
    )
    submission = Submission(
        homework_num=7,
        user_id="student-feedback",
        submission_mode="official",
        attempt_no=1,
        language="python",
        status="failed",
        code_text="print('x')",
    )
    result = SubmissionResult(
        submission_id=1,
        status="failed",
        compile_status="failed",
        run_status="not_started",
        quality_score=0,
    )
    session.add(
        Notice(
            title="Urgent Notice",
            author="admin",
            content="...",
            is_published=True,
            date=(datetime.now(UTC) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        )
    )
    session.commit()

    feedback = feedback_service.build_submission_feedback(session, submission, homework, result)

    assert feedback.deadline_status == "closing_soon"
    assert any("컴파일 오류" in hint for hint in feedback.hints)
    assert any("마감이 임박" in hint for hint in feedback.hints)
    assert any("Urgent Notice" in hint for hint in feedback.hints)


def test_latest_notice_hides_future_notice_and_allows_invalid_date_fallback(
    feedback_service, session: Session
):
    session.add(
        Notice(
            title="Future Notice",
            author="admin",
            content="...",
            is_published=True,
            date=(datetime.now(UTC) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
        )
    )
    session.add(
        Notice(
            title="Invalid Date Notice",
            author="admin",
            content="...",
            is_published=True,
            date="not-a-date",
        )
    )
    session.commit()

    latest = feedback_service._latest_notice(session)

    assert latest is not None
    assert latest.title == "Invalid Date Notice"
    assert feedback_service._parse_datetime("not-a-date") is None


def test_build_guides_uses_lint_week_and_message_fallback(feedback_service, session: Session):
    homework = Homework(
        num=9,
        title="Lint HW",
        intro="...",
        codeName="main",
        isLint=True,
    )
    session.add(homework)
    session.commit()
    session.add(
        GradingRule(
            scope="homework",
            homework_num=9,
            rule_name="lint_week",
            rule_value="week-custom",
            is_active=True,
        )
    )
    session.commit()

    feedback_service.week_rules = {"pylint": {"week-custom": ["rule1", "rule-missing"]}}
    guides = feedback_service._build_guides(session, homework)

    assert [guide.rule for guide in guides] == ["rule1", "rule-missing"]
    assert guides[0].summary == "규칙1"
    assert guides[0].description == "규칙1 상세"
    assert guides[1].summary == "rule-missing"
    assert guides[1].description == "rule-missing"
