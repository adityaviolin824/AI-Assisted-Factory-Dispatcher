# FastAPI build record

**Status:** built on 20 October 2026, following [the FastAPI structure guide](FASTAPI_STRUCTURE_GUIDE.md). Four endpoints serve saved runs and a paused dispatcher review over HTTP. All 123 offline tests pass (4 of them new for the API). No model was called while building or testing it.

**Update, 21 October 2026:** a fifth endpoint, `POST /reviews/{thread_id}/finalize`, applies the dispatcher's whole batch of choices with one calculation and saves the approved review (D15). Before any run has paused, the review endpoints answer 404 without creating the checkpoint file (D14). All 127 offline tests pass.

**In short:** the API adds no rules. Each endpoint calls code that already existed and was already tested:
- the run endpoints read the files in `output/runs/`;
- the review endpoints call `paused_review()` and `resume_graph()`, the same functions `resume_dispatcher_review.py` calls.

The dispatcher's answer is checked by `apply_answer`, exactly as in the terminal.

This document records:
- what was built;
- why each choice was made, with the alternatives, assumptions and effect;
- how it was checked;
- what is still open.

## 1. What was asked, and the answers that shaped it

- **The specification:** [FASTAPI_STRUCTURE_GUIDE.md](FASTAPI_STRUCTURE_GUIDE.md), unchanged. It sets the layout (`main.py` plus two router files in `fastapi_routes/`), the four endpoints, and the boundaries: no processing, no model calls, no notebook or data changes, and no allocation-policy changes.
- **Review before building:** Claude read the guide against the code and found four gaps:
  1. Nothing links a run ID to its thread ID.
  2. A strict request model would replace `apply_answer`'s refusal messages with FastAPI's generic ones.
  3. A React page on another port needs CORS.
  4. FastAPI was not a project dependency, and `main.py` existed but was empty.
- **Aditya's answers (20 October 2026):**
  - "do the uv add";
  - "make the necessary minimal changes";
  - CORS: "Leave CORS out for now";
  - document what is done and why in this file.
- **How the gaps were handled:**
  - Gap 1 follows the guide's own scope: "initially use the thread ID printed by the existing pipeline runner". It stays an open decision (section 9).
  - Gap 2 is built in (decision D4).
  - Gap 3 is left out, as Aditya chose (decision D11).
  - Gap 4 is done: the dependency was added and `main.py` filled in.

## 2. Files

| File | Change | What it does |
|---|---|---|
| `pyproject.toml` | one line added | `"fastapi[standard-no-fastapi-cloud-cli]>=0.147.0"` in `dependencies` (by `uv add`) |
| `uv.lock` | 261 lines added | the lock entries `uv add` wrote (section 3) |
| `main.py` | filled in (was an empty, tracked file) | creates the FastAPI app and includes the two routers |
| `fastapi_routes/runs.py` | new | `GET /runs` and `GET /runs/{run_id}`: read saved run files |
| `fastapi_routes/dispatcher.py` | new | `GET /reviews/{thread_id}`, `POST /reviews/{thread_id}/answer` and `POST /reviews/{thread_id}/finalize`: show, answer or finalize a paused review |
| `tests/test_fastapi_routes.py` | new | 4 offline tests of the endpoints (section 7) |
| `FASTAPI_BUILD.md` | new | this record |

Docs updated to stop calling `fastapi_routes/` a placeholder, and to give the new test count:
- `AGENTS.md` (root) and `backend/AGENTS.md`;
- `backend/README.md`;
- `docs/system-design.md`, `docs/project-plan.md` and `FEATURES.md`;
- `backend/docs/Pending_Improvements.md`;
- `docs/engineering-log.md`.

**Not changed:**
- **Calculation code:** every processing, routing, allocation and dispatcher review module, and `app_full_pipeline/pipeline_graph.py`.
- **Runner scripts:** `run_full_pipeline.py` and `resume_dispatcher_review.py`.
- **Inputs and references:** the notebooks, `backend/data/`, `harness/simulate.py` and `reference-documents/`.
- **Saved runs:** `output/runs/` still holds the same 15 runs.
- **The guide:** `FASTAPI_STRUCTURE_GUIDE.md` was left as it was.

