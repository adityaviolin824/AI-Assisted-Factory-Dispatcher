# Human team golden set: review record

The active answer key is [extended_dispatch_100_human_team_golden.json](extended_dispatch_100_human_team_golden.json), version 2, reconciled and frozen on 21 October 2026.

AI custom-created the questions and dispatch requests after repeated project experiments. The set includes several difficulty levels, from complete requests to contextual replies, interleaved conversations, multiple jobs in one message and deliberate exceptions. The scenarios emulate real-life dispatch situations and target weaknesses found in intake, linking, verification and allocation.

**Three members of our team divided the work and comprehensively hand-reviewed the set, line by line. This review was performed by humans, not AI.** It covers all 100 task cases and 149 messages, including expected fields, outcomes, labels and case links. The project owner confirmed the review method, scope and three-member participation on 21 October 2026.

Codex then applied the review comments and the owner's final preference decisions and ran automated consistency checks. This reconciliation and checking are separate from the team's human review. The source questions and initial answers remain AI-authored.

## Preserved review evidence

- The [returned workbook](extended_dispatch_100_human_team_review.xlsx) is preserved byte for byte. Its source contents were not rewritten to manufacture signatures or approvals.
- It records 91 case rows as Approved and 9 as Discuss; 147 message rows as Approved and 2 as Discuss. The discussion notes are reconciled below and retained verbatim in the key's provenance.
- Reviewer-name and review-date columns are blank. No individual names, dates or signatures were invented. The three-person, line-by-line review is recorded from the project owner's confirmation; 21 October is the confirmation/reconciliation date, not an invented date for each person's work.
- The AI draft key and original review template are retained as history. They are not the active evaluation answers.

## Reconciled decisions

No expectation cells or message labels/links were directly edited in the returned workbook. The team recorded corrections in the review notes. These notes and the owner's subsequent decisions produce **12 preference corrections**, with all message labels, case links and expected allocation outcomes unchanged.

| Record | Resolution |
|---|---|
| CASE-087, 090, 092, 094, 095 | Apply the explicit note: preference becomes `none`. Preserve each case's existing exception and source facts. |
| CASE-091 | Preference becomes `none`. The order ID identifies the source row; its customer name need not be repeated in the chat. |
| CASE-096 | Preference becomes `none`. Keep the deliberately unknown `ORD-9999`, the written Apr 20 deadline and the clarification outcome. The reserved CSV row `ORD-296` is not the requested order and must not replace it. |
| CASE-088 | The reviewer suggested fastest. The owner explicitly chose `none`: the deadline already sets the delivery requirement and does not state a preference. |
| CASE-100 | Keep intent `question` and outcome `reference`: this asks about history, not a new allocation. Its message label `request` means a new task, which may be a question. Preference becomes `none`. |
| L0130, L0131 | Keep each message linked to its existing two cases. The human notes explicitly confirm the two independent jobs; no label or link correction is needed. |
| CASE-086, 098, 099 | These were marked Approved but also contained unstated preferences. Apply the owner's general clarification and set them to `none`. |

**Default rule:** when no preference is explicitly stated, record `none`. Python's existing default is `minimize_tardiness`: minimize lateness, then delivery time, then cost. An explicit preference is stored separately. No allocator policy or ranking code was changed during reconciliation.

The deliberate quantity mismatch, unknown/missing identities, suspended/incompatible workshops and other input traps remain unchanged. They are testing material, not errors to erase.

## Validation and freeze

The offline checker confirms **100 task cases across 149 messages**, with **85 jointly feasible on-time recommendations** and **15 exceptions**: 2 past deadlines, 5 reviews, 7 clarifications and 1 reference question. It also checks workshop eligibility, cumulative queue arithmetic and repeatability. This is dataset feasibility, not an observed AI accuracy score. No paid pipeline run has been made on this set.

From `backend/`:

```sh
uv run --offline --no-sync python experimentation_notebooks/testing/check_extended_dispatch_100.py
```

| File | SHA-256 |
|---|---|
| Golden key, version 2 | `e8d861875b08cd9a6a118891180081f38a5739fe47dd0e86c0e03f10575380a1` |
| Returned human-review workbook | `8f9c9ad7af67370e730461a97faec0bdacbd9eb6109d09e7a9ad91b8ad62b2ba` |
| Archived AI draft key, version 1 | `f4b2e9e9163f70360deb1c8deffba89184e32a5059acc989f5a491baa332579b` |
| Original chat | `942e2bc872cd9aefed065bc27c9497d5f5e4a931b59d87c501bed3166be1ddeb` |
| Orders | `7ecfe4a1110524c87caf3ae30c63b8be135de00c8da6b6bea85a4eca68fe3824` |
| Workshops | `d7e1c97d3d338a2b5aef8e35f167e3582f22c4526e9c736c5b4c8125505ec59e` |

Any later change to the expected answers must be reviewed, versioned and recorded before the affected model run is scored. Do not change the key merely to agree with model output.
