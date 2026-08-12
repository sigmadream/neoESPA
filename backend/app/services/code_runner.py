from __future__ import annotations

import os
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ..core.config import settings
from .sandbox import NsJailLimits, NsJailSandboxRunner


SUPPORTED_LANGUAGES = ("c", "cpp", "python", "java")


class UnsupportedLanguageError(ValueError):
    pass


class UnsafeExecutionDisabledError(RuntimeError):
    pass


@dataclass
class PhaseExecutionResult:
    command: list[str]
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: int = 0
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return not self.timed_out and self.exit_code == 0


@dataclass
class RunnerExecutionResult:
    language: str
    source_name: str
    workspace: str
    compile_result: PhaseExecutionResult | None
    run_result: PhaseExecutionResult | None
    status: str

    @property
    def timed_out(self) -> bool:
        return (
            (self.compile_result is not None and self.compile_result.timed_out)
            or (self.run_result is not None and self.run_result.timed_out)
        )


class CodeRunner(ABC):
    @abstractmethod
    def run_code(
        self,
        language: str,
        source_code: str,
        *,
        input_data: str = "",
        source_name: str | None = None,
        timeout_seconds: int = 10,
    ) -> RunnerExecutionResult:
        raise NotImplementedError


class SubprocessCodeRunner(CodeRunner):
    ALLOWED_LANGUAGES = SUPPORTED_LANGUAGES
    DEFAULT_SOURCE_NAMES = {
        "c": "main.c",
        "cpp": "main.cpp",
        "python": "main.py",
        "java": "Main.java",
    }

    def run_code(
        self,
        language: str,
        source_code: str,
        *,
        input_data: str = "",
        source_name: str | None = None,
        timeout_seconds: int = 10,
    ) -> RunnerExecutionResult:
        normalized_language = language.strip().lower()
        self._ensure_supported_language(normalized_language)

        resolved_source_name = self._resolve_source_name(
            normalized_language,
            source_name,
        )
        normalized_timeout = max(int(timeout_seconds), 1)

        with tempfile.TemporaryDirectory(prefix="neoespa-runner-") as temp_dir:
            workspace = Path(temp_dir)
            source_path = workspace / resolved_source_name
            source_path.write_text(source_code, encoding="utf-8")

            compile_command, run_command = self._build_commands(
                normalized_language,
                source_path,
            )
            compile_result = self._execute(
                compile_command,
                workspace,
                normalized_timeout,
            )
            if not compile_result.succeeded:
                return RunnerExecutionResult(
                    language=normalized_language,
                    source_name=resolved_source_name,
                    workspace=str(workspace),
                    compile_result=compile_result,
                    run_result=None,
                    status="timeout" if compile_result.timed_out else "compile_error",
                )

            run_result = self._execute(
                run_command,
                workspace,
                normalized_timeout,
                input_data=input_data,
            )
            if run_result.timed_out:
                status = "timeout"
            elif run_result.exit_code == 0:
                status = "passed"
            else:
                status = "runtime_error"

            return RunnerExecutionResult(
                language=normalized_language,
                source_name=resolved_source_name,
                workspace=str(workspace),
                compile_result=compile_result,
                run_result=run_result,
                status=status,
            )

    def run_file(
        self,
        language: str,
        file_path: str,
        *,
        input_data: str = "",
        timeout_seconds: int = 10,
    ) -> RunnerExecutionResult:
        source_path = Path(file_path)
        return self.run_code(
            language,
            source_path.read_text(encoding="utf-8"),
            input_data=input_data,
            source_name=source_path.name,
            timeout_seconds=timeout_seconds,
        )

    def _ensure_supported_language(self, language: str) -> None:
        if language not in self.ALLOWED_LANGUAGES:
            raise UnsupportedLanguageError(f"Unsupported language: {language}")

    def _resolve_source_name(self, language: str, source_name: str | None) -> str:
        if source_name:
            return Path(source_name).name
        return self.DEFAULT_SOURCE_NAMES[language]

    def _build_commands(
        self,
        language: str,
        source_path: Path,
    ) -> tuple[list[str], list[str]]:
        executable_path = source_path.parent / "program"

        if language == "c":
            return (
                ["gcc", source_path.name, "-O2", "-o", executable_path.name],
                [str(executable_path)],
            )
        if language == "cpp":
            return (
                ["g++", source_path.name, "-O2", "-std=c++17", "-o", executable_path.name],
                [str(executable_path)],
            )
        if language == "java":
            class_name = source_path.stem
            return (
                ["javac", source_path.name],
                ["java", "-cp", ".", class_name],
            )
        return (
            ["python3", "-m", "py_compile", source_path.name],
            ["python3", source_path.name],
        )

    def _build_env(self, workspace: Path) -> dict[str, str]:
        return {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(workspace),
            "TMPDIR": str(workspace),
            "PYTHONNOUSERSITE": "1",
        }

    def _execute(
        self,
        command: list[str],
        workspace: Path,
        timeout_seconds: int,
        input_data: str = "",
    ) -> PhaseExecutionResult:
        started_at = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=self._build_env(workspace),
            )
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            return PhaseExecutionResult(
                command=command,
                stdout=completed.stdout,
                stderr=completed.stderr,
                exit_code=completed.returncode,
                duration_ms=duration_ms,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as error:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            return PhaseExecutionResult(
                command=command,
                stdout=error.stdout or "",
                stderr=error.stderr or "Execution timed out",
                exit_code=None,
                duration_ms=duration_ms,
                timed_out=True,
            )
        except FileNotFoundError:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            return PhaseExecutionResult(
                command=command,
                stdout="",
                stderr=f"Command not found: {command[0]}",
                exit_code=127,
                duration_ms=duration_ms,
                timed_out=False,
            )


class CodeRunnerService(SubprocessCodeRunner):
    """Legacy host runner guarded by an environment-aware fail-closed gate."""

    def run_code(
        self,
        language: str,
        source_code: str,
        *,
        input_data: str = "",
        source_name: str | None = None,
        timeout_seconds: int = 10,
    ) -> RunnerExecutionResult:
        if not settings.HOST_CODE_EXECUTION_ALLOWED:
            raise UnsafeExecutionDisabledError(
                "Host code execution is disabled. Configure an isolated judge runner."
            )
        return super().run_code(
            language,
            source_code,
            input_data=input_data,
            source_name=source_name,
            timeout_seconds=timeout_seconds,
        )


class NsJailCodeRunner(SubprocessCodeRunner):
    """Compile and execute submissions only through the reviewed NsJail policy."""

    def __init__(self, sandbox: NsJailSandboxRunner | None = None):
        self.sandbox = sandbox or NsJailSandboxRunner()

    def run_code(
        self, language: str, source_code: str, *, input_data: str = "",
        source_name: str | None = None, timeout_seconds: int = 10,
    ) -> RunnerExecutionResult:
        limits = NsJailLimits(
            wall_seconds=max(int(timeout_seconds), 1) + 2,
            cpu_seconds=max(int(timeout_seconds), 1),
        )
        return self.run_code_with_limits(
            language, source_code, input_data=input_data, source_name=source_name,
            limits=limits,
        )

    def run_code_with_limits(
        self, language: str, source_code: str, *, input_data: str = "",
        source_name: str | None = None, limits: NsJailLimits,
    ) -> RunnerExecutionResult:
        normalized = language.strip().lower()
        self._ensure_supported_language(normalized)
        resolved_name = self._resolve_source_name(normalized, source_name)
        with tempfile.TemporaryDirectory(prefix="neoespa-sandbox-") as temp_dir:
            workspace = Path(temp_dir)
            (workspace / resolved_name).write_text(source_code, encoding="utf-8")
            compile_command, run_command = self._sandbox_commands(normalized, resolved_name)
            compile_result = self._sandbox_phase(compile_command, workspace, b"", limits)
            if not compile_result.succeeded:
                return RunnerExecutionResult(
                    normalized, resolved_name, str(workspace), compile_result, None,
                    "timeout" if compile_result.timed_out else "compile_error",
                )
            run_result, output_limited = self._sandbox_phase_with_limit(
                run_command, workspace, input_data.encode(), limits
            )
            memory_limited = (
                run_result.exit_code not in {None, 0}
                and any(marker in run_result.stderr.lower() for marker in (
                    "memoryerror", "bad_alloc", "cannot allocate memory", "rlimit_as",
                ))
            )
            status = (
                "output_limit" if output_limited else "timeout" if run_result.timed_out
                else "memory_limit" if memory_limited
                else "passed" if run_result.exit_code == 0 else "runtime_error"
            )
            return RunnerExecutionResult(
                normalized, resolved_name, str(workspace), compile_result, run_result, status
            )

    def _sandbox_phase(
        self, command: list[str], workspace: Path, stdin: bytes, limits: NsJailLimits
    ) -> PhaseExecutionResult:
        result, _ = self._sandbox_phase_with_limit(command, workspace, stdin, limits)
        return result

    def _sandbox_phase_with_limit(
        self, command: list[str], workspace: Path, stdin: bytes, limits: NsJailLimits
    ) -> tuple[PhaseExecutionResult, bool]:
        executed = self.sandbox.run(command, workspace=workspace, stdin=stdin, limits=limits)
        return PhaseExecutionResult(
            command=command, stdout=executed.stdout.decode("utf-8", errors="replace"),
            stderr=executed.stderr.decode("utf-8", errors="replace"),
            exit_code=executed.exit_code, duration_ms=executed.duration_ms,
            timed_out=executed.timed_out,
        ), executed.output_limited

    @staticmethod
    def _sandbox_commands(language: str, source_name: str) -> tuple[list[str], list[str]]:
        source = f"/workspace/{source_name}"
        if language == "c":
            return ["/usr/bin/gcc", source, "-O2", "-o", "/workspace/program"], ["/workspace/program"]
        if language == "cpp":
            return ["/usr/bin/g++", source, "-O2", "-std=c++17", "-o", "/workspace/program"], ["/workspace/program"]
        if language == "java":
            return ["/usr/bin/javac", source], ["/usr/bin/java", "-cp", "/workspace", Path(source_name).stem]
        return ["/usr/bin/python3", "-m", "py_compile", source], ["/usr/bin/python3", source]
