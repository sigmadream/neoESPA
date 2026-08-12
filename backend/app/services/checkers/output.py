from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass


class CheckerError(RuntimeError):
    pass


@dataclass(frozen=True)
class CheckerResult:
    accepted: bool
    verdict: str
    message: str


class LineChecker:
    version = "line-v1"

    def check(self, expected: str, actual: str) -> CheckerResult:
        expected_lines = [
            line.rstrip() for line in expected.strip().splitlines()
        ]
        actual_lines = [line.rstrip() for line in actual.strip().splitlines()]
        accepted = expected_lines == actual_lines
        return CheckerResult(
            accepted,
            "AC" if accepted else "WA",
            "Lines match" if accepted else "Line mismatch",
        )


class TokenChecker:
    version = "token-v1"

    def check(self, expected: str, actual: str) -> CheckerResult:
        accepted = expected.split() == actual.split()
        return CheckerResult(
            accepted,
            "AC" if accepted else "WA",
            "Tokens match" if accepted else "Token mismatch",
        )


class UnorderedLineChecker:
    version = "unordered-line-v1"

    def check(self, expected: str, actual: str) -> CheckerResult:
        expected_lines = Counter(
            line.rstrip() for line in expected.strip().splitlines()
        )
        actual_lines = Counter(
            line.rstrip() for line in actual.strip().splitlines()
        )
        accepted = expected_lines == actual_lines
        return CheckerResult(
            accepted,
            "AC" if accepted else "WA",
            "Line multisets match" if accepted else "Unordered line mismatch",
        )


class FloatingPointChecker:
    version = "float-v1"

    def __init__(
        self,
        *,
        absolute_tolerance: float = 1e-6,
        relative_tolerance: float = 1e-6,
    ):
        if absolute_tolerance < 0 or relative_tolerance < 0:
            raise CheckerError("Floating-point tolerances must be non-negative")
        self.absolute_tolerance = absolute_tolerance
        self.relative_tolerance = relative_tolerance

    def check(self, expected: str, actual: str) -> CheckerResult:
        expected_tokens = expected.split()
        actual_tokens = actual.split()
        if len(expected_tokens) != len(actual_tokens):
            return CheckerResult(
                False, "WA", "Floating-point token count mismatch"
            )
        try:
            pairs = zip(
                map(float, expected_tokens),
                map(float, actual_tokens),
                strict=True,
            )
            accepted = all(
                math.isfinite(expected_value)
                and math.isfinite(actual_value)
                and math.isclose(
                    expected_value,
                    actual_value,
                    rel_tol=self.relative_tolerance,
                    abs_tol=self.absolute_tolerance,
                )
                for expected_value, actual_value in pairs
            )
        except (ValueError, OverflowError) as error:
            raise CheckerError(
                "Floating-point checker received a non-number"
            ) from error
        return CheckerResult(
            accepted,
            "AC" if accepted else "WA",
            (
                "Values are within tolerance"
                if accepted
                else "Floating-point mismatch"
            ),
        )


def get_checker(name: str, config: dict | None = None):
    normalized = name.strip().lower()
    factories = {
        "line": LineChecker,
        "token": TokenChecker,
        "unordered": UnorderedLineChecker,
        "float": FloatingPointChecker,
    }
    factory = factories.get(normalized)
    if factory is None:
        raise CheckerError(f"Unknown checker: {name}")
    if normalized == "float":
        selected = config or {}
        return factory(
            absolute_tolerance=float(selected.get("absolute_tolerance", 1e-6)),
            relative_tolerance=float(selected.get("relative_tolerance", 1e-6)),
        )
    return factory()
