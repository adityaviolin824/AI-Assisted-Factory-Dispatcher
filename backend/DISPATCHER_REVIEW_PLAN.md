# Dispatcher review and allocation plan

Updated: 20 October 2026. **Notebook 06 Part 8 is implemented, and so is [DISPATCHER_REVIEW_GRAPH_PLAN.md](DISPATCHER_REVIEW_GRAPH_PLAN.md): the `dispatcher_review/` modules and the graph's persistent review pause (see the [backend README](README.md#dispatcher-review-modules)). The API-first proposal below is superseded.** Two approval designs now exist. Notebook 06 Part 8, unchanged as the reference, is the per-row approval prototype: `approve`/`release`, approved work protected and planned first, and `finalize=True`. The implemented graph has one final approval: the dispatcher edits, reviews again, then approves the whole review last shown, which is labelled final without planning again. The sections below on protected approved work, the `approved` decision field and the two completion modes describe the notebook prototype, not the graph. [Notebook 06](experimentation_notebooks/06-dispatcher-workflow.ipynb) now implements read-only allocation/review views, cached AI explanations and a saved TXT report; its [implementation notes](experimentation_notebooks/06-dispatcher-workflow.md) record the scope, costs and checks. Its Parts 1-7 stay read-only; Part 8 applies typed dispatcher decisions and recalculates without a model call. Part 9 (19 October) puts the two views and Part 8's decisions on one Gradio screen, to settle what the frontend page shows and sends; nothing is saved from it. The past-deadline rule below (`deadline_passed`, decided 18 October) is implemented in the allocator. This document supersedes the 17 October proposal's exact queue positions with gaps, model-only clarification path and larger first increment. The 17 October team PDF remains a dated snapshot of that earlier design.

## Proposed next increment: modules, a review API and frontend design

**Superseded proposal, retained as design history.** The [final graph review plan](DISPATCHER_REVIEW_GRAPH_PLAN.md) now takes priority: one automatically checkpointed draft, one final approval, final JSON output, and API/frontend work later. Its new approval semantics deliberately differ from notebook 06. Do not implement the API-first sequence or save behaviour below as the current increment.

Requested by Aditya on 20 October 2026. This is a plan, not completed implementation or approval to run paid requests. The recommendation is to proceed with the demonstrated review calculation while the team reviews the evaluation key. Scores are needed for claims about AI performance; they are not a prerequisite for moving unchanged functions or testing the review interface against saved runs.

The scope remains the Factory Primer's three questions: show capability, capacity/queue feasibility and permission, then let the dispatcher make the decisions already supported in Python. This increment is a saved-run review demo. A complete live dispatch system still needs request intake through the product, operational assignments, reallocation and its own acceptance tests.

### Readiness evidence and boundaries

- On 20 October, `check_notebook_06.py` passed its 15 saved-run cases, nine controlled decision cases and real-file preservation check (25 PASS lines). The controlled cases cover corrections, workshop eligibility, late acceptance, approved workload, repeated review, finalization and saving.
- The known Gradio selection issue still reproduces: `pick_task` returns link-review item ID `L0051:J1`, which is outside the dropdown's verified-task IDs. Gradio warns and rejects it. The first small fix should leave that row visible without selecting an unsupported task; add a focused check before moving the functions.
- Some buttons described in Parts 1-7 are proposed labels, not implemented actions. Duplicate merging, cancellation/dismissal, link attachment and reconstruction of intake/processing reviews remain deferred. The API must expose supported actions per row so these labels cannot become working buttons accidentally.
- Calculation and decision helpers currently use notebook globals such as `decisions`, `source_tasks` and `RUN_NAME`. Moving them means passing their required inputs explicitly, not reproducing the notebook kernel as server-wide mutable state.
- The calculator uses configured CSV data and dispatch date, while the display also reads the saved run. Use one fixed, explicitly identified data snapshot for the first demo. Do not silently recalculate an incompatible saved run against a different dataset/date. Supporting simultaneous datasets or changing workshop facts is outside this increment.

### Two implementation approaches

