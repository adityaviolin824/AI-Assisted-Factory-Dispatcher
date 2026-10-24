# System design

Updated: 24 October 2026. This document describes the implemented application and marks future operational extensions separately. The [backend guide](../backend/README.md) owns script/API details, the [frontend guide](../frontend/README.md) describes the web interface, and the [project plan](project-plan.md) lists remaining work.

## 1. What each part is responsible for

```text
Shared chat -> fixed snapshot -> owned extraction batches -> linked/versioned tasks
    -> evidence verification -> routing -> deterministic workshop plan
    -> dispatcher review -> optional unsaved preview -> Approve all -> saved table
    -> optional Review again -> new saved version
```

Language models interpret requests, follow-ups and current instructions. Python controls identity, checks evidence and trusted records, and calculates dates, readiness, queues, cost, rankings and allocations. React displays the records and sends structured decisions. FastAPI connects these responsibilities without introducing another scheduler.

Capability checks establish whether a workshop can make the batch. Queue/capacity calculations establish whether it can take the work. Status, caps and request restrictions establish whether automatic selection is allowed. Manual destinations are authoritative and record any overrides.

**Design rationale:** bounded language interpretation preserves informal intent; deterministic calculations make selection repeatable and inspectable. A single unconstrained model doing interpretation and arithmetic would make numerical correctness depend on prose compliance. Valid schemas and source checks still do not guarantee correct meaning.

## 2. Identity, evidence and corrections

| Identity | Meaning |
|---|---|
| Message, `L0004` | A numbered nonempty line in one recorded input. |
| Item, `L0004:J2` | One extracted job within that message. |
| Task, `T:L0004:J2` | A request and its accepted follow-ups. |
| Order, `ORD-103` | A row in the trusted order CSV. |
| Run | One processing execution and its saved artifacts. |
| Thread | The persistent LangGraph review associated with an execution. |

One message can contain multiple jobs; multiple messages can update one task; separate tasks can refer to the same order. Order identity alone is not a deduplication key. Position-based message IDs apply to their recorded input, not arbitrary other chats.

### Extract once, retain context

Each intake call owns up to three target messages and receives up to two earlier messages as context. Python checks exact target coverage, nonempty verbatim evidence, repeated message/excerpt combinations and preservation of written order references. Context-only messages cannot create new accepted items. All jobs are retained before a target is marked processed.

The alternative global deduplication stage accepted overlap duplicates in an earlier run: 30 source messages appeared 48 times. Source ownership removes that mechanical failure without merging independent requests that share an order. Semantic duplicates and missed intent remain evaluation questions.

### Link a follow-up without rewriting history

Candidates are found through message references, written order IDs and recently touched tasks. The registry retains four recently touched task IDs and supplies at most six candidates within the payload limit. Empty/oversized/ambiguous candidate sets produce a review; they are not silently trimmed to force a link.

An accepted correction appends original evidence, increments the task version and clears previous verification. Current scheduling fields are stored separately from quotations, with evidence for dates, preferences, requested/excluded workshops, split requests and unsupported conditions. Uncertain candidates remain possible links, never confirmed attachments.

### Verify before allocation

Python supplies exact order lookups. A customer name or incomplete order reference cannot substitute for an identified CSV order. The model proposes current fields and evidence IDs; code checks task/version coverage, evidence membership, dates, workshop references and readiness.

- Delivery wording can set a deadline; dispatch wording such as "send out today" does not. Without a selected chat deadline, the order's CSV date applies unless a written unresolved date causes clarification.
- Explicit dates preserve a written year; yearless dates use the dataset year. A copied phrase such as "due Apr 13" is accepted when its single date matches its evidence.
- Supported relative phrases are today, tomorrow, this/next week and this/next month, with the supported "by" and "end of" forms. Python resolves them from configured `message_date`; weeks end on Friday and months on their last calendar day. Weekend week expressions and unsupported phrases require clarification.
- The supplied scenario uses message and dispatch dates of 1 April 2026. Chat displays those settings through `GET /chat/dates`; they do not automatically become the computer's current date.
- `possible_deadline_words` can add a clarification when a written date/time word remains unresolved. It never selects a deadline. Its punctuation-based clause rule can misread dispatch timing separated by a comma; the recorded CASE-070 failure remains a limitation.
- `stated_piece_counts` compares recognized digit/product wording for the order against CSV quantity and adds a blocker on disagreement. It does not replace the quantity or recognize every possible wording.
- `cancellation_words` adds a blocker when recognized possible cancellation/hold wording concerns a known allocation order. It excludes another named order and destination restrictions such as "do not allocate to W3". It does not cancel the request; negation and superseded instructions can still need human interpretation, and wording before the first order ID counts for every order in the message. This guard was added in the source on 24 October after the recorded golden runs; its tests failed before the change, and a replay of Test 11's saved answers sends CASE-097 to review.
- Processing never estimates quantity. Only an explicit dispatcher correction can replace the CSV batch quantity for planning.

