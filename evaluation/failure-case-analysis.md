# Failure case analysis

Evidence reviewed **4 November 2026**. This catalogue assembles **18 individually analysed development and evaluation failures** for the final evaluation report. It uses dated investigations, recorded model runs, current source and targeted offline checks. Analysis and documentation used AI assistance; this is not a new human annotation study.

These are 18 case studies across the application's development, not 18 new failures on one evaluation set. Eleven have implemented code fixes, one improved in a later recorded model configuration, one has a conservative mitigation, and five have no recorded semantic fix. Historical model failures do not establish how often the current configuration would fail on new answers.

## Evidence and counting rules

- A failure has an identifiable input or action, an expected behavior and an observed deviation. A correct refusal of an unsupported request is not a failure.
- Related examples with the same mechanism are grouped. CASE-046/047/051 illustrate one intake failure class; CASE-019/023/027 illustrate one linking failure class. They are not used to inflate the count.
- Code defects, model interpretation failures and remaining operational risks have different evidence. Risks without a recorded occurrence are listed separately and are not counted among the 18.
- For model behavior, the established cause can be the failed stage and its returned fields. The model's internal reason is generally unknown. Prompt wording and context presentation are hypotheses unless a controlled comparison isolates them.
- A passing regression test shows the checked code behavior. A saved-answer replay checks deterministic behavior using old model answers. Neither establishes fresh model accuracy or held-out performance.
- Original source labels such as `R25`, processing IDs such as `L0025`, task IDs and golden-set case IDs are different identifiers. They are paired explicitly below.

## Case index

| ID | Failure | Evidence period | Status at this review |
|---|---|---|---|
| F01 | Overlapping chat windows produced duplicate records | 6–7 October | Code fix implemented; historical evidence and current ownership checks inspected |
| F02 | Deadline parsing discarded an explicit year | 12–13 October | Code fix implemented; focused tests passed now |
| F03 | Supplied request R12 lost a workshop exclusion | 13–14 October | Later recorded configuration corrected this case; no universal model fix established |
| F04 | Unresolved follow-ups prevented verification and left stale holds | 15 October | Code/policy fix implemented; focused tests passed now |
| F05 | A correctly copied date with “due” became an unnecessary question | 19 October | Code fix implemented; focused tests passed now |
| F06 | A chat/CSV quantity conflict became a silent recommendation | 19 October | Code guard implemented; focused tests passed now |
| F07 | An accepted dispatcher destination was silently unused | 23 October | Code fix implemented; focused tests passed now |
| F08 | Complete ignored the dispatcher's earlier corrections | 22 October | Code fix implemented; focused test passed now |
| F09 | A successful Send could erase the next draft | 22 October | UI fix and recorded regression; test/source inspected, browser test not rerun here |
| F10 | Changes made during approval were lost | 22 October | UI fix and recorded regression; test/source inspected, browser test not rerun here |
| F11 | A non-finite queue report broke subsequent workshop reads | 3 November | Validation fix implemented; focused API test passed now |
| F12 | Workshop sign-in could not retry a failed list read | 3 November | UI fix and recorded regression; test/source inspected, browser test not rerun here |
| F13 | A cancelled golden-set order was recommended | 21–24 October | Conservative mitigation implemented; focused tests and a residual boundary checked now |
| F14 | A contextual follow-up lost its preference | 21–22 October | Observed in saved runs; semantic linking fix not recorded |
| F15 | A follow-up became a duplicate allocation request | 21–22 October | Observed in saved runs; semantic intake fix not recorded |
| F16 | A fabricated evidence pointer blocked valid work | 21–22 October | Safe rejection works; model-output/recovery problem remains |
| F17 | A comma made dispatch timing look like a deadline | 21–22 October | Observed in saved runs; current helper behavior reproduced now |
| F18 | A normal on-time requirement became an unsupported constraint | 21 October | Observed in one run; later runs passed, with no proven fix |

