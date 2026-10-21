# Pending improvements

Updated: 19 October 2026 (test count, date handling and the dispatcher prototype); the other issues are as of 15 October 2026, after modularization and the provisional-warning change. This is the active backend backlog. Historical observations below are labelled by their original tests; they are not fresh results under the changed workflow.

Current implementation: intake, processing, routing, allocation, the batch LangGraph pipeline and the harness adapter are modularized. The 87 offline tests pass. Notebook 06 Part 8 prototypes dispatcher decisions on saved runs, and Part 9 tries them on a Gradio screen (19 October 2026). Automatic holds have been replaced by allocation-preview warnings; the underlying interpretation errors remain. Partial saved-run previews and plan history are implemented, recorded under issues 12-13 for continuity.

The [backend README](../README.md) owns current behaviour and commands. The [project plan](../../docs/project-plan.md) owns product priorities; [system design](../../docs/system-design.md) owns rules and future dispatcher/state workflows. [Prompt/model experiments](evaluation/PROMPT_TESTING_RESULTS.md), the [extended report](evaluation/EXTENDED_RUN_REPORT.md) and the [engineering log](../../docs/engineering-log.md) preserve evidence. The [provisional-preview solution](../problems_solved/held_tasks_and_unresolved_followups.md) distinguishes the resolved blocking mechanism from unresolved linking.

Current model configuration remains Luna at every stage: intake `high`, linking and verification `medium`. Extraction uses three targets with two context messages; verification batches up to three tasks. CSVs and settings are fixed during a run. Recommendations affect only the temporary plan queue; persistent assignments are future work.

Historical baseline: Test 2 scored 30/30 intake labels and 28/30 readiness on the original requests, which contain no follow-ups. Test 6 produced 14 tasks, six held and eight verified before the warning change; five of nine expected-ready tasks were ready, and R14 lacked an exclusion. It reused intake/link answers and made three new verification calls. A new run can verify more tasks and require new paid calls; it has not been made.

Message labels are local to each input file. Blocker-file R15 and original-file R15 are different messages; extended-file R1 is L0003 because of its two headers.

## 1. A separate task can hide a restriction from the task it belongs to

**Status (15 October 2026): contained by a warning; root cause open.** A verified allocation task with no order ID that requests or excludes a workshop now warns the tasks of the 2 messages before it. In Test 6's saved state, R14 becomes a `provisional_recommendation` naming R15, and no other row in the 14 saved runs changes. The exclusion is still not enforced on R14, and intake still labels R15 a request.

**Observed:** blocker-file R14 requests ORD-024. R15 says, "Fastest workshop excluding QuickStitch." Intake makes R15 a separate request. In Test 6, R14 is ready with no excluded workshops; R15 correctly records W1 as excluded but is not ready because it has no order ID. A downstream plan could therefore select QuickStitch for R14.

**Established mechanism in Test 6, before provisional warnings:** `link_or_create_task` created a task immediately for an item labelled `request`, bypassing linking. Verification blocked R15 itself. However, a verified task needing clarification was not one of the intake/link/task-review records inspected by the former `hold_reviewed_requests`, so it did not hold R14. The older broad holds concealed this error. The new warning calculation covers this relationship without attaching or enforcing the exclusion.

**Later work:** investigate intake's request/follow-up distinction and separately evaluate containment for an unresolved allocation instruction with no order ID. An earlier proposal applied the two-message hold window to such an instruction. Since 15 October, warnings have replaced holds, so any new containment would be a warning or a dispatcher decision, not a hold. Missing identity alone does not prove that it is a follow-up: a blanket rule can hold unrelated independent requests. Holding must not silently merge tasks or invent an order ID.

**Check:** replay Test 6's saved state offline first. R14 must either receive the supported exclusion through a correct link or stay provisional (warned) until it is resolved. Also test an unrelated new request with no order ID and check which neighbouring tasks would be held. Compare full fields and holds, not only ready counts.

Evidence: Tests 5–6; [request routing](../order_processing_into_tasks/create_and_link_tasks.py); [verification and holds](../order_processing_into_tasks/verify_tasks.py). The original hold proposal was superseded by the implemented provisional-warning rule; the interpretation and exclusion-enforcement problem remains open.

## 2. Legitimate short replies are refused by linking

**Observed:** demo L0007, "For that we should focus a bit more on quality. It is pretty expensive.", goes to review with `gpt-4.1-mini`, Luna `medium`, and Luna `high`, despite the correct task being the only candidate. Blocker-file R09 ("Yes.") and R11 ("Normal priority. Cheapest feasible.") also fail to link. In Test 4, 25 link reviews had the correct task among the candidates.

