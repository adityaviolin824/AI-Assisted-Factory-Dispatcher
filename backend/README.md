# Backend implementation

Backend for [AI-Assisted-Factory-Dispatcher](../README.md), the repository for SweaterCo Dispatch Copilot.

Last checked: 20 October 2026, after adding the dispatcher review pause to the graph. The current application path uses the Python modules, `run_full_pipeline.py` and `resume_dispatcher_review.py`; the first FastAPI endpoints (`main.py`) serve saved runs and the paused review. Notebooks 05 and 06 are the experimental references; intentional differences are declared in the module tests.

**One-batch final approval, implemented 21 October:** the dispatcher completes all choices locally, with no per-click mutation, recalculation or persisted edits. One **Approve all** submits the set through `POST /reviews/{thread_id}/finalize`; Python keeps the dispatcher's destinations, schedules flexible work, saves immediately and returns the final dispatch table plus changed rows. **Check workshop options** (22 October 2026) sends the same set to `POST /reviews/{thread_id}/preview`, which runs that calculation and returns the draft and its changed rows, or the refusal, without saving, approving or resuming anything. **Review again** (22 October 2026) reopens an approved plan: `POST /runs/{run_id}/preview` and `POST /runs/{run_id}/finalize` add new choices to the saved ones, plan once from the original queues and save a new version, keeping the earlier one in `plan-history/`. This supersedes the older per-edit checkpoint/empty-approval interaction described below. Further reallocation remains pending. Docker comes at the absolute end.

For the earlier notebook stages, see the [experiment guide](../experiments/README.md), [development notes](../experiments/development-notes.md) and [timeline](../experiments/timeline.md). The public notebook copies retain the rules of their historical versions; they are not the current application entry points.

The backend turns factory chat into checked tasks and deterministic workshop allocation previews. It answers whether a workshop can make a batch, can take it given capacity and queue, and is allowed to take it. For most requests, avoiding lateness and reducing delivery time come first; explicit quality and cost preferences select their recorded policies. A general rule for delicate or expensive work still needs defined inputs and evaluation.

Reallocation, committed assignments and the product frontend remain future work. The first API routes read saved runs and show or answer a paused review. The existing mock group chat stores shared messages in SQLite and exports TXT snapshots; it does not invoke processing automatically.