Response IDs and versions are matched before accepting assessments. An unmatchable batch goes to review. Once matched, valid sibling assessments can be accepted independently; an oversized task retains its evidence in review. Remaining blockers prevent automatic readiness.

Expected interpretation/evidence failures become review outcomes. API, file and programming errors remain visible execution failures. There is no automatic continuation after a failed model request.

### Provisional warnings

An unresolved input does not automatically prevent another task from being verified. `possibly_affected_tasks` computes warning targets from explicit references, applicable two-message proximity and other requests for the same order. It changes no processing state.

Allocation saves `review_warnings` and marks affected recommendations provisional in `summary_rows`; raw decision status alone is insufficient for display. Provisional recommendations reserve tentative production/rework. Review records reserve nothing. Unchecked warnings prevent those rows from becoming approved.

**Rationale and limits:** broad stored holds previously blocked unrelated verification and could become stale. Recomputed warnings expose useful previews without inventing attachments. The proximity rule can flag an unrelated neighbor or miss a distant correction; a warning does not enforce an unlinked exclusion or cancellation. Historical saved tasks are not freshly verified by replanning them.

## 3. Recorded runs and allocation input

Each processing run saves `manifest.json`, `state.json` and per-call records under the configured output folder. The manifest records messages and language-stage settings; the plan records dispatch date. The current manifest is not a complete self-contained per-run data/configuration contract, so reproducing a review requires matching input data and process configuration.

The exact stage, model, settings, prompt, payload and response schema identify a reusable saved response. Cache hits are validated again before use. Their original usage/timing metadata is not a new charge. Prompt/input changes and newly reachable tasks can produce paid cache misses.

Completeness checks account for messages, extracted items and task versions. A complete run can still contain reviews or wrong interpretations. Standalone allocation can create an explicitly partial preview from an interrupted saved state; a full-graph execution error stops before allocation rather than automatically emitting a plan.

Plans and dispatcher revisions preserve history. Creation time is separate from dispatch date. Alternative objective plans use separate filenames and do not replace the default plan. Original processing files are not overwritten by dispatcher decisions.

## 4. Deterministic allocation

Automatic selection filters status, category compatibility, batch caps, requested destinations, exclusions and deadline feasibility before ranking. Unsupported splits/constraints, duplicate independent requests for one order and reference-only winning workshops require review.

```text
production_days = pieces / capacity_per_day
expected_rework_days = production_days * defect_rate * 0.5
delivery_days = queue_days + production_days + expected_rework_days + pickup_days
tardiness_days = max(0, delivery_days - days_available)
```

Only production and expected rework increase the temporary queue. Eligible on-time candidates are ranked by the configured objective. Default/fastest ranks lateness, delivery days and cost; cheapest starts with cost; quality starts with defect rate. The hybrid weights scaled lateness 0.5, cost 0.25 and piece share 0.25. It has no direct quality weight.

Tasks are planned earliest deadline first. A deadline on or before dispatch is review-only in the automatic path, with no queue reservation. When every option is late, the application shows a review and informational closest option; the historical harness adapter must return the least-late eligible workshop instead.

A greedy pass is not global optimization. Expected rework and workshop defect rates are estimates, not guarantees. Historical completed orders remain usable in replay; current production status and remaining-stage work are not enforced as live policy.

## 5. HTTP, storage and processing boundaries

FastAPI exposes 15 application routes across chat, saved runs and dispatcher reviews. Next.js forwards same-origin `/api/backend/...` requests to the configured API. There is one conversation and one dispatcher, without authentication or a live assignment ledger.