**Cause status:** the saved payload proves the demo's candidate evidence was present. The link prompt's requirement for an explicit relationship and supporting quote is a supported explanation for the refusals, but a controlled prompt experiment has not yet established causality. Increasing effort to `high` also rejected demo L0003 and was reverted.

**Later work:** decide what contextual evidence is sufficient to attach a reply, and when the dispatcher must resolve it. A single candidate is not by itself proof of a relationship. Evaluate any prompt or deterministic linking change against both legitimate replies and the incorrect-link cases below.

**Check:** supported replies reach the right task, increment its version and invalidate earlier verification. Ambiguous replies remain reviewable without attaching to an unrelated task. Prompt changes require new paid calls; saved answers cannot demonstrate an improved prompt.

Evidence: Tests 3–5 and the follow-up diagnosis.

## 3. Some follow-ups attach to the wrong task

**Observed:** Test 1's Prompt 1 merged original-file R19 into R16's ORD-114 task and introduced a `fastest` preference that verification accepted. Test 4, with the current prompt/settings, again merged R19 into ORD-114 and recorded 8 wrong attachments out of 81 link calls. Three crossed conversation threads: R19, R148 and R196.

Extended-file R148's "Fastest workshop excluding QuickStitch" attached to the ORD-013 task from R135 rather than the ORD-122 task from R147. The other five wrong attachments went to separate tasks within the same intended conversation.

**Cause status:** the wrong attachments are observed. They do not establish one universal cause across intake labelling, candidate selection and the link decision. Trace each saved payload and answer before changing a rule.

**Later work:** improve continuation detection without inferring a relationship from a shared customer, product, order or nearby position alone. Preserve independent requests, including independent requests about the same order.

**Check:** retain R19 and the extended cross-thread cases as negative examples when improving short-reply linking. Verify the final task's evidence, preference and exclusions, even if its readiness value is unchanged.

Evidence: Tests 1 and 4; extended report, Appendix A.2. Prompt 1 should not be reintroduced as written; Prompt 2 has not been shown to outperform the current prompt.

## 4. Intake mistakes send valid work to batch review; cancellation safety is incomplete

**Status (15 October 2026): cancellations warn, not block; intake unchanged.** R21's intake review no longer holds R02. It warns R02 instead: Test 6's saved state gives R02 the warning L0021. The next run will verify R02, and if R02 is ready its recommendation will be marked provisional. A cancellation verified as an `unclear` task naming its order now warns that order's other requests in the same way. Cancellation confirmation and enforcement belong to the future dispatcher handler.

**Observed:** Test 4 rejected 6 intake batches covering 18 lines because an answer labelled a line containing an order ID as non-task. In Tests 5–6, blocker-file R19 and R22 were labelled non-task, causing R19–R21 and R22–R24 to enter intake review. Expected-ready R19 and R23 therefore have no task; their source messages remain recorded for review.

**Cancellation concern:** the rejected answer labelled blocker-file R21's cancellation of ORD-095 as a new request. R02 stayed held because the batch failed and its intake-review record named ORD-095. This run does not prove that a correctly accepted batch would apply the cancellation to the original request. R22's instruction that ORD-035 is not ready must also affect R24's later request.

**Established mechanism:** the order-ID coverage check correctly rejects the inconsistent extraction; the whole batch then enters review. Removing the check would admit the omission. Why the model chose non-task is not proven.

**Later work:** improve retention and labelling of order-bearing instructions, especially cancellations, pauses and short updates. Decide whether recovering valid siblings from a rejected batch is necessary only after measuring the remaining failures; do not weaken message coverage to increase throughput.

**Check:** valid requests survive intake, every message retains an outcome, and cancellations/pauses block the relevant order without relying on an unrelated batch failure. Include an accepted batch containing a cancellation, a pause before a later request, and unrelated work that should continue.

Evidence: Tests 4–6; extended report, Appendix A.1.

## 5. The two-message warning window still has scope limitations

**Status (15 October 2026): the window now chooses warnings, not holds; its limits remain.** A false association (R20 and ORD-036) now marks a task provisional instead of stopping its verification. A distant correction is still missed. `HOLD_WINDOW` keeps its name.

**Already improved:** broad unnamed-review holds were narrowed in the processing modules. Test 6 held 6 tasks instead of Test 5's 13. Replaying the rule on Test 4's saved state held 36 of 111 instead of 107; the released tasks were not all newly verified.

**Observed false association in the old hold flow:** blocker-file R20 is about ORD-005 but held the paused ORD-036 task, because R18 belongs to that task and falls within the two-message window. The same relationship now produces a warning. ORD-036 should require clarification anyway, so this case does not measure the damage to an otherwise ready unrelated task.

