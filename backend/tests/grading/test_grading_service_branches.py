import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.models.schemas import (
    GradingRule,
    Homework,
    Submission,
    SubmissionCaseResult,
    SubmissionResult,
    User,
)
from app.services.auth_service import AuthService
from app.services.code_runner import (
    CodeRunner,
    PhaseExecutionResult,
    RunnerExecutionResult,
)
from app.services.grading_service import GradingService


engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


class ScriptedRunner(CodeRunner):
    def __init__(self, execution: RunnerExecutionResult):
        self.execution = execution

    def run_code(
        self,
        language: str,
        source_code: str,
        *,
        input_data: str = "",
        source_name: str | None = None,
        timeout_seconds: int = 10,
    ) -> RunnerExecutionResult:
        return self.execution


class PassingRunner(CodeRunner):
    def __init__(self, outputs: dict[str, str]):
        self.outputs = outputs

    def run_code(
        self,
        language: str,
        source_code: str,
        *,
        input_data: str = "",
        source_name: str | None = None,
        timeout_seconds: int = 10,
    ) -> RunnerExecutionResult:
        return _execution(
            status="passed",
            compile_exit=0,
            run_result=PhaseExecutionResult(
                command=["python3", "main.py"],
                stdout=self.outputs.get(input_data, ""),
                stderr="",
                exit_code=0,
                duration_ms=2,
            ),
        )


class FakeLintPipeline:
    def __init__(self, quality_score: float, issues: list | None = None, lint_weight: float = 10.0):
        self.quality_score = quality_score
        self.issues = issues or []
        self.lint_weight = lint_weight
        self.requested_week = None

    def analyze_python_code(self, source_text, *, week, session):
        self.requested_week = week
        return SimpleNamespace(
            quality_score=self.quality_score,
            enabled_issues=self.issues,
            lint_weight=self.lint_weight,
        )


def _execution(
    *,
    status: str,
    compile_exit: int | None = 0,
    compile_timed_out: bool = False,
    compile_stderr: str = "",
    run_result: PhaseExecutionResult | None = None,
) -> RunnerExecutionResult:
    return RunnerExecutionResult(
        language="python",
        source_name="main.py",
        workspace="/tmp/stub",
        compile_result=PhaseExecutionResult(
            command=["python3", "-m", "py_compile", "main.py"],
            stdout="",
            stderr=compile_stderr,
            exit_code=compile_exit,
            duration_ms=1,
            timed_out=compile_timed_out,
        ),
        run_result=run_result,
        status=status,
    )


def _dt_string(offset_days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=offset_days)).strftime("%Y-%m-%d %H:%M:%S")


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def _create_fixtures(
    session: Session,
    homework_num: int,
    *,
    is_lint: bool = False,
    language: str = "python",
    cases: list[dict] | None = None,
    raw_rule_value: str | None = None,
) -> tuple[Homework, Submission]:
    session.add(
        User(
            id="branch-student",
            sid=20246001,
            ps=AuthService.get_password_hash("student-pass"),
            name="branch-student",
            phone="010-0000-0000",
            email="branch-student@example.com",
            user_group="student",
        )
    )
    homework = Homework(
        num=homework_num,
        title="Branch Homework",
        intro="Branch grading",
        starttime=_dt_string(-1),
        deadline=_dt_string(1),
        codeName="main",
        sec=2,
        vitalSpace=False,
        disorderedOutput=False,
        isLint=is_lint,
    )
    session.add(homework)
    submission = Submission(
        homework_num=homework_num,
        user_id="branch-student",
        submission_mode="official",
        attempt_no=1,
        language=language,
        status="pending",
        code_text="print(input())",
        original_filename="answer.py",
    )
    session.add(submission)
    session.commit()
    session.refresh(homework)
    session.refresh(submission)
    session.add(SubmissionResult(submission_id=submission.id or 0))

    if raw_rule_value is not None or cases is not None:
        rule_value = raw_rule_value if raw_rule_value is not None else json.dumps({"cases": cases})
        session.add(
            GradingRule(
                scope="homework",
                homework_num=homework_num,
                rule_name="testcases",
                rule_value=rule_value,
                is_active=True,
            )
        )
    session.commit()
    return homework, submission


DEFAULT_CASES = [
    {"name": "case-1", "input": "1\n", "expected_output": "1\n", "score": 100, "is_hidden": False}
]


def test_compile_failure_marks_submission_failed():
    with Session(engine) as session:
        homework, submission = _create_fixtures(session, 11, cases=DEFAULT_CASES)
        runner = ScriptedRunner(
            _execution(status="compile_error", compile_exit=1, compile_stderr="SyntaxError: bad")
        )

        result = GradingService(runner=runner).grade_submission(session, submission, homework)

    assert submission.status == "failed"
    assert result.status == "failed"
    assert result.compile_status == "failed"
    assert result.run_status == "not_started"
    assert result.total_score == 0.0
    assert result.grader_summary == "Compilation failed."
    assert "SyntaxError" in (result.compile_log or "")


