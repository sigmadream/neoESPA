from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlmodel import Session, select

from ..core.support_files import resolve_support_dir
from ..models.schemas import (
    CodingRuleGuideItem,
    GradingRule,
    Homework,
    Notice,
    NoticeRead,
    Submission,
    SubmissionFeedbackRead,
    SubmissionResult,
)


class FeedbackService:
    def __init__(self, support_dir: Path | None = None):
        self.support_dir = support_dir or resolve_support_dir(__file__)
        self.week_rules = json.loads(
            (self.support_dir / "week_rules.json").read_text(encoding="utf-8")
        )
        self.pylint_messages = json.loads(
            (self.support_dir / "pylint_message.json").read_text(encoding="utf-8")
        )
        self.lint_manual = json.loads(
            (self.support_dir / "lint_rule_manual.json").read_text(encoding="utf-8")
        )

    def build_submission_feedback(
        self,
        session: Session,
        submission: Submission,
        homework: Homework,
        result: SubmissionResult | None,
    ) -> SubmissionFeedbackRead:
        deadline_status, deadline_message = self._deadline_feedback(homework)
        latest_notice = self._latest_notice(session)
        hints = self._build_hints(
            result, deadline_status, latest_notice, lint_enabled=homework.isLint
        )
        coding_rule_guides = self._build_guides(session, homework)

        return SubmissionFeedbackRead(
            submission_id=submission.id or 0,
            deadline_status=deadline_status,
            deadline_message=deadline_message,
            latest_notice=latest_notice,
            hints=hints,
            coding_rule_guides=coding_rule_guides,
        )

    def _deadline_feedback(self, homework: Homework) -> tuple[str, str]:
        now = datetime.now(UTC)
        deadline_at = self._parse_datetime(homework.deadline)
        start_at = self._parse_datetime(homework.starttime)

        if start_at and now < start_at:
            return "upcoming", "제출 기간이 아직 시작되지 않았습니다."
        if deadline_at and now > deadline_at:
            return "closed", "마감이 지나 추가 제출이 차단된 상태입니다."
        if deadline_at and deadline_at - now <= timedelta(hours=24):
            return "closing_soon", "마감이 24시간 이내로 가까워졌습니다."
        return "open", "현재 제출 가능한 상태입니다."

    def _latest_notice(self, session: Session) -> NoticeRead | None:
        notices = session.exec(select(Notice)).all()
        public_notices = [notice for notice in notices if self._notice_is_visible(notice)]
        if not public_notices:
            return None
        public_notices.sort(key=self._notice_sort_key, reverse=True)
        latest = public_notices[0]
        return NoticeRead(
            num=latest.num or 0,
            title=latest.title,
            author=latest.author,
            content=latest.content,
            date=latest.date,
            is_pinned=latest.is_pinned,
            is_published=latest.is_published,
        )

    def _build_hints(
        self,
        result: SubmissionResult | None,
        deadline_status: str,
        latest_notice: NoticeRead | None,
        *,
        lint_enabled: bool,
    ) -> list[str]:
        hints: list[str] = []

        if result is None or result.status == "pending":
            hints.append("채점 대기 중입니다. 결과가 나오기 전까지 최근 공지를 함께 확인하세요.")
        elif result.compile_status == "failed":
            hints.append("컴파일 오류가 발생했습니다. 파일명, 문법, 함수 시그니처를 다시 확인하세요.")
        elif result.run_status == "timeout":
            hints.append("시간 초과가 발생했습니다. 반복문 종료 조건과 알고리즘 복잡도를 점검하세요.")
        elif result.run_status == "failed":
            hints.append("런타임 오류가 발생했습니다. 입력 처리, 인덱스 범위, 예외 케이스를 확인하세요.")
        elif lint_enabled and result.quality_score < 20:
            hints.append("기능 점수 외에 코드 품질 점수가 낮습니다. 주차별 린트 가이드를 확인하세요.")
        else:
            hints.append("채점은 완료되었습니다. 히든 케이스와 린트 피드백을 바탕으로 다음 제출을 다듬어 보세요.")

        if deadline_status == "closing_soon":
            hints.append("마감이 임박했습니다. 수정 제출이 필요하다면 지금 바로 다시 제출하세요.")
        elif deadline_status == "closed":
            hints.append("이미 마감된 과제이므로 결과 분석과 회고에 집중하는 편이 좋습니다.")

        if latest_notice is not None:
            hints.append(f"최신 공지 '{latest_notice.title}'도 함께 확인하세요.")

        return hints

    def _build_guides(self, session: Session, homework: Homework) -> list[CodingRuleGuideItem]:
        if not homework.isLint:
            return []

        lint_week = self._lint_week(session, homework.num or 0)
        active_rules = self.week_rules.get("pylint", {}).get(str(lint_week), [])
        guides: list[CodingRuleGuideItem] = []
        manual_entries = self.lint_manual.get("pylint", {})

        for rule in active_rules[:6]:
            message_info = self.pylint_messages.get(rule, {})
            manual_info = manual_entries.get(rule, {})
            summary = message_info.get("kor") or message_info.get("eng") or rule
            description = manual_info.get("kor") or manual_info.get("eng") or summary
            guides.append(
                CodingRuleGuideItem(
                    rule=rule,
                    tool="pylint",
                    summary=summary,
                    description=description,
                )
            )

        return guides

    def _lint_week(self, session: Session, homework_num: int) -> str:
        rule = session.exec(
            select(GradingRule)
            .where(
                GradingRule.homework_num == homework_num,
                GradingRule.rule_name == "lint_week",
                GradingRule.is_active.is_(True),
            )
            .order_by(GradingRule.id.desc())
        ).first()
        if rule is None:
            return str(homework_num)
        return rule.rule_value.strip() or str(homework_num)

    def _parse_datetime(self, raw_value: str | None) -> datetime | None:
        if not raw_value:
            return None

        normalized = raw_value.replace(" ", "T")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

    def _notice_is_visible(self, notice: Notice) -> bool:
        if not notice.is_published:
            return False

        publish_at = self._parse_datetime(notice.date)
        if publish_at is None:
            return True
        return publish_at <= datetime.now(UTC)

    def _notice_sort_key(self, notice: Notice) -> tuple[bool, datetime]:
        publish_at = self._parse_datetime(notice.date) or datetime.min.replace(tzinfo=UTC)
        return notice.is_pinned, publish_at
