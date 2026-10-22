# SweaterCo Dispatch Copilot

## From factory chat to a dispatch decision you can inspect

**Project highlights · Evidence recorded through 20 October 2026**

> Understand the request. Enforce the rules. Calculate the trade-offs. Preserve the evidence.

Our backend turns informal factory messages into checked tasks and an explainable workshop allocation preview. It helps answer the dispatcher's three practical questions: **can this workshop make the batch, can it take the workload, and is it allowed to take it?**

The [experiment guide](experiments/README.md) links the earlier notebooks. The [development notes](experiments/development-notes.md) and [timeline](experiments/timeline.md) explain the problems found, changes tried and checks recorded along the way.

| Engineering evidence | What we have demonstrated |
|---|---|
| **123 backend tests, plus dedicated prototype checks** | Processing, routing, allocation, harness integration, the complete LangGraph flow with its dispatcher review pause, dispatcher decisions and synthetic-data feasibility; latest suite status is stated below |
| **120 historical orders · 8 workshops** | Evaluation with the supplied course simulator |
| **6 allocation policies · 3 baselines** | Normal and shock scenarios: 18 policy/scenario combinations |
| **8.1 vs 21.5 mean delivery days** | Default policy versus the random baseline in the normal replay |
| **18 saved answers · 0 new model API calls** | A complete 26-message graph execution using the local response cache |
| **Verified LangSmith trace** | The actual full-pipeline run, its graph steps and final plan were confirmed remotely |
| **Dispatcher review and re-review** | Typed corrections, eligible workshop choices, acknowledged lateness, protected approvals and final JSON in notebook 06, also tried on a Gradio screen; since 20 October the pipeline pauses for this review, keeps it in a SQLite checkpoint and saves it after one final approval |
| **30/30 readiness agreement in the corrected replay** | One fresh 30-message model run, replayed after a Python date fix; development-key agreement, not 30 assignments or a general accuracy guarantee |
| **111 extended-chat tasks verified** | The newer extended run checked all tasks, compared with only 4 under the earlier hold mechanism |
| **100 synthetic task cases · 149 messages** | 85 jointly feasible recommendations and 15 explicit exceptions, checked offline against unchanged workshop profiles |

---

## 1. Clear responsibility for language and decisions

**LLMs interpret the request. Python validates the evidence, enforces eligibility and calculates the allocation.**

The language stages identify jobs, connect supported follow-ups and assess the current request. Deterministic code performs order lookups, parses supported dates, checks restrictions, estimates delivery and cost, ranks workshops and updates tentative queues.

- Workshop eligibility runs before ranking: status, product compatibility, batch caps, exclusions and requested destinations.
- Readiness is calculated from the checked assessment and its blockers.
- Costs, delivery estimates and ranking keys are saved with the decision.
- Unsupported conditions, unclear instructions and late-only choices produce explicit review outcomes.
- Python resolves the supported relative delivery words from the recorded message date, preserves written years and reads dates copied with delivery wording such as "due Apr 13".
- A recognised piece count written for the identified order is compared with the CSV quantity in Python. A mismatch adds a clarification blocker without replacing the recorded quantity, even if the model overlooks the conflict.
- Dispatch timing stays separate from delivery deadlines. A deadline on or before dispatch goes to review without estimates, a least-late choice or a queue reservation.

This gives the dispatcher a calculation that can be inspected alongside the original wording.

## 2. Conversation processing with evidence and task identity

The input pipeline goes beyond extracting an order number from a sentence:

**Messages → extracted items → linked tasks → verified current versions → routing → allocation.**

| Capability | Why it matters |
|---|---|
| Separate message, item, task and order IDs | One message can contain several jobs; several messages can describe one evolving task. |
| Independent requests stay distinct | Sharing an order or customer does not automatically merge two jobs. |
| Context-aware extraction in bounded batches | Earlier messages provide context while each target message is extracted once. |
| Original quotations and order-reference coverage checks | Accepted extraction must retain written order IDs and use verbatim evidence. |
| Follow-up linking with bounded candidates | Attachments must use supplied task IDs and supporting text; uncertain relationships remain visible for review. |
| Task versions and verification invalidation | A linked correction increments the version and clears the earlier verification. |
| Evidence-backed scheduling fields | Dates, preferences and workshop instructions retain their source evidence. |
| Explicit outcome accounting | Recommendations, clarifications, processing reviews, unresolved links and non-task messages remain recorded. |