Chat stores messages in local SQLite and exports immutable snapshots with source mappings. Sending and snapshot capture make no model call. Explicit processing is refused unless `ALLOW_PAID_PROCESSING=1`; a background task processes the snapshot to its first review pause. Duplicate processing and overlapping processing requests are refused. Process interruption is reported as failure rather than indefinitely running.

JSON files store processing/plan records; a separate SQLite checkpoint stores the LangGraph pause. Neither database is an operational factory queue. Input signatures protect reviews against changed order/workshop files or dispatch date.

<a id="6-planned-dispatcher-review-and-reallocation"></a>

## 6. Dispatcher review and reallocation

### Final workflow decision, 22 October 2026

The web interaction is implemented: stage choices locally, optionally request an unsaved preview, submit the complete set once, calculate once, save immediately and inspect the change report. **Review again** optionally opens a saved result for a new version. Reallocation is that replanning, not a separate disabled feature or a second mandatory approval.

| Decision | Behavior |
|---|---|
| `correct` | Apply supported facts and resolve named original blockers. |
| `complete` | Treat the identified request as complete with dispatcher facts, recording overridden processing flags. |
| `add_batch` | Add a batch with known order identity, optional quantity/date/preference/destination and its own `ADD-n` ID. |
| `choose_workshop` | Keep the named destination fixed, recording lateness, broken automatic rules and overridden processing flags. Unknown order/workshop identity is refused. |
| `accept_late` | Accept the displayed option within its task version, workshop and delay bound. |
| `warnings_checked` | Confirm that named unresolved inputs do not affect this request. |
| `cancel` | Replace the request's prior choices with explicit cancellation, exclude it from routing/planning and retain a cancelled row with no reservation. Only `clear` undoes it. Added batches are removed with `clear` instead. |
| `clear` | Remove saved choices, undo cancellation or remove an added batch. |

Python rebuilds from original queues, placing manual destinations first and flexible work around them, each group in deadline order. A completed/manually placed request can bypass automatic duplicate-order review; other requests stay visible. A manual split is represented by quantities and additional batches, not automatic splitting.

`POST /reviews/{thread_id}/preview` runs the complete proposed calculation without saving, checkpointing or resuming. `POST /reviews/{thread_id}/finalize` applies it and saves the final table and changes. Ordinary form changes send no request.

Saved-plan `POST /runs/{run_id}/preview` and `/finalize` start from saved decisions plus new choices. Rebuilding from original queues prevents repeated reservations. Prior manual destinations remain fixed unless changed or cleared; previously approved flexible work may move. Changes compare outcome, destination and delivery estimate and retain before/after reasons, including added or removed rows.

The lower-level `/answer` API also supports explicit per-answer review and empty `approve_all`. These terminal/API modes are distinct from the web **Approve all** batch-finalization contract.

All-or-nothing validation refuses invalid decision sets without saving. A recalculated row can still remain unresolved. Cancelled requests are recorded separately and are neither approved nor unresolved; they no longer participate in duplicate-order blocking. Saved lateness consent is rechecked, but its whole-submission refusal behavior differs from newly submitted consent. The final coverage score, timeliness and field correctness remain separate evaluation measures.

### Cancellation decision, 24 October 2026

**Problem:** CASE-097 ("The customer has cancelled ORD-297. Do not allocate...") was verified as an allocation and recommended in all three golden runs. Approve all would approve it, and the only workaround was a misleading `correct` intent `question`.

**Decision:** two parts. `cancellation_words` in verification turns recognized cancellation/hold wording into a blocker, so the request needs review instead of receiving a recommendation. The dispatcher's `cancel` then records the outcome the dispatcher chooses: a cancelled row with no reservation, undone only with `clear`. Python never cancels a request by itself.

**Alternatives considered:** a verification prompt rule (it changes prompt text, so it needs paid reruns, and it stays probabilistic); automatic cancellation by Python (rejected by the project owner, because the dispatcher decides); keeping the intent workaround (it records a cancellation as a question).

**Assumptions:** cancellation wording in these chats is short and explicit, such as "cancelled", "call off" or "do not allocate". A false positive costs one review, not a wrong allocation. There is still no generic hold action; the dispatcher decides what a flagged request becomes.

