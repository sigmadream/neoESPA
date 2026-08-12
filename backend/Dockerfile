# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# base: 런타임/테스트 이미지가 공유하는 OS 레벨 툴체인
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS base

# Install C/C++ compilers for code grading
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 실행 결과가 호스트 OS(로케일/타임존/줄바꿈)에 좌우되지 않도록 고정한다.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# ---------------------------------------------------------------------------
# test: dev 의존성 + 테스트 코드를 포함한 검증 전용 이미지
#
# 컨테이너는 저장소 레이아웃을 그대로 재현한다.
#   /            <- 저장소 루트 (app/core/config.py 의 settings.BASE_DIR)
#   /app         <- backend/
#   /supportFiles, /database
# 덕분에 supportFiles 탐색과 기본 DB 경로가 개발 머신과 동일하게 동작한다.
#
# supportFiles 는 backend/ 바깥에 있으므로 named build context 로 주입한다.
#   docker build --target test --build-context supportfiles=./supportFiles ./backend
# ---------------------------------------------------------------------------
FROM base AS test

# Install dependencies including the dev group (pytest, black, ...)
RUN uv sync --frozen

COPY --from=supportfiles . /supportFiles
RUN mkdir -p /database

# 호스트의 __pycache__ 가 (bind mount 시에도) 결과에 영향을 주지 않도록 격리한다.
# NEOESPA_SUPPORT_DIR 은 의도적으로 설정하지 않는다. 개발 머신과 동일하게
# 상위 경로 탐색으로 /supportFiles 를 찾도록 두어야 탐색 로직까지 검증된다.
ENV PYTHONPYCACHEPREFIX=/tmp/pycache

COPY app ./app
COPY tests ./tests
COPY deploy ./deploy
COPY openapi.json API.md create_sample_data.py ./

# 인자를 그대로 pytest 로 넘긴다. (예: `... run --rm tests tests/grading -k lint`)
ENTRYPOINT ["/app/.venv/bin/pytest"]
CMD []

# ---------------------------------------------------------------------------
# runtime: API 서버 이미지 (docker build 기본 타깃)
# ---------------------------------------------------------------------------
FROM base AS runtime

# Install dependencies (no venv needed inside container)
RUN uv sync --frozen --no-dev

# Copy application source code
COPY app ./app
COPY deploy ./deploy
COPY openapi.json create_sample_data.py ./

EXPOSE 8000

# The queue is SQLite-backed; API replicas do not carry queue state in memory.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
