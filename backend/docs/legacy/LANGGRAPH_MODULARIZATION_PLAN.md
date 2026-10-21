# Plan: modularize notebook 05's LangGraph pipeline (chat file -> plan in one graph run)

Status: completed on 15 October 2026; archived as a decision and verification record. This is not an active implementation plan. Use [current implementation](../../README.md), [backend instructions](../../AGENTS.md) and the [project plan](../../../docs/project-plan.md). Paths in the original body are relative to `backend/`. Historical test counts, cache results and local-only trace checks below describe that implementation step; later verification confirmed the remote trace and later processing changes can require new verification calls.

## Context

Notebook 05's processing and allocation now live in modules, but the LangGraph wiring that runs them
together (notebook Part 4, Sections 14-15: graph state, 6 nodes, 2 routers, `build_graph`,
`recursion_limit`, `run_graph`) exists only in the notebook. `05-mvp-notebook-plan.md` is history: it
explains why the graph looks the way it does, and its "Human review later" section says how pauses
(`interrupt`, `Command(resume=...)`) would plug in later. This plan moves the graph into
`app_full_pipeline/` with the fewest changes, so one command runs chat file -> checked tasks -> plan.
After that, FastAPI and dispatcher review can call one function.

Decisions settled with Aditya (15 Oct 2026):
- Keep notebook 05's six nodes.
- An incomplete run that finishes without an error still gets a plan, marked partial.
- Keep all three scripts.
- LangSmith tracing stays on for real runs, and I make at most one real run.

## One run or two steps? (Aditya's question)

**Recommendation: both, with different jobs.**

The graph does the whole input-to-plan run. The two separate scripts stay as development tools.

Why the app path should be one graph run:
1. **It is the app's real flow.** A dispatcher's chat comes in and a plan comes out. FastAPI later calls one function, `run_graph(messages, label)`.
2. **No wrong-run risk.** The plan is made from the in-memory state of the run just processed, in the same run folder. Nothing has to name a folder by hand, which is the bug class repair I06 removed.
3. **One trace per run.** LangSmith shows one trace for the whole run, with every batch, verification and the plan as steps.
4. **Review needs both halves in one graph.** The planned dispatcher review goes answer -> re-verify -> save -> replan, so processing and allocation must sit in the same graph for a pause and resume to work.

Why the two scripts stay:
- `run_intake_and_processing.py` is for paid prompt tests. They need no plan, and they are logged in `PROMPT_TESTING_RESULTS.md`.
- `run_allocation.py` makes free, repeatable re-plans of saved runs, for objective experiments and the harness.

All three call the same functions and write the same run-folder layout. A test proves that the graph run equals processing followed by allocation, so there is still only one behaviour.

## New files

```
backend/
  app_full_pipeline/
    pipeline_graph.py            NEW: notebook Sections 14-15 (graph state, nodes, router, build_graph,
                                 recursion_limit, run_graph)
  run_full_pipeline.py           NEW: uv run python run_full_pipeline.py  (config.toml's chat file -> plan)
  tests/
    test_pipeline_graph.py       NEW: offline checks against notebook 05's graph and the two-step path
  LANGGRAPH_MODULARIZATION_PLAN.md  NEW: this plan plus a progress log, so work can resume if stopped
```

No change to the processing or allocation modules, `config.toml`, notebook 05, `data/`, `harness/`
or `pyproject.toml`. `langgraph` 1.2.11 is already a dependency.

### `app_full_pipeline/pipeline_graph.py` (one file, ~150 lines)

Function bodies come from notebook 05, copied exactly as with the other modules. The notebook's long comment blocks become concise docstrings.

