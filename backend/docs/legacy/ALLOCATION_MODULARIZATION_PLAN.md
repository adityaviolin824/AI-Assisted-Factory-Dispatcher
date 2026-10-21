# Plan: modularize notebook 05's routing and allocation (no LangGraph)

Status: completed on 15 October 2026; archived as a decision and verification record. This is not an active implementation plan. Use [current implementation](../../README.md) and [backend instructions](../../AGENTS.md). The original decisions and progress below describe the implementation at that time; later provisional warnings supersede its hold behaviour. Paths in the original body are relative to `backend/`. This replaced the first draft (route_task inside plan_tasks, byte-identical plan.json, no plan for an incomplete run, overwrite-only plan file).

## Goal

Move notebook 05's allocation (Part 3, Sections 10-13, plus the body of the graph node `plan_allocation`) into `task_routing/` and `task_allocation_to_workshops/`, so that:

- allocation runs **by itself on any saved run folder** (`output/runs/<start time>/`), free and repeatable, because a lot of allocation testing is coming;
- every allocation decision equals notebook 05's for the same verified tasks;
- the allocator can later be reused by an adapter for `../harness/simulate.py` (the professor's scorer).

Not in this task: LangGraph, a script that combines processing and allocation, dispatcher handling, the API, and any processing change (`Pending_Improvements.md` holds the processing backlog).

## Decisions (15 October 2026)

1. **Separate routing from allocation** (Aditya's proposal, adopted with corrections):

   ```
   processing state (verified tasks, reviews, non-task messages)
     -> routing (no queues; keeps input order)
          duplicate-order check over every verified allocation task with an order ID, ready or not
          allocate             -> allocator: deadline order (EDD), queue copy + pieces_so_far,
                                  recommend, reserve production + rework for recommendations only
                                  -> recommendations or allocation reviews (they belong to this plan)
          duplicate order      -> review records (same record and reason as the notebook)
          needs_clarification  -> clarification records
          reference            -> declined records ("not answered here")
     processing reviews and non-task messages -> carried as recorded
     -> collect: one summary row per input, and the count of chat messages covered
   ```

   - Routing uses the two existing conditions, not the intent label: a question with nothing to clarify is `reference`; a question with an open doubt, or a task that is not `information_sufficient`, is `needs_clarification`; any other task is `allocate`.
   - Allocator-discovered reviews stay in the allocator (unsupported split or condition, no workshop passes the hard rules, every allowed workshop late, requested workshop blocked, top workshop only a "reference"). EDD ordering is allocation policy and stays there; `recommend`'s readiness check is kept unchanged.
   - The handlers (`review_tasks_processing/`, `dispatcher_stuff_to_be_decided/`) stay empty: the routed records are kept in the plan.
2. **Acceptance is decision-level**, not byte-level: same route for every task, every decision record equal to the notebook's, same duplicate reviews, same final queues, the notebook's planning order (routed-out tasks removed) equal to the allocator's, and the same summary rows for complete runs.
3. **Equivalence first, then two separately tested additions** (Aditya, 15 October; `Pending_Improvements.md` issues 12-13 had listed them as deferred):
   - **Plan history:** `plan.json` stays the file the pipeline reads (`plan-<objective>.json` when `plan_objective` is set, never overwriting the default). Each allocation run also saves the same plan as `plan-history/<time>_<plan file name>`. `created_at` is inside the file, separate from `dispatch_date`.
   - **Partial previews:** an incomplete processing run is still planned. The plan stores `processing_complete`, a warning is printed, and every input without an outcome gets a `not_processed` row (unread messages, items awaiting linking, tasks awaiting verification). For an incomplete run only, allocation first applies processing's existing `hold_reviewed_requests` to its in-memory copy, so a task that a review found before the stop would hold is never recommended. Complete runs are planned exactly as saved. `state.json` and `manifest.json` are never changed.
4. **Known limit (documented, not fixed):** `pipeline_complete` does not check that the final hold pass ran. A run killed after its last verification checkpoint but before `save_run_outputs` writes `state.json` would look complete with some holds missing. No model call happens in that window (milliseconds of in-memory work), so an API failure cannot cause it. All 13 saved runs are final.
5. **Operating assumption:** the CSV files and allocation settings stay fixed while comparing plans. Each plan records `dispatch_date`, `objective_setting`, `workshop_profiles` and each decision's `order_snapshot` and `queue_snapshot`, so a data difference is visible.
6. **Settings:** `config.toml` gets `[allocation] dispatch_date = 2026-04-01` and a commented `# plan_objective = "hybrid"` (absent means each request's own preference). `DEFAULT_OBJECTIVE` stays a code constant in `rank_workshops.py`. Allocation reuses `CONFIG`, `DATA_DIR` and `write_json` from `order_processing_into_tasks/settings_and_data.py`.
7. **Harness adapter (Aditya, 15 October; step 9):**
   - Location: `backend/eval_harness/` (inside the backend git repository, beside the allocation modules), not the project plan's `evaluation/` folder, which is outside the repository. It imports the unchanged `../harness/simulate.py` and sets `simulate.DATA` to the configured data folder (`backend/data`), because the harness's own `DATA` (`DSS-Project-CODES/data`) does not exist.
   - Same rules as the app, for a batch with no request constraints: hard rules (`split_rejected`), estimates from the harness's queues and the batch's own sent date (`candidate_metrics`), late workshops removed, on-time ones ranked by the objective (`rank_candidates`). The harness needs one eligible workshop for every batch, while the app would review a batch with no on-time workshop. The adapter then returns the least-late workshop (the app's "closest option": lateness, then delivery days, then cost) for every objective. Alternative rejected: ranking late workshops by the objective (`require_on_time=False`), which lets minimize_cost pick a later workshop.
   - On-time check: the app's unrounded expected delivery days, so the harness measures the app's own policy. The harness rounds completion days; an estimate of 10.3 days for 10 available counts as late here. Alternative rejected: rounding like the harness.
   - Policies: all five objectives and the hybrid, each with its own allocator (its own piece counts for the share objectives), beside the three supplied baselines, in normal and `--shock` runs. The six official metrics come from `simulate.py`'s own report, unchanged. The project plan's tardiness measures (mean over all batches, mean over late batches, p90, total days late; completion date minus due date, rebuilt from the replay outcomes) are printed in a separate table labelled as external.

## Layout

```
backend/
  config.toml                          + [allocation] dispatch_date, optional plan_objective
  run_allocation.py                    uv run python run_allocation.py output/runs/<start time>
                                       (no argument: lists the saved runs and stops; never picks one)
  task_routing/
    route_verified_tasks.py            route_task, route_tasks
  task_allocation_to_workshops/
    allocation_settings_and_data.py    Sec 1-2: DISPATCH_DATE, PLAN_OBJECTIVE, Workshop, WORKSHOPS,
                                       ORDERS, INITIAL_QUEUES
    workshop_rules_and_estimates.py    Sec 10: rejection_reason, split_rejected, hard_rule_reason,
                                       candidate_metrics
    rank_workshops.py                  Sec 11: DEFAULT_OBJECTIVE, OBJECTIVE_FIELDS, OBJECTIVE_ALIASES,
                                       PREFERENCE_OBJECTIVES, DEFAULT_HYBRID_WEIGHTS, hybrid_score,
                                       rank_candidates
    recommend_one_task.py              Sec 12: task_deadline, review_decision, option_without_request,
                                       recommend
    allocation_plan.py                 Sec 13 + node 6: plan_tasks, summarize_plan,
                                       inputs_without_outcome, plan_allocation, plan_saved_run
  tests/test_allocation_modules.py     offline; notebook 05 is the reference (read only)
  eval_harness/
    run_harness_evaluation.py          uv run python -m eval_harness.run_harness_evaluation
                                       make_allocator (what simulate.py scores), run_comparison,
                                       days_late, print_lateness, main
  tests/test_harness_evaluation.py     offline; ../harness/simulate.py is only read
```

`run_intake_and_processing.py` and the processing modules are unchanged. Function bodies are copied exactly; the notebook's comment blocks become concise docstrings.

### Declared changes against notebook 05 (everything else is moved unchanged and checked by syntax tree)

| Definition | Change |
|---|---|
| `DISPATCH_DATE`, `PLAN_OBJECTIVE` | Read from `config.toml`; values equal the notebook's. |
| `plan_tasks` | Receives the `allocate` tasks only; no routing or duplicate branch; returns no `needs_clarification`/`reference_tasks`; its first print counts ready tasks. |
| `summarize_plan` | Also lists `duplicate_order_reviews` and the `not_processed` inputs. |
| `plan_allocation` | Takes `(run_dir, state, messages)` instead of the graph state; calls `route_tasks`; drops the `[Graph]` print; returns the plan. Steps 7-8 add `created_at`, the history copy, `processing_complete`, holds for incomplete runs and `not_processed`. |
| `route_task`, `route_tasks` | New: the routing conditions and the duplicate-order check moved out of `plan_tasks`. |
| `plan_saved_run`, `run_allocation.main` | New: read a saved run folder and plan it. |
| `inputs_without_outcome` | New (step 8): one `not_processed` record per unread message, unlinked item or task with neither a current verification nor a current review, following `pipeline_complete`'s checks. |

## Steps (all tests after each; update Progress after each)

1. `config.toml` `[allocation]`, `allocation_settings_and_data.py`, first tests (syntax trees, values equal the notebook's).
2. `workshop_rules_and_estimates.py`.
3. `rank_workshops.py`.
4. `recommend_one_task.py`.
5. `task_routing/route_verified_tasks.py` and `allocation_plan.py` (behaviour of the notebook for an incomplete run: no plan). Tests:
   - C1-C14 rewritten as module tests with their hand-worked answers, plus the notebook's `plan_tasks` as the oracle; declared difference: C14 (no deadline, unclear) is routed out, so the allocator's planning order is C12, C13, C11.
   - Routing cases: a reference question, a question with an open doubt, an unclear task, a ready task sharing its order with a not-ready allocation task (duplicate review), a ready unique task.
   - Every unique saved run in `output/runs/` (11 of 13 after ignoring run-folder paths): the module plan against the notebook's `plan_allocation` node on the same state.
   - The notebook's saved plan (`experimentation_notebooks/output/order-pipeline-mvp/runs/2026-10-13_12-13-34/plan.json`) against the module plan of `output/runs/2026-10-13_19-32-08` (same state).
   - End to end: notebook 05's whole graph against `process_messages` then `plan_saved_run`, from saved answers, 0 API requests.
6. `run_allocation.py`; real runs on the unique saved runs (no model calls); no argument lists runs.
7. Plan history. Tests: main file and copy equal; a second run keeps the first copy; an objective plan leaves `plan.json` intact and its copy names the objective; two saves in one second never overwrite a copy.
8. Partial previews. Tests: processing stopped (offline, injected failure) during extraction and during verification; every input has a row; `processing_complete` false; warning printed; the held-task example (a verify-stage review of one ORD-103 request makes the other one held, not planned); saved files unchanged byte for byte; complete runs unchanged.
9. Harness: an adapter beside the unchanged `../harness/simulate.py` (questions for Aditya first: location, deadline fallback, which objectives).
10. Docs: `README.md`, `backend/AGENTS.md` (rule wording below), repository `AGENTS.md`, `MODULARIZATION_INSTRUCTIONS.md`, `../docs/engineering-log.md`.

Rule wording for `backend/AGENTS.md` (follows from decision 3): "Plan allocation only when every input has an outcome ... an incomplete run makes no plan" becomes "Allocation plans one explicitly named run (the run just processed, or a saved run folder given to `run_allocation.py`). It always plans the verified tasks; when processing is incomplete, the plan is marked partial and lists every input without an outcome."

## Stop and ask Aditya if

- moved code would need a logic change beyond the table above;
- a decision differs from the notebook's in a way not listed here;
- a step could make a model call (allocation never should).

## Progress

| Step | Status | Evidence |
|---|---|---|
| 0. Plan rewritten to the agreed design | done 15 Oct | this file |
| 1. Settings and data | done 15 Oct | `config.toml` `[allocation]`; `allocation_settings_and_data.py`; data equal the notebook's; 19 tests pass |
| 2. Rules and estimates | done 15 Oct | `workshop_rules_and_estimates.py`; 4 definitions with the notebook's syntax tree; 19 tests pass |
| 3. Ranking | done 15 Oct | `rank_workshops.py`; 7 definitions with the notebook's syntax tree; 19 tests pass |
| 4. One recommendation | done 15 Oct | `recommend_one_task.py`; 4 definitions with the notebook's syntax tree; 19 tests pass |
| 5. Routing, plan, equivalence tests | done 15 Oct | `route_verified_tasks.py`, `allocation_plan.py`; 32 tests pass, none skipped; all 11 unique saved runs equal the notebook's plans; the notebook's saved 13 Oct plan reproduced (16 + 2 decisions, queues, summary rows). Mutation check (scratchpad, in memory): duplicates counted among ready tasks only, chat order instead of EDD, and transport reserved in the queue each make tests fail. The ready-only duplicate mistake is caught only by the made-up routing case: no saved run contains it. |
| 6. run_allocation.py, real runs | done 15 Oct | `run_allocation.py`; no argument lists the 13 saved runs. Real runs on the 11 unique saved runs (`2026-10-14_13-29-43` and `2026-10-14_13-31-55` repeat earlier runs): exit 0, 0 API requests, every chat message covered, all complete, one history copy equal to `plan.json` each; the 26 `manifest.json`/`state.json` files unchanged (SHA-256). Development results, not accuracy: supplied chat 2-3 recommendations per run (gpt-4.1-mini `2026-10-13_19-32-08`: T:L0009:J1 W6, T:L0021:J1 W5, as the notebook); its 14-16 reviews come from the notebook's rules (6-7 deadlines on or before the dispatch date 2026-04-01, the ORD-103 duplicate pair, a split request, late-only options, blocked requested workshops, the reference gate). Demo chat: 0 recommendations. Extended chat (`2026-10-14_19-29-34`, 222 messages): 0 recommendations, 107 processing reviews, 40 link reviews, 18 intake reviews (a processing issue, left for later). Blocker cases: 1 (`2026-10-15_00-05-48`) and 5 (`2026-10-15_15-28-46`) recommendations. |
| 7. Plan history | done 15 Oct | `created_at` and `plan-history/<time to the microsecond>_<plan file>`; `PlanFiles` tests: copy equals plan.json, two plans in one second keep both copies, an objective plan leaves plan.json unchanged; 35 tests pass |
| 8. Partial previews | done 15 Oct | `processing_complete`, `not_processed` rows, warnings, holds applied to a copy for incomplete runs. `PartialRuns` stops processing of the supplied chat offline with injected failures: extraction call 2 (27 unread messages and 2 unverified tasks listed, nothing planned), linking at the 2nd item (the supplied chat has no follow-up, so no link call exists to fail; 1 unlinked item listed), verification call 2 (the first batch's 3 tasks routed, 26 listed), and verification call 7 unreadable then call 8 failed (T:L0014:J1, verified, would be allocated by routing alone; the plan holds it because the review of T:L0020:J1 names ORD-103). Every message and task has a row; `manifest.json`, `state.json` and the caller's state are unchanged. Mutation check (scratchpad, in memory): skipping the holds, dropping item records, leaving `not_processed` out of the table, holding the caller's state and treating every run as complete each make tests fail. 38 tests pass. |
| 9. Harness adapter | done 15 Oct | Decision 7. `eval_harness/run_harness_evaluation.py`; `tests/test_harness_evaluation.py` (14 tests): `simulate.py` equals `project-material/harness/simulate.py` byte for byte and reads `backend/data` (120 orders, the app's 8 workshops); hand-worked rules (hard rules first, objective ranking, late workshops removed, days counted from the batch's sent date, least late when none is on time, the harness's queues used, piece counts per allocator); for all 120 orders under all six policies, the adapter's choice equals the app's recommendation or closest option; normal and shock replays finish (the harness raises on an ineligible choice); rebuilt days late agree with the harness's `late` flag for every batch. Mutation check (scratchpad): days from the dispatch date, late workshops ranked by objective, queues ignored, piece counts shared and a truncated completion day each make tests fail. 52 tests pass. First results (development, 15 Oct; normal run, official metrics): minimize_tardiness mean 8.1 days, p90 13.7, 2% late, 6% defective, cost 115,360, max share 25%; best baseline (random) 21.5, 45.6, 34%, 4%, 111,780, 23%. Baselines win on cost (cheapest 85,960, 93% late; our minimize_cost 101,005, 2% late) and on defects against minimize_tardiness (random and greedy_biggest 4% against 6%; hybrid 3%). Shock run: minimize_tardiness 8.3, 15.4, 2%, 6%, 115,665, 27%. External lateness (normal): minimize_tardiness 20 days late in total, against 704 for random. |
| 10. Docs | done 15 Oct | `README.md` (routing and allocation, harness evaluation, first results); `backend/AGENTS.md` (rule wording above, active-notebook line, new modules section, two placeholders removed); repository `AGENTS.md`; `MODULARIZATION_INSTRUCTIONS.md` (status notes only); `../docs/project-plan.md` (harness decision and location); `../docs/engineering-log.md` (entry, including why complete runs are planned as saved). |
