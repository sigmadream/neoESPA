import csv
import io
import zipfile
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models.schemas import Homework, Submission, SubmissionResult, User
from app.services.auth_service import AuthService


engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def _dt_string(offset_days: int, offset_hours: int = 0) -> str:
    return (
        datetime.now(UTC) + timedelta(days=offset_days, hours=offset_hours)
    ).strftime("%Y-%m-%d %H:%M:%S")


def _create_user(
    session: Session,
    user_id: str,
    sid: int,
    password: str,
    role: str,
) -> User:
    user = User(
        id=user_id,
        sid=sid,
        ps=AuthService.get_password_hash(password),
        name=user_id,
        phone="010-0000-0000",
        email=f"{user_id}@example.com",
        user_group=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _create_homework(session: Session, num: int, title: str) -> Homework:
    homework = Homework(
        num=num,
        title=title,
        intro=f"{title} intro",
        starttime=_dt_string(-1),
        deadline=_dt_string(2),
        codeName="main",
    )
    session.add(homework)
    session.commit()
    session.refresh(homework)
    return homework


def _create_submission(
    session: Session,
    *,
    homework_num: int,
    user_id: str,
    attempt_no: int,
    language: str,
    code_text: str,
    original_filename: str,
    submitted_at: datetime,
    total_score: float,
    submission_score: float | None = None,
    quality_score: float = 0.0,
    manual_total_score: float | None = None,
) -> Submission:
    submission = Submission(
        homework_num=homework_num,
        user_id=user_id,
        submission_mode="official",
        attempt_no=attempt_no,
        language=language,
        status="graded",
        code_text=code_text,
        original_filename=original_filename,
        submitted_at=submitted_at,
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)

    session.add(
        SubmissionResult(
            submission_id=submission.id or 0,
            status="graded",
            compile_status="passed",
            run_status="passed",
            total_score=total_score,
            submission_score=total_score if submission_score is None else submission_score,
            quality_score=quality_score,
            grader_summary="Graded",
            manual_total_score=manual_total_score,
        )
    )
    session.commit()
    return submission


def _login(client: TestClient, user_id: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"id": user_id, "ps": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_grade_export_returns_csv():
    with Session(engine) as session:
        _create_homework(session, 1, "Export Homework")
        _create_user(session, "admin-export", 10009001, "admin-pass", "admin")
        _create_user(session, "student-one", 20249001, "student-pass", "student")
        _create_user(session, "student-two", 20249002, "student-pass", "student")

        now = datetime.now(UTC)
        _create_submission(
            session,
            homework_num=1,
            user_id="student-one",
            attempt_no=1,
            language="python",
            code_text="print('old')\n",
            original_filename="main.py",
            submitted_at=now - timedelta(minutes=5),
            total_score=30.0,
        )
        latest_submission = _create_submission(
            session,
            homework_num=1,
            user_id="student-one",
            attempt_no=2,
            language="python",
            code_text="print('new')\n",
            original_filename="main.py",
            submitted_at=now,
            total_score=110.0,
            submission_score=100.0,
            quality_score=10.0,
            manual_total_score=88.0,
        )
        other_submission = _create_submission(
            session,
            homework_num=1,
            user_id="student-two",
            attempt_no=1,
            language="cpp",
            code_text="#include <iostream>\nint main(){std::cout<<1;}\n",
            original_filename="answer.cpp",
            submitted_at=now - timedelta(minutes=1),
            total_score=70.0,
        )

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        admin_token = _login(client, "admin-export", "admin-pass")
        response = client.get(
            "/api/admin/homeworks/1/grades/export",
            headers=_auth_headers(admin_token),
        )

        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert 'homework_1_grades.csv' in response.headers["content-disposition"]

    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 2
    assert rows[0]["user_id"] == "student-one"
    assert rows[0]["submission_id"] == str(latest_submission.id)
    assert rows[0]["attempt_no"] == "2"
    assert rows[0]["total_score"] == "88.0"
    assert rows[0]["submission_score"] == "100.0"
    assert rows[0]["quality_score"] == "10.0"
    assert rows[0]["manual_total_score"] == "88.0"
    assert rows[1]["user_id"] == "student-two"
    assert rows[1]["submission_id"] == str(other_submission.id)
    assert rows[1]["total_score"] == "70.0"
    assert rows[1]["submission_score"] == "70.0"
    assert rows[1]["quality_score"] == "0.0"


def test_latest_submissions_can_be_downloaded_as_archive():
    with Session(engine) as session:
        _create_homework(session, 2, "Archive Homework")
        _create_user(session, "admin-archive", 10009002, "admin-pass", "admin")
        _create_user(session, "student-alpha", 20249003, "student-pass", "student")
        _create_user(session, "student-beta", 20249004, "student-pass", "student")

        now = datetime.now(UTC)
        _create_submission(
            session,
            homework_num=2,
            user_id="student-alpha",
            attempt_no=1,
            language="python",
            code_text="print('alpha-old')\n",
            original_filename="main.py",
            submitted_at=now - timedelta(minutes=10),
            total_score=40.0,
        )
        _create_submission(
            session,
            homework_num=2,
            user_id="student-alpha",
            attempt_no=2,
            language="python",
            code_text="print('alpha-new')\n",
            original_filename="main.py",
            submitted_at=now - timedelta(minutes=1),
            total_score=95.0,
        )
        _create_submission(
            session,
            homework_num=2,
            user_id="student-beta",
            attempt_no=1,
            language="cpp",
            code_text="#include <iostream>\nint main(){std::cout<<\"beta\";}\n",
            original_filename="answer.cpp",
            submitted_at=now - timedelta(minutes=2),
            total_score=77.0,
        )

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        admin_token = _login(client, "admin-archive", "admin-pass")
        response = client.get(
            "/api/admin/homeworks/2/submissions/archive",
            headers=_auth_headers(admin_token),
        )

        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert 'homework_2_latest_submissions.zip' in response.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = sorted(archive.namelist())
        assert names == [
            "homework_2/20249003_student-alpha/attempt_2_main.py",
            "homework_2/20249004_student-beta/attempt_1_answer.cpp",
        ]
        assert (
            archive.read("homework_2/20249003_student-alpha/attempt_2_main.py").decode(
                "utf-8"
            )
            == "print('alpha-new')\n"
        )
        assert (
            archive.read(
                "homework_2/20249004_student-beta/attempt_1_answer.cpp"
            ).decode("utf-8")
            == '#include <iostream>\nint main(){std::cout<<"beta";}\n'
        )
