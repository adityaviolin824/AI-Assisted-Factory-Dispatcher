# Simple FastAPI structure for our project

This is a suggested structure, not an implemented API. Claude Code can use this guide without reading `demo_fastapi_backend/`. Follow the repository's `AGENTS.md` instructions too.

The API lets the frontend call our existing Python code. Our existing code continues to calculate whether a workshop can make a batch, take the workload and take it under the recorded rules. The dispatcher controls the final choices.

## 1. Keep the structure small

```text
backend/
    main.py                         NEW: creates the FastAPI application
    fastapi_routes/                 EXISTING folder
        __init__.py                 EXISTING
        runs.py                     NEW: endpoints for saved runs
        dispatcher.py               NEW: endpoints for dispatcher review

    app_full_pipeline/              EXISTING: LangGraph workflow and review pause
    dispatcher_review/              EXISTING: dispatcher decisions and recalculation
    task_allocation_to_workshops/   EXISTING: workshop calculations and allocation
```

A router is just a group of related endpoints. An endpoint is a URL the frontend can call. All routers belong to one FastAPI application.

These two router files are enough to start. Keep their request and response models in the same files initially. Move shared code into another file only when it is actually shared.

## 2. What each new file does

**`main.py` connects the pieces.** Its basic shape would be:

```python
from fastapi import FastAPI
from fastapi_routes import runs, dispatcher

app = FastAPI()
app.include_router(runs.router)
app.include_router(dispatcher.router)
```

**`runs.py` reads saved results.** It lists saved runs and returns a selected run's saved plan and results. Reading a run must not start processing or recalculate its plan. Accept a run ID from the configured runs folder, rather than an arbitrary file path.

**`dispatcher.py` handles review requests.** It reads the current review, accepts a dispatcher answer and returns the updated result. Reuse `paused_review()` and `resume_graph()` from `app_full_pipeline/pipeline_graph.py`, with the existing SQLite checkpointer.

The router validates the incoming JSON, calls the existing function and returns JSON. Keep allocation calculations and decision rules in their existing modules. Ordinary `def` endpoints suit the current synchronous Python functions.

## 3. Suggested first endpoints

`GET` reads information. `POST` submits an action.

| Method and URL | What the frontend gets or does | File |
|---|---|---|
| `GET /runs` | List saved runs. | `runs.py` |
| `GET /runs/{run_id}` | Read one saved run's results. | `runs.py` |
| `GET /reviews/{thread_id}` | Read a paused dispatcher review. | `dispatcher.py` |
| `POST /reviews/{thread_id}/answer` | Apply a dispatcher answer and return the resulting review. | `dispatcher.py` |
| `POST /reviews/{thread_id}/finalize` | Apply all the dispatcher's choices at once and save the approved review (added 21 October 2026, see [FASTAPI_BUILD.md](FASTAPI_BUILD.md) D15). | `dispatcher.py` |

`run_id` identifies a saved run folder. `thread_id` identifies a LangGraph conversation kept in the checkpoint database. They are different IDs. A saved run folder alone does not create a paused review; initially use the thread ID printed by the existing pipeline runner.

For example, choosing a workshop sends this body to the answer endpoint, using a real task ID from the review:

```json
{
  "decisions": [
    {"decision": "choose_workshop", "task_id": "TASK_ID_FROM_REVIEW", "workshop_id": "W1"}
  ],
  "then": "review_again"
}
```

Final approval uses the same endpoint:

```json
{"decisions": [], "then": "approve_all"}
```

Preserve the existing answer format and refusal messages. The frontend should receive the resulting review, any refusal, and whether the review is still waiting or has finished. An unknown or finished thread should get a clear response.

## 4. What happens when a button is clicked

```text
Frontend sends the dispatcher answer
    -> FastAPI checks its format
    -> dispatcher.py calls resume_graph(...)
    -> existing Python code applies the decisions
    -> API returns the updated review
    -> frontend displays it
```

Keep the current behavior: dispatcher-selected work is planned first, other allocations fit around it, and warnings stay visible. Final approval saves the review last shown without planning again. It currently saves JSON; it does not commit operational workshop assignments.

## 5. First implementation boundary

- Start with existing saved runs and paused reviews. These operations need no model calls and do not depend on the golden-set evaluation.
- A new processing run can make paid calls. Add its API entry separately when requested; never trigger it automatically when a page opens.
- Reuse the current checkpoints and saved files. The tutorial's user database, authentication and todo code are outside this first step.
- Keep reallocation buttons disabled for now. Preserve the later option **Review again after reallocation**.
- Leave notebooks, source CSVs and `harness/simulate.py` unchanged. Keep allocation-policy changes separate from API wiring.
- Use `uv` for Python dependencies. Check current official documentation when implementing, and test the endpoints offline alongside the existing backend tests.

This layout gives each endpoint a clear home while keeping the existing calculation code reusable. Add files only when a concrete responsibility needs one.

Reference: [FastAPI's guide to routers and multiple files](https://fastapi.tiangolo.com/tutorial/bigger-applications/).
