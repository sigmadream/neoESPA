from __future__ import annotations

import tempfile
from pathlib import Path

from ..sandbox import NsJailLimits, NsJailSandboxRunner
from .output import CheckerError, CheckerResult


class SpecialJudgeChecker:
    version = "special-python-v1"

    def __init__(self, sandbox: NsJailSandboxRunner, source: str):
        self.sandbox = sandbox
        self.source = source

    def check(
        self, input_data: str, expected: str, actual: str
    ) -> CheckerResult:
        with tempfile.TemporaryDirectory(
            prefix="neoespa-special-judge-"
        ) as temporary:
            workspace = Path(temporary)
            (workspace / "checker.py").write_text(self.source, encoding="utf-8")
            (workspace / "input.txt").write_text(input_data, encoding="utf-8")
            (workspace / "expected.txt").write_text(expected, encoding="utf-8")
            (workspace / "actual.txt").write_text(actual, encoding="utf-8")
            result = self.sandbox.run(
                [
                    "/usr/bin/python3",
                    "/workspace/checker.py",
                    "/workspace/input.txt",
                    "/workspace/expected.txt",
                    "/workspace/actual.txt",
                ],
                workspace=workspace,
                limits=NsJailLimits(
                    wall_seconds=3,
                    cpu_seconds=2,
                    memory_mb=128,
                    file_size_mb=1,
                    process_count=1,
                    open_files=16,
                    output_bytes=64 * 1024,
                ),
            )
        message = result.stdout.decode("utf-8", errors="replace").strip()[:500]
        if (
            result.timed_out
            or result.output_limited
            or result.exit_code not in {0, 1}
        ):
            raise CheckerError(
                "Special judge failed: "
                + (
                    result.stderr.decode("utf-8", errors="replace").strip()[
                        :500
                    ]
                    or "internal error"
                )
            )
        return CheckerResult(
            accepted=result.exit_code == 0,
            verdict="AC" if result.exit_code == 0 else "WA",
            message=message
            or (
                "Accepted by special judge"
                if result.exit_code == 0
                else "Rejected by special judge"
            ),
        )
