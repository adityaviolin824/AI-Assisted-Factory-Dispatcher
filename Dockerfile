# Image for the backend API (FastAPI) only. Written 22 October 2026 as a placeholder: it has not been
# built or run. The frontend is not included; it still needs the Next.js server (see frontend/next.config.ts).
#
# Build, from the repository root:
#   docker build -t sweaterco-backend .
# Run, keeping saved runs and review checkpoints in backend/output on your computer:
#   docker run --rm -p 8000:8000 -v "$(pwd)/backend/output:/app/output" sweaterco-backend
# Then open http://127.0.0.1:8000/docs. The API makes no model calls, so it needs no API key.
#
# The processing scripts (such as run_full_pipeline.py) do call OpenAI and cost money. To run one in the
# container, pass the key when it starts, never inside the image:
#   docker run --rm --env-file backend/.env -v "$(pwd)/backend/output:/app/output" sweaterco-backend python run_full_pipeline.py

# Python exactly as backend/pyproject.toml requires (requires-python = "==3.13.14"). "slim" is Debian
# with only what Python needs.
FROM python:3.13.14-slim

# uv, the same version that wrote backend/uv.lock. Change it together with uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /bin/

# Compile the packages to bytecode while installing, so the server starts faster. Copy packages out of
# uv's cache instead of linking them: the cache below is a separate build mount, where links cannot work.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# The backend lives in /app, so config.toml's relative paths (data/, output/) work as they do on a laptop.
WORKDIR /app

# Dependencies first, from the two dependency files only. Docker reuses this slow step until one of
# them changes. --locked stops if uv.lock is out of date; --no-dev leaves out Jupyter and Gradio.
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev

# Then the code, config.toml and the input data. .dockerignore keeps out .env, .venv, output/ and notebooks.
COPY backend/ ./

# Use the environment uv just made. fastapi run serves on all addresses (0.0.0.0), as a container needs.
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["fastapi", "run", "main.py", "--port", "8000"]
