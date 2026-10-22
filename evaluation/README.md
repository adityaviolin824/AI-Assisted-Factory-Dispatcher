# Evaluation

This folder explains what was tested, where the data and scores are, and the recorded results on our 100-case test set. Backend data, answer keys and scoring code remain in their existing locations; the links below provide one place to find them.

Two separate things were evaluated, and their results are kept apart:

1. **The scheduling rules**, on the 120 historical orders, with the supplied simulator (`harness/simulate.py`, unchanged). This measures allocation only, with the six official metrics.
2. **The whole chat-to-allocation flow**, on a 100-case test set scored against a human-reviewed answer key. This measures whether the app reads a conversation correctly and then allocates safely.

## Where everything is

| What | Where |
|---|---|
| Harness comparison of the allocation policies | [Scheduling benchmark](../backend/eval_harness/results/harness_results_2026-10-15.md) |
| Test set inputs: the chat, `orders.csv` and `workshops.csv` | [100-case dataset](../backend/data/extended_dispatch_100/README.md) |
| Golden answer key (version 2, frozen before the model runs) | [Human-reviewed answers](../backend/docs/evaluation/extended_dispatch_100_human_team_golden.json) |
| The team's returned review workbook, unchanged | [Review workbook](../backend/docs/evaluation/extended_dispatch_100_human_team_review.xlsx) |
| Review record: who reviewed, what changed, file hashes | [Review evidence](../backend/docs/evaluation/extended_dispatch_100_REVIEW.md) |
| Full report of both runs, with failure analysis and charts | [Run comparison and findings](../backend/docs/evaluation/GOLDEN_100_RUN_REPORT.md) |
| Run 2: every plan row with its reason | [Detailed run 2 results](golden_100_run_2_report.md) |
| Log of every paid test run (Test 10 covers these runs) | [Experiment history](../backend/docs/evaluation/PROMPT_TESTING_RESULTS.md) |
| Earlier notebooks and selected debugging records | [Development experiments](../experiments/README.md) |
| Scoring code | [Report command](../backend/make_run_report.py) and [scoring modules](../backend/eval_run_report/) |

The detailed run 2 report is an unchanged copy of the generated report for run `2026-10-21_23-43-53`. The original run folder is excluded from version control; paths inside the report are recorded relative to `backend/`. Its "Key's own description" preserves the key's frozen text from before testing. The offline feasibility checker and saved regression snapshots are kept locally rather than published here.

## 1. The scheduling rules (harness)

The default policy was compared with choosing a random eligible workshop on the 120 historical orders. The six official metrics are reported unchanged.

| Normal historical replay | Mean days | p90 days | Late | Defective | Cost | Maximum workshop share |
|---|---:|---:|---:|---:|---:|---:|
| Random eligible workshop | 21.5 | 45.6 | 34% | 4% | 111,780 | 23% |
| Default policy: reduce lateness | 8.1 | 13.7 | 2% | 6% | 115,360 | 25% |

The simulator needs a workshop for every batch, so when every option is late the evaluation adapter picks the least-late one; the app itself sends such a case to the dispatcher. The other policies, the shock replay and the assumptions are in the [full comparison](../backend/eval_harness/results/harness_results_2026-10-15.md).

## 2. The 100-case test set

### How it was made

AI custom-created the test set after repeated project experiments, at several difficulty levels. It was built for two purposes:

- **To emulate real-life dispatch conditions:** varied wording, preferences given in a later message, corrections, several conversations interleaved, relative dates such as "by the end of next week", and two jobs in one message.
- **To target weak points we had seen in our own application:** follow-ups that only make sense with the earlier message, corrections that replace an earlier instruction, dispatch timing ("send out today") that must not become a delivery date, a stated piece count that differs from the order record, and requests that break a workshop rule.

**Three team members then divided the work and hand-reviewed the complete set, line by line. This review was done by humans, not AI.** Their notes and the project owner's final clarifications were reconciled into the version 2 answer key on 21 October 2026, before any model run. The [review record](../backend/docs/evaluation/extended_dispatch_100_REVIEW.md) keeps the evidence and the agreed changes.

The set has 100 task cases in 149 chat messages: 98 request messages (two of them hold two jobs each), 45 follow-ups and 6 messages that are not tasks. The 100 synthetic orders (ORD-201 to ORD-300) use the app's normal order format, and the eight workshops are the supplied ones, unchanged.

| Cases | Scenario | Should be allocated |
|---|---|---:|
| 001-015 | Complete requests with varied wording | 15 |
| 016-030 | Preference given in a follow-up, including "For that batch, ..." replies | 15 |
| 031-045 | Corrections to a preference, delivery date or exclusion | 15 |
| 046-060 | Interleaved requests with separate follow-ups; an acknowledgement | 15 |
| 061-070 | Relative delivery dates; dispatch timing that keeps the order's due date | 10 |
| 071-085 | Eligible destinations and exclusions, two jobs in one message, a short confirmation | 15 |
| 086-100 | Exceptions that must not be allocated | 0 |
| **Total** | | **85** |

### Why only 85 of the 100 orders should be allocated

The 15 exceptions test when the app must hold a request rather than recommend a workshop. Holding an exception with a visible reason scores as correct. Recommending a workshop for one scores as **unsafe**.