## 3. The dependency

**Command, run from `backend/`:**

```text
uv add "fastapi[standard-no-fastapi-cloud-cli]"
```

**Why this form:**
- FastAPI's official installation page recommends `uv add "fastapi[standard]"`. The same page offers `fastapi[standard-no-fastapi-cloud-cli]` for "the standard dependencies but without the `fastapi-cloud-cli`".
- The cloud CLI only deploys to FastAPI Cloud, which this project does not use. Leaving it out installs fewer packages, and nothing used here is lost.
- The standard extra provides:
  - `fastapi-cli`, which gives the `fastapi dev` command;
  - `uvicorn`, the server;
  - `httpx`, which `TestClient` needs.

**Evidence from the lockfile diff:**
- The diff only adds packages. No existing package changed version.
- FastAPI 0.147.0, uvicorn 0.54.0 and httpx 0.28.1 were already installed, because Gradio (a `dev` dependency) uses them. They are now declared as runtime dependencies, which matters because the API is application code, not a notebook tool.
- The 16 newly installed packages:
  - `fastapi-cli` 0.0.32 and `rich-toolkit`, for the `fastapi` command;
  - `uvloop` and `watchfiles`, for uvicorn's standard extra;
  - `email-validator` and `dnspython`;
  - `pydantic-settings` and `pydantic-extra-types`;
  - six OpenTelemetry packages and `googleapis-common-protos`.

**OpenTelemetry (checked, because review responses contain chat text):**
- FastAPI 0.147 has built-in OpenTelemetry support, and its standard extra installs the OpenTelemetry SDK and an OTLP HTTP exporter.
- Reading `fastapi/applications.py` and `fastapi/telemetry/_runtime.py` showed when anything is exported:
  - only when `FASTAPI_OTEL_AUTO_CONFIGURE=true`;
  - and only with an `OTEL_EXPORTER_OTLP_ENDPOINT` (or a per-signal endpoint) set.
- Neither is set by this project, so nothing is exported. If either is ever set in the server's environment, request traces would be sent to that endpoint.

## 4. How it is wired

```text
frontend (later) --HTTP--> main.py (FastAPI app)
                              |
              +---------------+------------------+
              |                                  |
   fastapi_routes/runs.py            fastapi_routes/dispatcher.py
   reads output/runs/<run>/          opens output/dispatcher-review-checkpoints.sqlite
   manifest.json, plan.json,         -> paused_review(thread_id)      (show)
   dispatcher-plan.json              -> resume_graph(thread_id, answer) (answer)
                                         -> dispatcher_review node -> apply_answer
                                         -> save_review node on approve_all
```

