# Held tasks are never verified, and some restrictions are missed

Status: completed historical investigation. The final plan was agreed with Aditya on 15 October 2026, and steps 1-6 were implemented and documented that day (see Progress). No paid run on the blocker file has measured the change since; Test 7 (19 October) ran the original 30 requests, which have no follow-ups. The interpretation limits in the [backlog](../docs/Pending_Improvements.md) remain open.

- **Problem write-up:** [Held tasks and unresolved follow-ups](../problems_solved/held_tasks_and_unresolved_followups.md).
- **Backlog:** [Pending improvements](../docs/Pending_Improvements.md), issues 1, 4, 5 and 12.

## Problem

Today, an unresolved input *holds* the tasks it might change:
- `hold_reviewed_requests` (`verify_tasks.py`) writes a `related_review` record and clears the task's verification.
- `run_verification` holds tasks before the model sees them.

In run `2026-10-15_21-19-26` this caused the following:
- **Six held tasks were never verified.** One is ORD-108 (R07, "Move it now", due Apr 03). R09 "Yes." held it because the reply could not be linked to a task. Its plan row shows no order.
- **Holds are saved state that can go stale.** Partial plans need a copy of the state and a second hold call. `pipeline_complete` must check `held_task_ids`. Removing a review does not remove its hold.
- **Two kinds of input never hold anything,** because verified tasks are not hold sources:
  - R15 "Fastest workshop excluding QuickStitch" became its own task (no order, excludes W1), so R14 (ORD-024) stays ready without the exclusion.
  - A cancellation verified as its own `unclear` task would not stop the request it names.

## Decision (Aditya, 15 October 2026)

Allocation previews are allowed while follow-up links need review.

1. **No hold for a possible effect.** An unresolved follow-up that *might* affect an original task does not hold that task. The original task is verified and planned using its established instructions.
2. **Reviews stay visible.** The ambiguous input stays in review, with its original text and its candidate task IDs.
3. **Affected tasks are marked provisional.** A recommendation that the input may affect is flagged provisional, and the dispatcher is told: "This follow-up may modify this request. Please confirm whether it applies; the recommendation may need recalculation." A candidate relationship is never presented as a confirmed link.
4. **Enforced rules are unchanged.** An incomplete or invalid request is still not allocatable. Confirmed restrictions and linked corrections are still enforced. Verification failures and missing-information checks are unchanged.
5. **No new machinery.** There is no new model stage, automatic linking, graph branch or reallocation. Reallocation comes later; the plan keeps the evidence it will need.

Details settled in the same discussion:
- **Which tasks are warned:** the hold rule's own targets, from `review_targets`:
  - the order or message IDs the input names;
  - otherwise the tasks of the 2 messages before it;
  - then the other requests for those orders.

  This flags 6 tasks in Test 6. Using every link candidate would flag 10 of 14.
- **Queue time:** a provisional recommendation reserves queue time like any recommendation.
- **Named orders:** a review that names an order (R21, "ORD-095 cancelled") also only warns: R02 gets a provisional recommendation, and its warning names R21's row.
- **Two extra warning sources,** both from verified tasks. Each was replayed on all 14 saved runs:
  - **R15 rule:** an allocation task with no order ID that requests or excludes a workshop warns the tasks of the 2 messages before it. It affects only R14.
  - **Unclear rule:** a task verified as `unclear` that names an order warns the other tasks it names. It changes nothing in the 14 runs.

## The design

`possibly_affected_tasks(state)` (in `verify_tasks.py`) replaces `hold_reviewed_requests`. It returns `{task_id: [IDs of the plan rows that may modify it]}` and changes nothing.

Its sources:

| Source | Targets (`review_targets`) | Row ID |
|---|---|---|
| Intake review | its text and message | `L0021` |
| Link review | its quotes and message | `L0009:J1` |
| Failed task review (`stage == "verify"`, current version) | its evidence, with no window | the task ID |
| Verified allocation task, no order, requested or excluded workshop (R15 rule) | its text and first message | the task ID |
| Verified `unclear` task with an order ID | its text, with no window | the task ID |

After the sources, it applies the same-order spread used today. A task never warns itself.

The function is called only when a plan is made, on the state being planned, so a warning can never go stale.

`summarize_plan` gives each routed task that has a warning:
- a reason ending with "Provisional: L0009:J1 may modify this request. Please confirm whether it applies; the result may need recalculation.";
- if the task is a recommendation, the outcome `provisional_recommendation`.

The decision records, the ranking, routing and queue reservations do not change. `plan["review_warnings"]` keeps the whole map, for the later reallocation work.

## Code edits

| File | Function | Edit |
|---|---|---|
| `order_processing_into_tasks/verify_tasks.py` | `hold_reviewed_requests` becomes `possibly_affected_tasks` | Keep the sources and the spread; add the two verified-task sources. Delete the `related_review` writes and the `held_task_ids` updates. Return the map. |
| same | `record_task_review` | Drop the `stage` and `blocking_review_ids` parameters. The record keeps `"stage": "verify"`, so the related_review records of older saved runs can still be told apart. |
| same | `run_verification` | Remove the leading hold call, so every task is verified. Update the header's "Order of calls". |
| `order_processing_into_tasks/extract_items.py` | `intake_window` | Drop `held_task_ids` from the intake review record. |
| `order_processing_into_tasks/create_and_link_tasks.py` | `record_link_review` | Drop `held_task_ids` and the unused `review_targets` import. |
| `order_processing_into_tasks/processing_run.py` | `pipeline_complete` | Remove the held-task check and its docstring sentence. |
| same | `save_run_outputs` | Remove the hold call. Fix the stale "so no plan is made" print and header line 11. |
| `task_allocation_to_workshops/allocation_plan.py` | `plan_allocation` | Remove `import copy` and the copy-and-hold block. Add `plan["review_warnings"] = possibly_affected_tasks(state)`. Update the header. |
| same | `summarize_plan` | Mark warned routed rows as above. Widen the outcome column. |

