import pytest

from app.services.checkers import CheckerError, FloatingPointChecker, get_checker
from app.services.scoring import CaseScore, GroupPolicy, calculate_group_score


def test_builtin_checkers():
    assert get_checker("token").check("1  2\n", "1 2").accepted
    assert get_checker("line").check("a  \nb", "a\nb").accepted
    assert get_checker("unordered").check("a\nb\na", "a\na\nb").accepted
    assert not get_checker("unordered").check("a\na", "a").accepted


def test_float_checker_tolerance_and_invalid_number():
    checker = FloatingPointChecker(absolute_tolerance=1e-5)
    assert checker.check("1.00000", "1.000001").accepted
    assert not checker.check("1", "1.1").accepted
    with pytest.raises(CheckerError):
        checker.check("number", "1")


def test_group_scoring_dependencies_and_all_or_nothing():
    total, groups = calculate_group_score(
        [
            CaseScore("base", True, 20),
            CaseScore("base", True, 20),
            CaseScore("advanced", True, 30),
            CaseScore("advanced", False, 30),
        ],
        [
            GroupPolicy("base", "sum"),
            GroupPolicy("advanced", "all_or_nothing", dependency="base"),
        ],
    )
    assert total == 40
    assert groups == {"base": 40, "advanced": 0}


def test_group_scoring_rejects_dependency_cycle():
    with pytest.raises(ValueError, match="cycle"):
        calculate_group_score(
            [],
            [GroupPolicy("a", dependency="b"), GroupPolicy("b", dependency="a")],
        )
