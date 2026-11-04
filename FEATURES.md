# Capabilities and evidence

SweaterCo Dispatch Copilot reads factory requests, calculates workshop options and records dispatcher decisions. Implementation status and recorded evidence through 3 November 2026 are summarized below. See the [product overview](README.md), [backend guide](backend/README.md) and [frontend guide](frontend/README.md).

## Implemented workflow

| Capability | Behavior |
|---|---|
| Shared operations chat | Each message keeps its sender's name and original text, and a resent message is saved only once. Everyone sees one shared history, and the dispatcher processes a fixed text copy of it. |
| Demo sign-in and roles | A name and a role, Team member, Dispatcher or Workshop, for each browser tab, without passwords or authentication; messages carry the signed-in name. Team members get the Chat page only, including **Clear chat**, which asks "Are you sure?" on the page and then empties the conversation for everyone while snapshots, runs and plans stay. The dispatcher gets the Dispatcher page only: **See chat history** shows the chat read-only, and dispatch processing starts there. |
| Checked voice input | **Record** turns one short spoken request into text in the message box through OpenAI's `gpt-transcribe`; the worker checks and edits it before **Send**. English is supported and Mandarin is experimental. The API refuses it without paid-processing permission. |
| Local Chinese translation | Optional and switched off. When switched on, **Send** saves a Chinese message as its English translation, made locally by Tencent's Hy-MT2-1.8B; a translation that changes an order or workshop ID is refused. It was checked on 12 made-up messages only. |
| Explicit processing | On the Dispatcher page, **Prepare chat for dispatch** captures a snapshot; **Start dispatch workflow** sends it into the language/validation/allocation pipeline. The API requires paid-processing permission. |
| Evidence-backed interpretation | Each message is extracted once, even when it also appears as context; several jobs in one message stay separate; a follow-up with more than six possible tasks goes to review; a correction creates a new task version; each fact must cite a real source message. |
| Deterministic planning | Python checks each workshop's categories, status and batch cap and the request's preferences and exclusions, then calculates delivery, cost, expected rework and queue effects. |
| Workshop reports | A workshop reports whether it is taking new work, its pieces per day, days of work already booked and pickup lead time (3 November 2026). Each run fixes these values when it starts and the planning rules use them; a later report applies from the next run. The Dispatcher page lists reported changes. |
| Uncertainty visibility | Requests needing clarification, uncertain links and provisional warnings stay visible, separate from approved rows. |
| Dispatcher control | Correct facts and quantity, complete an identified request, add batches, fix destinations, check applicable warnings and cancel a request so it reserves no workshop time. |
| Unsaved preview | **Check workshop options** calculates the whole pending choice set without saving or resuming the graph. |
| One approval | **Approve all** calculates once, preserves manual destinations, replans flexible work and saves the change report immediately. |
| Reallocation and history | **Review again** updates saved choices and saves a new version from the original queues, preserving earlier revisions. |
| Inspection | Source messages, task evidence, workshop comparisons, rejection reasons, tentative queues and before/after changes. |
| Model usage and cost | Each saved run's calls, reused answers, tokens, model time and estimated model cost by stage, counted from its call records with no model call. |

Reallocation concerns the proposed dispatch table. It does not recall work already started, book workshop work or update live production queues. A saved final table may retain unresolved rows.

## Clear responsibility for decisions

Language models interpret requests, follow-ups and current constraints. Python checks evidence and order facts and calculates dates, readiness, eligibility, queues, costs and rankings. React displays backend results and sends structured choices.

Automatic selection enforces workshop restrictions and on-time feasibility. The dispatcher's named workshop is authoritative, including overrides of lateness or automatic rules; each consequence is recorded. A known order and destination are still required. Processing never estimates quantity; a human dispatcher may explicitly supply the batch quantity.

Corrections increment task versions and invalidate stale verification. Unresolved follow-ups remain reviewable; affected recommendations can be provisional without inventing a link. Provisional recommendations reserve tentative workload, while unresolved review records reserve nothing. Unchecked warnings prevent approval of those rows.

## Historical scheduler benchmark

The unchanged supplied simulator compares five objectives and a hybrid against three baselines under normal and shock scenarios over 120 historical orders. Official metrics remain unchanged; extra tardiness-severity measures are separate.

| Normal replay | Mean days | p90 days | Late | Defective | Cost | Maximum workshop share |
|---|---:|---:|---:|---:|---:|---:|
| Random eligible | 21.5 | 45.6 | 34% | 4% | 111,780 | 23% |
| Highest capacity | 49.0 | 80.6 | 84% | 4% | 108,430 | 70% |
| Cheapest eligible | 105.1 | 192.9 | 93% | 8% | 85,960 | 70% |
| Default: minimize tardiness | 8.1 | 13.7 | 2% | 6% | 115,360 | 25% |

The default has 2 late batches versus random's 41, with 20 total tardiness days versus 704. In the shock replay it records 8.3 mean days and 2% late versus random's 23.4 days and 39%. Cost and defects remain visible trade-offs, and cheapest wins total cost.

The harness requires a workshop even when every eligible option is late; its adapter supplies the least-late option. The application instead requests review. Results are seeded historical simulation, not live delivery guarantees or language-interpretation accuracy. The [complete benchmark](backend/eval_harness/results/harness_results_2026-10-15.md) includes every policy, assumption and baseline win.

## Conversation datasets and recorded results

| Dataset | Size | Purpose |
|---|---|---|
| Development conversation | 7 messages | Corrections, short replies and quality preferences. |
| Blocker cases | 26 messages | Ambiguous links, cancellations, pauses and missing facts. |
| Supplied requests | 30 messages | Independent dispatch requests, restrictions and unsupported questions. |
| Extended chat | 222 parsed lines, including 220 labelled messages | Interleaving, unknown orders, contradictory facts and review propagation. |
| Golden set | 100 cases across 149 messages | 85 jointly feasible cases and 15 deliberate exceptions. |

