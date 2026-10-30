# Project plan

Updated: 31 October 2026 for workshop-informed dispatch priorities and English-only default configuration. Local Chinese translation was implemented on 30 October, after the 29 October model-usage view and voice input. This document separates implemented capabilities, recorded verification and remaining work for SweaterCo Dispatch Copilot. The [backend guide](../backend/README.md) and [frontend guide](../frontend/README.md) describe operation; the [system design](system-design.md) defines the current contracts.

## Product objective

Produce an explainable dispatch table from operations messages and trusted order/workshop records. For each batch, establish whether a workshop can make it, can take it given capacity and queue, and is allowed to take it. The dispatcher controls the final destinations and can inspect the evidence and calculated consequences.

The application saves decision tables. It does not book workshop work, track production progress or maintain live operational reservations.

## Implemented capabilities

| Area | Implemented behavior | Boundary |
|---|---|---|
| Operations chat | Save named messages, optionally dictate a message and check it before sending, save a Chinese message as its local English translation, read history, capture a fixed snapshot (**Prepare chat for dispatch**), display configured dates and explicitly start processing (**Start dispatch workflow**). | One shared conversation. Processing and voice transcription require paid-processing permission on the API server; voice sends audio to OpenAI, is unmeasured on real speech and treats Mandarin as experimental. Translation keeps only the English, checks only order and workshop IDs and runs on Apple silicon only. |
| Interpretation | Extract owned messages, identify separate jobs, link supported follow-ups, verify task evidence and retain unresolved input. | Semantic errors remain; source coverage and valid schemas do not prove correct interpretation. |
| Allocation | Check workshop rules, calculate delivery/cost/queue effects and rank candidates in deadline order. | Fixed CSV inputs and tentative queues; no guarantee of a globally optimal plan. |
| Dispatcher review | Correct facts, complete requests, add batches, choose destinations and acknowledge applicable warnings. | A valid order identity is required. Failed source records are not all directly repairable. |
| Preview | **Check workshop options** calculates the complete pending choice set without saving. | Ordinary form edits do not call the backend; later edits invalidate the preview. |
| Approval and reallocation | **Approve all** applies choices once, places manual destinations first, replans flexible work, saves and reports changes. | Saved tables can contain unresolved rows. No second approval is required. |
| Review again | Apply further choices to a saved table and save a new version from the original queue snapshot. | Earlier manual destinations remain fixed unless changed or cleared; other rows may move. |
| HTTP and web interface | FastAPI serves chat, runs and reviews; Next.js provides introduction, Chat and Dispatcher pages. | No authentication, operational assignment service or multi-dispatcher coordination. |
| Model usage | The Dispatcher shows each saved run's calls, reused answers, tokens, model time and estimated cost by stage, from its call records. | Estimates from a stored price table, not an invoice; model time sums call durations. |
| Evaluation | Historical scheduler benchmark, request experiments, a reviewed 100-case key and automatic/assisted scores. | Development-set results and key-informed corrections are distinct from held-out accuracy and measured human performance. |

## Current priorities

Current product work prioritizes workshop-informed dispatch and a clear, usable interface. The earlier evaluation-first and PII-first implementation sequences are superseded.

1. **Deepen business value in one dispatch workflow.** Scope workshop-maintained availability, temporary capacity and remaining-queue reports in SQL, connected to affected batches, Python recalculation and dispatcher review. This is proposed work; storage choice and the first bounded contract remain to be settled.
2. **Verify the connected workflow.** Preserve Chat, snapshots, processing, preview, approval, Review again and historical evidence. Check changed workshop facts, queue ownership and repeated review; fix consequential defects in the selected flow.
3. **Protect presentation and interface quality.** Prepare a coherent business episode, polished workshop/dispatcher interfaces, a reliable demonstration and backup, concise architecture explanation and presentation rehearsal.
4. **Use existing evaluation evidence.** Consolidate required submission material and retain limitations. No new dataset, model sweep, supplementary benchmark or usability study is scheduled as a separate sprint workstream; functional/regression verification of changed code remains required.
5. **Prepare handover, then consider deployment.** Retain input identity, settings, evidence and setup requirements. Containerization and deployment remain the final phase.

Chinese/bilingual expansion, PII filtering and additional prompt-injection checks are deferred. Translation is disabled by default through its existing configuration; the implementation is retained. The [further implementation roadmap](../FURTHER_IMPLEMENTATION.md) preserves earlier technical research.

On 29 October 2026, the in-app model-usage view and cloud voice input were implemented. The subsequent PII-first extension order is superseded by the 31 October sprint priorities.

