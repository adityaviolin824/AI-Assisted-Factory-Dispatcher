# System design

Updated: 20 October 2026. Sections 1-5 describe the current modular backend, including partial previews and provisional warnings. Notebooks 05 and 06 remain unchanged experimental references, with intentional module differences declared in the tests. Section 6 records the implemented dispatcher review (notebook 06 and, since 20 October, the graph's persistent review pause) and the planned reallocation; sections 7-8 preserve the planned application and frontend design. The [backend README](../backend/README.md) owns run commands and implementation details; the [project plan](project-plan.md) owns priorities and remaining work. Historical v3/v4 handoffs and resume are documented in their existing walkthroughs and engineering records, not part of the current module contract.

**Approved interaction change, 21 October 2026; not implemented yet:** Project handoff supersedes the per-edit review workflow below for new frontend work. Keep the dispatcher's complete choices in page memory with no mutation/replanning/persistent draft on clicks. One **Approve all** authorizes applying the set and rearranging flexible work; calculate once, save immediately, then show the final dispatch table and before/after reasons. Keep manual destinations fixed and assume the dispatcher knows why; warnings inform rather than demand another confirmation. Existing run records stay preserved, and unidentified work is not invented. The current API refuses edits combined with approval, so the batch path needs implementation/testing. The MVP is a dispatch-table decision aid, not a live production system. Docker remains at the absolute end.

## 1. What each part is responsible for

```text
Original messages
    -> owned extraction batches
    -> source checks and task registry
    -> follow-up linking and current-version verification
    -> verified current tasks, separate reviews and computed warnings
    -> workshop filters, calculations and ranking
    -> tentative allocation plan
```

The model interprets language. Python controls identity, validates evidence, looks up known orders and calculates dates, queue time, cost, scores and allocations. A model can describe recorded results; it must not invent numerical comparisons or workshop facts.

This separation answers the Factory Primer: capability comes from product compatibility; capacity and queue calculations show whether the workshop can take the work; status, caps and request restrictions determine whether it is allowed.

**Reason:** asking the model to interpret a correction is useful. Asking it to remember every duplicate, calculate a queue and enforce every restriction made correctness depend on following prose instructions. Deterministic checks provide repeatable rejection rules. They do not prove that every interpretation is correct.

## 2. Identity, evidence and corrections

### Four different IDs

| Identity | What it means | Why it is separate |
|---|---|---|
| Message ID, such as `L0004` | One nonempty source line. | The same line can appear again as context. |
| Item ID, such as `L0004:J2` | One extracted job within that message. | A single message can contain two independent requests. |
| Task ID, such as `T:L0004:J2` | One request with its linked follow-ups. | Several messages can describe one changing request. |
| Order ID, such as `ORD-103` | A row in trusted order data. | Two different requests can concern the same order. |

Position-based message IDs are meaningful within the recorded input. They are not a permanent cross-channel or cross-file identity scheme. A changed input must not resume as though it were the same run.

### Extract once, retain context

Each extraction call owns up to three new messages. Up to two earlier messages provide context only. The saved processed-message IDs prevent another accepted extraction of those same targets in the run. All jobs from a message are saved before that message is marked processed.

Before accepting a batch, Python requires exact target coverage, a clean separation between items and non-task messages, real nonempty source quotations, no repeated message/excerpt combination, and preservation of every written order reference in the extracted evidence.

**Reason and alternative:** this removes overlap duplication at its source. A single global model deduplication call was previously allowed to return every duplicate. A simple set of order IDs would also be wrong: it would erase independent requests about the same order. A set of source lines alone would lose a second job in one line.

**Limit:** these rules prevent specific mechanical errors. Two different paraphrases of the same job, or a missed action with no extra order ID, still need semantic evaluation. Do not equate exact coverage or a plausible task count with perfect understanding.

### Link a follow-up without rewriting history

A new request creates a task from its item ID. A follow-up is compared with candidates found through source IDs, written order IDs and recently touched tasks. The registry keeps the four most recently touched task IDs; no more than six candidates are sent for linking. Too many candidates, no usable match or an oversized linking payload require review. Candidates are not silently trimmed to force a decision.

An accepted correction appends its original evidence, increments the task version and clears the previous verification. Verification then considers the current task with its recorded evidence. It must not accept yesterday's verified fields as proof that the corrected request is ready.

Original quotations remain unchanged. Current scheduling fields are stored separately: deadline, requested/excluded workshops, preference, split request and unsupported conditions. Each known workshop mention needs an interpretation; a superseded instruction needs later evidence. This lets a correction replace a requirement while retaining what the dispatcher originally said.

The multi-message example is a useful discussion case. It is an example, not evidence that all possible conversations are handled.

### Verify before allocation

Python supplies exact order lookups. A customer name or request label cannot stand in for a written order ID. Unknown IDs and unsupported dates require clarification; explicit dates without a year use the dataset year, 2026.

The P5 fix accepts a reformatted date when it resolves to the same calendar date written in the selected evidence. A returned date without selected deadline evidence is ignored; existing missing-deadline checks still apply. This handles the observed `Mar 23` / `March 23, 2026` formatting difference without accepting an unsupported date. It does not resolve uncertain deadline changes.

**A copy that keeps its delivery word (19 October 2026, after Test 7).**
- When the model copies "due Apr 13" instead of "Apr 13", Python reads the one written date inside the copy. That date must still equal a date written in the deadline evidence, year included. A copy with two or more dates still asks.
- Reason: in Test 7 this wording blocked three plainly dated requests (R25-R27).
- Alternative rejected: a prompt change, which would make every verification request new and paid, and could still be ignored.
- Effect: Test 7's saved answers replay at 30/30 readiness, against 27/30, with no API call. A scan of all 61 saved verification calls found no other answer read differently.

**Delivery deadlines and relative dates (decided 18 October 2026).**

- Only delivery wording sets a deadline: due, deliver by, back by, must be back by, or the customer's ship date. Dispatch timing such as "send out today" or "go out this week" never changes it.
- When the chat states no deadline, the plan uses the order's `orders.csv` due date. A ready allocation task always has an order in `orders.csv`, and every order has a due date; a task without an order asks for one.
- The model copies relative delivery words exactly; Python turns them into a date counted from `message_date` in `config.toml`. The supplied chats carry times but no dates, so it is 1 April 2026, the fixtures' historical "today". The run's manifest records it.
- Fixed phrase list: today, tomorrow, this week, next week, this month and next month, each also after "by", "end of" or "by the end of". A week ends on Friday: from Wednesday 1 April, this week is 3 April and next week 10 April. A month ends on its last calendar day: this month is 30 April, next month 31 May.
- Everything else asks for a calendar date, including "by Friday", "next Friday", "end of the week", and week words written on a Saturday or Sunday (which Friday is meant is unclear).
- A vague amount such as "usual quantities" is never estimated. The order is identified first; its `orders.csv` quantity applies.

Reason: the model interprets wording and code calculates dates, so every date can be checked and repeated. Alternatives rejected: telling the model today's date in the prompt, which would make the model calculate dates (and the evidence check would still reject a date not written in the message); and an NLP date library, unnecessary for six phrases. Assumptions: the message date is known (a fixed setting here; a live chat would record each message's date) and the Friday week end matches the team's usage. Effect: correctness improves for relative delivery words, which no longer always need a question, and dispatch wording can no longer become a deadline. The verification prompt changed, so the next processing run pays for new verification calls while intake and link answers are reused. Harness scores are unchanged. Interpretation accuracy is unmeasured until a paid run.