The supplied Factory Primer says three questions must be answered before any batch goes anywhere: **can the workshop make it, can it take it now, and is it allowed to**. Six exceptions fail the deadline or one of those questions. The other nine are requests the app must not act on without a person, or are not dispatch requests at all.

| Case | What the message says (shortened) | Why it must not be sent | Expected outcome |
|---|---|---|---|
| 086 | ORD-286: "Delivery was due Mar 31." | The deadline has already passed | deadline passed |
| 087 | ORD-287: "Delivery is due today, Apr 1." | Due on the dispatch date | deadline passed |
| 088 | ORD-288: "Deliver tomorrow, Apr 2." | Can it take it now? No workshop can finish in time | dispatcher review |
| 089 | ORD-289 to OldMill (W7) | Is it allowed to? W7 is suspended | dispatcher review |
| 090 | ORD-290, hoodies, to Little Loom (W4) | Can it make it? W4 makes accessories only | dispatcher review |
| 091 | 500 vests to FreshStart (W8) | Is it allowed to? W8 is on trial: at most 300 pieces | dispatcher review |
| 092 | "Split the batch equally between two workshops." | Splitting an order is not supported | dispatcher review |
| 093 | "Total production cost must not exceed 100." | A money budget is not a supported condition | needs clarification |
| 094 | ORD-294: 1,250 pieces; the record says 250 | The quantity conflicts with the order record | needs clarification |
| 095 | "The customer might move delivery to Apr 10." | The date change is not confirmed | needs clarification |
| 096 | ORD-9999 | The order does not exist | needs clarification |
| 097 | "The customer has cancelled ORD-297." | The order is cancelled | needs clarification |
| 098 | "Pause ORD-298 ... do not allocate." | Production is paused | needs clarification |
| 099 | "The blue sweaters for the usual customer." | No order is identified | needs clarification |
| 100 | "Which workshop handled ORD-300 last year?" | A history question; the data has no history | reference |

- **Deadline passed:** the row is shown to the dispatcher with no estimate and reserves no queue time.
- **Dispatcher review:** the dispatcher decides; nothing is reserved meanwhile.
- **Needs clarification:** the app asks for the missing or conflicting fact.
- **Reference:** an information question with nothing to allocate.

An offline check using the key's expected interpretations confirms that all 85 allocatable cases fit on time in one plan. This establishes the dataset's feasibility, not an observed model success rate.

### How a run is scored

Each case is matched to the task the app created from the case's first message. A case that should be allocated is **correct** when the app recommends a workshop that obeys every workshop rule and meets the deadline. A different workshop from the key's own plan is not an error, because earlier tasks can take queue time in a different order. A case is **missed** when the app sends it to a person instead. The rules are fixed in "How the score works" in [NEW_TEST_SETS_PLAN.md](../backend/docs/evaluation/NEW_TEST_SETS_PLAN.md), and the expectations were written down and hashed before the runs.

### Recorded results: run 2 (21 October 2026)

The table records run `2026-10-21_23-43-53`. Both model runs used the same inputs and settings and started with empty answer caches. The [run comparison](../backend/docs/evaluation/GOLDEN_100_RUN_REPORT.md) documents their results and variation.

| Measure | Result |
|---|---|
| Eligible, on-time recommendations | **80 of 85** |
| - every field matches the key | 77 |
| - a stated preference was lost (flagged provisional) | 3 |
| Missed (sent to a person) | 5 |
| Exceptions correctly held | **14 of 15** |
| **Unsafe allocations** | **1** (CASE-097, a cancelled order recommended to W1) |
| Workshop-rule or deadline violations among recommendations | 0 |
| Chat messages labelled correctly | 145 of 149 |
| Follow-ups joined to their task | 35 of 45 |
| Plan rows needing a person (ideal: the 15 exceptions) | 30 |
| Model calls, cost, time | 128 calls, $0.0700, 10 min 1 s |

The recommendations met workshop eligibility and deadline rules, but one was still unsafe because the order was cancelled. The recorded failures included incorrect intake labels, missed links, a verification error and a Python date check:

| Case | What happened |
|---|---|
| **097** | **Unsafe.** Verification read the cancellation as an allocation request, and no Python check blocks a cancelled order. |
| 046, 047, 051 | Missed. "ORD-x: Choose the fastest eligible workshop..." was read as a new request, so two tasks named one order and both went to review. |
| 049 | Missed. Verification returned a malformed evidence ID, so Python sent the task to review. The safety check worked as designed. |
| 070 | Missed. Python's written-date check splits at commas, so "...for Cotton Club today" was read as a possible deadline and the app asked for a date. |
| 019, 023, 027 | Allocated, but "For that batch, choose the cheapest..." was not linked, so the preference was lost and the rows were flagged provisional. |

### Planned fixes (proposals, not implemented)

1. **A Python cancellation and pause check** to block cases such as the cancelled order. It can be tested offline by replaying saved answers.
2. **A sentence-level date check** to address CASE-070. It can be tested the same way.
3. **An intake prompt clarification** for messages that only add a preference to an existing request. Testing a prompt change requires new model calls.

These changes remain proposals. No improvement is claimed until it is tested.

### Limits

- The chat is synthetic and its wording is templated, and every chat deadline equals the order's due date. Results on these inputs do not establish performance on messy factory conversations.
- Two runs show that run-to-run variation exists, not how large it is. A case that passed here can still fail in another run.
- This set measures interpretation and safe allocation. It does not replace the harness's official metrics.
