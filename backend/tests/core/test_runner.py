import pytest
from app.services.code_runner import (
    CodeRunnerService,
    UnsafeExecutionDisabledError,
    UnsupportedLanguageError,
)


@pytest.fixture(autouse=True)
def enable_development_runner(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTO_GRADING_ENABLED", "true")


def test_runner_blocks_unsupported_language():
    runner = CodeRunnerService()
    with pytest.raises(UnsupportedLanguageError):
        runner.run_code("ruby", "puts 'hello'")


def test_runner_enforces_timeout():
    runner = CodeRunnerService()
    result = runner.run_code(
        "python",
        "while True:\n    pass\n",
        timeout_seconds=1,
    )
    assert result.status == "timeout"
    assert result.timed_out is True


def test_python_success_execution():
    runner = CodeRunnerService()
    code = "print('hello world')"
    result = runner.run_code("python", code)

    assert result.status == "passed"
    assert result.run_result.stdout.strip() == "hello world"
    assert result.run_result.exit_code == 0


def test_python_compile_error():
    runner = CodeRunnerService()
    # 파이썬은 py_compile로 컴파일 에러를 확인하도록 구현됨
    code = "if True\n    print('missing colon')"
    result = runner.run_code("python", code)

    assert result.status == "compile_error"
    assert result.compile_result.succeeded is False


def test_python_runtime_error():
    runner = CodeRunnerService()
    code = "raise ValueError('error')"
    result = runner.run_code("python", code)

    assert result.status == "runtime_error"
    assert result.run_result.exit_code != 0
    assert "ValueError" in result.run_result.stderr


def test_python_input_handling():
    runner = CodeRunnerService()
    code = "val = input(); print(f'got {val}')"
    result = runner.run_code("python", code, input_data="test-input")

    assert result.status == "passed"
    assert result.run_result.stdout.strip() == "got test-input"


def test_runner_cannot_execute_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTO_GRADING_ENABLED", "true")

    with pytest.raises(
        UnsafeExecutionDisabledError, match="Host code execution is disabled"
    ):
        CodeRunnerService().run_code("python", "print('must not run')")