**Written-date check when no deadline is selected (decided 19 October 2026).**

- When the model selects no deadline for an allocation task, `possible_deadline_words` in `verify_tasks.py` reads the task's evidence with fixed lists. If it finds a written date ("Apr 2") or a time word ("tomorrow", "Friday", "this week"), Python adds "Confirm which written date is the current deadline."
- A clause with a dispatch phrase (send/go out, dispatch, place) and no delivery word (deliver, due, back, ship, arrive, deadline) only says when to send the work, so its dates are skipped. Time words after "last" refer to the past and are skipped. Clauses end at punctuation and at a spaced dash.
- The check can only add that question. It never sets or removes a deadline.

Reason: the 18 October review proved two faults in the earlier fallback. "Send out ORD-045 on April 2." asked a deadline question although only dispatch timing was written. "Deliver ORD-045 tomorrow." with no selected deadline became ready against the later CSV date, a silent error.

Alternatives rejected:
- trusting the model alone, which leaves that silent error path;
- a second model call, which adds cost and latency and is still unverifiable;
- having Python choose the deadline itself, which would make code interpret language.

Assumptions: the fixed lists cover the supplied chats; slash dates such as "4/2" are not detected.

Effect: a task can only become less ready, never wrongly ready. No prompt changed, so saved answers still replay.

Measured: 73 offline tests pass, and 3 of the new cases fail on the old check. In the fresh 30-request run (Test 7) the check fired on no line.

**Piece-count check (decided 19 October 2026, after Test 8).**

- For an allocation task whose order is in `orders.csv`, `stated_piece_counts` in `verify_tasks.py` finds every piece count written for that order in the task's evidence: a number before a product word or "pieces", with up to two words between ("1300 vests", "1,250 cardigan pieces"). Text after another order ID belongs to that order.
- If any count differs from the CSV's pieces, Python adds "The chat states N pieces for ORD-x, but orders.csv records M; confirm the quantity." The CSV quantity is never replaced.

Reason: in Test 8, "ORD-105, 1300 vests" (R191) was marked ready although the CSV records 200 and the order lookup was in the verification payload. Allocation then recommended W3 with no warning. The prompt already asks for clarification when facts conflict, so this was a model miss that a fixed rule can catch.

Alternatives rejected:
- a prompt change, which makes every verification call new and paid, and could still be ignored;
- using the chat's quantity, which the 18 October decision forbids;
- also comparing product and customer names, where synonyms make a text rule unreliable; the model still checks those.

Assumptions: counts are written as digits; "twelve hundred" is not detected. In a quote naming several orders, a count must follow its order ID ("ORD-281, 120 sweaters"); written before the ID, it can be credited to the wrong order and ask unnecessarily. A capacity remark such as "W8 takes 300 pieces" also asks, which is safe.

Effect: a task can only become less ready, never wrongly ready. No prompt changed, so saved answers still replay.

Measured: 76 offline tests pass. A scan of the three chat files flags no line of the 30 supplied requests, one line of the 100-case set (R142, ORD-294: 1,250 against 250, CASE-094, which the key expects to ask) and 37 lines of the old extended chat, all quantity conflicts in its key. Replaying the saved answers with no API call leaves Test 7's 30 plan rows unchanged; in Test 8 only R191 changes, from a W3 recommendation to a clarification.

