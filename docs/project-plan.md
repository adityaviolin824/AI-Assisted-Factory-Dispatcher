# Project plan

Updated: 28 October 2026 for the future implementation roadmap; recorded verification dates remain unchanged. This document separates implemented capabilities, recorded verification and remaining work for SweaterCo Dispatch Copilot. The [backend guide](../backend/README.md) and [frontend guide](../frontend/README.md) describe operation; the [system design](system-design.md) defines the current contracts.

## Product objective

Produce an explainable dispatch table from operations messages and trusted order/workshop records. For each batch, establish whether a workshop can make it, can take it given capacity and queue, and is allowed to take it. The dispatcher controls the final destinations and can inspect the evidence and calculated consequences.

The application saves decision tables. It does not book workshop work, track production progress or maintain live operational reservations.

## Implemented capabilities

| Area | Implemented behavior | Boundary |
|---|---|---|
| Operations chat | Save named messages, read history, capture a fixed snapshot, display configured dates and explicitly start processing. | One shared conversation. Processing requires paid-processing permission on the API server. |
| Interpretation | Extract owned messages, identify separate jobs, link supported follow-ups, verify task evidence and retain unresolved input. | Semantic errors remain; source coverage and valid schemas do not prove correct interpretation. |
| Allocation | Check workshop rules, calculate delivery/cost/queue effects and rank candidates in deadline order. | Fixed CSV inputs and tentative queues; no guarantee of a globally optimal plan. |
| Dispatcher review | Correct facts, complete requests, add batches, choose destinations and acknowledge applicable warnings. | A valid order identity is required. Failed source records are not all directly repairable. |
| Preview | **Check workshop options** calculates the complete pending choice set without saving. | Ordinary form edits do not call the backend; later edits invalidate the preview. |
| Approval and reallocation | **Approve all** applies choices once, places manual destinations first, replans flexible work, saves and reports changes. | Saved tables can contain unresolved rows. No second approval is required. |
| Review again | Apply further choices to a saved table and save a new version from the original queue snapshot. | Earlier manual destinations remain fixed unless changed or cleared; other rows may move. |
| HTTP and web interface | FastAPI serves chat, runs and reviews; Next.js provides introduction, Chat and Dispatcher pages. | No authentication, operational assignment service or multi-dispatcher coordination. |
| Evaluation | Historical scheduler benchmark, request experiments, a reviewed 100-case key and automatic/assisted scores. | Development-set results and key-informed corrections are distinct from held-out accuracy and measured human performance. |

## Current priorities

1. **Verify the integrated user journey.** Exercise Chat, snapshots, processing handoff, the matching review, preview, approval and Review again. Preserve source mappings, refusal feedback and existing run evidence.
2. **Resolve observed correctness gaps.** Three historical golden runs expose unsafe cancellation interpretation. The 24 October source sends recognized cancellation/hold wording to review and lets the dispatcher cancel the request; a saved-answer replay held CASE-097, but broader wording and a fresh run remain to be measured. Internal links can discard unsaved choices. The dispatch-versus-delivery comma check can ask an unnecessary date question.
3. **Strengthen evaluation.** Consolidate all 30 supplied requests by required behavior; score decisions and explanation faithfulness separately; specify stronger scoring and test its boundary cases before future comparisons.
4. **Evaluate generalization and human effort.** Freeze unseen conversations before further tuning, repeat selected comparisons and measure dispatcher performance without answer-key access.
5. **Prepare reproducible handover.** Retain input identity, settings, scoring versions, selected sanitized evidence and setup requirements. Containerization and deployment remain the final phase.

The [further implementation roadmap](../FURTHER_IMPLEMENTATION.md) records the next product extensions: workshop-maintained availability in a proposed PostgreSQL operational store, local PII filtering, basic prompt-injection checks and a public cost evidence bundle. They remain planned work; core correctness and the required evaluation retain priority.

These are priorities, not authorization for paid model calls or implementation of every proposed experiment.

## Dispatcher contract

Unfinished choices remain in page memory. Dropdowns, corrections and resets do not write drafts, checkpoints or browser storage. **Check workshop options** is an explicit read-only calculation over the complete set. **Approve all** sends that set once, calculates once and saves immediately with a change report.

