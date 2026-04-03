from ..services.collab_ws import CollabConnectionManager
from ..services.export_service import ExportService
from ..services.feedback_service import FeedbackService
from ..services.grading_queue import GradingQueueService
from ..services.grading_service import GradingService
from ..services.notification_service import NotificationService
from ..services.observability_service import ObservabilityService
from ..services.plagiarism_service import PlagiarismService


grading_service = GradingService()
grading_queue = GradingQueueService(grading_service)
export_service = ExportService()
feedback_service = FeedbackService()
notification_service = NotificationService()
observability_service = ObservabilityService()
plagiarism_service = PlagiarismService()
collab_ws_manager = CollabConnectionManager()

SUBMISSION_ATTEMPT_RETRY_LIMIT = 3
