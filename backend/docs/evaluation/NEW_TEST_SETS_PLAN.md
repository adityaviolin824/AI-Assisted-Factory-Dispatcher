# Synthetic test-set design and scoring

Design recorded 19 October 2026; human-review freeze 21 October; results recorded 21-22 October. This document defines the 100-case dataset and original scoring. It is a historical evaluation protocol, not a pending implementation plan.

## Status

- The synthetic dataset contains 100 intended cases in 149 messages, new orders ORD-201 to ORD-300 and byte-identical supplied workshop profiles.
- Three team members divided the work and comprehensively hand-reviewed every case/message. AI authored the initial scenarios and answers; automated reconciliation/checking is distinct from that human review.
- Version 2 of the golden key reconciles 12 unstated preferences to `none`. Labels, links and expected outcomes remain unchanged. See the [review record](extended_dispatch_100_REVIEW.md).
- Offline feasibility validation found 85 jointly on-time recommendations and 15 exceptions before scored model calls.
- Tests 10 and 11 subsequently completed three fresh automatic runs and a separate key-informed review. See the [recorded results](../../../evaluation/README.md).
- The supplied request, order, workshop and simulator files remain unchanged.

## Reproduction contract

Each test dataset has a chat TXT and a folder containing `orders.csv` and `workshops.csv`. Tests 10 and 11 temporarily selected that folder in `config.toml`, used separate output/cache folders and restored the default configuration by hash. A cache miss can make a paid call; every scored fresh run started with an empty cache.

The dataset [README](../../data/extended_dispatch_100/README.md) records the input settings. Keep original expectations and the scoring definitions fixed when reproducing historical results. Any stronger metric needs a separate version before scoring a new experiment. Local run outputs and the notebook-support feasibility checker are excluded from publication.

Input hashes at freeze: chat `942e2bc8...`, orders `7ecfe4a1...`, workshops `d7e1c97d...`, key `e8d861875b08cd9a...`. Full hashes and the returned human-review workbook are in the review record.

## Scoring scope

The allocation headline below checks recommendation presence and requested/excluded destinations. It does not require every interpreted field to match, so a lost preference can still count as allocated. Eligibility and timeliness were inspected separately in the recorded experiments. The later final-plan scorer checks approved rows and total quantity, but its coverage headline does not require timeliness/full field agreement and its split-part detail checks read only the main part.

## How the score works (fixed before the run)

- **Matching.** Each case is matched to the app task created from its first message. When that message holds two jobs (L0130 and L0131), the task whose excerpts name the case's order is used. The J number is not used, because it can change.
- **Decision (the headline):** for each case, whether it was recommended.
  - **Correct allocation:** recommended, the key says recommendation, and the workshop obeys the case's requested and excluded workshops.
  - **Correct non-allocation:** not recommended, and the key says exception.
    - Any explicit non-allocation counts, as the set's README says.
    - For example, the history question may come out as a clarification rather than a reference, and a cancellation may come out as an intake or link review.
  - **Wrong allocation (unsafe):** recommended, but the key says exception. CASE-094 (1,250 pieces stated, 250 recorded) is Test 8's R191 pattern.
  - **Missed allocation:** the key says recommendation, but the app did not recommend. Each one is listed with the app's reason.
- **Why each miss happened.** Each missed or changed allocation is put in exactly one class:
  - intake labelled its follow-up as a new request (this also sends both tasks to duplicate-order review);
  - its follow-up was not linked (link review);
  - verification blocked it, or read a field wrongly;
  - allocation: its own fields are right, but the plan differs. Usually a cascade, where an earlier task took the queue time: the key's plan has little slack in a few places (4 cases under 1 day, 16 under 3 days). It can also be another task naming the same order; the app's reason says which.
- **Workshop check.** For each recommendation, the selected workshop is compared with the key's own plan (the deterministic plan of the offline check). A difference points to a misread preference or date, or to a cascade.
- **Fields, labels and links:**
  - the five allocator fields of each case;
  - the 149 message labels;
  - whether each of the 45 follow-ups joined its case.
- **Counts:** messages, tasks, recommendations (provisional ones listed separately), reviews by reason, execution failures, cost and time.

## What this set does and does not test

It tests:
- allocation at volume: 85 tasks through one shared queue over seven workshops;
- follow-ups that change a preference, a deadline or an exclusion;
- interleaved threads, two jobs in one message, relative delivery words and dispatch timing;
- 15 exceptions, including the R191 quantity pattern.

It does not test these well:
- **Messy language.** The wording is templated: "Choose the fastest eligible workshop that meets delivery" recurs throughout. 37 of the 45 follow-ups name their order ID; only 8 rely on context (7 "For that batch", 1 "Yes"), the pattern that failed in Test 3.
- **Deadlines.** Every chat deadline equals its CSV due date. So if the model ignored a deadline, the app would fall back to the same date and the error would go unnoticed.

So its score is a best case for clean chat. The supplied 30 requests (traps) and the old extended chat (conflicts) remain the hard tests.

## The brief report (for teammates)

One file, `docs/evaluation/APP_PERFORMANCE_REPORT.md`, with one section per test set:
- what the set tests, and which files are sent with it;
- the provenance statement: "AI custom-created our test set after repeated experiments, with several difficulty levels to emulate real-life dispatch situations and target weaknesses in our system. Three team members divided the work and comprehensively hand-reviewed it line by line; this review was done by humans, not AI. Their notes and the documented preference rules were reconciled into the golden key before scoring." Include the reviewed scope and key hash. Refer to the review record for the documented review method/count and the absence of individual names/dates.
- one headline table: tasks, should allocate, allocated (correct / wrong), not allocated (correct / missed), and reviews by reason;
- the reasons for the misses, as classified above;
- a few lines of findings and limits, plus cost and time;
- paths relative to `backend/`, and no keys or machine-specific paths.

## The automatic run report (implemented 19 Oct)

`make_run_report.py` writes `run_report.md` into any run folder from the files the run already saves (`manifest.json`, `state.json`, `plan.json` and `calls/`). With `--key` and `--data`, it adds the score above. The [backend README](../../README.md#run-reports) describes it.

- **Why a script:** the same numbers are needed after every run, and counting them by hand from `plan.json` is slow and error-prone. It reads saved files only, so it is free and repeatable.
- **Alternatives rejected:**
  - a node in the LangGraph pipeline, which would not report older runs or runs planned again by `run_allocation.py`, and adds nothing to dispatch;
  - a notebook, which teammates cannot run on a new run folder with one command;
  - recording the data folder in `manifest.json`, which changes a function copied from notebook 05; the folder is named on the command line instead.
- **Assumptions:** the key has this set's JSON format; intake writes one excerpt per job, so a two-job message can be matched by order ID.
- **Checks:** 11 offline tests in `tests/test_run_report.py`, using a made-up run built from the key: a perfect run scores 85 correct allocations, 15 correct non-allocations, 149/149 labels and 45/45 links, and one fault per test gives the expected cause. On copies of the saved runs, the cost tables reproduce the recorded figures, such as $0.0705 for Test 8's 37 verification calls.
- **Older runs:** plans made before 15 October 2026 have no review warnings, so the report says the count was not recorded. A processing-only run has no plan, so the script asks for `run_allocation.py` first.

## Remaining evaluation work

The supplied 30-request key is AI-authored development evidence and needs documented human review before it is described as human-labelled. Separate explanation faithfulness, a new held-out result after tuning on known failures, stronger versioned scoring and real dispatcher effort remain to be measured. Renaming an older fixture is optional and does not change its historical results.
