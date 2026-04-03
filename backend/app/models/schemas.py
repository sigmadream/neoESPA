from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Column, Index, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_string() -> str:
    return utc_now().strftime("%Y-%m-%d %H:%M:%S")


class UserProfile(SQLModel):
    id: str = Field(primary_key=True, max_length=50)
    sid: int = Field(unique=True)
    name: str = Field(max_length=100)
    phone: str = Field(max_length=50)
    email: str = Field(max_length=255)
    user_group: str = Field(default="student", max_length=20)


class User(UserProfile, table=True):
    __tablename__ = "users"

    ps: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class UserCreate(UserProfile):
    ps: str


class UserLogin(SQLModel):
    id: str
    ps: str


class UserRead(UserProfile):
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserProfileUpdate(SQLModel):
    name: str
    phone: str
    email: str


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"


class PasswordChangeRequest(SQLModel):
    current_password: str
    new_password: str


class UserStatusUpdate(SQLModel):
    is_active: bool


class AdminPasswordResetRequest(SQLModel):
    new_password: str


class UserRoleUpdate(SQLModel):
    user_group: str


class AdminUserWrite(UserProfile):
    ps: Optional[str] = None
    is_active: bool = True


class BulkUserCreateRequest(SQLModel):
    users: list[AdminUserWrite] = []
    default_password: str = "welcome1234"
    skip_existing: bool = True


class BulkUserCreateResult(SQLModel):
    created_count: int
    skipped_count: int
    created_users: list[UserRead] = []
    skipped_ids: list[str] = []


class SystemSettingRead(SQLModel):
    key: str
    value: str
    value_type: str
    description: Optional[str] = None
    updated_at: datetime


class SystemSettingUpdate(SQLModel):
    key: str
    value: str | float | int | bool


class SystemSettingsUpdateRequest(SQLModel):
    settings: list[SystemSettingUpdate] = []


class AssignmentBase(SQLModel):
    title: str = Field(max_length=200)
    intro: str
    codeName: str = Field(max_length=100)
    starttime: Optional[str] = Field(default=None, max_length=50)
    deadline: Optional[str] = Field(default=None, max_length=50)


class HomeworkBase(AssignmentBase):
    pass


class Homework(HomeworkBase, table=True):
    __tablename__ = "homework"

    num: Optional[int] = Field(default=None, primary_key=True)
    intro: str = Field(sa_column=Column(Text, nullable=False))
    filename: Optional[str] = Field(default=None, max_length=255)
    ratedatanum: int = Field(default=0)
    sec: int = Field(default=1)
    sbnum: int = Field(default=10)
    isDetected: bool = Field(default=False)
    vitalSpace: bool = Field(default=False)
    disorderedOutput: bool = Field(default=False)
    isLint: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class HomeworkAdminCreate(HomeworkBase):
    filename: Optional[str] = None
    ratedatanum: int = 0
    sec: int = 1
    sbnum: int = 10
    isDetected: bool = False
    vitalSpace: bool = False
    disorderedOutput: bool = False
    isLint: bool = False


class HomeworkTestCaseWrite(SQLModel):
    name: str
    input: str = ""
    expected_output: str
    score: float = 0.0
    is_hidden: bool = False


class HomeworkAdminWrite(HomeworkAdminCreate):
    allowed_languages: list[str] = []
    testcases: list[HomeworkTestCaseWrite] = []
    lint_week: Optional[str] = None


class AssignmentRead(AssignmentBase):
    schedule_status: str
    can_submit: bool


class HomeworkRead(AssignmentRead):
    num: int
    filename: Optional[str] = None
    ratedatanum: int
    sec: int
    sbnum: int
    isDetected: bool
    vitalSpace: bool
    disorderedOutput: bool
    isLint: bool
    allowed_languages: list[str] = []


class HomeworkAdminRead(HomeworkRead):
    testcases: list[HomeworkTestCaseWrite] = []
    lint_week: Optional[str] = None
    problem_file_name: Optional[str] = None
    input_zip_name: Optional[str] = None
    output_zip_name: Optional[str] = None
    parsed_testcase_count: int = 0