For a compact report, F01, F02, F04–F08 and F13–F17 provide twelve substantial cases spanning processing, calculation boundaries, review and current semantic limitations. F03 supplies an additional direct example from the official 30 requests. F09–F12 add user-interface and workshop reliability evidence. The full catalogue can be retained as supporting material; the evaluation report should include at least ten individual analyses rather than only this index.

## F01. Thirty source messages became 48 records

- **Expected and observed:** each source message should be extracted once, while retaining separate jobs within one message. In the early overlapping-window design, 30 messages appeared 48 times. Consolidation retained the 18 overlap repeats, and copies could receive different verification outcomes.
- **Established cause:** five-line windows advancing three lines repeatedly supplied the same sources. Acceptance did not enforce target ownership. Exact-object/description deduplication failed because repeated versions differed; model consolidation did not remove them. Missing prompt/run metadata prevents attributing the saved output to a particular edited prompt.
- **Response and verification:** intake was redesigned around owned target messages, with earlier messages supplied only as context. Python checks coverage, repeated items and source quotations. The dated investigation records the failure; the current `owned_windows` and `validate_intake` implementation was inspected. No historical-version replay was made in this audit.
- **Remaining limit:** preventing repeated extraction does not establish whether two different messages describe one task. F14/F15 show that semantic linking remains separate.
- **Sources:** [development notes, case 1](../experiments/development-notes.md#1-thirty-messages-became-48-records), [6 October investigation](../docs/engineering-log.md#2026-10-06-comprehensive-deduplication-investigation), [current extraction checks](../backend/order_processing_into_tasks/extract_items.py).

## F02. A written 2027 deadline was accepted as 2026

- **Expected and observed:** a controlled assessment cited “Please allocate ORD-061 by April 2, 2027” but proposed April 2, 2026. The earlier verifier accepted the wrong year and marked it ready.
- **Established cause:** the month-first date pattern could end before the explicit year. `read_date` then supplied the default year before comparing dates. This was a deterministic parsing defect, independent of the model's proposed answer.
- **Response and verification:** the pattern now captures complete dates, including years, and the proposed date must match its evidence. The 13 October log records twelve repair cases and before-fix failures. The current `Deadlines` tests passed in this audit, including rejection of a shortened date drawn from explicit 2027 evidence.
- **Remaining limit:** yearless dates still use the configured dataset year. This is the historical experiment's convention, not a general live-calendar policy.
- **Sources:** [development notes, case 2](../experiments/development-notes.md#2-a-deadline-lost-its-written-year), [repair record](../docs/engineering-log.md#2026-10-13-simplify-notebook-05s-storage-repair-i03-and-i04-and-document-it), [deadline tests](../backend/tests/test_processing_modules.py), [date reader](../backend/order_processing_into_tasks/verify_tasks.py).

## F03. Supplied request R12 silently lost “nothing new to QuickStitch”

- **Input and expectation:** R12 in the supplied [dispatch_requests.txt](../backend/data/dispatch_requests.txt) requests ORD-053 and says “Boss says nothing new to QuickStitch this week, they're swamped.” Under the prewritten interpretation, W1 must be excluded from this request.
- **Observed and cause evidence:** the all-mini run `2026-10-13_19-32-08`, task `T:L0012:J1`, was ready with `excluded_workshops: []` and no blocker. This audit read that saved state directly. The numerical allocator cannot enforce a restriction missing from its structured input; the observed failure is in interpretation, not the arithmetic.
- **Response and verification:** the later all-Luna run `2026-10-14_14-40-08` records `excluded_workshops: ["W1"]`, also confirmed directly. The experiment report records prompt/model comparisons. Those observations establish improvement on this case; they do not isolate every contribution of the changed configuration or guarantee future exclusion accuracy.
- **Remaining limit:** describe this as a silent restriction loss in a historical configuration. Do not claim W1 was actually assigned on this evidence alone.
- **Sources:** [Test 2 comparison and R12 analysis](../backend/docs/evaluation/PROMPT_TESTING_RESULTS.md#test-2-every-stage-on-luna-current-prompt-14-oct-2026), [current normalized-rule enforcement](../backend/task_allocation_to_workshops/workshop_rules_and_estimates.py).

## F04. An unresolved “Yes” left a request unverified

- **Input and expectation:** the blocker conversation's R07 asks to place ORD-108; R08 asks “Speed priority?”; R09 answers “Yes.” Uncertain linking should retain the original request's established facts for review.
- **Observed and cause evidence:** the investigation of saved run `2026-10-15_21-19-26` found that R08 became a separate task, linking refused R09, and a nearby-message hold kept `T:L0007:J1` out of verification. Removing only the unresolved-link record from a diagnostic copy did not clear its stored `related_review`. The linking payload already contained the relevant messages, so missing access to them did not explain that refusal.
- **Response and verification:** persistent holds were replaced by recomputed provisional warnings; uncertainty no longer prevents verification of established evidence. The recorded audit replayed fourteen saved states and mutation-checked the warning rules. Current `PossiblyAffectedTasks` tests passed, including `test_a_review_does_not_stop_verification`.
- **Remaining limit:** the old run was not present at the expected path during this audit; its before-fix evidence is the dated investigation. The code fix does not solve the short reply's semantic linking or retroactively verify old saved tasks.
- **Sources:** [detailed investigation and solution](../backend/problems_solved/held_tasks_and_unresolved_followups.md), [implementation record](../backend/debugging/held-tasks-never-verified.md), [current verification tests](../backend/tests/test_processing_modules.py).

## F05. “due Apr 13” was rejected although the date was explicit

- **Input and expectation:** supplied R25, ORD-109, explicitly says “due Apr 13.” The selected evidence should yield 2026-04-13. R26/R27 are related instances of the same defect and are not separate counted failures.
- **Observed and cause evidence:** Test 7's verifier copied `due_date_text` with the delivery word, while `read_date` accepted only a bare date. R25–R27 therefore asked to confirm an explicit date. This audit read their saved task records in `2026-10-19_10-34-52` and confirmed the unnecessary blocker.
- **Response and verification:** `resolve_scheduling` now extracts a single written date from a copied phrase and still checks it against the full evidence date. Multiple dates or a wrong year remain guarded. The dated test-first repair and saved-answer replay restored readiness on these three rows; current `Deadlines` tests passed.
- **Remaining limit:** the recorded 30/30 readiness replay used the same model answers. It does not establish 30/30 performance on fresh answers, and the report retained a separate field disagreement.
- **Sources:** [Test 7 and its date-fix replay](../backend/docs/evaluation/PROMPT_TESTING_RESULTS.md#test-7-a-fresh-run-after-the-18-and-19-october-deadline-changes-19-oct-2026), [date-resolution source](../backend/order_processing_into_tasks/verify_tasks.py), [deadline tests](../backend/tests/test_processing_modules.py).

## F06. A 1,300-versus-200 quantity conflict reached allocation

- **Input and expectation:** extended-chat R191 describes ORD-105 as 1,300 vests for Bright Basics. The order CSV records 200 hoodies for Cotton Club. This discrepancy must require review rather than silently planning a different batch.
- **Observed and cause evidence:** Test 8 marked the task ready despite the order lookup being in its verification payload. The saved plan, inspected here, recommends W3 for `T:L0193:J1` using ORD-105's CSV facts. R191's source label and L0193's file position differ. The model missed the conflict, and no deterministic piece-count guard then prevented readiness.
- **Response and verification:** `stated_piece_counts` now blocks a written count that differs from the identified order's CSV quantity. The dated replay changed the unsafe recommendation to clarification while retaining the other recommendations. Current `PieceCounts` tests passed, including the recorded 1,300/200 pattern.
- **Remaining limit:** this is a quantity guard, not a complete semantic validator for customer/product identity. CSV quantity is not overwritten by processing; an explicit dispatcher correction is a separate action.
- **Sources:** [Test 8 and piece-count replay](../backend/docs/evaluation/PROMPT_TESTING_RESULTS.md#test-8-the-extended-chat-on-the-current-code-19-oct-2026), [piece-count tests](../backend/tests/test_processing_modules.py), [current guard](../backend/order_processing_into_tasks/verify_tasks.py).

## F07. A saved dispatcher destination was not used

- **Action and expectation:** the dispatcher chooses W1 for a known-order clarification or split row, then finalizes. The destination must be used under the dispatcher-override contract, with its consequences recorded, or the action must be explicitly refused.
- **Observed and cause evidence:** the 23 October audit reproduced accepted and saved `choose_workshop` entries for `T:L0005:J1` and `T:L0023:J1`, while both rows remained unresolved without a workshop or change entry. Only allocation-ready tasks reached the choice logic, and the recommendation function stopped unsupported/split tasks before making estimates.
- **Response and verification:** `derive_task` now records processing flags overridden by a destination/Complete action and makes an identified batch plannable. An unknown order is refused. The log records four tests failing first; all four focused choice/split/known-order checks passed in this audit.
- **Remaining limit:** unchecked provisional warnings can still prevent final approval. That is explicit review behavior, distinct from silently dropping a destination.
- **Sources:** [reproduction and cause](../docs/engineering-log.md#2026-10-23-pipeline-audit-open-issues-with-evidence), [fix record](../docs/engineering-log.md#2026-10-23-the-dispatchers-chosen-workshop-overrides-what-processing-left-open), [current derivation](../backend/dispatcher_review/dispatcher_plan.py), [controlled decision tests](../backend/tests/test_dispatcher_review.py).

## F08. Complete ignored earlier saved corrections

- **Action and expectation:** after correcting a request's order to ORD-041, Complete should use that corrected order. Completing a request previously corrected to a question should turn it into the intended allocation.
- **Observed and cause evidence:** the earlier implementation asked for the order again in the first case and left the second as a reference/question. `complete` checked the original verified task instead of merging its saved dispatcher facts.
- **Response and verification:** it now builds `corrected = {**task, **entry.get("facts", {})}` before checking identity and intent. The 22 October log records both failures. `test_completing_a_request_uses_its_saved_corrections` passed in this audit and checks both branches.
- **Remaining limit:** passing this test establishes the saved-correction contract for the controlled cases, not successful recovery of every failed processing record. F16 has a separate recovery limitation.
- **Sources:** [22 October review fixes](../docs/engineering-log.md#2026-10-22-review-fixes-after-step-5), [Complete implementation](../backend/dispatcher_review/dispatcher_decisions.py), [regression test](../backend/tests/test_dispatcher_review.py).

## F09. A successful Send erased text typed while waiting

- **Action and expectation:** a worker submits a request and starts another draft while the save response is delayed. Text shown as editable must not silently disappear.
- **Observed and cause evidence:** a recorded browser proof typed “ Also ORD-062.” during a held send; it appeared and then disappeared when the response ran `setText("")`. The textarea remained editable while the request was outstanding.
- **Response and verification:** the composer uses `readOnly={sending}` while preserving focus. The alternative of clearing only an unchanged draft was considered but complicated failed-send messaging and submission-ID ownership. The log records a failing test before the repair. Current source and the test “while a message sends, its text box cannot change” were inspected.
- **Remaining limit:** the browser test was not rerun in this audit. It uses a controlled backend response; it is not a real-device speech or transcription evaluation.
- **Sources:** [22 October review fixes](../docs/engineering-log.md#2026-10-22-review-fixes-after-step-5), [composer](../frontend/components/Composer.tsx), [chat regression](../frontend/tests/chat.spec.ts).

## F10. A dispatcher edit made during approval was lost

- **Action and expectation:** after starting Approve all, the dispatcher changes a workshop choice while the response is delayed. The interface must not accept an edit that the outstanding approval request cannot contain and then silently replace it.
- **Observed and cause evidence:** the choice and added-batch forms stayed enabled during the save. The changed value was absent from the request and was overwritten by the returned saved plan. The recorded regression failed because the controls were enabled.
- **Response and verification:** both forms now sit in disabled fieldsets while `approving` is true, covering initial approval and Review again. Current fieldsets and the test “while Approve all runs, the choices cannot be changed” were inspected; its response is deliberately held before checking the controls.
- **Remaining limit:** the browser regression was not rerun here. Locking these controls does not provide concurrent-dispatcher conflict handling.
- **Sources:** [22 October review fixes](../docs/engineering-log.md#2026-10-22-review-fixes-after-step-5), [dispatcher page](../frontend/app/dispatcher/page.tsx), [review regression](../frontend/tests/review.spec.ts).

## F11. A non-finite queue report broke later reads

- **Input and expectation:** a workshop report supplies `NaN` or `Infinity` as days of work booked. Invalid queue values should be refused without changing shared reports.
- **Observed and cause evidence:** the 3 November review found that Python's JSON reader accepted these values, the report was saved, and later `GET /workshops` responses failed. Negative-value checks alone did not exclude non-finite floats.
- **Response and verification:** `save_report` now checks `math.isfinite(queue_days)` before saving. The current API regression submits raw JSON for both values, checks 422 and verifies no reports file was created. That focused test passed in this audit.
- **Remaining limit:** valid concurrent report writes can still race; this validation fix does not establish concurrent-write safety. That risk is documented separately rather than counted as an observed incident.
- **Sources:** [3 November review pass](../docs/engineering-log.md#2026-11-03-workshop-reports-used-from-the-next-dispatch-run), [report validation](../backend/task_allocation_to_workshops/workshop_updates.py), [API regression](../backend/tests/test_workshop_updates.py).

## F12. Workshop sign-in could not retry a failed first read

- **Action and expectation:** the first workshop-list request fails; selecting Workshop again should permit another read and allow sign-in after recovery.
- **Observed and cause evidence:** the role stayed selected after failure, so choosing it again did not trigger the change handler. A single failed read left the user stuck. A sleeping backend is one possible trigger, not an observed outage established by this test.
- **Response and verification:** failure now clears the selected Workshop role and shows an explicit retry instruction. Current source and the browser regression were inspected. The log also documents a test-harness mistake: Playwright `check()` expected the role to remain selected even though the failure deliberately cleared it. Clicking for that first attempt corrected the test; the recorded repeated check then passed 30/30.
- **Remaining limit:** no browser test or hosted retry was rerun here. The historical 30/30 figure concerns that controlled retry test, not hosted availability or model accuracy.
- **Sources:** [3 November review pass](../docs/engineering-log.md#2026-11-03-workshop-reports-used-from-the-next-dispatch-run), [sign-in handler](../frontend/app/sign-in/page.tsx), [retry regression](../frontend/tests/workshop.spec.ts).

## F13. Golden CASE-097 was recommended despite cancellation

- **Input and expectation:** golden R145/L0145 says “The customer has cancelled ORD-297. Do not allocate or reserve workshop capacity for this order.” Expected handling is non-allocation pending dispatcher resolution.
- **Observed and cause evidence:** all three historical fresh runs marked it as an allocation without a blocker and recommended W1. This audit read each saved plan/state and confirmed that outcome. No deterministic cancellation wording check then prevented readiness; valid numerical allocation could therefore act on a wrong interpretation.
- **Response and verification:** the 24 October change added a conservative readiness blocker plus an explicit dispatcher `cancel` action. The recorded Test 11 replay reused all 128 answers and held 15/15 exceptions, with zero unsafe allocations and 81/85 expected allocations. Current `Cancellations` tests passed, including the embedded Test 11 assessment. The replay is not a new model run.
- **Current failure boundary:** this audit confirmed `cancellation_words("Do not cancel ORD-045. Allocate it as planned.", "ORD-045")` returns `["cancel"]`. Negation can therefore cause unnecessary review. Superseding instructions and multi-order scope retain documented limits. The guard never automatically cancels an order.
- **Sources:** [golden failures](../backend/docs/evaluation/GOLDEN_100_RUN_REPORT.md#every-failing-case-with-its-proof), [Test 11 cancellation replay](../backend/docs/evaluation/END_TO_END_TEST_2026-10-22.md#11-follow-up-replay-24-october-2026-the-cancellation-check), [current guard/tests](../backend/tests/test_processing_modules.py).

## F14. Golden CASE-019 lost a contextual cheapest preference

- **Input and expectation:** R023/L0023 requests ORD-219 and says its preference will follow. R024/L0024 says “For that batch, Choose the cheapest eligible workshop that meets delivery.” The key expects one request with preference `cheapest`.
- **Observed and cause evidence:** in both Test 10 runs and Test 11, L0024 stayed in link review. In Test 10 run 1 the task needed clarification; in run 2 and Test 11 it became a provisional W5 recommendation with preference `none`. These stored outcomes were checked directly. The relevant earlier task was among the link candidates, so missing candidate access does not explain this specific refusal.
- **Response and verification:** provisional warnings expose the unresolved evidence; the key-informed dispatcher corrected the preference in Test 11. Neither is an automatic semantic linking fix. Context presentation/prompt strictness remain possible explanations, not a proven internal model cause.
- **Remaining limit:** CASE-023/027 have the same mechanism and are supporting instances. Broad allocation coverage can count these preference losses as correct, so field/link metrics and dispatcher effort must be reported separately.
- **Sources:** [golden linking analysis](../backend/docs/evaluation/GOLDEN_100_RUN_REPORT.md#every-failing-case-with-its-proof), [public run-2 row and field comparison](golden_100_run_2_report.md), [Test 11 review decisions](../backend/docs/evaluation/END_TO_END_TEST_2026-10-22.md#4-the-dispatchers-choices), [candidate selection](../backend/order_processing_into_tasks/create_and_link_tasks.py).

## F15. Golden CASE-046's follow-up became a duplicate request

- **Input and expectation:** R080/L0080 requests ORD-246 with “Preference to follow”; R082/L0082 says “ORD-246: Choose the fastest eligible workshop that meets delivery.” The key expects a follow-up attached to the existing task.
- **Observed and cause evidence:** in both Test 10 saved states, L0082 was labelled `request`. It therefore created another task instead of entering linking, and duplicate-order review withheld the allocation. This audit confirmed both labels and outcomes. The report associates the problem with complete-sounding follow-ups whose original request was in context rather than the new-message portion; prompt causality was not independently isolated.
- **Response and verification:** duplicate-order review prevented double allocation but increased human work. CASE-046 linked and allocated in Test 11 without a demonstrated semantic fix; the same intake mechanism affected CASE-026/051 there.
- **Remaining limit:** this is run-to-run variation, not evidence of a stable repair. CASE-047/051 and the additional run-1 examples are grouped under this mechanism, not counted separately.
- **Sources:** [golden intake/batch comparison](../backend/docs/evaluation/GOLDEN_100_RUN_REPORT.md#every-failing-case-with-its-proof), [Test 11 before review](../backend/docs/evaluation/END_TO_END_TEST_2026-10-22.md#3-before-the-review), [request/follow-up handling](../backend/order_processing_into_tasks/create_and_link_tasks.py), [duplicate-order routing](../backend/task_routing/route_verified_tasks.py).

## F16. Golden CASE-049 returned an evidence ID outside its catalogue

- **Input and expectation:** ORD-249's R085/L0085 request and R087/L0087 follow-up establish a valid request with normal priority. Every returned evidence pointer must refer to its supplied catalogue.
- **Observed and cause evidence:** verification produced a doubled task prefix, such as `T:L0085:J1:J1:E1`, rather than an available catalogue ID. All three saved states retain the processing-review reason “Selected evidence must belong to this task's supplied catalog.” The payload was valid; the invalid pointer was in the model output.
- **Response and verification:** the deterministic membership guard correctly refused the answer. In Test 11 the key-informed dispatcher added a replacement batch because decisions could not name the failed-verification task. The original failed row remained unresolved beside that replacement.
- **Remaining limit:** safe rejection is successful containment of an output failure, with a usability cost. A shorter-ID proposal and improved failed-task recovery were not implemented or evaluated by this audit. Do not call the guard itself a defect.
- **Sources:** [golden evidence-pointer failure](../backend/docs/evaluation/GOLDEN_100_RUN_REPORT.md#every-failing-case-with-its-proof), [Test 11 choices and unresolved rows](../backend/docs/evaluation/END_TO_END_TEST_2026-10-22.md#4-the-dispatchers-choices), [evidence membership check](../backend/order_processing_into_tasks/verify_tasks.py), [review task lookup](../backend/dispatcher_review/dispatcher_decisions.py).

## F17. Golden CASE-070's comma created a false deadline question

- **Input and expectation:** R119/L0119 says “Send out ORD-270, 360 vest pieces for Cotton Club today. Keep the delivery due date in the order record.” Today describes dispatch; the stored delivery deadline should remain applicable.
- **Observed and cause evidence:** all three saved plans put the case in clarification. `CLAUSE_BREAK` includes commas, separating “Send out ORD-270” from “…today”. The latter fragment has a time word without a dispatch word and is treated as possible delivery evidence.
- **Current reproduction:** the helper returns `["today"]` for that text. Removing only the comma after ORD-270 makes it return `[]`. This comparison was executed during the audit, confirming the documented punctuation-sensitive mechanism. It is a helper reproduction, not a full pipeline rerun.
- **Response and remaining limit:** Test 11 used a key-informed Complete decision to recover the batch. The suggested sentence-level interpretation change remains unimplemented; it would need controls for a real delivery date inside a dispatch sentence. It must not simply suppress every date near a dispatch word.
- **Sources:** [golden failure](../backend/docs/evaluation/GOLDEN_100_RUN_REPORT.md#every-failing-case-with-its-proof), [independent pipeline audit](../docs/engineering-log.md#2026-10-23-pipeline-audit-open-issues-with-evidence), [current date-word helper](../backend/order_processing_into_tasks/verify_tasks.py).

## F18. Golden CASE-032's normal on-time requirement became a blocker

- **Input and expectation:** R052/L0052 requests the lowest defect rate among eligible on-time workshops; R053/L0053 confirms delivery Apr 21, replacing May 4. The key expects a quality preference and a normal feasibility check.
- **Observed and cause evidence:** Test 10 run 1 put “Use only workshops that can complete the order on time.” in `unhandled_constraints`, making the request unnecessarily unclear. This audit read that stored field directly. The deterministic code honored the supplied blocker, so the observed error is the verifier's classification of an already supported condition.
- **Response and verification:** the same case was recommended at W4 in Test 10 run 2 and Test 11, with no extra constraint. A prompt clarification was proposed; no controlled semantic fix is recorded.
- **Remaining limit:** the later successes show variability, not remediation. Asking for help was conservative, but it was still unnecessary dispatcher work on a feasible case under the frozen key.
- **Sources:** [golden failure analysis](../backend/docs/evaluation/GOLDEN_100_RUN_REPORT.md#every-failing-case-with-its-proof), [human-reviewed key](../backend/docs/evaluation/extended_dispatch_100_human_team_golden.json), [constraint/readiness handling](../backend/order_processing_into_tasks/verify_tasks.py).

## Current limitations that must not be invented as observed incidents

- **Concurrent workshop reports:** saving reports reads and rewrites one file without a transaction. Lost concurrent writes are a code-level risk; no such incident was established in the reviewed record.
- **Concurrent calculations for different runs:** `use_run_workshops` mutates shared planner records. Interleaving a preview with another run's planning could mix values. This audit did not execute a concurrency reproduction, so this is a remaining risk, not a nineteenth observed failure.
- **Operational boundaries:** no authentication, temporary hosted storage and no live workshop booking are declared scope limitations. They are not automatically failed test cases. Separate hosting also does not establish scaling or high availability.
- **Evidence gaps:** real-speech accuracy, measured human review time, separate systematic explanation grading and current-version held-out performance remain unestablished. An unmeasured capability is not a fabricated negative result.

## How targeted dispatch files can extend this evidence

Five development/stress inputs were created in local commit `205ae54` on 4 November, then removed by commit `90d1979` during this audit. They are not present in the current working tree, and this audit does not restore them or claim that they ran. The table below preserves their intended coverage as a planning record. No extra dataset is needed merely to reach ten documented failures. If new inputs are introduced later, review their case expectations before scoring and add a failure entry only after recording an actual deviation.

| Earlier draft filename | Relevant catalogue cases and future checks |
|---|---|
| `dispatch_linking_checks.txt` | F14/F15: R01–R06 test contextual linking and interleaving; R11/R24/R30 test corrections; R28/R29 test non-duplicating acknowledgements. |
| `dispatch_review_checks.txt` | F06/F07/F13: quantity conflict, constrained destinations and cancellation. Preview/approval/Review again still require separately recorded dispatcher actions. Correct rule-based refusals are expected successes. |
| `dispatch_ambiguous_wording.txt` | F05/F17: inspect timing/date interpretation; R03/R23 are controls. The exact comma defect already has the golden CASE-070 input. Missing identities must not be guessed. |
| `dispatch_cancellation_and_correction_checks.txt` | F13: R04 tests negation; R07/R18/R23/R24 test later clarifications; R10/R19 test multi-order scope. |
| `dispatch_explanation_faithfulness_checks.txt` | F03/F14/F16: compare reasons against actual restrictions, evidence and missing facts. Judge decisions and explanation faithfulness separately. |

Such inputs are informed by known weaknesses. A later score on them is not automatically held-out evidence. Preserve the distinction between development cases, regression replays and a genuinely reserved evaluation set. The supplied, extended, blocker and golden-set inputs used by the observed cases remain separate evidence sources.

## Verification performed for this catalogue

**Fresh checks on 4 November:** 18 existing backend tests passed, with no model calls, plus the two direct helper comparisons reported in F13/F17. No runtime fix, new model answer, frontend browser run, deployment or dependency installation was made.

From `backend/`, the focused test command was:

```sh
PYTHONPATH=tests UV_CACHE_DIR=.uv-cache uv run --offline --no-sync python -m unittest \
  test_processing_modules.Deadlines \
  test_processing_modules.PieceCounts \
  test_processing_modules.Cancellations \
  test_processing_modules.PossiblyAffectedTasks \
  test_dispatcher_review.ControlledDecisions.test_completing_a_request_uses_its_saved_corrections \
  test_dispatcher_review.ControlledDecisions.test_a_choice_overrides_what_processing_left_open \
  test_dispatcher_review.ControlledDecisions.test_a_split_request_takes_the_dispatchers_batches \
  test_dispatcher_review.ControlledDecisions.test_completing_a_split_request_plans_it \
  test_dispatcher_review.ControlledDecisions.test_a_choice_without_a_known_order_is_refused \
  test_workshop_updates.Routes.test_refusals_save_nothing -v
```

The tests protect model access and use temporary files. Some dispatcher tests depend on local saved runs/notebooks excluded from the public repository; the command is not a promise that those fixtures exist in a clean checkout.

**Read-only artifact inspection:** the source states/plans of all three golden runs were available and checked for CASE-019/032/046/049/070/097. Original R12 was checked in both the all-mini and all-Luna saved states. Test 7's R25–R27 state and Test 8's R191 state/plan were also inspected. The older held-request run was unavailable at its recorded path, so F04 explicitly relies on its dated investigation. No source run was regenerated or edited.

These local run folders are excluded from publication. Public evidence is supplied by the linked reports, published run-2 table, frozen key, regression sources and engineering records. This catalogue does not claim that every historical failure was reproduced from the historical code version or that every documented fix received a fresh model evaluation.