| Approach | Proposed files and logic | Benefit | Trade-off and risk | Verification |
|---|---|---|---|---|
| One dispatcher module | Put the calculation, decision helpers, file saving and JSON view mapping in `review_tasks_processing/dispatcher_review.py`; expose them through `fastapi_routes/dispatcher.py`. | Fewest files and smallest initial move. | One larger file combines calculation and display responsibilities. Low risk within the fixed-data assumption. | Before/after saved-run and decision equivalence, then API request tests. |
| Two small modules, recommended | Keep calculation, decisions and JSON persistence in `review_tasks_processing/dispatcher_review.py`; keep deterministic row/detail mapping in `review_tasks_processing/dispatcher_views.py`; use the same thin `fastapi_routes/dispatcher.py`. | The notebook, API and frontend share one calculation, while view changes stay separate. | One extra module with a concrete purpose. Low risk after equivalence checks; no new framework or database. | The same equivalence checks, plus view coverage and API-to-calculation agreement. |

Both approaches modify notebook 06 to call the extracted functions and add `tests/test_dispatcher_review.py` and `tests/test_dispatcher_api.py`. FastAPI dependencies would be added to `pyproject.toml` and `uv.lock` locally only when implementing the API. No dependency is installed by this plan. The proposed two-module approach is a small separation of calculation and presentation, not a broad backend redesign.

### Build order and acceptance checks

1. **Close the small notebook boundary.** Fix the proven unsupported-row selection case. List which row types can actually be corrected, chosen, approved or left unresolved. Keep existing refusals and unresolved records; add no new resolution feature.
2. **Extract and compare.** Move Part 8's calculation, decision entry and save functions, plus deterministic view preparation from Parts 2-4/9. Preserve hard rules, formulas, source identities, stable versions, approved-first reservations and finalization rules. Record before/after outputs on copies of saved runs and the controlled decision cases. Keep notebook 06 and Gradio as callers of the same functions. Existing paid explanation cells stay separate and optional; importing or loading the review must never call them.
3. **Add the basic FastAPI service.** List saved runs, load a review, apply supported decisions, recalculate and finalize approved rows. Validate browser inputs in Python. Generate approval/late-acceptance baselines from the server's current calculation, rather than trusting browser-supplied ETA or final-status fields. Use one decisions file per run, retaining current history files. No browser sessions, graph waits, operational database, new AI call or reallocation endpoint.
4. **Design the frontend while the contract settles.** Make a simple wireframe for the planned landing, operations and dispatcher pages. Build/connect the dispatcher page first: run picker, outcome counts, queues, Suggested allocations, Needs attention, source messages, calculated reasons/options and supported controls. The other pages can remain clearly marked designs/placeholders until their backend journey is implemented. Defer visual tooling and frontend dependencies until that phase.
5. **Check the complete saved-run demo.** Open a run, inspect evidence, correct a supported fact, choose an eligible workshop, accept an explicitly late option, approve, reload saved decisions and finalize. Verify that repeated recalculation adds no duplicate workload, protected work remains valid, invalid actions change no saved decision and source files remain unchanged. Confirm disabled controls send no requests. Run the existing backend suite after module/API changes, with network blocked and explanation/model stand-ins where required.

### Proposed API contract

Names below are proposed routes, not existing endpoints. One small FastAPI app/router file is enough for this increment; request models can live beside those routes. The browser sends supported commands, not arbitrary internal decision records.

| Route | Purpose |
|---|---|
| `GET /runs` | List known saved runs and whether they can be reviewed with the configured snapshot. |
| `GET /runs/{run_id}/review` | Return current saved decisions, outcome counts, queues, detailed rows, evidence, options and supported actions. No model call or write. |
| `POST /runs/{run_id}/decisions` | Validate one supported command on a copy, recalculate, then save the valid decision/draft plan with history and return the refreshed review. |
| `POST /runs/{run_id}/review` | Recalculate from the source and current saved decisions, without adding a decision. |
| `POST /runs/{run_id}/finalize` | Recalculate and save final labels for valid, approved rows without unchecked warnings; retain unresolved rows. This does not commit factory assignments. |

