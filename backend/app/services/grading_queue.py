from __future__ import annotations

from collections import deque
from datetime import UTC, datetime

from sqlmodel import Session, select

from ..models.schemas import Homework, Submission, SubmissionResult
from .grading_service import GradingService


class GradingQueueService:
    def __init__(self, grading_service: GradingService | None = None):
        self.grading_service = grading_service or GradingService()
        self._queue: deque[int] = deque()
        self._enqueued_submission_ids: set[int] = set()

    def enqueue(self, session: Session, submission_id: int) -> Submission:
        submission = session.get(Submission, submission_id)
        if submission is None:
            raise ValueError("Submission not found")

        result = self._get_or_create_result(session, submission_id)
        submission.status = "pending"
        result.status = "pending"
        result.compile_status = "not_started"
        result.run_status = "not_started"
        result.total_score = 0.0
        result.submission_score = 0.0
        result.quality_score = 0.0
        result.exit_code = None
        result.runtime_ms = None
        result.compile_log = None
        result.runtime_log = None
        result.manual_total_score = None
        result.adjustment_note = None
        result.adjusted_at = None
        result.adjusted_by = None
        result.grader_summary = "Submission queued for grading."
        result.graded_at = None

        if submission_id not in self._enqueued_submission_ids:
            self._queue.append(submission_id)
            self._enqueued_submission_ids.add(submission_id)

        session.add(submission)
        session.add(result)
        session.commit()
        session.refresh(submission)
        return submission

    def process_next(self, session: Session) -> Submission | None:
        while True:
            if self._queue:
                submission_id = self._queue.popleft()
                self._enqueued_submission_ids.discard(submission_id)
            else:
                # The in-memory queue is lost on restart while statuses stay
                # "pending" in the DB — fall back to the oldest pending row.
                submission_id = session.exec(
                    select(Submission.id)
                    .where(Submission.status == "pending")
                    .order_by(Submission.id)
                ).first()
                if submission_id is None:
                    return None

            submission = session.get(Submission, submission_id)
            if submission is None:
                continue

            result = self._get_or_create_result(session, submission_id)
            submission.status = "grading"
            result.status = "grading"
            result.grader_summary = "Submission is being graded."
            session.add(submission)
            session.add(result)
            session.commit()

            try:
                homework = session.get(Homework, submission.homework_num)
                if homework is None:
                    raise ValueError("Homework not found")
                self.grading_service.grade_submission(session, submission, homework)
            except Exception as error:
                session.rollback()
                submission = session.get(Submission, submission_id)
                if submission is None:
                    continue
                result = self._get_or_create_result(session, submission_id)
                submission.status = "retryable"
                result.status = "retryable"
                result.grader_summary = f"Queue processing failed: {error}"
                result.graded_at = datetime.now(UTC)
                session.add(submission)
                session.add(result)
                session.commit()
            else:
                session.refresh(submission)

            return submission

        return None

    def snapshot(self) -> tuple[int, list[int]]:
        return len(self._queue), list(self._queue)

    def _get_or_create_result(self, session: Session, submission_id: int) -> SubmissionResult:
        result = session.exec(
            select(SubmissionResult).where(SubmissionResult.submission_id == submission_id)
        ).first()
        if result is not None:
            return result

        result = SubmissionResult(submission_id=submission_id)
        session.add(result)
        session.flush()
        return result
