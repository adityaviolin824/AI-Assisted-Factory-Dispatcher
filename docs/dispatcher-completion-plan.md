# Dispatcher review implementation

Implemented 22-23 October 2026. This record describes the completed dispatcher actions and their verification. The current [system design](system-design.md#6-dispatcher-review-and-reallocation) and [backend guide](../backend/README.md#dispatcher-review-modules) define the application contract.

## Workflow

The dispatcher completes the choice set locally, optionally previews its calculated consequences and selects **Approve all** once. Python fixes manually selected destinations, plans flexible work around them, saves immediately and reports changes. **Review again** optionally applies additional choices to a saved table as a new version. A saved table can contain unresolved rows; complete coverage of every source request is not guaranteed.

## Implemented actions

### Complete a request

The `complete` decision applies dispatcher facts, sets the identified request to allocation and records overridden processing flags. It requires a known order, supplied or already attached to the task. A blank deadline uses the order date. This fixes the earlier case where correcting visible facts left the original blockers unresolved.

### Editable quantity

The dispatcher can supply a positive whole-number quantity. Blank uses `orders.csv`. Estimates, caps and reservations use this batch quantity while preserving source facts. Processing and language models still never replace CSV quantity automatically. Explicit quality preference ranks workshops by defect rate; the interface's delicate/expensive label is a human selection, not automatic value inference.

### Duplicate requests and added batches

A completed or manually placed request bypasses automatic duplicate-order review; the other requests remain visible. `add_batch` creates an independent `ADD-n` row with known order identity and optional quantity, deadline, preference and destination. This supports manual split batches and work missed by processing. It does not repair or remove the failed source record.

### Check workshop options

`POST /reviews/{thread_id}/preview` calculates the entire proposed choice set without writing files, resuming the graph or adding a checkpoint. Later edits invalidate the preview. Ordinary form edits do not calculate or save. Whole-set calculation matters because several batches can affect the same queue.

### Approve all and Review again

`POST /reviews/{thread_id}/finalize` applies the complete set with one calculation, saves the result and returns changes. Invalid decision sets are refused without saving. Manual destinations are authoritative, including lateness and rule overrides, and their consequences remain in the record.

`POST /runs/{run_id}/preview` and `/finalize` apply new choices to saved decisions. Planning starts from original queues, preserving manual destinations unless changed or cleared. Previously approved flexible work can move. New revisions retain the prior files in `plan-history/`. A removed added batch has no `after` row in the change report.

Reallocation is this recalculation within approval/re-review; separate disabled Reallocate controls were removed on 24 October 2026.

## Recorded implementation checks

| Increment | Date | Recorded checks after the increment |
|---|---|---|
| Complete a request | 22 October | 129 backend and 42 browser tests passed. |
| Editable quantity | 22 October | 131 backend and 42 browser tests passed. |
| Duplicate request handling | 22 October | 132 backend tests passed. |
| Add a batch | 22 October | 136 backend and 43 browser tests passed. |
| Explicit unsaved preview | 22 October | 137 backend and 47 browser tests passed. |
| Review again | 22 October | 141 backend and 49 browser tests passed. |
| Workshop choices override open processing flags | 23 October | 149 backend tests passed, including four new regressions. |

These counts record successive historical increments, not different current suite totals. The 24 October baseline, after the cancellation change, was 170 backend and 66 browser tests, with type checking, lint and build passing. The latest recorded baseline, on 30 October after local translation, is 176 backend and 72 browser tests. No tests were rerun to edit this record.

## Verification boundaries

Tests establish correction, cap/queue accounting, refusal, preview without writes, stable re-review and saved history under controlled inputs. Test 11 separately exercised the HTTP review with answer-key-informed decisions. This is not a real dispatcher usability measurement.

The current verification source adds a conservative possible-cancellation/hold blocker; it does not itself cancel the request. The backend also implements explicit `cancel`, preserving a cancelled row without reservations and allowing `clear` to undo it. Direct repair of every failed intake/link/verification record, automatic splitting, live workshop assignments and transactional production transfers remain outside these implemented actions. A generic Hold action is not part of the current product. Saved/new lateness consent has different whole-submission refusal behavior, and finalization can leave unresolved rows.
