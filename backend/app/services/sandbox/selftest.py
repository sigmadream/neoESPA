from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from ..code_runner import NsJailCodeRunner
from .nsjail import NsJailSandboxRunner


def run_hostile_selftest(
    *, policy_path: Path, attestation_path: Path, runtime_version: str
) -> dict:
    # A persisted attestation must never survive a failed re-check (for
    # example after a kernel, runtime image, or policy change). The API then
    # remains fail-closed while the worker executes the fixtures.
    attestation_path.unlink(missing_ok=True)
    sandbox = NsJailSandboxRunner(config_path=policy_path)
    errors = sandbox.readiness_errors()
    if errors:
        raise RuntimeError("; ".join(errors))
    runner = NsJailCodeRunner(sandbox)
    fixtures = {
        "basic": ("print('ok')", "passed"),
        "network": (
            "import socket\ns=socket.socket(); s.connect(('1.1.1.1', 53))",
            "runtime_error",
        ),
        "root_write": (
            "open('/host-escape', 'w').write('bad')",
            "runtime_error",
        ),
        "fork_bomb": ("import os\nwhile True:\n os.fork()", "runtime_error"),
        "timeout": ("while True: pass", "timeout"),
        "output": ("while True: print('x' * 4096)", "output_limit"),
    }
    passed: list[str] = []
    results: dict[str, str] = {}
    for name, (source, expected) in fixtures.items():
        result = runner.run_code("python", source, timeout_seconds=2)
        results[name] = result.status
        if result.status != expected:
            raise RuntimeError(
                f"Hostile fixture {name} returned {result.status}, expected {expected}"
            )
        passed.append(name)
    payload = {
        "passed": True,
        "fixtures": passed,
        "results": results,
        "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "runtime_version": runtime_version,
        "tested_at": datetime.now(UTC).isoformat(),
    }
    attestation_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = attestation_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.chmod(0o600)
    os.replace(temporary, attestation_path)
    return payload