On 30 October 2026, local Chinese-to-English translation at **Send** was implemented ahead of that order: Tencent's Hy-MT2-1.8B, 8-bit, on the host through MLX, behind a `config.toml` switch. A translation that changes an order or workshop ID is refused; the English replaces the original. The [system design](system-design.md#local-translation-decision-30-october-2026) records the decision.

Bilingual review, local dictation and Singlish/code-switching remain deferred research. Current source behavior and historical verification remain distinct from those proposals.

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

- **Local PII filtering:** the first scope is names of people and addresses (decided 29 October 2026). Free-text names and addresses need local entity recognition, such as Presidio with a local NLP model, which is a new dependency requiring approval; validating the masked input needs an authorized paid run. Use stable aliases, protect model calls and external tracing, preserve order facts and exact-source checks, and measure misses, unnecessary masking and added latency. Voice recordings reach the transcription model before any text filter.
- **Basic prompt-injection checks:** kept as future work (29 October 2026). Begin with an explainable local signature set and visible review of flagged input. Aho-Corasick is an optional matching optimization; a local encoder classifier needs separate evaluation. Preserve legitimate corrections and do not describe these checks as complete protection.
- **Public cost evidence:** the in-app usage view is implemented (29 October 2026). Still planned: export selected sanitized usage records and the historical price/calculation method. The retained 22 October run reproduces a $0.0757 model-usage estimate for 128 calls; raw run folders remain excluded. Keep historical estimates, local response reuse, provider-cached input and human review costs distinct.

Implementation details, verification criteria and the proposed sequence are centralized in [Further implementation](../FURTHER_IMPLEMENTATION.md). No privacy/security measurement, database implementation or new paid run is established by this planning update.

## Planned Chinese-English communication

Enable workers to write requirements and understand clarification in Chinese or English while preserving the facts needed for workshop capability, capacity/queue and permission checks. The [research and workflow](../MULTILINGUAL_INPUT_RESEARCH.md) recommends typed bilingual input/review before voice and records local translation/ASR candidates, licenses, runtime uncertainty and evaluation design. This is mostly researched scope, not a measured language capability. Two parts are implemented: cloud dictation (29 October 2026), where OpenAI `gpt-transcribe` produces an editable transcript before **Send**, and local Chinese-to-English translation at **Send** (30 October 2026), which saves only the English and was checked on 12 made-up messages.

Keep the original source beside a labeled derived translation (the current translation replaces it), compare direct multilingual interpretation with translation assistance, and extend cancellation/date/quantity validation before enabling Chinese automatic processing. Provide clarification in the worker's language; keep Python calculations and dispatcher authority unchanged. Protect both language views before external interpretation/tracing. Local dictation would replace the cloud call behind the same editable transcript, text fallback and no automatic approval.

Evaluate independently reviewed operational facts, negation/exclusions, follow-up ownership, unnecessary reviews, unsafe actions, translation/explanation faithfulness, speaker-separated voice results and latency. Singlish, Singapore English pronunciation and Mandarin-English code-switching are separate evaluation categories. Required coursework evaluation and known correctness work retain priority; Docker and deployment remain last.

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

Latest recorded results, 30 October 2026 after local translation: 176 offline backend tests and 72 frontend Playwright tests passed; type checking, lint and the frontend build passed. Some backend checks require local notebooks or saved runs excluded from the public repository. Browser tests use controlled API responses; the chat bridge also has an offline real-pipeline test using saved model answers. Voice tests use a fake browser microphone and simulated transcription replies, so no real speech or paid transcription has been tested. Translation tests replace the model's answer; the real model was checked separately on 12 made-up messages. These checks do not establish live operational safety or unseen semantic accuracy and were not rerun for documentation editing.

DeepEval examples are local reference material, not an integrated evaluation service. Select semantic metrics only for actual language tasks; exact structured lookups do not justify retrieval metrics.

## Sprint and final presentation checklist

- Sprint 1: problem, business value, architecture, assumptions, risks, chosen primary objective and success criteria.
- Sprint 2: working demonstration, architecture overview, implemented/planned capabilities with owners/status and a credible validation plan.
- Sprint 3 and final: demonstration, baseline/objective/hybrid/shock comparisons, all 30 request behaviors, separate explanation evaluation, failures, limitations and reproducible records.

The original brief requires a final evaluation report with metric rationale, dataset construction, per-category results, at least 10 analysed failures and further measurement plans. Presentation claims must distinguish current capabilities, historical evidence and planned work.

## Deferred work and records

Authentication, multiple live channels, local speech recognition and measured voice accuracy, operational assignment transactions, workshop notifications, live queue ownership and general-purpose question answering remain future work. Docker and deployment follow core correctness and evaluation. The [engineering log](engineering-log.md) records dated causes, changes and verification; the [evaluation guide](../evaluation/README.md) indexes measured results.