**Useful previews despite unresolved follow-ups.** Original tasks continue through normal verification; potentially affected recommendations carry provisional summary labels and references to the unresolved input. The dispatcher can inspect a calculation while the uncertain relationship remains explicit. Notebook 06 now prototypes typed corrections and recalculation; automatic resolution of ambiguous links and cancellations remains future work.

The processing stages use structured response schemas and additional Python checks. Response matching also checks task IDs and versions, so an answer for another task or an old version cannot silently become the current assessment.

## 3. Scheduling gains measured against the supplied baselines

We evaluate the allocation rules using the **unchanged course harness**, with the same input orders and seeded simulation settings for every policy. All three baselines remain in the comparison.

**Normal historical replay · 120 orders · official harness metrics**

| Policy | Mean days | p90 days | Late | Defective | Cost | Maximum workshop share |
|---|---:|---:|---:|---:|---:|---:|
| Random eligible | 21.5 | 45.6 | 34% | 4% | 111,780 | 23% |
| Highest capacity | 49.0 | 80.6 | 84% | 4% | 108,430 | 70% |
| Cheapest eligible | 105.1 | 192.9 | 93% | 8% | 85,960 | 70% |
| **Our default: minimize tardiness** | **8.1** | **13.7** | **2%** | 6% | 115,360 | 25% |

The default policy reduces mean delivery time by approximately **62% versus random**, using the displayed rounded results. Its reported late percentage falls from **34% to 2%**.

- In the shock replay, the default still records **8.3 mean days and 2% late**, compared with random's **23.4 days and 39% late**.
- A separately labelled external measure records **20 total days late**, compared with **704 for random** in the normal replay.
- Alternative objectives expose real trade-offs: the cost objective records **101,005 cost and 2% late** in the normal replay, with 16.5 mean delivery days.

The full comparison also includes defect, concentration, robustness and hybrid policies. Baselines retain visible wins: cheapest has the lowest cost, while random and highest capacity have fewer defective batches than our default in this seeded normal replay. These results support a strong delivery improvement without claiming a win on every metric.

The harness requires one eligible workshop per order. Where the application would request review because every option is late, its evaluation adapter selects the least-late option. That difference is documented, and the six official metrics remain unchanged.

## 4. Testing across sizes, ambiguity and failure conditions

Our development evidence covers compact conversations, independent requests, targeted failure cases and a larger interleaved chat. Each input serves a different testing purpose.

| Input | Size | What it exercises |
|---|---:|---|
| Empty and blank files | 0 messages | Clean early exit without creating a run or plan |
| Conversational demo | 7 messages | Corrections, short replies, incomplete identity and quality instructions |
| Focused blocker cases | 26 messages | Holds, pauses, cancellations, missing instructions, separate jobs and ambiguous links |
| Supplied request file | 30 messages | Independent dispatch requests, vague references, restrictions and unsupported information questions |
| Extended chat | 222 lines, including 220 labelled messages | Interleaving, wrong attachments, review propagation, unknown orders and conflicts with stored order facts |
| Balanced synthetic extended conversation | 100 intended task cases across 149 messages | Consistent feasible work alongside corrections, interleaving, relative dates, workshop restrictions and 15 explicit exceptions |

**The 123-test backend suite covers the implementation from several angles:**

- Structural comparisons with the reference notebook, plus exact prompt and schema comparisons.
- Hand-worked allocation cases C1–C14 and controlled routing examples.
- Decision and queue comparisons across saved processing states.
- Complete graph execution compared with both the notebook and the two-script path.
- Injected interruptions during extraction, linking and verification.
- Partial-preview accounting, preservation of processing files and plan-history behaviour.
- Harness eligibility, policy choices, queue use and external lateness calculations.
- The run report: costs from saved call records, and scoring against an answer key, checked on a made-up perfect run and one fault at a time.
- The dispatcher review: the modules against notebook 06's Part 8 on 13 saved runs and one decision sequence, the controlled decisions, every answer refusal, changed inputs, and a review paused, closed and resumed on a SQLite file.

