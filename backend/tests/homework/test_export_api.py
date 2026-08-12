import csv
import io
import zipfile
from datetime import UTC, datetime, timedelta

from app.core.compression import decompress_text


def test_grade_export_returns_csv(
    client,
    create_user,
    create_homework,
    create_submission,
    create_submission_result,
    login_user,
    auth_headers,
):
    create_homework(1, "Export Homework")
    create_user("admin-export", 10009001, "admin-pass", "admin")
    create_user("student-one", 20249001, "student-pass", "student")
    create_user("student-two", 20249002, "student-pass", "student")

    now = datetime.now(UTC)
    first_submission = create_submission(
        homework_num=1,
        user_id="student-one",
        attempt_no=1,
        language="python",
        code_text="print('old')\n",
        original_filename="main.py",
        submitted_at=now - timedelta(minutes=5),
        status="graded",
    )
    create_submission_result(
        first_submission.id or 0,
        total_score=30.0,
        grader_summary="Graded",
    )

    latest_submission = create_submission(
        homework_num=1,
        user_id="student-one",
        attempt_no=2,
        language="python",
        code_text="print('new')\n",
        original_filename="main.py",
        submitted_at=now,
        status="graded",
    )
    create_submission_result(
        latest_submission.id or 0,
        total_score=110.0,
        submission_score=100.0,
        quality_score=10.0,
        grader_summary="Graded",
        manual_total_score=88.0,
    )

    other_submission = create_submission(
        homework_num=1,
        user_id="student-two",
        attempt_no=1,
        language="cpp",
        code_text="#include <iostream>\nint main(){std::cout<<1;}\n",
        original_filename="answer.cpp",
        submitted_at=now - timedelta(minutes=1),
        status="graded",
    )
    create_submission_result(
        other_submission.id or 0,
        total_score=70.0,
        grader_summary="Graded",
    )

    admin_token = login_user("admin-export", "admin-pass")
    response = client.get(
        "/api/admin/homeworks/1/grades/export",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "homework_1_grades.csv" in response.headers["content-disposition"]

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


def test_latest_submissions_can_be_downloaded_as_archive(
    client,
    create_user,
    create_homework,
    create_submission,
    create_submission_result,
    login_user,
    auth_headers,
):
    create_homework(2, "Archive Homework")
    create_user("admin-archive", 10009002, "admin-pass", "admin")
    create_user("student-alpha", 20249003, "student-pass", "student")
    create_user("student-beta", 20249004, "student-pass", "student")

    now = datetime.now(UTC)
    alpha_old_submission = create_submission(
        homework_num=2,
        user_id="student-alpha",
        attempt_no=1,
        language="python",
        code_text="print('alpha-old')\n",
        original_filename="main.py",
        submitted_at=now - timedelta(minutes=10),
        status="graded",
    )
    create_submission_result(
        alpha_old_submission.id or 0,
        total_score=40.0,
        grader_summary="Graded",
    )

    latest_alpha_submission = create_submission(
        homework_num=2,
        user_id="student-alpha",
        attempt_no=2,
        language="python",
        code_text="print('alpha-new')\n",
        original_filename="main.py",
        submitted_at=now - timedelta(minutes=1),
        status="graded",
        stored_compressed=True,
    )
    create_submission_result(
        latest_alpha_submission.id or 0,
        total_score=95.0,
        grader_summary="Graded",
    )

    beta_submission = create_submission(
        homework_num=2,
        user_id="student-beta",
        attempt_no=1,
        language="cpp",
        code_text='#include <iostream>\nint main(){std::cout<<"beta";}\n',
        original_filename="answer.cpp",
        submitted_at=now - timedelta(minutes=2),
        status="graded",
    )
    create_submission_result(
        beta_submission.id or 0,
        total_score=77.0,
        grader_summary="Graded",
    )

    admin_token = login_user("admin-archive", "admin-pass")
    response = client.get(
        "/api/admin/homeworks/2/submissions/archive",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert (
        "homework_2_latest_submissions.zip"
        in response.headers["content-disposition"]
    )
    assert latest_alpha_submission.code_text != "print('alpha-new')\n"
    assert (
        decompress_text(latest_alpha_submission.code_text)
        == "print('alpha-new')\n"
    )
    assert (
        beta_submission.code_text
        == '#include <iostream>\nint main(){std::cout<<"beta";}\n'
    )

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = sorted(archive.namelist())
        assert names == [
            "homework_2/20249003_student-alpha/attempt_2_main.py",
            "homework_2/20249004_student-beta/attempt_1_answer.cpp",
        ]
        assert (
            archive.read(
                "homework_2/20249003_student-alpha/attempt_2_main.py"
            ).decode("utf-8")
            == "print('alpha-new')\n"
        )
        assert (
            archive.read(
                "homework_2/20249004_student-beta/attempt_1_answer.cpp"
            ).decode("utf-8")
            == '#include <iostream>\nint main(){std::cout<<"beta";}\n'
        )
