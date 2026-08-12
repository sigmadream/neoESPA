"""실제 nsjail 프로세스를 띄워 격리 정책을 검증하는 테스트.

`test_nsjail_contract.py`는 mock 기반이라 어떤 운영체제에서도 실행되지만,
정책이 실제로 격리를 강제하는지는 증명하지 못한다. 이 모듈은 mock을 전혀
사용하지 않고 `deploy/nsjail.cfg` 정책으로 실제 코드를 실행한다.

    docker compose -f docker-compose.test.yml run --rm --build sandbox-tests

nsjail 바이너리와 커널 네임스페이스 권한이 없는 환경(Windows/macOS 호스트,
일반 `tests` 이미지)에서는 자동으로 skip 된다.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import stat
from pathlib import Path

import pytest

from app.core.config import settings
from app.services.code_runner import NsJailCodeRunner
from app.services.sandbox import NsJailLimits, NsJailSandboxRunner
from app.services.sandbox.selftest import run_hostile_selftest

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _policy_path() -> Path:
    configured = os.getenv("NSJAIL_CONFIG_PATH")
    if configured:
        return Path(configured)
    return BACKEND_DIR / "deploy" / "nsjail.cfg"


def _skip_reason() -> str | None:
    if platform.system() != "Linux":
        return "실제 nsjail 실행은 Linux에서만 가능합니다"
    if shutil.which("nsjail") is None:
        return "nsjail 바이너리가 없습니다 (sandbox-tests 서비스로 실행하세요)"
    if not _policy_path().is_file():
        return f"nsjail 정책 파일이 없습니다: {_policy_path()}"
    return None


_SKIP_REASON = _skip_reason()

pytestmark = [
    pytest.mark.nsjail,
    pytest.mark.skipif(_SKIP_REASON is not None, reason=_SKIP_REASON or ""),
]


@pytest.fixture(scope="module")
def sandbox() -> NsJailSandboxRunner:
    return NsJailSandboxRunner(config_path=_policy_path())


@pytest.fixture(scope="module")
def runner(sandbox: NsJailSandboxRunner) -> NsJailCodeRunner:
    return NsJailCodeRunner(sandbox)


# --- 준비 상태 -------------------------------------------------------------


def test_reviewed_policy_passes_readiness_without_mocks(sandbox):
    assert sandbox.readiness_errors() == []


# --- 정상 실행 경로 --------------------------------------------------------


def test_python_submission_runs_inside_the_jail(runner):
    result = runner.run_code("python", "print('ok')", timeout_seconds=5)

    assert result.status == "passed"
    assert result.run_result is not None
    assert result.run_result.stdout.strip() == "ok"


def test_stdin_is_delivered_to_the_jailed_process(runner):
    result = runner.run_code(
        "python",
        "print(f'got {input()}')",
        input_data="42",
        timeout_seconds=5,
    )

    assert result.status == "passed"
    assert result.run_result.stdout.strip() == "got 42"


def test_c_submission_is_compiled_and_executed_inside_the_jail(runner):
    source = (
        "#include <stdio.h>\n"
        "int main(void) {\n"
        "    int a, b;\n"
        '    if (scanf("%d %d", &a, &b) != 2) return 1;\n'
        '    printf("%d\\n", a + b);\n'
        "    return 0;\n"
        "}\n"
    )

    result = runner.run_code("c", source, input_data="3 4", timeout_seconds=10)

    assert result.status == "passed", result.compile_result
    assert result.run_result.stdout.strip() == "7"


def test_workspace_is_writable_from_inside_the_jail(runner):
    source = (
        "open('artifact.txt', 'w').write('hello')\n"
        "print(open('artifact.txt').read())\n"
    )

    result = runner.run_code("python", source, timeout_seconds=5)

    assert result.status == "passed"
    assert result.run_result.stdout.strip() == "hello"


def test_compile_error_is_reported_from_the_jail(runner):
    result = runner.run_code(
        "c", "int main(void) { return notdeclared; }", timeout_seconds=10
    )

    assert result.status == "compile_error"
    assert result.compile_result.succeeded is False


# --- 격리 강제 -------------------------------------------------------------


def test_network_is_unreachable_even_for_a_reachable_listener(runner):
    """네트워크 네임스페이스가 실제로 연결을 끊는지 확인한다.

    테스트 프로세스가 직접 여는 리스너를 대상으로 하므로, 실패 원인이
    '서비스가 없어서'가 아니라 '격리 때문'임이 보장된다.
    """
    import socket

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        # 감옥 바깥(테스트 프로세스)에서는 같은 주소로 접속이 성공한다.
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            pass

        source = (
            "import socket\n"
            f"socket.create_connection(('127.0.0.1', {port}), timeout=2)\n"
            "print('connected')\n"
        )
        result = runner.run_code("python", source, timeout_seconds=5)

    assert result.status == "runtime_error"
    assert "connected" not in result.run_result.stdout


def test_root_filesystem_is_read_only_from_inside_the_jail(runner):
    result = runner.run_code(
        "python", "open('/host-escape', 'w').write('bad')", timeout_seconds=5
    )

    assert result.status == "runtime_error"
    assert not Path("/host-escape").exists()


def test_fork_bomb_is_contained_by_process_limits(runner):
    result = runner.run_code(
        "python", "import os\nwhile True:\n os.fork()", timeout_seconds=5
    )

    assert result.status == "runtime_error"


def test_cpu_limit_terminates_an_infinite_loop(runner):
    result = runner.run_code("python", "while True: pass", timeout_seconds=2)

    assert result.status == "timeout"


def test_output_limit_is_enforced(runner):
    result = runner.run_code(
        "python", "while True: print('x' * 4096)", timeout_seconds=5
    )

    assert result.status == "output_limit"


def test_memory_limit_is_enforced(runner):
    result = runner.run_code_with_limits(
        "python",
        "buffer = bytearray(512 * 1024 * 1024)\nprint(len(buffer))",
        limits=NsJailLimits(wall_seconds=10, cpu_seconds=5, memory_mb=64),
    )

    assert result.status in {"memory_limit", "runtime_error"}
    assert result.run_result.exit_code != 0


# --- 운영 게이트 -----------------------------------------------------------


def test_hostile_selftest_attestation_unlocks_sandbox_ready(
    tmp_path, monkeypatch
):
    """운영 배포 게이트를 mock 없이 그대로 재현한다.

    hostile fixture 6종을 실제 nsjail로 실행하고, 그 결과로 기록된
    attestation이 `settings.SANDBOX_READY`(fail-closed 스위치)를 실제로
    열어주는지까지 확인한다.
    """
    policy = _policy_path()
    attestation_path = tmp_path / "attestation.json"
    monkeypatch.setenv("JUDGE_RUNTIME_VERSION", "sandbox-test-runtime")

    payload = run_hostile_selftest(
        policy_path=policy,
        attestation_path=attestation_path,
        runtime_version=settings.JUDGE_RUNTIME_VERSION,
    )

    assert payload["passed"] is True
    assert payload["results"] == {
        "basic": "passed",
        "network": "runtime_error",
        "root_write": "runtime_error",
        "fork_bomb": "runtime_error",
        "timeout": "timeout",
        "output": "output_limit",
    }

    stored = json.loads(attestation_path.read_text(encoding="utf-8"))
    assert stored == payload
    assert stat.S_IMODE(attestation_path.stat().st_mode) == 0o600

    monkeypatch.setenv("SANDBOX_READY", "true")
    monkeypatch.setenv("SANDBOX_ATTESTATION_PATH", str(attestation_path))
    monkeypatch.setenv("NSJAIL_CONFIG_PATH", str(policy))
    assert settings.SANDBOX_READY is True

    # 정책이 바뀌면 attestation은 즉시 무효가 되어야 한다.
    tampered = tmp_path / "tampered.cfg"
    tampered.write_text(
        policy.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8"
    )
    monkeypatch.setenv("NSJAIL_CONFIG_PATH", str(tampered))
    assert settings.SANDBOX_READY is False