Additional checks cover the interface prototypes and the new fixture:

- **12 mock-chat tests** cover shared storage, submission retries, concurrent writes, failed-save recovery and reproducible exports.
- **Nine dispatcher decision cases** cover corrections, invalid choices, explicit late acceptance, protected approvals, changed estimates, re-review, finalization and saved history. The retained check also exercises saved-run views with fake explanations.
- **The 100-case fixture check** verifies message coverage and all 85 on-time recommendations in one cumulative plan, with independent production/rework arithmetic and repeatable queues.

Recorded mutation checks deliberately broke selected routing, queue and integration behaviour and confirmed that the checks detected those changes.

**Latest recorded suite status:** all 123 backend tests pass (20 October 2026), including 11 for the run report, 23 for the graph and its review pause, 22 for the dispatcher review modules and 4 for the first HTTP API endpoints. The saved-run comparison now removes the declared provisional-warning marks before comparing Test 8's summary rows with the notebook reference; decision records, routing and queues are compared unchanged. The separate synthetic-fixture check passes.

The experiments have also exposed concrete weaknesses, including excessive holds and incorrect or refused links. We retain the failures and their evidence so improvements target observed problems. These are development datasets; unseen accuracy and repeated fresh-model reliability remain separate measurements.

## 5. Model and reasoning choices tested against cost and behaviour

We have **eight documented experiment groups** covering model changes, prompt alternatives, reasoning effort, larger inputs, hold behaviour and the newer deadline rules. The comparisons include:

- `gpt-4.1-mini` and `gpt-5.6-luna` across the language-processing stages.
- The current intake prompt and two rewritten alternatives.
- A mixed-model pipeline and an all-Luna pipeline.
- Luna linking at both `medium` and `high` reasoning effort.
- A verification comparison with identical task evidence, prompts and batches while changing the model configuration.

The results informed the current stage settings: **intake at `high`, linking and verification at `medium`**. Higher effort did not automatically improve linking: the tested `high` setting became stricter and was reverted.

The earlier all-Luna run on the original 30-message file achieved **30/30 intake labels and 28/30 readiness agreement**. Test 7 then made one fresh run after the deadline changes. It exposed a concrete formatting failure: the model copied "due Apr 13", while the date reader accepted only the bare date. A focused Python fix restored those three cases without changing model answers.

Replaying Test 7's 20 saved answers after that fix gave **30/30 intake labels, 30/30 readiness agreement and every allocation-plan outcome matching the development key**, with zero new API calls. One judgment-call field difference remained. This is agreement on one development sample; only 20 requests were expected ready for scheduling, and the plan still made three automatic recommendations.

**The newer extended-chat run verified all 111 tasks**, with 19 of the key's 20 expected-ready tasks ready and 40 of 41 verified order-data conflicts blocked. It reused 155 earlier intake/link answers and made 37 new verification calls. The run exposed one unflagged wrong recommendation (R191: 1300 pieces written, 200 in the order data), so its safety condition was not met. A Python piece-count check added the same day blocks it: replaying the saved answers with no API call leaves 3 correct recommendations and 0 unsafe ones. We retain the original result alongside the progress; it does not establish reliable automatic handling of arbitrary conversations.

| Historical cost evidence | Recorded amount |
|---|---:|
| Original 30-message file, all-mini and current all-Luna configurations (fresh-run equivalents) | Approximately **$0.018–$0.020** |
| Extended-chat diagnostic run, 157 model requests | **$0.0760** |
| Targeted verification increment after the hold change, 3 new calls | **$0.0031** |
| Test 7, fresh 30-message run, 20 calls | **$0.0157**, approximately 105 seconds of model time |
| Test 8, 37 new verification calls with intake/linking reused | **$0.0705**, 8 minutes 11 seconds wall time |
| Repeated full graph run using 18 saved answers | **0 new model API calls** |

These are recorded experiment costs or estimates from recorded usage, rather than a universal price per request. Fresh-run equivalents include requests that an experiment may have answered from the local cache. Most configurations have limited fresh samples; cached repetitions establish reproducibility rather than independent model trials.

## 6. Persistent response caching that makes iteration economical

