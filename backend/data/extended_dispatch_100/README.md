# Human team golden set: 100 dispatch tasks

Created 19 October 2026 for the SweaterCo Track 2 project. This is an additional synthetic development test set. It is separate from the professor's supplied data and the official historical harness benchmark.

AI custom-created the questions and dispatch requests after repeated project experiments, with several difficulty levels to emulate real-life dispatch situations and address weaknesses found in our intake, linking, verification and allocation. These are synthetic scenarios, not captured factory conversations.

**Three team members divided the work and comprehensively hand-reviewed the complete set, line by line. The review was performed by humans, not AI.** The returned workbook and the project owner's final clarifications were reconciled into the version 2 golden key on 21 October 2026. The initial questions and draft answers remain AI-authored; see the [review record](../../docs/evaluation/extended_dispatch_100_REVIEW.md) for the evidence and agreed changes.

There are **100 intended task cases across 149 messages**. With the reviewed correct interpretations, the existing deterministic allocator produces **85 on-time recommendations in one cumulative plan**. The other 15 are explicit exceptions. This establishes input feasibility. Model extraction, linking and end-to-end accuracy were measured later: in two paid runs on 21 October 2026 (Test 10), and in one on 22 October 2026 that also tested the dispatcher's review (Test 11). See the [evaluation summary](../../../evaluation/README.md). No paid model call was made to create or validate it.

## Files

| File | Purpose |
|---|---|
| [orders.csv](orders.csv) | 100 new synthetic order rows, ORD-201 to ORD-300, using the existing application schema. All are IN_PROGRESS at ASSEMBLY; completion fields are empty. |
| [workshops.csv](workshops.csv) | Byte-identical snapshot of the supplied eight workshop profiles. Existing capacity, queues, status, categories and batch caps are retained. |
| [dispatch_requests_extended_conversation_and_edge_cases_100.txt](dispatch_requests_extended_conversation_and_edge_cases_100.txt) | Matching conversational requests, corrections, short replies, interleaving and exception cases. |
| [Human-team golden key](../../docs/evaluation/extended_dispatch_100_human_team_golden.json) | Reviewed case-to-message relationships, final interpretation fields, expected outcomes and review provenance. Kept outside application inputs. |
| [Returned review workbook](../../docs/evaluation/extended_dispatch_100_human_team_review.xlsx) | The team's submitted review, preserved unchanged. |
| [Review record](../../docs/evaluation/extended_dispatch_100_REVIEW.md) | Three-member manual-review credit, reconciled notes and frozen file hashes. |
| Offline check (kept with the local notebooks, not published) | Checks source coverage, schemas, routing, eligibility, cumulative queues and repeatable previews without model calls. |

The application expects the names `orders.csv` and `workshops.csv` inside its configured data folder. The descriptive folder identifies this test set without changing application loaders. In this project, order rows are trusted source facts; tasks are the separate requests interpreted from chat.

## Scenario mix

| Cases | Scenario | Cases expected to receive recommendations |
|---|---|---:|
| 001-015 | Complete requests with varied wording | 15 |
| 016-030 | Preference supplied in a follow-up, including contextual replies | 15 |
| 031-045 | Confirmed preference, delivery-date or exclusion corrections | 15 |
| 046-059 | Interleaved requests with separate follow-ups | 14 |
| 060 | Complete request followed by acknowledgement | 1 |
| 061-069 | Relative delivery dates interpreted from the fixed message date | 9 |
| 070 | Dispatch timing leaves the CSV delivery date intact | 1 |
| 071-080 | Eligible destinations/exclusions, including exactly 300 pieces at W8's cap | 10 |
| 081-084 | Two independent jobs in each of two source messages | 4 |
| 085 | Short confirmation of a quality preference | 1 |
| 086-100 | Explicit exception cases, listed below | 0 |
| Total | 100 intended task cases | **85** |

The 149 messages contain 98 request messages, 45 follow-up messages and 6 non-task messages. Two request messages each contain two independent jobs, so 98 root messages represent 100 task cases. Message labels such as R017 and processing IDs such as L0017 refer to messages, not case numbers or order IDs. There are no header lines in the TXT to shift those IDs.

Expected exception outcomes:

- 2 `deadline_passed`: already due, or due on the dispatch date.
- 5 `review_required`: a future deadline no workshop can meet, a suspended destination, an incompatible destination, a batch exceeding W8's cap, and an unsupported split.
- 7 `needs_clarification`: unsupported budget, quantity mismatch, unconfirmed date change, unknown order, cancellation, pause, and missing order identity.
- 1 `reference`: a historical assignment question the provided data cannot answer.

