import json
from datetime import UTC, datetime

from sqlmodel import Session, select

from .migrations import apply_migrations
from .system_settings import SYSTEM_SETTING_DEFINITIONS
from ..models.schemas import GradingRule, Homework, Notice, SystemSetting, User
from ..services.auth_service import AuthService

SEEDED_AT = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)

SEEDED_USERS = [
    {
        "id": "admin",
        "sid": 100000001,
        "password": "pllab818",
        "name": "Administrator",
        "phone": "051-510-3939",
        "email": "pllab@pusan.ac.kr",
        "user_group": "admin",
    },
    {
        "id": "testuser",
        "sid": 12345678,
        "password": "qwer1234",
        "name": "Practice User",
        "phone": "010-0000-0000",
        "email": "test@example.com",
        "user_group": "student",
    },
]

SEEDED_HOMEWORKS = [
    {
        "num": 1,
        "title": "Sample Problem: A+B",
        "intro": "Write a program that takes two integers A and B, and prints their sum.",
        "deadline": "2026-12-31 23:59:59",
        "codeName": "aplusb",
        "starttime": "2026-03-01 00:00:00",
        "sbnum": 10,
        "sec": 1,
        "ratedatanum": 10,
        "isLint": True,
        "isDetected": False,
        "vitalSpace": False,
        "disorderedOutput": False,
        "filename": "sample-homework.pdf",
        "testcases": [
            {
                "name": "sample-1",
                "input": "1 2\n",
                "expected_output": "3\n",
                "score": 40,
                "is_hidden": False,
            },
            {
                "name": "hidden-1",
                "input": "100 250\n",
                "expected_output": "350\n",
                "score": 60,
                "is_hidden": True,
            },
        ],
    }
]

SEEDED_NOTICES = [
    {
        "num": 1,
        "title": "Welcome to neoESPA",
        "author": "Administrator",
        "content": "Read the first assignment and verify that your account can log in before the first deadline.",
        "date": "2026-03-01 09:00:00",
        "is_pinned": True,
        "is_published": True,
    }
]

DEFAULT_SYSTEM_SETTINGS = {
    key: definition["default_value"]
    for key, definition in SYSTEM_SETTING_DEFINITIONS.items()
}


def _password_matches(plain_password: str, stored_password: str) -> bool:
    try:
        return AuthService.verify_password(plain_password, stored_password)
    except ValueError:
        return False


def _seed_users(session: Session) -> None:
    for seeded_user in SEEDED_USERS:
        user = session.get(User, seeded_user["id"])
        password = seeded_user["password"]
        user_fields = {
            "sid": seeded_user["sid"],
            "name": seeded_user["name"],
            "phone": seeded_user["phone"],
            "email": seeded_user["email"],
            "user_group": seeded_user["user_group"],
            "is_active": True,
            "updated_at": SEEDED_AT,
        }

        if user is None:
            session.add(
                User(
                    id=seeded_user["id"],
                    ps=AuthService.get_password_hash(password),
                    created_at=SEEDED_AT,
                    **user_fields,
                )
            )
            continue

        for field_name, value in user_fields.items():
            setattr(user, field_name, value)
        if not _password_matches(password, user.ps):
            user.ps = AuthService.get_password_hash(password)


def _seed_homeworks(session: Session) -> None:
    for seeded_homework in SEEDED_HOMEWORKS:
        homework = session.get(Homework, seeded_homework["num"])
        homework_fields = {
            "title": seeded_homework["title"],
            "intro": seeded_homework["intro"],
            "deadline": seeded_homework["deadline"],
            "codeName": seeded_homework["codeName"],
            "starttime": seeded_homework["starttime"],
            "sbnum": seeded_homework["sbnum"],
            "sec": seeded_homework["sec"],
            "ratedatanum": seeded_homework["ratedatanum"],
            "isLint": seeded_homework["isLint"],
            "isDetected": seeded_homework["isDetected"],
            "vitalSpace": seeded_homework["vitalSpace"],
            "disorderedOutput": seeded_homework["disorderedOutput"],
            "filename": seeded_homework["filename"],
            "updated_at": SEEDED_AT,
        }

        if homework is None:
            session.add(
                Homework(
                    num=seeded_homework["num"],
                    created_at=SEEDED_AT,
                    **homework_fields,
                )
            )
        else:
            for field_name, value in homework_fields.items():
                setattr(homework, field_name, value)

        _upsert_homework_rule(
            session,
            homework_num=seeded_homework["num"],
            rule_name="testcases",
            rule_value=json.dumps({"cases": seeded_homework["testcases"]}),
            description="Homework testcase policy.",
        )


def _seed_notices(session: Session) -> None:
    for seeded_notice in SEEDED_NOTICES:
        notice = session.get(Notice, seeded_notice["num"])
        notice_fields = {
            "title": seeded_notice["title"],
            "author": seeded_notice["author"],
            "content": seeded_notice["content"],
            "date": seeded_notice["date"],
            "is_pinned": seeded_notice["is_pinned"],
            "is_published": seeded_notice["is_published"],
            "updated_at": SEEDED_AT,
        }

        if notice is None:
            session.add(Notice(num=seeded_notice["num"], **notice_fields))
            continue

        for field_name, value in notice_fields.items():
            setattr(notice, field_name, value)


def _seed_system_settings(session: Session) -> None:
    for key, value in DEFAULT_SYSTEM_SETTINGS.items():
        setting = session.get(SystemSetting, key)
        definition = SYSTEM_SETTING_DEFINITIONS[key]
        if setting is None:
            session.add(
                SystemSetting(
                    key=key,
                    value=value,
                    value_type=definition["value_type"],
                    description=definition["description"],
                    updated_at=SEEDED_AT,
                )
            )
            continue

        setting.value = value
        setting.value_type = definition["value_type"]
        setting.description = definition["description"]
        setting.updated_at = SEEDED_AT


def _upsert_homework_rule(
    session: Session,
    *,
    homework_num: int,
    rule_name: str,
    rule_value: str,
    description: str,
) -> None:
    rule = session.exec(
        select(GradingRule).where(
            GradingRule.scope == "homework",
            GradingRule.homework_num == homework_num,
            GradingRule.rule_name == rule_name,
        )
    ).first()
    if rule is None:
        session.add(
            GradingRule(
                scope="homework",
                homework_num=homework_num,
                rule_name=rule_name,
                rule_value=rule_value,
                is_active=True,
                description=description,
                created_at=SEEDED_AT,
                updated_at=SEEDED_AT,
            )
        )
        return

    rule.rule_value = rule_value
    rule.is_active = True
    rule.description = description
    rule.updated_at = SEEDED_AT


def seed_database(engine) -> None:
    apply_migrations(engine)

    with Session(engine) as session:
        _seed_users(session)
        _seed_homeworks(session)
        _seed_notices(session)
        _seed_system_settings(session)
        session.commit()
