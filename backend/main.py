# main.py: the FastAPI application, so a frontend can call the existing Python code over HTTP.
#
# Run from backend/:  uv run fastapi dev main.py     then open http://127.0.0.1:8000/docs
#
# Routes: fastapi_routes/runs.py reads saved runs; fastapi_routes/dispatcher.py shows and answers a
# dispatcher review that run_full_pipeline.py paused. No route processes a chat or calls a model, so
# no request costs money. Why it is built this way: FASTAPI_BUILD.md.
from fastapi import FastAPI

from fastapi_routes import dispatcher, runs

app = FastAPI(title="Dispatcher API")
app.include_router(runs.router)
app.include_router(dispatcher.router)