These need no change: routing, ranking, `recommend`, the graph, the run scripts, the harness, notebook 05, `data/`, `config.toml`, the prompts and the response formats.

Older saved runs still plan with no special code. Their held tasks are unverified, so they keep their `processing_review` rows.

## Tests

All tests run offline.

New:
- **`test_processing_modules.PossiblyAffectedTasks`**, on a small made-up state:
  - every source above, and the same-order spread;
  - a no-order task without a workshop rule warns nothing;
  - the state is unchanged.
- **`run_verification` verifies a task that a link review may affect.** A fake `ask` records the requested task IDs and raises `ReviewRequired`.
- **Test 6's saved state** (skipped if `output/` lacks it):
  - every decision equals the notebook's;
  - only R14's row changes: it becomes `provisional_recommendation`, naming `T:L0015:J1`.

Updated:
- **Change lists:** the `CHANGED` and `NEW` lists and their dated comments.
- **`assert_same_plan`:** `review_warnings` becomes a declared new field.
- **`SavedRuns`:** skips the Test 6 state, which its own test above covers.
- **`PartialRuns`:** the "review found before the stop" test now expects T:L0014:J1 to be planned and marked provisional (naming T:L0020:J1), instead of held.

## Steps

Validate each step before starting the next.

1. **Failing tests first** (systematic debugging): write the new tests and confirm each fails for its stated reason. The rest of the suite stays green.
2. **Remove the holds and add warnings from reviews:** the code edits without the two verified-task sources. Then update the declared tests and run the full suite.
3. **The two verified-task sources:** the R15 rule and the unclear rule. Then run the full suite.
4. **Evidence beyond the tests**, in scratchpad scripts, without changing `output/`:
   - a replay of the warnings on all 14 saved states;
   - a mutation check: switch each change off in memory and confirm that a test fails;
   - a check that the protected files are unchanged.
5. **Simplify** (code-simplifier): review only the touched functions, without changing behaviour, then run the suite again.
6. **Docs:**
   - `Pending_Improvements.md`;
   - the solution section of `problems_solved/held_tasks_and_unresolved_followups.md`;
   - `backend/AGENTS.md`;
   - `README.md`;
   - `../docs/system-design.md` section 2 (the decision entry);
   - `../docs/engineering-log.md`;
   - the test count in `../docs/project-plan.md`.
7. **Report, then ask before any paid run.**
   - The next real run of the blocker file verifies the 6 tasks held today. That is about 5 new verification calls, under one cent at Test 6's cost.
   - Intake and link answers stay cached.

## Stop and ask Aditya if

- a change would alter prompts, response formats, or intake or link payloads;
- a saved run's decisions change, or a row other than T:L0014:J1 changes;
- a paid run seems needed.

## Progress

| Step | Status | Evidence |
|---|---|---|
| 1. Failing tests first | done | 5 new/changed tests failed for the stated reasons: T:L0002-L0004 never sent to verification; Test 6 changed no row; T:L0014:J1 held in the partial run; `possibly_affected_tasks` missing (2). The other 64 passed. |
| 2. Remove holds; warnings from reviews | done | Only the 2 tests awaiting step 3 failed (after moving 4 changed functions from `MOVED` to `CHANGED`). |
| 3. Two verified-task sources | done | `uv run python -W default -m unittest discover -s tests`: 69 OK, no warnings, none skipped. |
| 4. Replays, mutation check, unchanged files | done | **Replay** (all 14 saved states, plans in temporary folders): the warned tasks are Test 4 36 (107 old holds), Test 5 6 (13) and Test 6 7 (the old 6 holds plus T:L0014:J1). The only provisional row in any run is T:L0014:J1 in Test 6; runs with no holds are unchanged. **Mutation check** (55 tests; control 0 failures): no R15 rule 2 failures; no unclear rule 1; a task may warn itself 3; old `related_review` records counted as failures 1 (after a test was added: before it, 0 failures, yet Test 4 rose to 50 warned tasks and Test 5 to 8); no warnings in the plan 4; verification skipping affected tasks 1. **Unchanged:** `git status` lists only the 7 intended files; notebook 05, `data/`, `config.toml` and the prompts are untouched; `output/runs` still has 14 folders and no newer file. |
| 5. Simplify | done | Touched functions reviewed; one docstring re-wrapped. The `stage == "verify"` filter stays (see step 4), and so does the self-exclusion filter. `review_targets` and `HOLD_WINDOW` keep their names and modules, since moving or renaming them would touch more files than the fix needs. 69 OK, no warnings, none skipped. |
| 6. Docs | done | `Pending_Improvements.md` (header update and status notes on issues 1, 4, 5 and 12); the solution section of `problems_solved/held_tasks_and_unresolved_followups.md` (and its status line); `backend/AGENTS.md` (the allocation rule and the processing-module note); `README.md`; `../docs/system-design.md` (section 2 decision entry, section 3 sentence); `../docs/engineering-log.md` (new top entry); `../docs/project-plan.md` (test count, Application row); `../docs/project-explanation.md` (the hold paragraph). |
| 7. Report; ask about a paid run | report given 15 October 2026 | Waiting for Aditya to approve or decline the paid run. |
