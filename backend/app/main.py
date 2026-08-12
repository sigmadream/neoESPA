import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.router import router as api_router, ws_router
from .core.config import settings
from .core.db import engine
from .core.migrations import apply_migrations
from .core.request_context import request_id_context
from sqlalchemy import text
from sqlmodel import Session, select
from datetime import UTC, datetime
from .models.schemas import JudgeWorker
from .services.artifact_store import LocalArtifactStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_security()
    apply_migrations(engine)
    if settings.ENVIRONMENT == "development":
        from .core.seed import seed_database

        seed_database(engine)
        logging.getLogger(__name__).info("Development seed applied")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    lifespan=lifespan,
)


@app.get("/health/live")
def health_live():
    return {"status": "live"}


@app.get("/health/ready")
def health_ready():
    errors: list[str] = []
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as error:
        errors.append(f"database: {error}")
    try:
        LocalArtifactStore().initialize()
    except Exception as error:
        errors.append(f"artifact_store: {error}")
    if errors:
        return JSONResponse(status_code=503, content={"status": "not_ready", "errors": errors})
    return {"status": "ready"}


@app.get("/health/judge")
def health_judge():
    now = datetime.now(UTC)
    with Session(engine) as session:
        workers = session.exec(select(JudgeWorker)).all()
    online = []
    for worker in workers:
        heartbeat = worker.heartbeat_at
        if heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=UTC)
        if worker.status in {"online", "draining"} and (now - heartbeat).total_seconds() <= 60:
            online.append(worker.worker_id)
    available = settings.AUTOMATIC_GRADING_AVAILABLE and bool(online)
    return JSONResponse(
        status_code=200 if available else 503,
        content={
            "status": "ready" if available else "not_ready",
            "automatic_grading_enabled": settings.AUTO_GRADING_ENABLED,
            "sandbox_ready": settings.SANDBOX_READY,
            "online_workers": online,
        },
    )


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    incoming = request.headers.get("X-Request-ID", "").strip()
    request_id = incoming[:80] if incoming else uuid.uuid4().hex
    request.state.request_id = request_id
    context_token = request_id_context.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_context.reset(context_token)


@app.exception_handler(HTTPException)
async def http_error_envelope(request: Request, error: HTTPException):
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    message = error.detail if isinstance(error.detail, str) else "Request failed"
    return JSONResponse(
        status_code=error.status_code,
        headers=error.headers,
        content={
            "detail": error.detail,
            "code": f"http_{error.status_code}",
            "message": message,
            "field_errors": [],
            "request_id": request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_envelope(request: Request, error: RequestValidationError):
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    field_errors = [
        {
            "field": ".".join(str(part) for part in item["loc"] if part != "body"),
            "message": item["msg"],
            "type": item["type"],
        }
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "detail": error.errors(),
            "code": "validation_error",
            "message": "Request validation failed",
            "field_errors": field_errors,
            "request_id": request_id,
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
