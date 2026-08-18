import json

from sqlalchemy import inspect, text
from sqlmodel import SQLModel

VERSION = "0027_homework_testcases"


def upgrade(engine) -> None:
    SQLModel.metadata.create_all(engine)
    if not inspect(engine).has_table("grading_rules"):
        return
    with engine.begin() as connection:
        existing = connection.execute(
            text("SELECT COUNT(*) FROM homework_testcases")
        ).scalar_one()
        if existing:
            return
        rules = connection.execute(
            text(
                "SELECT id, homework_num, rule_value FROM grading_rules "
                "WHERE rule_name = 'testcases' AND is_active = 1 "
                "ORDER BY id"
            )
        ).mappings()
        migrated_rule_ids: list[int] = []
        for rule in rules:
            try:
                loaded = json.loads(rule["rule_value"])
            except TypeError, json.JSONDecodeError:
                continue
            cases = loaded.get("cases", []) if isinstance(loaded, dict) else []
            if not isinstance(cases, list):
                continue
            for position, case in enumerate(cases, start=1):
                if not isinstance(case, dict):
                    continue
                connection.execute(
                    text(
                        "INSERT INTO homework_testcases "
                        "(homework_num, case_name, position, input_text, "
                        "expected_output, score, is_hidden, created_at, updated_at) "
                        "VALUES (:homework_num, :case_name, :position, :input_text, "
                        ":expected_output, :score, :is_hidden, CURRENT_TIMESTAMP, "
                        "CURRENT_TIMESTAMP)"
                    ),
                    {
                        "homework_num": rule["homework_num"],
                        "case_name": str(case.get("name", f"case-{position}")),
                        "position": position,
                        "input_text": str(case.get("input", "")),
                        "expected_output": str(case.get("expected_output", "")),
                        "score": float(case.get("score", 0.0)),
                        "is_hidden": int(bool(case.get("is_hidden", False))),
                    },
                )
            migrated_rule_ids.append(rule["id"])
        for rule_id in migrated_rule_ids:
            connection.execute(
                text("DELETE FROM grading_rules WHERE id = :rule_id"),
                {"rule_id": rule_id},
            )
