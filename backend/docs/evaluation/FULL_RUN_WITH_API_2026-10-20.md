# Full paid run with the API review (Test 9, 20 October 2026)

**Verdict: everything worked.** One fresh paid run took the original 30-request chat through processing, allocation and the pause for the dispatcher. The review was then done entirely through the new FastAPI endpoints:
- shown;
- one workshop choice;
- one invalid answer;
- final approval.

Every step gave the expected result. Nothing failed, so no debugging was needed, and only 1 of the 2 allowed paid runs was used. The run cost $0.0160.

The model's answers were the best so far on this chat by the key's readiness measure, 29/30, with no silent date error. The problems found are about the model's field choices and how blockers are listed (section 5), not about the code paths that ran.

## 1. What Aditya asked

1. Remove JWT and other complicated additions, and simplify the API code with the code-simplifier skill, so that a beginner can read it.
2. Do a full paid run with the original `dispatch_requests.txt` and check that everything works.
3. If something goes wrong, debug it systematically and do one final paid run: **2 paid runs maximum.**
4. Write down what happened, what Claude is happy with and what it is not happy with.

Before the run, Aditya chose a **fresh** run with an empty answer cache, so every model call was really sent. They chose this over reusing saved answers.

## 2. What was done, step by step

**Step 1: JWT and simplification.**
- No JWT, login or authentication existed. A search of the backend (outside `.venv` and `output/`) found no JWT, OAuth, passlib, bcrypt or jose code, and `pyproject.toml` has no such package. Nothing had to be removed.
- The code-simplifier pass changed readability only:
  - `fastapi_routes/runs.py`: one helper, `saved_run_ids()`, lists the saved run folders. Both endpoints use it, in place of a set expression.
  - `fastapi_routes/dispatcher.py`: a helper that returned an exception object is gone. Each endpoint now raises its 404 directly, and `paused_review(...)[1]` became named variables.
  - `tests/test_fastapi_routes.py`: a dense loop over three 404 cases became three plain checks, and a duplicated `read_json` is now imported.
  - `main.py` was already minimal and is unchanged.
- All 123 offline tests passed afterwards.

**Step 2: the paid run.**
- **`config.toml` for this run only:**
  - `chat_file = "data/dispatch_requests.txt"`;
  - `[output] folder = "output/fresh-run-2026-10-20"`, a new folder, so the answer cache was empty.
- **Backup:** the file was copied first. Afterwards the copy was put back, and its SHA-256 (`920d4f7f...`) matches the original and git.
- **Command:** `uv run python run_full_pipeline.py`, run from `backend/`. Exit code 0, from 22:33:27 to 22:35:43 (2 min 16 s).
- **Settings:** the same as Test 7, as printed by the run. Every stage ran on `gpt-5.6-luna`: intake at `high`, linking and verification at `medium`. Batches were 3 new and 2 context messages, with 3 tasks per verification. The dispatch date was 2026-04-01.
- **Run folder:** `output/fresh-run-2026-10-20/runs/2026-10-20_22-33-28`. The checkpoint file is `output/fresh-run-2026-10-20/dispatcher-review-checkpoints.sqlite`, and the thread ID was `51209ddb-4fa9-41c7-a4d6-05c35e6490fd`.
- **LangSmith:** `.env` has `LANGSMITH_TRACING=true`, so the run was traced, as Test 7 was. The trace includes the chat text, the tasks, the plan and the first review. The API server does not load `.env`, so the review steps in step 3 were not traced.

**Step 3: the review through the API.** The local server was started with `uv run fastapi dev main.py --port 8765 --no-reload`, using the same temporary config, and stopped afterwards. Calls, in order:

| # | Call | Status | Checked result |
|---|---|---|---|
| 1 | `GET /runs` | 200 | one run: `2026-10-20_22-33-28`, label `dispatch_requests.txt`, 30 messages |
| 2 | `GET /runs/2026-10-20_22-33-28` | 200 | `plan` equals `plan.json`; `dispatcher_plan` is `null` |
| 3 | `GET /reviews/<thread>` | 200 | `waiting`, no refusal; 3 recommendations, 8 `deadline_passed`, 9 dispatcher reviews, 9 clarifications, 1 link review |
| 4 | `POST .../answer`: choose W6 for T:L0008:J1 (R08) | 200 | R08 is `dispatcher_choice` at W6 ("It overrides the requested W8"), planned first. R09, which the allocator had given W6, moved to W8. W6's queue after the plan went from 2.18 to 4.15 days. |
| 5 | `POST .../answer`: `"then": "save_draft"` | 200 | refused with `apply_answer`'s own text, `"then" must be "review_again" or "approve_all", not 'save_draft'.`; the review is unchanged |
| 6 | `POST .../answer`: `approve_all` | 200 | `finished`; the final review equals the saved `dispatcher-plan.json`; planning order, queues and reservations are the same as the review shown in step 4; 4 rows approved (R08, R09, R21, R25) and 26 left unresolved |
| 7 | `GET /runs/2026-10-20_22-33-28` | 200 | `dispatcher_plan` now equals the saved file |
| 8 | `GET /reviews/<thread>` | 404 | "Thread ... has no paused dispatcher review." |
| 9 | `POST .../answer` again | 404 | the same message |

The server log had no error or traceback. The run folder now holds `dispatcher-decisions.json` (only R08 at W6) and `dispatcher-plan.json`, beside the unchanged processing and plan files.

## 3. Cost and time

| Stage | Calls (all paid) | Input tokens (cached) | Output tokens (reasoning) | Cost | Model time |
|---|---|---|---|---|---|
| Intake, Luna `high` | 10 | 7,476 (0) | 2,523 (885) | $0.0045 | 38 s |
| Linking, Luna `medium` | 1 | 549 (0) | 178 (100) | $0.0003 | 3 s |
| Verification, Luna `medium` | 10 | 22,301 (13,347) | 7,562 (3,450) | $0.0111 | 93 s |
| **Whole run** | **21** | 30,326 (13,347) | 10,263 (4,435) | **$0.0160** | 134 s |

**Source:** `make_run_report.py` on the run folder, which wrote `run_report.md` there, using the price table of 14 October.

**Comparison with Test 7:** $0.0157 and 105 s for 20 calls. This run made one extra call, for linking, and verification was slower. With one run each, the time difference may be chance.

The API review steps made no model call and cost nothing.

## 4. Score against the key

The key is the fresh-run key for `dispatch_requests.txt`, written on 19 October before Test 7, together with the verification key it uses. The prompts have not changed since then.