Verification normally handles at most three tasks per call, within a 24,000-character serialized JSON limit. Larger batches shrink; a single task that cannot fit goes to review with its full evidence. First match the response's task IDs, versions and coverage. An unmatchable or unreadable response sends the requested batch to review. Otherwise check each assessment independently, accepting valid siblings while rejected assessments go to review and later batches continue.

Missing facts, unhandled conditions and remaining clarification questions block readiness. Information questions remain reference records and are excluded from allocation. These records are retained; the notebook does not implement a conversational answer service.

**Trade-off:** several bounded calls are easier to inspect and retry manually than a global semantic pass, but can add call overhead. The limits are current settings, not proof of scalability. Measure accuracy, call count, payload growth and latency before changing them.

### Interpretation failures become review outcomes

Expected model-format, evidence and input-limit failures raise `ReviewRequired`, which the stage catches and records. Intake reviews retain each original message; link reviews retain the unattached follow-up and candidate IDs; task reviews retain the current version, evidence, reason and response trace where available. Missing essential facts remain clarification blockers. API, file and programming errors stop execution visibly; automatic retries and continuation after API failures are not implemented.

**Decision: allocation previews with provisional warnings (15 October 2026, Aditya).** Uncertainty about a separate input does not prevent normal verification of an original task. Ready, feasible tasks are planned from their established instructions, and the uncertain input remains reviewable. This keeps the dispatcher's capability, capacity/queue and permission comparison available without inventing a link or committing an assignment.

`possibly_affected_tasks(state)` computes a warning map without changing state. Its sources are intake reviews, unresolved links, current failed verifications, verified allocation instructions with no order but a requested/excluded workshop, and verified unclear tasks naming an order. Targets come from explicit message/order references; where applicable, an unnamed source uses the tasks of the two preceding messages. Warnings spread to other requests for an affected order. A task never warns itself, and old `related_review` holds are not treated as new verification failures.

Allocation saves that map as `review_warnings`. A warned recommendation becomes `provisional_recommendation` in `summary_rows`, with a request to confirm whether the input applies. The underlying `decisions` statuses remain unchanged, so a consumer must read the warnings and summary too. Provisional recommendations reserve production and expected rework within the plan's temporary queues. Review records reserve nothing.

**Alternatives and reason:** broad holds stopped unrelated work; keeping verified tasks held still withheld useful previews. Warning every link candidate was too broad in the recorded cases. Automatically attaching uncertain replies would invent relationships. The chosen warning rule reuses the existing target lookup and adds no model stage or graph branch. The [problem and solution record](../backend/problems_solved/held_tasks_and_unresolved_followups.md) preserves the exact examples, alternative proposals, historical hold decisions and offline verification.

**Assumptions and limits:** the dispatcher must see unresolved reviews before actual dispatch approval. A warning does not enforce an exclusion or cancellation that was never linked to the original task. The two-message window can flag an unrelated neighbour or miss a distant correction. Genuine verification failures, missing facts and confirmed linked restrictions still block or constrain the original request. Human resolution and reallocation remain future work.

**Measured effect:** 69 offline tests passed. Replaying all 14 saved states preserved allocation decisions and tentative queues; only R14's summary row in the two Test 6 copies became provisional, pointing to R15. Older saved tasks were not re-verified. New processing runs can reach previously skipped verification requests, incur new paid calls and change subsequent queue-dependent decisions. This is a verified workflow change, not a fresh model-accuracy result.

## 3. Recorded runs and allocation input

Each module run creates `backend/output/runs/<start time>/` with `manifest.json`, `state.json` and `calls/`. The manifest records the input messages, prompts, models, reasoning efforts and processing settings. Successful structured responses are cached under `output/response-cache/`, keyed by the exact stage/model/settings/prompt/payload/schema request. Reused answers are validated again, and their new call records identify cache reuse.

These modules do not write v3/v4 handoff schemas, code/data fingerprints, a latest-run pointer, a separate summary file or a resume contract. The graph passes the current run's processing state directly to allocation; standalone allocation requires an explicitly named saved run folder. Each processing run starts fresh. File checkpoints preserve accepted progress for inspection, and saved answers can avoid repeated calls; neither is persistent graph resume.

`pipeline_complete` checks that every message has an extraction outcome, every item belongs to a task or link review, and every current task has accepted verification or a current review. A complete run may contain unresolved reviews and incorrect interpretations; completeness means accounting, not accuracy or permission to commit.

Standalone allocation can preview an incomplete checkpoint. It stores `processing_complete: false`, prints warnings and lists unfinished messages/items/tasks as `not_processed`. The normal full graph reaches allocation after saving, including a normally finished incomplete run; an execution exception stops the graph before that node. No automatic plan is promised after an API failure.

Allocation writes the current plan and a timestamped history copy from the same in-memory object. Explicit-objective plans preserve the default filename. `created_at` and `dispatch_date` have separate meanings. The two file writes are not a transaction. The allocator does not change processing files or source CSVs. Warning relationships are recomputed from the state each time a plan is made and stored in that plan, so no saved hold needs a release step.

**Reason and assumptions:** explicitly naming or passing the run prevents accidental fallback to older results without reintroducing disk handoff validation. CSVs/settings are assumed fixed during a run and comparison. Plans preserve workshop profiles and decision snapshots, but do not claim code/data identity enforcement. Transactional assignments, queue versions and persistent human waits belong to the future workflow in section 6.

## 4. Workshop eligibility and calculated comparisons