def test_compile_timeout_sets_timeout_compile_status():
    with Session(engine) as session:
        homework, submission = _create_fixtures(session, 12, cases=DEFAULT_CASES)
        runner = ScriptedRunner(
            _execution(status="timeout", compile_exit=None, compile_timed_out=True)
        )

        result = GradingService(runner=runner).grade_submission(session, submission, homework)

    assert result.compile_status == "timeout"
    assert result.run_status == "timeout"
    assert result.grader_summary == "Execution timed out."


def test_runtime_timeout_case_message_and_status():
    with Session(engine) as session:
        homework, submission = _create_fixtures(
            session,
            13,
            cases=[
                {"name": "public-1", "input": "1\n", "expected_output": "1\n", "score": 50, "is_hidden": False},
                {"name": "hidden-1", "input": "2\n", "expected_output": "2\n", "score": 50, "is_hidden": True},
            ],
        )
        runner = ScriptedRunner(
            _execution(
                status="timeout",
                compile_exit=0,
                run_result=PhaseExecutionResult(
                    command=["python3", "main.py"],
                    stdout="",
                    stderr="",
                    exit_code=None,
                    duration_ms=2000,
                    timed_out=True,
                ),
            )
        )

        result = GradingService(runner=runner).grade_submission(session, submission, homework)
        case_results = session.exec(
            select(SubmissionCaseResult)
            .where(SubmissionCaseResult.submission_id == submission.id)
            .order_by(SubmissionCaseResult.case_index)
        ).all()

    assert result.run_status == "timeout"
    assert result.total_score == 0.0
    assert case_results[0].message == "Execution timed out."
    assert case_results[1].message == "Hidden case exceeded the time limit."


def test_runtime_error_case_message_and_status():
    with Session(engine) as session:
        homework, submission = _create_fixtures(
            session,
            14,
            cases=[
                {"name": "public-1", "input": "1\n", "expected_output": "1\n", "score": 50, "is_hidden": False},
                {"name": "hidden-1", "input": "2\n", "expected_output": "2\n", "score": 50, "is_hidden": True},
            ],
        )
        runner = ScriptedRunner(
            _execution(
                status="runtime_error",
                compile_exit=0,
                run_result=PhaseExecutionResult(
                    command=["python3", "main.py"],
                    stdout="",
                    stderr="ZeroDivisionError",
                    exit_code=1,
                    duration_ms=3,
                ),
            )
        )

        result = GradingService(runner=runner).grade_submission(session, submission, homework)
        case_results = session.exec(
            select(SubmissionCaseResult)
            .where(SubmissionCaseResult.submission_id == submission.id)
            .order_by(SubmissionCaseResult.case_index)
        ).all()

    assert result.run_status == "failed"
    assert case_results[0].message == "Runtime error occurred during execution."
    assert case_results[1].message == "Hidden case failed during execution."


def test_apply_execution_result_runtime_error_and_success_fallback():
    service = GradingService(runner=ScriptedRunner(_execution(status="passed")))
    submission = Submission(
        homework_num=1,
        user_id="branch-student",
        submission_mode="official",
        attempt_no=1,
        language="python",
        status="pending",
        code_text="print(1)",
    )
    run_result = PhaseExecutionResult(
        command=["python3", "main.py"], stdout="", stderr="boom", exit_code=1, duration_ms=1
    )

    failed_result = SubmissionResult(submission_id=1)
    service._apply_execution_result(
        submission,
        failed_result,
        _execution(status="runtime_error", run_result=run_result),
    )
    assert failed_result.status == "failed"
    assert failed_result.run_status == "failed"
    assert failed_result.grader_summary == "Execution failed."

    ok_result = SubmissionResult(submission_id=2)
    service._apply_execution_result(
        submission,
        ok_result,
        _execution(
            status="passed",
            run_result=PhaseExecutionResult(
                command=["python3", "main.py"], stdout="ok", stderr="", exit_code=0, duration_ms=1
            ),
        ),
    )
    assert ok_result.status == "graded"
    assert ok_result.total_score == 100.0
    assert ok_result.grader_summary == "Execution completed successfully."


def test_invalid_testcase_configurations_raise():
    service = GradingService(runner=ScriptedRunner(_execution(status="passed")))

    for homework_num, raw_value in (
        (21, "{not-json"),
        (22, json.dumps("scalar")),
        (23, json.dumps({"cases": "not-a-list"})),
        (24, json.dumps({"cases": ["not-a-dict"]})),
    ):
        with Session(engine) as session:
            homework, submission = _create_fixtures(
                session, homework_num, raw_rule_value=raw_value
            )
            try:
                service.grade_submission(session, submission, homework)
                raise AssertionError("Expected invalid testcase configuration to fail")
            except ValueError as error:
                assert "Invalid testcase configuration" in str(error)
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)