Every intake, linking and verification model request passes through one recording-and-cache layer. Its fingerprint covers the **stage, model, reasoning effort or temperature, prompt, complete payload and response schema**.

A matching saved answer is loaded locally before any API client is created. The normal validation and processing checks still run, and the new run records `reused_response: true`.

Answers are saved as JSON under the configured output folder's `response-cache/`, so reuse survives a process or notebook-kernel restart. Each run also retains its own `calls/` records. Changing one stage's model, effort or prompt invalidates that stage's matching requests; other stages can still reuse identical requests, while changed downstream evidence can require new answers. A different output folder has its own cache.

The verified full-pipeline replay handled:

| Stage | Saved answers reused | New model API calls |
|---|---:|---:|
| Extraction | 9 | 0 |
| Linking | 6 | 0 |
| Verification | 3 | 0 |
| **Total** | **18** | **0** |

**A fresh graph execution can therefore rebuild tasks and recalculate the allocation without repeating the model work.** This recorded 18-answer example predates the provisional-warning change. The current flow can reach additional verification requests, so the same chat is not guaranteed to remain fully cached. Cache hits avoid model-request latency and additional model charges. Standalone allocation also supports repeated objective experiments without calling a model.

Changed requests can require new paid calls, including downstream requests whose payloads change. Saved responses preserve earlier mistakes too; fresh model evaluation remains distinct from a cached replay.

**Dispatcher explanations have their own cache.** Notebook 06 Parts 1-7 fingerprint the explanation model, settings, prompt and calculated facts, then reuse saved text from `output/dispatcher-ai-cache/`. A changed explanation request can make a paid call. Part 8's dispatcher calculation and Part 9's Gradio screen do not call an explanation model.

The run reporter distinguishes new model spending from the estimated cost of making every recorded request fresh. Locally reused records retain their original token/time metadata, which is excluded from this run's new model spending and model time. These local saved-answer hits are separate from provider-side cached input tokens on a new API request, which the reporter prices using its recorded rate table.

## 7. Observability from original message to final plan

Every run leaves inspectable artifacts:

| Artifact | What it makes visible |
|---|---|
| `manifest.json` | Input messages, stage models, prompts and processing settings |
| `state.json` | Extracted items, task versions, verification, reviews and unresolved links |
| `calls/` | Request fingerprints, model responses, recorded usage/timing and cache reuse |
| `plan.json` | Outcomes, original-message coverage, constraints, candidate calculations, ranking evidence and queue snapshots |
| `plan-history/` | Timestamped copies for inspecting earlier previews; objective experiments retain separate files |
| `run_report.md`, when generated | Settings, stage/outcome counts, review reasons, calls, token use, estimated cost and model time; optional scores against a matching answer key |

**A reusable offline reporter replaces one-off result inspection.** `make_run_report.py` produces the report for an explicitly selected saved run; supplying a matching key and data folder adds case outcomes, causes, field agreement, message labels and follow-up-link checks. It records the key's hash and rejects mismatched chat/data inputs. The command makes no model call and changes only the derived report. It is currently invoked separately rather than automatically after every pipeline run, and it requires a saved `plan.json`.

Standalone allocation can produce partial previews with a completeness flag, printed warnings and records for unfinished inputs. An execution exception stops the full graph before allocation; it does not automatically emit a partial plan. Reviews retain their reasons and reserve no tentative capacity. Plan creation time is separate from the dispatch date used by the calculations.

The modularized **LangGraph pipeline** connects processing and allocation in one run, then pauses for the dispatcher's review. Its nodes call the same tested functions used by the standalone development scripts.

With tracing enabled, **LangSmith records the full graph even when every model answer comes from the local cache**. The run on 15 October at **9:19:26 pm Singapore time** was confirmed remotely: 26 messages, a final plan, 34 chain spans and no recorded errors. It contained zero LLM spans because no model was invoked.

This gives us two complementary views: local artifacts preserve the detailed records, while LangSmith shows the execution flow. Tests deliberately disable cloud tracing; standalone scripts have different tracing coverage from the full graph.

## 8. A shared chat prototype with reproducible inputs

The existing Streamlit mock chat gives multiple browser sessions one shared conversation, stored in project-local SQLite. It retains the sender, original text and timestamp. A successful send clears the draft; a failed save keeps the text available to retry. Submission IDs distinguish retrying one event from deliberately sending the same wording again.