| Measure | Test 2 | Test 7 | **Test 9** |
|---|---|---|---|
| Intake labels | 30/30 | 30/30 | **29/30**: R19 labelled `follow_up` (key: `request`) |
| Readiness (a line is correct when it is its own task and its readiness matches) | 28/30 | 27/30 | **29/30**: all 20 expected-ready tasks ready, 9 of the 10 not-ready ones not ready; R19 is a link review, not its own task |
| Field errors on ready tasks | 1 (R23, judgment call) | 1 (R23) | **2, both key judgment calls:** R23 `fastest` and R25 `quality` (key: `none` for both) |
| Silent errors (wrong deadline, estimated quantity) | 0 | 0 | **0**: every due date matches the key; R01's quantity is not estimated |
| Extra "which written date" questions | | 0 | **0** |
| Plan outcomes matching the key | 28/30 | 27/30 | **28/30** (R25's workshop and R19; see below) |
| Link reviews / review warnings | 0 / 0 | 0 / 0 | **1 / 3**: L0019, which makes R13, R17 and R18 provisional |

**The plan against the key's list:**
- **Recommendations:** R09 to W6 and R21 to W5 match. R25 went to W2, where the key expects W1.
- **`deadline_passed`:** R04, R07, R16, R17, R22, R26, R27 and R28, all as the key expects, with R07 and R22 ready.
- **Dispatcher review:** R06, R08, R11, R12, R23, R24 and R30, each for the key's reason.
- **Duplicate-order review:** R14 and R20.
- **The not-ready lines:** need clarification, except R19, which is in link review. R19 is not allocated in either case.

## 5. What I am happy about

- **The whole path works with real model answers, not only with saved test answers:** chat file, intake, linking, verification, plan, pause, then show, edit, refuse and approve through HTTP. It ended with a saved final review and a clean 404 afterwards.
- **"The dispatcher decides" holds on a real run.** The chosen W6 was used and planned first, and Python moved R09 from W6 to W8 around it. Final approval kept the shown workshops and numbers exactly.
- **Refusals keep their own wording** through the API, and a refused answer changed nothing.
- **Best readiness on this chat so far (29/30), with no silent error:**
  - R26 and R27, which Test 7 blocked because the model copied "due Apr 13", are read correctly.
  - R07 and R22 are ready and correctly sent to `deadline_passed`.
- **R19 was handled safely.** In Test 1, Prompt 1 merged R19 ("That big reorder from last week") into the wrong task, and nothing flagged it. This time intake called it a follow-up, but linking refused to guess between four candidates and sent it to review. The three tasks it might affect are marked provisional, and nothing was allocated from it.
- **Cost and limits:**
  - the same cost as Test 7;
  - one paid run of the two allowed;
  - `config.toml` restored exactly;
  - the API made no model call;
  - all 123 offline tests pass.

## 6. What I am not happy about

1. **R25 got a different workshop because of a model field choice.**
   - The model read "the last batch came back rough" as a quality preference, which the key's judgment call says it is not. So the plan ranked R25 by defect rate and chose W2 (SteadyHands) instead of W1.
   - W2 is on time, cheaper ($650 against $750) and has fewer defects (3% against 12%), so the result is not harmful here.
   - But it is a silent change. Its reason says "ranks first under minimize_defects", while the terminal review prints no reason for a recommendation row.
   - The same kind of judgment call gave R23 `fastest`. That had no effect, because a split request goes to review.
2. **Run-to-run variation at the same settings.** Test 7 labelled R19 a request and made no link call. This run labelled it a follow-up, which added a link call, a link review and 3 provisional warnings. One run per setting cannot say which is typical.
3. **Blockers are cluttered for the dispatcher.**
   - R01 lists 5 blockers for 2 missing facts:
     - the model's "Order ID";
     - Python's "order ID" and "What is the order ID?", added by `verify_tasks.py` when the order is missing;
     - the model's question, which repeats the reason.
   - The cause: `dict.fromkeys` removes only exact repeats, and "Order ID" and "order ID" differ in case.
   - R29 lists a note that is not a blocker ("this is dispatch timing, not a delivery deadline") twice, once as a missing detail and once as an unsupported condition.
   - The dispatcher has to resolve each one by number with `correct`.
   - Not changed: it is processing behaviour, and a fix would need paid runs to evaluate.
4. **Outdated wording in 8 rows.** The `deadline_passed` reason still says only a revised deadline can return the request to allocation. Since 20 October, the dispatcher's own workshop choice also allocates it, late. The text comes from the allocator's notebook-05 code and was left unchanged.
5. **R23 (split requested) cannot take a dispatcher's workshop choice.** The review tells the dispatcher to decide, but a choice would be ignored. This is the open question raised earlier.
6. **The API cannot be used on its own yet:**
   - a run still has to be started from the terminal (`run_full_pipeline.py`, which can make paid calls);
   - the thread ID still has to be copied from its printout;
   - the frontend cannot find a review from a run yet (an open decision in [FASTAPI_BUILD.md](../../FASTAPI_BUILD.md)).
7. **One run is weak evidence.** The readiness gain over Test 7 (29 against 27) and the time difference may be chance.

## 7. Files

- **Changed by this step:**
  - `fastapi_routes/runs.py`, `fastapi_routes/dispatcher.py`, `tests/test_fastapi_routes.py` (simplification);
  - `FASTAPI_BUILD.md` (one sentence on `saved_run_ids()`);
  - this file;
  - Test 9 in [PROMPT_TESTING_RESULTS.md](PROMPT_TESTING_RESULTS.md);
  - an entry in the engineering log.
- **Created, and not committed (under `output/`):** `output/fresh-run-2026-10-20/`, with the run folder (`run_report.md`, `dispatcher-plan.json` and `dispatcher-decisions.json` included), its response cache and its checkpoint file.
- **Temporarily changed, then restored:** `config.toml`.
- **Not changed:**
  - any processing, allocation, review or graph code;
  - the notebooks and data;
  - `output/runs/`, which still holds 15 runs.

## 8. How to repeat the review part

From `backend/`, with `config.toml` pointing at the folder that holds the paused run:

```text
uv run fastapi dev main.py
```

Open http://127.0.0.1:8000/docs, or use curl with the thread ID that `run_full_pipeline.py` printed:

```text
curl http://127.0.0.1:8000/reviews/<thread ID>
curl -X POST http://127.0.0.1:8000/reviews/<thread ID>/answer -H "Content-Type: application/json" \
     -d '{"decisions": [{"decision": "choose_workshop", "task_id": "T:L0008:J1", "workshop_id": "W6"}], "then": "review_again"}'
```

This run's thread is already approved, so it now answers 404. A new review needs a new `run_full_pipeline.py` run.
