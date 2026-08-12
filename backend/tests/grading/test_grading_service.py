import json
from datetime import UTC, datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st
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
from app.services.grading_service import GradingService, MISSING_TESTCASES_ERROR


engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


class StubRunner(CodeRunner):
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
        return RunnerExecutionResult(
            language=language,
            source_name=source_name or "main.py",
            workspace="/tmp/stub",
            compile_result=PhaseExecutionResult(
                command=["python3", "-m", "py_compile", source_name or "main.py"],
                exit_code=0,
                duration_ms=1,
            ),
            run_result=PhaseExecutionResult(
                command=["python3", source_name or "main.py"],
                stdout=self.outputs.get(input_data, ""),
                stderr="",
                exit_code=0,
                duration_ms=2,
            ),
            status="passed",
        )


def _dt_string(offset_days: int, offset_hours: int = 0) -> str:
    return (
        datetime.now(UTC) + timedelta(days=offset_days, hours=offset_hours)
    ).strftime("%Y-%m-%d %H:%M:%S")


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def _create_user(session: Session) -> None:
    session.add(
        User(
            id="student-case",
            sid=20244001,
            ps=AuthService.get_password_hash("student-pass"),
            name="student-case",
            phone="010-0000-0000",
            email="student-case@example.com",
            user_group="student",
        )
    )
    session.commit()


def _create_homework(session: Session, homework_num: int) -> Homework:
    homework = Homework(
        num=homework_num,
        title="Case Homework",
        intro="Case grading",
        starttime=_dt_string(-1),
        deadline=_dt_string(1),
        codeName="main",
        sec=2,
        vitalSpace=False,
        disorderedOutput=False,
    )
    session.add(homework)
    session.commit()
    session.refresh(homework)
    return homework


def _create_submission(session: Session, homework_num: int) -> Submission:
    submission = Submission(
        homework_num=homework_num,
        user_id="student-case",
        submission_mode="official",
        attempt_no=1,
        language="python",
        status="pending",
        code_text="print(input())",
        original_filename="answer.py",
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)
    session.add(SubmissionResult(submission_id=submission.id or 0))
    session.commit()
    return submission


def _create_testcase_rule(session: Session, homework_num: int, cases: list[dict]) -> None:
    session.add(
        GradingRule(
            scope="homework",
            homework_num=homework_num,
            rule_name="testcases",
            rule_value=json.dumps({"cases": cases}),
            is_active=True,
        )
    )
    session.commit()


def test_score_is_calculated_from_test_results():
    with Session(engine) as session:
        _create_user(session)
        homework = _create_homework(session, 1)
        submission = _create_submission(session, 1)
        _create_testcase_rule(
            session,
            1,
            [
                {
                    "name": "public-1",
                    "input": "2\n",
                    "expected_output": "2\n",
                    "score": 40,
                    "is_hidden": False,
                },
                {
                    "name": "hidden-1",
                    "input": "5\n",
                    "expected_output": "25\n",
                    "score": 60,
                    "is_hidden": True,
                },
            ],
        )

        grading_service = GradingService(
            runner=StubRunner({"2\n": "2\n", "5\n": "10\n"})
        )
        result = grading_service.grade_submission(session, submission, homework)
        stored_case_results = session.exec(
            select(SubmissionCaseResult)
            .where(SubmissionCaseResult.submission_id == submission.id)
            .order_by(SubmissionCaseResult.case_index)
        ).all()

    assert result.status == "graded"
    assert result.total_score == 40.0
    assert result.submission_score == 40.0
    assert result.passed_case_count == 1
    assert result.total_case_count == 2
    assert len(stored_case_results) == 2
    assert stored_case_results[0].passed is True
    assert stored_case_results[0].score_awarded == 40.0
    assert stored_case_results[1].passed is False
    assert stored_case_results[1].score_awarded == 0.0


def test_hidden_cases_do_not_leak_expected_output():
    with Session(engine) as session:
        _create_user(session)
        homework = _create_homework(session, 2)
        submission = _create_submission(session, 2)
        _create_testcase_rule(
            session,
            2,
            [
                {
                    "name": "hidden-secret",
                    "input": "secret\n",
                    "expected_output": "top-secret-answer\n",
                    "score": 100,
                    "is_hidden": True,
                }
            ],
        )

        grading_service = GradingService(
            runner=StubRunner({"secret\n": "wrong-output\n"})
        )
        grading_service.grade_submission(session, submission, homework)
        stored_case_result = session.exec(
            select(SubmissionCaseResult).where(
                SubmissionCaseResult.submission_id == submission.id
            )
        ).first()

    assert stored_case_result is not None
    assert stored_case_result.message == "Hidden case failed."
    assert "top-secret-answer" not in stored_case_result.message


def test_grading_requires_active_testcases():
    with Session(engine) as session:
        _create_user(session)
        homework = _create_homework(session, 3)
        submission = _create_submission(session, 3)

        grading_service = GradingService(runner=StubRunner({}))

        try:
            grading_service.grade_submission(session, submission, homework)
            assert False, "Expected grading without testcases to fail"
        except ValueError as error:
            assert str(error) == MISSING_TESTCASES_ERROR


@settings(max_examples=20, deadline=None)
@given(
    case_scores=st.lists(
        st.integers(min_value=1, max_value=40),
        min_size=1,
        max_size=5,
    ),
    passed_cases=st.lists(
        st.booleans(),
        min_size=1,
        max_size=5,
    ),
)
def test_grading_score_stays_within_case_bounds(case_scores: list[int], passed_cases: list[bool]):
    case_count = min(len(case_scores), len(passed_cases))
    case_scores = case_scores[:case_count]
    passed_cases = passed_cases[:case_count]

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        _create_user(session)
        homework = _create_homework(session, 4)
        submission = _create_submission(session, 4)

        cases = []
        runner_outputs = {}
        for index, (score, should_pass) in enumerate(
            zip(case_scores, passed_cases, strict=True),
            start=1,
        ):
            case_input = f"input-{index}\n"
            expected_output = f"expected-{index}\n"
            cases.append(
                {
                    "name": f"case-{index}",
                    "input": case_input,
                    "expected_output": expected_output,
                    "score": score,
                    "is_hidden": False,
                }
            )
            runner_outputs[case_input] = expected_output if should_pass else f"wrong-{index}\n"

        _create_testcase_rule(session, 4, cases)

        grading_service = GradingService(runner=StubRunner(runner_outputs))
        result = grading_service.grade_submission(session, submission, homework)

    expected_score = float(
        sum(score for score, should_pass in zip(case_scores, passed_cases, strict=True) if should_pass)
    )
    max_score = float(sum(case_scores))

    assert result.total_score == expected_score
    assert result.submission_score == expected_score
    assert result.passed_case_count == sum(passed_cases)
    assert result.total_case_count == case_count
    assert 0.0 <= result.total_score <= max_score
    assert result.submission_score <= max_score