Python starts from the original workshop queues, places manually selected destinations first and plans flexible batches around them, each group in earliest-deadline order. A manual destination can override normal status, capability, batch-cap, exclusion and lateness rules; its consequences are recorded. Unknown order identity is refused rather than invented. Automatic choices continue to enforce the normal rules.

**Review again** starts from saved decisions plus new choices and rebuilds once from the same input snapshot. It does not add the prior result's reservations again. Final tables may retain unresolved rows; approval does not establish that every source request was resolved or that a workshop assignment was committed.

## Workshop queues and the planned live SQL workflow

### Current behavior

- Queue values represent days of production work; capacity represents pieces per day.
- A planned batch adds production plus expected rework to a temporary queue: production is pieces / capacity, and expected rework is production × defect rate × 0.5.
- Pickup/transport affects delivery time but does not occupy production capacity.
- Reviews reserve no tentative work. Provisional recommendations do reserve tentative production/rework, but unchecked warnings prevent final approval of those rows.
- Each calculation begins from the loaded snapshot. CSVs are unchanged; elapsed time and real workshop progress are not applied automatically.

For example, 3 starting queue days plus 2 production days and 0.02 expected rework days yields 5.02 tentative queue days.

### Future operational workflow

Live assignments require current order/workshop facts, a consistent workload snapshot and an atomic commit of assignment, reservation and history. Confirmation must recheck changed facts, repeated submissions must not reserve twice, and failure must preserve the last valid state. A graph checkpoint stores workflow progress and cannot replace this operational transaction.

Queue ownership must be defined before implementation: a workshop total that already includes application assignments must not have those assignments added again. Per-batch remaining work, including external work, is a candidate design. PostgreSQL is now the proposed shared operational-store direction for access by workshop staff and dispatchers; SQLite remains a local alternative and continues to support the existing chat/checkpoint flow. The operational schema and transaction service do not exist.

Future acceptance checks include changed status/capacity between preview and commit, duplicate confirmation, rollback, external work and progress updates without double counting. These checks concern future live operations, not the implemented file-based reallocation.

### Workshop availability and self-service updates

An authenticated workshop screen should let staff record their own temporary closures and permitted capacity changes through the backend API. A one-week closure must affect automatic eligibility when the proposed production period overlaps it; checking only the dispatch date is insufficient. Date boundaries, calendars and reopening behavior need an explicit policy before calendar-aware estimates are implemented. Administrative suspension and other workshops' data remain outside workshop-edit permissions.

