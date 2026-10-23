# main.py: the FastAPI application, so a frontend can call the existing Python code over HTTP.
#
# Run from backend/:  uv run fastapi dev main.py     then open http://127.0.0.1:8000/docs
# To allow the one paid route:  ALLOW_PAID_PROCESSING=1 uv run fastapi dev main.py
#
# Routes: fastapi_routes/runs.py reads saved runs; fastapi_routes/dispatcher.py shows and answers a
# dispatcher review that the pipeline paused; fastapi_routes/chat.py saves the operations chat and
# captures snapshots of it. Only POST /chat/snapshots/{snapshot_id}/process calls models, which can
# cost money, and it is refused unless the server was started with ALLOW_PAID_PROCESSING=1. Why it is
# built this way: FASTAPI_BUILD.md.
from fastapi import FastAPI

from fastapi_routes import chat, dispatcher, runs

app = FastAPI(title="Dispatcher API")
app.include_router(runs.router)
app.include_router(dispatcher.router)
app.include_router(chat.router)
