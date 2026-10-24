# End-to-end test of the whole application (Test 11, 22 October 2026)

Historical experiment record: the results below describe the implementation at the run date. A conservative possible-cancellation/hold guard and a dispatcher `cancel` decision were subsequently added on 24 October; they do not revise these scores. [Section 11](#11-follow-up-replay-24-october-2026-the-cancellation-check) records a free replay of this run's saved answers with that change. See the [current implementation](../../README.md).

**Recorded result: key-informed review covered every expected case.** One fresh paid run took the 100-case golden set through processing, allocation and the pause for the dispatcher. A simulated dispatcher who knows the answer key then reviewed it through the app's HTTP API.

| Stage | Correct allocations (of 85) | Exceptions not allocated (of 15) | Unsafe | Approved rows of no case |
|---|---|---|---|---|
| Before the review (Test 10's scorer) | 81 | 14 | 1 (CASE-097) | - |
| Approve all with no choices | 67 | 14 | 1 (CASE-097) | 0 |
| **After Approve all with 23 choices** | **85** | **15** | **0** | **0** |
| **After Review again** | **85** | **15** | **0** | **0** |

- After the review, every allocation has every field matching the key and is on time.
- The paid run cost $0.0757 for 128 calls and took 9 min 23 s. The review made no model call.
- This is a historical regression baseline. Its frozen coverage headline is separate from timeliness/full field agreement; split-part detail checks currently inspect only the main part. The record separately reports all 85 allocations on time with matching fields.

**What the "after" numbers mean.** They show what the app can reach when the dispatcher knows every right answer. They are not model accuracy, and not the effort of a real dispatcher: here the dispatcher had the key. The "before" row is the measure of the model and Python on their own.

## 1. Experiment objective and scope

- Add a score for the table after the dispatcher's review.
- Run one fresh paid run of the whole application. The protocol permitted a second run only if materially necessary; no third run was permitted.
- Do the dispatcher's work: correct inputs, allocate, Approve all, then reallocate with Review again.
- Record the performance before and after the review in this file.
- The target was complete case coverage after review: every case the key allocates is allocated, and none of the others is.
- Do not change the main logic of the app.

## 2. What was done, step by step

**Rules frozen before the run.**
- The rules, the expectation and the dispatcher's method were written into [the testing results](PROMPT_TESTING_RESULTS.md) ("End-to-end test with the dispatcher's review") before any paid call. That section's SHA-256 is `0a041b0f14bbecef...`, and it was unchanged after the run.
- The two new scoring files were frozen at the same time:
  - [`eval_run_report/final_plan_score.py`](../../eval_run_report/final_plan_score.py): `86154af0d6579ee4...`;
  - [`eval_run_report/key_informed_choices.py`](../../eval_run_report/key_informed_choices.py): `1061573f4a650dda...`.
- The key (`e8d861875b08cd9a...`) and the inputs (chat `942e2bc8...`, orders `7ecfe4a1...`, workshops `d7e1c97d...`) matched their frozen hashes before and after.

**Rehearsal, with no model call.** Before any paid call, the scorer and the choice builder were run on a scratch copy of Test 10's run 2. One Approve all with 24 choices gave 85 of 85 and 15 of 15 there. The rehearsal found no problem in either tool, and nothing in the app was changed.

**Step 1: the paid run.**
- `config.toml` was backed up and set as for Test 10:
  - chat: `data/extended_dispatch_100/dispatch_requests_extended_conversation_and_edge_cases_100.txt`;
  - data: `data/extended_dispatch_100`;
  - a new output folder, `output/end_to_end_test_2026-10-22`, so the cache was empty.
- Settings, checked in the printout: every stage on `gpt-5.6-luna`, intake at `high`, linking and verification at `medium`. Batches are 3 target and 2 context messages, with 3 tasks per verification. The dispatch date is 2026-04-01.
- `uv run python run_full_pipeline.py` ran once, from 22:30:59 to 22:40:22. It made 128 calls; all were paid and none failed. The plan was complete, and the run paused for the dispatcher.
- Run folder: `output/end_to_end_test_2026-10-22/runs/2026-10-22_22-31-00`.
- As in Test 10, the run was traced to LangSmith, because `.env` enables tracing.

**Step 2: score before the review.** `make_run_report.py <run> --key ... --data ...` wrote `run_report.md` into the run folder, using Test 10's rules unchanged.

**Step 3: the review, through the HTTP API.**
- The API was started with `uv run fastapi run main.py --host 127.0.0.1 --port 8765`, so it was reachable only from this computer, and stopped afterwards. `main.py` does not load `.env`, so nothing from the review was traced.
- Every request and response is saved in `output/end_to_end_test_2026-10-22/test11/`. The calls, in order:
  1. `GET /reviews/{thread_id}`: the first review, saved as `first-review.json`.
  2. `POST /reviews/{thread_id}/preview`, with the 23 choices (Check workshop options): accepted, 59 rows change.
  3. `POST /reviews/{thread_id}/finalize`, with the same choices (Approve all): finished, 85 approved, the same 59 changes. The app saved `dispatcher-plan.json` and `dispatcher-decisions.json`, revision 1.
  4. `POST /runs/{run_id}/preview`, then `/finalize` (Review again): the builder found nothing to fix, so both were sent with no choices. Nothing changed; revision 2 was saved.
- No answer was refused, so the choice builder never needed a fix.

**Step 4: score after the review.** `score_dispatcher_review.py` scored the first review as Approve all with no choices would approve it, then revision 1, then revision 2.

**Step 5: restore.**
- `config.toml` was restored, and its SHA-256 matches the backup (`920d4f7f...`).
- The run's `manifest.json`, `state.json` and `plan.json` hash the same as before the review.
- `output/runs/` (266 files) and Test 10's runs are unchanged.

**Second paid run: not made.** The first run completed with no failed call and could be scored. A second run would only measure run-to-run variation again, which Test 10 already showed, and would not change the main result: what the review can fix.

## 3. Before the review

From `run_report.md`, by Test 10's rules. A provisional recommendation counts as allocated there.

| Measure | This run | Test 10 run 1 | Test 10 run 2 |
|---|---|---|---|
| Correct allocations (of 85) | **81** | 73 | 80 |
| - with every allocator field matching the key | 78 | 71 | 77 |
| - provisional | 14 | 10 | 15 |
| Missed | 4 | 12 | 5 |
| Exceptions not allocated (of 15) | 14 | 14 | 14 |
| Unsafe allocations | 1 (CASE-097) | 1 (CASE-097) | 1 (CASE-097) |
| Labels | 146/149 | 140/149 | 145/149 |
| Follow-ups joined | 36/45 | 30/45 | 35/45 |
| Correct allocations at the key's own workshop | 64/81 | 61/73 | 61/80 |

**What went wrong**, from the run report. These are the same patterns as in Test 10:
- **CASE-026 and CASE-051 (intake):** a follow-up was read as a new request, so two tasks named one order and both went to duplicate-order review.
- **CASE-049 (verification):** verification returned an evidence ID outside the task's catalog, so the task went to processing review.
- **CASE-070 (verification):** Python's written-date check split "Send out ORD-270, ... today" at a comma and asked which date applies.
- **CASE-097 (unsafe):** "The customer has cancelled ORD-297. Do not allocate..." was verified as an allocation and recommended to W1.
- **Linking:** the 7 "For that batch, ..." follow-ups and L0109 went to link review again. Three of those cases (CASE-019, 023 and 027) lost their "cheapest" preference.

**Approve all with no choices** would approve only 67 of the 85. The 14 provisional rows stay unresolved until the dispatcher checks their warnings, and CASE-097 is still approved.

## 4. The dispatcher's choices

The choice builder is a test tool, not part of the app. It reads the key, which no real dispatcher has, and writes decisions in the form the dispatcher page sends; the app's endpoints check, apply and plan them. Its rules are in the docstring of `key_informed_choices`. For Approve all it wrote 23 decisions:

| Decision | Rows | Why |
|---|---|---|
| `warnings_checked` | 15: ORD-216 to 219, 221 to 229, 259 and 260 | The provisional rows' fields match the key, so the unresolved rows their warnings name do not change them. ORD-226's row also carried a warning. |
| `correct` preference `cheapest` | ORD-219, ORD-223, ORD-227 | Their "For that batch, cheapest" follow-ups stayed in link review. |
| `complete` with the key's order, preference and date | ORD-226, ORD-251 | Duplicate-order review, caused by the intake misreads. The follow-ups' own tasks stay in review, unapproved. |
| `complete` with the order and preference | ORD-270 | The date question from the comma split. The CSV due date applies. |
| `add_batch` ORD-249, with the key's date | ADD-1 | The task failed verification, so no decision can name it. The added batch carries the order, and the failed task stays in processing review. |
| `correct` intent `question` | ORD-297 (CASE-097) | The cancelled order. The only decision that stops a clean recommendation (see section 6). |

Approve all then re-planned the whole table from the original queues, with those choices, and 59 rows changed. Review again found nothing left to fix.

## 5. After the review

| Measure | After Approve all (revision 1) | After Review again (revision 2) |
|---|---|---|
| Correct allocations (of 85) | 85 | 85 |
| Missed; wrong | 0; 0 | 0; 0 |
| Correct non-allocations (of 15) | 15 | 15 |
| Unsafe allocations | 0 | 0 |
| Approved rows that belong to no case | 0 | 0 |
| **Perfect** | **yes** | **yes** |
| Every allocator field matching the key | 85 | 85 |
| On time | 85 | 85 |
| At the key's own workshop | 82 | 82 |
| Carried by a batch the dispatcher added | 1 (ORD-249) | 1 |
| Approved rows; unresolved rows | 85; 26 | 85; 26 |

- **The 26 unresolved rows** were left as they are:
  - the 14 exceptions that are not CASE-097;
  - the reference row CASE-097 became;
  - the 8 follow-ups in link review;
  - the two follow-up tasks of ORD-226 and ORD-251;
  - CASE-049's failed task.

  None is approved, and a final table may keep unresolved rows by design.
- **Review again is stable.** With no new choices, revision 2 has the same rows, workshops, delivery estimates and queues as revision 1. Planning again from the original queues does not drift or reserve work twice.
- **Extra check, not in the frozen rules**, on a scratch copy of the run so the recorded files stayed as they are:
  - one Review again with 84 `choose_workshop` decisions, each at the key's own workshop;
  - 13 rows changed: three batches moved between W1 and W6, six approved rows kept their workshop with new estimates, and four exception rows showed a different option;
  - the table stayed perfect, now with all 85 allocations at the key's own workshop, which is the key's own plan;
  - so Review again also reallocates correctly when it does move work.

## 6. What this shows, and what to decide

**Verified outcomes:**
- One fresh run plus 23 choices reached a perfect table. The decisions the app offers were enough for every case: `correct`, `complete`, `add_batch` and `warnings_checked`.
- No answer was refused. Check workshop options showed exactly what Approve all then saved.
- The model's own score, 81 of 85, is the best so far on this set.
- The review needed no model call and changed no source file of the run.

**Limitations identified on 22 October; no application behavior was changed by this experiment:**
1. **There is no "do not allocate" decision.**
   - A cancelled order that verification reads as a clean allocation (CASE-097, in all three runs) is approved by Approve all unless the dispatcher changes it.
   - The only decision that stops it is `correct` intent `question`. The final table then calls a cancellation "Information question; not an allocation", which is a misleading record.
   - Options:
     - a cancellation rule in verification (model and prompt work, paid to test);
     - an explicit dispatcher decision such as "not to be allocated", with a reason;
     - accepting the workaround and documenting it.
   - Each needs a decision, because "no hold action" is a product rule.
   - Addressed on 24 October with the explicit decision plus a Python check in verification; see section 11.
2. **A task that failed verification cannot be named by any decision** (CASE-049). Adding a batch works, but the failed row stays in processing review next to the batch that replaced it.
3. **The model-side failures remain**, and their fixes are still proposals, not implemented:
   - "For that batch" linking;
   - follow-ups read as new requests;
   - the comma split in the date check;
   - malformed evidence IDs;
   - cancellations.

   Each one cost the dispatcher one or more choices.
4. **The dispatcher's workload.** 23 choices on 100 cases, 15 of them warning checks. A real dispatcher has no key and would need to read each case, so the time this takes was not measured.

## 7. Limits

- The dispatcher had the key, so "after" is the app's ceiling, not a measured human result.
- One run. Test 10 showed that run-to-run variation moves the before-review score by several cases.
- The chat is templated, and every chat deadline equals its CSV date, so it is a best case for clean chat.
- This does not replace the six official harness metrics or the 30-request evaluation, which stay separate.
- The run folders are gitignored, so this file keeps the important numbers.

## 8. Cost and time

| Stage | Calls (all paid) | Cost | Model seconds |
|---|---|---|---|
| Intake, Luna `high` | 50 | $0.0244 | 205 |
| Linking, Luna `medium` | 44 | $0.0121 | 109 |
| Verification, Luna `medium` | 34 | $0.0392 | 244 |
| **Total** | **128** | **$0.0757** | **558** |
| Dispatcher review (API) | 0 | $0 | - |

The wall time of the paid run was 9 min 23 s. Prices are those of the 14 October price table in `eval_run_report/run_summary.py`.

## 9. Files

**New, and checked offline by `tests/test_final_plan_score.py` (3 tests):**
- [`score_dispatcher_review.py`](../../score_dispatcher_review.py): the score after the review, written into the run folder as Markdown.
- [`eval_run_report/final_plan_score.py`](../../eval_run_report/final_plan_score.py): its rules.
- [`eval_run_report/key_informed_choices.py`](../../eval_run_report/key_informed_choices.py): the simulated dispatcher, for tests only.

**Not committed** (in `output/`):
- `output/end_to_end_test_2026-10-22/runs/2026-10-22_22-31-00/`: the run, its `run_report.md` (before the review), the dispatcher's two saved versions and `plan-history/`.
- `output/end_to_end_test_2026-10-22/test11/`: the first review, the choices, every API request and response, and the three scores after the review.

The 145 offline tests passed after `config.toml` was restored.

## 10. How to repeat it, and use it for regression tests

Every step after the paid run is free and can be repeated. From `backend/`, with `config.toml` set as in step 1 (the API and the allocation modules read their data folder from it):

```sh
uv run python make_run_report.py <run> --key docs/evaluation/extended_dispatch_100_human_team_golden.json --data data/extended_dispatch_100
uv run python -m eval_run_report.key_informed_choices <run> --key <key> --data <data> --table <first-review.json> --level 0 --out <choices.json>
uv run python score_dispatcher_review.py <run> --key <key> --data <data>
```

For a regression test after a code change:
- **Allocation or review changes:** re-plan a scratch copy of this run and score it again. This makes no model call.
- **Processing changes:** run the pipeline again with the same output folder. Unchanged requests reuse the saved answers in `output/end_to_end_test_2026-10-22/response-cache/` and cost nothing; a changed prompt, payload or model makes new, paid calls.

Then compare against the numbers above, before and after the review.

## 11. Follow-up replay, 24 October 2026: the cancellation check

This replays the run above with the code of 24 October; it is not a new run. The Python check `cancellation_words` and the dispatcher decision `cancel` were added test-first: their tests failed before the change and pass after it.

**How it was run.** A scratch copy of `backend/` had its `config.toml` pointed at the 100-case set and held this run's 128 saved model answers. The replay script replaced the model client with one that refuses every call, so an answer that had not been saved would have stopped the run instead of being paid for. All 128 answers were reused: no call was sent and the cost was $0.

**3 of the 115 plan rows changed** against this run's `plan.json`:
- `T:L0145:J1` (CASE-097): from a W1 recommendation (14.75 of 31 days) to `needs_clarification`, with the reason "The chat may cancel or hold ORD-297 ("cancelled", "Do not allocate"); the dispatcher decides whether to allocate it."
- `T:L0146:J1` (CASE-098, the order paused for fabric approval): already `needs_clarification`; it gained the same kind of blocker for "do not allocate".
- `T:L0118:J1` (CASE-069): from W5 to W1. ORD-297 no longer reserves 0.636 days on W1, so W1's queue for this batch is 13.116 days instead of 13.752. W1's delivery estimate becomes 15.18 days against W5's 15.34, so W1 ranks first under minimize_tardiness. The batch has 60 days available, so it is on time either way.

**Scores.** `make_run_report.py` scored the replay before the review. Then one decision, `cancel` for `T:L0145:J1`, was sent with `finalize`, and `score_dispatcher_review.py` scored the approved table.

| Measure | This run | Replay |
|---|---:|---:|
| Before the review: expected allocations, of 85 | 81 | 81 |
| Before the review: exceptions not allocated, of 15 | 14 | 15 |
| Before the review: unsafe allocations | 1 (CASE-097) | 0 |
| Recommendations; needs clarification | 68; 8 | 67; 9 |
| After Approve all: correct allocations, of 85 | 67 (no choices) | 67 (one `cancel`) |
| After Approve all: correct non-allocations, of 15 | 14 | 15 |
| After Approve all: unsafe allocations | 1 | 0 |
| After Approve all: at the key's own workshop | 56 | 55 |
| Approved; cancelled; unresolved rows | 68; 0; 42 | 67; 1; 42 |

The one fewer row at the key's own workshop is CASE-069: W1 is on time but is not the workshop of the key's plan.

**Limits.** The replay reuses the same model answers, so it tests the Python check on one sample, not the model. The check recognizes only listed wording, does not read negation ("do not cancel") or a superseding instruction, and counts wording before the first order ID for every order in the message. A fresh paid run is still needed to measure the change on new model answers. The replay files are in the session's scratch folder, not in `output/`.