**Untested risk:** an unnamed correction referring more than two messages back may leave the affected task without a warning. Test 6 contains no such case and cannot establish its safety. Explicit order/message references use their referenced tasks, and warnings spread to other requests for the same order. Warnings themselves do not prevent allocation.

**Later work and check:** test interleaved conversations, multiple tasks in one message, distant corrections and unrelated nearby tasks. Decide the acceptable warning policy from that evidence. Keep this issue distinct from issue 1: R15 currently never enters the review path that applies this window.

Evidence: Test 6 limits and the 15 October hold-window engineering-log entry; [review target selection](../order_processing_into_tasks/extract_items.py).

## 6. Verification needs explicit decisions on intent, stage conflicts and conditional preferences

These are decisions to settle before prompt changes, not all proven model mistakes:

| Case in the original 30-request file | Recorded behaviour | Decision and later check |
|---|---|---|
| R07: order, quantity and deadline, but no action verb | Test 2 calls the intent unclear; the development key expects ready | Decide whether this form establishes an allocation request in this channel, then test comparable unseen wording. |
| R22: chat says ready to dispatch; CSV stage is WASHING | Test 2 asks for confirmation; the development key expects ready | Define the experiment's verification boundary and a separate deterministic live-status policy. Preserve the distinction from the historical harness. |
| R23: split only "if that gets it back faster" | Test 2 records a split and `fastest`; the key expects a split with no general preference | Decide whether the condition changes the whole objective. Allocation currently sends splits to review, so the field mismatch is not an observed committed wrong assignment. |

Original-file R28's unnecessary "Who has room this week?" clarification was an earlier mini-model failure and was correct in Test 2. Likewise, original-file R12's missing exclusion was corrected in Test 2. Retain them as regression cases rather than claiming they still fail under every current run.

Evidence: Test 2 and its pre-run verification key. The key is a development interpretation, not an official answer key.

## 7. Ordinal and relative delivery dates need deterministic handling

**Confirmed offline:** `read_date("30th October")` returns `None`, while "30 October" and "October 30" are understood. The demo contains this ordinal form. A correct link alone will therefore not make its deadline usable.

**Later work:** add deterministic support for the observed date form, preserving the written year and the requirement that a proposed deadline agree with its source evidence. Relative or ambiguous dates remain subject to clarification until a recorded reference date and supported resolution rule exist.