The current modules preserve the earlier allocation rules and use a fixed dispatch snapshot of 1 April 2026. Order dates and workshop profiles come from the supplied data. It records order status and current production stage; a COMPLETE order receives a historical-experiment warning but is not blocked. This does not establish a live dispatch status policy or model remaining work at each stage. The batch is the full CSV order quantity.

### Hard rules come first

A candidate must pass active status, category compatibility, batch cap, explicit requested destination and exclusions. The normal plan also requires estimated on-time delivery. A request for an ineligible workshop requires review; the plan does not silently reserve a different workshop.

Splits and unsupported conditions require review. Independent allocation tasks for the same order remain distinct but need batch clarification before allocation; the system cannot assume they authorise the same or different quantities. A separate information question about that order does not create another allocation.

V4 also checks the winning workshop's recorded role. If it is mentioned only as a `reference`, rather than an explicit destination or exclusion, and is not the requested workshop, B17 sends the task to review and reserves nothing. This was added after processing misread R12's instruction against QuickStitch. It is a safeguard for that recorded ambiguity, not proof that the model interpreted every exclusion correctly. A standing instruction is not propagated to other tasks; its scope and expiry remain open decisions.

**Past deadline (decided 18 October 2026).** A deadline on or before the dispatch date is checked before the hard rules. Every workshop has a pickup lead time of at least one day, so no estimate can meet it. The decision gets status `deadline_passed`, with no estimates, no least-late option and no queue time. Only a revised deadline that the dispatcher confirms can return it to allocation, and the original date stays on record. Since 20 October, in the dispatcher review, the dispatcher's own workshop choice also allocates it, late (section 6). Alternative rejected: naming the least-late workshop, as for a future deadline, which invited accepting lateness on work already overdue. The harness replay is unaffected: it sends each batch on its own order date, at least 14 days before it is due. In the 30-request run, six orders (ORD-029, ORD-114, ORD-120, ORD-107, ORD-055 and ORD-002) move from late-only reviews to `deadline_passed`.

When every allowed candidate is late for a later deadline, the review names the least-late option and its calculated delay. When a requested destination fails a rule or deadline, `option_without_request` shows the best on-time alternative with the destination restriction removed and exclusions retained. These are information for review: neither substitutes a workshop nor reserves capacity. The summary table may show such an option in its workshop column, so its outcome and reason must be read together.

### Calculations

For quantity `pieces` and a candidate workshop:

```text
production_days = pieces / daily_capacity
expected_rework_days = production_days * defect_rate * 0.5
queue_days = max(0, recorded_queue_days)
eta_days = queue_days + production_days + expected_rework_days + transport_days
days_available = due_date - dispatch_date
tardiness_days = max(0, eta_days - days_available)
cost = pieces * cost_per_piece
piece_share = (previous_planned_pieces_at_workshop + pieces)
              / (all_previous_planned_pieces + pieces)
```

Cost is rounded to two decimal places. Time and share comparisons use their calculated precision; printed rounding does not decide ties. Piece share concerns the pieces assigned in this plan, not a reconstruction of all factory history from queue days.

Expected rework models the supplied half-batch rework assumption. It does not predict which particular batch will be defective. Estimates use elapsed days; the factory's working-day calendar is not implemented here.

### Ranking rules currently implemented

For the first five policies below, compare the first value, then the second and third when earlier values tie. Smaller values win.

| Policy | Comparison order |
|---|---|
| `minimize_tardiness` | Tardiness, estimated delivery time, cost. |
| `minimize_cost` | Cost, estimated delivery time, defect rate. |
| `minimize_defects` | Defect rate, estimated delivery time, cost. |
| `minimize_concentration` | Piece share, estimated delivery time, defect rate. |
| `minimize_robustness` | Piece share, tardiness, defect rate. |
| `hybrid` | `0.5 * scaled_tardiness + 0.25 * scaled_cost + 0.25 * scaled_piece_share`. |

Hybrid values are scaled from the minimum to maximum within the current candidate set. A field with equal values contributes zero. Its score is rounded to 12 decimal places. Exact remaining ties retain workshop input order. Candidate-relative scaling means the scores are not absolute quality measures that can be compared across unrelated requests.

An absent preference or a fastest preference uses `minimize_tardiness`; cheapest uses `minimize_cost`; quality uses `minimize_defects`. In v4, `PLAN_OBJECTIVE = None` preserves each task's preference; an explicit plan objective applies that policy to every task for experiments. Aliases resolve once, and an unknown objective stops planning. The name `minimize_robustness` is retained from the code; the comparison itself is a share/lateness/defect rule, not proof of resilience under disruption.

The normal plan filters out late candidates before ranking. Their remaining tardiness values are therefore zero: default ranking compares estimated delivery time and then cost. The lower-level recommendation function can explore late alternatives when explicitly configured, but that is not the normal plan's behavior.

### How quality fits the business priority

Avoiding lateness is normally first priority. Delicate or expensive work may give much greater priority to avoiding defects. V4 retains the explicit quality preference, which compares defect rate first among the allowed, on-time candidates. Defects also influence expected rework and therefore delivery time under other policies.

The current hybrid has **no direct defect-rate weight**. There is no separate implemented rule that identifies expensive or delicate work. Workshop price per piece is a processing cost, not proof of the order's value or cost of failure.

The next policy experiment should compare the existing quality-first rule with any proposed weighted quality trade-off, using explicit task information. New weights and exception rules remain undecided. Hard eligibility should remain common to both alternatives. If the desired quality/deadline combination has no feasible workshop, ask for a decision rather than quietly changing the request.

