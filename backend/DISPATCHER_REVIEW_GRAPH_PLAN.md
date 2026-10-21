# Dispatcher review graph: implemented design and later interaction change

Updated: 20 October 2026.

**Superseding user decision, 21 October 2026:** the editing/approval interaction below is the implemented historical design, not the target for the new frontend. Follow [PROJECT_HANDOFF.md](../PROJECT_HANDOFF.md): keep the complete choice set local and unsaved; on one **Approve all**, apply it, rearrange flexible work around the dispatcher's fixed choices, save immediately and show what changed and why. No per-click checkpoint/recalculation or mandatory second approval. This needs a batch-finalization change because current `approve_all` refuses edits. No runtime change is made by updating the plan. The existing initial source-run/checkpoint records are preserved; unfinished dispatcher edits must not be written before submission.

**Status:** implemented on 20 October 2026, with the 117 offline tests passing; see the [backend README](README.md#dispatcher-review-modules) and the [engineering log](../docs/engineering-log.md). Decisions made during implementation: a final row's outcome and decision status become `approved` with `final: true`; `accept_late` is sent alone; `max_days` keeps the notebook's form; `durability="exit"`; `plan_objective` is not applied to the review. Later on 20 October Aditya replaced section 2's "Hard rules still apply ... An allowed late choice still needs explicit lateness acceptance": the dispatcher decides, so a chosen workshop is planned first and always used, even when late, past its deadline or against a hard rule, with the override in its reason. This document otherwise stays as the agreed plan.

This supersedes this file's earlier per-task approval and save-draft design, and the API-first proposal in [DISPATCHER_REVIEW_PLAN.md](DISPATCHER_REVIEW_PLAN.md). Keep notebook 06 unchanged as the reference. The intentional approval differences below must be declared and tested.

## 1. Goal and scope

Move notebook 06's demonstrated dispatcher calculations into Python modules, then connect them to the existing pipeline with a durable human-review pause.

The dispatcher must be able to inspect the current plan, choose a workshop, correct supported facts, accept explicitly shown lateness and approve all valid allocations at the end. The Factory Primer's three questions remain the purpose: can a workshop make the batch, can it take it given capacity and queue, and is it allowed to take it?

For this increment:
- One dispatcher and one current draft per review thread.
- SQLite preserves unfinished workflow progress.
- Final approval writes JSON in the existing run folder.
- FastAPI, frontend/Gradio work, notebook edits, operational assignments, reallocation and new exports remain outside scope.
- No paid requests are authorized. The review calculation and resume path make no model call. Test the initial pipeline using saved answers and model stand-ins.

The evaluation key can be reviewed and scored separately. Saved-response equivalence and controlled cases establish whether the code move preserves the supported rules; they do not establish new AI accuracy.

## 2. The final interaction

```text
Processing -> allocation preview -> pause for dispatcher
                                      |
                 choose/correct -> validate and recalculate
                                      |
                         checkpoint the updated draft
                                      |
                           show updated review; pause
                                      |
                           Approve all allocations
                                      |
                      save the displayed final JSON -> END
```

### Editing

- A workshop choice updates the current draft. Later choices for that task replace its earlier choice.
- Python validates the edit and recalculates the draft before acknowledging it as accepted.
- The chosen workshop remains the dispatcher's destination during recalculation. If it cannot meet the rules, retain the choice visibly as unresolved; never silently substitute another workshop.
- Hard rules still apply: status, category, batch caps and request restrictions. Explicit manual destination overrides retain their existing provenance. An allowed late choice still needs explicit lateness acceptance.
- An input/command refusal leaves the last accepted draft unchanged and returns its reason.
- A valid partial correction may leave a task needing clarification. That is a valid intermediate review state, not a reason to discard the correction.
- Accepted changes are preserved in the graph checkpoint before the refreshed review is presented as saved. Local edits not yet submitted/accepted are not promised durable storage.

### One final approval

The only final approval action is **Approve all allocations**.

- It applies to the latest displayed, validated draft, including valid AI suggestions the dispatcher never edited.
- It approves only feasible allocation rows without unchecked warnings or unacknowledged lateness. All other rows remain explicitly unresolved.
- Approval changes authorization/status and saves the result. It must preserve the displayed selected workshops, metrics, planning order, reservations and queue projections.
- It must not consult an earlier review or rerank/repack work into different numbers at this point.
- There is no per-row Approve/Undo approval cycle in this workflow. There is no partly approved workload to protect during editing.
- An approval answer contains no edits. Edits must first produce a refreshed review; combining edits and final approval in one answer is refused without applying either.
- Finalization can contain an approved subset and unresolved rows. Its queues remain the displayed tentative projections, not committed factory queue balances.

### Saving and the single draft

Do not add a separate **Save allocations**, **Save draft** or **save draft and exit** action in this increment.

- The checkpoint holds the current draft while the graph is paused.
- Closing the program leaves that draft available under the same thread ID.
- Accepted edits update that draft; they do not create committed workshop assignments.
- Final approval writes `dispatcher-decisions.json` and `dispatcher-plan.json` with the existing history convention.
- During a paused thread, do not also load/rewrite a competing editable JSON draft. The checkpoint is authoritative; the original `plan.json` is a preserved reference, and final JSON is an output.
- Save the approved result even when there were no manual edits. Also preserve an intentional clearing of all manual decisions; do not restore older decisions because the current dictionary is empty.
- Original CSVs, `manifest.json`, processing `state.json` and the original allocation `plan.json` remain unchanged.

SQLite here stores workflow progress. An operational assignment database and actual workshop queue updates are deferred.

## 3. State and persistence

Use LangGraph's `interrupt()` with a durable `SqliteSaver` and a stable `thread_id`. Tests use `InMemorySaver`, plus a real temporary-file SQLite restart test.

The existing graph state keeps:
- `plan`: the original automatic allocation preview, preserved for comparison.
- `decisions`: current structured human edits.
- `review`: the latest calculated draft displayed to the dispatcher.
- `then`: `review_again` or `approve_all`.
- `review_error`: a refusal message, or `None`.

These last four are additions to the current graph schema. They are ordinary JSON-compatible data.

The review supplied to `interrupt` must already be in checkpointed graph state. Resuming restarts the interrupted node from its beginning; therefore do not rebuild the displayed review from CSVs before reading the answer. Read the checkpointed review and apply the answer to that version.

Use one fixed order/workshop snapshot and dispatch date for each thread. Record a small input signature in the review metadata for the configured order/workshop CSV contents and dispatch date at initialization; compare it on resume. This needs no additional graph-state field. Refuse changed inputs clearly rather than applying approval to newly calculated numbers. Do not introduce a snapshot database or automatic migration. Keep code/schema fixed while a thread is in progress.

Proposed checkpoint file: `OUTPUT_DIR / "dispatcher-review-checkpoints.sqlite"`, inside the ignored output folder. Verify that ignore rule before creating the file during implementation.

Official references, checked 20 October 2026:
- [Interrupts and restarting an interrupted node](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [Persistence and thread IDs](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Official SQLite checkpoint package](https://pypi.org/project/langgraph-checkpoint-sqlite/)

Do not wrap `interrupt()` in a broad exception handler. Keep final output writes in a separate node after approval.

## 4. Modules

Use the proposed `backend/dispatcher_review/` package. Before renaming the old `dispatcher_stuff_to_be_decided/` placeholder, confirm that it is still empty and that the new directory does not already contain work. Preserve any existing contents.

### `dispatcher_review/dispatcher_plan.py`

Reuse notebook Part 8a and the existing allocator for:
- Applying supported corrections to derived task copies, preserving source versions and evidence.
- Routing, eligibility, deadline checks, metrics, ranking, manual choices and accepted lateness.
- Rebuilding tentative queues from the original snapshot, adding production/rework once.
- Warning maps, input accounting and unresolved outcomes.

Use explicit imports, including the helpers previously supplied by earlier notebook cells.

**Intentional differences from notebook 06:**
- The module draft has no per-row approval stage or approved-first scheduling. Ready tasks use the normal deadline order and recorded manual choices.
- Do not carry the notebook's `approved_decision` and protected-approval loop into this new workflow as unused machinery.
- Implement `build_dispatcher_plan(run_dir, decisions)` for draft calculation and a separate `finalize_review(review)` for a copied, labelled result.
- `finalize_review` uses the checkpointed draft. It does not rerun allocation. It sets final/approved labels for valid rows, records final/unresolved IDs consistently and preserves all displayed numerical results.
- Legacy per-row approval entries are not silently imported into a new graph thread. There is no migration requirement in this increment.

This is a targeted workflow change, not permission to change workshop rules, formulas, relative-date handling or ranking objectives.

### `dispatcher_review/dispatcher_decisions.py`

Move/adapt the supported Part 8b helpers with explicit decisions/tasks/review arguments:
- `entry_for`, `correct`, `choose_workshop`, `accept_late`, `warnings_checked`, `clear` and `open_blockers`.
- A small `verified_tasks_by_id(run_dir)` loader.
- `apply_answer(run_dir, decisions, review, answer)`.
- Plain `print_review` output for the terminal.
- Final JSON/history saving, reusing `save_dispatcher_files` where compatible with the new contract.

Do not expose per-task `approve` or `release` commands. New threads start with empty human edits; resumed threads use their checkpointed edits, including intentionally empty edits.

`apply_answer` must:
1. Validate the answer shape, allowed action names, required fields, task IDs and expected value types.
2. Apply commands to a copy.
3. Recalculate and validate the proposed draft for edit answers.
4. Return accepted decisions, updated review, next action and refusal information. Invalid input leaves the original accepted state unchanged.

Check nonnegative integer blocker indexes, supported fact names/values, valid date strings and finite nonnegative lateness limits. Convert expected input mistakes to clear refusals; keep file/API/programming errors visible.

Lateness acceptance refers to the estimate shown in the current review. Do not combine it with edits that would change that estimate in the same answer; show the changed estimate first. Do not silently accept unseen additional lateness.

Only the final save helper writes dispatcher JSON/history files. The checkpointer separately persists draft graph state.

## 5. Answer contract

Keep the terminal input small and explicit. These are proposed JSON examples, not commands executed during planning.

An edit:
```json
{
  "decisions": [
    {
      "decision": "choose_workshop",
      "task_id": "T:L0009:J1",
      "workshop_id": "W1"
    }
  ],
  "then": "review_again"
}
```

Other supported edits: `correct` with `facts`/`resolves`, `accept_late`, `warnings_checked` with `row_ids`, and `clear`. A batch of ordinary edits is all or nothing; it calculates one updated review. Validate acceptance commands against the shown estimates.

Final approval, as a separate answer:
```json
{
  "decisions": [],
  "then": "approve_all"
}
```

Reject unknown actions, `save_draft`, per-task approval commands and any `approve_all` answer containing edits. Return the existing draft with the refusal reason.

The task ID above is illustrative and must be taken from the particular run's displayed review. IDs from another run are not interchangeable.

## 6. Graph and runners

Keep eight nodes: the existing six plus `dispatcher_review` and `save_review`.

```text
... -> save_outputs -> plan_allocation -> dispatcher_review
                                              |
                                  edits/refusal -> dispatcher_review
                                              |
                                      approve_all -> save_review -> END
```

- **`plan_allocation`:** retain its original plan creation and saving. It also initializes empty human decisions and calculates the initial `review`, returning both so they are checkpointed before the interrupt node. Record the fixed input signature. This is a declared change to this node.
- **`dispatcher_review`:** call `interrupt` with the checkpointed review/error, apply a resumed answer and return the changed graph keys. Edit answers calculate a new draft; a valid approval answer authorizes the already displayed draft.
- **`after_review`:** edits/refusals loop back to `dispatcher_review`; valid `approve_all` goes to `save_review`.
- **`save_review`:** label a copy with `finalize_review`, save final JSON/history and return the final `review`. It does not select workshops, calculate new queues or update operational assignments.

`build_graph(checkpointer)` compiles with the supplied saver. `run_graph(messages, label, checkpointer)` starts a new UUID thread and returns `(graph_state, steps, thread_id, paused)`. `resume_graph(thread_id, answer, checkpointer)` uses `Command(resume=answer)` with the same thread.

Read final/paused state with `get_state(config)`. Handle interrupt events separately from node updates; do not count an interrupt payload as an ordinary node result. Empty input still creates no run.

Keep the existing batch-based recursion limit with room for the interrupt step; test the bound rather than treating a step-count comment as proof. Resumes need only the review and loop/save transition, so a small bound such as 10 is sufficient.

Runtime dependency, when implementing: `uv add langgraph-checkpoint-sqlite` from `backend/`. Check current compatibility and the lockfile diff; do not upgrade unrelated dependencies or install globally. No dependency is added by this plan.

Runners:
- Update `run_full_pipeline.py` to open the SQLite saver with its context manager, run to the first pause and print the run folder, paid-call count, current review, thread ID and resume command.
- Add `resume_dispatcher_review.py <thread_id> <answer.json>` to apply an answer. Print the updated saved draft/refusal or final output locations.
- With a thread ID but no answer file, show the checkpointed review without applying a change. With no arguments, show usage.
- Leaving a review paused preserves it; no separate save-draft exit is needed.

When configured on, LangSmith tracing also includes the review and human decisions. Keep tracing off during offline tests. The new review/resume functions must not instantiate an explanation or interpretation model.

## 7. Verification before declaring this implemented

Add `tests/test_dispatcher_review.py` and update `tests/test_pipeline_graph.py` and the notebook-reference test helper as needed. Keep notebook 06 unchanged.

1. **Declared code changes:** compare reusable definitions with notebook 06 by syntax tree. Declare the changed scheduler/approval semantics and explicit-argument/input-validation differences. Do not claim all Part 8a functions moved unchanged.
2. **Baseline equivalence:** with no human edits, the draft's allocation decisions, routing, metrics, planning order and queues match the notebook and current allocator. Use copied runs replanned under current rules, not stale historical plan rows; ignore only expected metadata differences.
3. **Supported decisions:** retain controlled correction, eligibility, version, lateness and warning checks. Notebook tests for protected per-task approvals remain historical reference behaviour, not requirements of the new approval workflow.
4. **Latest choice wins:** choose W1, show/checkpoint it, then approve all. W1 and its displayed metrics remain in the final output.
5. **No silent final recalculation:** finalization changes labels/metadata only. Unchanged AI suggestions can be approved; unresolved/provisional rows remain unresolved. The original draft object stays unchanged.
6. **Input refusal:** malformed shapes/types, missing fields, unknown tasks/actions, negative/out-of-range blocker indexes and mixed edit/approval answers are refused. A valid edit followed by an invalid edit rolls back the whole answer.
7. **Durable draft:** pause with SQLite, close the connection/process context, rebuild the graph with a new connection and resume. The accepted choices and displayed review are preserved, without model calls.
8. **Changed inputs:** changing the fixture CSV/date while paused is refused before applying an answer.
9. **Clearing/no manual edits:** clearing the last edit persists an empty draft and cannot resurrect older choices. Approving a valid unchanged AI plan writes final output even with an empty manual-edits dictionary.
10. **Accounting and preservation:** repeat edits/reviews do not accumulate queues. Human decisions and final artifacts preserve source run/task IDs. Original manifests, state, plans, CSVs, notebooks and simulator remain unchanged.
11. **Failure and empty cases:** empty input creates no run; an error before planning still stops visibly; incomplete processing can produce a partial review with unfinished inputs retained.
12. **Graph accounting:** test nodes/edges, pause detection, per-run/resume limits and equivalent original processing/allocation outputs before the review stage.

Run from `backend/`:
```sh
uv run python -m unittest discover -s tests -v
uv run python experimentation_notebooks/testing/check_notebook_06.py
```

Tests use temporary outputs, saved answers/model stand-ins, a blank API key, disabled tracing and refused network connections. Do not run the normal full-pipeline runner to demonstrate this increment without separately authorized model calls.

## 8. Documentation and deferred work

After implementation tests pass, update:
- `backend/AGENTS.md` and root `AGENTS.md` for actual module scope.
- `backend/README.md` for graph, persistence, answer examples, runners and costs.
- [DISPATCHER_REVIEW_PLAN.md](DISPATCHER_REVIEW_PLAN.md), [system design](../docs/system-design.md) and [project plan](../docs/project-plan.md) to distinguish the new implementation from notebook 06's older per-row approval prototype.
- `FEATURES.md` and the [engineering log](../docs/engineering-log.md), reporting actual results and limitations.
- Existing relevant memory notes only if their real location is identified. Do not invent a memory-file path or rewrite historical results.

The earlier API-first proposal is superseded for this increment. API/frontend design follows the tested graph contract later. The known Gradio row-selection issue stays recorded; there is no notebook/UI fix in this increment.

**Parked requirement: "Review again after reallocation."** Keep that exact user-facing requirement. When reallocation is implemented, the dispatcher must retain the choice of inspecting its changed results before authorized finalization. No reallocation control or endpoint is implemented now.

Operational assignments, live queue commits, transfers, duplicate merging, cancellations, unclear-link/intake recovery, extra AI explanations and multiple dispatchers remain deferred. A finalized JSON plan may retain unresolved rows and must not be presented as completed live factory dispatch.
