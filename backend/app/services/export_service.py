from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

from sqlmodel import Session, select

from ..core.compression import decompress_text
from ..models.schemas import Homework, Submission, SubmissionResult, User

DEFAULT_SOURCE_NAMES = {
    "c": "main.c",
    "cpp": "main.cpp",
    "python": "main.py",
    "java": "Main.java",
}


class ExportService:
    def build_grade_csv(self, session: Session, homework: Homework) -> bytes:
        students = session.exec(select(User).order_by(User.sid, User.id)).all()
        latest_submissions = self._latest_submission_by_user(
            session,
            homework.num or 0,
        )
        submission_results = self._submission_results(
            session,
            list(latest_submissions.values()),
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "sid",
                "user_id",
                "name",
                "email",
                "homework_num",
                "homework_title",
                "submission_id",
                "attempt_no",
                "status",
                "total_score",
                "submission_score",
                "quality_score",
                "manual_total_score",
                "compile_status",
                "run_status",
                "submitted_at",
            ]
        )

        included_user_ids: set[str] = set()
        for user in students:
            if user.user_group != "student" and user.id not in latest_submissions:
                continue

            submission = latest_submissions.get(user.id)
            result = submission_results.get(submission.id or 0) if submission is not None else None
            writer.writerow(
                [
                    user.sid,
                    user.id,
                    user.name,
                    user.email,
                    homework.num or 0,
                    homework.title,
                    submission.id if submission is not None else "",
                    submission.attempt_no if submission is not None else "",
                    submission.status if submission is not None else "missing",
                    self._effective_total_score(result),
                    result.submission_score if result is not None else "",
                    result.quality_score if result is not None else "",
                    result.manual_total_score if result is not None and result.manual_total_score is not None else "",
                    result.compile_status if result is not None else "",
                    result.run_status if result is not None else "",
                    submission.submitted_at.isoformat() if submission is not None else "",
                ]
            )
            included_user_ids.add(user.id)

        for user_id, submission in latest_submissions.items():
            if user_id in included_user_ids:
                continue
            user = session.get(User, user_id)
            if user is None:
                continue
            result = submission_results.get(submission.id or 0)
            writer.writerow(
                [
                    user.sid,
                    user.id,
                    user.name,
                    user.email,
                    homework.num or 0,
                    homework.title,
                    submission.id or "",
                    submission.attempt_no,
                    submission.status,
                    self._effective_total_score(result),
                    result.submission_score if result is not None else "",
                    result.quality_score if result is not None else "",
                    result.manual_total_score if result is not None and result.manual_total_score is not None else "",
                    result.compile_status if result is not None else "",
                    result.run_status if result is not None else "",
                    submission.submitted_at.isoformat(),
                ]
            )

        return output.getvalue().encode("utf-8")

    def build_latest_submission_archive(self, session: Session, homework: Homework) -> bytes:
        latest_submissions = self._latest_submission_by_user(session, homework.num or 0)
        archive_buffer = io.BytesIO()

        with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for user_id in sorted(latest_submissions):
                submission = latest_submissions[user_id]
                source_text = decompress_text(submission.code_text or "")
                if not source_text.strip():
                    continue

                user = session.get(User, user_id)
                if user is None:
                    continue

                source_name = submission.original_filename or DEFAULT_SOURCE_NAMES.get(
                    submission.language,
                    "main.txt",
                )
                safe_source_name = Path(source_name).name
                archive_path = (
                    f"homework_{homework.num}/{user.sid}_{user.id}/"
                    f"attempt_{submission.attempt_no}_{safe_source_name}"
                )
                archive.writestr(archive_path, source_text)

        return archive_buffer.getvalue()

    def _latest_submission_by_user(
        self,
        session: Session,
        homework_num: int,
    ) -> dict[str, Submission]:
        submissions = session.exec(
            select(Submission)
            .where(
                Submission.homework_num == homework_num,
                Submission.submission_mode == "official",
            )
            .order_by(
                Submission.user_id,
                Submission.submitted_at.desc(),
                Submission.id.desc(),
            )
        ).all()

        latest_submissions: dict[str, Submission] = {}
        for submission in submissions:
            latest_submissions.setdefault(submission.user_id, submission)
        return latest_submissions

    def _submission_results(
        self,
        session: Session,
        submissions: list[Submission],
    ) -> dict[int, SubmissionResult]:
        submission_ids = [submission.id for submission in submissions if submission.id is not None]
        if not submission_ids:
            return {}

        results = session.exec(
            select(SubmissionResult).where(SubmissionResult.submission_id.in_(submission_ids))
        ).all()
        return {result.submission_id: result for result in results}

    def _effective_total_score(self, result: SubmissionResult | None) -> float | str:
        if result is None:
            return ""
        if result.manual_total_score is not None:
            return result.manual_total_score
        return result.total_score
