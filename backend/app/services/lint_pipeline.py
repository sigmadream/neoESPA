from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session

from ..core.support_files import resolve_support_dir
from ..core.system_settings import DEFAULT_LINT_SETTINGS, parse_boolean_setting
from ..models.schemas import SystemSetting

PYLINT_SEVERITY_MAP = {
    "fatal": "issue",
    "error": "issue",
    "warning": "issue",
    "convention": "style",
    "refactor": "performance",
    "information": "information",
    "info": "information",
}


@dataclass
class NormalizedLintIssue:
    tool: str
    rule: str
    severity: str
    neo_severity: str
    message_eng: str
    message_kor: str
    line_start: int
    line_end: int
    enabled_for_week: bool
    external_url: str | None = None


@dataclass
class LintAnalysisResult:
    tool: str
    week: str | None
    issues: list[NormalizedLintIssue]
    lint_weight: float
    penalty_total: float
    quality_score: float

    @property
    def enabled_issues(self) -> list[NormalizedLintIssue]:
        return [issue for issue in self.issues if issue.enabled_for_week]


class _BadNameVisitor(ast.NodeVisitor):
    def __init__(self, bad_names: set[str], good_names: set[str]):
        self.bad_names = bad_names
        self.good_names = good_names
        self.findings: list[dict[str, object]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_arguments(node.args)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_arguments(node.args)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._record_target(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._record_target(node.target)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._record_target(node.target)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._record_target(node.target)
        self.generic_visit(node)

    def _record_arguments(self, args: ast.arguments) -> None:
        for argument in [
            *args.posonlyargs,
            *args.args,
            *args.kwonlyargs,
        ]:
            self._record_name(argument.arg, argument.lineno)
        if args.vararg is not None:
            self._record_name(args.vararg.arg, args.vararg.lineno)
        if args.kwarg is not None:
            self._record_name(args.kwarg.arg, args.kwarg.lineno)

    def _record_target(self, node: ast.AST) -> None:
        if isinstance(node, ast.Name):
            self._record_name(node.id, node.lineno)
            return
        if isinstance(node, (ast.Tuple, ast.List)):
            for element in node.elts:
                self._record_target(element)

    def _record_name(self, name: str, line_number: int) -> None:
        if name in self.good_names:
            return
        if name in self.bad_names:
            self.findings.append(
                {
                    "rule": "disallowed-name",
                    "severity": "warning",
                    "message": f"Disallowed name {name}",
                    "lineStart": line_number,
                    "lineEnd": line_number,
                }
            )


class LintPipelineService:
    def __init__(self, support_dir: Path | None = None):
        self.support_dir = support_dir or resolve_support_dir(__file__)
        self.week_rules = json.loads(
            (self.support_dir / "week_rules.json").read_text(encoding="utf-8")
        )
        self.message_catalog = {
            "pylint": json.loads(
                (self.support_dir / "pylint_message.json").read_text(
                    encoding="utf-8"
                )
            ),
            "cppcheck": json.loads(
                (self.support_dir / "cppcheck_message.json").read_text(
                    encoding="utf-8"
                )
            ),
            "pmd": json.loads(
                (self.support_dir / "pmd_message.json").read_text(
                    encoding="utf-8"
                )
            ),
        }
        self.lint_manual = json.loads(
            (self.support_dir / "lint_rule_manual.json").read_text(
                encoding="utf-8"
            )
        )
        pylint_manual = self.lint_manual["pylint"]
        self.max_line_length = int(pylint_manual["max-line-length"]["default"])
        self.bad_names = {
            name.strip()
            for name in pylint_manual["bad-names"]["default"].split(",")
            if name.strip()
        }
        self.good_names = {
            name.strip()
            for name in pylint_manual["good-names"]["default"].split(",")
            if name.strip()
        }

    def analyze_python_code(
        self,
        code_text: str,
        *,
        week: int | str | None = None,
        session: Session | None = None,
    ) -> LintAnalysisResult:
        raw_issues = self._collect_python_issues(code_text)
        issues = self.normalize_python_issues(
            raw_issues, week=week, session=session
        )
        lint_weight, penalty_total, quality_score = self._score_issues(
            session, issues
        )
        return LintAnalysisResult(
            tool="pylint",
            week=str(week) if week is not None else None,
            issues=issues,
            lint_weight=lint_weight,
            penalty_total=penalty_total,
            quality_score=quality_score,
        )

    def normalize_python_issues(
        self,
        raw_issues: list[dict[str, object]],
        *,
        week: int | str | None = None,
        session: Session | None = None,
    ) -> list[NormalizedLintIssue]:
        return [
            self._normalize_issue(
                "pylint", raw_issue, week=week, session=session
            )
            for raw_issue in raw_issues
        ]

    def _collect_python_issues(self, code_text: str) -> list[dict[str, object]]:
        issues: list[dict[str, object]] = []
        lines = code_text.splitlines()

        for index, line in enumerate(lines, start=1):
            if line.endswith((" ", "\t")):
                issues.append(
                    {
                        "rule": "trailing-whitespace",
                        "severity": "convention",
                        "message": "There is a trailing whitespace",
                        "lineStart": index,
                        "lineEnd": index,
                    }
                )

            if len(line) > self.max_line_length:
                issues.append(
                    {
                        "rule": "line-too-long",
                        "severity": "convention",
                        "message": f"Line too long ({len(line)}/{self.max_line_length})",
                        "lineStart": index,
                        "lineEnd": index,
                    }
                )

            stripped = line.strip()
            if ";" in line and stripped and not stripped.startswith("#"):
                issues.append(
                    {
                        "rule": "multiple-statements",
                        "severity": "convention",
                        "message": "More than one statement on a single line",
                        "lineStart": index,
                        "lineEnd": index,
                    }
                )

            if ".format(" in line:
                issues.append(
                    {
                        "rule": "consider-using-f-string",
                        "severity": "refactor",
                        "message": "Formatting a regular string which could be an f-string",
                        "lineStart": index,
                        "lineEnd": index,
                    }
                )

        if code_text and not code_text.endswith("\n"):
            line_number = max(len(lines), 1)
            issues.append(
                {
                    "rule": "missing-final-newline",
                    "severity": "convention",
                    "message": "Please add a blank line at the end of the file",
                    "lineStart": line_number,
                    "lineEnd": line_number,
                }
            )

        try:
            tree = ast.parse(code_text)
        except SyntaxError as error:
            line_number = error.lineno or 1
            issues.append(
                {
                    "rule": "syntax-error",
                    "severity": "error",
                    "message": error.msg,
                    "lineStart": line_number,
                    "lineEnd": line_number,
                }
            )
            return issues

        bad_name_visitor = _BadNameVisitor(self.bad_names, self.good_names)
        bad_name_visitor.visit(tree)
        issues.extend(bad_name_visitor.findings)
        return issues

    def _normalize_issue(
        self,
        tool: str,
        raw_issue: dict[str, object],
        *,
        week: int | str | None = None,
        session: Session | None = None,
    ) -> NormalizedLintIssue:
        severity = str(raw_issue.get("severity", "warning")).lower()
        rule = str(raw_issue.get("rule", "unknown"))
        line_start = int(raw_issue.get("lineStart", raw_issue.get("line", 1)))
        line_end = int(raw_issue.get("lineEnd", line_start))
        raw_message = str(raw_issue.get("message", "")).strip()
        message_eng, message_kor = self._render_message(tool, rule, raw_message)
        neo_severity = PYLINT_SEVERITY_MAP.get(severity, "issue")
        enabled_for_week = self._rule_enabled_for_week(
            tool, rule, week, session=session
        )

        return NormalizedLintIssue(
            tool=tool,
            rule=rule,
            severity=severity,
            neo_severity=neo_severity,
            message_eng=message_eng,
            message_kor=message_kor,
            line_start=line_start,
            line_end=line_end,
            enabled_for_week=enabled_for_week,
            external_url=self._build_external_url(tool, severity, rule),
        )

    def _render_message(
        self, tool: str, rule: str, raw_message: str
    ) -> tuple[str, str]:
        rule_entry = self.message_catalog.get(tool, {}).get(rule)
        if rule_entry is None:
            return raw_message, ""

        pattern = rule_entry["eng"]
        if not raw_message:
            return pattern, rule_entry["kor"]

        try:
            matches = re.findall(pattern, raw_message)
        except re.error:
            matches = []

        if not matches or raw_message == pattern:
            return raw_message, rule_entry["kor"]

        values = matches[0]
        if not isinstance(values, tuple):
            values = (values,)

        try:
            translated = rule_entry["kor"] % values
        except TypeError:
            translated = rule_entry["kor"]

        return raw_message, translated

    def _rule_enabled_for_week(
        self,
        tool: str,
        rule: str,
        week: int | str | None,
        session: Session | None,
    ) -> bool:
        if self._default_rules_enabled(session):
            return True

        if week is None:
            return True

        week_rules = self.week_rules.get(tool, {})
        allowed_rules = week_rules.get(str(week))
        if allowed_rules is None:
            return True
        return rule in allowed_rules

    def _default_rules_enabled(self, session: Session | None) -> bool:
        if session is None:
            return False

        setting = session.get(SystemSetting, "lint_set_default")
        if setting is None:
            return False

        try:
            return parse_boolean_setting(setting.value)
        except ValueError:
            return False

    def _build_external_url(
        self, tool: str, severity: str, rule: str
    ) -> str | None:
        if tool != "pylint":
            return None
        return (
            "https://pylint.readthedocs.io/en/stable/user_guide/messages/"
            f"{severity}/{rule}.html"
        )

    def _score_issues(
        self,
        session: Session | None,
        issues: list[NormalizedLintIssue],
    ) -> tuple[float, float, float]:
        lint_weight = self._get_setting(session, "lint_calc_weight")
        penalty_unit = self._get_setting(session, "lint_calc_panalty")
        severity_weights = {
            "issue": self._get_setting(session, "lint_err_issue"),
            "style": self._get_setting(session, "lint_err_style"),
            "performance": self._get_setting(session, "lint_err_performance"),
            "information": self._get_setting(session, "lint_err_information"),
        }

        penalty_total = 0.0
        for issue in issues:
            if not issue.enabled_for_week:
                continue
            penalty_total += penalty_unit * severity_weights.get(
                issue.neo_severity, 1.0
            )

        quality_score = max(lint_weight - penalty_total, 0.0)
        return lint_weight, round(penalty_total, 2), round(quality_score, 2)

    def _get_setting(self, session: Session | None, key: str) -> float:
        if session is not None:
            setting = session.get(SystemSetting, key)
            if setting is not None:
                try:
                    return float(setting.value)
                except ValueError:
                    pass
        return DEFAULT_LINT_SETTINGS[key]
