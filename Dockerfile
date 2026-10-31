# Backend API only. Build from the repository root: docker build -t sweaterco-backend .
# Mount /app/output to retain chat, saved runs and review checkpoints. Inject API credentials only
# at runtime; processing and cloud voice require ALLOW_PAID_PROCESSING=1.

FROM python:3.13.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /bin/uv
ENV UV_LINK_MODE=copy
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-editable

# The final image contains Python, production dependencies and backend source. No uv binary,
# package cache, notebook dependencies, translation runtime or local model weights are copied in.
FROM python:3.13.14-slim
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY backend/ ./
EXPOSE 8000
# Render supplies PORT. Use one process: the current snapshot-status contract records its PID.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