ORD-296 and ORD-299 are present as source rows, but their corresponding scenarios deliberately name an unknown order and omit identity respectively. The unknown reference is ORD-9999. The quantity mismatch in CASE-094 is deliberate: 1,250 stated pieces versus 250 recorded pieces. Other written product, customer and quantity facts match their rows; obsolete dates in correction threads are explicitly superseded. These exceptions are separate from the 85 feasible cases.

## Offline verification

From `backend/`:

```text
uv run --offline --no-sync python experimentation_notebooks/testing/check_extended_dispatch_100.py
```

The check uses the expected interpretations as controlled fixtures. It does not run intake, linking, verification models, notebook processing cells or the full pipeline. Network connections are blocked during the check.

It confirms all 100 cases have source messages; the chat matches the frozen message map; all 85 recommendations obey workshop/request restrictions and their deadlines after earlier reservations; reviews reserve nothing; and repeating the same plan gives the same queues. It independently checks production, expected rework and delivery arithmetic. All seven active workshops receive work; suspended W7 receives none.

The 85% is a deliberate composition of this dataset. It is not an observed AI success rate, a claim of generalisation, or a replacement for official harness results. An LLM may still misread a feasible request. Evaluate any future model run against this unchanged key and record extraction/linking errors, false-ready results, correct automatic recommendations, appropriate reviews, cost and latency separately. Accept equivalent explicit non-allocation handling of the exception cases; the original wording and actual reason must remain visible. Unnecessary clarification on a feasible case is a miss.

## Team review of the answer key

Review is complete for the 100 cases and 149 messages. The [submitted workbook](../../docs/evaluation/extended_dispatch_100_human_team_review.xlsx) records approval/discussion statuses and human notes. The owner confirmed that three members divided the work and reviewed it manually, line by line. Individual reviewer-name and date columns were left blank; no names, dates or signatures have been invented.

The agreed reconciliation corrects 12 unstated preferences to `none`. No preference means the existing default, **minimize lateness**, unless another preference is explicitly stated. The owner explicitly confirmed that a delivery deadline alone is not a fastest preference. Message labels, case links, expected outcomes and intentional input traps remain unchanged. The nine case discussion flags and two message discussion flags are resolved in the [review record](../../docs/evaluation/extended_dispatch_100_REVIEW.md).

The active key is now `extended_dispatch_100_human_team_golden.json`, version 2. The original AI draft and blank-review template are preserved in the evaluation archive. Codex applied the human notes and owner decisions and ran consistency checks; those automated checks do not replace or constitute the team's human review.

## Settings for a future model test

The active `backend/config.toml` was left unchanged. If a separate model test is later authorized, use these values in its existing sections and restart the process/kernel so imported lookup dictionaries reload:

```toml
[input]
chat_file = "data/extended_dispatch_100/dispatch_requests_extended_conversation_and_edge_cases_100.txt"
data_folder = "data/extended_dispatch_100"
message_date = 2026-04-01

[output]
folder = "output/extended_dispatch_100"

[allocation]
dispatch_date = 2026-04-01
```

These are replacements for the matching existing settings, not a complete config file or extra duplicate sections. Retain the existing model and batch sections. The new IDs and messages will need new model answers, so processing is not authorized by the offline check. Use this chat and its matching CSV folder together. Do not use the old extended chat with these orders.

When displaying a future saved run in notebook 06, set its `DATA_FOLDER` to `BACKEND_DIR / "data/extended_dispatch_100"` and select the corresponding run. Its default order lookup folder otherwise points at the supplied data. Parts 1-7 can request new paid explanations on cache misses and have not been run for this set.

The snapshot date is **1 April 2026**, regardless of the computer's date. The allocator uses its existing elapsed-day estimates. This does not add a factory working-day calendar or a live status policy.

## Presentation wording

“AI custom-created our 100-case, 149-message test set after repeated project experiments. It contains questions and dispatch requests at several difficulty levels, designed to emulate real-life situations and target weaknesses in our system. Three members of our team divided the work and comprehensively hand-reviewed the set, line by line; this review was done by humans, not AI. We reconciled their comments into a golden answer key. Offline checks confirm that 85 cases can be allocated on time together and 15 test exceptions. In our better of two full runs, the app allocated 80 of the 85 correctly and held 14 of the 15 exceptions; one cancelled order was allocated, and a check for that is our top-ranked proposed fix.”

The observed results are reported separately, in the [evaluation summary](../../../evaluation/README.md) and the [full run report](../../docs/evaluation/GOLDEN_100_RUN_REPORT.md). Preserve this dataset and its prewritten answer key so those results can be reproduced. The professor's `harness/simulate.py`, supplied data and official metrics are unchanged. Aditya requested the test composition; Codex authored the synthetic inputs, expected interpretations and offline validation.
