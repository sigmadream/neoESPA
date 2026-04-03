from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlmodel import Session, select

from ..models.schemas import PlagiarismPair, PlagiarismPairRead, PlagiarismRun, PlagiarismRunRead, Submission, SubmissionResult


@dataclass
class CandidatePair:
    left: Submission
    right: Submission
    similarity_score: float


class PlagiarismService:
    def __init__(self, threshold: float = 0.95):
        self.threshold = threshold

    def run_for_homework(
        self,
        session: Session,
        *,
        homework_num: int,
        created_by: str,
    ) -> PlagiarismRun:
        latest_submissions = self._latest_submissions(session, homework_num)
        run = PlagiarismRun(
            homework_num=homework_num,
            created_by=created_by,
            status="completed",
            compared_submission_count=len(latest_submissions),
            flagged_pair_count=0,
        )
        session.add(run)
        session.flush()

        candidate_pairs = self._candidate_pairs(latest_submissions)
        flagged_pairs = [
            pair for pair in candidate_pairs if pair.similarity_score >= self.threshold
        ]

        for candidate in flagged_pairs:
            pair = PlagiarismPair(
                run_id=run.id or 0,
                homework_num=homework_num,
                left_submission_id=candidate.left.id or 0,
                right_submission_id=candidate.right.id or 0,
                left_user_id=candidate.left.user_id,
                right_user_id=candidate.right.user_id,
                similarity_score=round(candidate.similarity_score, 4),
                status="flagged",
                summary=(
                    f"Normalized source similarity {round(candidate.similarity_score * 100, 1)}%"
                ),
            )
            session.add(pair)
            self._mark_submission_result(session, candidate.left.id or 0)
            self._mark_submission_result(session, candidate.right.id or 0)

        run.flagged_pair_count = len(flagged_pairs)
        run.summary = (
            f"Compared {len(latest_submissions)} latest submissions and flagged "
            f"{len(flagged_pairs)} pairs."
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run

    def list_pairs(
        self,
        session: Session,
        *,
        homework_num: int | None = None,
    ) -> list[PlagiarismPairRead]:
        statement = select(PlagiarismPair)
        if homework_num is not None:
            statement = statement.where(PlagiarismPair.homework_num == homework_num)
        pairs = session.exec(
            statement.order_by(PlagiarismPair.similarity_score.desc(), PlagiarismPair.id.desc())
        ).all()
        return [self.to_pair_read(session, pair) for pair in pairs]

    def get_pair(self, session: Session, pair_id: int) -> PlagiarismPairRead | None:
        pair = session.get(PlagiarismPair, pair_id)
        if pair is None:
            return None
        return self.to_pair_read(session, pair, include_code=True)

    def list_runs(self, session: Session) -> list[PlagiarismRunRead]:
        runs = session.exec(
            select(PlagiarismRun).order_by(PlagiarismRun.created_at.desc(), PlagiarismRun.id.desc())
        ).all()
        return [self.to_run_read(run) for run in runs]

    def to_run_read(self, run: PlagiarismRun) -> PlagiarismRunRead:
        return PlagiarismRunRead(
            id=run.id or 0,
            homework_num=run.homework_num,
            created_by=run.created_by,
            status=run.status,
            compared_submission_count=run.compared_submission_count,
            flagged_pair_count=run.flagged_pair_count,
            summary=run.summary,
            created_at=run.created_at,
        )

    def to_pair_read(
        self,
        session: Session,
        pair: PlagiarismPair,
        *,
        include_code: bool = False,
    ) -> PlagiarismPairRead:
        left_submission = session.get(Submission, pair.left_submission_id)
        right_submission = session.get(Submission, pair.right_submission_id)
        return PlagiarismPairRead(
            id=pair.id or 0,
            run_id=pair.run_id,
            homework_num=pair.homework_num,
            left_submission_id=pair.left_submission_id,
            right_submission_id=pair.right_submission_id,
            left_user_id=pair.left_user_id,
            right_user_id=pair.right_user_id,
            similarity_score=pair.similarity_score,
            status=pair.status,
            summary=pair.summary,
            left_code=left_submission.code_text if include_code and left_submission is not None else None,
            right_code=right_submission.code_text if include_code and right_submission is not None else None,
            created_at=pair.created_at,
        )

    def _mark_submission_result(self, session: Session, submission_id: int) -> None:
        result = session.exec(
            select(SubmissionResult).where(SubmissionResult.submission_id == submission_id)
        ).first()
        if result is None:
            result = SubmissionResult(submission_id=submission_id)
        result.plagiarism_flag = True
        session.add(result)

    def _latest_submissions(self, session: Session, homework_num: int) -> list[Submission]:
        submissions = session.exec(
            select(Submission)
            .where(
                Submission.homework_num == homework_num,
                Submission.submission_mode == "official",
            )
            .order_by(Submission.user_id, Submission.submitted_at.desc(), Submission.id.desc())
        ).all()

        latest_by_user: dict[str, Submission] = {}
        for submission in submissions:
            if not submission.code_text or not submission.code_text.strip():
                continue
            latest_by_user.setdefault(submission.user_id, submission)
        return list(latest_by_user.values())

    def _candidate_pairs(self, submissions: list[Submission]) -> list[CandidatePair]:
        pairs: list[CandidatePair] = []
        for index, left_submission in enumerate(submissions):
            for right_submission in submissions[index + 1 :]:
                left_code = self._normalize_source(left_submission.code_text or "")
                right_code = self._normalize_source(right_submission.code_text or "")
                if not left_code or not right_code:
                    continue
                similarity = SequenceMatcher(None, left_code, right_code).ratio()
                pairs.append(
                    CandidatePair(
                        left=left_submission,
                        right=right_submission,
                        similarity_score=similarity,
                    )
                )
        return pairs

    def _normalize_source(self, source: str) -> str:
        normalized_lines: list[str] = []
        for raw_line in source.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#") or line.startswith("//"):
                continue
            normalized_lines.append("".join(line.split()))
        return "".join(normalized_lines)
