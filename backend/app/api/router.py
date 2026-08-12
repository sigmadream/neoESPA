from fastapi import APIRouter

from ..domains.auth.router import router as auth_router
from ..domains.analytics.router import router as analytics_router
from ..domains.admin_auth.router import router as admin_auth_router
from ..domains.collab.router import router as collab_router
from ..domains.collab.router import ws_router as collab_ws_router
from ..domains.contests.router import router as contests_router
from ..domains.contests.router import public_router as public_contests_router
from ..domains.dashboard.router import router as dashboard_router
from ..domains.exams.router import router as exams_router
from ..domains.grading.router import router as grading_router
from ..domains.homework.router import router as homework_router
from ..domains.jobs.router import router as jobs_router
from ..domains.materials.router import router as materials_router
from ..domains.notices.router import router as notices_router
from ..domains.notifications.router import router as notifications_router
from ..domains.observability.router import router as observability_router
from ..domains.plagiarism.router import router as plagiarism_router
from ..domains.problems.router import router as problems_router
from ..domains.settings.router import router as settings_router
from ..domains.submissions.router import router as submissions_router
from ..domains.users.router import router as users_router
from ..domains.qa.router import router as qa_router

router = APIRouter()


@router.get("/ping")
async def ping():
    return {"status": "ok", "backend": "python/fastapi"}


# Standard HTTP domains under /api
for child_router in [
    auth_router,
    analytics_router,
    admin_auth_router,
    users_router,
    dashboard_router,
    homework_router,
    jobs_router,
    submissions_router,
    grading_router,
    notices_router,
    settings_router,
    materials_router,
    notifications_router,
    observability_router,
    plagiarism_router,
    problems_router,
    exams_router,
    collab_router,
    contests_router,
    public_contests_router,
    qa_router,
]:
    router.include_router(child_router)

# WebSocket endpoints (keep root /ws path)
# Need to use root app or a router without /api prefix
# We'll re-include the main router in main.py, but for WS we need a separate export
ws_router = collab_ws_router
