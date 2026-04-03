from .v0001_submission_core import VERSION as V0001_SUBMISSION_CORE
from .v0001_submission_core import upgrade as upgrade_v0001_submission_core
from .v0002_submission_adjustments import VERSION as V0002_SUBMISSION_ADJUSTMENTS
from .v0002_submission_adjustments import upgrade as upgrade_v0002_submission_adjustments
from .v0003_platform_extensions import VERSION as V0003_PLATFORM_EXTENSIONS
from .v0003_platform_extensions import upgrade as upgrade_v0003_platform_extensions
from .v0004_user_timestamp_backfill import VERSION as V0004_USER_TIMESTAMP_BACKFILL
from .v0004_user_timestamp_backfill import upgrade as upgrade_v0004_user_timestamp_backfill

MIGRATIONS = [
    (V0001_SUBMISSION_CORE, upgrade_v0001_submission_core),
    (V0002_SUBMISSION_ADJUSTMENTS, upgrade_v0002_submission_adjustments),
    (V0003_PLATFORM_EXTENSIONS, upgrade_v0003_platform_extensions),
    (V0004_USER_TIMESTAMP_BACKFILL, upgrade_v0004_user_timestamp_backfill),
]