An explicit export captures the conversation once and saves a TXT snapshot plus a manifest with source-message mapping, original multiline text and the TXT's SHA-256. Export files are published together after both writes succeed. This provides stable inputs for experiments without replacing the original conversation.

The chat exports inputs for processing; automatic pipeline execution, clarification replies and a product dispatcher interface are not connected yet. Its SQLite database stores messages, not workshop assignments.

## 9. Dispatcher views, decisions and optional re-review

Notebook 06 now prototypes the dispatcher's next step after an allocation preview.

**Two views make each case inspectable.** Suggested allocations show the original request, order facts, selected workshop, calculated comparisons and rejected alternatives. Needs attention groups unresolved cases by their actual problem. Cached AI notes sit beside the recorded reasons; unsupported history/pricing questions receive a plain limitation notice and make no explanation-model call. Views can also be saved as text.

**Part 8 applies structured dispatcher decisions in Python, without another model call:**

| Action | Implemented prototype behavior |
|---|---|
| Correct an order ID or deadline | Resolve only the named blockers, create a derived task version and retain dispatcher provenance. |
| Choose a different workshop | Allow a lower-ranked eligible choice while enforcing status, category, batch caps and exclusions. A new choice replaces an earlier approval of the task. |
| Accept calculated lateness | Retain the deadline and limit acceptance to the reviewed workshop, task version and accepted delay. A past deadline first needs a confirmed revised date. |
| Approve work | Reserve approved work first in its recorded approval order and seed both queues and assigned piece counts. Changed facts or a refused/worsened estimate withdraw approval visibly. |
| Review again or finalize | Rebuild from the original saved state and current decisions. Finalize changes labels, not calculated queues; unchecked warnings remain unresolved. |
| Save a revision | Save decisions and the derived plan with history copies, preserving the original processing state, manifest and allocation plan. |

The calculation avoids accumulating another reservation each time a preview is repeated. Nine controlled decision cases pass, and a deliberately broken version that ignored approvals failed the protection check. These are notebook checks with simulated human decisions. Duplicate-order resolution, cancellation handling, link-review recovery and operational assignment transactions are not implemented by this prototype.

**Part 9 puts both views and these decisions on one Gradio screen.** Each decision goes into the same decisions Part 8 saves, so the latest decision counts, and recalculates the plan and queues at once; no model is called. The form names each task by its order, deadline and request, and clicking a table row picks its task. The screen lets us decide what the React dispatcher page must show and send before building it, and its decision table is that page's first data contract. Unsupported cases stay visible with their reasons.

**Since 20 October the pipeline itself pauses for the dispatcher.** Part 8's calculation moved into `backend/dispatcher_review/`, and the LangGraph run stops after the plan with the first review. The dispatcher answers from the terminal (`resume_dispatcher_review.py`): edits are checked and recalculated into a new review. The dispatcher decides: a chosen workshop is fixed first and always used, even when late, past its deadline or against a hard rule, with the override written in its reason, and Python plans the other work around it. One final "approve all" saves the review last shown as JSON, without planning again. A paused review is kept in a SQLite checkpoint, so it survives the program ending. Each answer is all or nothing, and a refused one says why and changes nothing. This replaces the notebook's per-row approvals with one final approval; the notebook stays unchanged as the reference. No model is called while reviewing. The checks are offline tests with simulated answers; the frontend that will send these answers is not built yet.

AI explanation text has been generated in one recorded run, but faithfulness has not yet been scored. The typed decision calculation is separate from those explanation calls.

## 10. A matching synthetic dataset for extended testing

We created a [separate 100-case test set](backend/data/extended_dispatch_100/README.md) with new order IDs, matching conversational requests and a byte-identical snapshot of the supplied workshop profiles. AI custom-created its questions and dispatch requests after repeated project experiments, with several difficulty levels to emulate real-life situations and target weaknesses found in intake, linking, verification and allocation. Source CSVs and the professor's simulator are unchanged.

The conversation includes **149 messages, 45 follow-ups, interleaved requests, confirmed corrections and two messages that each contain two jobs**. The expected relationships and final fields are recorded in a separate answer key, outside application inputs.

