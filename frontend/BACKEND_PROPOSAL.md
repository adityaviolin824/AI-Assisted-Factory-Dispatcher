# Backend contract proposal

**Status: agreed 21 October 2026 ("Agree all three"), built in the order 3, 2, 1.** Sections 3 and 2 are implemented and tested offline; section 1 (chat bridge) is not built yet, so the Chat page and its tests still use test fixtures through `lib/api.ts`. Every real processing run needs Aditya's permission because it calls paid models. Where the built code differs from this proposal, the section says so under **As built**.

Three changes are proposed. Each says why it is needed, what it does, the alternatives considered and its effect on correctness, latency and evaluation.

## 1. Chat bridge

**Why.** Chat is a core interface ([plan, Operations](FRONTEND_PLAN.md#operations-the-core-chat-interface)). The mock chat (`backend/experimentation_notebooks/mock_frontend/app.py`) already has tested helpers for storing messages and exporting a snapshot, but the browser cannot call them: they run inside Streamlit. Thin FastAPI routes reuse those helpers instead of copying their rules into JavaScript.

| Method and path | Body | Answer | Model call |
|---|---|---|---|
| `GET /chat/messages` | none | Every message in saved order: `{message_id, sender, raw_text, received_at_utc}` | No |
| `POST /chat/messages` | `{submission_id, sender, raw_text}` | The saved message. Repeating a submission ID saves nothing new (`save_message`). An invalid name or empty text answers 422 with the mock's own message, such as "Use a single-line name without a colon." | No |
| `GET /chat/snapshots` | none | Every snapshot, newest first (shape below) | No |
| `POST /chat/snapshots` | none | A new snapshot of the whole conversation (`export_conversation`). An empty chat answers 400 "There are no messages to export yet." | No |
| `GET /chat/snapshots/{snapshot_id}` | none | One snapshot, read again while processing runs | No |
| `POST /chat/snapshots/{snapshot_id}/process` | none | Starts the pipeline on that snapshot's `dispatch_requests.txt` and answers at once with `processing: "running"`. A snapshot already started answers 409. | **Yes, paid** |

A snapshot is `{snapshot_id, exported_at_utc, message_count, text, lines: [{message_id, request_label, processing_message_id}], processing, run_id, thread_id, error}`. `text` is the exported TXT; `lines` is the manifest's mapping from a chat message to its `R01` label and the pipeline's `L0001` ID. `processing` is `not_started`, `running`, `finished` or `failed`; `run_id` and `thread_id` are filled when the paused review exists, and `error` says why processing failed.

**Decisions.**

- **Processing starts and returns at once; the page reads the snapshot every five seconds.** Evidence: the Next.js rewrite cuts a proxied request after 30 seconds by default (`node_modules/next/dist/server/lib/router-utils/proxy-request.js`, line 37), and a run takes minutes. Alternatives: one long request with a raised `experimental.proxyTimeout` (simpler, but a refresh or closed tab loses the result); a job queue (more than one run at a time needs). Proposed: FastAPI's `BackgroundTasks` runs the pipeline and writes the status beside the snapshot, so a refresh shows the same state.
- **Paid processing is switched off unless the server is started with it on**, for example an environment variable such as `ALLOW_PAID_PROCESSING=1`. Otherwise the process route refuses with a clear message. Development and browser tests use fixtures or a recorded replay, so no click in a test or demo can spend money by accident.
- **Dispatcher links back to Chat through the snapshot.** A run's rows quote `L0028`-style IDs; the snapshot whose `run_id` is that run maps `L0028` to the chat message. Runs made from a file (all saved runs so far) have no snapshot, so their rows show quotes but no Chat link.
- **The dispatch date stays the pipeline's fixed 1 April 2026** (as in the mock's notebook handoff). Live dates are separate work.

**Effect.** Correctness: the mock's validation, idempotent send and export format are reused unchanged, and processing reads exactly the captured snapshot. Latency: sending and reading are single SQLite queries; processing time is the pipeline's own. Evaluation: unchanged; the harness and the 30-request evaluation do not use the chat.

## 2. One-batch final approval

**Why.** The dispatcher keeps every choice in the page and submits them once with **Approve all** ([plan section 7](FRONTEND_PLAN.md#7-editing-and-approval-exact-behavior)). The current `POST /reviews/{thread_id}/answer` refuses that: `answer_problem` in `backend/dispatcher_review/dispatcher_decisions.py` says "Approve all takes no decisions" and "Send accept_late alone". Sending the edits as hidden `review_again` requests first would break the agreed rule of no requests before approval.

| Method and path | Body | Answer |
|---|---|---|
| `POST /reviews/{thread_id}/finalize` | `{decisions: [...]}`, the same decision forms as today | Accepted: `{status: "finished", review, changes}`, saved at once. Refused: 409 with every reason, and nothing is saved. |

Steps, all in Python: check the inputs have not changed (`input_signature`); check every decision's form; apply all decisions to a copy; calculate the plan once with `build_dispatcher_plan`, which keeps the dispatcher's chosen workshops fixed and arranges the other work around them; refuse the whole batch if `decision_problems` is not empty; otherwise approve and save the review as today. `changes` lists each row whose outcome, workshop or delivery estimate differs from the review the dispatcher was shown, with both values, as `print_review` already marks them.

**Decisions.**

- **Lateness acceptance carries its limit.** `accept_late` accepts the lateness shown in one review, and other decisions in the same batch can change it. The page sends `max_days` with the lateness it showed; if the recalculated lateness is larger, the batch is refused with that reason. Alternative: keep `accept_late` alone (today's rule), which forces a second request.
- **The existing answer route stays** for the command-line review (`resume_dispatcher_review.py`).

**Effect.** Correctness: one calculation over the full set of choices, no intermediate state, and a refusal changes nothing. Latency: one request and one plan calculation (no model call). Evaluation: the saved `dispatcher-plan.json` keeps its current shape.

**As built (21 October 2026).** A new answer value, `"then": "finalize"`, in `apply_answer` (`backend/dispatcher_review/dispatcher_decisions.py`); the route `POST /reviews/{thread_id}/finalize` sends `{"decisions": body["decisions"], "then": "finalize"}` through the existing answer route. The graph is unchanged: an accepted batch returns `then: "approve_all"`, so `save_review` approves and saves it as before. Three deviations:
- **A refusal is 200 with `refused` set, not 409.** It keeps the API's rule that a refused answer is a normal response (`FASTAPI_BUILD.md`, D5) and gives the page one refusal path for both routes. Nothing is saved, and the review shown stays unchanged.
- **`changes` is a field of the final review, not of the response.** It is then saved inside `dispatcher-plan.json`, so the run folder records what the dispatcher changed. It compares against the review shown before approval, so the "approved" labels of `finalize_review` do not count as changes. Each entry is `{id, order_id, before, after}`, where `before` and `after` hold `outcome`, `workshop`, `delivery_days` and `reason`.
- **No `max_days` is needed for the limit.** `accept_late` already takes the lateness of the review the dispatcher was shown. If the rest of the batch makes that task later, the plan leaves it in review with "... does not cover it", and finalize refuses the batch with that reason instead of saving the task as unresolved.

## 3. Reading a review must not create storage

**Evidence.** `GET /reviews/{thread_id}` created `backend/output/dispatcher-review-checkpoints.sqlite` (20 KB, 21 October 2026, 18:40) when no checkpoint file existed, because `fastapi_routes/dispatcher.py` opens a `SqliteSaver` for every read. The handoff rule is that reading creates nothing.

**Proposal.** Before opening the saver, answer 404 "No paused dispatcher reviews exist yet." when `CHECKPOINT_FILE` does not exist. Alternative: open SQLite read-only by URI, which also works but is harder to read.

**Effect.** Correctness: reads become side-effect free. Latency and evaluation: unchanged.

**As built (21 October 2026).** `require_checkpoint_file()` in `backend/fastapi_routes/dispatcher.py` runs first in every review route and answers the 404 above; a test checks that no file is created.
