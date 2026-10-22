# Dispatcher completion plan

Decided by Aditya on 22 October 2026; written and implemented by Claude Code. This file lists the steps in order and is updated as each one is finished. The [final workflow decision](system-design.md#final-workflow-decision-22-october-2026) still governs everything not changed here.

## Goal

Every allocation request should end up placed, either by the dispatcher or by Python, without another model call:

1. The dispatcher corrects missing information.
2. Python shows workshop suggestions.
3. A workshop the dispatcher chooses is final: Python keeps it fixed, even when it is late or breaks a rule.
4. **Approve all** calculates once, saves immediately and explains what changed.
5. **Review again** is optional, on the saved result.

When the dispatcher does not choose a workshop, Python needs three facts to place the request itself: the order ID, the quantity and the deadline. The category comes from the order record. An "expensive item" option ranks workshops by lowest defect rate.

## What already works (no change)

- A workshop the dispatcher chooses is always used, with any lateness or broken rule written in the reason (`flexible_decision` in `backend/dispatcher_review/dispatcher_plan.py`).
- **Approve all** sends every choice at once; Python plans once, saves and returns what changed (`POST /reviews/{thread_id}/finalize`, `ChangesTable` in the frontend).
- Rows Python could already plan show a workshop comparison.
- The preference "quality" ranks by lowest defect rate. It only needs a clearer label.

## Steps

Each step is built and checked on its own before the next starts. A suspected defect is proven with a test before it is fixed.

### Step 1. Complete a request

**Problem to prove first:** the form can correct the order ID and deadline, but the frontend never says which open questions the correction answers (`resolves` in `decisionsFrom`, `frontend/lib/choices.ts`). Python only treats a request as ready when its open questions are cleared, so a corrected row most likely stays "needs clarification". Check on run `2026-10-14_14-40-08`, task `T:L0010:J1`, which has no order ID.

**Change:**
- New decision `complete`: "this request is complete, plan it with these facts".
  - It needs an order ID, typed or already on the task; otherwise it is refused.
  - Python sets the intent to allocation and treats every open question and unsupported condition of the request as answered.
  - What processing recorded stays on record beside the dispatcher's facts.
  - A blank deadline means the order's recorded due date.
- In the form, a checkbox "This request is complete: plan it with these facts".
- The preference "quality" is labelled "quality (expensive or delicate item)".

**Files:** `backend/dispatcher_review/dispatcher_decisions.py`, `backend/tests/test_dispatcher_review.py`, `frontend/lib/choices.ts`, `frontend/lib/types.ts`, `frontend/components/ChoiceForm.tsx`, `frontend/tests/review.spec.ts`.

**Checks:** a backend test shows the corrected row staying in clarification before the change and being planned after it; a request without an order ID is refused; a browser test checks the exact decision sent.

### Step 2. Editable quantity

**Change:**
- `quantity` becomes a correctable fact: a whole number above 0. Blank means the quantity in `orders.csv`.
- Python uses the dispatcher's quantity everywhere it uses the batch size: delivery estimates, batch caps and queue reservations. The recorded quantity stays on record.
- The form gets a Quantity field.
- For the dispatcher only, this replaces the decision of 18 October 2026 that "a quantity is never typed in" and the rule of 19 October 2026 that the CSV quantity is never replaced (`backend/AGENTS.md`). Processing and the model still never replace it.

**Files:** `backend/dispatcher_review/dispatcher_plan.py`, `backend/task_allocation_to_workshops/recommend_one_task.py`, their tests, `frontend/components/ChoiceForm.tsx`.

**Checks:** a quantity above W8's 300-piece cap removes W8; the reservation uses the new quantity; a plan without a dispatcher quantity is exactly the same as before (the existing comparison tests stay green).

### Step 3. Two requests naming one order

**Problem to prove first:** when two requests name the same order, both go to review, and a workshop the dispatcher chooses on either is not used. Three of run 2's five golden-set misses were this case.

**Change:** a request that the dispatcher placed (workshop chosen) or completed (step 1) is planned as normal. The other requests for that order stay in review and reserve nothing.

**Files:** `backend/dispatcher_review/dispatcher_plan.py`, `backend/tests/test_dispatcher_review.py`.

**Checks:** a test proving the failure first, then that the placed request is planned and the other is not.

### Step 3b. Add a batch

Added 22 October 2026 at Aditya's suggestion. It covers work that no row covers: a split (one order sent as two batches), a request the model missed, or a message that never became a task.

**Change:**
- New decision `add_batch`: an order ID (required), a quantity and a deadline (empty means the order's own, from `orders.csv`), a preference and an optional workshop.
- Python makes it a row of its own, labelled "Added by the dispatcher", and plans it like any other batch. It skips the duplicate-order check (step 3). If the same order already has a planned batch, the reason says so; nothing is blocked, because the dispatcher decides.
- An **Add a batch** button opens that small form. The batch stays in page memory until Approve all, like every other choice.

**Files:** `backend/dispatcher_review/dispatcher_decisions.py`, `backend/dispatcher_review/dispatcher_plan.py`, `backend/tests/test_dispatcher_review.py`, `frontend/lib/choices.ts`, `frontend/lib/types.ts`, a new form component, `frontend/app/dispatcher/page.tsx`, `frontend/tests/review.spec.ts`.

**Checks:** an added batch is planned and reserves its quantity once; two added batches of one order are both planned; a batch without a valid order is refused; a browser test checks the exact decision sent.

### Step 4. Check workshop options

**Change:**
- New endpoint `POST /reviews/{thread_id}/preview` with `{"decisions": [...]}`. It runs the same calculation as finalize over the whole set of pending choices, and returns the draft and any refusal. It saves nothing, does not resume the review and writes no checkpoint.
- A **Check workshop options** button beside Approve all. The result is labelled "Preview, not saved": the rows that would change and, for the selected row, its workshop comparison.
- Changing any choice marks the preview out of date and hides it.

**Rule change:** unfinished choices can now reach Python, but only when the dispatcher clicks this button, and nothing is saved. There is still one Approve all, no autosave and no calculation on ordinary clicks.

**Why the whole set:** if two orders both choose W1, each estimate must include the other's workload. The existing planner already does this from the original queues; no second scheduler is added.

**Files:** `backend/dispatcher_review/dispatcher_decisions.py`, `backend/fastapi_routes/dispatcher.py`, `backend/tests/test_fastapi_routes.py`, `frontend/lib/api.ts`, `frontend/components/ReviewBar.tsx`, `frontend/app/dispatcher/page.tsx`, `frontend/tests/review.spec.ts`.

**Checks:** the preview equals what finalize would save; the run folder and checkpoint file are unchanged afterwards; in the browser, the button sends one request and a changed choice hides the preview.

### Step 5. Review again

**Change:**
- New endpoints `POST /runs/{run_id}/finalize` and `POST /runs/{run_id}/preview`.
  - They start from the saved choices (`dispatcher-decisions.json`) and add the new ones.
  - Python plans once from the original queues, so nothing is reserved twice.
  - Finalize saves a new version; `plan-history/` keeps the old one. It returns what changed compared with the previous saved plan.
- A **Review again** button on a saved plan opens the same choice form over it.
- A saved added batch (step 3b) can be removed or changed there. Until then, a decision can only name a verified task, so `ADD-1` and the like cannot be named.

**Decision (Aditya, 22 October 2026):** rows approved the first time are not fixed. Python may move any row the dispatcher did not choose a workshop for, and the changes table shows every move. Aditya's reason: "that is exactly why the review exists, and this is an mvp". The alternative, keeping earlier approved rows fixed, was considered and not chosen. Step 4's preview already covers checking before a save; Review again covers changes after it.

**Files:** `backend/dispatcher_review/dispatcher_decisions.py`, `backend/fastapi_routes/runs.py`, `backend/tests/test_fastapi_routes.py`, `frontend/lib/api.ts`, `frontend/app/dispatcher/page.tsx`, `frontend/tests/review.spec.ts`.

**Checks:** a workshop fixed in the first approval stays fixed; the queues equal one fresh calculation with all choices; the old version stays in `plan-history/`; a browser test covers the button and the submission.

**As built:**
- The changes are compared with the saved plan as approval would label the new one, so an unchanged approved row is not listed. A removed added batch is listed with no later row.
- On a row with saved choices, the form offers "Undo my saved choices for this task", or "Remove this added batch"; either sends one `clear`.
- The paused review's disabled **Reallocate** and **Review again after reallocation** buttons are unchanged (`frontend/AGENTS.md`).
- Also changed: `backend/dispatcher_review/dispatcher_decisions.py` (`changed_rows`), `backend/tests/test_dispatcher_review.py`, `frontend/lib/choices.ts`, `frontend/lib/types.ts`, `frontend/components/ChoiceForm.tsx`, `ReviewBar.tsx`, `ChangesTable.tsx`, `TaskTable.tsx` and `frontend/app/globals.css`.

## Not in this plan

- Step 6, turning rows that never became tasks into tasks: replaced by step 3b, where the dispatcher adds the batch directly. Those rows themselves stay as they are.
- A hold or "do not dispatch" action: rejected.
- A request that asks for a split stays unsupported as a request; the dispatcher can add the batches with step 3b.
- Model calls, prompt changes, and alerts when a chat deadline differs from `orders.csv`.
- The "Approved dispatcher plan" title on a plan with rows left: unchanged unless requested.

## Safety

No Git commands, installations, paid model runs or Docker. The supplied CSVs, reference documents, `harness/simulate.py`, notebooks 05 and 06 and the golden key stay unchanged. Tests run offline: `uv run --offline --no-sync python -m unittest discover -s tests -v` from `backend/`, and `npm run typecheck`, `npm run lint`, `npm run build` and `npm test` from `frontend/`.

## Progress

| Step | Status |
|---|---|
| 1. Complete a request | Done 22 October 2026: failure proven, `complete` added, 129 backend and 42 browser tests pass |
| 2. Editable quantity | Done 22 October 2026: `batch_pieces` used by estimates, caps and reservations; 131 backend and 42 browser tests pass |
| 3. Two requests naming one order | Done 22 October 2026: failure proven, placed or completed requests skip the duplicate check; 132 backend tests pass |
| 3b. Add a batch | Done 22 October 2026: `add_batch` plans each added batch as its own row (`ADD-1`, ...), skipping the duplicate check; 136 backend and 43 browser tests pass |
| 4. Check workshop options | Done 22 October 2026: `POST /reviews/{thread_id}/preview` saves nothing and equals what finalize saves; 137 backend and 47 browser tests pass |
| 5. Review again | Done 22 October 2026: `POST /runs/{run_id}/preview` and `/finalize` start from the saved choices, plan once and save a new version; 141 backend and 49 browser tests pass |