**With the authored correct interpretations, 85 cases receive valid on-time recommendations together in one earliest-deadline-first plan.** Validation uses the existing routing/allocation code, includes every earlier production/rework reservation and confirms that rerunning does not double-count workload. All seven active workshops receive work; suspended W7 receives none. The 15 exceptions exercise expired dates, an impossible future deadline, status/capability/cap restrictions, splits, budgets, conflicting quantities, uncertain dates, unknown/missing identity, cancellation/pause and unsupported history.

This is **85% designed and verified feasibility**, not an 85% observed AI success rate. In the better of two full runs on 21 October 2026 (Test 10), 80 of 85 cases were allocated correctly, 14 of 15 exceptions were held and one cancelled order (CASE-097) was allocated unsafely; see [evaluation/](evaluation/README.md). The separate test makes it possible to measure avoidable reviews on feasible work while retaining known exception cases, without confusing contradictory source data with successful-request throughput.

**Three members of our team divided the work and comprehensively hand-reviewed the complete set, line by line. This review was performed by humans, not AI.** The [returned workbook](backend/docs/evaluation/extended_dispatch_100_human_team_review.xlsx) preserves their notes unchanged. The [human-team golden key](backend/docs/evaluation/extended_dispatch_100_human_team_golden.json), version 2, applies 12 preference corrections following those notes and the owner's clarification: without an explicit preference, the default is to minimize lateness. Outcomes and message links are unchanged, and the offline check still confirms 85 feasible cases and 15 exceptions. The [review record](backend/docs/evaluation/extended_dispatch_100_REVIEW.md) records the owner-confirmed three-member review, reconciliation and hashes; individual names and dates were not supplied or invented. AI drafted the original material and assisted with reconciliation, which is separate from the human review.

---

## A presentation-ready description

> We turn informal factory chat into evidence-backed dispatch previews. Language models interpret requests; Python checks workshop eligibility and calculates delivery, cost and queue effects. Our notebook now lets a dispatcher correct facts, choose an eligible workshop, protect approvals and review a recalculated plan, also on a simple screen that recalculates after every decision. We also built a matching synthetic test set of 100 task cases across 149 messages, with 85 verified as jointly feasible before any model run. AI custom-created its varied scenarios after repeated experiments, and three team members divided the work and hand-reviewed the set line by line. In the unchanged supplied historical simulator, our default policy reduced mean delivery time from 21.5 to 8.1 days against random, with the reported late percentage falling from 34% to 2%. Saved responses, decision history and LangSmith traces let us inspect and reproduce recorded results.

**Scope of the evidence:** the application produces previews. Dispatcher actions are a notebook prototype and a terminal-driven pause in the pipeline; a final approval is saved JSON, not a committed assignment. Historical simulator gains, development-key interpretation scores, controlled dispatcher checks and synthetic-data feasibility are separate results. Test 8 exposed an unflagged quantity-conflict recommendation, now blocked by a Python piece-count check in a no-cost replay; conversational linking and explanation faithfulness still need improvement/evaluation. Live commitments, a connected dispatcher frontend, repeated fresh-model reliability and unseen generalisation are not established by the current work.

## Evidence behind the highlights

- [Current implementation, test coverage and harness results](backend/README.md)
- [Prompt, model, reasoning-effort and cost experiments](backend/docs/evaluation/PROMPT_TESTING_RESULTS.md)
- Extended-chat evaluation and failure analysis
- Dispatcher prototype, implemented actions and offline checks
- Shared chat and reproducible snapshot exports
- [Synthetic extended dataset, expected outcomes and verification](backend/data/extended_dispatch_100/README.md)
- [Current processing walkthroughs: linking](backend/code-section-demos-explanations/01-task-linking-demo.md), [verification](backend/code-section-demos-explanations/02-task-verification-demo.md) and [saved files](backend/code-section-demos-explanations/03-order-processing-files-explanation.md)
- Allocation modularization and verification record
- LangGraph integration and equivalence checks
- [Engineering decisions and verification evidence](docs/engineering-log.md)
- [Experiment notebooks, selected investigations and development timeline](experiments/README.md)
- Known interpretation issues and pending improvements
