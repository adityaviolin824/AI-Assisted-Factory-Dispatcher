# Project plan

Updated: 22 October 2026. This is the active record of status, priorities and remaining work. Notebook 05 remains the reference for the modularized backend and its integrated LangGraph pipeline.

**Current work:** Project handoff records Aditya's latest priority: design the frontend, connect it to the existing API and check functionality through dispatcher review. Do not make allocation rates, model improvements or dedicated evaluation a prerequisite; Aditya will address those in later backend work. **Docker, containers, Compose and deployment come at the absolute end and must be ignored for now.** UI/API correctness, secret protection, isolated tooling and the no-Git instruction still apply.

**Core frontend scope correction:** build both Operations chat and Dispatcher in the current Next.js app, including the small chat API bridge and explicit conversation-snapshot-to-pipeline handoff. Use the existing mock chat and source for behavior; a saved-quote viewer/disabled Send is not completion. Both interfaces need sophisticated, distinctive dark designs using **build-web-apps:frontend-app-builder** and the broad visual guardrails, without fixing a palette/font/layout here. The read-only dispatcher already exists; preserve it and complete both interfaces. Send/history/export do not need model calls; actual paid snapshot processing remains separately authorized.

**Latest approved review workflow:** choices remain local and unsaved while the dispatcher completes the whole set. One **Approve all** submits it; Python preserves his destinations, rearranges flexible work, saves immediately and shows the final table with before/after reasons. No per-edit database/checkpoint writes, recalculation, autosave or mandatory second approval. Built on 21 October 2026: `POST /reviews/{thread_id}/finalize` applies the whole set with one calculation, saves at once and records `changes`; the Dispatcher's Approve all uses it (backend proposal, section 2). The assignment MVP's main output is an explainable dispatch table. Keep the separate evaluation evidence for the final assignment, without expanding into a factory execution system.

