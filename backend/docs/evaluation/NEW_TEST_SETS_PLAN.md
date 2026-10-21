# Plan: our own test sets (written 19 Oct 2026, updated the same day)

Purpose: measure how well the app handles realistic and tricky chats, on data the team controls.

- The professor's files stay unchanged and remain the graded set: `data/dispatch_requests.txt`, `data/orders.csv` and `data/workshops.csv`.
- Not allocating a request that cannot or must not be allocated is correct behaviour, and the report scores it that way. Examples: wrong information, an unknown order, a past deadline, a forbidden workshop.

## Status

- **The first set is ready for review.** `data/extended_dispatch_100/` contains:
  - a README;
  - a 149-message chat;
  - `orders.csv`, with new orders ORD-201 to ORD-300;
  - `workshops.csv`, byte-identical to the supplied file.
- **Its key and check.** The key is `docs/evaluation/extended_dispatch_100_expected.json`. The offline check is `experimentation_notebooks/testing/check_extended_dispatch_100.py`.
- **Claude ran the offline check on 19 Oct, and it passes.** It found 100 cases in 149 messages, and 85 on-time recommendations in one shared-queue plan, plus 15 exceptions. SHA-256 hashes:
  - chat `942e2bc8...`;
  - orders `7ecfe4a1...`;
  - workshops `d7e1c97d...`;
  - key `f4b2e9e9...`.
- **Not done yet:** the old extended chat (`data/dispatch_requests_extended.txt`) has not been renamed.

## What the code already supports (no code change needed)

- **One folder per test set.** `config.toml` names the chat file (`[input] chat_file`) and a data folder holding `orders.csv` and `workshops.csv` (`[input] data_folder`). The set's README gives the exact settings, with output to `output/extended_dispatch_100/`.
- **The data folder setting is shared.** The module tests and the harness evaluation read the same `data_folder`.
  - While `config.toml` points at a test set, neither the tests nor the harness are run.
  - After every test run, `config.toml` is restored and checked by hash, as in Tests 7 and 8.
- **Every model call will be new and paid.** New CSVs change what intake and verification send to the model, so no saved answer is reused.
- **The renamed file.** `data/dispatch_requests_extended.txt` is named in four documents:
  - `docs/evaluation/EXTENDED_RUN_REPORT.md`;
  - `docs/evaluation/PROMPT_TESTING_RESULTS.md`;
  - `../docs/engineering-log.md`;
  - `../docs/follow-up-linking-diagnosis-2026-10-14.md`.

  After the rename, a "renamed to ..." note is added; past results are not rewritten.

## Ground truth: the existing JSON key, after human review

- **What the key holds.**
  - For each of the 100 cases: its messages (request or follow-up), the expected outcome, and the expected fields (order, due date, preference, requested and excluded workshops, split).
  - For each of the 149 messages: request, follow-up or non-task.
- **It replaces the table format proposed earlier.** It can be read by a script, and the offline check proves its allocations are feasible.
- **It was not labelled by humans.** Its README says that Codex, an AI assistant, wrote the inputs, the key and the check.
  - Before the report can say "the ground truth was labelled by humans", a person must review every case, fix what is wrong, and sign it off (name and date in the README).
  - Otherwise the report must say "written by an AI assistant, not yet reviewed by a human".
- **Found in Claude's read-only review (19 Oct), for the human reviewer to decide:**
  - 12 of the 15 exception cases have a preference that the chat never states: CASE-086, 087, 088, 090, 091, 092, 094, 095, 096, 098, 099 and 100.
  - Their values cycle fastest, cheapest, quality, which looks like a template; the chat implies `none`.
  - They change no expected outcome, but they would count as false field errors.
  - The preferences of all 85 allocatable cases agree with the chat.
- **After the review:** rerun the offline check, then freeze the key (record its hash and time) before the paid run.
- **Team division of work:** divide case and message-link review among members using the existing `extended_dispatch_100_team_review.xlsx` workbook. Record actual reviewer names and dates on the assigned rows, reconcile agreed corrections in one copy, and retain that evidence. Once the completed review is returned, apply and validate the changes, rename the reviewed key to `extended_dispatch_100_human_team_golden.json`, and update references together. Completion and sign-off remain pending.

## Steps

| Step | Who | Paid? | What |
|---|---|---|---|
| 1 | Team | no | Rename the old extended file. The first new set is done. |
| 2 | Team | no | Divide the cases and message-link checks among reviewers using the existing team-review workbook. Correct the expectations, record names and dates, reconcile disagreements and sign off the reviewed scope. |
| 3 | Claude | no | Rerun the offline check, freeze the key, and run a preflight with a blank API key to count the calls. |
| 4 | Team | - | Approve one paid run. (The piece-count check was added on 19 Oct.) |
| 5 | Claude | yes | Make one run of `run_full_pipeline.py` with the README's settings. Then restore `config.toml` and check it by hash. |
| 6 | Claude | no | Score the run: `uv run python make_run_report.py <run folder> --key <key> --data data/extended_dispatch_100` writes `run_report.md` into the run folder. |
| 7 | Claude | no | Write the brief report, and record the run as a new test in `PROMPT_TESTING_RESULTS.md`, as `AGENTS.md` requires. |

**Estimate for step 5,** from the per-call costs of Tests 4 and 8:
- about 50 intake, 45 link and 34 verification calls;
- roughly $0.10-0.20, and 12-15 minutes.

The preflight gives the exact number of calls.

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

So its score is a best case for clean chat. The professor's 30 requests (traps) and the old extended chat (conflicts) remain the hard tests.

## The brief report (for teammates)

One file, `docs/evaluation/APP_PERFORMANCE_REPORT.md`, with one section per test set:
- what the set tests, and which files are sent with it;
- a statement of who wrote and reviewed the ground truth that matches what actually happened. After the divided team review is completed, use: "We prepared the golden set by dividing review of an AI-authored draft among team members. Each reviewer checked assigned cases and message links, and the team consolidated the agreed corrections into a signed-off evaluation key before testing." Include actual reviewer names, reviewed scope, dates and the key's hash. Until that work is returned and reconciled, keep the human-review status pending.
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

## Open decisions for the team

1. **The R191 piece-count check before the run: done (19 Oct).**
   - `stated_piece_counts` in `verify_tasks.py` blocks a task whose evidence writes a piece count for its order that differs from `orders.csv`. A static scan flags CASE-094's message (R142) and no other line of this set.
   - Tested offline (76 tests) and by replaying Tests 7 and 8 with no API call; see Test 8 in `PROMPT_TESTING_RESULTS.md`.
2. **Who reviews the key,** and the exact wording of the ground-truth statement.
3. **The professor's 30 requests in the report.**
   - The existing keys for them (Tests 7 and 8) were written by the AI assistant.
   - They need the same human review before the report calls them human-labelled.
4. **Names.** The new name of the old extended file, and of any later test-set folders.
