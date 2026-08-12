from .v0001_submission_core import VERSION as V0001_SUBMISSION_CORE
from .v0001_submission_core import upgrade as upgrade_v0001_submission_core
from .v0002_submission_adjustments import VERSION as V0002_SUBMISSION_ADJUSTMENTS
from .v0002_submission_adjustments import upgrade as upgrade_v0002_submission_adjustments
from .v0003_platform_extensions import VERSION as V0003_PLATFORM_EXTENSIONS
from .v0003_platform_extensions import upgrade as upgrade_v0003_platform_extensions
from .v0004_user_timestamp_backfill import VERSION as V0004_USER_TIMESTAMP_BACKFILL
from .v0004_user_timestamp_backfill import upgrade as upgrade_v0004_user_timestamp_backfill
from .v0005_materials_board_and_qa import VERSION as V0005_MATERIALS_BOARD_AND_QA
from .v0005_materials_board_and_qa import upgrade as upgrade_v0005_materials_board_and_qa
from .v0006_problem_revisions import VERSION as V0006_PROBLEM_REVISIONS
from .v0006_problem_revisions import upgrade as upgrade_v0006_problem_revisions
from .v0007_problem_artifacts import VERSION as V0007_PROBLEM_ARTIFACTS
from .v0007_problem_artifacts import upgrade as upgrade_v0007_problem_artifacts
from .v0008_judge_jobs import VERSION as V0008_JUDGE_JOBS
from .v0008_judge_jobs import upgrade as upgrade_v0008_judge_jobs
from .v0009_capabilities import VERSION as V0009_CAPABILITIES
from .v0009_capabilities import upgrade as upgrade_v0009_capabilities
from .v0010_audit_context import VERSION as V0010_AUDIT_CONTEXT
from .v0010_audit_context import upgrade as upgrade_v0010_audit_context
from .v0011_admin_bootstrap import VERSION as V0011_ADMIN_BOOTSTRAP
from .v0011_admin_bootstrap import upgrade as upgrade_v0011_admin_bootstrap
from .v0012_contests import VERSION as V0012_CONTESTS
from .v0012_contests import upgrade as upgrade_v0012_contests
from .v0013_selected_grading_run import VERSION as V0013_SELECTED_GRADING_RUN
from .v0013_selected_grading_run import upgrade as upgrade_v0013_selected_grading_run
from .v0014_analytics_consent import VERSION as V0014_ANALYTICS_CONSENT
from .v0014_analytics_consent import upgrade as upgrade_v0014_analytics_consent
from .v0015_admin_invitations import VERSION as V0015_ADMIN_INVITATIONS
from .v0015_admin_invitations import upgrade as upgrade_v0015_admin_invitations
from .v0016_admin_auth_assurance import VERSION as V0016_ADMIN_AUTH_ASSURANCE
from .v0016_admin_auth_assurance import upgrade as upgrade_v0016_admin_auth_assurance
from .v0017_revision_judge_policy import VERSION as V0017_REVISION_JUDGE_POLICY
from .v0017_revision_judge_policy import upgrade as upgrade_v0017_revision_judge_policy
from .v0018_legacy_storage_backfill import VERSION as V0018_LEGACY_STORAGE_BACKFILL
from .v0018_legacy_storage_backfill import upgrade as upgrade_v0018_legacy_storage_backfill
from .v0019_revision_approvals import VERSION as V0019_REVISION_APPROVALS
from .v0019_revision_approvals import upgrade as upgrade_v0019_revision_approvals
from .v0020_audit_capability import VERSION as V0020_AUDIT_CAPABILITY
from .v0020_audit_capability import upgrade as upgrade_v0020_audit_capability
from .v0021_contest_operation_approvals import VERSION as V0021_CONTEST_OPERATION_APPROVALS
from .v0021_contest_operation_approvals import upgrade as upgrade_v0021_contest_operation_approvals
from .v0022_system_setting_history import VERSION as V0022_SYSTEM_SETTING_HISTORY
from .v0022_system_setting_history import upgrade as upgrade_v0022_system_setting_history
from .v0023_operational_capabilities import VERSION as V0023_OPERATIONAL_CAPABILITIES
from .v0023_operational_capabilities import upgrade as upgrade_v0023_operational_capabilities
from .v0024_interactive_problem_mode import VERSION as V0024_INTERACTIVE_PROBLEM_MODE
from .v0024_interactive_problem_mode import upgrade as upgrade_v0024_interactive_problem_mode
from .v0025_contest_result_phase import VERSION as V0025_CONTEST_RESULT_PHASE
from .v0025_contest_result_phase import upgrade as upgrade_v0025_contest_result_phase

MIGRATIONS = [
    (V0001_SUBMISSION_CORE, upgrade_v0001_submission_core),
    (V0002_SUBMISSION_ADJUSTMENTS, upgrade_v0002_submission_adjustments),
    (V0003_PLATFORM_EXTENSIONS, upgrade_v0003_platform_extensions),
    (V0004_USER_TIMESTAMP_BACKFILL, upgrade_v0004_user_timestamp_backfill),
    (V0005_MATERIALS_BOARD_AND_QA, upgrade_v0005_materials_board_and_qa),
    (V0006_PROBLEM_REVISIONS, upgrade_v0006_problem_revisions),
    (V0007_PROBLEM_ARTIFACTS, upgrade_v0007_problem_artifacts),
    (V0008_JUDGE_JOBS, upgrade_v0008_judge_jobs),
    (V0009_CAPABILITIES, upgrade_v0009_capabilities),
    (V0010_AUDIT_CONTEXT, upgrade_v0010_audit_context),
    (V0011_ADMIN_BOOTSTRAP, upgrade_v0011_admin_bootstrap),
    (V0012_CONTESTS, upgrade_v0012_contests),
    (V0013_SELECTED_GRADING_RUN, upgrade_v0013_selected_grading_run),
    (V0014_ANALYTICS_CONSENT, upgrade_v0014_analytics_consent),
    (V0015_ADMIN_INVITATIONS, upgrade_v0015_admin_invitations),
    (V0016_ADMIN_AUTH_ASSURANCE, upgrade_v0016_admin_auth_assurance),
    (V0017_REVISION_JUDGE_POLICY, upgrade_v0017_revision_judge_policy),
    (V0018_LEGACY_STORAGE_BACKFILL, upgrade_v0018_legacy_storage_backfill),
    (V0019_REVISION_APPROVALS, upgrade_v0019_revision_approvals),
    (V0020_AUDIT_CAPABILITY, upgrade_v0020_audit_capability),
    (V0021_CONTEST_OPERATION_APPROVALS, upgrade_v0021_contest_operation_approvals),
    (V0022_SYSTEM_SETTING_HISTORY, upgrade_v0022_system_setting_history),
    (V0023_OPERATIONAL_CAPABILITIES, upgrade_v0023_operational_capabilities),
    (V0024_INTERACTIVE_PROBLEM_MODE, upgrade_v0024_interactive_problem_mode),
    (V0025_CONTEST_RESULT_PHASE, upgrade_v0025_contest_result_phase),
]