**Proposed save behaviour, to approve with this plan:** unlike Gradio's extra notebook save cells, a successful API Apply saves the accepted command and refreshed draft immediately. This gives one shared file-backed set of decisions that survives a refresh/server restart. Rejected commands are not saved. Avoid per-browser drafts. If explicit Save draft is preferred, settle that before implementing the routes rather than silently mixing both models. One dispatcher and one local server remain the assumption; multi-user editing/conflict machinery is deferred.

A valid command may still leave a task needing clarification or review; that outcome is not itself a rejected command. For example, correcting one missing fact does not clear another blocker, and choosing an allowed late workshop still requires explicit lateness acceptance before it reserves work. Preserve those intermediate review states.

Known run IDs resolve inside the configured runs folder; the API does not accept arbitrary filesystem paths. Raw task/message IDs retain their different meanings. Expected invalid inputs and unsupported actions get clear refusals. API/file/programming failures remain visible, rather than being hidden as successful reviews.

The modular route and offline request-testing approach follows the official [FastAPI router guide](https://fastapi.tiangolo.com/tutorial/bigger-applications/) and [testing guide](https://fastapi.tiangolo.com/tutorial/testing/), checked 20 October 2026.

### Reallocation and the optional second review

Aditya explicitly wants the dispatcher to choose **Review again after reallocation**. Preserve that control in the frontend design and this plan.

- For the first connected demo, **Reallocate** and **Review again after reallocation** are disabled and labelled as planned. They send no request and change no backend state. Do not create a successful stub endpoint.
- A current **Choose workshop** action changes a tentative recommendation. Moving a committed assignment between workshops is the deferred reallocation feature; label the distinction clearly.
- When reallocation is implemented, recommend **Review again after reallocation = Yes** as the initial setting. Yes returns changed results for inspection before finalization. No permits finalization only within explicit dispatcher authorization and existing validation; it never approves missing facts, unchecked warnings, unsafe workshops or unacknowledged lateness.
- Keep today's working **Recalculate preview** action separate from that future choice. Do not add another LangGraph pause/resume loop just to support either control; the graph has had one dispatcher review pause since 20 October 2026.

### Deferred work and evidence

Defer live committed assignments and transfers, duplicate merging, cancellations, uncertain-link/intake recovery, multiple concurrent dispatchers, fresh-chat API processing and new model explanations. Keep those limits visible in the demo. The approved golden key and a separately authorized paid run remain parallel evaluation work; human-assisted results must remain separate from unaided AI scores.

No professor inputs, simulator, saved source run or current allocation policy is changed by this plan. Completing these steps means the saved-run review demo is ready to use through an API/frontend; it does not establish the full product or its measured AI performance as complete.

## One-page decision summary

Help one dispatcher decide whether a workshop can make a batch, can take its workload and is allowed to take it, as described in the [Factory Primer](../reference-documents/Factory_Primer.md#3-the-outside-workshops-track-2). Keep the first implementation small:

| Decision | Agreed planning direction |
|---|---|
| Human clarification | Structured dispatcher facts can make a new task version ready after Python validation, without a model call. Record human authority separately from model verification. |
| Late-only work | Offer **Accept least-late option**, with explicit acknowledgement of the calculated lateness. Preserve the original deadline; never label late work on time. Only for a deadline after the dispatch date. |
| Past deadline | A deadline on or before the dispatch date is review-only (`deadline_passed`): no estimates, least-late option or queue time. Only a revised deadline that the dispatcher confirms returns it to allocation; the original date stays on record. Implemented 18 October. |
| Protected work | Keep its workshop and relative order among protected jobs. Pack protected production/rework after the original backlog, carry their piece counts, then allocate flexible work. Approved estimates may improve; they must not worsen under unchanged inputs. |
| Repeat review | Recalculate from the source run and one current decisions file. One calculation supports preview or finalization; no accumulated queue mutations. |
| First decision increment | One saved fixture, structured decisions, protected recalculation and final JSON. No additional AI calls or summary work, free-text interpretation, Excel, frontend or review-specific LangGraph machinery. Existing read-only explanations stay separate from allocation. |
| Existing policies | Keep automatic allocation on-time-only and retain the historical harness baseline. Human-approved exceptions are separate measured outcomes. |

**Flow:** saved inputs -> apply explicit human resolutions -> Python readiness checks -> reserve protected work -> allocate flexible work -> draft or authorized final JSON. Unresolved work remains visible. Finalize is not approval of an unresolved warning or an unacknowledged late result.

**Implemented notebook interface (Part 8a); proposed for extraction into a module:**

```text
build_dispatcher_plan(source_run, decisions, *, finalize=False) -> dict
```

This function calculates and returns the result; saving happens afterwards. The finalize flag changes authorization/status, not the calculated queues. The UI can later call this same function through an API route.

**Illustrative decisions-file excerpt:** the task and workshop below are from the original-request fixture; this is a proposed format, not a recorded dispatcher decision.

```json
{
  "source_run": "2026-10-14_14-40-08",
  "dispatcher": "dispatcher-name",
  "decisions": {
    "T:L0012:J1": {
      "source_version": 1,
      "decision_version": 1,
      "action": "accept_least_late",
      "late_acknowledgement": {
        "reviewed_revision": "preview-001",
        "workshop_id": "W5",
        "max_tardiness_days": 0.06
      }
    }
  }
}
```

Other entries can supply supported fact corrections, a chosen workshop, a same-batch target, an explicit review resolution, dismissal/cancellation or a protected approval. Each entry is the current decision for that task, not another queue increment. A protected approval retains the reviewed task version, workshop, relative sequence and accepted estimate. Store actual unrounded calculations in saved records; 0.06 above is the readable example.

**Implemented format (19 October), which differs from the excerpt above.**
- An entry has no single `action`. It combines independent fields, so one task can carry a correction, a workshop choice and an approval at once.
- The fields are `source_version`, `decision_version`, `facts`, `resolves`, `workshop`, `accept_late` (`workshop`, `version`, `days`), `approved` (`workshop`, `version`, `eta_days`, `sequence`) and `warnings_checked`.
- `sequence` is [approval group, position in that review's reservation order]. It keeps approved work in the order the dispatcher reviewed it.
- The file records `source_run` and a `revision` number; it has no dispatcher-name field yet.

## What the current code actually supports

[Verification](order_processing_into_tasks/verify_tasks.py) calculates readiness in Python from intent, a known order and remaining blockers. The automatic modules obtain those facts through a model assessment. Notebook 06 Part 8 now adds structured dispatcher corrections; that path has not yet moved into the application modules. Preserve its explicit human provenance and validation when extracting it, rather than allowing the API to set a readiness flag directly.

[plan_tasks](task_allocation_to_workshops/allocation_plan.py) copies starting queues, resets `pieces_so_far` to an empty dictionary, sorts tasks by deadline and calls the on-time-only recommendation path. Therefore **the current function cannot be used completely unchanged** for seeded protected piece counts and per-task late acceptance. In notebook 06, keep one small dispatcher calculation using the existing recommendation, eligibility, metric and ranking helpers. Reuse the formulas; do not copy them or edit application modules before the notebook behavior is demonstrated. Any later shared-loop extension must preserve existing defaults and baseline results.

[recommend](task_allocation_to_workshops/recommend_one_task.py) already accepts `require_on_time=False`, but that alone ranks all eligible workshops under the selected objective. It does not necessarily select the least-late workshop. The acknowledged late action must use the lateness-first ranking explicitly, matching the [harness adapter's fallback](eval_harness/run_harness_evaluation.py), while retaining the request's other restrictions.

## Structured facts from the dispatcher

Treat the dispatcher as an explicit source of facts and decisions, not as another model answer.

1. Apply corrections to a derived copy of the original task. Keep the original messages, model assessment, source version and the human decision. A fact change creates a new version; replaying the same file must not keep incrementing it. Use the entry's decision version to identify changes consistently.
2. Support a known order ID, explicit date, supported preference, requested/excluded workshop, confirmed follow-up target, same-batch relationship, dismissal and cancellation. Read quantity/category from the trusted order table for the MVP's full-order batch. Unknown orders, unsupported splits and unresolved conditions remain blocked.
3. Validate identity, date format, workshop IDs, conflicting instructions, batch duplication and the specific missing facts/questions. Record which review was resolved and how. Do not clear every blocker merely because one field was supplied. Code can validate a structured human instruction; it cannot prove the person understood the original conversation correctly.
4. If complete, create an allocation-ready record with dispatcher provenance, current version and validation results. Do not fabricate model verification or overwrite a model-call record. The automated model path remains unchanged; implementing this second path will require the backend instructions to distinguish human validation from model verification.
5. Recompute routing and warnings from the derived tasks and explicit resolutions. Untouched questions, unresolved cancellation/constraint warnings and ambiguous batch identity still block finalization of affected work. A task can be ready for calculation while its recommendation is provisional.

For a message that failed extraction, reference its review/source-message ID and create a stable dispatcher task ID, for example `dispatcher:L0019:1`. Preserve its original text. One review message does not imply one allocation: the blocker fixture's six intake-review messages include a cancellation, a pause and a follow-up, as well as allocation requests. Resolve their relationships explicitly rather than creating six jobs. A confirmed same-batch relationship leaves one active canonical batch and retains the other records as resolved aliases/evidence; it does not itself resolve conflicting instructions.

**Manual destination versus requester instruction:** store the original requested workshop and the dispatcher's chosen workshop separately. Choosing a different destination is a recorded dispatcher override, not a claim that the requester asked for it. Make that override visible. Exclusions still apply unless explicitly amended; suspended status, capability and batch caps cannot be waived through the dropdown.

Human-assisted results must be reported separately from the model's unaided interpretation scores. A successful manual reconstruction is not evidence that extraction or linking has improved.

## Acknowledged late allocation

Late-only work is a major part of the current example, not a rare exception. The [30-request Luna plan](output/runs/2026-10-14_14-40-08/plan.json) contains **3 recommendations, 15 review outcomes and 12 clarifications**. The 15 reviews comprise 13 allocation decisions plus 2 duplicate-order reviews. Nine allocation reviews have no on-time option. Six concern in-progress orders whose deadlines are on or before the fixed 1 April dispatch date. Since 18 October those six are `deadline_passed` reviews with no calculated options, so acknowledged lateness applies to the other three.

ORD-053's closest option is W5: 9.06 estimated days with 9 days available, or approximately **0.06 days / 1.44 hours late**. The actual stored calculation is unrounded. This is a modelled fractional-day difference, not a factory-clock appointment or a reason to silently round the task on time.

Proposed action:

- Show the least-late eligible workshop under the current queues, with the original deadline, estimated delivery, lateness and relevant restrictions.
- Require an explicit per-task acknowledgement against that reviewed version and calculation. Record the dispatcher, selected workshop, accepted lateness limit and resulting estimate. Generic finalization or an ordinary approval does not grant late permission.
- Recalculate before saving. If the workshop changes, facts change, or lateness becomes worse than the accepted limit, return the affected task for review. A previously accepted number is not blanket permission for any future delay.
- Preserve status/capability/cap/request restrictions and unresolved-review checks. If an authorized manual destination is late, acknowledge that destination's lateness explicitly; do not describe a constrained manual choice as the globally best workshop.
- Leave unacknowledged late-only tasks in review. Keep the original deadline and record lateness honestly. A real deadline correction is a separate human-supplied fact, never a workaround for the on-time gate.
- A deadline on or before the dispatch date is not late-only work: it is a `deadline_passed` review with no least-late option. A revised deadline that the dispatcher confirms is its only path back to allocation.

The application's automatic default remains on-time-only. The harness's mandatory least-late fallback remains unchanged. Compare human-assisted/late-accepted decisions separately from the original model scores and historical allocator results.

## Protect approved work without exact time slots

For unchanged source facts, the protection promise is: **same workshop, same relative order among protected jobs, no worse delivery estimate. Earlier completion is allowed and shown.** It no longer promises an identical start/finish time or the same position relative to unapproved work. If exact appointments later become necessary, that is a different scheduling feature.

At each preview:

1. Start from the original source queues. Identify the unique protected canonical batches from valid approvals, retaining their reviewed per-workshop order, not the order of dictionary keys or approval clicks.
2. Recalculate each protected batch at its approved workshop, using the existing production/rework/transport calculations. Reserve only production plus expected rework after the original backlog. Sum each batch exactly once. Compare its new delivery estimate with the accepted one; invalid or worsened approvals become exceptions rather than silent changes.
3. Seed the piece counts with those same protected batches. Queue days alone are insufficient: workload-share and hybrid calculations also need the pieces already assigned in this plan. Do not invent a piece count for the original backlog; preserve the existing within-plan share definition.
4. Allocate the remaining flexible tasks earliest deadline first using those seeded queues and counts. Manual pins and acknowledged late exceptions are per-task choices; ordinary flexible tasks retain the current automatic rules. Append their production/rework once and update piece counts once.
5. Combine protected and flexible decisions into one result. Preserve the original queues separately from the queues after protected work and the final projected queues, so the record explains the calculation.

Why the promise holds: with the same workshop and relative protected order, removing unapproved predecessors cannot increase the work before an approved job. New flexible work is placed behind protected work. Do not resort protected jobs by new deadlines or replay them a second time through the flexible allocator.

This is simpler than preserving gaps, but still trades unrestricted scheduling for stable approvals. A new urgent flexible task may be later or unresolved because approved work has priority. Changed/cancelled protected tasks reopen their own approval; related approvals must be checked, not blindly reused. This notebook rule is not a guarantee against real factory progress, closures or changed source data.

## Fixed calculation, two completion modes

Each calculation loads the source run afresh and applies the current decisions file once. Use the fixture's dispatch date and fixed order/workshop data, not today's date; assume those source tables stay unchanged throughout the prototype. Never start from the previous preview's tasks, derived versions, queue totals or piece counts. Preserve source files and input accounting. A cancellation removes the confirmed batch from this calculation; removing a protected approval merely makes that task flexible.

| Mode | Result |
|---|---|
| `finalize=False` | Draft preview showing protected/flexible choices, changes from reviewed estimates, late options, warnings and unresolved cases. |
| `finalize=True` | The same calculated queues, with authorized valid allocations marked final. No automatic approval of provisional recommendations, missing facts, duplicate ambiguity or unacknowledged lateness. Those rows stay unresolved. |

A final result may contain a valid subset and unresolved cases; it must state that distinction. Preserve the source run's processing-completeness value and separately report dispatcher resolutions. Human recovery must not rewrite history to imply the AI processed every message successfully. Partial source runs retain every unread/unverified input as unresolved unless a person explicitly reconstructs or resolves it.

First-increment files: one current `dispatcher-decisions.json` and one calculated `dispatcher-plan.json` in the source run, with saved revisions using the existing plan-history convention. Include source run, dispatch date, creation time, decision/plan revision, draft/final status, human provenance, protected work, calculated metrics, queues, piece counts, warnings and unresolved outcomes. Preserve the original `state.json`, `manifest.json` and allocation `plan.json`. Identical inputs produce identical allocation/queue results; creation timestamps and draft/final labels are metadata.

This paragraph's earlier advice (no dispatcher-specific LangGraph loop, persistent graph waits only if later needed) applied to the notebook increment and was superseded on 20 October 2026 by Aditya's decision recorded in [DISPATCHER_REVIEW_GRAPH_PLAN.md](DISPATCHER_REVIEW_GRAPH_PLAN.md). The graph now pauses after `plan_allocation` with LangGraph's `interrupt()`, keeps the paused review in a SQLite checkpoint and loops until one final approval. With tracing on, the reviews and decisions are part of the `full-pipeline` trace. The processing and allocation nodes are unchanged. A later API can drive the same graph with its thread ID.

## First increment and checks

Start with **the existing original-request Luna fixture**, `2026-10-14_14-40-08`, because it contains recommendations, clarifications, duplicate batches and blocked manual destinations. Re-planned with the 18 October rule, its nine late-only outcomes became three late-only reviews and six `deadline_passed` reviews. Recompute current warnings when loading old states; their saved plans predate the warning feature. Keep fixtures independent: the same task ID in two runs can refer to different work.

Build only structured decisions, protected recalculation and JSON in notebook 06. Use existing reasons and a plain table for review. No paid run is authorized or needed for this increment. Afterwards add the blocker fixture, `2026-10-15_21-19-26`, to demonstrate human recovery of formerly held/unverified tasks and raw intake reviews. That demonstrates the human path; only a separately approved fresh model run could measure current automated interpretation.

**Status (19 October):** notebook 06 Part 8 implements this increment on that fixture.
- `experimentation_notebooks/testing/check_notebook_06.py` covers checks 1-4 and 6, and the repeat and release parts of check 5. It uses nine cases, a fake model and copies of the run folders.
- Not covered yet: duplicate aliases, cancellations, link reviews and the blocker fixture.

Keep a small set of meaningful offline checks:

1. A structured correction creates one stable new version; unknown facts or an unresolved blocker still prevent readiness. Human validation is labelled correctly.
2. Ordinary on-time allocation matches the existing rules. A manual lower-ranked eligible choice is allowed; a suspended/incompatible/capped choice is rejected and its requester/dispatcher fields remain distinct.
3. Explicit late acceptance retains the original deadline and calculated lateness. Without acknowledgement, or after a worse calculation, it stays in review.
4. Protected workshops/order remain unchanged and their estimates do not worsen. Seeded piece counts are included in workload-share/hybrid calculations.
5. Repeating identical decisions gives identical queues/counts; duplicate aliases and recovered messages do not create another batch. Cancelling or releasing one task does not silently move other protected work.
6. Finalize changes authorization/status without changing the numeric plan. Provisional warnings remain unresolved until explicitly resolved; final JSON retains every input outcome.

Pure recalculation makes these checks small; it does not remove the need to prove them. Use controlled fixture variants only when labelled as such. Do not call a simulated dispatcher decision a historical team approval. Source CSVs, workshop capacity and the course simulator remain unchanged.

## Later increments and scope boundaries

- Add the two frontend views, **Suggested allocations** and **Needs attention**, after the notebook contract works. Use a detail panel for original evidence, calculations and rejected alternatives. Notebook 06 Part 9 (19 October) prototypes both views in Gradio with Part 8's decisions only, and its decision table is the first data contract. The React page, its detail panel and the unsupported resolutions remain.
- Add optional AI summaries and free-text amendment parsing later, only if templates/forms are insufficient. Evaluate faithfulness and task targeting before paid experiments. These calls may need new cache entries; measure human review time, AI time and calculation time separately.
- Keep Excel in the product plan, deferred from the first increment: one workbook with Allocations, Workshops and Needs attention, generated from the authoritative JSON. Add an export dependency only when implementing it with project-local uv management. Projected workload changes; capacity, capability, rates and source CSVs do not.
- Keep one workshop per full-order batch. Stage-by-stage scheduling, unsupported splits, automatic workshop notification, started-work transfers, live status/calendar policy and transactional multi-run assignments remain future work. Match the [project plan](../docs/project-plan.md) and the [broader operational design](../docs/system-design.md#6-planned-dispatcher-review-and-reallocation), keeping those later features separate from this file-based review calculation.

The [blocker state](output/runs/2026-10-15_21-19-26/state.json) and [manifest](output/runs/2026-10-15_21-19-26/manifest.json), [prompt/model records](docs/evaluation/PROMPT_TESTING_RESULTS.md), and [engineering log](../docs/engineering-log.md) retain the evidence and limits. This plan changes no runtime behavior, model score or recorded harness result.