## 5. Tentative plans and queues

The notebook copies the starting queues and visits accepted tasks in source order. Only a feasible recommendation adds production and expected rework to the selected workshop's tentative queue. Transport is outside its production occupancy. Review items reserve nothing. A question with unresolved doubts or missing details routes to clarification; a question without them remains an unanswered reference record. Non-task messages and intake/link/task reviews are retained separately for message accounting. Processing reviews appear in the summary and inspection output without entering `plan_tasks` or workshop ranking.

Later requests see the earlier tentative reservations. Running the plan again begins from the original snapshot. Daily capacity remains a production rate; it is not decremented by assigning a batch.

V4 saves numeric reasons, candidate metrics, ranking keys, rejection reasons, order/queue snapshots and workshop profiles once per plan. It copies non-task messages from the checked processing run so the summary accounts for every input line. The saved plan records its definition-cell code hash, handoff state hash and data hashes. This fingerprints saved definition cells, not unsaved notebook edits or the run cell. The default and explicitly selected objective plans use separate filenames. These records make evaluation reproducible; they are not committed assignments or a transactional database.

**Reason:** this provides a consistent preview without claiming a real workshop assignment has been committed. It also prevents a rejected or unconfirmed choice from taking capacity away from later requests. Source order can affect outcomes, so evaluation must keep task order consistent or deliberately test another ordering policy.

## 6. Planned dispatcher review and reallocation

This section preserves the useful decisions from the older review design. **The database, UI and transactional reallocation are not implemented. Notebook 06 Part 8 prototypes file-based dispatcher decisions and per-row approvals, and Part 9 tries them on a Gradio screen (19 October 2026). Since 20 October 2026 the pipeline graph pauses for the dispatcher's review and saves it after one final approval (below).** The planned MVP gives the dispatcher a choice between finalization within explicit authorization and another review preview; automatic live commitment remains outside the current implementation.

**Deferred deadline discrepancy:** A chat request can name a different date from `orders.csv`. The preferred future policy is to keep the trusted CSV deadline authoritative until an authorized update, show both dates and the original request to the dispatcher, and record the resolution before recalculating delivery feasibility. A mismatch alone does not establish whether the chat or CSV is outdated. Automatic comparison, mismatch alerts and reconciliation are deferred to avoid extra prototype complexity. Current code still accepts a confirmed chat-date override; this is a planned edge-case response, not a code change or an implemented notification.

### Dispatcher MVP proposal, 16 October 2026

The detailed plan now lives in backend/DISPATCHER_REVIEW_PLAN.md, updated 18 October. First prototype one saved fixture, structured human corrections validated in Python, manual choices, explicitly acknowledged least-late allocation, protected workload and final JSON. Pack protected work after the original backlog, retain its workshop and relative protected order, and seed both queue days and piece counts before flexible allocation. Earlier completion is allowed; worsening an approved estimate is not. This supersedes exact time slots with unused gaps. One replayable calculation supports preview or finalization; unresolved warnings remain unresolved. Defer free-text AI, summaries, Excel, frontend and a review-specific LangGraph loop. The two views and JSON-derived workbook remain later increments.

**Implemented 19 October 2026 in notebook 06 Part 8:** typed decisions (corrected order ID or deadline, a chosen eligible workshop, accepted lateness, approval) and `build_dispatcher_plan`.
- Each review reloads the source run, applies the decisions file once and places approved work first, in approval order. The other tasks then run earliest deadline first through the existing `recommend`.
- Review again and Finalize call the same calculation. Finalize only labels rows: a row is final when it is approved and has no unchecked warning.
- No model is called. Only `dispatcher-decisions.json` and `dispatcher-plan.json` are written, with history copies.
- Reason: one replayable calculation cannot reserve the same work twice, and keeping it in the notebook leaves the modules and harness results unchanged.
- Alternative rejected: mutating the previous preview's queues, which can double-count reservations.
- Assumption: the fixture's order and workshop data stay fixed.
- Effect: correct queue accounting across repeated reviews. Duplicates, cancellations and link reviews are not handled yet.
- Checked offline by `backend/experimentation_notebooks/testing/check_notebook_06.py`. The sections below retain the broader live assignment and transactional reallocation design, not prerequisites for this file-based prototype.

**Implemented 19 October 2026 in notebook 06 Part 9:** one Gradio screen for one saved run, showing the queues, Suggested allocations and Needs attention. Each decision calls a Part 8b helper on the notebook's `decisions`, the same ones Parts 8c to 8f use, then recalculates with `build_dispatcher_plan`, so the latest decision counts. It makes no model call; Parts 8d to 8f save the decisions.
- Reason: settle what the dispatcher page shows and which decisions it sends before building the React page and its API. A decision needs Python to recalculate the plan, so a static React mock could not test the loop. Gradio runs in the notebook's kernel and calls Part 8's functions directly, with no API and no module move. Aditya chose Gradio in the notebook and limited it to one screen with Part 8's decisions only.
- Alternatives: a minimal FastAPI script with Swagger UI, which Aditya deferred; the existing Streamlit dependency, which the codebase sweep suggested, but a Streamlit app runs as its own script, so Part 8's notebook functions would first have to move into a module; a React page now, which needs that API first; separate drafts per browser session, the first version, which Aditya replaced later on 19 October because the latest decision should count and one dispatcher works at a time. Those drafts also needed the notebook's `decisions` swapped while a helper ran.
- Assumptions: one dispatcher per run at a time, and source data fixed while the screen is open. Every page shares one set of decisions with the notebook, and saving stays in Parts 8d to 8f. Running Part 9 again stops the earlier screen, so an old page cannot change a new run's decisions. A workshop chosen for an approved task replaces the approval.
- Effect: correctness is Part 8's, since the screen's tables equaled those of the same decisions typed with the helpers. One recalculation took 0.002 s on the 30-request run and 0.007 s on the 181-row run, before Gradio's page update. Evaluation is unchanged: human-assisted results stay separate from model scores. Gradio is a `dev` dependency, so the application's runtime dependencies are unchanged.
- Its decision table, with the fields each decision reads, is the first data contract for the dispatcher console.

