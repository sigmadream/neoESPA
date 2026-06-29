from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, select

from ..models.schemas import (
    GradingRule,
    Homework,
    Submission,
    SubmissionCaseResult,
    SubmissionResult,
)
from ..core.compression import decompress_text
from .code_runner import CodeRunner, CodeRunnerService, RunnerExecutionResult
from .lint_pipeline import LintPipelineService

MISSING_TESTCASES_ERROR = "Homework has no active test cases configured"
LINT_APPLICATION_THRESHOLD = 80.0
LINT_APPLICATION_THRESHOLD_LABEL = int(LINT_APPLICATION_THRESHOLD)


@dataclass
class HomeworkTestCase:
    case_index: int
    case_name: str
    input_data: str
    expected_output: str
    is_hidden: bool = False
    score: float = 0.0


class GradingService:
    def __init__(
        self,
        runner: CodeRunner | None = None,
        lint_pipeline: LintPipelineService | None = None,
    ):
        self.runner = runner or CodeRunnerService()
        self.lint_pipeline = lint_pipeline or LintPipelineService()

    def grade_submission(
        self,
        session: Session,
        submission: Submission,
        homework: Homework | None = None,
    ) -> SubmissionResult:
        source_text = decompress_text(submission.code_text or "")
        if not source_text.strip():
            raise ValueError("Submission does not contain executable source code")

        resolved_homework = homework or session.get(Homework, submission.homework_num)
        if resolved_homework is None:
            raise ValueError("Homework not found for submission")

        with session.begin_nested():
            result = session.exec(
                select(SubmissionResult).where(SubmissionResult.submission_id == submission.id)
            ).first()
            if result is None:
                result = SubmissionResult(submission_id=submission.id or 0)

            result.manual_total_score = None
            result.adjustment_note = None
            result.adjusted_at = None
            result.adjusted_by = None

            test_cases = self._load_test_cases(session, resolved_homework.num or 0)
            if not test_cases:
                raise ValueError(MISSING_TESTCASES_ERROR)

            self._clear_case_results(session, submission.id or 0)
            self._grade_with_test_cases(
                session,
                submission,
                result,
                resolved_homework,
                test_cases,
            )

            self._apply_lint_feedback(session, submission, result, resolved_homework)
            session.add(submission)
            session.add(result)
            session.flush()

        session.commit()
        session.refresh(result)
        session.refresh(submission)
        return result

    def _grade_with_test_cases(
        self,
        session: Session,
        submission: Submission,
        result: SubmissionResult,
        homework: Homework,
        test_cases: list[HomeworkTestCase],
    ) -> None:
        compile_logs: list[str] = []
        runtime_logs: list[str] = []
        runtime_ms_total = 0
        passed_case_count = 0
        total_score = 0.0
        run_status = "passed"
        last_exit_code = 0
        source_text = decompress_text(submission.code_text or "")
        for test_case in test_cases:
            execution = self.runner.run_code(
                submission.language,
                source_text,
                input_data=test_case.input_data,
                source_name=submission.original_filename,
                timeout_seconds=homework.sec or 10,
            )

            compile_result = execution.compile_result
            if compile_result is None:
                raise ValueError("Runner returned no compile result")

            compile_log = self._merge_logs(compile_result)
            if compile_log:
                compile_logs.append(f"[{test_case.case_name}] {compile_log}")

            if not compile_result.succeeded:
                self._apply_execution_result(submission, result, execution)
                result.total_case_count = len(test_cases)
                result.passed_case_count = 0
                return

            run_result = execution.run_result
            if run_result is None:
                raise ValueError("Runner returned no runtime result")

            runtime_ms_total += run_result.duration_ms
            last_exit_code = run_result.exit_code if run_result.exit_code is not None else last_exit_code

            runtime_log = self._format_runtime_log(test_case.case_name, run_result.stdout, run_result.stderr)
            if runtime_log:
                runtime_logs.append(runtime_log)

            case_passed, case_message = self._evaluate_case(homework, test_case, execution)
            case_score = test_case.score if case_passed else 0.0

            session.add(
                SubmissionCaseResult(
                    submission_id=submission.id or 0,
                    case_index=test_case.case_index,
                    case_name=test_case.case_name,
                    is_hidden=test_case.is_hidden,
                    passed=case_passed,
                    score_awarded=case_score,
                    runtime_ms=run_result.duration_ms,
                    message=case_message,
                )
            )

            if case_passed:
                passed_case_count += 1
                total_score += case_score
                continue

            if execution.status == "timeout":
                run_status = "timeout"
            elif execution.status == "runtime_error" and run_status != "timeout":
                run_status = "failed"

        submission.status = "graded"
        result.status = "graded"
        result.compile_status = "passed"
        result.run_status = run_status
        result.total_case_count = len(test_cases)
        result.passed_case_count = passed_case_count
        result.total_score = round(total_score, 2)
        result.submission_score = round(total_score, 2)
        result.quality_score = 0.0
        result.exit_code = last_exit_code
        result.runtime_ms = runtime_ms_total
        result.compile_log = "\n\n".join(compile_logs) if compile_logs else None
        result.runtime_log = "\n\n".join(runtime_logs) if runtime_logs else None
        result.grader_summary = (
            f"Passed {passed_case_count}/{len(test_cases)} test cases."
        )
        result.graded_at = datetime.now(UTC)

    def _apply_execution_result(
        self,
        submission: Submission,
        result: SubmissionResult,
        execution: RunnerExecutionResult,
    ) -> None:
        compile_result = execution.compile_result
        run_result = execution.run_result

        result.compile_log = self._merge_logs(compile_result)
        result.runtime_log = self._merge_logs(run_result)
        result.graded_at = datetime.now(UTC)
        result.runtime_ms = run_result.duration_ms if run_result is not None else None
        result.total_case_count = 0
        result.passed_case_count = 0

        if compile_result is not None:
            if compile_result.timed_out:
                result.compile_status = "timeout"
            elif compile_result.succeeded:
                result.compile_status = "passed"
            else:
                result.compile_status = "failed"

        if execution.status == "compile_error":
            submission.status = "failed"
            result.status = "failed"
            result.run_status = "not_started"
            result.exit_code = compile_result.exit_code if compile_result is not None else None
            result.total_score = 0.0
            result.submission_score = 0.0
            result.quality_score = 0.0
            result.grader_summary = "Compilation failed."
            return

        if execution.status == "timeout":
            submission.status = "failed"
            result.status = "failed"
            result.run_status = "timeout"
            result.exit_code = run_result.exit_code if run_result is not None else None
            result.total_score = 0.0
            result.submission_score = 0.0
            result.quality_score = 0.0
            result.grader_summary = "Execution timed out."
            return

        if execution.status == "runtime_error":
            submission.status = "failed"
            result.status = "failed"
            result.run_status = "failed"
            result.exit_code = run_result.exit_code if run_result is not None else None
            result.total_score = 0.0
            result.submission_score = 0.0
            result.quality_score = 0.0
            result.grader_summary = "Execution failed."
            return

        submission.status = "graded"
        result.status = "graded"
        result.run_status = "passed"
        result.exit_code = run_result.exit_code if run_result is not None else 0
        result.total_score = 100.0
        result.submission_score = 100.0
        result.quality_score = 0.0
        result.grader_summary = "Execution completed successfully."

    def _apply_lint_feedback(
        self,
        session: Session,
        submission: Submission,
        result: SubmissionResult,
        homework: Homework,
    ) -> None:
        if not homework.isLint:
            return
        if submission.language != "python":
            return
        source_text = decompress_text(submission.code_text or "")
        if not source_text.strip():
            return
        if result.status != "graded" or result.compile_status != "passed":
            return

        lint_week = self._load_lint_week(session, homework.num or 0)
        lint_report = self.lint_pipeline.analyze_python_code(
            source_text,
            week=lint_week,
            session=session,
        )
        functional_score = round(result.submission_score, 2)
        result.quality_score = round(lint_report.quality_score, 2)
        lint_applied_to_total = functional_score > LINT_APPLICATION_THRESHOLD
        result.total_score = round(
            functional_score + result.quality_score,
            2,
        ) if lint_applied_to_total else functional_score

        lint_summary_lines = []
        for issue in lint_report.enabled_issues[:5]:
            lint_summary_lines.append(
                f"- {issue.rule}: {issue.message_kor or issue.message_eng}"
            )

        lint_summary = (
            f"Lint score {result.quality_score}/{int(lint_report.lint_weight)} "
            f"after {len(lint_report.enabled_issues)} active issues."
        )
        score_summary = (
            f"Functional score {functional_score}/100. "
            f"Total score {result.total_score}."
        )
        if not lint_applied_to_total:
            score_summary = (
                f"{score_summary} Lint was not applied to the total because the "
                f"functional score is {LINT_APPLICATION_THRESHOLD_LABEL} or below."
            )

        if lint_summary_lines:
            lint_log_block = "Lint findings:\n" + "\n".join(lint_summary_lines)
            if result.runtime_log:
                result.runtime_log = f"{result.runtime_log}\n\n{lint_log_block}"
            else:
                result.runtime_log = lint_log_block

        if result.grader_summary:
            result.grader_summary = (
                f"{result.grader_summary} {score_summary} {lint_summary}"
            )
        else:
            result.grader_summary = f"{score_summary} {lint_summary}"

    def _load_test_cases(
        self,
        session: Session,
        homework_num: int,
    ) -> list[HomeworkTestCase]:
        rule = session.exec(
            select(GradingRule)
            .where(
                GradingRule.homework_num == homework_num,
                GradingRule.rule_name == "testcases",
                GradingRule.is_active.is_(True),
            )
            .order_by(GradingRule.id.desc())
        ).first()
        if rule is None:
            return []

        try:
            parsed = json.loads(rule.rule_value)
        except json.JSONDecodeError as error:
            raise ValueError("Invalid testcase configuration") from error

        if isinstance(parsed, dict):
            raw_cases = parsed.get("cases", [])
        elif isinstance(parsed, list):
            raw_cases = parsed
        else:
            raise ValueError("Invalid testcase configuration")

        if not isinstance(raw_cases, list):
            raise ValueError("Invalid testcase configuration")

        test_cases: list[HomeworkTestCase] = []
        explicit_scores = all(
            isinstance(item, dict) and "score" in item for item in raw_cases
        )
        default_score = 100.0 / len(raw_cases) if raw_cases and not explicit_scores else 0.0

        for index, raw_case in enumerate(raw_cases, start=1):
            if not isinstance(raw_case, dict):
                raise ValueError("Invalid testcase configuration")

            test_cases.append(
                HomeworkTestCase(
                    case_index=index,
                    case_name=str(raw_case.get("name", f"case-{index}")),
                    input_data=str(raw_case.get("input", "")),
                    expected_output=str(raw_case.get("expected_output", "")),
                    is_hidden=bool(raw_case.get("is_hidden", False)),
                    score=float(raw_case.get("score", default_score)),
                )
            )

        return test_cases

    def _load_lint_week(self, session: Session, homework_num: int) -> str:
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

    def _evaluate_case(
        self,
        homework: Homework,
        test_case: HomeworkTestCase,
        execution: RunnerExecutionResult,
    ) -> tuple[bool, str]:
        run_result = execution.run_result
        if run_result is None:
            return False, "Execution result missing."

        if execution.status == "timeout":
            if test_case.is_hidden:
                return False, "Hidden case exceeded the time limit."
            return False, "Execution timed out."

        if execution.status == "runtime_error":
            if test_case.is_hidden:
                return False, "Hidden case failed during execution."
            return False, "Runtime error occurred during execution."

        actual_output = run_result.stdout
        expected_output = test_case.expected_output

        if self._outputs_match(homework, actual_output, expected_output):
            return True, "Passed."

        if test_case.is_hidden:
            return False, "Hidden case failed."

        return (
            False,
            f"Expected {self._preview_output(expected_output)!r} but got {self._preview_output(actual_output)!r}.",
        )

    def _outputs_match(
        self,
        homework: Homework,
        actual_output: str,
        expected_output: str,
    ) -> bool:
        return self._normalize_output(homework, actual_output) == self._normalize_output(
            homework,
            expected_output,
        )

    def _normalize_output(self, homework: Homework, raw_output: str) -> Any:
        normalized = raw_output.replace("\r\n", "\n").strip()

        if homework.disorderedOutput:
            if homework.vitalSpace:
                return sorted(
                    [line for line in normalized.splitlines() if line]
                )
            return sorted(
                [" ".join(line.split()) for line in normalized.splitlines() if line.strip()]
            )

        if homework.vitalSpace:
            return normalized

        return normalized.split()

    def _preview_output(self, raw_output: str, limit: int = 120) -> str:
        compact = raw_output.replace("\r\n", "\n").strip()
        if len(compact) <= limit:
            return compact
        return f"{compact[:limit]}..."

    def _format_runtime_log(self, case_name: str, stdout: str, stderr: str) -> str | None:
        parts: list[str] = []
        if stdout:
            parts.append(f"[{case_name}] stdout:\n{stdout}")
        if stderr:
            parts.append(f"[{case_name}] stderr:\n{stderr}")
        if not parts:
            return None
        return "\n".join(parts)

    def _clear_case_results(self, session: Session, submission_id: int) -> None:
        existing_case_results = session.exec(
            select(SubmissionCaseResult).where(
                SubmissionCaseResult.submission_id == submission_id
            )
        ).all()
        for case_result in existing_case_results:
            session.delete(case_result)
        session.flush()

    def _merge_logs(self, phase_result) -> str | None:
        if phase_result is None:
            return None

        parts = [part for part in (phase_result.stdout, phase_result.stderr) if part]
        if not parts:
            return None
        return "\n".join(parts)