| Definition | Calls (module) | Status |
|---|---|---|
| `PipelineState` (TypedDict: messages, label, run_dir, processing, summary, plan) | - | moved |
| node `start_run` | `processing_run.prepare_run` | moved |
| node `link_items` | `create_and_link_tasks.link_pending_items`, `settings_and_data.save_checkpoint` | moved |
| node `extract_batch` | `extract_items.owned_windows`, `extract_items.intake_window`, `save_checkpoint` | moved |
| node `verify_tasks` | `verify_tasks.run_verification` | moved |
| node `save_outputs` | `processing_run.save_run_outputs` (returns `summary`) | moved |
| node `plan_allocation` | `allocation_plan.plan_allocation(Path(run_dir), processing, messages)` | changed: body is now one call to the module function, which already holds the notebook node's code |
| router `after_link` | `owned_windows` | moved |
| router `after_save` | - | removed (Aditya's choice: always plan) |
| `build_graph` | LangGraph `StateGraph` | changed: fixed edge `save_outputs -> plan_allocation` |
| `recursion_limit` | `owned_windows` | moved (2N + 10) |
| `run_graph(messages, label)` | `build_graph().stream(..., stream_mode="updates")` | changed: LangSmith run name `full-pipeline`, so module runs are told apart from notebook runs (`order-pipeline-mvp`) |

The graph:

```
START -> start_run -> link_items --after_link--> extract_batch -> link_items   (one turn per batch)
                                 \-------------> verify_tasks -> save_outputs -> plan_allocation -> END
```

How the run is orchestrated:
- **The state is plain data.** The graph state holds only plain data (lists, dicts, strings), so LangSmith shows the whole state at every step.
  - `processing` is the same dict that is saved as `state.json`. Nodes change it in place and return it.
  - A node returns only the keys it changed. There are no reducers.
- **Each node makes its own `RecordedModel(run_dir)`.** This is the notebook's choice; an object cannot live in the state.
  - The call files are named by request fingerprint, so separate callers never clash.
  - An API client is created only on a cache miss.
- **The batch loop:** `after_link` asks `owned_windows`, the same function `extract_batch` uses, whether a batch is left. Yes means `extract_batch`, no means `verify_tasks`.
- **Steps:** a run with N batches takes 2N + 5 steps whether it is complete or not. That is 25 steps for the supplied 30 messages and 23 for the 26 blocker-case messages.
- **Errors stop the graph.** An API, file or programming error stops the graph and is shown as it is, and no plan is made.
  - `state.json` keeps the progress.
  - `run_allocation.py <folder>` can still make the partial plan.
- **An incomplete run still gets a plan.** If processing finishes but is incomplete, `plan_allocation` makes a partial plan (`processing_complete: false`, with `not_processed` rows), as `backend/AGENTS.md` already requires of allocation.
- **The run folder layout** is the same as running the two scripts in turn: `output/runs/<start time>/` with `manifest.json`, `state.json`, `calls/`, `plan.json` and `plan-history/`.
- **Not in scope:** no checkpointer, `interrupt` or resume. These stay future work, as in notebook 05.

### `run_full_pipeline.py` (~40 lines, like `run_intake_and_processing.py`)

1. `load_dotenv(BACKEND_DIR / ".env", override=False)` loads the OpenAI key, used only on a cache miss, and the LangSmith settings. Tracing therefore follows `.env`, which is on.
2. It prints the inputs and settings once:
   - orders and workshops loaded;
   - each stage's model and reasoning effort;
   - the batch settings;
   - the dispatch date and the plan objective;
   - the output folder.
3. `read_messages(CHAT_FILE)` reads the chat, then `run_graph(messages, CHAT_FILE.name)` runs the graph. An empty file creates no run folder.
4. It prints the run folder, the steps, the plan file, and the model calls with how many were paid. Paid calls are counted the way `run_intake_and_processing.py` counts them.

### `tests/test_pipeline_graph.py` (offline: saved answers, API blocked, tracing off)

These tests reuse the existing helpers:
- `load_notebook_05`;
- `offline_modules`, `logic`, `module_definitions` and `undefined_names` from `test_processing_modules`;
- `pinned_settings`, `assert_same_plan` and `failing_model_calls` from `test_allocation_modules`.

1. **Same as notebook:**
   - Each moved definition has notebook 05's syntax tree.
   - Every other function is declared `CHANGED` (`plan_allocation`, `build_graph`, `run_graph`) or `NEW` (`run_full_pipeline.main`).
   - No undefined names.
2. **Graph shape:** the nodes and edges equal the notebook's, except that `save_outputs` has one fixed edge to `plan_allocation` and no edge to END.
3. **End to end**, on `data/dispatch_requests.txt`, 0 API requests:
   - The graph takes the same 25 steps as notebook 05's graph.
   - `manifest.json`, `state.json` and `calls/` equal the notebook graph's, with the one existing declared manifest difference.
   - The plan passes `assert_same_plan` against the notebook graph's plan.
4. **Graph equals the two steps.** On the same messages, the graph run and `process_messages` then `plan_saved_run` produce equal `manifest`, `state`, `calls` and `plan`, apart from `created_at`. The graph's run folder holds exactly `manifest.json`, `state.json`, `calls/`, `plan.json` and `plan-history/`.
5. **Empty input:** `run_graph([], ...)` returns `(None, [])` and creates no run folder.
6. **Error stops the graph:** an injected API failure during verification raises `RuntimeError`, leaves `state.json` in place, and creates no `plan.json`.
7. **An incomplete run still gets a plan.** With the save step's completeness check patched to `False`, the graph still ends with `plan_allocation`, in 2N + 5 steps.

**Tracing in tests.** `tests/notebook_reference.py` already sets `LANGSMITH_TRACING=false` for every test, so test fixtures never reach LangSmith. I read "tracing should always be on" as applying to real runs, not tests. Tell me if you also want test runs traced.

## Implementation steps (validate each before the next; log each in `LANGGRAPH_MODULARIZATION_PLAN.md`)

0. Write this plan to `backend/LANGGRAPH_MODULARIZATION_PLAN.md`, with a progress table.
1. **Graph module and its first tests.**
   - Write `pipeline_graph.py`, then tests 1 and 2.
   - Confirm from the installed langgraph 1.2.11 source that `StateGraph`, `add_conditional_edges`, `compile` and `stream(stream_mode="updates")` are current, and that no deprecation warning is printed.
   - Run the full suite: the 52 existing tests plus the new ones.
2. **Tests 3 and 4**, end to end and graph equals two steps. Run the full suite.
3. **Tests 5 to 7**, empty input, stop on error and incomplete run. Run the full suite.
4. **`run_full_pipeline.py`, then the one real run.**
   - **Check:** first run an offline cache check on `config.toml`'s chat file (`dispatch_requests_blocker_cases.txt`, current Luna settings):
     - it runs in a temporary folder;
     - the API client is replaced by a guard, so a cache miss raises an error instead of paying;
     - tracing is off;
     - nothing is written to `output/`.
   - **If any request has no saved answer:** stop and ask Aditya, because the real run would be paid.
   - **If every request has a saved answer:** make the **one** real run, `uv run python run_full_pipeline.py`, with tracing on (from `.env`).
     - Expected: 23 steps, 0 paid calls, and a plan.
     - Compare its `state.json` and `plan.json` with run `2026-10-15_15-28-46` (same input and settings, made with the two scripts).
     - Report any difference; do not fix it.
     - Tell Aditya the run name to look for in LangSmith.
5. **Simplification review.** Copied bodies stay untouched, and the suite runs again.
6. **Docs.** I show each edit:
   - `README.md`: a new "Full pipeline (LangGraph)" section covering the three scripts and when to use each, the graph, the run folder and the LangSmith note.
   - `backend/AGENTS.md`:
     - a new "Full pipeline graph" section;
     - `app_full_pipeline/` leaves the placeholder list;
     - the active-notebook line now says the graph is modularized.
   - Root `AGENTS.md` ("... modularized" line).
   - `MODULARIZATION_INSTRUCTIONS.md` step 6: the graph is done, the API is not.
   - `docs/project-plan.md` status row.
   - `docs/system-design.md` section 7 status sentence.
   - `docs/engineering-log.md` entry with the evidence.
   - At the end, one interview checkpoint question (Interview-Preparation.md), unless deadline mode is requested.

## Verification (what "done" means)

- `uv run python -m unittest discover -s tests -v` from `backend/` passes: the 52 existing tests plus the new graph tests, offline, with 0 API requests.
- The graph module's moved definitions equal notebook 05's. Only `plan_allocation`, `build_graph` and `run_graph` are declared changed, and `after_save` is removed.
- On the supplied chat file:
  - the module graph matches notebook 05's graph in steps, state and plan;
  - the module graph matches the two-step path in state and plan, apart from `created_at`.
- At most one real run is made, traced, with 0 paid calls. Its trace is visible in LangSmith.
- Notebook 05, `data/`, `harness/`, `reference-documents/`, `config.toml` and the processing and allocation modules are unchanged. No dependency is added and nothing is committed.

## Stop and ask Aditya if

- any request would need a paid API call;
- the graph's results differ from notebook 05's, or from the two-step path, beyond the declared changes;
- a processing or allocation module would need a change;
- a second real run seems needed.

## Progress

| Step | Status | Evidence |
|---|---|---|
| 0. This plan saved | done 15 Oct | `LANGGRAPH_MODULARIZATION_PLAN.md` |
| 1. Graph module, tests 1-2 | done 15 Oct | `app_full_pipeline/pipeline_graph.py`. 8 definitions equal notebook 05's syntax tree; `plan_allocation`, `build_graph`, `run_graph` declared changed. Edges: the notebook's, with `save_outputs -> plan_allocation` fixed instead of the `after_save` router. langgraph 1.2.11 source: `add_conditional_edges(source, path, path_map)`, `compile()`, `stream(stream_mode="updates")` current (the only deprecation in `stream` is `checkpoint_during`, not used); no warnings with `-W default`. |
| 2. Tests 3-4 (end to end, graph equals two steps) | done 15 Oct | On `data/dispatch_requests.txt`, saved answers, 0 API requests: 25 steps equal the notebook graph's; manifest (plus `reasoning_effort`), state, calls and summary equal; `assert_same_plan` passes; graph run equals `process_messages` + `plan_saved_run` (plan differs only in `created_at`); folder holds manifest, state, calls, plan.json, plan-history (1 copy). |
| 3. Tests 5-7 (empty input, error, incomplete run) | done 15 Oct | Empty and blank files: `(None, [])`, no run folder. Injected verify failure: the injected `RuntimeError` propagates, `state.json` kept, no `plan.json`. Completeness patched to False: 25 steps ending `plan_allocation`, plan `processing_complete: false`. Full suite: 65 tests OK. In-memory breaks (scratchpad `mutation_check_graph.py`): control 0 failures; router skips extraction 7 failures; plan drops a message 3; step limit too small 2 errors. |
| 4. `run_full_pipeline.py`, cache check, one real run | done 15 Oct | Cache check (scratchpad `cache_check_full_pipeline.py`: temporary folder, API client blocked, tracing off) on `dispatch_requests_blocker_cases.txt` with the configured Luna models: 23 steps, 18 calls, 0 without a saved answer; `output/` unchanged. The one real run, traced: `output/runs/2026-10-15_21-19-26`, 23 steps, 18 calls, 0 paid, complete; LangSmith run `full-pipeline` in project `adi-dss-subcontractor-project` (tracing confirmed enabled locally; the LangSmith side was not queried). Its manifest, state, call files and plan (except `created_at`) equal run `2026-10-15_15-28-46`, made with the two scripts. Outcomes: 5 recommendation, 6 processing_review, 6 intake_review, 4 link_review, 3 needs_clarification, 1 non_task; 26 of 26 messages covered. |
| 5. Simplification review | done 15 Oct | Copied bodies untouched; `run_full_pipeline.py` counts paid calls in two lines, like `run_intake_and_processing.py`; one long test line wrapped. Suite: 65 OK. |
| 6. Docs | done 15 Oct | `README.md` (new "Full pipeline (LangGraph)" section, intro lines), `AGENTS.md` (active-notebook line, new "Full pipeline graph" section, `app_full_pipeline/` out of the placeholders), `../AGENTS.md`, `MODULARIZATION_INSTRUCTIONS.md` (step 6), `../docs/project-plan.md` (Verification and Application rows, next step 3), `../docs/system-design.md` (section 7 status and table), `../docs/engineering-log.md` (new entry). |
