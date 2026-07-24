import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.router import router as api_router, ws_router
from .api.runtime import grading_queue
from .core.config import settings
from .core.db import engine
from .core.migrations import apply_migrations
from .domains.users.serializers import to_user_read as _to_user_read


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
