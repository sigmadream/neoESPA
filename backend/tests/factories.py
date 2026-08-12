from datetime import UTC, datetime, timedelta

from app.core.compression import compress_text
from app.models.schemas import Homework, Submission, SubmissionResult, User
from app.services.auth_service import AuthService


def dt_string(offset_days: int, offset_hours: int = 0) -> str:
    return (
        datetime.now(UTC) + timedelta(days=offset_days, hours=offset_hours)
    ).strftime("%Y-%m-%d %H:%M:%S")


def create_user(
    session,
    user_id,
    sid,
    password="password",
    role="student",
    is_active=True,
    name=None,
    phone="010-0000-0000",
    email=None,
):
    user = User(
        id=user_id,
        sid=sid,
        ps=AuthService.get_password_hash(password),
        name=name or user_id,
        phone=phone,
        email=email or f"{user_id}@example.com",
        user_group=role,
        is_active=is_active,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_homework(
    session,
    num,
    title,
    start_offset_days=-1,
    deadline_offset_days=2,
    intro=None,
    code_name="main",
    starttime=None,
    deadline=None,
):
    homework = Homework(
        num=num,
        title=title,
        intro=intro or f"{title} intro",
        starttime=starttime or dt_string(start_offset_days),
        deadline=deadline or dt_string(deadline_offset_days),
        codeName=code_name,
    )
    session.add(homework)
    session.commit()
    session.refresh(homework)
    return homework


def create_submission(
    session,
    *,
    homework_num,
    user_id,
    attempt_no=1,
    language="python",
    code_text="print('ok')\n",
    original_filename=None,
    submitted_at=None,
    submission_mode="official",
    status="pending",
    deadline_snapshot=None,
    stored_compressed=False,
    storage_path=None,
):
    submission = Submission(
        homework_num=homework_num,
        user_id=user_id,
        submission_mode=submission_mode,
        attempt_no=attempt_no,
        language=language,
        status=status,
        code_text=compress_text(code_text) if stored_compressed else code_text,
        original_filename=original_filename,
        storage_path=storage_path,
        deadline_snapshot=deadline_snapshot,
        submitted_at=submitted_at or datetime.now(UTC),
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)
    return submission


def create_submission_result(
    session,
    submission_id,
    *,
    status="graded",
    compile_status="passed",
    run_status="passed",
    total_score=0.0,
    submission_score=None,
    quality_score=0.0,
    passed_case_count=0,
    total_case_count=0,
    grader_summary=None,
    manual_total_score=None,
    adjustment_note=None,
    adjusted_at=None,
    adjusted_by=None,
    graded_at=None,
):
    result = SubmissionResult(
        submission_id=submission_id,
        status=status,
        compile_status=compile_status,
        run_status=run_status,
        total_score=total_score,
        submission_score=total_score if submission_score is None else submission_score,
        quality_score=quality_score,
        passed_case_count=passed_case_count,
        total_case_count=total_case_count,
        grader_summary=grader_summary,
        manual_total_score=manual_total_score,
        adjustment_note=adjustment_note,
        adjusted_at=adjusted_at,
        adjusted_by=adjusted_by,
        graded_at=graded_at,
    )
    session.add(result)
    session.commit()
    session.refresh(result)
    return result