AI generated the golden scenarios after development experiments. Three team members then checked every case and message by hand. The reconciled version 2 key was frozen before initial scored runs. The [review record](backend/docs/evaluation/extended_dispatch_100_REVIEW.md) preserves the returned workbook, corrections and hashes; automated consistency checks are separate from human review.

| Golden-set result | Test 10 run 1 | Test 10 run 2 | Test 11 automatic | Test 11 key-informed review |
|---|---:|---:|---:|---:|
| Expected allocations obtained, of 85 | 73 | 80 | 81 | 85 |
| Every allocator field matches the key | 71 | 77 | 78 | 85 |
| Exceptions left unallocated, of 15 | 14 | 14 | 14 | 15 |
| Unsafe exception allocations | 1 | 1 | 1 | 0 |

The automatic score includes provisional recommendations and can count a lost preference as allocated. The final coverage score does not require timeliness or every field to match; split-part detail checks inspect only the main part. Test 11 separately recorded all 85 allocations on time with matching fields after 23 key-informed decisions; 26 source rows remained unresolved. This is recovery capability, not autonomous accuracy or measured human effort.

CASE-097 cancellation was incorrectly recommended in all three fresh runs. A 24 October replay of Test 11's saved model answers, with the new Python cancellation check and no model calls, sent it to review instead: 15 of 15 exceptions held, no unsafe allocation and 81 of 85 allocations unchanged. That is a replay, not a fresh run. Follow-up classification/linking, malformed evidence IDs and the comma/date check also caused failures. Repeated results of 73, 80 and 81 under the same settings demonstrate variation, not a measured improvement between versions.

The supplied 30-request Test 7 replay reached 30/30 readiness agreement after a Python date fix with no new model answers. Test 9's separate fresh run recorded 29/30 readiness agreement. These are development results with different methods, not 30 automatic assignments. See the [evaluation index](evaluation/README.md) and [experiment record](backend/docs/evaluation/PROMPT_TESTING_RESULTS.md).

## Verification and observability

Latest recorded checks, on 3–4 November 2026 after workshop reports and a review pass, passed 184 offline backend tests, 97 Playwright tests, type checking, lint and the frontend build. The backend categories total 184: 27 processing, 25 allocation, 15 harness, 23 graph, 43 dispatcher review, 11 run-report, 4 final-score, 11 run/review API, 19 chat API and 6 workshop report checks.

Checks cover hand-worked scheduling cases, source/schema contracts, task versions, queue accounting, partial plans, graph/standalone equivalence, refusal, preview without writes, approval, re-review and chat snapshots. Recorded mutation checks establish detection of selected deliberately broken rules. Some checks depend on local notebooks/saved runs excluded from publication. Browser tests use controlled API responses; a backend chat test also executes the pipeline with saved model answers.

Runs retain messages/settings, processing state, per-call records and plans. `make_run_report.py` generates counts, reasons, tokens, estimated cost and latency and optionally scores against a matching key; the Dispatcher shows the same per-stage usage for each saved run. `score_dispatcher_review.py` evaluates approved rows. Exact saved-answer reuse avoids another model call but still revalidates the response and recalculates the plan.

Optional LangSmith tracing records graph execution, including cached runs. The historical 15 October trace contained 34 chain spans and zero LLM spans for a fully cached 26-message execution. Tracing can transmit source and decision data; offline tests disable it.

## Remaining limitations

- The 24 October cancellation check recognizes only listed wording. It does not read negation ("do not cancel") or a later instruction that supersedes a cancellation, and wording before the first order ID in a message counts for every order named in it, so it can flag the wrong order. Each such mistake asks for review rather than allocating. Only a replay of saved answers has measured it, not a fresh run; the historical golden scores are unchanged.
- Separate explanation faithfulness, held-out generalization and real dispatcher effort are not established.
- Moving to another page inside the app can discard unsaved dispatcher choices without a warning.
- If the chat and `orders.csv` give different deadlines, there is no automatic alert.
- Voice input sends audio to OpenAI and is not measured on real speech; Singapore English, Singlish and Mandarin are not evaluated.
- Authentication, clarification replies, multiple channels, live assignments and production tracking are not implemented.
- The hosted demo (Vercel frontend, Render backend, deployed 31 October 2026) has a sign-in that labels users but does not authenticate them. Its saved chat, runs, reviews and workshop reports are reset when the backend restarts.

## Planned extensions

The [further implementation roadmap](FURTHER_IMPLEMENTATION.md), updated 29 October 2026, proposes:

- Shared order/workshop records in PostgreSQL, with authenticated workshop updates for dated closures and permitted capacity changes. Automatic planning would check affected production dates and recheck changes before approval. A first, unauthenticated version of workshop reports, applied from the next run, exists since 3 November 2026.
- Deferred on 31 October 2026 in favor of deeper dispatch features: local filtering of people's names and addresses before model calls, basic prompt-injection checks, and bilingual Chinese-English review with local voice recognition. The [model and workflow research](docs/MULTILINGUAL_INPUT_RESEARCH.md) records the candidates and proposed checks.
- A sanitized public evidence bundle for reproducing recorded model-cost estimates without publishing full run records. The in-app usage view covers runs held locally; the public bundle is still to be prepared.

These extensions are not implemented or measured. A database alone does not provide workshop access controls, current availability or live booking guarantees. The [project plan](docs/project-plan.md) defines priorities. The [engineering log](docs/engineering-log.md) retains dated investigation and verification evidence; [experiments](experiments/README.md) preserves historical notebook stages rather than current application contracts.
