from datetime import UTC, datetime, timedelta
import json

from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.models.schemas import GradingRule, Homework, Submission, SubmissionResult, SystemSetting, User
from app.services.auth_service import AuthService
from app.services.code_runner import CodeRunner, PhaseExecutionResult, RunnerExecutionResult
from app.services.grading_service import GradingService
from app.services.lint_pipeline import LintPipelineService


engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


class PassingRunner(CodeRunner):
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
            source_name=source_name or "answer.py",
            workspace="/tmp/stub",
            compile_result=PhaseExecutionResult(
                command=["python3", "-m", "py_compile", source_name or "answer.py"],
                exit_code=0,
                duration_ms=1,
            ),
            run_result=PhaseExecutionResult(
                command=["python3", source_name or "answer.py"],
                stdout="ok\n",
                stderr="",
                exit_code=0,
                duration_ms=1,
            ),
            status="passed",
        )


def _dt_string(offset_days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=offset_days)).strftime("%Y-%m-%d %H:%M:%S")


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_python_lint_messages_are_normalized():
    pipeline = LintPipelineService()
    normalized = pipeline.normalize_python_issues(
        [
            {
                "rule": "trailing-whitespace",
                "severity": "convention",
                "message": "There is a trailing whitespace",
                "lineStart": 1,
            },
            {
                "rule": "missing-final-newline",
                "severity": "convention",
                "message": "Please add a blank line at the end of the file",
                "lineStart": 4,
            },
        ],
        week=1,
    )

    assert pipeline.max_line_length == 100
    assert len(normalized) == 2
    assert normalized[0].neo_severity == "style"
    assert normalized[0].message_kor == "라인의 끝에 공백이 있습니다"
    assert normalized[0].enabled_for_week is True
    assert normalized[1].message_kor == "파일의 마지막 줄에는 빈 라인을 추가해 주세요"


def test_lint_penalty_affects_total_score():
    with Session(engine) as session:
        session.add(
            User(
                id="lint-student",
                sid=20245001,
                ps=AuthService.get_password_hash("student-pass"),
                name="lint-student",
                phone="010-0000-0000",
                email="lint-student@example.com",
                user_group="student",
            )
        )
        session.add(
            Homework(
                num=1,
                title="Lint Homework",
                intro="Lint grading",
                starttime=_dt_string(-1),
                deadline=_dt_string(1),
                codeName="answer",
                sec=2,
                isLint=True,
            )
        )
        session.add(
            Submission(
                homework_num=1,
                user_id="lint-student",
                submission_mode="official",
                attempt_no=1,
                language="python",
                status="pending",
                code_text="print('ok')  ",
                original_filename="answer.py",
            )
        )
        session.commit()

        submission = session.exec(select(Submission)).first()
        session.add(SubmissionResult(submission_id=submission.id or 0))
        session.add(SystemSetting(key="lint_calc_weight", value="30", value_type="number"))
        session.add(SystemSetting(key="lint_calc_panalty", value="10", value_type="number"))
        session.add(SystemSetting(key="lint_err_issue", value="1", value_type="number"))
        session.add(SystemSetting(key="lint_err_style", value="1", value_type="number"))
        session.add(SystemSetting(key="lint_err_performance", value="1", value_type="number"))
        session.add(SystemSetting(key="lint_err_information", value="1", value_type="number"))
        session.add(SystemSetting(key="lint_set_default", value="true", value_type="boolean"))
        session.add(
            GradingRule(
                scope="homework",
                homework_num=1,
                rule_name="testcases",
                rule_value=json.dumps(
                    {
                        "cases": [
                            {
                                "name": "print-ok",
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

        homework = session.get(Homework, 1)
        grading_service = GradingService(runner=PassingRunner())
        result = grading_service.grade_submission(session, submission, homework)

    assert result.submission_score == 100.0
    assert result.quality_score == 10.0
    assert result.total_score == 110.0
    assert result.grader_summary is not None
    assert "Lint score 10.0/30" in result.grader_summary
    assert result.runtime_log is not None
    assert "trailing-whitespace" in result.runtime_log


def test_lint_is_saved_but_not_applied_below_threshold():
    with Session(engine) as session:
        session.add(
            User(
                id="lint-threshold",
                sid=20245002,
                ps=AuthService.get_password_hash("student-pass"),
                name="lint-threshold",
                phone="010-0000-0000",
                email="lint-threshold@example.com",
                user_group="student",
            )
        )
        session.add(
            Homework(
                num=2,
                title="Threshold Homework",
                intro="Threshold grading",
                starttime=_dt_string(-1),
                deadline=_dt_string(1),
                codeName="answer",
                sec=2,
                isLint=True,
            )
        )
        session.add(
            Submission(
                homework_num=2,
                user_id="lint-threshold",
                submission_mode="official",
                attempt_no=1,
                language="python",
                status="pending",
                code_text="print('ok')  ",
                original_filename="answer.py",
            )
        )
        session.commit()

        submission = session.exec(select(Submission).where(Submission.homework_num == 2)).first()
        session.add(SubmissionResult(submission_id=submission.id or 0))
        session.add(SystemSetting(key="lint_calc_weight", value="30", value_type="number"))
        session.add(SystemSetting(key="lint_calc_panalty", value="10", value_type="number"))
        session.add(SystemSetting(key="lint_err_issue", value="1", value_type="number"))
        session.add(SystemSetting(key="lint_err_style", value="1", value_type="number"))
        session.add(SystemSetting(key="lint_err_performance", value="1", value_type="number"))
        session.add(SystemSetting(key="lint_err_information", value="1", value_type="number"))
        session.add(SystemSetting(key="lint_set_default", value="true", value_type="boolean"))
        session.add(
            GradingRule(
                scope="homework",
                homework_num=2,
                rule_name="testcases",
                rule_value=json.dumps(
                    {
                        "cases": [
                            {
                                "name": "print-ok",
                                "input": "",
                                "expected_output": "ok\n",
                                "score": 80,
                                "is_hidden": False,
                            }
                        ]
                    }
                ),
                is_active=True,
            )
        )
        session.commit()

        homework = session.get(Homework, 2)
        grading_service = GradingService(runner=PassingRunner())
        result = grading_service.grade_submission(session, submission, homework)

    assert result.submission_score == 80.0
    assert result.quality_score == 10.0
    assert result.total_score == 80.0
    assert result.grader_summary is not None
    assert "Lint was not applied to the total" in result.grader_summary