**Expected effect:** correctness: a recognized cancellation can no longer become a clean recommendation, and a cancelled request reserves no queue time, so later work can move earlier (CASE-069 moved from W5 to W1 in the replay, on time either way). Latency: one regular-expression check per allocation task and no model call. Evaluation: exception handling can be rechecked for free by replaying saved answers; the historical fresh-run scores are unchanged.

### Storage and workflow choice

The implemented file-based calculation supports a single dispatcher without introducing an operational database. `dispatcher-decisions.json` and `dispatcher-plan.json` retain revisions in `plan-history/`. The original manifest, state and automatic plan stay unchanged. This keeps review deterministic and inspectable while operational transactions remain outside current scope.

### Future live assignment transfers

Transferring work already accepted by a workshop requires a different contract: preserve the existing assignment while evaluating a replacement, recheck current facts, atomically release/reserve only movable work, prevent duplicate operations and preserve history on failure. Started/completed work needs a remaining-work policy. Per-batch progress and externally accepted work need consistent queue ownership.

These operational requirements are future work. They do not describe missing functionality in the implemented dispatch-table reallocation.

<a id="7-planned-application-architecture-and-langgraph"></a>

## 7. Application architecture and LangGraph

The eight-node graph runs `start_run`, `link_items`, `extract_batch`, `verify_tasks`, `save_outputs`, `plan_allocation`, `dispatcher_review` and `save_review`, with extraction/linking and review loops. Nodes delegate to the same Python modules as standalone scripts.

`dispatcher_review` pauses through `interrupt()` and resumes with a stable thread ID. `SqliteSaver` preserves workflow progress with durability `exit`: checkpoints are saved when execution stops, not after every processing step. A finished or unknown thread has no paused review.

Read-only preview and saved-plan Review again use the same deterministic functions outside the graph. The initial finalization resumes the paused graph and saves the review. A graph checkpoint does not commit an operational assignment.

Clarification replies returning to the original conversation and additional persistent waits are not implemented. If added, replies must identify the request/version, invalidate superseded verification and keep transactional operational writes separate from resumable nodes.

Optional LangSmith tracing can transmit chat, state, plans and dispatcher choices even when model answers are cached. Offline tests disable tracing. Local cache reuse does not imply an execution has no external telemetry.

<a id="8-planned-frontend-pages"></a>

## 8. Web interface

| Page | Implemented purpose | Remaining boundary |
|---|---|---|
| Introduction | Explain the product, show a worked example and recorded evaluation figures, and link into the application. | Figures are fixed recorded evidence, not live performance. |
| Chat | Save named messages, show history and scenario dates, capture snapshots, process explicitly and open the resulting review. | One conversation; no source-linked clarification reply loop or voice. |
| Dispatcher | Read runs, inspect source evidence and options, stage decisions, preview, approve, review again and show changes. | No authentication, workshop booking or live production tracking. |

The dark/light visual system is implemented in shared CSS. React preserves source identities and backend-calculated values. Unsupported information queries remain explicit outcomes rather than fabricated answers. Added channels, voice and operational charts must use the same backend rules and recorded facts if implemented later.

## 9. Evidence and limits

The latest recorded suite, on 24 October 2026 after the cancellation change, passed 170 offline backend tests and 66 Playwright tests, with type checking, lint and the frontend build passing. Counts refer to that record, not a new documentation-only run. Some regression checks require local source notebooks or saved outputs absent from a clean public checkout. Browser tests simulate API responses; a chat bridge test also uses the real pipeline with saved model answers.

The [scheduler benchmark](../backend/eval_harness/results/harness_results_2026-10-15.md) reports normal/shock results under the unchanged six official metrics plus separately labelled tardiness measures. The [evaluation guide](../evaluation/README.md) separates those results from conversation interpretation, key-informed dispatcher recovery and explanation quality. Historical cancellation failures prompted a conservative source guard and an explicit dispatcher cancellation. A replay of Test 11's saved answers, with no model calls, held all 15 exceptions with no unsafe allocation; no fresh paid run has measured it. Broader semantic coverage, contextual linking, held-out generalization and measured human effort remain open. DeepEval reference material is not integrated.