def test_cases_without_scores_share_remaining_budget():
    with Session(engine) as session:
        homework, submission = _create_fixtures(
            session,
            25,
            cases=[
                {"name": "scored", "input": "1\n", "expected_output": "1\n", "score": 40},
                {"name": "unscored-1", "input": "2\n", "expected_output": "2\n"},
                {"name": "unscored-2", "input": "3\n", "expected_output": "3\n"},
            ],
        )
        runner = PassingRunner({"1\n": "1\n", "2\n": "2\n", "3\n": "3\n"})

        result = GradingService(runner=runner).grade_submission(session, submission, homework)

    assert result.total_score == 100.0
    assert result.passed_case_count == 3


def test_lint_feedback_applied_above_threshold():
    issues = [
        SimpleNamespace(rule="C0114", message_kor="모듈 docstring 없음", message_eng="Missing docstring")
    ]
    lint_pipeline = FakeLintPipeline(quality_score=7.5, issues=issues)

    with Session(engine) as session:
        homework, submission = _create_fixtures(
            session, 31, is_lint=True, cases=DEFAULT_CASES
        )
        session.add(
            GradingRule(
                scope="homework",
                homework_num=31,
                rule_name="lint_week",
                rule_value="week-03",
                is_active=True,
            )
        )
        session.commit()

        runner = PassingRunner({"1\n": "1\n"})
        result = GradingService(runner=runner, lint_pipeline=lint_pipeline).grade_submission(
            session, submission, homework
        )

    assert lint_pipeline.requested_week == "week-03"
    assert result.quality_score == 7.5
    assert result.total_score == 107.5
    assert "Lint score 7.5" in (result.grader_summary or "")
    assert "Lint findings:" in (result.runtime_log or "")
    assert "모듈 docstring 없음" in (result.runtime_log or "")


def test_lint_feedback_not_applied_at_or_below_threshold():
    lint_pipeline = FakeLintPipeline(quality_score=5.0)

    with Session(engine) as session:
        homework, submission = _create_fixtures(
            session,
            32,
            is_lint=True,
            cases=[
                {"name": "pass", "input": "1\n", "expected_output": "1\n", "score": 80},
                {"name": "fail", "input": "2\n", "expected_output": "2\n", "score": 20},
            ],
        )
        runner = PassingRunner({"1\n": "1\n", "2\n": "wrong\n"})

        result = GradingService(runner=runner, lint_pipeline=lint_pipeline).grade_submission(
            session, submission, homework
        )

    assert result.submission_score == 80.0
    assert result.quality_score == 5.0
    assert result.total_score == 80.0
    assert "Lint was not applied to the total" in (result.grader_summary or "")


def test_lint_feedback_skipped_for_non_python_language():
    lint_pipeline = FakeLintPipeline(quality_score=9.0)

    with Session(engine) as session:
        homework, submission = _create_fixtures(
            session, 33, is_lint=True, language="c", cases=DEFAULT_CASES
        )
        runner = PassingRunner({"1\n": "1\n"})

        result = GradingService(runner=runner, lint_pipeline=lint_pipeline).grade_submission(
            session, submission, homework
        )

    assert lint_pipeline.requested_week is None
    assert result.quality_score == 0.0
    assert result.total_score == 100.0


def test_load_lint_week_defaults_to_homework_number():
    service = GradingService(runner=ScriptedRunner(_execution(status="passed")))

    with Session(engine) as session:
        assert service._load_lint_week(session, 77) == "77"

        session.add(
            GradingRule(
                scope="homework",
                homework_num=77,
                rule_name="lint_week",
                rule_value="   ",
                is_active=True,
            )
        )
        session.commit()
        assert service._load_lint_week(session, 77) == "77"


def test_normalize_output_disordered_and_vital_space_combinations():
    service = GradingService(runner=ScriptedRunner(_execution(status="passed")))
    base = Homework(num=1, title="t", intro="i", codeName="main")

    base.disorderedOutput = True
    base.vitalSpace = True
    assert service._normalize_output(base, "b line\r\na line\n\n") == ["a line", "b line"]

    base.vitalSpace = False
    assert service._normalize_output(base, "b   line\na  line\n") == ["a line", "b line"]

    base.disorderedOutput = False
    base.vitalSpace = True
    assert service._normalize_output(base, " keep  spacing \r\n") == "keep  spacing"

    base.vitalSpace = False
    assert service._normalize_output(base, "1  2\n3\n") == ["1", "2", "3"]


def test_preview_output_truncates_long_output():
    service = GradingService(runner=ScriptedRunner(_execution(status="passed")))
    preview = service._preview_output("x" * 300)
    assert preview.endswith("...")
    assert len(preview) == 123


def test_format_runtime_log_and_merge_logs_empty_paths():
    service = GradingService(runner=ScriptedRunner(_execution(status="passed")))

    assert service._format_runtime_log("case", "", "") is None
    assert "stderr" in (service._format_runtime_log("case", "", "boom") or "")
    assert service._merge_logs(None) is None
    assert (
        service._merge_logs(
            PhaseExecutionResult(command=["true"], stdout="", stderr="", exit_code=0)
        )
        is None
    )
