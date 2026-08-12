import hashlib
import json
from types import SimpleNamespace

import pytest

from app.services.sandbox.selftest import run_hostile_selftest


def test_hostile_selftest_writes_policy_and_result_bound_attestation(
    tmp_path, monkeypatch,
):
    policy = tmp_path / "nsjail.cfg"
    policy.write_text("reviewed-policy", encoding="utf-8")
    attestation = tmp_path / "attestation.json"

    class ReadySandbox:
        def __init__(self, config_path):
            assert config_path == policy

        def readiness_errors(self):
            return []

    class FixtureRunner:
        def __init__(self, _sandbox):
            pass

        def run_code(self, _language, source, timeout_seconds):
            assert timeout_seconds == 2
            if "socket" in source or "host-escape" in source or "fork" in source:
                status = "runtime_error"
            elif "while True: pass" in source:
                status = "timeout"
            elif "print('x' * 4096)" in source:
                status = "output_limit"
            else:
                status = "passed"
            return SimpleNamespace(status=status)

    monkeypatch.setattr("app.services.sandbox.selftest.NsJailSandboxRunner", ReadySandbox)
    monkeypatch.setattr("app.services.sandbox.selftest.NsJailCodeRunner", FixtureRunner)

    payload = run_hostile_selftest(
        policy_path=policy, attestation_path=attestation, runtime_version="image@sha256:abc"
    )

    assert json.loads(attestation.read_text("utf-8")) == payload
    assert payload["policy_sha256"] == hashlib.sha256(policy.read_bytes()).hexdigest()
    assert payload["results"]["network"] == "runtime_error"
    assert payload["results"]["output"] == "output_limit"


def test_failed_recheck_invalidates_previous_attestation(tmp_path, monkeypatch):
    policy = tmp_path / "nsjail.cfg"
    policy.write_text("broken-policy", encoding="utf-8")
    attestation = tmp_path / "attestation.json"
    attestation.write_text('{"passed": true}', encoding="utf-8")

    class NotReadySandbox:
        def __init__(self, config_path):
            pass

        def readiness_errors(self):
            return ["nsjail unavailable"]

    monkeypatch.setattr("app.services.sandbox.selftest.NsJailSandboxRunner", NotReadySandbox)

    with pytest.raises(RuntimeError, match="nsjail unavailable"):
        run_hostile_selftest(
            policy_path=policy, attestation_path=attestation, runtime_version="runtime-v1"
        )

    assert not attestation.exists()