class Notice(SQLModel, table=True):
    __tablename__ = "notice"

    num: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    author: str = Field(max_length=100)
    content: str = Field(sa_column=Column(Text, nullable=False))
    date: str = Field(default_factory=utc_now_string)
    is_pinned: bool = Field(default=False)
    is_published: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=utc_now)


class NoticeRead(SQLModel):
    num: int
    title: str
    author: str
    content: str
    date: str
    is_pinned: bool
    is_published: bool


class NoticeAdminWrite(SQLModel):
    title: str
    author: str
    content: str
    date: Optional[str] = None
    is_pinned: bool = False
    is_published: bool = True


class Submission(SQLModel, table=True):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint(
            "homework_num",
            "user_id",
            "submission_mode",
            "attempt_no",
            name="uq_submission_attempt",
        ),
        Index("ix_submissions_homework_user", "homework_num", "user_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    homework_num: int = Field(foreign_key="homework.num", nullable=False)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    submission_mode: str = Field(default="official", max_length=20)
    attempt_no: int = Field(default=1, ge=1)
    language: str = Field(max_length=20)
    status: str = Field(default="pending", max_length=20)
    code_text: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    original_filename: Optional[str] = Field(default=None, max_length=255)
    storage_path: Optional[str] = Field(default=None, max_length=500)
    deadline_snapshot: Optional[str] = Field(default=None, max_length=50)
    submitted_at: datetime = Field(default_factory=utc_now)


class SubmissionCreate(SQLModel):
    homework_num: int
    language: str
    code_text: Optional[str] = None
    original_filename: Optional[str] = None


class SubmissionRead(SQLModel):
    id: int
    homework_num: int
    homework_title: Optional[str] = None
    user_id: str
    submission_mode: str
    attempt_no: int
    language: str
    status: str
    original_filename: Optional[str] = None
    deadline_snapshot: Optional[str] = None
    submitted_at: datetime
    total_score: float = 0.0
    submission_score: float = 0.0
    quality_score: float = 0.0
    compile_status: str = "not_started"
    run_status: str = "not_started"
    grader_summary: Optional[str] = None
    manual_total_score: Optional[float] = None
    score_adjustment_note: Optional[str] = None
    score_adjusted_at: Optional[datetime] = None
    score_adjusted_by: Optional[str] = None


class StudentDashboardOverview(SQLModel):
    total_homeworks: int
    submitted_homeworks: int
    graded_homeworks: int
    pending_homeworks: int
    missing_homeworks: int
    closing_soon_homeworks: int
    average_latest_score: Optional[float] = None


class StudentDashboardHomeworkItem(SQLModel):
    homework_num: int
    title: str
    deadline: Optional[str] = None
    starttime: Optional[str] = None
    schedule_status: str
    can_submit: bool
    submission_count: int = 0
    latest_submission_id: Optional[int] = None
    latest_submission_status: Optional[str] = None
    latest_submission_at: Optional[datetime] = None
    latest_score: Optional[float] = None
    latest_language: Optional[str] = None
    remaining_seconds: Optional[int] = None
    grader_summary: Optional[str] = None


class StudentDashboardRead(SQLModel):
    generated_at: datetime
    overview: StudentDashboardOverview
    homework_items: list[StudentDashboardHomeworkItem] = []
    recent_submissions: list[SubmissionRead] = []


class SubmissionScoreAdjustRequest(SQLModel):
    manual_total_score: float
    adjustment_note: Optional[str] = None


class CodeSnapshot(SQLModel, table=True):
    __tablename__ = "code_snapshots"
    __table_args__ = (
        Index("ix_code_snapshots_homework_user_created", "homework_num", "user_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    homework_num: int = Field(foreign_key="homework.num", nullable=False)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    language: str = Field(max_length=20)
    code_text: str = Field(sa_column=Column(Text, nullable=False))
    snapshot_type: str = Field(default="auto_save", max_length=20)
    created_at: datetime = Field(default_factory=utc_now)


class CodeSnapshotCreate(SQLModel):
    homework_num: int
    language: str
    code_text: str
    snapshot_type: str = "auto_save"


class CodeSnapshotRead(SQLModel):
    id: int
    homework_num: int
    user_id: str
    language: str
    code_text: str
    snapshot_type: str
    created_at: datetime


class SubmissionFile(SQLModel, table=True):
    __tablename__ = "submission_files"
    __table_args__ = (
        Index("ix_submission_files_submission_kind", "submission_id", "artifact_kind"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submissions.id", nullable=False)
    artifact_kind: str = Field(max_length=32)
    file_name: Optional[str] = Field(default=None, max_length=255)
    storage_path: str = Field(max_length=500)
    content_type: Optional[str] = Field(default=None, max_length=100)
    size_bytes: Optional[int] = None
    text_excerpt: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    created_at: datetime = Field(default_factory=utc_now)


class SubmissionResult(SQLModel, table=True):
    __tablename__ = "submission_results"
    __table_args__ = (
        UniqueConstraint("submission_id", name="uq_submission_result_submission"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submissions.id", nullable=False)
    status: str = Field(default="pending", max_length=20)
    compile_status: str = Field(default="not_started", max_length=20)
    run_status: str = Field(default="not_started", max_length=20)
    total_score: float = Field(default=0.0)
    submission_score: float = Field(default=0.0)
    quality_score: float = Field(default=0.0)
    passed_case_count: int = Field(default=0)
    total_case_count: int = Field(default=0)
    exit_code: Optional[int] = None
    runtime_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    plagiarism_flag: bool = Field(default=False)
    compile_log: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    runtime_log: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    grader_summary: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    manual_total_score: Optional[float] = Field(default=None)
    adjustment_note: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    adjusted_at: Optional[datetime] = Field(default=None)
    adjusted_by: Optional[str] = Field(default=None, max_length=50)
    graded_at: Optional[datetime] = Field(default=None)


class SubmissionCaseResult(SQLModel, table=True):
    __tablename__ = "submission_case_results"
    __table_args__ = (
        UniqueConstraint(
            "submission_id", "case_index", name="uq_submission_case_index"
        ),
        Index("ix_submission_case_results_submission", "submission_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submissions.id", nullable=False)
    case_index: int = Field(ge=1)
    case_name: str = Field(max_length=100)
    is_hidden: bool = Field(default=False)
    passed: bool = Field(default=False)
    score_awarded: float = Field(default=0.0)
    runtime_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    message: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))


class GradingRule(SQLModel, table=True):
    __tablename__ = "grading_rules"
    __table_args__ = (
        UniqueConstraint(
            "scope", "homework_num", "rule_name", name="uq_grading_rule_scope_name"
        ),
        Index("ix_grading_rules_scope_homework", "scope", "homework_num"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    scope: str = Field(default="system", max_length=20)
    homework_num: Optional[int] = Field(default=None, foreign_key="homework.num")
    rule_name: str = Field(max_length=100)
    rule_value: str = Field(sa_column=Column(Text, nullable=False))
    is_active: bool = Field(default=True)
    description: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SystemSetting(SQLModel, table=True):
    __tablename__ = "system_settings"

    key: str = Field(primary_key=True, max_length=100)
    value: str = Field(sa_column=Column(Text, nullable=False))
    value_type: str = Field(default="string", max_length=20)
    description: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    updated_at: datetime = Field(default_factory=utc_now)


class SystemEventLogRead(SQLModel):
    id: int
    category: str
    level: str
    event_type: str
    message: str
    submission_id: Optional[int] = None
    user_id: Optional[str] = None
    request_path: Optional[str] = None
    context_json: Optional[str] = None
    created_at: datetime


class SystemEventLog(SQLModel, table=True):
    __tablename__ = "system_event_logs"
    __table_args__ = (
        Index("ix_system_event_logs_category_created", "category", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    category: str = Field(max_length=40)
    level: str = Field(default="info", max_length=20)
    event_type: str = Field(max_length=80)
    message: str = Field(sa_column=Column(Text, nullable=False))
    submission_id: Optional[int] = Field(default=None, foreign_key="submissions.id")
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    request_path: Optional[str] = Field(default=None, max_length=255)
    context_json: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    created_at: datetime = Field(default_factory=utc_now)


class AuditLogRead(SQLModel):
    id: int
    actor_user_id: Optional[str] = None
    action_type: str
    target_type: str
    target_id: Optional[str] = None
    payload_json: Optional[str] = None
    created_at: datetime


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_action_created", "action_type", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    actor_user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    action_type: str = Field(max_length=80)
    target_type: str = Field(max_length=80)
    target_id: Optional[str] = Field(default=None, max_length=120)
    payload_json: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    created_at: datetime = Field(default_factory=utc_now)


class NotificationRead(SQLModel):
    id: int
    kind: str
    title: str
    message: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    is_read: bool
    created_at: datetime


class NotificationMarkReadRequest(SQLModel):
    notification_ids: list[int] = []


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    kind: str = Field(max_length=50)
    title: str = Field(max_length=200)
    message: str = Field(sa_column=Column(Text, nullable=False))
    reference_type: Optional[str] = Field(default=None, max_length=50)
    reference_id: Optional[str] = Field(default=None, max_length=120)
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)


class LectureMaterialBase(SQLModel):
    title: str = Field(max_length=200)
    description: str = Field(sa_column=Column(Text, nullable=False))
    url: str = Field(max_length=500)
    is_published: bool = True


class LectureMaterial(LectureMaterialBase, table=True):
    __tablename__ = "lecture_materials"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_by: str = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class LectureMaterialWrite(LectureMaterialBase):
    pass


class LectureMaterialRead(LectureMaterialBase):
    id: int
    created_by: str
    created_at: datetime
    updated_at: datetime


class AdminDashboardHomeworkMetric(SQLModel):
    homework_num: int
    title: str
    submission_rate: float
    total_students: int
    submitted_students: int
    average_latest_score: Optional[float] = None
    failed_submission_count: int = 0
    pending_submission_count: int = 0


class AdminDashboardFailureMetric(SQLModel):
    failure_type: str
    count: int


class AdminDashboardQueueStatus(SQLModel):
    queue_size: int
    queued_submission_ids: list[int] = []


class AdminDashboardRead(SQLModel):
    generated_at: datetime
    total_homeworks: int
    active_students: int
    total_submissions: int
    queue: AdminDashboardQueueStatus
    homework_metrics: list[AdminDashboardHomeworkMetric] = []
    failure_metrics: list[AdminDashboardFailureMetric] = []
    recent_events: list[SystemEventLogRead] = []


class CodingRuleGuideItem(SQLModel):
    rule: str
    tool: str
    summary: str
    description: str


class SubmissionFeedbackRead(SQLModel):
    submission_id: int
    deadline_status: str
    deadline_message: str
    latest_notice: Optional[NoticeRead] = None
    hints: list[str] = []
    coding_rule_guides: list[CodingRuleGuideItem] = []


class PlagiarismRunRead(SQLModel):
    id: int
    homework_num: int
    created_by: str
    status: str
    compared_submission_count: int
    flagged_pair_count: int
    summary: Optional[str] = None
    created_at: datetime


class PlagiarismPairRead(SQLModel):
    id: int
    run_id: int
    homework_num: int
    left_submission_id: int
    right_submission_id: int
    left_user_id: str
    right_user_id: str
    similarity_score: float
    status: str
    summary: Optional[str] = None
    left_code: Optional[str] = None
    right_code: Optional[str] = None
    created_at: datetime


class PlagiarismRun(SQLModel, table=True):
    __tablename__ = "plagiarism_runs"
    __table_args__ = (
        Index("ix_plagiarism_runs_homework_created", "homework_num", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    homework_num: int = Field(foreign_key="homework.num", nullable=False)
    created_by: str = Field(foreign_key="users.id", nullable=False)
    status: str = Field(default="completed", max_length=30)
    compared_submission_count: int = Field(default=0)
    flagged_pair_count: int = Field(default=0)
    summary: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=utc_now)


class PlagiarismPair(SQLModel, table=True):
    __tablename__ = "plagiarism_pairs"
    __table_args__ = (
        Index("ix_plagiarism_pairs_run_similarity", "run_id", "similarity_score"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="plagiarism_runs.id", nullable=False)
    homework_num: int = Field(foreign_key="homework.num", nullable=False)
    left_submission_id: int = Field(foreign_key="submissions.id", nullable=False)
    right_submission_id: int = Field(foreign_key="submissions.id", nullable=False)
    left_user_id: str = Field(foreign_key="users.id", nullable=False)
    right_user_id: str = Field(foreign_key="users.id", nullable=False)
    similarity_score: float = Field(default=0.0)
    status: str = Field(default="flagged", max_length=30)
    summary: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=utc_now)


class CollabSessionCreate(SQLModel):
    title: str
    homework_num: Optional[int] = None
    initial_code: str = ""
    participant_ids: list[str] = []


class CollabCodeUpdate(SQLModel):
    code: str


class CollabChatWrite(SQLModel):
    content: str


class CollabParticipantRead(SQLModel):
    user_id: str
    role: str
    can_edit: bool
    joined_at: datetime
    left_at: Optional[datetime] = None


class CollabSessionRead(SQLModel):
    id: int
    title: str
    homework_num: Optional[int] = None
    mentor_id: str
    status: str
    current_code: str
    participants: list[CollabParticipantRead] = []
    created_at: datetime
    closed_at: Optional[datetime] = None


class CollabMessageRead(SQLModel):
    id: int
    session_id: int
    user_id: str
    content: str
    created_at: datetime


class CollabCodeSnapshotRead(SQLModel):
    id: int
    session_id: int
    user_id: Optional[str] = None
    code_text: str
    created_at: datetime


class CollabHistoryRead(SQLModel):
    session: CollabSessionRead
    messages: list[CollabMessageRead] = []
    code_snapshots: list[CollabCodeSnapshotRead] = []


class CollabSession(SQLModel, table=True):
    __tablename__ = "collab_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    homework_num: Optional[int] = Field(default=None, foreign_key="homework.num")
    mentor_id: str = Field(foreign_key="users.id", nullable=False)
    status: str = Field(default="active", max_length=30)
    current_code: str = Field(default="", sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utc_now)
    closed_at: Optional[datetime] = Field(default=None)


class CollabParticipant(SQLModel, table=True):
    __tablename__ = "collab_participants"
    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_collab_session_user"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="collab_sessions.id", nullable=False)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    role: str = Field(default="member", max_length=30)
    can_edit: bool = Field(default=True)
    joined_at: datetime = Field(default_factory=utc_now)
    left_at: Optional[datetime] = Field(default=None)


class CollabMessage(SQLModel, table=True):
    __tablename__ = "collab_messages"
    __table_args__ = (
        Index("ix_collab_messages_session_created", "session_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="collab_sessions.id", nullable=False)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    content: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utc_now)


class CollabCodeSnapshot(SQLModel, table=True):
    __tablename__ = "collab_code_snapshots"
    __table_args__ = (
        Index("ix_collab_code_snapshots_session_created", "session_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="collab_sessions.id", nullable=False)
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    code_text: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utc_now)


class ExamBase(AssignmentBase):
    pass


class ExamWrite(ExamBase):
    allowed_languages: list[str] = []


class ExamRead(AssignmentRead):
    id: int
    allowed_languages: list[str] = []
    created_by: str
    created_at: datetime
    updated_at: datetime


class Exam(ExamBase, table=True):
    __tablename__ = "exams"

    id: Optional[int] = Field(default=None, primary_key=True)
    intro: str = Field(sa_column=Column(Text, nullable=False))
    allowed_languages_json: str = Field(
        default="[]", sa_column=Column(Text, nullable=False)
    )
    created_by: str = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ExamSubmissionCreate(SQLModel):
    language: str
    code_text: str
    original_filename: Optional[str] = None


class ExamSubmissionRead(SQLModel):
    id: int
    exam_id: int
    user_id: str
    language: str
    status: str
    original_filename: Optional[str] = None
    submitted_at: datetime


class ExamSubmission(SQLModel, table=True):
    __tablename__ = "exam_submissions"
    __table_args__ = (Index("ix_exam_submissions_exam_user", "exam_id", "user_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    exam_id: int = Field(foreign_key="exams.id", nullable=False)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    language: str = Field(max_length=20)
    code_text: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(default="submitted", max_length=30)
    original_filename: Optional[str] = Field(default=None, max_length=255)
    submitted_at: datetime = Field(default_factory=utc_now)


class ExamResult(SQLModel, table=True):
    __tablename__ = "exam_results"
    __table_args__ = (
        UniqueConstraint("exam_submission_id", name="uq_exam_result_submission"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    exam_submission_id: int = Field(foreign_key="exam_submissions.id", nullable=False)
    total_score: float = Field(default=0.0)
    graded_at: Optional[datetime] = Field(default=None)
