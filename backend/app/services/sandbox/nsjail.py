from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


class SandboxNotReadyError(RuntimeError):
    pass


@dataclass(frozen=True)
class NsJailLimits:
    wall_seconds: int = 10
    cpu_seconds: int = 5
    memory_mb: int = 256
    file_size_mb: int = 16
    process_count: int = 16
    open_files: int = 32
    output_bytes: int = 1024 * 1024
    cpu_ms_per_second: int = 1000


@dataclass(frozen=True)
class SandboxExecutionResult:
    stdout: bytes
    stderr: bytes
    exit_code: int | None
    duration_ms: int
    timed_out: bool
    output_limited: bool = False


class NsJailSandboxRunner:
    """Linux-only adapter for a deployment-reviewed NsJail policy.

    The policy owns namespace, read-only root, tmpfs and seccomp rules. This
    adapter refuses configs that do not visibly enable the required controls;
    a Linux hostile-fixture self-test remains the final production gate.
    """

    REQUIRED_CONFIG_MARKERS = (
        "clone_newnet: true",
        "clone_newuser: true",
        "clone_newns: true",
        "clone_newpid: true",
        "clone_newipc: true",
        "clone_newcgroup: true",
        "uidmap {",
        "gidmap {",
        "seccomp_",
        "is_bind: true",
        "rw: false",
    )

    def __init__(
        self,
        *,
        binary: str = "nsjail",
        config_path: Path | None = None,
    ):
        self.binary = binary
        configured = config_path or (
            Path(os.environ["NSJAIL_CONFIG_PATH"])
            if os.getenv("NSJAIL_CONFIG_PATH")
            else None
        )
        self.config_path = configured.resolve() if configured else None

    def readiness_errors(self) -> list[str]:
        errors: list[str] = []
        if platform.system() != "Linux":
            errors.append("NsJail runner requires Linux")
        if shutil.which(self.binary) is None:
            errors.append("nsjail executable is not installed")
        if self.config_path is None or not self.config_path.is_file():
            errors.append("NSJAIL_CONFIG_PATH must point to a policy file")
            return errors
        policy = self.config_path.read_text(encoding="utf-8")
        for marker in self.REQUIRED_CONFIG_MARKERS:
            if marker not in policy:
                errors.append(
                    f"NsJail policy is missing required marker: {marker}"
                )
        return errors

    def run(
        self,
        command: list[str],
        *,
        workspace: Path,
        stdin: bytes = b"",
        limits: NsJailLimits | None = None,
    ) -> SandboxExecutionResult:
        errors = self.readiness_errors()
        if errors:
            raise SandboxNotReadyError("; ".join(errors))
        if not command or not command[0].startswith("/"):
            raise ValueError(
                "Sandbox command must use an absolute in-jail executable path"
            )
        resolved_workspace = workspace.resolve()
        if not resolved_workspace.is_dir():
            raise ValueError("Sandbox workspace must be an existing directory")
        selected = limits or NsJailLimits()
        nsjail_command = [
            self.binary,
            "-Mo",
            "--config",
            str(self.config_path),
            "--bindmount",
            f"{resolved_workspace}:/workspace",
            "--cwd",
            "/workspace",
            "--time_limit",
            str(selected.wall_seconds),
            "--rlimit_cpu",
            str(selected.cpu_seconds),
            "--rlimit_as",
            str(selected.memory_mb),
            "--rlimit_fsize",
            str(selected.file_size_mb),
            "--rlimit_nproc",
            str(selected.process_count),
            "--rlimit_nofile",
            str(selected.open_files),
            "--cgroup_mem_max",
            str(selected.memory_mb * 1024 * 1024),
            "--cgroup_pids_max",
            str(selected.process_count),
            "--cgroup_cpu_ms_per_sec",
            str(min(1000, max(1, selected.cpu_ms_per_second))),
            "--detect_cgroupv2",
            "--",
            *command,
        ]
        started = time.perf_counter()
        try:
            with (
                tempfile.TemporaryFile() as stdout_file,
                tempfile.TemporaryFile() as stderr_file,
            ):
                completed = subprocess.run(
                    nsjail_command,
                    input=stdin,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    timeout=selected.wall_seconds + 2,
                    check=False,
                    cwd=resolved_workspace,
                )
                stdout_file.seek(0)
                stderr_file.seek(0)
                stdout = stdout_file.read(selected.output_bytes + 1)
                stderr = stderr_file.read(selected.output_bytes + 1)
                # Test doubles may provide direct captured output.
                if isinstance(getattr(completed, "stdout", None), bytes):
                    stdout = completed.stdout
                if isinstance(getattr(completed, "stderr", None), bytes):
                    stderr = completed.stderr
                duration_ms = int((time.perf_counter() - started) * 1000)
                output_limited = (
                    len(stdout) > selected.output_bytes
                    or len(stderr) > selected.output_bytes
                )
                stdout = stdout[: selected.output_bytes]
                stderr = stderr[: selected.output_bytes]
            return SandboxExecutionResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=completed.returncode,
                duration_ms=duration_ms,
                # NsJail enforces RLIMIT_CPU itself and reports its SIGKILL as
                # exit 137 rather than causing subprocess.TimeoutExpired.
                # A memory cgroup kill normally happens well before the CPU
                # duration threshold and remains distinguishable as MLE/RE.
                timed_out=(
                    completed.returncode in {137, -9}
                    and duration_ms >= selected.cpu_seconds * 900
                    and b"SIGKILL" in stderr
                ),
                output_limited=output_limited,
            )
        except subprocess.TimeoutExpired as error:
            return SandboxExecutionResult(
                stdout=error.stdout or b"",
                stderr=error.stderr or b"",
                exit_code=None,
                duration_ms=int((time.perf_counter() - started) * 1000),
                timed_out=True,
            )