`main.py` holds no logic. It creates `app = FastAPI(title="Dispatcher API")` and includes `runs.router` and `dispatcher.router`, as in [FastAPI's guide to bigger applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/). It imports the modules rather than their `router` variables, so the two routers cannot overwrite each other's name.

## 5. The endpoints

| Method and URL | Returns | Errors |
|---|---|---|
| `GET /runs` | `[{"run_id", "label", "messages"}]`: every folder in `output/runs/` with a `manifest.json`, oldest first; the same list `run_allocation.py` prints | none |
| `GET /runs/{run_id}` | `{"run_id", "plan", "dispatcher_plan"}`: the run's `plan.json`, and its `dispatcher-plan.json` once the dispatcher approved (`null` before) | 404 `{"detail": "No saved run <run_id>."}` |
| `GET /reviews/{thread_id}` | `{"status": "waiting", "review", "refused"}`: the paused review, and why the last answer was refused (`null` if it was not) | 404 `{"detail": "Thread <thread_id> has no paused dispatcher review."}` for a finished or unknown thread |
| `POST /reviews/{thread_id}/answer` | the answer's result, see below | the same 404; 422 if the body is not a JSON object |
| `POST /reviews/{thread_id}/finalize` | body `{"decisions": [...]}`: the answer `{"decisions": ..., "then": "finalize"}`, see below | the same 404 and 422 |

Before any run has paused (no checkpoint file), every review endpoint answers 404 `{"detail": "No paused dispatcher reviews exist yet."}`.

**What the answer endpoint returns:**
- **After an edit:** `{"status": "waiting", "review": <the new review>, "refused": null}`.
- **After a refused answer:** `{"status": "waiting", "review": <the same review>, "refused": "<apply_answer's reason>"}`. Nothing changed.
- **After `approve_all`:** `{"status": "finished", "review": <the final review>, "refused": null}`. The final review is the one saved in the run folder as `dispatcher-plan.json`.
- **After an accepted `finalize`:** the same `finished` response. The final review also has `changes`: each row whose outcome, workshop or delivery estimate differs from the review shown, with both versions and their reasons.
- **After a refused `finalize`:** the refused-answer response above. Nothing is saved.

**The answer body** is the same JSON as an answer file for `resume_dispatcher_review.py` (see the [backend README](README.md#dispatcher-review-modules)):

```json
{"decisions": [{"decision": "choose_workshop", "task_id": "T:L0008:J1", "workshop_id": "W6"}],
 "then": "review_again"}
```

```json
{"decisions": [], "then": "approve_all"}
```

**Trying it locally.** Run from `backend/`:

```text
uv run fastapi dev main.py
```

Then open http://127.0.0.1:8000/docs, where every endpoint can be called from the browser. With curl:

```text
curl http://127.0.0.1:8000/runs
curl http://127.0.0.1:8000/runs/<run ID>
curl http://127.0.0.1:8000/reviews/<thread ID>
curl -X POST http://127.0.0.1:8000/reviews/<thread ID>/answer \
     -H "Content-Type: application/json" \
     -d '{"decisions": [], "then": "approve_all"}'
```

**A thread ID only exists after `run_full_pipeline.py` has run.** It prints the ID. No saved run has a paused review yet, and that script can make paid model calls on cache misses, so it needs Aditya's approval first. The run endpoints work without it.

## 6. Decisions

Each decision gives its reason, the alternatives considered, the assumptions it rests on, and its effect on correctness, latency or evaluation (root `AGENTS.md`).

**D1. The endpoints hold no rules; they call the existing functions.**
- **Reason:** the guide, and the project rule that deterministic code in the modules calculates every allocation. `paused_review` and `resume_graph` are already tested, including a pause, a closed SQLite connection and a resume.
- **Alternative:** calling `apply_answer` and `build_dispatcher_plan` directly from the router. That would bypass the graph's checkpoint, so the terminal and the API could show different reviews of the same thread.
- **Effect:** the API and `resume_dispatcher_review.py` behave identically on the same thread. There is one source of truth for the review state.

**D2. Plain `def` endpoints, not `async def`.**
- **Reason:** every function they call is synchronous: file reads, SQLite and the graph. FastAPI runs a `def` endpoint in a worker thread, so a slow recalculation does not block the server's event loop.
- **Alternative:** `async def` calling synchronous code. This blocks the event loop.
- **Effect:** correct by default.
- **Assumption:** the SQLite checkpointer can be used from a worker thread. Verified: `SqliteSaver` opens its connection with `check_same_thread=False` and guards it with a `threading.Lock`.

**D3. Each review request opens the SQLite checkpoint file, then closes it.**
- **Reason:** this is exactly what `resume_dispatcher_review.py` does (`with SqliteSaver.from_conn_string(str(CHECKPOINT_FILE))`). It needs no application startup code, and tests can point it at a temporary file by patching one name.
- **Alternative:** one connection for the whole app, opened in a FastAPI `lifespan`. That is more code and a shared connection to manage, for a saving of milliseconds per request.
- **Effect:** each request has a little extra latency for opening a local file, which is not measurable next to a review recalculation.
- **Assumption:** one dispatcher, as in the graph plan.

**D4. The answer body is a plain JSON object (`answer: dict`), not a detailed Pydantic model.**
- **Reason:** `apply_answer` (through `answer_problem`) already checks the whole answer and explains every refusal in the dispatcher's terms, for example `"then" must be "review_again", "approve_all" or "finalize", not 'save_draft'.`. A detailed model would refuse the same answers first with FastAPI's generic 422 messages, so the dispatcher would see different words from the API than from the terminal.
- **Alternative:** a full Pydantic model for each decision type. It gives a richer `/docs` page, but it duplicates rules that must stay in one place.
- **Effect:**
  - FastAPI checks only that the body is a JSON object (anything else gets 422). Everything else is refused by `apply_answer` with its own message, and nothing changes.
  - The `/docs` page shows the body as a generic object, so the examples in section 5 are the reference.

**D5. A refused answer is a normal response (200), not an HTTP error.**
- **Reason:** in the graph a refusal is not a failure. The review simply waits again, unchanged, with the reason, which is how `resume_graph` returns it. The frontend shows the reason and the same review.
- **Alternative:** a 400 or 422 for a refusal. That would mix "your decision was not accepted" with "your request was malformed", and the frontend would need the review from a second request.
- **Effect:** one response shape for every answer: `status`, `review`, `refused`.

**D6. A finished or unknown thread gets 404, checked first.**
- **Reason:**
  - `resume_graph` raises `ValueError` for such a thread. Catching `ValueError` in the router could also hide unrelated errors.
  - So the router first calls `paused_review`, exactly as the resume script does, and returns 404 with the script's own wording.
  - Any other error stays a visible server error, as the backend rules require.
- **Alternative:** 409 for a finished thread and 404 for an unknown one. That would need a second check, and both cases mean the same thing to the frontend: "there is no review waiting here".
- **Effect:** a clear message for both cases. A finished review is still available as `dispatcher_plan` from `GET /runs/{run_id}`.

**D7. `run_id` must name a saved run folder.**
- **Reason:** the guide says to accept a run ID, not a file path. The endpoint checks the ID against `saved_run_ids()`, the names of the folders in `output/runs/` that hold a `manifest.json`, so `..` or any other path can never be read. A test checks `..` directly.
- **Alternative:** building the path and checking that it stays inside `output/runs/`. That needs more code, for the same protection.
- **Effect:** only saved runs can be read.

**D8. `GET /runs/{run_id}` returns `plan.json` and `dispatcher-plan.json` only.**
- **Reason:** the guide says "the saved plan and results". `plan.json` is the allocation, and `dispatcher-plan.json` is the approved review. `manifest.json` and `state.json` are processing internals that the frontend does not need yet.
- **Alternative:** returning every file in the folder. That gives larger responses and exposes internals.
- **Effect:** small, stable responses. Add a field only when a page needs it.

**D9. Full URLs in the route decorators, with no router prefixes.**
- **Reason:** each URL can be read in one place, exactly as written in the guide's table. FastAPI supports both forms.
- **Effect:** none on behaviour.

**D10. The server is started with `uv run fastapi dev main.py`.**
- **Reason:** it is the documented command and needs no extra configuration. It was checked by starting the real server (section 8).
- **Alternative:** FastAPI's guide also suggests `[tool.fastapi] entrypoint = "main:app"` in `pyproject.toml`, so that `uv run fastapi dev` needs no path. That is one more setting, for a convenience nobody needs yet.
- **Effect:** none on behaviour.

**D11. No CORS (Aditya, 20 October 2026: "Leave CORS out for now").**
- **Reason:** the React page's address is not known yet. The `/docs` page, curl and tests work without CORS.
- **Effect:** a browser page on another origin (for example a Vite dev server on port 5173) cannot call the API until CORS is added.
- **To add it later**, add FastAPI's `CORSMiddleware` in `main.py` with the page's exact origin, or use the frontend dev server's proxy. Do not allow every origin.

**D12. The API does not load `backend/.env`.**
- **Reason:**
  - None of these endpoints needs the OpenAI key, so the server never reads it.
  - `resume_dispatcher_review.py` loads `.env` only for LangSmith settings.
- **Effect:**
  - An answer sent through the API is traced to LangSmith only if `LANGSMITH_TRACING=true` and its settings are set in the shell that starts the server. It is then traced as the run "full-pipeline", and the trace includes the review and the dispatcher's decisions.
  - In this one respect the API differs from the resume script.
  - The tests never load `.env`.

**D13. No endpoint starts a processing run, or finds a thread from a run.**
- **Reason:** the guide's first boundary. A new processing run can make paid model calls and must never start because a page was opened. The thread ID is the one `run_full_pipeline.py` prints.
- **Effect:** the frontend has to be given the thread ID. See open decision 1 in section 9.

**D14. Before any run has paused, the review endpoints answer 404 and create no file (21 October 2026).**
- **Evidence:** `GET /reviews/{thread_id}` created `output/dispatcher-review-checkpoints.sqlite` (20 KB) when no checkpoint file existed, because opening a `SqliteSaver` creates the file.
- **Reason:** reading must create nothing ([frontend/BACKEND_PROPOSAL.md](../frontend/BACKEND_PROPOSAL.md), section 3).
- **Alternative:** opening SQLite read-only by URI. It works too, but is harder to read.
- **Effect:** reads have no side effect. Latency and evaluation are unchanged.

**D15. One batch of choices is finalized with `"then": "finalize"` (21 October 2026).**
- **Reason:** the dispatcher keeps every choice in the page and submits them once with Approve all. `answer` refuses that ("Approve all takes no decisions", "Send accept_late alone"), and sending hidden `review_again` answers first would break the rule of no requests before approval.
- **How:** `apply_answer` applies the whole batch to a copy and calls `build_dispatcher_plan` once. It refuses the batch on `decision_problems`, or when accepted lateness no longer covers its task after the other choices. Otherwise it adds `changes` and returns `then: "approve_all"`, so the graph's existing `save_review` saves it. The route only forwards the body.
- **Alternatives:** a new graph node (more code, the same result); a 409 for a refusal, as first proposed (rejected for D5's single response shape).
- **Effect:** one request and one plan calculation, no model call. `dispatcher-plan.json` gains `changes` when it was finalized this way.

## 7. Tests (`tests/test_fastapi_routes.py`, offline)

**Setup:** each test runs the graph on the supplied chat file from saved answers. It uses the existing `paused_run` helper and a temporary SQLite file, so the run is paused for the dispatcher exactly as `run_full_pipeline.py` leaves it. The runs folder and the checkpoint file used by the API are patched to that temporary folder. The real `output/` folder is never touched.

**Calls:** they go through FastAPI's `TestClient`, which calls the app in memory without a network connection, as in [FastAPI's testing guide](https://fastapi.tiangolo.com/tutorial/testing/).

**`test_saved_runs_are_listed_and_read`:**
- `GET /runs` lists the run with the label and message count from its `manifest.json`.
- `GET /runs/{run_id}` returns its `plan.json`, with `dispatcher_plan` `null`.
- An unknown ID gets the 404 message.
- `read_run("..")` is refused.

**`test_a_paused_review_is_shown_answered_and_approved`:**
1. `GET /reviews/{thread_id}` returns the paused review exactly as the checkpoint holds it.
2. Choosing W6 for T8 returns a new waiting review with T8 at W6.
3. An answer with `"then": "save_draft"` returns `apply_answer`'s own refusal text and the same review.
4. `approve_all` returns `finished`, with the final review equal to the saved `dispatcher-plan.json`; T8 is still at W6.
5. `GET /runs/{run_id}` now returns that plan.
6. The finished thread, a second approval and an unknown thread each get the 404 message.

**`test_finalize_applies_every_choice_once_and_saves`:**
1. W99 for T8 is refused with `apply_answer`'s message, and the review is unchanged.
2. W6 for T8 returns `finished`, with the final review equal to the saved `dispatcher-plan.json`.
3. Its `changes` show T8 moving from `review_required` to `dispatcher_choice` at W6.
4. A second finalize gets the 404 message.

**`test_an_answer_must_be_a_json_object`:** a JSON list gets 422 from FastAPI, and the review is unchanged.

**`test_reviews_get_404_and_no_file_is_created`:** with no checkpoint file, reading, answering and finalizing each get the 404 of D14, and no file appears.

**`test_no_module_uses_an_undefined_name`:** `main`, `runs` and `dispatcher` use only names they define or import.

**Offline guarantees, as in the other test files:**
- every network connection is refused;
- the API client is replaced by one that refuses requests;
- LangSmith tracing is off;
- `.env` is never loaded.

**Run them** from `backend/`:

```text
uv run python -m unittest discover -s tests -v
```

They need the `discover` form, which puts `tests/` on the import path for the shared helpers.

## 8. Verification record (20 October 2026)

- **New tests:** `uv run python -m unittest discover -s tests -p "test_fastapi_routes.py" -v` ran 4 tests, all OK.
- **Mutation check:** the answer endpoint was changed on purpose to always return `"refused": null`. `test_a_paused_review_is_shown_answered_and_approved` then failed. The file was restored from a copy and compared byte for byte with `cmp`.
- **Full suite:** `uv run python -m unittest discover -s tests` ran 123 tests, all OK:
  - 23 processing;
  - 25 routing/allocation;
  - 15 harness;
  - 23 graph;
  - 22 dispatcher review;
  - 11 run report;
  - 4 API.
- **Notebook check:** `uv run python experimentation_notebooks/testing/check_notebook_06.py` printed all 25 PASS lines.
- **Real server, started locally** with `uv run fastapi dev main.py --port 8765 --no-reload` and stopped afterwards:
  - `GET /runs` returned the 15 saved runs (the first: `2026-10-13_19-32-08`, label `dispatch_requests.txt`, 30 messages);
  - `GET /runs/2026-10-14_14-40-08` returned 200;
  - `GET /runs/no-such-run` returned 404 `{"detail":"No saved run no-such-run."}`;
  - `GET /docs` returned 200;
  - `/openapi.json` listed exactly the four paths.
  - The review endpoints were not called on the real server: no thread exists, and opening the checkpoint file would have created it in `output/`.
- **Untouched outputs:** `output/runs/` still holds 15 runs, and there is still no `output/dispatcher-review-checkpoints.sqlite`.
- **Cost:** no model call was made, and no paid run was started.
- **Live check on a paid run (later on 20 October, Test 9):**
  - a fresh run of `run_full_pipeline.py` on `dispatch_requests.txt` paused;
  - its review was then shown, edited (W6 for R08), refused (`save_draft`) and approved through these endpoints;
  - every response matched the saved files.
  - See [the run write-up](docs/evaluation/FULL_RUN_WITH_API_2026-10-20.md).

## 9. Limits and open decisions

**Open decisions (Aditya's to make):**
1. **How the frontend finds a review.** Today the thread ID exists only in `run_full_pipeline.py`'s printout. Options:
   - save the thread ID in the run folder when the graph pauses (this changes the runner and the graph tests);
   - add `GET /reviews`, listing the paused threads in the checkpoint file with their run IDs (read-only, no change to existing code).
2. **CORS origin** (D11): needed once the React page is connected, unless its dev server proxies requests.
3. **A processing endpoint:** a separate request, because it can make paid calls (guide, section 5).

**Known limits of this first step:**
- **One dispatcher.** There is no login, no permissions and no guard against two answers sent to the same thread at the same moment.
- **Local use only.** Nothing here is set up for deployment.
- **Checkpoint file creation:** only `run_full_pipeline.py` and the resume script create `output/dispatcher-review-checkpoints.sqlite`; the API answers 404 until it exists (D14). It is in `output/`, so git ignores it.
- **Large responses:** a review is returned whole, with every decision record, which may be large for long chats.
- **Server log noise:** the graph's progress lines (`[Graph] ...`) print to the server log.
- **What approval means:** the final approval saves JSON in the run folder. It commits no operational assignment and changes no live queue.
- **Reallocation:** not built. "Review again after reallocation" stays parked.
- **Fixed inputs:** code, data and the dispatch date must stay fixed while a review is paused, as before. Changed order or workshop data is refused by `apply_answer`.
