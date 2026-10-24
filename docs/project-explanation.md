# Product and technical overview

Updated: 24 October 2026. SweaterCo Dispatch Copilot turns operations messages into an explainable workshop dispatch table. The [backend guide](../backend/README.md), [frontend guide](../frontend/README.md) and [system design](system-design.md) document the implemented behavior.

## The problem

A factory sends batches to outside workshops when it needs additional capacity. The dispatcher must establish whether each workshop can make the product, can take the batch given its capacity and queue, and is allowed to take it under workshop and request restrictions. Informal messages, missing facts and later corrections make that decision difficult to trace.

The application keeps original messages beside recommendations, calculates the alternatives and records the dispatcher's final choices. Most requests prioritize avoiding lateness and reducing delivery time; explicit cost and quality preferences select the corresponding policies. Production delivery time is separate from software processing latency.

## Current workflow

1. Operations staff send named messages in Chat and capture a fixed conversation snapshot.
2. Language models extract owned messages, identify jobs, connect supported follow-ups and assess current task evidence.
3. Python checks order identity, quantities, dates, restrictions and readiness. Uncertain or unsupported input remains visible.
4. The scheduler calculates workshop eligibility, delivery, cost and tentative shared queues in deadline order.
5. LangGraph preserves the initial dispatcher review in a SQLite checkpoint.
6. The dispatcher stages corrections, completes requests, adds batches and chooses destinations. An explicit optional preview calculates the whole set without saving.
7. **Approve all** submits once. Python keeps manual destinations fixed, replans flexible work, saves the table and reports changes. **Review again** applies further choices to a saved plan as a new version.

The output is a saved decision table. It does not book workshop capacity or transfer work already in production. A final table can contain unresolved rows.

## Why the responsibilities are separate

The model interprets language; Python validates evidence and performs arithmetic; the dispatcher controls destinations. React displays these records and sends structured choices through FastAPI. The same scheduling functions serve the application and historical benchmark adapter.

A correction appends evidence, increments its task version and invalidates previous verification. Message, item, task and order IDs are separate because one message can contain several jobs and several messages can concern one evolving task. A schema-valid answer can still misunderstand meaning, so implementation tests and language evaluation remain distinct.

## Why duplicate counts were a real engineering problem

In the historical investigation of 6 October, 30 source messages appeared 48 times across overlapping intake groups. A later deduplication call returned all 48 and the application accepted them. The demonstrated cause was a missing source-ownership acceptance rule; saved files did not establish which edited prompts produced every answer.

Owned target batches now prevent context-only messages from creating accepted duplicates. Different jobs within one message retain separate item IDs. Order ID alone cannot identify a task: an information question and allocation request may name the same order and remain independent.

This prevents a mechanical duplication mechanism. It does not establish correct semantic merging of every differently worded request. The [development notes](../experiments/development-notes.md) retain the diagnosis and verification boundaries.

## How recommendations are calculated

Automatic selection removes workshops that fail status, category compatibility, batch cap, requested/excluded destinations or deadline feasibility. Production is quantity / daily capacity; expected rework is production × defect rate × 0.5. Delivery adds queue, production, rework and pickup time; only production/rework occupy the temporary queue.

Default/fastest ranks lateness, delivery and cost. Cheapest starts with cost; quality starts with defect rate. The weighted hybrid combines lateness, cost and piece share without a direct quality weight. Delicacy/value inference and alternative weights require defined inputs and evaluation.

When no on-time automatic option exists, the request remains for review. Manual destinations override automatic restrictions and lateness, with the consequences recorded. Python still requires a known order and workshop. Reallocation rebuilds once from original queues rather than repeatedly adding previous reservations.

Unresolved follow-ups produce provisional warnings instead of persistent holds. A provisional recommendation reserves tentative work but cannot be approved until applicable warnings are checked. Candidate relationships remain uncertain; the system does not invent attachments.

## Recorded evidence

| Evidence | Recorded result | Meaning |
|---|---|---|
| Historical scheduler replay | Default: 8.1 mean delivery days and 2/120 late; random: 21.5 days and 41/120 late. | Allocation rules on a seeded simulation. Cost and defects are higher for the default; all six official metrics remain reported. |
| Supplied 30-request development set | Test 7 replay after a Python date fix: 30/30 readiness agreement; Test 9 fresh run: 29/30 readiness agreement. | Different experiments; a saved-answer replay is not a fresh language sample or 30 automatic allocations. |
| Human-reviewed 100-case set | Three fresh automatic runs: 73, 80 and 81 of 85 expected allocations; 14/15 exceptions held in each. A 24 October replay of Test 11's saved answers with the cancellation check: 81 of 85 and 15/15. | Existing broad allocation score; lost preferences can count as allocated. CASE-097 cancellation was unsafe in all three runs; the replay reuses the same model answers, so it is not a fresh run. |
| Key-informed API review | 85/85 expected allocations and 15/15 exceptions after 23 choices in Test 11. | Recovery capability with answer-key access, not autonomous accuracy or a human usability study. Twenty-six source rows remained unresolved. |
| Implementation checks | Latest recorded 24 October baseline, after the cancellation change: 170 backend and 66 browser tests; type checking, lint and build passed. | Checked code/interaction properties; some fixtures are local and browser API replies are simulated. |

See the [evaluation guide](../evaluation/README.md) for datasets, scoring definitions, costs, latency, failure evidence and complete results. The final coverage headline does not require timeliness or every field to match; split-part detail checks currently inspect only the main part. Test 11 separately reported all 85 allocations on time with matching fields.

## Remaining work

- Measure the cancellation check in a fresh run, settle broader cancellation wording (negation, superseded instructions) and reduce unnecessary interpretation/link reviews.
- Consolidate all 30 supplied requests by behavior and evaluate explanation faithfulness separately from decision correctness.
- Version stronger scoring, test deliberately wrong outputs and evaluate unseen conversations after development on known failures.
- Measure human dispatcher correctness, unsafe decisions, completion time and review effort without answer-key access.
- Improve per-run reproducibility and protect unsaved choices across internal navigation.
- Define chat/CSV deadline discrepancy handling; the current checked chat date can override the CSV date without an automatic mismatch alert.

Authentication, clarification replies, voice, multiple channels, live assignment transactions, progress/queue ownership and operational transfers are future extensions. Docker and deployment follow core functionality and evaluation.

## Engineering decisions to defend

- Source ownership prevents repeated extraction while retaining multi-job messages.
- Task versions prevent stale verification after a correction.
- Deterministic calculations expose queue and ranking effects rather than delegating arithmetic to a model.
- Provisional warnings keep uncertainty visible without blocking every nearby request.
- One batch approval avoids hidden per-edit persistence and recalculation.
- Manual destinations remain authoritative while their consequences are recorded.
- Workflow checkpoints preserve review progress; they do not replace future operational transactions.
- Historical simulation, fresh model runs, cached replays and assisted review answer different evaluation questions.

Development used AI assistance for implementation, investigation and documentation. The human dataset review is recorded separately in the [review provenance](../backend/docs/evaluation/extended_dispatch_100_REVIEW.md).
