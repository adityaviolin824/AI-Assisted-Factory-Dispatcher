# Targeted dispatch evaluation inputs

Created **4 November 2026** with AI assistance. These are newly authored synthetic development/stress scenarios based on known implementation boundaries. They have not been processed by a model, scored or reviewed by the human team. No passing result or held-out claim is established by adding or committing them.

## Files

| Input file | Messages | Focus |
|---|---:|---|
| [dispatch_linking_checks.txt](dispatch_linking_checks.txt) | 30 | Contextual follow-ups, interleaved senders, exclusions, preference/date corrections, questions and acknowledgements. |
| [dispatch_review_checks.txt](dispatch_review_checks.txt) | 24 | Suspended/incompatible/capped workshops, lateness, conflicting facts, unsupported constraints and clear control requests. |
| [dispatch_ambiguous_wording.txt](dispatch_ambiguous_wording.txt) | 24 | Missing identities, unclear referents, conditional requests, uncertain dates/quantities and dispatch-versus-delivery wording. |
| [dispatch_cancellation_and_correction_checks.txt](dispatch_cancellation_and_correction_checks.txt) | 26 | Cancellation, negation, later corrections, multiple orders in one message and workshop exclusions. |
| [dispatch_explanation_faithfulness_checks.txt](dispatch_explanation_faithfulness_checks.txt) | 18 | Reasons that preserve constraints, use actual calculations and distinguish missing facts from unsupported guarantees. |
| **Total** | **122** | Message count, not an order count or an accuracy denominator. |

Each file is a separate conversation; never concatenate them into one evaluation input. Repeated order IDs within a file are intentional. Some messages modify an earlier request, some ask questions and some contain multiple jobs. Cases/tasks must be annotated before a scored run; one line is not necessarily one task.

## Source records and dates

Use the existing [orders.csv](../orders.csv) and [workshops.csv](../workshops.csv) in `backend/data/`. This folder contains chat inputs only, so the configured `data_folder` remains `"data"`, not this subfolder.

The scenario's **message date and dispatch date are both 1 April 2026**. Creation on 4 November does not change that experimental snapshot. Explicit April/May delivery changes are deliberate and may differ from the order CSV. Clear control requests must still use the recorded quantities and obey eligibility, queues and feasibility; their eventual workshop choices have not been calculated here.

To select a file for a later authorised experiment, use its backend-relative path, for example `data/evaluation_scenarios_2026_11_04/dispatch_linking_checks.txt`, as the existing `input.chat_file` setting. Keep `input.data_folder = "data"`, `input.message_date = 2026-04-01` and `allocation.dispatch_date = 2026-04-01`. Existing settings are not changed by this addition. Use a fresh process for changed configuration and record the exact configuration used.

These remain historical planning inputs. They do not establish a live order-status policy, workshop booking, new speech capability or automatic interpretation of unsupported conditions.

## What to judge before scoring

Prepare a human-reviewed case/message map and expected outcomes before the first scored run. The points below are draft adjudication guidance, not a complete golden key or a record of human approval.

| Suite | Specific checks |
|---|---|
| Linking | R05 and R06 attach to their own senders' earlier requests despite interleaving. R14's W6 instruction for ORD-103 must not replace ORD-061's W6 exclusion. R11/R24/R30 supersede only the named date/preference. R28/R29 must not create duplicate allocations. |
| Review | R01/R02/R03 test status, category and cap rules. R04/R05/R06/R11 test late or passed deadlines without invented consent. R07/R08 test exclusions/conflicts. R12 must not overwrite CSV quantity. R16–R20 are clearer controls; cumulative queue feasibility still needs calculation. R21–R24 test unsupported facts/conditions. |
| Ambiguity | Missing identities and unresolved alternatives must not become guessed orders. R12's date format needs clarification. R17's forwarded relative date must not be anchored to the current snapshot without evidence. R03/R23 distinguish dispatch timing from delivery. R24 is a workshop exclusion, not a cancellation. A vague preference alone does not justify inventing a constraint. |
| Cancellation/correction | Possible cancellation wording is a reason for review, not an automatic saved cancellation. R04 tests negation; R07/R18/R23/R24 test later clarifications and known conservative-guard limits. R10/R19 test order ownership within one message. R05/R21 test workshop exclusions. R26 cannot silently clear an existing dispatcher cancellation; a separate review action is required. |
| Explanation | Judge the decision and its reason separately. Preserve exclusions, preference and actual deadlines. Cite the actual failed rule or recorded calculation. Cost per piece does not answer selling-price/transport questions; capacity does not provide a machine count; a current recommendation does not prove assignment history; low defect rate does not guarantee zero defects. |

The review TXT creates inputs for dispatcher review. It does **not** execute preview, correction, cancellation, approval or Review again. Those checks need separately recorded dispatcher choices or existing API/browser tests. Explanation inputs similarly do not establish measured explanation quality until actual reasons are judged.

## Later evaluation record

Before a paid run, obtain the usual approval and freeze the case key, input files, source CSVs, prompts, model settings and code version. Keep outputs outside these input files. Record the run ID, date, fresh/reused calls, costs, elapsed time and failures. Score interpretation/linking, decision correctness and explanation faithfulness separately, and retain unnecessary reviews and unsafe actions as failures where appropriate.

These visible, developer-authored challenge inputs support targeted diagnosis and regression work. If their outcomes inform fixes, subsequent scores on the same inputs are development/regression results. A claim of current-version held-out performance needs a separately reserved evaluation protocol and untouched cases.

## Preparation record

- **Purpose:** supply focused, reproducible chat inputs for the linking, review and difficult-language gaps identified while reviewing the final evaluation requirements.
- **Provenance:** AI-authored on 4 November 2026 using existing order/workshop records and known failure classes. Human adjudication remains outstanding.
- **Validation:** all five files (122 messages) passed formatting/order checks and loaded unchanged through the existing chat reader. Referenced order/workshop IDs, README links, named source quantities, W7's suspension, W8's 300-piece cap and W4's category were checked against the CSVs. These are input checks, not model-performance tests.
- **Source fingerprints (SHA-256):** `orders.csv`: `0880af9742fe7cc0923c5009e2de48a0bedb57b78cc294e35a1c9721fe0311f8`; `workshops.csv`: `d7e1c97d3d338a2b5aef8e35f167e3582f22c4526e9c736c5b4c8125505ec59e`.
- **Remaining work:** review the draft expectations, define case-level scoring and run authorised experiments. No application behavior, source CSV, supplied simulator, existing test set or default configuration is changed.