**Final decision, 22 October:** supported structured human corrections go directly through Python, without repeating AI processing. Use one planning pass around fixed manual destinations, save, then always show the report. **Review again after reallocation** is optional and starts from the saved result; that return path is built as **Review again** (22 October, [completion plan](dispatcher-completion-plan.md)), and the remaining reallocation work is still pending. The [final workflow decision](system-design.md#final-workflow-decision-22-october-2026) records the sequence and supersedes older approval proposals. A new requirement that every dispatch request receive an explicit disposition, broader recovery forms and pre-submission preview calculations remain proposals. Current finalization can save unresolved rows; these notes do not establish a 100% completion guarantee.

- **Notebook 06:** read-only dispatcher views and cached explanations in Parts 1-7. Part 8 prototypes the dispatcher decision loop (19 October): typed corrections, workshop choices, accepted lateness and approvals, recalculated from the original queues. Part 9 shows both views on one Gradio screen, where the same decisions are entered into Part 8's decisions (the latest counts) and recalculated at once; Parts 8d to 8f save them.
- **Dispatcher review in the graph, implemented 20 October:** the dispatcher calculation is modularized in `backend/dispatcher_review/`, and the pipeline graph pauses for the dispatcher's review with LangGraph's `interrupt()`. The paused draft is kept in a SQLite checkpoint; `resume_dispatcher_review.py` shows it or sends one answer; one final `approve_all` saves the review last shown as JSON. Notebook 06 stays unchanged; the new approval semantics are declared and tested (123 offline tests pass). Implemented as the final graph review plan, which superseded the earlier API-first proposal and keeps **Review again after reallocation** as a parked requirement. The first FastAPI endpoints (20 October) read saved runs and show or answer a paused review (build record); the frontend, operational assignments and reallocation follow later; there is no assignment database.
- **Dates:** since 18 October, a deadline on or before the dispatch date is review-only, and agreed relative delivery dates are resolved in Python. Since 19 October, when no deadline is selected, a written date or time word outside dispatch wording asks a question.
- **Fresh run:** Test 7 of the [prompt testing record](../backend/docs/evaluation/PROMPT_TESTING_RESULTS.md) measured these changes on the 30 requests: readiness 27/30 against 28/30, and no silent error. Three of the misses came from "due Apr 13"-style copies. After a Python fix the same day, its saved answers replay at 30/30 with no API call.
- **100-case golden set (21 October):** AI custom-created varied scenarios after repeated experiments to emulate real dispatch situations and target observed weaknesses. Three team members divided the work and comprehensively hand-reviewed all 100 cases and 149 messages line by line; this was human review, not AI review. The [version 2 golden key](../backend/docs/evaluation/extended_dispatch_100_human_team_golden.json) and [review record](../backend/docs/evaluation/extended_dispatch_100_REVIEW.md) reconcile 12 unstated preferences to `none`, whose default is to minimize lateness. Offline checks still find 85 jointly feasible recommendations and 15 exceptions. Model accuracy on this set remains unmeasured; no paid run is authorized by this review.

The queue and live SQL section reflects the review of notebook 04 on 13 October; notebook 05 keeps that queue code. The earlier processing v3/allocation v4 run evidence retains its 10 October baseline.

Read the [backend README](../backend/README.md) for the implementation, [system design](system-design.md) for rules and decisions, and [project explanation](project-explanation.md) when preparing a presentation. Older proposals are preserved in the archive.

## Where the overall plan lives

| Topic | Active document |
|---|---|
| Build sequence, current status, open decisions and evaluation | This project plan. |
| LangGraph's planned role and application data flow | [Planned application architecture](system-design.md#7-planned-application-architecture-and-langgraph). |
| Landing page, operations chat/voice page and dispatcher console | [Planned frontend](system-design.md#8-planned-frontend-pages). |
| Notebook behavior, settings and saved outputs | [Backend implementation](../backend/README.md). |
| Broader original architecture and product direction | Overall guideline, especially sections 3–4, 7 and 8–13. It is preserved as reference context. |

The active documents now carry the product direction alongside implementation status. A planned page or graph node is not an implemented capability.

## What the project should achieve

Help one dispatcher choose an outside workshop and explain the choice. The Factory Primer gives three checks: can the workshop make the batch, can it take the work given its capacity and queue, and is it allowed to take it?

The practical MVP deliverable is the final dispatch table, including human choices, calculated delivery/queue effects, unresolved cases and why any flexible allocations changed. Aditya's manual decisions are authoritative; automatic recommendations still use the normal rules. Reallocation here concerns the proposed batch plan, not transferring production already started. Operational databases, workshop notifications and real factory deployment are not prerequisites for demonstrating this assignment MVP.

For most tasks, avoiding lateness and reducing delivery time are the first priorities. Delicate or expensive work may give much greater importance to a low defect rate. Cost and workload concentration also matter. Software response time is a separate performance measure; making an API call faster does not establish a better workshop choice.

These priorities must operate within workshop eligibility and the request's restrictions. A quality preference does not silently waive the deadline or permit an otherwise ineligible workshop.

## Where we are now

| Area | Current position | What is still missing |
|---|---|---|
| Chat processing | Current modules own target messages once, preserve evidence, link supported follow-ups and verify current task versions. Interpretation failures become review records; potentially affected requests continue with provisional warnings. Date checks retain the written year. Only delivery wording sets a deadline, and Python counts agreed relative delivery words from the message date (18 October). | Refused/wrong links, dropped or mislabelled instructions, ordinal dates, human resolution, a paid check of the 18 October verification prompt and unseen interpretation evaluation. |
| Allocation | Modular routing and allocation preserve the tested rules, reference-workshop gate and EDD planning. The graph uses its own run state directly, with no disk handoff. Provisional recommendations reserve tentative queue time. | Persistent assignments, live status enforcement, committed dispatcher approval and reallocation. |
| Quality preference | An explicit quality preference selects the defect-rate-first ranking. Expected rework also affects delivery estimates. | A defined way to recognise delicate/expensive work and evaluate any additional quality weighting. |
| Outputs | Module runs use `backend/output/runs/<start time>/`: manifest, state, calls, plan and plan-history. Plans include review warnings, input accounting, completeness and missing outcomes. Objective plans preserve the default. | Durable operational state and graph waits; no code/data fingerprint enforcement or processing resume is implemented. |
| Verification | Offline checks in `backend/experimentation_notebooks/testing/` pass: notebook structure, C1–C14, end-to-end equivalence with notebook 04, and the I03/I04 repairs. All 123 tests in `backend/tests/` pass (20 October 2026): 23 for the intake and processing modules, 25 for routing and allocation, 15 for the harness adapter, 23 for the LangGraph pipeline and its review pause, 22 for the dispatcher review modules, 4 for the HTTP API and 11 for the run report (`backend/make_run_report.py`), which writes a report into a run folder and can score it against a JSON answer key. `check_notebook_06.py` checks notebook 06's views and its Part 8 decisions offline, and builds its Part 9 screen. | Expand scenario coverage and score decisions/explanations on unseen requests. Historical harness results are recorded below; they do not establish model interpretation accuracy. |
| Application | Modular backend and FastAPI routes for runs, reviews, one-batch approval and Review again exist. The chat bridge (send, history, snapshots and snapshot processing) was built on 23 October 2026. The Next.js Chat and Dispatcher pages call these routes. | Current focus: design both dark core interfaces, complete chat capture/history/snapshot/processing integration and the dispatcher batch contract. Later: dedicated model/allocator evaluation, reallocation, operational assignments and Docker/deployment. |

The current notebook is 05-order-pipeline-mvp.ipynb. Its explanation and implementation describe the flow, the storage simplification and the evidence. Earlier notebooks are kept for comparison and history:

- processing v3 and allocation v4, the 10 October baseline;
- processing v4, allocation v5 and notebook 04.

The redundant earlier allocation draft was removed on 10 October after confirming its useful explanations are retained in the allocator; its recorded outputs remain historical evidence.

Notebook 05's run `runs/2026-10-13_12-13-34` replayed saved answers, with 0 paid requests. Results:

- 29 tasks, 18 of them ready;
- 2 recommendations, 16 reviews, 10 clarification tasks, 1 reference question and 1 non-task message;
- all 30 messages accounted for.

The saved outputs equal notebook 04's, apart from the fields 05 no longer saves. The outcome counts also equal those of the recorded processing run `20261010T011019Z-4326b087` and its saved v4 plan. Both are development outcomes, not scored accuracy or committed assignments. The v4 review holds the historical verification. The issues record holds processing fixes and remaining errors.

## Planned product

The product has three pages: a landing/demo page for evaluators, an operations page with chat channels and later voice-to-text, and a dispatcher console with a unified review queue, evidence, comparisons, assignment controls and supported decision Q&A. One dispatcher remains the authoritative decision role. Build the text request-to-review flow first; add channels and voice after its behavior is measured. The [frontend design](system-design.md#8-planned-frontend-pages) describes what each page shows and why.

The recorded technology direction is Next.js/React for the frontend and Python with FastAPI for the backend (first endpoints built 20 October 2026). Notebook 05 already uses LangGraph for the batch pipeline. The dispatcher review recalculates from saved inputs and structured decisions; since 20 October 2026 the same graph pauses for it and resumes from a SQLite checkpoint. Other persistent waits are optional later work if requirements justify them. Python functions continue to enforce eligibility and calculate allocations. The API server exists; the frontend is the current implementation focus. Docker and deployment are deferred to the absolute end.

## Work in this order

1. **Establish a repeatable verification and evaluation baseline.** Preserve the complete run and its settings. Retain C1–C14 and the offline checks of notebook 05, plus the module tests in `backend/tests/`; the earlier processing checks cover processing v3. Extend coverage for source dates and broader conversation cases. Prepare expected behavior for all 30 requests, record known interpretation errors and reserve unseen cases before further tuning. Success means results can be reproduced without old compiled test files, and counts are separate from accuracy scores.
2. **Extend policy evaluation from the recorded baseline.** The adapter and its mandatory-choice/least-late contract are implemented, with five objectives and the hybrid compared against three baselines in normal/shock runs. Keep the current default and these results as the baseline for further policy experiments. Compare quality-sensitive cases, define supported inputs for delicate/expensive work and decide conflicts with a hard deadline. Do not invent numerical quality weights or infer order value from workshop prices.
3. **Modularization is complete (15 October 2026).** Intake, processing, routing, allocation and the full batch graph are implemented; this is a completed milestone, not outstanding work. Move any further notebook code in small steps and compare results before and after each move. Preserve task identity, evidence checks, version invalidation, run-completeness checks, ranking formulas and tentative queue behavior. Choose module boundaries around responsibilities already demonstrated by the notebooks.
4. **Prototype a small dispatcher calculation before the interface or persistent state.** Follow the dispatcher plan in notebook 06. **Its first increment is implemented in Part 8 (19 October 2026); duplicates, cancellations, link reviews and the blocker fixture remain.** First use the retained original-request Luna fixture: structured human corrections validated in Python, manual workshop choices, explicitly acknowledged least-late choices (future deadlines only; a past deadline needs a confirmed revised deadline), protected workload and final JSON. Rebuild from the same source run and one decisions file. Keep approved workshops and relative protected order; pack their production/rework and carry their piece counts before allocating flexible tasks. Earlier completion is allowed; worsening an approved estimate is not. Use one calculation with preview/finalize modes; unresolved warnings never become approved merely through finalization. No paid run, AI summaries, free-text parsing, Excel, frontend or review-specific LangGraph loop in this increment. Add the blocker fixture afterwards for human recovery of old holds and intake reviews. Part 9 (19 October) prototypes the two views on a Gradio screen to settle the dispatcher page's functions and data contract; the React page and a JSON-derived Excel workbook remain later increments. Persistent operational assignments may later use project-local SQLite and transactions; those are not prerequisites for the file-based prototype. Source CSVs and simulator queues stay separate.
5. **Connect dispatcher review before the interface.** **Implemented 20 October 2026** as the final graph review plan: the demonstrated calculation is extracted, the current draft is checkpointed in SQLite, the review resumes, and one approval saves the displayed valid allocations as final JSON. The original notebook stays frozen and its intentional approval differences are declared in the tests. No API/frontend or operational assignment database in this increment; the known Gradio selection issue stays recorded. Evaluation continues in parallel. Next, design/connect the API, dispatcher page and operations-to-dispatcher text journey, including their acceptance tests. Preserve the later optional review after reallocation and present implemented capabilities separately from plans.
6. **Complete evaluation, then add extensions.** Repeat the frozen comparisons, score the 30 messages and unseen cases, and present failures and limits. Add multiple channels, voice transcription and monitoring only after the core dispatch flow passes its acceptance cases. Voice feeds the same text pipeline; it does not get a separate allocator.

No new feature is implemented by this document. Exact timing and feature ownership still need team agreement; do not present this list as a completed sprint commitment.

## Workshop queues and the planned live SQL workflow

### Current notebook behavior

Checked against notebook 04, particularly `candidate_metrics`, `plan_tasks` and `plan_allocation`. Notebook 05 keeps this queue code: `candidate_metrics` is unchanged, and `plan_tasks` differs only by the removed `policy_version` field (checked by `testing/check_structure.py`).

- A queue is estimated days of production work; capacity remains pieces per day.
- `plan_tasks` copies the starting queues. Each feasible recommendation adds `processing_days + expected_rework_days` to the selected workshop's temporary queue. Later tasks in that plan see the increased workload.
- Production time (`processing_days`) is `pieces / capacity`. The current expected-rework estimate is `processing_days * defect_rate * 0.5`; preserve that formula during modularization.
- Pickup/transport time affects delivery estimates but does not occupy production capacity. Reviews and clarification items add no workload.
- For illustration, a 3-day starting queue plus 2 production days and 0.02 expected rework days becomes 5.02 days in the temporary plan.
- The saved plan records queues before and after planning. It does not commit an assignment or update the workshop CSV. A separate plan starts from the original loaded queues and does not automatically inherit earlier recommendations. The notebook also does not reduce workload as time passes or refresh workshop progress during a run.

**Current operating assumption:** run the prototype separately against fixed CSV inputs. Overlapping runs and changing CSVs are outside this intended use. Modularization is complete under that assumption; later refactoring must preserve the demonstrated rules. Configuration files hold settings; live workload will come from operational storage.

### Future application behavior

**Planned, not implemented:** read current workshop data from SQL and persist confirmed assignments. The existing deterministic calculations can be reused, with explicit inputs supplied from the database. Replacing the CSV reader alone does not implement assignment writes or live updates.

1. Read current order and workshop facts, including status, category support, batch caps, capacity and outstanding workload. Calculate a recommendation using a consistent snapshot and a temporary queue copy.
2. Show the recommendation as a preview. Viewing it or leaving it for dispatcher review does not commit workload. The file-based MVP's authorization modes are specified in the dispatcher plan; a later live commit must still recheck relevant facts before writing operational state.
3. At confirmation or the agreed commit point, recheck the task and relevant order/workshop facts. Even with one dispatcher and separate allocation runs, workshop progress can change between preview and confirmation. Recalculate when relevant facts have changed before committing the choice.
4. Save the assignment, its workload reservation and history together in one transaction. Use database locking or version checks to protect the recheck and write from intervening updates. A repeated confirmation must not add the same batch twice; a failed commit must leave no partial assignment or reservation. Choose the exact SQL mechanism during implementation; see [SQLite transaction documentation](https://www.sqlite.org/lang_transaction.html).
5. Read the updated operational workload for later allocations. Workshop progress updates should reduce remaining work used in subsequent estimates; they do not automatically refresh a queue dictionary already held by a running calculation.

**Queue ownership decision still required:** define whether a workshop's reported total already includes our committed batches. Adding those batches again would count the same work twice. The preferred direction is assignment records with remaining work/progress per batch, from which code derives the queue. Work accepted outside this app must also be represented. An alternative is a workshop-maintained queue total, with an explicit agreement about what it includes and how new reservations are incorporated. Do not have the app and workshop independently overwrite the same total with incompatible meanings.

**Reason and expected effect:** current facts let the dispatcher check whether a workshop can make the batch, can take it given its remaining workload, and is allowed to take it, as required by the Factory Primer. Persistent assignments carry workload into later runs; progress updates keep estimates current; protected commits prevent lost or duplicated reservations. This extends storage and the commit workflow without changing the ranking policy or giving arithmetic to the LLM.

The recorded starting direction remains project-local SQLite, as described in [system design](system-design.md#storage-and-workflow-choice). A server database can be reconsidered when deployment or workshop-update requirements justify it; this addition does not select a new database or implement a live connection. Source CSVs and the historical simulator remain separate from operational state.

### Checks required when this workflow is implemented

- A recommendation increases only its temporary queue; a review changes neither temporary nor committed workload.
- Confirmation persists the batch once, and the next allocation sees it. Workshop progress and external work are reflected without counting a batch twice.
- A changed queue, capacity or status between preview and confirmation triggers current checks and recalculation before commitment.
- Repeated confirmation creates no duplicate assignment; transaction failure preserves the previously committed state.

These are future acceptance checks, not claims of implemented SQL behavior or completed tests.

## Decisions still requiring an answer

| Decision | Current boundary |
|---|---|
| How do we identify quality-sensitive work? | An explicit quality request works today. Order value and delicacy are not established inputs to the policy. |
| Should quality use a first-priority rule or a weighted trade-off? | Allocation v4 retains the quality-first policy. Its current hybrid has no direct defect-rate weight. Compare alternatives before choosing new weights. |
| What if no allowed workshop meets the deadline? | The normal plan sends the request for review and reserves nothing. A different deadline or exception needs an explicit decision. |
| Which doubts can be nonblocking? | Processing v3 blocks readiness while clarification questions remain. The older optional-note proposal is not current behavior. |
| What approves an initial assignment? | A notebook recommendation is only a preview. The application's automatic-versus-human-confirmed commit policy is unresolved. |
| Who owns live workshop workload? | Define whether workshop reports include our assignments. Prefer per-batch assignments and remaining-work updates, including external work, before deriving the queue. See the live SQL workflow above; no operational queue is implemented yet. |
| What can be moved after work starts? | Every order should allow a re-dispatch request. Started/completed work needs a remaining-work, recall or rework policy before automatic transfer. |
| How should live calendars and status work? | The experiment uses a fixed dataset snapshot and elapsed-day estimates. Live dispatch requires an explicit status policy and a calendar decision. |
| What if a chat deadline differs from the order's CSV deadline? | Recognized, deferred edge case. The preferred future policy is to use the trusted CSV deadline until an authorized update, show the dispatcher both dates and the original message, and ask whether the recorded order deadline needs correction. Comparison, alerts and resolution are not implemented in this increment. |
| Do standing instructions apply across requests? | R12's QuickStitch instruction is task-local today. Global scope, expiry and source evidence need a decision before enforcement across a channel or all tasks. |
| How will the allocator serve the harness? | Decided 15 October 2026 (Aditya). The harness requires one eligible workshop for every batch, where the app would ask for review: when no eligible workshop is on time, the adapter returns the least-late one (the app's closest option). It keeps the app's unrounded on-time check, although the harness rounds completion dates. See the [backend README](../backend/README.md#harness-evaluation-simulatepy). |

**Deadline discrepancy to discuss with the professor:** An illustrative order has a CSV due date of April 10, but its chat request says April 8. Either the message or the stored date could be outdated; accepting one silently can change which workshop appears able to deliver on time. A future dispatcher alert should expose the discrepancy and preserve the evidence before an authorized deadline update and recalculation. This supports the Factory Primer's capacity/queue and delivery-feasibility decision. Keep this reconciliation out of the current implementation to limit complexity. The current code still permits a confirmed chat-date override and otherwise uses the CSV date; this documentation update changes neither deadline handling nor task order.

## Evaluation and evidence

### Historical scheduler replay

Keep the supplied [simulator](../harness/simulate.py) and input CSVs unchanged. The 120-order replay includes historical completed orders; it is separate from live dispatch and from the 30 chat requests.

Compare the chosen primary objective, another objective and a weighted hybrid against all three supplied baselines, including a shock run. Report where a baseline wins. Preserve the simulator's six official metrics and definitions: mean delivery days, p90 delivery days, percentage late, percentage defective, cost and maximum workshop share. Report any extra lateness-severity measures separately.

Use the same inputs, seed and normal/shock scenarios for random eligible, highest capacity, cheapest and our policies. The adapter was built on 15 October 2026 as `backend/eval_harness/run_harness_evaluation.py`: Aditya chose `backend/` over the `evaluation/` folder, so it is version-controlled with the allocation modules it scores. It benchmarks the modularized notebook 05 allocation rules (five objectives and the hybrid, normal and shock runs); older log entries describe earlier policies, not these results. The notebook uses a fixed 1 April snapshot and strict unrounded deadlines, while the harness uses each order's arrival and its own completion-date rounding: the adapter counts the days available from each batch's sent date and keeps the unrounded check. First results are in the [backend README](../backend/README.md#harness-evaluation-simulatepy).

An external evaluator should derive tardiness from the same replay outcomes: `max(0, completion_date - due_date)`, with mean tardiness across all batches and late batches, p90 tardiness and total tardiness days. Keep the six official outputs beside these additional measures. Piece-days late is an optional extension, not an official metric.

A policy named robustness is not evidence of robust performance. Show its measured response to the shock scenario. Similarly, a low predicted defect rate is an estimate, not a guarantee of defect-free production.

### Request interpretation and explanation

Evaluate all 30 supplied messages by their required behavior. Score interpretation/decision correctness separately from explanation correctness. Inspect evidence fidelity, missed jobs, duplicate jobs, follow-up linking, corrected requirements, readiness, requested/excluded workshops and unsupported questions.

Analyse at least 10 failure cases and explain what caused them. These 30 messages have already been used for debugging and prompt development, so their results are development results. Include unseen requests before claiming generalisation. Count messages, extracted items, tasks and allocations separately: a matching total alone does not prove correctness.

Report model/API latency, calls and token use separately from delivery outcomes. Keep prompts, settings and input identity with results so comparisons describe the same experiment. No fresh model evaluation or performance claim was produced by this documentation update.

### Application, graph and explanation evaluation

| Component | Evidence to collect when implemented |
|---|---|
| Interpreter | Schema validity, correct intent/order/date fields, constraint precision and recall, appropriate clarifications and invented-field counts against labelled source evidence. |
| Deterministic allocator | Eligibility and calculation checks, no invalid selections, preserved ranking/tie-breaks, no reservation for review, unchanged starting snapshot. Retain C1–C14 and extend current run-state, partial-accounting and provisional-warning regressions. |
| Future persistent workflows | When implemented: correct branches and tool arguments, replies attached to the right request/version, restart behavior, repeated replies/clicks without duplicate assignment, stale preview rejection and transaction rollback. The dispatcher review pause (20 October 2026) already checks resuming after the program ends, refused answers, changed inputs and repeated reviews without double reservations. |
| Explanation assistant | Claims agree with recorded metrics and rejection reasons; changed constraints invoke deterministic recalculation; unsupported history/pricing questions get an explicit limitation. |
| Frontend journey | Text entry to review/decision, clarification returning to its source channel, consistent review/assignment states, clear informational alternatives and successful task completion. Later voice tests assess transcript fidelity and the same dispatch journey. |

Use deterministic checks and a human-reviewed behavior rubric first. DeepEval is a planned supplement for semantic intent, explanation groundedness, tool correctness and conversation completion after those components exist. It is not currently wired into this pipeline. Choose its current APIs at implementation time; a model judge does not establish numeric or eligibility correctness. Follow the guideline's evaluation framework without adding retrieval metrics to exact CSV/database lookup.

Freeze the first scored baseline, expected answers, inputs, prompts, settings, source fingerprints and metric definitions. Repeat the same comparisons after meaningful changes and at final handover. Preserve objective experiments side by side using v4's separate filenames. Record new tests separately when extending the evaluation set.

### Future regression tooling review

Added 15 October 2026 at Aditya's request. [campusx-official/rag-eval-deepeval](https://github.com/campusx-official/rag-eval-deepeval) now exists locally under `backend/full_evaluation_suite/rag-eval-deepeval/` and has received a read-only relevance review. Its regression comparison, semantic scoring, telemetry, safety and LangSmith examples are retained as reference; only three approved clutter files were removed. No DeepEval integration, dependency installation or evaluation run has occurred. Licence, dependency/API compatibility and suitability of individual metrics still need checking before adoption.
The existing 87 offline tests remain the current implementation baseline. Later work should:

1. Build on the completed content review: check licence, dependencies, maintenance and current APIs, then identify useful coverage beyond the existing tests.
2. Select tests relevant to our request interpretation, provisional warnings, constraint retention and recorded decision explanations. Evaluate any retrieval-specific techniques against our actual CSV/structured-data workflow before adopting them.
3. Keep expected outcomes and scoring rules separate from application inputs. Distinguish deterministic checks using saved responses from fresh model samples and judge-based evaluation; record costs and obtain the existing required approval before paid calls.
4. Trial a small set of representative cases, including known warning/linking failures, and verify that a deliberately wrong result is detected before adopting more tooling.
5. Record the chosen components, actual verification results and limitations before presenting this integration as an implemented capability. Keep this proposal out of `FEATURES.md` until it is implemented and checked.

### Sprint and final presentation checklist

- **Sprint 1:** Problem, business value, proposed solution, architecture, risks, assumptions, chosen primary objective and a roadmap with success criteria.
- **Sprint 2:** Working demonstration, implemented/planned feature status and owners, plus early validation evidence.
- **Sprint 3 and final:** Final demonstration, baseline/objective/hybrid comparisons, shock results, request and explanation evaluation, failure analysis, limitations and reproducible records.

These requirements are carried forward from the earlier project plan and the project guideline. Reference documents remain unchanged; parts describing proposed architecture or unresolved formulas are historical context, not proof of today's implementation.

## Deferred work and records

Voice, multiple live channels, vector retrieval, broader information answering and operational charts remain later work. The three-page direction is retained in the [frontend design](system-design.md#8-planned-frontend-pages). Live ingestion should retain message, channel, sender, timestamp and original text. Charts should display recorded backend calculations. Neither requires a new model-led allocation calculation.

**Dispatcher run selection (Aditya, 21 October 2026).** Temporarily, the Dispatcher page lets the user choose any old saved run, so reviews can be tested without processing new messages; remove this once the chat-to-dispatcher path works. Later, give runs production names that a dispatcher can choose by date, time and possibly order count, for example "19 September 2026 Allocations - 15 Orders"; today a run is named by its processing start time and source file, with a message count rather than an order count. See the frontend plan.

Use the [engineering log](engineering-log.md) for meaningful problems, failed approaches, established causes, fixes, verification and uncertainty. Use interview preparation to practise defending the actual work and distinguish personal contributions from AI assistance. The identical backend copy stays available beside the code; keep the two copies in sync when changing those learning rules.
