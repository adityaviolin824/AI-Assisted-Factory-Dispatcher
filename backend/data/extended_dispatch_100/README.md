# Synthetic extended dispatch test: 100 tasks

Created 19 October 2026 for the SweaterCo Track 2 project. This is an additional synthetic development test set. It is separate from the professor's supplied data and the official historical harness benchmark.

There are **100 intended task cases across 149 messages**. With the authored correct interpretations, the existing deterministic allocator produces **85 on-time recommendations in one cumulative plan**. The other 15 are explicit exceptions. This establishes input feasibility; model extraction, linking and end-to-end accuracy have not been measured on this set. No paid model call was made to create or validate it.

## Files

| File | Purpose |
|---|---|
| [orders.csv](orders.csv) | 100 new synthetic order rows, ORD-201 to ORD-300, using the existing application schema. All are IN_PROGRESS at ASSEMBLY; completion fields are empty. |
| [workshops.csv](workshops.csv) | Byte-identical snapshot of the supplied eight workshop profiles. Existing capacity, queues, status, categories and batch caps are retained. |
| [dispatch_requests_extended_conversation_and_edge_cases_100.txt](dispatch_requests_extended_conversation_and_edge_cases_100.txt) | Matching conversational requests, corrections, short replies, interleaving and exception cases. |
| [Expected cases](../../docs/evaluation/extended_dispatch_100_expected.json) | Authored case-to-message relationships, final interpretation fields and expected outcomes. Kept outside application inputs. |
| [Offline check](../../experimentation_notebooks/testing/check_extended_dispatch_100.py) | Checks source coverage, schemas, routing, eligibility, cumulative queues and repeatable previews without model calls. |

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

Use the [editable team review workbook](../../docs/evaluation/extended_dispatch_100_team_review.xlsx) in Excel or import it into Google Sheets. It includes the original messages, all expected case fields, both source CSVs, and instructions. Share one working copy and divide the cases among reviewers.

1. In **Case review**, read each conversation and source order facts. Check the expected outcome and the fields to the right, including the deadline, preference and workshop restrictions.
2. In **Message review**, check each message's label and linked case IDs. Read neighbouring messages for contextual replies. Keep source text and stable IDs unchanged.
3. Edit the amber expectation cells directly and explain corrections in **Review notes**. Twelve exception cases have an unstated preference in the original key; these are flagged for review. Deliberate input conflicts, including CASE-094's quantity mismatch, must remain in the source data.
4. Choose **Approved** only after reviewing and correcting the row, and enter the reviewer's actual name and date. Use **Discuss** for unresolved questions. The workbook counts only approvals with a name and date.
5. Return the completed workbook so agreed edits can be applied to the JSON. It does not auto-sync. Resolve disagreements, validate case/message links, rerun the offline check, and record the reviewed key's hash, reviewers and date before scoring a model run.

Aditya's requested naming step: once the team-reviewed file is returned and its agreed corrections are applied and validated, rename the reviewed answer key to `extended_dispatch_100_human_team_golden.json` in `backend/docs/evaluation/`. Update the checker and documentation references together, retaining the AI-authored provenance and actual human review record. This is a pending step; the current draft key keeps its existing name.

The workbook starts with zero human sign-offs and preserves the original JSON values. Until review and reconciliation are complete, describe the labels as AI-authored draft expectations. Afterwards, use wording such as "AI-authored, reviewed and corrected by [actual names] on [actual date]" for the scope actually reviewed.

Record the division of review work through each row's reviewer name and date, covering the assigned cases and message links. Consolidate agreed corrections in one working copy. Once that review is complete, the presentation can say:

"We prepared the golden set by dividing review of an AI-authored draft among team members. Each reviewer checked assigned cases and message links, and the team consolidated the agreed corrections into a signed-off evaluation key before testing."

Use this completed-work wording only for the review actually performed, and retain the reviewer names, scope and dates as its evidence.

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

“We created an additional synthetic test set with 100 task cases and 149 conversational messages. We verified offline that 85 cases can receive valid on-time recommendations after accounting for shared queues. Fifteen cases test explicit exceptions. Model interpretation accuracy on this set has not yet been measured.”

After an authorized model run, report the observed results separately. Preserve this dataset and its prewritten answer key so those results can be reproduced. The professor's `harness/simulate.py`, supplied data and official metrics are unchanged. Aditya requested the test composition; Codex authored the synthetic inputs, expected interpretations and offline validation.
