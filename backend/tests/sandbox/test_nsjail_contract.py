from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.sandbox import NsJailLimits, NsJailSandboxRunner, SandboxNotReadyError
from app.services.sandbox import SandboxExecutionResult
from app.services.code_runner import NsJailCodeRunner


SECURE_POLICY = """
clone_newnet: true
clone_newuser: true
clone_newns: true
clone_newpid: true
clone_newipc: true
clone_newcgroup: true
uidmap { inside_id: "65534" outside_id: "" count: 1 }
gidmap { inside_id: "65534" outside_id: "" count: 1 }
seccomp_string: "DEFAULT KILL"
mount { src: "/runtime" dst: "/" is_bind: true rw: false }
"""


def test_runner_is_fail_closed_without_linux_runtime(tmp_path):
    runner = NsJailSandboxRunner(config_path=tmp_path / "missing.cfg")
    with pytest.raises(SandboxNotReadyError):
        runner.run(["/usr/bin/python3"], workspace=tmp_path)


def test_runner_rejects_policy_without_security_controls(tmp_path, monkeypatch):
    policy = tmp_path / "weak.cfg"
    policy.write_text("clone_newnet: false", encoding="utf-8")
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("shutil.which", lambda _binary: "/usr/bin/nsjail")
    errors = NsJailSandboxRunner(config_path=policy).readiness_errors()
    assert any("clone_newnet" in error for error in errors)
    assert any("seccomp" in error for error in errors)


def test_runner_builds_bounded_nsjail_command(tmp_path, monkeypatch):
    policy = tmp_path / "secure.cfg"
    policy.write_text(SECURE_POLICY, encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("shutil.which", lambda _binary: "/usr/bin/nsjail")

    with patch("subprocess.run") as run:
        run.return_value.stdout = b"ok\n"
        run.return_value.stderr = b""
        run.return_value.returncode = 0
        result = NsJailSandboxRunner(config_path=policy).run(
            ["/usr/bin/python3", "/workspace/main.py"],
            workspace=workspace,
            limits=NsJailLimits(wall_seconds=3, memory_mb=64, process_count=4),
        )

    command = run.call_args.args[0]
    assert "--config" in command
    assert "--rlimit_as" in command and "64" in command
    assert "--rlimit_nproc" in command and "4" in command
    assert "--cgroup_mem_max" in command
    assert "--cgroup_pids_max" in command and "4" in command
    assert "--cgroup_cpu_ms_per_sec" in command
    assert "--detect_cgroupv2" in command
    assert f"{workspace.resolve()}:/workspace" in command
    assert result.stdout == b"ok\n"


def test_code_runner_reports_output_limit_without_host_execution():
    class FakeSandbox:
        calls = 0

        def run(self, command, **_kwargs):
            self.calls += 1
            return SandboxExecutionResult(
                stdout=b"compiled" if self.calls == 1 else b"x" * 10,
                stderr=b"", exit_code=0, duration_ms=1, timed_out=False,
                output_limited=self.calls == 2,
            )

    runner = NsJailCodeRunner(FakeSandbox())
    result = runner.run_code("python", "print('x')")
    assert result.status == "output_limit"
    assert result.run_result is not None
    assert result.run_result.stdout == "x" * 10


def test_code_runner_distinguishes_memory_limit():
    class FakeSandbox:
        calls = 0

        def run(self, command, **_kwargs):
            self.calls += 1
            return SandboxExecutionResult(
                stdout=b"", stderr=b"MemoryError" if self.calls == 2 else b"",
                exit_code=1 if self.calls == 2 else 0, duration_ms=1, timed_out=False,
            )

    result = NsJailCodeRunner(FakeSandbox()).run_code("python", "x = bytearray(10**12)")
    assert result.status == "memory_limit"


def test_runner_maps_nsjail_cpu_limit_sigkill_to_timeout(tmp_path, monkeypatch):
    policy = tmp_path / "secure.cfg"
    policy.write_text(SECURE_POLICY, encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("shutil.which", lambda _binary: "/usr/bin/nsjail")

    with patch("subprocess.run") as run, patch("time.perf_counter", side_effect=[1.0, 3.0]):
        run.return_value.stdout = b""
        run.return_value.stderr = b"terminated with signal: SIGKILL (9)"
        run.return_value.returncode = 137
        result = NsJailSandboxRunner(config_path=policy).run(
            ["/usr/bin/python3"], workspace=workspace,
            limits=NsJailLimits(cpu_seconds=2, wall_seconds=4),
        )

    assert result.timed_out is True