**Decision recorded, 18 October 2026:** wording such as "send out today/this week" must not override the delivery deadline. Preserve it as evidence; use the known order deadline unless the source explicitly specifies or changes delivery timing ("deliver by", "must be back by", or equivalent). Resolve clear relative delivery phrases in Python using the message's recorded date, or an explicit run reference for undated input. These fixtures define today as 1 April 2026; the computer's date is not their reference. State a week/month end-date policy before converting ranges into deadlines. A prompt-only date injection cannot fix the current Python parser/evidence rejection, and changed processing inputs may require paid verification. No processing change or paid test was made in this review. See [notebook 06 follow-up notes](../experimentation_notebooks/06-dispatcher-workflow.md#date-handling-past-deadlines-and-quantities-implemented-18-october-2026).

**Status, 19 October 2026:**
- **Implemented on 18 October:** the 18 October policy, including relative delivery words resolved in Python and `deadline_passed`.
- **Fixed on 19 October:** the two fallback faults found in review, with regression cases (`possible_deadline_words`). A dispatch-only clause no longer asks a deadline question, and an omitted relative delivery word now asks one.
- **Found by Test 7 and fixed the same day:** the date reader rejected a copied date that keeps its delivery word ("due Apr 13"), which blocked R25-R27. Python now reads the one written date inside the copy. Test 7's answers replay at 30/30 readiness with no API call ([prompt testing record](evaluation/PROMPT_TESTING_RESULTS.md), Test 7).
- **Still open:** ordinal dates such as "30th October" and slash dates such as "4/2".

**Check:** ordinal dates with and without a year, existing accepted formats, impossible dates and a proposed year differing from the source. Preserve the I04 year checks. This can be tested offline without a model call.

The demo also uses bare "52" rather than a complete order reference. Under current rules that requires identity clarification; do not silently normalize it or report the demo fully resolved after a date-parser change.

Evidence: Test 3; follow-up diagnosis, section 13; [date parsing](../order_processing_into_tasks/verify_tasks.py).

## 8. Evaluation can hide consequential errors and has limited repeatability evidence

**Observed measurement gap:** Test 6 reports "0 unsafe ready" because its existing key counts R14's missing exclusion as a field error. That label does not mean every ready task respects every instruction. Five tasks were marked ready, but only four matched all expected fields.

**Evidence limits:** most settings have one fresh run. Cached replays establish reproducibility and code behaviour, not model stability. Test 2's original 30 requests contain no follow-ups, and the development examples have already informed debugging and prompts. In Test 1, identical evidence received different mini-model verification outcomes in different batches; batch effects versus sampling variation were not isolated.

**Later work:** retain historical scores unchanged, but report readiness, field correctness, wrong links, missed tasks, holds and constraint-violating recommendations separately. Write expectations before new runs, reserve unseen cases, and obtain approval for fresh repeated samples. Record settings, input, costs and model time with each run.

**Check:** a missing exclusion or wrong merged preference must remain visible even when readiness matches the key. Evaluate decisions separately from explanations. Existing offline equivalence checks do not establish semantic accuracy or superiority over scheduling baselines.

Evidence: Tests 1, 2 and 6; [evaluation requirements](../../docs/project-plan.md#evaluation-and-evidence).

## 9. The extended chat needs a clearer evaluation purpose

**Observed:** from extended-file R31 onwards, 44 requests conflict with `orders.csv` and 5 name unknown orders. Correctly blocking these inputs must not be treated as failed readiness. The file is useful for conflict handling but cannot serve as a clean readiness benchmark for those requests.

**Later work:** preserve the existing file and key as recorded evidence. Decide whether to maintain a separate, consistent input set for successful processing and allocation. The blocker file already provides a smaller set with matching order facts, but covers only selected failure types.

**Check:** validate stated order facts before running a future readiness benchmark; label intentional conflicts and unknown orders separately. Keep unseen evaluation cases apart from examples used to tune prompts.

Evidence: Test 4 and the extended report's scoring key.

## 10. Model latency needs measurement after correctness is stable

**Recorded trade-off:** Test 2 took about 131 seconds of model time on the original 30 requests versus about 70 seconds for the earlier all-mini run, at roughly similar recorded cost. Luna verification averaged 9.4 seconds per call. Test 4 took 10 minutes 23 seconds wall time while verifying only 4 tasks because of broad holds.

**Later work:** measure the completed modular flow, including the extra verification work released by narrower holds. Establish the required response time before changing batch sizes, concurrency or models. Such changes can alter model context, cache matching and results.

**Check:** record wall time, stage time, paid calls and tokens alongside correctness on the same input. Keep software latency separate from the allocator's predicted manufacturing/delivery time. These historical timings are not a current performance guarantee.

Evidence: Tests 2, 4 and 6.

## 11. Processing stops on an API failure

**Priority: revisit after allocation modularization. Status: source-confirmed behaviour; no failure-handling change implemented.**

**What happens today:** `make_chat_model` sets `max_retries=0`. An exception during the model invocation is recorded with its error type/status and raised as an execution failure; `process_messages` stops. Previously saved checkpoints and answers remain available. This differs from an expected interpretation failure, which becomes a review record and allows processing to continue. No automatic retry or reprocessing loop exists.

**Why allowing allocation alone is insufficient:** all extraction and linking finish before verification starts. A failure during extraction or linking leaves no verified tasks in that run. An interruption during verification can leave earlier batches verified, which could support a useful partial preview.

**Proposed later change:** for selected recoverable API failures, retain the affected message/item/task IDs and source evidence, record a visible processing failure such as "API error; manual rerun needed", then continue with independent work. Keep this distinguishable from a question the dispatcher can answer about an order. File errors, programming errors and invalid credentials/configuration should remain execution failures. Decide which API failures permit continuation before changing the catch behaviour; do not convert every exception into ordinary review.

**Constraint to resolve:** a failed extraction or linking call may conceal a cancellation or restriction affecting another task. Any continuation policy must preserve the failed input and compute provisional warnings for potentially affected previews under the agreed policy. Merely recording a failed batch does not establish that neighbouring recommendations are safe to commit. Keep the targeting limitations in issues 1, 4 and 5 explicit; do not silently reintroduce automatic holds.

**Manual reruns and cost:** a saved answer is reused only when the full request fingerprint matches. Recovering a failed stage can change downstream payloads, so a rerun is not guaranteed to call only the originally failed requests. A proposed stop after three consecutive API failures would limit a consecutive failure streak, not total calls or spending; no threshold is selected here. Keep reruns manual.

**Offline checks before implementation is accepted:** inject one model-call failure separately at extraction, linking and verification. Check that every affected input is visible, potentially affected recommendations carry the agreed warnings, independent work continues where permitted, and no automatic retry occurs. Include a failed cancellation/correction and a failure in the last verification batch. Check that file/programming/configuration errors still stop visibly. Use a stubbed caller; no paid requests are needed to test this control flow.

Evidence: [model calls and cache](../order_processing_into_tasks/model_calls_with_cache.py), [processing sequence](../order_processing_into_tasks/processing_run.py), and [backend failure rules](../AGENTS.md). This review inspected source; it did not reproduce a live API outage. A future continuation policy requires an explicit update to those rules and matching tests.

## 12. Partial allocation previews need explicit accounting

**Status: implemented and verified offline on 15 October 2026.** `run_allocation.py` can plan a named saved checkpoint even when processing is incomplete. The plan stores `processing_complete: false`, prints warnings and retains each unfinished message, unlinked item and unverified task as `not_processed`. Reviews count as outcomes, not ready allocations. No separate completion file or old-folder backfill is used.

The normal full graph plans a run that finishes without an exception, including one marked incomplete. An API, file or programming exception stops the graph before allocation; it does not trigger automatic partial planning or continuation. Issue 11 remains a separate decision.

Warnings are recomputed from the current state whenever allocation runs. The former final-hold/checkpoint caveat and partial-state copy no longer apply. Processing files remain unchanged. Tests inject interruptions during extraction, linking and verification, check input accounting and partial labels, and confirm that a related failed assessment produces a provisional warning rather than removing an otherwise usable preview.

**Remaining boundary:** missing work can change duplicates, EDD order and tentative queues. Completeness is not interpretation accuracy. Evaluate complete runs consistently, retain provisional outcomes and coverage in reports, and report partial results separately. Dispatcher approval and reallocation are still future work.

## 13. Retain earlier allocation previews when rerunning

**Status: implemented and verified offline on 15 October 2026.** Allocation writes `plan.json` and an identical timestamped history copy from the same in-memory plan. Both contain `created_at` separately from `dispatch_date`. History names include microseconds and identify the objective plan; explicit-objective plans do not overwrite the default.

Tests check identical payloads, preservation of earlier copies, repeated saves within one second and objective separation. These are two file writes, not an atomic transaction. Ordinary file failures remain visible. No assignment database or automatic recovery framework is implied.

## Later application work already tracked elsewhere

These are planned capabilities or policy decisions, rather than fixes to bundle into allocation modularization:

- Persistent LangGraph clarification and approval waits are not needed for the file-based dispatcher prototype (notebook 06 Part 8). Consider them only if later requirements show a need.
- Move dispatcher resolution of the same task/version and approval from the notebook 06 prototype into the application, then add persistent assignments and reallocation. A preview must remain separate from a committed queue reservation. The decision table in notebook 06 Part 9 is the first contract for that API and the React dispatcher page.
- Resolve queue ownership, stale-preview checks, duplicate confirmations and transaction behaviour before live commits.
- Decide live order-status/calendar rules, chat-versus-CSV deadline reconciliation, the scope/expiry of standing workshop exclusions, and supported inputs for quality-sensitive work.
- Preserve the implemented harness adapter and recorded normal/shock comparisons; extend and repeat the frozen evaluation at final handover, preserving all six official metrics.

The detailed scope and acceptance cases remain in [Project plan](../../docs/project-plan.md) and [System design](../../docs/system-design.md). These support the Factory Primer's checks of workshop capability, capacity/queue feasibility and permission; no new architecture is selected by this backlog.

## How to resume this backlog

1. Preserve the 123-test offline baseline (20 October 2026) and current preview-only boundary; modularization, partial accounting, plan history, the graph's dispatcher review pause and the first API endpoints are complete.
2. Select the next scoped change with Aditya. API-failure continuation (issue 11) is still unimplemented and must not be confused with the completed partial-preview support.
3. Diagnose missing-instruction, cancellation and wrong-link cases from saved evidence. Provisional warnings expose risks; they do not resolve the underlying interpretation.
4. Evaluate legitimate short replies alongside negative examples so fewer reviews do not create more wrong attachments. Wider chronological context, a full-chat comparison or another model remain experiments, not agreed fixes. Change one factor at a time and obtain approval before paid calls.
5. Settle verification-policy questions, add supported ordinal-date parsing with offline evidence, and evaluate the resulting flow on fresh and unseen cases when authorized.
6. Record each established cause, change, verification, limitation and contribution in the engineering log and the relevant problem record. Cached completion alone does not establish a semantic fix.

Attribution: Aditya requested the backlog and made the modularization and provisional-preview decisions. Codex consolidated the original records and this documentation cleanup; the experiment and implementation records preserve their individual attribution. No new model run was made for this update.
