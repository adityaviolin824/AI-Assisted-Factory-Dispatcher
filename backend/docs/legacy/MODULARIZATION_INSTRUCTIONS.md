# Modularization instructions

> Archived on 15 October 2026. Intake, processing, routing, allocation and the batch LangGraph integration are complete. This is a historical decision record, not current coding instructions. Use [backend instructions](../../AGENTS.md), [current implementation](../../README.md) and the [project plan](../../../docs/project-plan.md). Paths and instructions in the original body refer to `backend/` and the work as it stood then; its unfinished dispatcher/API ideas are governed by the active plan.

I want you to go through @experimentation_notebooks/05-order-pipeline-mvp.ipynb and check if it is ready for modularization for our MVP. The deadline is coming up, but I don't want to rush it. This is the main file to refer to. For the overall idea, but not the exact details, you can check @experimentation_notebooks/Project_Overall_Guideline.md.

Paths in this file are relative to `backend/`; `testing/` and `mock_frontend/` mean those folders inside `experimentation_notebooks/`. Follow the `AGENTS.md` files (repository root and `backend/`). Steps 1 and 2 were done on 13 October 2026, steps 3 and 4 on 15 October 2026 (see [ALLOCATION_MODULARIZATION_PLAN.md](ALLOCATION_MODULARIZATION_PLAN.md)), and the LangGraph part of step 6 also on 15 October 2026 (see [LANGGRAPH_MODULARIZATION_PLAN.md](LANGGRAPH_MODULARIZATION_PLAN.md)). Step 5 and the API part of step 6 are context for later.

## What I mean by modularization

First, I will type some sample input into the mock chat in @experimentation_notebooks/mock_frontend/. It saves messages in SQLite, and **Export for notebook** writes a TXT snapshot in the same format as @data/dispatch_requests.txt (one message per line, for example `R01 [07:53] Chen: ...`).

1> Whatever manual deterministic or LLM processing (for voice input) should be in @order_intake_from_chat/.
We will also add a small basic LLM for voice-to-text transcription immediately after modularization (not part of this task).
This is the folder that will be hit first by the input that comes from the frontend, through the API (FastAPI, details to be decided later).
Its output is the message list that processing reads. Today that is `read_messages` (Section 2) reading the TXT file.

2> Then the processed text goes to @order_processing_into_tasks/.
This folder contains the main modules for processing the text into items, tasks, orders, review records, etc.
This is Part 2 of the notebook (Sections 3 to 9: prompts, model calls, run folder and state, extraction, tasks and linking, verification, saving the run), plus the Part 1 helpers it uses.
Note: the notebook's Section 6 is called "Intake", but it is the LLM extraction of items, so it belongs here, not in `order_intake_from_chat/`.

3> After processing, tasks go to @task_routing/, then to @task_allocation_to_workshops/. Done on 15 October 2026 (`task_routing/route_verified_tasks.py`). The decision on non-task messages is below.

4> @task_allocation_to_workshops/: Part 3 of the notebook (Sections 10 to 13), without the routing step. Done on 15 October 2026; `run_allocation.py` plans a saved run folder by itself.

5> @dispatcher_stuff_to_be_decided/ and @review_tasks_processing/: what the dispatcher sees and does (see the decision below). Not now.

6> @app_full_pipeline/ (the LangGraph wiring, Part 4 of the notebook) and @fastapi_routes/ (the API). The LangGraph wiring was done on 15 October 2026 (`app_full_pipeline/pipeline_graph.py`, run by `run_full_pipeline.py`). The API: not now.

## Decision: routing and non-task messages

