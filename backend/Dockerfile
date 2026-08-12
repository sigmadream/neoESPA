FROM python:3.14-slim

# Install C/C++ compilers for code grading
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (no venv needed inside container)
RUN uv sync --frozen --no-dev

# Copy application source code
COPY . .

EXPOSE 8000

# The queue is SQLite-backed; API replicas do not carry queue state in memory.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
