import json

from sqlmodel import Session, create_engine, select
from sqlmodel.pool import StaticPool

from app.core.seed import seed_database
from app.models.schemas import (
    GradingRule,
    Homework,
    Notice,
    SystemSetting,
    User,
)
from app.services.auth_service import AuthService


def test_seed_creates_admin_and_sample_homework():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    seed_database(engine)
    seed_database(engine)

    with Session(engine) as session:
        admin = session.get(User, "admin")
        practice_user = session.get(User, "testuser")
        sample_homework = session.get(Homework, 1)
        sample_homework_rules = session.exec(
            select(GradingRule).where(
                GradingRule.scope == "homework",
                GradingRule.homework_num == 1,
                GradingRule.rule_name == "testcases",
            )
        ).all()
        welcome_notice = session.get(Notice, 1)
        lint_weight = session.get(SystemSetting, "lint_calc_weight")

        assert admin is not None
        assert admin.user_group == "admin"
        assert AuthService.verify_password("admin", admin.ps)

        assert practice_user is not None
        assert AuthService.verify_password("qwer1234", practice_user.ps)

        assert sample_homework is not None
        assert sample_homework.title == "Sample Problem: A+B"
        assert sample_homework.isLint is True
        assert len(sample_homework_rules) == 1
        testcase_payload = json.loads(sample_homework_rules[0].rule_value)
        assert [case["name"] for case in testcase_payload["cases"]] == [
            "sample-1",
            "hidden-1",
        ]
        assert sum(case["score"] for case in testcase_payload["cases"]) == 100

        assert welcome_notice is not None
        assert welcome_notice.is_pinned is True

        assert lint_weight is not None
        assert lint_weight.value == "50"

        assert (
            len(session.exec(select(User).where(User.id == "admin")).all()) == 1
        )
        assert (
            len(session.exec(select(Homework).where(Homework.num == 1)).all())
            == 1
        )