- Scope: the app only allocates. It asks the dispatcher only questions that help allocation. Information questions are not the app's or the dispatcher's business.
- The dispatcher gets every allocation decision with its reasons, plus a review section where he clarifies order numbers or dates, or allocates to a workshop himself. `dispatcher_stuff_to_be_decided/` owns this. `review_tasks_processing/` applies his answers about facts (order number, date) and sends the task back through routing.
- `task_routing/` splits the verified tasks three ways: allocate, ask the dispatcher, or declined. It is deterministic code that reads recorded fields: no LLM and no queue. In the notebook this is step 3 of `plan_tasks` (Section 13); it moves out of allocation unchanged. Moving it changes no result, because the tasks it skips never touch the queues. (Checked on 15 October 2026: the duplicate-order check moved with it and still counts every verified allocation task with an order ID, ready or not; every saved run gives the notebook's decisions.)
- Declined messages are only recorded in the run (today R02 and R13). They still need that record: the course scores all 30 requests by behaviour, and these count as decline-to-answer.
- Keep the current rule: a "question" with something left to clarify goes to the dispatcher; one with nothing to clarify is declined. Do not decline every "question". In the run of 2026-10-13, 5 of the 6 tasks labelled "question" (R01, R03, R15, R18, R29) were requests to get an order out that lacked an order number or date.
- Known issue, to fix later in the processing prompt, not in routing: R28 has all its facts, but "Who has room this week?" was recorded as a doubt, so the dispatcher would be asked the app's own job.
- Open, to decide before building the review section: is it a form (order number, date, workshop) or free text? A form needs no LLM. When the dispatcher picks a workshop himself, should code block a pick that breaks a hard rule (status, category, batch cap)?

## First: fix the paths broken by the folder move

Done on 13 October 2026; kept as a record.

The folders were reorganized: `experimentation/` is now `experimentation_notebooks/`, the repository's `data/` is now `backend/data/`, and `dispatcher_stuff_to_decide/` is now `dispatcher_stuff_to_be_decided/`. Notebook 05 and its checks still use the old paths. On 2026-10-13, `testing/check_allocation_rules.py` stopped with `StopIteration` in Section 1, because `ROOT` is found by looking for `data/orders.csv` at the repository root.

- Fix paths only, with no behaviour change:
  - in 05: Section 1 (`ROOT`, `EXPERIMENT_DIR`), Section 2 (CSV paths), Section 17 (`dispatch_requests.txt`) and the folder names in its text;
  - `testing/notebook_code.py`;
  - the run commands in `testing/` and in `mock_frontend/README.md`;
  - `testing/protected-files.sha256`;
  - the folder names in `backend/AGENTS.md`.
- Then run the five offline checks in `experimentation_notebooks/testing/`. They block API calls, so a wrong cache path shows up as an error, not a bill. Do not run the notebook's run cell before they pass.

## How to work

1. First report whether 05 is ready and what would block a clean move. Then propose the module layout for steps 1 and 2, including how processing runs before allocation and the graph are moved. Wait for my approval before moving code.
2. Move code without changing behaviour: same prompts, schemas, rules and outputs. Fixes come later, one at a time.
3. Leave notebook 05 as the reference; change only its paths.
4. Move one module at a time and run the checks after each.
5. Regression check: the modules must reproduce the baseline in `testing/check_end_to_end.py` from the saved answers, with 0 API requests. Extend the offline checks to cover the modules.
6. Modules use short functions, clear names and concise docstrings, not the notebook's long comment blocks.
7. Keep message, item, task and order IDs separate.
8. Ask before any paid API call, new dependency, or change to `data/` or the repository's `reference-documents/` and `harness/`. Run Python with `uv run` from `backend/`.

## Done when

- Intake and processing code live in their folders, and a short script runs them on `data/dispatch_requests.txt`.
- They produce the same tasks and review records as the notebook (ignoring run IDs and times), with 0 API requests.
- The offline checks pass for both the notebook and the modules.
- `README.md` says how to run them.

# USE SIMPLE EASILY READABLE CODE. DO NOT BREAK UP CODE AND MAKE IT HARD TO NAVIGATE JUST TO MAKE MODULES SHORTER
# KEEP DOCUMENTING YOUR STEPS AND PROGRESS INTO A MARKDOWN FILE SO THAT YOU CAN RECOVER EVEN IF THE PROCESS STOPS MIDWAY
### Do not assume anything. Work stepwise and ask clarifying questions if unsure about any step.