**Implemented 20 October 2026: dispatcher review modules and a persistent graph pause** (plan, [backend README](../backend/README.md#dispatcher-review-modules)). Notebook 06 Part 8 moved into `backend/dispatcher_review/`, and the graph gained two nodes after `plan_allocation`: `dispatcher_review`, which pauses with LangGraph's `interrupt()` and applies each answer, and `save_review`, which saves the approved review.
- The dispatcher edits (correct facts, choose a workshop, accept shown lateness, mark warnings checked, clear), sees the recalculated review, and finally approves all. Approval labels the review last shown: each recommendation, dispatcher's choice or accepted lateness without an unchecked warning becomes `approved` and final; other rows stay unresolved. Nothing is planned again at approval. An answer is all or nothing; a refused answer changes nothing and says why.
- Every review plans from the original queues, so reviewing again never reserves the same work twice: first the tasks with a workshop the dispatcher chose, then the other ready tasks around them, each group earliest deadline first.
- The dispatcher decides (Aditya, later on 20 October 2026): a chosen workshop is always used, even when it is late, the deadline has passed or it breaks a hard rule (status, category, batch cap or a request exclusion); the lateness, the original deadline and the broken rule are written in the row's reason. The allocator's own selections still enforce every hard rule. Reason: Aditya set the dispatcher as the final authority, whose choices are allocated exactly as given with the other work planned around them; the code records every override instead of refusing it. Alternative: refusing a forbidden or late choice until it is confirmed, the earlier design, which Aditya replaced.
- The paused review lives in a SQLite checkpoint (`output/dispatcher-review-checkpoints.sqlite`, `langgraph-checkpoint-sqlite`) under the run's thread ID, saved with `durability="exit"`: when the run stops at a pause, at the end or on an error.
- Each review records a signature of `orders.csv`, `workshops.csv` and the dispatch date; an answer to a paused review whose inputs changed is refused.
- Reason: the dispatcher's review becomes part of the pipeline run, and a paused review survives the program ending, so it can be answered later from a terminal now and from an API or frontend later. One final approval of the review the dispatcher saw means the saved workshops and numbers are exactly the ones shown; with no per-row approval there is no partly approved workload to protect while editing. Aditya chose this design on 20 October 2026.
- Alternatives: the API-first proposal (a FastAPI service over the review calculation, with file-backed decisions and no graph waits), which Aditya superseded; notebook 06's per-row approve and release with approved work planned first, kept as the notebook's prototype; `InMemorySaver`, which loses a paused review when the program ends (used only in tests); LangGraph's default durability, which saves a checkpoint after every step, where Aditya chose `"exit"`.
- Assumptions: one dispatcher per thread; the code, the order and workshop data and the dispatch date stay fixed while a review is paused; each request's own preference ranks the review (it does not apply `plan_objective` from `config.toml`, which is unset by default).
- Effect: correctness is checked offline by `backend/tests/test_dispatcher_review.py` (the modules against notebook 06's Part 8 on 13 saved runs and one decision sequence, the controlled decisions and every refusal) and `backend/tests/test_pipeline_graph.py` (the pause, edits, approval, refusals, step limits and a SQLite pause and resume across a closed connection). Resuming makes no model call. Evaluation is unchanged: the harness and model scores do not use the review, and human-assisted results stay separate. A final review is saved JSON, not a committed assignment; reallocation, live queues and the second review after reallocation remain planned.

### Separate allocation from review

One authoritative human dispatcher remains the scope. Every order should offer a request to change workshop. An already allocated order can also need review; these are separate states, not two copies of the batch.

The earlier proposal used fields such as `allocation_status`, `review_required`, `review_reason`, `current_allocation_id` and task revision. These are proposed application fields, not claims about the current parsing schema.

A corrected review item should update the same task and return to allocation only when its current version passes validation. The planned structured dispatcher path uses human facts plus Python checks without a model call; the automated path retains model verification. Keep their provenance separate. Merely viewing a request is not approval. An allocated order with a pending move keeps its current assignment until a replacement commits. A manual selection is always used, even a late or hard-rule-breaking one (decision of 20 October 2026); it preserves the deadline and records the lateness and any broken rule.

### Proposed change-of-workshop sequence

1. Load the current task, active assignment and relevant queue state. Retain the old assignment while preparing the change.
2. Check the requested destination against current facts. Separate work that can still be moved from work already performed. Initially, only unstarted queued work is a candidate for automatic transfer; started or finished work needs an explicit remaining-work/recall/rework policy.
3. Show the calculated alternative and its effect on queues, with the dispatcher’s reason if one was supplied. Do not invent a reason.
4. On confirmation, recheck task, allocation and queue versions. A stale preview must be recalculated before commitment.
5. In one transaction, release only the movable old reservation, preserve other batches' reservations, reserve the replacement work, change the active assignment and append history. A failure must leave the original assignment and reservations intact.

A repeated submission needs a stable operation ID so it cannot allocate twice. Order ID alone is insufficient because an order may have distinct requests or future child batches. Choosing the current workshop again must not create another reservation or a false move. Cancellation and rejection preserve the original assignment.

Record operation, task/order/batch identity, versions, previous/requested/resulting workshops, actor, timestamps, supplied reason, source decision, relevant snapshots, calculated comparison and outcome. Retain pending, committed, rejected, cancelled and superseded outcomes rather than replacing history with one current workshop field. Keep dispatcher waiting time separate from production queue time, and retain total elapsed time across repeated moves.

### Storage and workflow choice

A single project-local SQLite database is the recorded first application direction: derived order/workshop lookup tables plus transactional operational records. Source CSVs stay unchanged, and the simulator keeps its own queues. This avoids a server dependency before there is a demonstrated need. PostgreSQL or a larger data-access layer can be reconsidered if concurrency or deployment requirements justify them.

The notebook's CSV dictionaries are sufficient for current exact lookups; they are not a substitute for transactional persistent assignments. The first dispatcher prototype uses saved files and a replayable calculation, without a new database or graph waits. Since 20 October 2026 the graph's review pause is kept in a SQLite checkpoint file; that file stores workflow progress only, not assignments. A graph checkpoint would not replace the database transaction protecting a live assignment and its reservations.

### Acceptance cases before calling this workflow complete

- Missing identity followed by a correction updates the existing task; remaining blockers still prevent assignment.
- An unrelated information question never creates an actionable allocation.
- An allocated task can appear in review without duplicating its active batch.
- Any workshop the dispatcher chooses is used, with a broken rule or lateness recorded in its reason; other work is planned around it.
- A successful move releases and reserves exactly the movable work, leaving other reservations intact.
- Repeated clicks and choosing the same workshop do not create extra assignments or reservations.
- A stale preview, transaction failure or cancellation preserves the previous committed assignment.
- Repeated moves retain every outcome and the relevant timing/history.
- Started or completed work goes through the agreed remaining-work policy rather than erasing performed work.
- Every explanation matches recorded facts and comparisons.

Reallocation is an application workflow. The official historical harness still receives one workshop choice per batch and remains unchanged.

## 7. Planned application architecture and LangGraph

**Status:** broader future application design carried forward from the overall guideline, sections 3–4, 6 and 12. Notebook 05 already runs the batch pipeline through LangGraph, and since 15 October `backend/app_full_pipeline/pipeline_graph.py` runs the same graph on the modules, ending with a plan of the run just processed. The processing modules also keep a plain run loop with equivalent results. Since 20 October 2026 the graph also pauses for the dispatcher's review and saves it after one final approval, with a SQLite checkpointer (section 6). Persistent clarification waits remain optional later work when justified; `state.json` is a file snapshot, not a LangGraph checkpoint. The workflow below describes that later operational scope.

```text
Operations text / later voice transcript
    -> ingestion with message, channel, sender and timestamp
    -> interpretation and trusted-data lookup
    -> code validation and workflow routing
        -> missing or ambiguous facts: ask, persist and wait
        -> unsupported/information query: record an explicit outcome, no allocation
        -> ready allocation: deterministic workshop checks and preview
    -> stored comparison and dispatcher review
        -> clarification/correction: current-version human/code or model validation and new preview
        -> confirmation under the agreed policy: recheck versions and commit atomically
        -> rejection/cancellation: preserve prior assignment
    -> recorded outcome and evidence-based explanation
```

### Where LangGraph fits

The current batch graph and its dispatcher review pause are implemented. The other waits below are possible later responsibilities.

| Stage | Planned responsibility | Boundary |
|---|---|---|
| Interpret and resolve | Call the existing language stages and exact lookup functions; carry request IDs, evidence and versions. | The model cannot invent order identity or workshop facts. |
| Validate and route | Branch on validated intent, blockers and eligibility results. | Code decides readiness and applies hard rules. |
| Clarify and wait | Persist the unresolved request and route its question to the originating channel/user. Resume the same request after a reply. | A correction increments its version and invalidates earlier verification/preview. |
| Preview and review | Call the deterministic allocator and store its comparison; pause for a dispatcher decision where required by the approval policy. | Showing a suggestion or waiting for approval must not commit operational queue reservations; tentative plan reservations remain separate. |
| Commit or cancel | Invoke the transactional assignment service after current facts and versions are rechecked. | Duplicate submissions, stale previews and failures preserve the last valid assignment. |
| Explain and follow up | Read the stored decision; call a comparison/replanning function if requirements change. | Explanations use recorded numbers. Unavailable history or quoted prices remain unsupported. |

For a persistent wait, use `interrupt()` with a checkpointer and stable `thread_id`; continue using `Command(resume=...)` and the same ID. Resuming restarts the interrupted node, so keep assignment writes in a separate transactional step protected against duplicate operations. The dispatcher review pause follows this: `dispatcher_review` only reads the checkpointed review before `interrupt()`, and `save_review` writes the files. The durable checkpointer is chosen: `SqliteSaver` from `langgraph-checkpoint-sqlite` (20 October 2026), separate from any future operational database. These API details were checked on 10 and 20 October against official [interrupt](https://docs.langchain.com/oss/python/langgraph/interrupts) and [persistence](https://docs.langchain.com/oss/python/langgraph/persistence) documentation.

Graph state should reference the message/channel, task version, evidence, outstanding question, decision record and assignment/queue versions. Operational records remain authoritative for committed workshop work; graph state tracks progress through the workflow. A shared channel is not enough to identify the request being resumed.

### Technology direction and reasons

| Direction | Reason and expected effect | Alternative or unresolved boundary |
|---|---|---|
| Python scheduler and FastAPI backend | Reuse the verified notebook functions and Pydantic records; preserve calculations and eligibility across UI and evaluation. | Rewriting the scheduler in frontend code risks different outcomes. Since 20 October 2026, four endpoints read saved runs and show or answer a paused review by calling the existing graph functions; their decisions are recorded in the FastAPI build record. |
| Next.js/React frontend | Follow the guideline's web direction and separate operations users from the single dispatcher. | No pages or routes are implemented; choose specific UI libraries when building them. |
| Existing LangGraph batch flow with the dispatcher review pause; optional later clarification waits | Keep the working processing graph. Its review pause (20 October 2026) keeps an unanswered review in a SQLite checkpoint. Consider further orchestration only when asynchronous clarification requirements demonstrate a need. | The checkpoint stores workflow progress, not committed assignments. |
| Project-local SQLite operational state | Start with one dispatcher and transactional assignment/history updates without a database server. | Concurrency and deployment may justify another relational store later. No database or schema exists yet. |

This design serves the primer's three checks: the interpreter or explicit human correction preserves the batch and restrictions; code checks capability, capacity/queue feasibility and permission; the dispatcher sees the evidence before a real assignment is recorded. An optional future workflow coordinator would manage waits, not arithmetic. Validate the file-based correction, approval and duplicate-reservation behavior first; add restart and transaction cases when persistent operations are implemented.

## 8. Planned frontend pages

**Status:** product direction, not implemented screens. Notebook 06 Part 9 prototypes the dispatcher console's two review views in Gradio to settle their functions and data contract (section 6); it is not the product frontend. The overall guideline, section 7, supplies the three-page model. Exact visual styling remains to be designed after the core workflow is proven.

| Page | User and purpose | What it should show |
|---|---|---|
| Product / landing page | Evaluators and stakeholders understand the problem and enter the demo. | Factory problem, actual capabilities, simple architecture, measured results and limitations, project identity and demo access. Use real evaluation figures only. |
| Operations channels | Factory users submit text and receive clarification/outcomes in context. | Channel list, message timeline, text composer, processing status, source-linked clarification and recorded outcomes. Add voice input later on this page; show the transcript for confirmation before submission. |
| Dispatcher console | One dispatcher reviews requests and controls assignments across channels. | Unified work list; source evidence and missing facts; candidate comparisons, rejected workshops and warnings; calculated delivery/cost/quality trade-offs; permitted confirmation, rejection and reallocation actions; assignment history; supported decision Q&A. |

### First text journey and later voice

Start with one operations channel and a usable dispatcher console. A user submits a message, sees its processing state and answers a focused clarification when needed. The dispatcher opens the same task, checks the source and calculated candidates, and takes an explicit action under the agreed approval policy. The UI distinguishes recommendations, review, clarification, unanswered questions and committed assignments. An informational closest option must not look like an assignment.

An allocated task can also require review of a proposed move. Review and Allocated should be filters over the same item with separate allocation/review state; displaying it in both must not create another batch. Show the existing assignment while a move is pending, and require a fresh preview when its task or queue version changes.

Later, multiple channels feed the same intake queue and dispatcher console. Preserve message/channel/sender IDs, timestamps and original text; return clarifications to the correct source. Protect shared scheduling state against concurrent submissions. Start with the smallest queue/rate-limit implementation that meets measured needs.

Voice is a later input control on the operations page. Transcription produces text for review and then enters the same interpretation, validation and allocation flow. Transcription errors can change quantities, dates or workshop names, so evaluate transcript fidelity and the resulting dispatch behavior. Voice does not introduce another scheduler or require a fourth page.

The dispatcher assistant may explain a stored choice and its alternatives. A changed deadline or destination requires deterministic recalculation and a new preview; it is not approval to commit. General meeting assistance and answers based on missing factory data remain outside the dispatch workflow. Operational charts, if added later, read recorded backend calculations.

## 9. Evidence and limits

The latest verified module baseline is 123 offline tests (20 October 2026): 23 processing, 25 routing/allocation, 15 harness, 23 graph, 22 dispatcher review, 11 run-report and 4 API. They check declared notebook differences, exact prompts and schemas, routing, calculations, queues, cached graph/two-step equivalence, partial accounting, history, provisional warnings and the dispatcher review pause. The independent review also replayed all 14 saved processing states without changing their files. No fresh model calls were made for the provisional-warning change.

The harness adapter is implemented and its recorded normal/shock results are in the [evaluation report](../backend/eval_harness/results/harness_results_2026-10-15.md). Preserve its six official metrics and keep external tardiness, request interpretation and explanation evaluation separate. Known model failures and development-set limitations remain in the active backlog and [experiment record](../backend/docs/evaluation/PROMPT_TESTING_RESULTS.md).

Controlled checks do not establish unseen semantic accuracy, optimal weights, real production outcomes or transactional live correctness. DeepEval reference code has been added and inspected, but it is not integrated. Use the [evaluation plan](project-plan.md#evaluation-and-evidence) before making broader claims.