Retain versions and an audit history, recheck relevant changes before approval, and flag existing affected work without silently transferring accepted assignments. Preserve the current manual-override contract while defining future operational authorization. The [roadmap](../FURTHER_IMPLEMENTATION.md#1-shared-operational-data-and-workshop-availability) records alternatives and acceptance checks. Keep supplied CSVs and the historical simulator unchanged.

## Planned privacy, injection checks and public evidence

- **Local PII filtering:** start with defined contact/identifier patterns and stable aliases; evaluate local entity recognition only if required. Protect model calls and external tracing, preserve order facts and exact-source checks, and measure misses, unnecessary masking and added latency.
- **Basic prompt-injection checks:** begin with an explainable local signature set and visible review of flagged input. Aho-Corasick is an optional matching optimization; a local encoder classifier needs separate evaluation. Preserve legitimate corrections and do not describe these checks as complete protection.
- **Public cost evidence:** export selected sanitized usage records and the historical price/calculation method. The retained 22 October run reproduces a $0.0757 model-usage estimate for 128 calls; raw run folders remain excluded. Keep historical estimates, local response reuse, provider-cached input and human review costs distinct.

Implementation details, verification criteria and the proposed sequence are centralized in [Further implementation](../FURTHER_IMPLEMENTATION.md). No privacy/security measurement, database implementation or new paid run is established by this planning update.

## Decisions and limits

| Topic | Current contract or open boundary |
|---|---|
| Quality-sensitive work | An explicit quality preference ranks by defect rate. Automatic inference from value/delicacy and new weights need defined inputs and evaluation. |
| Hybrid policy | Lateness, cost and piece share; no direct defect-rate weight. |
| No on-time automatic option | Leave the request for review. The historical harness adapter must instead choose the least-late eligible option. |
| Chat/CSV deadline disagreement | Checked chat evidence can override the CSV date; otherwise the CSV date applies. Automatic discrepancy alerts and an authorization policy are not implemented. |
| Standing instructions | Restrictions are task-local; global scope and expiry need a defined policy. |
| Started/completed work | Historical replay includes completed orders. Operational transfer, remaining-stage work and live status/calendar policies are not implemented. |
| Saved lateness acceptance | Rechecked during planning. Additional changes can return a previously accepted row to review; saved and newly submitted consent have different whole-submission refusal behavior. |
| Cancellation | Historical golden runs expose an unsafe recommendation. The 24 October source guard adds a clarification blocker for recognized possible cancellation/hold wording; it does not itself cancel the request. An explicit `cancel` decision, offered in the Dispatcher as **Cancel this request**, excludes a verified request from planning; `clear` undoes it. A saved-answer replay held CASE-097. Negation, supersession and wording before the first order ID can still need human review. |
| Failed intake/link/verification recovery | Added batches can cover missing work, but the source review can remain unresolved beside the replacement. |

## Evaluation and evidence

### Historical scheduler replay

The unchanged supplied simulator compares five objectives and a hybrid against random eligible, highest capacity and cheapest eligible, with normal and shock scenarios over 120 historical orders. Seed 5105 and all six official outputs are retained: mean delivery days, p90 delivery days, percentage late, percentage defective, cost and maximum workshop share.

The adapter uses each batch's sent date and current harness queues. It retains the application's unrounded feasibility check and supplies a least-late destination when the harness requires a choice. External mean/p90/total tardiness measures are reported separately from the six official metrics.

See the [benchmark](../backend/eval_harness/results/harness_results_2026-10-15.md) for complete comparisons, shock assumptions and baseline wins. Delivery outcomes are separate from API latency; random defect draws do not establish production quality guarantees.

### Request interpretation and explanation

All 30 supplied requests must be reported by extract / clarify / refuse / decline-to-answer behavior, with decision correctness and explanation faithfulness judged separately. These requests informed development, so they are not held-out evidence.

The additional 100-case, 149-message synthetic set was comprehensively hand-reviewed by three team members and frozen before initial scoring. Tests 10 and 11 preserve three fresh automatic runs and a separate key-informed dispatcher experiment. Existing scores can count allocations with lost preferences; the final coverage headline does not require timeliness or every field to match. A stronger score must be versioned rather than applied retroactively to improve historical numbers.

The final evaluation should include at least 10 individual failure analyses, unseen requests after tuning on known failures, category breakdowns, repeatability information, calls/tokens/cost/latency and explanation evidence. Saved-answer replays establish deterministic behavior for those answers, not model stability. Human-informed recovery establishes capability, not measured dispatcher time savings.

### Verification status

Latest recorded results, 24 October 2026 after the cancellation change: 170 offline backend tests and 66 frontend Playwright tests passed; type checking, lint and the frontend build passed. Some backend checks require local notebooks or saved runs excluded from the public repository. Browser tests use controlled API responses; the chat bridge also has an offline real-pipeline test using saved model answers. These checks do not establish live operational safety or unseen semantic accuracy and were not rerun for documentation editing.

DeepEval examples are local reference material, not an integrated evaluation service. Select semantic metrics only for actual language tasks; exact structured lookups do not justify retrieval metrics.

## Sprint and final presentation checklist

- Sprint 1: problem, business value, architecture, assumptions, risks, chosen primary objective and success criteria.
- Sprint 2: working demonstration, architecture overview, implemented/planned capabilities with owners/status and a credible validation plan.
- Sprint 3 and final: demonstration, baseline/objective/hybrid/shock comparisons, all 30 request behaviors, separate explanation evaluation, failures, limitations and reproducible records.

The original brief requires a final evaluation report with metric rationale, dataset construction, per-category results, at least 10 analysed failures and further measurement plans. Presentation claims must distinguish current capabilities, historical evidence and planned work.

## Deferred work and records

Authentication, multiple live channels, voice, operational assignment transactions, workshop notifications, live queue ownership and general-purpose question answering remain future work. Docker and deployment follow core correctness and evaluation. The [engineering log](engineering-log.md) records dated causes, changes and verification; the [evaluation guide](../evaluation/README.md) indexes measured results.
