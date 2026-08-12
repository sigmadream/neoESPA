from datetime import UTC, datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import Column, Index, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_string() -> str:
    return utc_now().strftime("%Y-%m-%d %H:%M:%S")


class JudgeVerdict(StrEnum):
    AC = "AC"
    WA = "WA"
    TLE = "TLE"
    MLE = "MLE"
    OLE = "OLE"
    RE = "RE"
    CE = "CE"
    PE = "PE"
    IE = "IE"
    JG = "JG"


class UserProfile(SQLModel):
    id: str = Field(primary_key=True, max_length=50)
    sid: int = Field(unique=True)
    name: str = Field(max_length=100)
    phone: str = Field(max_length=50)
    email: str = Field(max_length=255)
    user_group: str = Field(default="student", max_length=20)
    organization_id: Optional[str] = Field(
        default=None, max_length=80, index=True
    )


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


class RoleCapability(SQLModel, table=True):
    __tablename__ = "role_capabilities"
    __table_args__ = (
        UniqueConstraint("role_name", "capability", name="uq_role_capability"),
        Index("ix_role_capabilities_role", "role_name"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    role_name: str = Field(max_length=40)
    capability: str = Field(max_length=80)


class RoleCapabilitiesUpdate(SQLModel):
    capabilities: list[str] = Field(default_factory=list)


class RoleCapabilitiesRead(SQLModel):
    role_name: str
    capabilities: list[str]


class ProblemCollaborator(SQLModel, table=True):
    __tablename__ = "problem_collaborators"
    __table_args__ = (
        UniqueConstraint(
            "problem_id", "user_id", name="uq_problem_collaborator"
        ),
        Index("ix_problem_collaborators_user", "user_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    problem_id: int = Field(foreign_key="problems.id", nullable=False)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    can_edit: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)


class ProblemCollaboratorCreate(SQLModel):
    user_id: str
    can_edit: bool = True


class ProblemCollaboratorRead(ProblemCollaboratorCreate):
    id: int
    problem_id: int
    created_at: datetime


class AnalyticsConsent(SQLModel, table=True):
    __tablename__ = "analytics_consents"
    __table_args__ = (
        Index("ix_analytics_consent_user_created", "user_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    granted: bool
    purpose: str = Field(max_length=120)
    policy_version: str = Field(max_length=40)
    scope_json: str = Field(
        default="[]", sa_column=Column(Text, nullable=False)
    )
    created_at: datetime = Field(default_factory=utc_now)


class AnalyticsConsentCreate(SQLModel):
    granted: bool
    purpose: str = Field(min_length=1, max_length=120)
    policy_version: str = Field(min_length=1, max_length=40)
    scopes: list[str] = Field(default_factory=list)


class AnalyticsConsentRead(SQLModel):
    id: int
    user_id: str
    granted: bool
    purpose: str
    policy_version: str
    scopes: list[str]
    created_at: datetime


class AdminInvitation(SQLModel, table=True):
    __tablename__ = "admin_invitations"

    id: Optional[int] = Field(default=None, primary_key=True)
    token_hash: str = Field(unique=True, max_length=64)
    email: str = Field(max_length=255, index=True)
    role_name: str = Field(max_length=40)
    created_by: str = Field(foreign_key="users.id", nullable=False)
    expires_at: datetime
    used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)


class AdminInvitationCreate(SQLModel):
    email: str = Field(min_length=3, max_length=255)
    role_name: str = Field(min_length=1, max_length=40)
    ttl_minutes: int = Field(default=1440, ge=1, le=10080)


class AdminInvitationIssued(SQLModel):
    id: int
    token: str
    email: str
    role_name: str
    expires_at: datetime


class AdminInvitationAccept(SQLModel):
    token: str
    id: str = Field(min_length=1, max_length=50)
    sid: int
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(max_length=50)
    password: str = Field(min_length=8, max_length=255)


class AdminAuthAssurance(SQLModel, table=True):
    __tablename__ = "admin_auth_assurance"

    user_id: str = Field(primary_key=True, foreign_key="users.id")
    mfa_required: bool = Field(default=False)
    mfa_enrolled: bool = Field(default=False)
    mfa_method: Optional[str] = Field(default=None, max_length=20)
    updated_at: datetime = Field(default_factory=utc_now)


class AdminAuthAssuranceRead(SQLModel):
    mfa_required: bool
    mfa_enrolled: bool
    mfa_method: Optional[str] = None


class StepUpRequest(SQLModel):
    password: str


class AdminUserWrite(UserProfile):
    ps: Optional[str] = None
    is_active: bool = True


class AdminBootstrapToken(SQLModel, table=True):
    __tablename__ = "admin_bootstrap_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    token_hash: str = Field(unique=True, max_length=64)
    expires_at: datetime = Field(index=True)
    used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)


class AdminBootstrapCreate(SQLModel):
    token: str = Field(min_length=32)
    id: str = Field(min_length=1, max_length=50)
    sid: int
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=12)


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


PROBLEM_REVISION_STATUSES = (
    "draft",
    "validating",
    "ready",
    "published",
    "archived",
)


class Problem(SQLModel, table=True):
    __tablename__ = "problems"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, max_length=80, index=True)
    title: str = Field(max_length=200)
    owner_id: Optional[str] = Field(
        default=None, foreign_key="users.id", index=True
    )
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProblemRevision(SQLModel, table=True):
    __tablename__ = "problem_revisions"
    __table_args__ = (
        UniqueConstraint(
            "problem_id", "revision_no", name="uq_problem_revision_no"
        ),
        Index("ix_problem_revisions_problem_status", "problem_id", "status"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    problem_id: int = Field(foreign_key="problems.id", nullable=False)
    revision_no: int = Field(ge=1)
    statement: str = Field(default="", sa_column=Column(Text, nullable=False))
    input_description: str = Field(
        default="", sa_column=Column(Text, nullable=False)
    )
    output_description: str = Field(
        default="", sa_column=Column(Text, nullable=False)
    )
    time_limit_ms: int = Field(default=1000, ge=1)
    memory_limit_mb: int = Field(default=256, ge=1)
    output_limit_kb: int = Field(default=1024, ge=1)
    process_limit: int = Field(default=1, ge=1)
    source_limit_kb: int = Field(default=1024, ge=1)
    checker_type: str = Field(default="token", max_length=40)
    problem_mode: str = Field(default="standard", max_length=20)
    checker_config_json: str = Field(
        default="{}", sa_column=Column(Text, nullable=False)
    )
    language_multipliers_json: str = Field(
        default="{}", sa_column=Column(Text, nullable=False)
    )
    allowed_languages_json: str = Field(
        default='["c", "cpp", "python", "java"]',
        sa_column=Column(Text, nullable=False),
    )
    status: str = Field(default="draft", max_length=20, index=True)
    validation_report: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    created_by: Optional[str] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    published_at: Optional[datetime] = None


class ProblemRevisionApproval(SQLModel, table=True):
    __tablename__ = "problem_revision_approvals"
    __table_args__ = (
        UniqueConstraint(
            "revision_id", "reviewer_id", name="uq_revision_reviewer_approval"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    revision_id: int = Field(
        foreign_key="problem_revisions.id", nullable=False, index=True
    )
    reviewer_id: str = Field(foreign_key="users.id", nullable=False)
    decision: str = Field(default="approved", max_length=20)
    note: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    created_at: datetime = Field(default_factory=utc_now)


class ProblemRevisionApprovalCreate(SQLModel):
    decision: str = "approved"
    note: Optional[str] = Field(default=None, max_length=1000)


class ProblemRevisionApprovalRead(ProblemRevisionApprovalCreate):
    id: int
    revision_id: int
    reviewer_id: str
    created_at: datetime


class ProblemAsset(SQLModel, table=True):
    __tablename__ = "problem_assets"
    __table_args__ = (
        UniqueConstraint(
            "revision_id",
            "asset_kind",
            "display_name",
            name="uq_problem_asset_name",
        ),
        Index("ix_problem_assets_revision_kind", "revision_id", "asset_kind"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    revision_id: int = Field(foreign_key="problem_revisions.id", nullable=False)
    asset_kind: str = Field(max_length=40)
    display_name: str = Field(max_length=255)
    storage_path: str = Field(max_length=500)
    sha256: Optional[str] = Field(default=None, max_length=64, index=True)
    size_bytes: int = Field(default=0, ge=0)
    content_type: Optional[str] = Field(default=None, max_length=100)
    is_hidden: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)


class TestCaseGroup(SQLModel, table=True):
    __tablename__ = "testcase_groups"
    __table_args__ = (
        UniqueConstraint(
            "revision_id", "group_key", name="uq_testcase_group_key"
        ),
        Index("ix_testcase_groups_revision_order", "revision_id", "position"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    revision_id: int = Field(foreign_key="problem_revisions.id", nullable=False)
    group_key: str = Field(max_length=80)
    position: int = Field(default=1, ge=1)
    score: float = Field(default=100.0, ge=0)
    scoring_policy: str = Field(default="sum", max_length=30)
    dependency_group_id: Optional[int] = Field(
        default=None, foreign_key="testcase_groups.id"
    )
    created_at: datetime = Field(default_factory=utc_now)


class ProblemTestCase(SQLModel, table=True):
    __tablename__ = "problem_testcases"
    __table_args__ = (
        UniqueConstraint(
            "revision_id", "case_name", name="uq_problem_testcase_name"
        ),
        UniqueConstraint(
            "revision_id", "position", name="uq_problem_testcase_position"
        ),
        Index("ix_problem_testcases_revision_group", "revision_id", "group_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    revision_id: int = Field(foreign_key="problem_revisions.id", nullable=False)
    group_id: Optional[int] = Field(
        default=None, foreign_key="testcase_groups.id"
    )
    case_name: str = Field(max_length=120)
    position: int = Field(ge=1)
    input_asset_id: int = Field(foreign_key="problem_assets.id", nullable=False)
    output_asset_id: int = Field(
        foreign_key="problem_assets.id", nullable=False
    )
    score: float = Field(default=0.0, ge=0)
    is_sample: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)


class ProblemAssetRead(SQLModel):
    id: int
    revision_id: int
    asset_kind: str
    display_name: str
    sha256: Optional[str] = None
    size_bytes: int
    content_type: Optional[str] = None
    is_hidden: bool
    created_at: datetime


class ProblemTestCaseRead(SQLModel):
    id: int
    revision_id: int
    group_id: Optional[int] = None
    case_name: str
    position: int
    input_asset_id: int
    output_asset_id: int
    score: float
    is_sample: bool
    created_at: datetime


class ProblemTestCaseUpdate(SQLModel):
    group_id: Optional[int] = None
    case_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    position: Optional[int] = Field(default=None, ge=1)
    score: Optional[float] = Field(default=None, ge=0)
    is_sample: Optional[bool] = None


class TestCaseGroupCreate(SQLModel):
    group_key: str = Field(min_length=1, max_length=80)
    position: int = Field(default=1, ge=1)
    score: float = Field(default=100, ge=0)
    scoring_policy: str = "sum"
    dependency_group_id: Optional[int] = None


class TestCaseGroupRead(TestCaseGroupCreate):
    id: int
    revision_id: int
    created_at: datetime


class AssignmentProblem(SQLModel, table=True):
    __tablename__ = "assignment_problems"
    __table_args__ = (
        UniqueConstraint(
            "homework_num", "position", name="uq_assignment_problem_position"
        ),
        UniqueConstraint(
            "homework_num", "revision_id", name="uq_assignment_problem_revision"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    homework_num: int = Field(
        foreign_key="homework.num", nullable=False, index=True
    )
    revision_id: int = Field(
        foreign_key="problem_revisions.id", nullable=False, index=True
    )
    position: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)


class ProblemCreate(SQLModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    statement: str = ""
    input_description: str = ""
    output_description: str = ""
    time_limit_ms: int = Field(default=1000, ge=1, le=60_000)
    memory_limit_mb: int = Field(default=256, ge=1, le=4096)
    output_limit_kb: int = Field(default=1024, ge=1, le=65_536)
    process_limit: int = Field(default=1, ge=1, le=32)
    source_limit_kb: int = Field(default=1024, ge=1, le=10_240)
    checker_type: str = "token"
    problem_mode: str = "standard"
    checker_config: dict = Field(default_factory=dict)
    language_multipliers: dict[str, float] = Field(default_factory=dict)
    allowed_languages: list[str] = ["c", "cpp", "python", "java"]


class ProblemUpdate(SQLModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    is_active: Optional[bool] = None


class ProblemRevisionCreate(SQLModel):
    clone_from_revision_id: Optional[int] = None
    statement: Optional[str] = None
    input_description: Optional[str] = None
    output_description: Optional[str] = None
    time_limit_ms: Optional[int] = Field(default=None, ge=1, le=60_000)
    memory_limit_mb: Optional[int] = Field(default=None, ge=1, le=4096)
    output_limit_kb: Optional[int] = Field(default=None, ge=1, le=65_536)
    process_limit: Optional[int] = Field(default=None, ge=1, le=32)
    source_limit_kb: Optional[int] = Field(default=None, ge=1, le=10_240)
    checker_type: Optional[str] = None
    problem_mode: Optional[str] = None
    checker_config: Optional[dict] = None
    language_multipliers: Optional[dict[str, float]] = None
    allowed_languages: Optional[list[str]] = None


class ProblemRead(SQLModel):
    id: int
    code: str
    title: str
    owner_id: Optional[str] = None
    is_active: bool
    latest_revision_no: Optional[int] = None
    published_revision_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class ProblemRevisionRead(SQLModel):
    id: int
    problem_id: int
    revision_no: int
    statement: str
    input_description: str
    output_description: str
    time_limit_ms: int
    memory_limit_mb: int
    output_limit_kb: int
    process_limit: int
    source_limit_kb: int
    checker_type: str
    problem_mode: str
    checker_config: dict
    language_multipliers: dict[str, float]
    allowed_languages: list[str]
    status: str
    validation_report: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    published_at: Optional[datetime] = None


class AssignmentProblemCreate(SQLModel):
    revision_id: int
    position: int = Field(default=1, ge=1)


class AssignmentProblemRead(SQLModel):
    id: int
    homework_num: int
    revision_id: int
    position: int
    created_at: datetime


JUDGE_JOB_STATUSES = (
    "queued",
    "leased",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    "dead_letter",
)


class JudgeJob(SQLModel, table=True):
    __tablename__ = "judge_jobs"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key", name="uq_judge_job_idempotency_key"
        ),
        Index("ix_judge_jobs_claim", "status", "priority", "created_at"),
        Index("ix_judge_jobs_lease", "status", "lease_expires_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    job_type: str = Field(max_length=40)
    status: str = Field(default="queued", max_length=20)
    payload_json: str = Field(
        default="{}", sa_column=Column(Text, nullable=False)
    )
    payload_hash: str = Field(max_length=64)
    idempotency_key: Optional[str] = Field(default=None, max_length=120)
    parent_job_id: Optional[int] = Field(
        default=None, foreign_key="judge_jobs.id"
    )
    problem_id: Optional[int] = Field(default=None, foreign_key="problems.id")
    revision_id: Optional[int] = Field(
        default=None, foreign_key="problem_revisions.id"
    )
    submission_id: Optional[int] = Field(
        default=None, foreign_key="submissions.id"
    )
    priority: int = Field(default=100)
    progress: float = Field(default=0.0, ge=0, le=100)
    lease_owner: Optional[str] = Field(default=None, max_length=120)
    lease_expires_at: Optional[datetime] = None
    heartbeat_at: Optional[datetime] = None
    lease_generation: int = Field(default=0, ge=0)
    attempt_count: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    error_message: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    result_json: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    created_at: datetime = Field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class JudgeJobEvent(SQLModel, table=True):
    __tablename__ = "judge_job_events"
    __table_args__ = (
        UniqueConstraint(
            "job_id", "sequence_no", name="uq_judge_job_event_sequence"
        ),
        Index("ix_judge_job_events_job_sequence", "job_id", "sequence_no"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="judge_jobs.id", nullable=False)
    sequence_no: int = Field(ge=1)
    event_type: str = Field(max_length=40)
    message: str = Field(sa_column=Column(Text, nullable=False))
    payload_json: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    created_at: datetime = Field(default_factory=utc_now)


class JudgeWorker(SQLModel, table=True):
    __tablename__ = "judge_workers"

    worker_id: str = Field(primary_key=True, max_length=120)
    status: str = Field(default="online", max_length=20, index=True)
    capabilities_json: str = Field(
        default="{}", sa_column=Column(Text, nullable=False)
    )
    concurrency: int = Field(default=1, ge=1)
    current_job_id: Optional[int] = Field(
        default=None, foreign_key="judge_jobs.id"
    )
    heartbeat_at: datetime = Field(default_factory=utc_now, index=True)
    last_error: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )


class JudgeWorkerRead(SQLModel):
    worker_id: str
    status: str
    capabilities_json: str
    concurrency: int
    current_job_id: Optional[int] = None
    heartbeat_at: datetime
    last_error: Optional[str] = None


class GradingMetricsRead(SQLModel):
    queued_jobs: int
    running_jobs: int
    failed_jobs: int
    dead_letter_jobs: int
    workers_online: int
    workers_offline: int
    average_queue_wait_ms: float = 0.0
    verdict_counts: dict[str, int] = Field(default_factory=dict)
    problem_error_counts: dict[str, int] = Field(default_factory=dict)
    worker_failure_rate: float = 0.0


class GradingRun(SQLModel, table=True):
    __tablename__ = "grading_runs"
    __table_args__ = (
        Index(
            "ix_grading_runs_submission_created", "submission_id", "created_at"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submissions.id", nullable=False)
    job_id: Optional[int] = Field(default=None, foreign_key="judge_jobs.id")
    problem_revision_id: Optional[int] = Field(
        default=None, foreign_key="problem_revisions.id"
    )
    lease_generation: int = Field(default=0)
    verdict: str = Field(default="JG", max_length=10)
    score: float = Field(default=0.0)
    runtime_version: str = Field(default="legacy", max_length=120)
    checker_version: str = Field(default="standard-v1", max_length=120)
    result_json: str = Field(
        default="{}", sa_column=Column(Text, nullable=False)
    )
    created_at: datetime = Field(default_factory=utc_now)


class JudgeJobRead(SQLModel):
    id: int
    job_type: str
    status: str
    parent_job_id: Optional[int] = None
    problem_id: Optional[int] = None
    revision_id: Optional[int] = None
    submission_id: Optional[int] = None
    priority: int
    progress: float
    lease_owner: Optional[str] = None
    lease_generation: int
    attempt_count: int
    max_attempts: int
    error_message: Optional[str] = None
    result_json: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class JudgeJobEventRead(SQLModel):
    id: int
    job_id: int
    sequence_no: int
    event_type: str
    message: str
    payload_json: Optional[str] = None
    created_at: datetime


class RejudgeScope(SQLModel):
    problem_id: Optional[int] = None
    revision_id: Optional[int] = None
    homework_num: Optional[int] = None
    contest_id: Optional[int] = None
    user_id: Optional[str] = None
    submission_ids: list[int] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    verdicts: list[str] = Field(default_factory=list)
    submitted_after: Optional[datetime] = None
    submitted_before: Optional[datetime] = None


class RejudgePreviewRead(SQLModel):
    target_count: int
    submission_ids: list[int]
    truncated: bool = False


class RejudgeCreate(RejudgeScope):
    reason: str = Field(min_length=1, max_length=500)
    target_revision_id: Optional[int] = None
    idempotency_key: str = Field(min_length=1, max_length=120)
    contest_approval_id: Optional[int] = None


class Contest(SQLModel, table=True):
    __tablename__ = "contests"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, max_length=80, index=True)
    title: str = Field(max_length=200)
    starts_at: datetime
    ends_at: datetime
    freeze_at: Optional[datetime] = None
    visibility: str = Field(default="private", max_length=20)
    access_code_hash: Optional[str] = Field(default=None, max_length=64)
    allowed_organizations_json: str = Field(
        default="[]", sa_column=Column(Text, nullable=False)
    )
    scoring_format: str = Field(default="icpc", max_length=20)
    allow_virtual: bool = Field(default=False)
    system_testing: bool = Field(default=False)
    status: str = Field(default="draft", max_length=20, index=True)
    created_by: str = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(default_factory=utc_now)


class ContestProblem(SQLModel, table=True):
    __tablename__ = "contest_problems"
    __table_args__ = (
        UniqueConstraint(
            "contest_id", "position", name="uq_contest_problem_position"
        ),
        UniqueConstraint(
            "contest_id", "revision_id", name="uq_contest_problem_revision"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    contest_id: int = Field(
        foreign_key="contests.id", nullable=False, index=True
    )
    revision_id: int = Field(foreign_key="problem_revisions.id", nullable=False)
    label: str = Field(max_length=20)
    position: int = Field(ge=1)
    points: float = Field(default=100.0, ge=0)


class ContestParticipation(SQLModel, table=True):
    __tablename__ = "contest_participations"
    __table_args__ = (
        UniqueConstraint(
            "contest_id",
            "user_id",
            "participation_type",
            name="uq_contest_participation",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    contest_id: int = Field(foreign_key="contests.id", nullable=False)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    participation_type: str = Field(default="official", max_length=20)
    started_at: datetime = Field(default_factory=utc_now)
    ends_at: Optional[datetime] = None


class Clarification(SQLModel, table=True):
    __tablename__ = "contest_clarifications"

    id: Optional[int] = Field(default=None, primary_key=True)
    contest_id: int = Field(
        foreign_key="contests.id", nullable=False, index=True
    )
    user_id: str = Field(foreign_key="users.id", nullable=False)
    problem_id: Optional[int] = Field(default=None, foreign_key="problems.id")
    question: str = Field(sa_column=Column(Text, nullable=False))
    answer: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    status: str = Field(default="open", max_length=20)
    created_at: datetime = Field(default_factory=utc_now)
    answered_at: Optional[datetime] = None


class ContestAnnouncement(SQLModel, table=True):
    __tablename__ = "contest_announcements"

    id: Optional[int] = Field(default=None, primary_key=True)
    contest_id: int = Field(
        foreign_key="contests.id", nullable=False, index=True
    )
    title: str = Field(max_length=200)
    message: str = Field(sa_column=Column(Text, nullable=False))
    created_by: str = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(default_factory=utc_now)


class ContestResultEvent(SQLModel, table=True):
    __tablename__ = "contest_result_events"
    __table_args__ = (
        Index("ix_contest_result_events_replay", "contest_id", "sequence_no"),
        UniqueConstraint(
            "contest_id", "sequence_no", name="uq_contest_result_sequence"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    contest_id: int = Field(foreign_key="contests.id", nullable=False)
    sequence_no: int = Field(ge=1)
    participation_id: int = Field(
        foreign_key="contest_participations.id", nullable=False
    )
    contest_problem_id: int = Field(
        foreign_key="contest_problems.id", nullable=False
    )
    submission_id: int = Field(foreign_key="submissions.id", nullable=False)
    grading_run_id: Optional[int] = Field(
        default=None, foreign_key="grading_runs.id"
    )
    verdict: str = Field(max_length=10)
    score: float = Field(default=0.0)
    result_phase: str = Field(default="live", max_length=20, index=True)
    occurred_at: datetime = Field(default_factory=utc_now)


class ContestOperationApproval(SQLModel, table=True):
    __tablename__ = "contest_operation_approvals"

    id: Optional[int] = Field(default=None, primary_key=True)
    contest_id: int = Field(
        foreign_key="contests.id", nullable=False, index=True
    )
    operation: str = Field(max_length=40)
    reason: str = Field(sa_column=Column(Text, nullable=False))
    approved_by: str = Field(foreign_key="users.id", nullable=False)
    used_by_job_id: Optional[int] = Field(
        default=None, foreign_key="judge_jobs.id"
    )
    used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)


class ContestOperationApprovalCreate(SQLModel):
    operation: str = "rejudge"
    reason: str = Field(min_length=1, max_length=1000)


class ContestOperationApprovalRead(ContestOperationApprovalCreate):
    id: int
    contest_id: int
    approved_by: str
    used_by_job_id: Optional[int] = None
    used_at: Optional[datetime] = None
    created_at: datetime


class ContestCreate(SQLModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    starts_at: datetime
    ends_at: datetime
    freeze_at: Optional[datetime] = None
    visibility: str = "private"
    access_code: Optional[str] = None
    allowed_organizations: list[str] = Field(default_factory=list)
    scoring_format: str = "icpc"
    allow_virtual: bool = False


class ContestRead(SQLModel):
    id: int
    code: str
    title: str
    starts_at: datetime
    ends_at: datetime
    freeze_at: Optional[datetime] = None
    visibility: str
    allowed_organizations: list[str] = Field(default_factory=list)
    scoring_format: str
    allow_virtual: bool
    system_testing: bool
    status: str
    created_by: str
    created_at: datetime


class ContestProblemCreate(SQLModel):
    revision_id: int
    label: str = Field(min_length=1, max_length=20)
    position: int = Field(ge=1)
    points: float = Field(default=100.0, ge=0)


class ContestProblemRead(ContestProblemCreate):
    id: int
    contest_id: int


class ContestParticipationCreate(SQLModel):
    access_code: Optional[str] = None
    participation_type: str = "official"


class ContestParticipationRead(SQLModel):
    id: int
    contest_id: int
    user_id: str
    participation_type: str
    started_at: datetime
    ends_at: Optional[datetime] = None


class ClarificationCreate(SQLModel):
    problem_id: Optional[int] = None
    question: str = Field(min_length=1, max_length=4000)


class ClarificationAnswer(SQLModel):
    answer: str = Field(min_length=1, max_length=4000)


class ClarificationRead(SQLModel):
    id: int
    contest_id: int
    user_id: str
    problem_id: Optional[int] = None
    question: str
    answer: Optional[str] = None
    status: str
    created_at: datetime
    answered_at: Optional[datetime] = None


class ContestAnnouncementCreate(SQLModel):
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=10000)


class ContestAnnouncementRead(SQLModel):
    id: int
    contest_id: int
    title: str
    message: str
    created_by: str
    created_at: datetime


class ContestResultEventCreate(SQLModel):
    participation_id: int
    contest_problem_id: int
    submission_id: int
    grading_run_id: Optional[int] = None
    verdict: str
    score: float = Field(default=0, ge=0)


class ContestScoreboardRow(SQLModel):
    rank: int
    user_id: str
    solved: int
    score: float
    penalty_minutes: int


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
    problem_revision_id: Optional[int] = Field(
        default=None, foreign_key="problem_revisions.id", index=True
    )
    # This is the mutable pointer to the selected immutable run.  Keep it as an
    # indexed application-managed reference: a database FK would create the
    # submissions -> grading_runs -> judge_jobs -> submissions dependency cycle.
    selected_grading_run_id: Optional[int] = Field(default=None, index=True)
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
    storage_sha256: Optional[str] = Field(default=None, max_length=64)
    legacy_storage_path: Optional[str] = Field(default=None, max_length=500)
    legacy_storage_status: Optional[str] = Field(default=None, max_length=20)
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
    problem_revision_id: Optional[int] = None
    selected_grading_run_id: Optional[int] = None
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
    compile_log: Optional[str] = None
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
        Index(
            "ix_code_snapshots_homework_user_created",
            "homework_num",
            "user_id",
            "created_at",
        ),
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
        Index(
            "ix_submission_files_submission_kind",
            "submission_id",
            "artifact_kind",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submissions.id", nullable=False)
    artifact_kind: str = Field(max_length=32)
    file_name: Optional[str] = Field(default=None, max_length=255)
    storage_path: str = Field(max_length=500)
    storage_sha256: Optional[str] = Field(default=None, max_length=64)
    legacy_storage_path: Optional[str] = Field(default=None, max_length=500)
    legacy_storage_status: Optional[str] = Field(default=None, max_length=20)
    content_type: Optional[str] = Field(default=None, max_length=100)
    size_bytes: Optional[int] = None
    text_excerpt: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    created_at: datetime = Field(default_factory=utc_now)


class SubmissionResult(SQLModel, table=True):
    __tablename__ = "submission_results"
    __table_args__ = (
        UniqueConstraint(
            "submission_id", name="uq_submission_result_submission"
        ),
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
    message: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )


class GradingRule(SQLModel, table=True):
    __tablename__ = "grading_rules"
    __table_args__ = (
        UniqueConstraint(
            "scope",
            "homework_num",
            "rule_name",
            name="uq_grading_rule_scope_name",
        ),
        Index("ix_grading_rules_scope_homework", "scope", "homework_num"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    scope: str = Field(default="system", max_length=20)
    homework_num: Optional[int] = Field(
        default=None, foreign_key="homework.num"
    )
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


class SystemSettingHistory(SQLModel, table=True):
    __tablename__ = "system_setting_history"
    __table_args__ = (
        Index("ix_system_setting_history_key_id", "setting_key", "id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    setting_key: str = Field(max_length=100, index=True)
    previous_value: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    new_value: str = Field(sa_column=Column(Text, nullable=False))
    changed_by: str = Field(foreign_key="users.id", nullable=False)
    rolled_back_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)


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
        Index(
            "ix_system_event_logs_category_created", "category", "created_at"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    category: str = Field(max_length=40)
    level: str = Field(default="info", max_length=20)
    event_type: str = Field(max_length=80)
    message: str = Field(sa_column=Column(Text, nullable=False))
    submission_id: Optional[int] = Field(
        default=None, foreign_key="submissions.id"
    )
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
    result: str = "success"
    request_id: Optional[str] = None
    job_id: Optional[int] = None
    before_json: Optional[str] = None
    after_json: Optional[str] = None
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
    result: str = Field(default="success", max_length=20, index=True)
    request_id: Optional[str] = Field(default=None, max_length=80, index=True)
    job_id: Optional[int] = Field(
        default=None, foreign_key="judge_jobs.id", index=True
    )
    before_json: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    after_json: Optional[str] = Field(
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
    __table_args__ = (
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )

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
    url: str = Field(default="", max_length=500)
    content: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    attachment_name: Optional[str] = Field(default=None, max_length=255)
    attachment_relpath: Optional[str] = Field(default=None, max_length=500)
    is_published: bool = True


class LectureMaterial(LectureMaterialBase, table=True):
    __tablename__ = "lecture_materials"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_by: str = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MaterialCommentBase(SQLModel):
    content: str = Field(sa_column=Column(Text, nullable=False))


class MaterialComment(MaterialCommentBase, table=True):
    __tablename__ = "material_comments"

    id: Optional[int] = Field(default=None, primary_key=True)
    material_id: int = Field(foreign_key="lecture_materials.id", nullable=False)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(default_factory=utc_now)


class MaterialCommentCreate(MaterialCommentBase):
    pass


class MaterialCommentRead(MaterialCommentBase):
    id: int
    material_id: int
    user_id: str
    user_name: Optional[str] = None
    created_at: datetime


class LectureMaterialWrite(LectureMaterialBase):
    pass


class LectureMaterialRead(LectureMaterialBase):
    id: int
    created_by: str
    comments: list[MaterialCommentRead] = []
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
        Index(
            "ix_plagiarism_runs_homework_created", "homework_num", "created_at"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    homework_num: int = Field(foreign_key="homework.num", nullable=False)
    created_by: str = Field(foreign_key="users.id", nullable=False)
    status: str = Field(default="completed", max_length=30)
    compared_submission_count: int = Field(default=0)
    flagged_pair_count: int = Field(default=0)
    summary: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    created_at: datetime = Field(default_factory=utc_now)


class PlagiarismPair(SQLModel, table=True):
    __tablename__ = "plagiarism_pairs"
    __table_args__ = (
        Index(
            "ix_plagiarism_pairs_run_similarity", "run_id", "similarity_score"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="plagiarism_runs.id", nullable=False)
    homework_num: int = Field(foreign_key="homework.num", nullable=False)
    left_submission_id: int = Field(
        foreign_key="submissions.id", nullable=False
    )
    right_submission_id: int = Field(
        foreign_key="submissions.id", nullable=False
    )
    left_user_id: str = Field(foreign_key="users.id", nullable=False)
    right_user_id: str = Field(foreign_key="users.id", nullable=False)
    similarity_score: float = Field(default=0.0)
    status: str = Field(default="flagged", max_length=30)
    summary: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
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
    homework_num: Optional[int] = Field(
        default=None, foreign_key="homework.num"
    )
    mentor_id: str = Field(foreign_key="users.id", nullable=False)
    status: str = Field(default="active", max_length=30)
    current_code: str = Field(
        default="", sa_column=Column(Text, nullable=False)
    )
    created_at: datetime = Field(default_factory=utc_now)
    closed_at: Optional[datetime] = Field(default=None)


class CollabParticipant(SQLModel, table=True):
    __tablename__ = "collab_participants"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "user_id", name="uq_collab_session_user"
        ),
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
        Index(
            "ix_collab_code_snapshots_session_created",
            "session_id",
            "created_at",
        ),
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
    __table_args__ = (
        Index("ix_exam_submissions_exam_user", "exam_id", "user_id"),
    )

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
        UniqueConstraint(
            "exam_submission_id", name="uq_exam_result_submission"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    exam_submission_id: int = Field(
        foreign_key="exam_submissions.id", nullable=False
    )
    total_score: float = Field(default=0.0)
    graded_at: Optional[datetime] = Field(default=None)