Notebook 06 now provides read-only dispatcher views of a saved plan, cached explanations for allocation/review items and a TXT export. Information questions stay outside allocation and make no explanation-model call. Parts 1-7 only read the plan. Part 8 (19 October 2026) prototypes the dispatcher review loop with no model call: typed decisions correct a deadline or order ID, choose an eligible workshop, accept lateness or approve rows, and every review recalculates from the original queues with approved work placed first. It writes only `dispatcher-decisions.json` and `dispatcher-plan.json` in the run folder, and only once a decision is entered. Part 9 (19 October) shows both views on one Gradio screen inside Jupyter: each decision goes into Part 8's decisions, so the latest decision counts, and recalculates the plan and queues at once with Part 8's calculation; it makes no model call, and Parts 8d to 8f save the decisions. Gradio is a `dev` dependency, installed by `uv sync`. Its implementation notes record the scope, original paid run and offline checks. The notebook stays unchanged as the reference: its Part 8 per-row approval is the earlier prototype, and the [dispatcher review modules](#dispatcher-review-modules) replace it with one final approval.

## Which script to use

Run commands from `backend/`, using the project-local `uv` environment.

| Script | Purpose | Model calls |
|---|---|---|
| `uv run python run_full_pipeline.py` | Configured chat file to processing, allocation and a paused dispatcher review in one LangGraph run; prints the review and its thread ID. | Cache misses can make paid calls. |
| `uv run python resume_dispatcher_review.py <thread ID> [<answer.json>]` | Show a paused review again, or send it one answer. | None. |
| `uv run fastapi dev main.py` | Local HTTP API: list and read saved runs, show and answer a paused review by thread ID, save the operations chat and capture snapshots of it (in `output/chat/`); open `http://127.0.0.1:8000/docs`. | None: processing a chat snapshot is refused. |
| `ALLOW_PAID_PROCESSING=1 uv run fastapi dev main.py` | The same API, where `POST /chat/snapshots/{snapshot_id}/process` also runs the pipeline on one snapshot in the background, up to a paused dispatcher review (23 October 2026, `fastapi_routes/chat.py`). The chat page shows the run and links to its review. | Cache misses can make paid calls. |
| `uv run python run_intake_and_processing.py` | Processing only, for prompt/model experiments. | Cache misses can make paid calls. |
| `uv run python run_allocation.py output/runs/<start time>` | Replan one explicitly named saved processing run. Without a folder, list available runs. | None. |
| `uv run python -m eval_harness.run_harness_evaluation` | Historical scheduler comparison beside the unchanged course simulator. | None. |
| `uv run python make_run_report.py output/runs/<start time>` | Write `run_report.md` into a saved run folder; add `--key <key.json> --data <data folder>` to score it against an answer key. | None. |
| `uv run python score_dispatcher_review.py output/runs/<start time> --key <key.json> --data <data folder>` | Score the table after the dispatcher's review against an answer key; writes `dispatcher_review_score.md` into the run folder. | None. |

Obtain approval before any run that could make paid model calls. A previously free run does not establish that the current flow is fully cached.

## Intake and processing modules

`config.toml -> read_chat_messages -> extract_items -> create_and_link_tasks -> verify_tasks -> processing_run`

| File | Responsibility |
|---|---|
| `config.toml` | Input/output paths, the message date, stage models, reasoning efforts, batching and allocation settings. Paths are relative to `backend/`. |
| `order_intake_from_chat/read_chat_messages.py` | TXT snapshot to numbered source messages. |
| `order_processing_into_tasks/settings_and_data.py` | Load settings and the trusted CSV lookup dictionaries; provide JSON save helpers. |
| `order_processing_into_tasks/model_prompts.py` | Intake, linking and verification prompts. |
| `order_processing_into_tasks/model_calls_with_cache.py` | Cache lookup, paid calls when needed, structured responses and per-call records. |
| `order_processing_into_tasks/extract_items.py` | Extract owned target messages; check coverage, verbatim quotations, duplicates and written order IDs. |
| `order_processing_into_tasks/create_and_link_tasks.py` | Create tasks or attach supported follow-ups; preserve ambiguous links for review. |
| `order_processing_into_tasks/verify_tasks.py` | Verify current task versions and scheduling evidence; turn agreed relative delivery words into dates; ask when a written piece count differs from the CSV; compute which tasks unresolved inputs may affect. |
| `order_processing_into_tasks/processing_run.py` | Run processing, check input accounting and save the state and summary. |

Current recorded model configuration: `gpt-5.6-luna` at all three stages, with intake at `high` and linking/verification at `medium`. A configured reasoning effort is sent instead of temperature. Extraction owns three target messages with two earlier context messages; verification batches up to three tasks within the configured payload limit.

Message, item, task and order IDs remain separate. A correction appends original evidence, increases the task version and clears its previous verification. Schema validity alone does not establish that the interpretation is correct. Unknown identity, missing essential facts, unsupported conditions and failed checks remain visible blockers or reviews.

Deadlines (decided 18 October 2026): only delivery wording such as "due", "deliver by" or "back by" sets a deadline; dispatch timing such as "send out today" does not. Without a chat deadline, the plan uses the order's CSV due date. The model copies relative delivery words exactly, and Python counts them from `message_date` in `config.toml` (1 April 2026 for the supplied chats): today, tomorrow, this or next week (ending on Friday) and this or next month (ending on its last day), each also after "by", "end of" or "by the end of". Any other relative words ask for a calendar date. A vague amount such as "usual quantities" is never estimated; the identified order's CSV quantity applies. When the model selects no deadline but the evidence has a written date or a time word such as "tomorrow" outside a dispatch clause, Python asks "Confirm which written date is the current deadline." (`possible_deadline_words`, 19 October 2026); the check can only add that question. A copied deadline that keeps its delivery word, such as "due Apr 13", is read by its one written date, which must still match the evidence.

Quantities (decided 19 October 2026, after Test 8): a piece count written for the identified order that differs from `orders.csv` blocks readiness. For "ORD-105, 1300 vests" when the CSV records 200, Python adds "The chat states 1300 pieces for ORD-105, but orders.csv records 200; confirm the quantity." (`stated_piece_counts` in `verify_tasks.py`). The CSV quantity is never replaced, and the check can only add a blocker.

Interpretation failures are recorded and other work continues. API, file and programming errors stop processing visibly; automatic retries and API-failure continuation are not implemented.

## Routing and allocation modules

`verified_tasks -> route_tasks -> plan_tasks -> recommend -> summarize_plan -> plan.json`

| File | Responsibility |
|---|---|
| `task_routing/route_verified_tasks.py` | Route verified tasks to allocation, duplicate-order review, clarification or reference. |
| `task_allocation_to_workshops/allocation_settings_and_data.py` | Load workshops, orders, initial queues, dispatch date and optional objective. |
| `task_allocation_to_workshops/workshop_rules_and_estimates.py` | Enforce eligibility and calculate delivery, expected rework, lateness, cost and share. |
| `task_allocation_to_workshops/rank_workshops.py` | Rank candidates under the five objectives or hybrid, with deterministic tie-breaks. |
| `task_allocation_to_workshops/recommend_one_task.py` | Produce one recommendation or an allocation review with its reasons and alternatives. |
| `task_allocation_to_workshops/allocation_plan.py` | Plan earliest deadline first, reserve tentative workload, account for inputs and save the plan/history. |

Hard checks run before selection: active status, product compatibility, batch caps, requested destination, exclusions and on-time feasibility. Splits and unsupported conditions require review. Independent verified allocation requests for the same order require batch clarification. A reference-only winning workshop also requires review rather than a silent assignment.

The allocator uses a queue copy. Only recommendations, including provisional recommendations, add production plus expected rework to that copy. Transport affects delivery but not production occupancy. Reviews reserve nothing. Another plan starts from the loaded snapshot; nothing is committed to a workshop or written back to the CSVs.

The fixed experiment dispatch date is 1 April 2026. A deadline on or before it is review-only (`deadline_passed`, decided 18 October 2026): no estimates, least-late option or queue time, because every workshop needs at least one day. Only a revised deadline that the dispatcher confirms can return the request to allocation; the original date stays on record. In the dispatcher review, the dispatcher's own workshop choice also allocates it, late (20 October 2026). A checked chat deadline may override the CSV date; a future mismatch alert and authorization policy remain planned. Historical completed orders remain allowed with a warning. Live status/calendar enforcement and remaining-stage work are not implemented.

### Provisional recommendations

An unresolved input that may change a task no longer automatically holds it. The task proceeds through normal verification using its established instructions. If it is ready and feasible, allocation can recommend a workshop while preserving the uncertain input separately for review.

- `plan["review_warnings"]` maps affected task IDs to the review/message/task rows that may modify them.
- `summary_rows` marks a warned recommendation as `provisional_recommendation` and asks the dispatcher to confirm whether the input applies.
- Raw records in `decisions` retain their ordinary status. Consumers must read the warning map and summary, not the raw status alone.
- Candidate task IDs are possible links, never confirmed attachments.
- Warning targets use explicit message/order references, otherwise the two preceding messages where applicable, then other requests for the same order. This can flag unrelated neighbours or miss distant corrections.
- Warnings are recomputed for each plan and saved in that plan, not stored as holds in processing state.

This supports previews, not approval to dispatch. An unresolved cancellation or exclusion can still make a provisional suggestion unsuitable. Dispatcher resolution and reallocation are future work. Old saved runs retain their original unverified held tasks; replanning does not create missing verification results. See [the diagnosed problem and solution](problems_solved/held_tasks_and_unresolved_followups.md).

### Plan files and incomplete processing

The allocator writes `plan.json` and the same in-memory plan to `plan-history/<creation time>_<plan file>`. `created_at` is separate from the date the plan reasons about, `dispatch_date`. An explicit objective writes `plan-<objective>.json` and an objective-named history copy without replacing the default. Processing's `manifest.json` and `state.json` remain unchanged.

Standalone allocation can plan an interrupted saved run. It sets `processing_complete: false`, prints a warning and lists unread messages, unlinked items and unverified tasks as `not_processed`. Missing work can change duplicates, planning order and queues; a partial preview is not equivalent to a complete plan. Use complete runs for comparable evaluation and retain provisional outcomes separately from final correctness claims.

An exception in the full graph stops it before allocation; it does not automatically produce a partial plan. `run_allocation.py` can subsequently plan that checkpoint. A graph run that finishes normally but is incomplete does reach allocation and produces a partial plan.

## Dispatcher review modules

`plan.json -> build_dispatcher_plan (first review) -> apply_answer (each answer) -> finalize_review -> save_dispatcher_files`

| File | Responsibility |
|---|---|
| `dispatcher_review/dispatcher_plan.py` | Apply the dispatcher's decisions to copies of the verified tasks, route and plan them as allocation does, and list every input with its outcome (`build_dispatcher_plan`). Label a copy of the shown review as final (`finalize_review`). Record the dispatch date and the order and workshop data a review was calculated from (`input_signature`). |
| `dispatcher_review/dispatcher_decisions.py` | Check one answer, apply it to a copy of the decisions and calculate the review again (`apply_answer`); the decision helpers; print a review; save the approved result. |

These are notebook 06's Part 8 cells, with the differences declared in `tests/test_dispatcher_review.py` (decided 20 October 2026, plan). The main ones: the dispatcher approves the whole shown review once, so per-row approve and release are gone; and the dispatcher decides, so every review plans the tasks with a chosen workshop first and the other ready tasks around them, each group earliest deadline first from the original queues. A review is a preview; no model is called.

An answer is one JSON object. Decisions are named after their helpers, and use the task IDs of this run's review:

```json
{"decisions": [{"decision": "choose_workshop", "task_id": "T:L0009:J1", "workshop_id": "W1"},
               {"decision": "correct", "task_id": "T:L0021:J1", "facts": {"due_date": "2026-04-20"}, "resolves": [0]}],
 "then": "review_again"}
```

```json
{"decisions": [], "then": "approve_all"}
```

```json
{"decisions": [{"decision": "choose_workshop", "task_id": "T:L0009:J1", "workshop_id": "W1"},
               {"decision": "accept_late", "task_id": "T:L0012:J1"}],
 "then": "finalize"}
```

- `correct` takes `facts` (`order_id`, `quantity`, `due_date`, `preference` or `intent`, as text; a quantity is a whole number of pieces that replaces the `orders.csv` quantity for that task in every estimate, batch cap and reservation, 22 October 2026) and `resolves` (blocker numbers shown in the review, from 0). `complete` takes the same `facts` and resolves every blocker of the request, so Python plans it as an allocation with the dispatcher's facts; it needs an order ID, given or already on the task, and an empty deadline means the order's due date (22 October 2026, [completion plan](../docs/dispatcher-completion-plan.md)). `add_batch` adds a batch that no row covers, such as one part of a split or a request processing missed: it takes `facts` (an order ID in `orders.csv`, required, and optionally `quantity`, `due_date` and `preference`; a fact left out is the order's own) and an optional `workshop_id`, but no `task_id`. Python names the batch `ADD-1`, `ADD-2` and so on, checks its facts as it checks a correction, and plans it as a row of its own whose reason starts "Added by the dispatcher." and names the other planned batches of its order. It skips the duplicate-order check and sends no other request to review; in the approved plan's `changes` its `before` is `null` (22 October 2026). `choose_workshop` takes `workshop_id`; a later choice for the same task replaces the earlier one. The chosen workshop is always used, even when it is late or the deadline has passed (shown as accepted lateness, with the original deadline kept) or it breaks a hard rule (status, category, batch cap or a request exclusion; the reason says "It overrides the hard rule ..."). It also overrides whatever processing left open on the task (missing facts, open questions, unhandled constraints, a split request or an intent other than allocation), and so does `complete`; the row's reason ends "It overrides what processing left open: ..." (23 October 2026). Python needs an order in `orders.csv`, given or already on the task, to build the batch; without one the answer is refused, so a choice is never saved and then ignored. A request with a chosen workshop, or completed with `complete`, skips the duplicate-order check and is planned; the other requests for that order stay in review (22 October 2026). `accept_late` accepts the allocator's late option shown for a task, up to that lateness or an optional `max_days` (0 or more), and must be sent alone. `warnings_checked` takes `row_ids` such as `["L0019"]`. `clear` removes a task's whole decision entry; named after a batch already added (`ADD-1`), it removes the batch, and the other decisions can change one (22 October 2026).
- `review_again` applies the decisions and returns a new review. The answer is all or nothing: an unknown task, decision or field, a wrong form, a blocker number outside the list, or a recalculated review with `decision_problems` refuses the whole answer, says why and changes nothing.
- `approve_all` takes no decisions. It approves the review last shown without planning again: every recommendation, dispatcher's choice or accepted lateness without an unchecked warning becomes `approved` with `final: true`; every other row stays unresolved. Approving a review with no edits is allowed and saves it.
- `finalize` applies the whole batch with one calculation and then approves it as `approve_all` does, so the page can send every choice at once. `accept_late` may come with other decisions here; if they make that task later than the review shown, the batch is refused with the reason. The saved final review also lists `changes`: each row whose outcome, workshop or delivery estimate differs from the review shown, with both versions and their reasons.
- Approval writes `dispatcher-decisions.json` and `dispatcher-plan.json` into the run folder, each with a copy in `plan-history/`. `plan.json`, `manifest.json` and `state.json` are not changed. A final review is saved JSON that may keep unresolved rows; it commits no workshop assignment and changes no live queue.
- Review again (`review_saved_plan`, called by `POST /runs/{run_id}/preview` and `/finalize`) starts from those two saved files and applies new decisions as `finalize` does: one calculation from the original queues, so nothing is reserved twice. Earlier workshop choices stay fixed; Python may move any other row, including one approved before (Aditya's decision, 22 October 2026). Its `changes` compare the saved plan with the new one as approval labels it, so an unchanged approved row is not listed, and a removed added batch is listed with `after: null`. A refused set saves nothing.

## Full pipeline (LangGraph)

`app_full_pipeline/pipeline_graph.py` connects the same module functions:

```text
START -> start_run -> link_items --after_link--> extract_batch -> link_items
                                 \-------------> verify_tasks -> save_outputs -> plan_allocation
plan_allocation -> dispatcher_review --after_review--> dispatcher_review   (pause again)
                                     \---------------> save_review -> END   (approve_all)
```

There are eight nodes and two conditional routers. The initial linking pass has no work in a fresh run. All extraction/linking finishes before verification. Nodes hold no business rules and return only changed state keys. One run writes the same files as processing followed by standalone allocation of that run, then stops at the dispatcher's review.

`plan_allocation` also calculates the empty decisions and the first review, so both are saved before the pause. `dispatcher_review` calls LangGraph's `interrupt()` with the saved review and the reason for any refused answer. On resume, LangGraph runs that node again from its start, so it only reads the saved review and applies the answer to that version; it writes no file. `save_review` labels and saves the approved review.

### Pausing and resuming

A paused run is kept by `SqliteSaver` (package `langgraph-checkpoint-sqlite`) in `output/dispatcher-review-checkpoints.sqlite`, under a new thread ID for each run, so it can be answered after the program that paused it has ended. The state is saved when a run stops (durability `"exit"`): at a pause, at the end or on an error, not after every processing step.

```text
uv run python run_full_pipeline.py                                    run to the first review; prints the thread ID
uv run python resume_dispatcher_review.py <thread ID>                 show the paused review again
uv run python resume_dispatcher_review.py <thread ID> <answer.json>   send one answer
```

Each `review_again` answer prints the new review, with changed rows marked, or the refusal and the unchanged review. A valid `approve_all` prints the final review and where it was saved, and ends the thread. A finished or unknown thread has no paused review. Leaving a review unanswered keeps it as a draft. A thread whose `orders.csv`, `workshops.csv` or dispatch date changed while it was paused refuses every answer until they are restored or the chat is processed as a new run. Keep the code unchanged while a review is paused.

### Cost and LangSmith

The response-cache fingerprint covers stage, model, reasoning effort or temperature, prompt, full payload and response schema. A matching answer is validated and loaded before an API client is created. The new call record says `reused_response: true`. Cached usage and timings describe the original call, not a new charge.

Changing a prompt, schema, setting or upstream result can change downstream payloads. Removing holds also sends previously skipped tasks to verification. Therefore the demo and blocker file may now need new verification calls even with unchanged model settings. Historical statements that these files were fully cached describe the earlier flow. Cached mistakes remain mistakes; replay is not a fresh model sample.

Historical run `2026-10-15_21-19-26`, before provisional warnings, reused nine extraction, six linking and three verification answers: 18 cached requests, zero new model calls. It took 23 graph-node steps. Remote verification confirmed its `full-pipeline` LangSmith trace, run ID `01a13fb7-b4de-77a2-88b4-e8cadecb751d`, starting 15 October at 21:19:26 Singapore time: final plan present, no recorded errors and 34 chain spans (root, 23 nodes and 10 router calls), with zero LLM spans.

With tracing enabled, valid credentials/configuration and network access, normal nonempty `run_full_pipeline.py` executions send chat text, state, the plan and the first review to LangSmith even when all answers are cached; each `resume_dispatcher_review.py` answer sends the review and the dispatcher's decisions. Resuming makes no model call. Tests disable tracing. Standalone allocation has no graph trace; standalone processing has no whole-run graph and cannot be assumed to log a fully cached execution. Remote receipt of one trace does not guarantee future uploads.

## Harness evaluation (simulate.py)

`eval_harness/run_harness_evaluation.py` calls the unchanged `../harness/simulate.py`, pointing its data lookup to `backend/data`. It compares all five objectives and the hybrid against random eligible, highest capacity and cheapest eligible in normal and shock scenarios: 18 policy/scenario combinations over 120 historical orders and eight workshops.

The adapter reuses the app's eligibility, calculation and ranking rules with the harness's batch arrival date and dynamic queues. Unlike the app, the harness requires one eligible workshop per batch. When none is on time, the adapter selects the least-late one. It retains the app's unrounded feasibility check; the harness rounds completion days. Piece counts are separate for each allocator. The app's past-deadline rule never applies in the replay: each batch is sent on its own order date, at least 14 days before it is due, so the harness scores are unaffected.

Report the six official metrics unchanged: mean delivery days, p90 delivery days, percentage late, percentage defective, cost and maximum workshop share. External tardiness measures are calculated from the same replay outcomes and printed separately.

Recorded normal replay: the default policy has 8.1 mean delivery days and 2% late versus random's 21.5 days and 34% late. Random has fewer defective batches (4% versus 6%) and lower cost (111,780 versus 115,360); cheapest has the lowest cost at 85,960 with 93% late. The default's shock result is 8.3 mean days and 2% late. See the [complete recorded tables](eval_harness/results/harness_results_2026-10-15.md). These are historical simulator results, not live guarantees or evidence of chat interpretation accuracy.

## Run reports

`make_run_report.py <run folder>` writes `run_report.md` into the run folder from the files the run saved: settings from `manifest.json`, processing counts from `state.json`, every plan row with its reason from `plan.json`, and each stage's calls, tokens, cost and model time from `calls/`. It makes no model call and changes no other file, so it can be repeated. "Cost in this run" counts only calls not answered from the saved-answer cache; "cost of a fresh run" prices every call. Prices are the table in `eval_run_report/run_summary.py` (checked 14 Oct 2026). On Test 8's run it reproduces the recorded $0.0705 for 37 verification calls.

With `--key <key.json> --data <data folder>`, the report adds a score against a JSON answer key in the format of `docs/evaluation/extended_dispatch_100_human_team_golden.json`, following [How the score works](docs/evaluation/NEW_TEST_SETS_PLAN.md#how-the-score-works-fixed-before-the-run):
- each case is matched to the task created from its first message, by order ID when that message holds two jobs;
- decisions: correct allocation (obeying the key's requested and excluded workshops), correct non-allocation (by any route), unsafe allocation and missed allocation;
- each missed allocation, and each allocation to another workshop than the key's own plan, gets one cause: intake, link, verification or allocation;
- the key's own plan is calculated by the app's routing and allocation rules from the given data folder;
- the allocator fields of verified matched tasks, the message labels and the follow-up links.

The data folder is named on the command line because a run's manifest does not record it and `config.toml` is restored after each test run. A run needs its `plan.json`; for a plan made before 15 October 2026 the review-warning count is reported as not recorded. The script refuses a key whose messages differ from the run's chat, a data folder that lacks the key's orders, and workshops that differ from those the run was planned with. The report gives the key's hash and, when present, its recorded human-review provenance. For the 100-case golden key this credits the comprehensive manual, line-by-line review by three team members and preserves the AI-authored draft origin. The script reproduces the recorded provenance; it does not perform or certify that human review.

`score_dispatcher_review.py <run folder> --key <key.json> --data <data folder>` scores the table after the dispatcher's review: by default the run's `dispatcher-plan.json`, or another table given with `--plan`, such as a copy in `plan-history/`. A table that has not been approved yet is scored as Approve all with no choices would approve it. Only approved rows count as allocated, and each counts for the case of its order, so a batch the dispatcher added also counts. The rules are in `eval_run_report/final_plan_score.py` and were written before Test 11. It makes no model call and writes only the score file (by default `dispatcher_review_score.md` in the run folder). `eval_run_report/key_informed_choices.py` is a simulated dispatcher that knows the key. It is for tests only; Test 11 used it to measure the app's ceiling ([end-to-end test](docs/evaluation/END_TO_END_TEST_2026-10-22.md)).

## Verification

The current baseline is **127 offline tests** (22 October 2026): 23 processing, 25 routing/allocation, 15 harness, 23 graph, 24 dispatcher review, 11 run-report and 6 API tests. Run from `backend/`:

```text
uv run python -m unittest discover -s tests -v
```

They cover declared notebook differences, exact prompts/schemas, source dates, routing, C1-C14, queue reservations, saved-state comparisons, cached end-to-end paths, graph equivalence, injected failures, partial accounting, history and provisional warnings. The dispatcher review tests compare the modules with notebook 06's Part 8 on 13 saved runs and one decision sequence, check every answer refusal, and pause, close and resume a run on a temporary SQLite file. Tests block model calls and network connections and disable tracing. Passing them establishes the checked implementation properties, not semantic accuracy on unseen messages.

The latest independent review replayed all 14 saved runs without changing their files. For the same saved states, decisions and tentative queues matched the notebook; only R14's summary row in the two Test 6 copies changed to a provisional recommendation naming R15. Formerly held tasks remain unverified in those historical states. A fresh processing run can verify more tasks and consequently change later tentative queue decisions.

## Current notebook: 05

Notebook 05 remains unchanged as the experimental reference. Its explanation, implementation record and offline checks describe that notebook. Its older hold behaviour differs from the current modules; the module tests explicitly declare intentional changes.

## The earlier pair: processing v3 and allocation v4

These are historical references, not the current storage or resume contract. The processing walkthrough, v4 review and [engineering log](../docs/engineering-log.md) preserve their handoff schemas, fingerprints, matching resume, source-order planning and recorded checks. Do not apply those older contracts to the current modules, which use in-memory graph state, EDD planning and the run-folder files described above.

## What to read next

| Document | Purpose |
|---|---|
| [Experiment notebooks and history](../experiments/README.md) | Processing, allocation, the combined graph and the first dispatcher screen, with selected debugging records. |
| [Prompt and model experiments](docs/evaluation/PROMPT_TESTING_RESULTS.md) | Historical scoring keys, model/prompt comparisons, costs and failures; add future approved paid runs here. |
| [Project plan](../docs/project-plan.md) | Product priorities, open decisions and evaluation requirements. |
| [System design](../docs/system-design.md) | Current rules and planned dispatcher, storage, graph waits and frontend. |
| [Presentation explanation](../docs/project-explanation.md) | A plain explanation of the current implementation and evidence. |
| [Project highlights](../FEATURES.md) | Supported strengths and measured results. |
| [Engineering log](../docs/engineering-log.md) | Debugging, verification and attribution. |

`review_tasks_processing/` is a future handler. The product frontend and operational assignment database are not implemented. The mock chat's SQLite database stores messages; it is not an assignment ledger.
