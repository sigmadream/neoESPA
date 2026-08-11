from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CaseScore:
    group_key: str
    passed: bool
    score: float


@dataclass(frozen=True)
class GroupPolicy:
    key: str
    policy: str = "sum"
    dependency: str | None = None


def calculate_group_score(
    cases: list[CaseScore], policies: list[GroupPolicy]
) -> tuple[float, dict[str, float]]:
    grouped: dict[str, list[CaseScore]] = {}
    for case in cases:
        grouped.setdefault(case.group_key, []).append(case)
    policy_by_key = {policy.key: policy for policy in policies}
    unknown = set(grouped) - set(policy_by_key)
    if unknown:
        raise ValueError(f"Missing group policies: {', '.join(sorted(unknown))}")

    scores: dict[str, float] = {}
    visiting: set[str] = set()

    def score_group(key: str) -> float:
        if key in scores:
            return scores[key]
        if key in visiting:
            raise ValueError("Testcase group dependencies contain a cycle")
        visiting.add(key)
        policy = policy_by_key[key]
        if policy.dependency:
            if policy.dependency not in policy_by_key:
                raise ValueError(f"Unknown dependency group: {policy.dependency}")
            if score_group(policy.dependency) <= 0:
                scores[key] = 0.0
                visiting.remove(key)
                return 0.0
        group_cases = grouped.get(key, [])
        if policy.policy == "all_or_nothing":
            value = sum(case.score for case in group_cases) if all(case.passed for case in group_cases) else 0.0
        elif policy.policy == "sum":
            value = sum(case.score for case in group_cases if case.passed)
        else:
            raise ValueError(f"Unknown scoring policy: {policy.policy}")
        scores[key] = round(value, 6)
        visiting.remove(key)
        return scores[key]

    for policy in policies:
        score_group(policy.key)
    return round(sum(scores.values()), 6), scores
