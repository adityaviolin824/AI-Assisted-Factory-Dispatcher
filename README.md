# SweaterCo Dispatch Copilot

SweaterCo Dispatch Copilot helps factory teams decide which outside workshop should handle each batch of work. It reads requests from a shared chat, checks the order and workshop records, and prepares a table with suggested workshops, delivery estimates and the reasons for each suggestion.

The source repository is [AI-Assisted-Factory-Dispatcher](https://github.com/adityaviolin824/AI-Assisted-Factory-Dispatcher). SweaterCo Dispatch Copilot is the application name.

It is designed for dispatchers who assign the work, operations staff who send requests, and managers who need to understand the plan. Instead of checking every workshop and recalculating its workload by hand, the dispatcher can compare the options, deal with exceptions and make the final decision.

The original messages are kept with the recommendations, so the dispatcher can check where an instruction came from. Missing or conflicting information is flagged for review. Previously saved AI answers can be reused when the same request is processed again.

Learn [how it works](#how-it-works), explore the [architecture](#product-architecture), or [run it locally](#run-locally).

## Why this is useful

- **Less checking by hand.** The dispatcher gets the requests, order details, workshop options and reasons in one table. Python checks restrictions and calculates delivery, cost and queue effects.
- **Less time on routine planning.** The system compares the eight workshops and builds a shared plan. The dispatcher can focus on missing information, exceptions and final choices.
- **Low AI running costs.** Models handle the language tasks. Allocation and structured dispatcher review run in Python without model calls. An identical saved AI request can reuse its answer without another paid call.
- **An easier handover.** Operations staff and managers can read the original messages and recorded reasons instead of relying on one person's memory of the chat.

Recorded per-run model costs, calls and latency are listed in the [evaluation results](#testing-and-recorded-results).

Staff time savings have not yet been measured against a manual dispatcher. Workshop production costs are a separate trade-off: the historical test below achieved faster delivery with higher production cost.

## Core capabilities

The system combines three core capabilities:

1. **LLM-based request interpretation.** Language models read informal chat messages and extract structured tasks, order references and instructions. They also identify follow-ups and propose which request an update belongs to.
2. **Deterministic verification and capacity-aware planning.** Python checks order facts, workshop capabilities and restrictions, then calculates delivery, cost and queue effects. It recommends workshops based on those checks, deadlines and the request's stated preferences.
3. **Human-in-the-loop decision making.** The dispatcher reviews recommendations and exceptions, corrects facts, chooses workshops and approves the final table. Source messages, decisions and reasons are retained so the choices can be traced. Cases that cannot be resolved with the supported actions remain visible.

## How it works

The implemented workflow is:

1. **The team sends requests and corrections in Chat.** When processing starts, the system uses a saved copy of the conversation so later messages do not change the input halfway through a run.
2. **The system identifies the work being requested.** AI reads the messages, extracts the order references and instructions, and connects related follow-up messages. Uncertain connections are left for review.
3. **The requests are checked against the records.** Python checks order quantities, deadlines and workshop restrictions. It then calculates which workshops have the capacity to finish the work, taking their existing queues into account.
4. **The dispatcher receives a proposed dispatch table.** Each suggestion includes a workshop, estimated delivery time, cost and reason. Requests with missing facts, conflicting instructions or no suitable workshop appear under **Needs attention**.
5. **The dispatcher reviews the whole table.** They can correct facts and choose workshops. Their unfinished changes stay on the page until they click **Approve all**.
6. **The final choices are applied together.** The approval flow keeps the dispatcher's workshop choices fixed, schedules the remaining work around them, saves the resulting table and shows what changed. It does not require another approval before saving.
7. **An approved table can be reviewed again.** With **Review again**, the dispatcher adds new choices to the saved ones. Python plans once more and saves a new version, and the earlier version is kept.

The output is a dispatch table for the team to use. It does not yet book work with workshops or update a live factory system.

### How reallocation works

Suppose a dispatcher sends extra work to a workshop and lengthens its queue by two days. Another batch planned there may now miss its deadline. When the dispatcher clicks **Approve all**, Python keeps the dispatcher's own workshop choices fixed and recommends a workshop again for every other ready batch, in deadline order, using the updated queues. A batch whose earlier workshop can no longer finish on time moves to one that can. If none can, it stays under **Needs attention** with the reason.

The saved table shows every row that changed: its old and new outcome, workshop, delivery days and reason. **Review again** repeats this planning on an approved table when the dispatcher adds more choices, and saves a new version.

## Product architecture

This view shows the workflow from Chat to the dispatch table. The [implementation status](#what-is-available-now) below lists what works today.

```mermaid
---
config:
  theme: base
  look: classic
  markdownAutoWrap: false
  themeVariables:
    fontFamily: system-ui, sans-serif
    fontSize: 15px
    primaryTextColor: "#EAF2F5"
    textColor: "#EAF2F5"
    lineColor: "#839BA8"
    clusterBkg: "#111D27"
    clusterBorder: "#334B5A"
    titleColor: "#EAF2F5"
    edgeLabelBackground: "#172631"
  flowchart:
    curve: basis
    nodeSpacing: 30
    rankSpacing: 42
---
flowchart TB
    subgraph PRODUCT["SWEATERCO DISPATCH COPILOT"]
        direction TB

        TEAM["Operations chat · Next.js<br/>Requests, questions and corrections"]:::screen
        FACTS[("Order and workshop facts<br/>Quantities, dates, capacity and queue")]:::data

        subgraph PROCESSING["01 / UNDERSTAND AND PLAN · PYTHON + LANGGRAPH"]
            direction LR
            READ["AI reads the messages<br/>and connects follow-ups"]:::ai
            CHECK["Check the facts<br/>Keep missing details visible"]:::logic
            PLAN["Compare workshops<br/>Build a draft dispatch table"]:::logic
            READ --> CHECK --> PLAN
        end

        subgraph DISPATCHER["02 / DISPATCHER REVIEW · NEXT.JS + FASTAPI"]
            direction LR
            VIEW["See suggestions and problems<br/>with reasons and source messages"]:::screen
            CHOOSE["Make all choices on the page<br/>Keep unfinished choices local"]:::screen
            APPROVE["Approve all<br/>Send the complete set once"]:::screen
            VIEW --> CHOOSE --> APPROVE
        end

        subgraph RESULT["03 / SAVE THE DECISION TABLE · PYTHON"]
            direction LR
            APPLY["Keep chosen workshops fixed<br/>Fit other work around them"]:::logic
            SAVE["Save the final table immediately<br/>Show what changed and why"]:::logic
            APPLY --> SAVE
        end

        TEAM -- "Process a saved snapshot" --> PROCESSING
        FACTS --> PROCESSING
        PROCESSING --> DISPATCHER
        DISPATCHER -- "Approve all, once" --> RESULT
        RESULT -- "Review again: add choices, save a new version" --> DISPATCHER
    end

    classDef screen fill:#183A49,stroke:#63AFC0,color:#F1F7F9,stroke-width:1.5px
    classDef ai fill:#143D36,stroke:#64B39F,color:#EDFAF5,stroke-width:1.5px
    classDef logic fill:#1C2E40,stroke:#7B9FBC,color:#EFF5FA,stroke-width:1.5px
    classDef data fill:#24342F,stroke:#87AA91,color:#F0F7F1,stroke-width:1.5px
    style PRODUCT fill:#0B141D,stroke:#334B5A,stroke-width:1px
```

## Backend architecture

This view shows the processing steps, LangGraph loops, saved records and API connections. Dotted lines are data and model-call connections.

**Approve all** runs one planning pass. Python places the dispatcher's chosen workshops first, then checks each flexible batch in deadline order against the queues so far. If no suitable workshop can finish a batch on time, it stays in Needs attention rather than being moved repeatedly.

```mermaid
---
config:
  theme: base
  look: classic
  markdownAutoWrap: false
  themeVariables:
    fontFamily: system-ui, sans-serif
    fontSize: 15px
    primaryTextColor: "#EAF2F5"
    textColor: "#EAF2F5"
    lineColor: "#839BA8"
    clusterBkg: "#111D27"
    clusterBorder: "#334B5A"
    titleColor: "#EAF2F5"
    edgeLabelBackground: "#172631"
  flowchart:
    curve: basis
    nodeSpacing: 28
    rankSpacing: 38
---
flowchart TB
    subgraph BACKEND["BACKEND / CURRENT IMPLEMENTATION"]
        direction TB

        INPUT["Chat snapshot or saved TXT + config.toml<br/>The Chat API or run_full_pipeline.py starts the run"]:::input
        CSV[("orders.csv + workshops.csv<br/>Trusted batch facts and workshop queues")]:::data

        subgraph GRAPH["LANGGRAPH / RUN THE STEPS AND WAIT FOR THE DISPATCHER"]
            direction TB
            START["start_run<br/>Number messages and open a run record"]:::logic
            LINK["link_items<br/>Create tasks or attach supported follow-ups"]:::ai
            MORE{"Unread messages?"}:::gate
            EXTRACT["extract_batch<br/>Read a small batch and check its evidence"]:::ai
            VERIFY["verify_tasks<br/>AI checks the current request<br/>Python checks dates, quantities and readiness"]:::logic
            OUTPUT["save_outputs<br/>Save messages, task versions and verification"]:::logic
            PLAN["plan_allocation<br/>Route tasks; check and rank workshops<br/>Use earliest deadlines and tentative queues"]:::logic
            REVIEW["dispatcher_review<br/>Pause for corrections or workshop choices<br/>Unresolved cases stay visible"]:::human
            FINAL["save_review<br/>Save approved rows and unresolved cases<br/>as the final dispatch table"]:::human

            START --> LINK --> MORE
            MORE -->|Yes| EXTRACT --> LINK
            MORE -->|No| VERIFY --> OUTPUT --> PLAN --> REVIEW
            REVIEW -->|Edit or refusal: review again| REVIEW
            REVIEW -->|Approve current draft| FINAL
        end

        subgraph LANGUAGE["SHARED AI CALL LAYER"]
            direction TB
            CACHE["RecordedModel + response cache<br/>Reuse an exact saved answer first"]:::data
            MODEL["OpenAI models<br/>Called only when no matching answer exists"]:::ai
            CACHE -->|Cache miss| MODEL
            MODEL -->|Record the answer| CACHE
        end

        subgraph RECORDS["LOCAL RECORDS"]
            RUNS[("Run folder<br/>manifest.json · state.json · calls/<br/>plan.json · dispatcher-plan.json")]:::data
            PAUSE[("SQLite checkpoint<br/>Keep a paused review across restarts")]:::data
            CHAT[("Chat SQLite + snapshot folders<br/>Messages and fixed copies of the conversation")]:::data
        end

        API["FastAPI · 15 routes<br/>/chat: dates, messages, snapshots, process<br/>/runs: list, read, preview, finalize<br/>/reviews/{thread_id}: read, answer, preview, finalize"]:::input

        subgraph APPROVAL["APPROVE ALL / ONE PLANNING PASS AROUND THE DISPATCHER'S CHOICES"]
            direction TB
            FIXED["Start from the original queues<br/>Place dispatcher choices first and keep them fixed"]:::logic
            NEXT{"Another flexible batch<br/>in deadline order?"}:::gate
            OPTIONS["Check workshops against queues so far<br/>Keep or change the previous workshop"]:::logic
            ONTIME{"Eligible on-time option?"}:::gate
            RESERVE["Place the batch at that workshop<br/>Add its production and rework to the queue"]:::logic
            ATTENTION["Keep the batch in Needs attention<br/>Record why it cannot be placed"]:::logic
            CHANGES["Save the table and show every change<br/>Old and new outcome, workshop, delivery days and reason"]:::logic
            AGAIN{"Review again selected?"}:::gate
            DONE["Keep the saved table"]:::data

            FIXED --> NEXT
            NEXT -->|Yes| OPTIONS --> ONTIME
            ONTIME -->|Yes| RESERVE --> NEXT
            ONTIME -->|No| ATTENTION --> NEXT
            NEXT -->|No| CHANGES --> AGAIN
            AGAIN -->|No| DONE
        end

        INPUT --> START
        CSV -. "Order facts" .-> VERIFY
        CSV -. "Eligibility, prices and queues" .-> PLAN
        EXTRACT -. "Interpret wording" .-> CACHE
        LINK -. "Check follow-up links" .-> CACHE
        VERIFY -. "Assess current task" .-> CACHE
        OUTPUT -. "Write" .-> RUNS
        PLAN -. "Write preview" .-> RUNS
        FINAL -. "Write final result" .-> RUNS
        REVIEW -. "Save paused state" .-> PAUSE
        API -. "Read plans, save Review again versions" .-> RUNS
        API -. "Read or resume review" .-> PAUSE
        API -. "Save messages and snapshots" .-> CHAT
        REVIEW -- "Approve all: the complete choice set, once" --> FIXED
        AGAIN -- "Yes: saved and new choices, save a new version" --> FIXED
    end

    classDef input fill:#183A49,stroke:#63AFC0,color:#F1F7F9,stroke-width:1.5px
    classDef ai fill:#143D36,stroke:#64B39F,color:#EDFAF5,stroke-width:1.5px
    classDef logic fill:#1C2E40,stroke:#7B9FBC,color:#EFF5FA,stroke-width:1.5px
    classDef data fill:#24342F,stroke:#87AA91,color:#F0F7F1,stroke-width:1.5px
    classDef human fill:#362C20,stroke:#CBA56D,color:#FFF3E0,stroke-width:1.5px
    classDef gate fill:#253341,stroke:#93AABA,color:#F1F7FA,stroke-width:1.5px
    style APPROVAL fill:#111D27,stroke:#334B5A,stroke-width:1px
    style BACKEND fill:#0B141D,stroke:#334B5A,stroke-width:1px
```

## What is available now

| Part | Status |
|---|---|
| Processing and allocation | The backend reads saved chat files, checks requests and produces workshop recommendations with reasons and queue estimates. |
| Dispatcher review | The backend pauses for the initial review. The dispatcher can submit all choices in one approval request, after which Python recalculates the plan, saves the result and returns a list of changes. **Review again** opens an approved table for new choices and saves a new version. |
| Web interface | Chat and Dispatcher screens exist and call the backend. Chat saves messages, captures a fixed snapshot of the conversation and can send that snapshot through the pipeline to a paused dispatcher review (23 October 2026). Processing calls paid AI models, so the API refuses it unless it was started with `ALLOW_PAID_PROCESSING=1`. Automated browser checks use controlled API responses; the chat bridge also has an offline pipeline integration test using saved model answers. The published evidence does not include a retained live-browser run artifact. |
| Saved AI responses | Identical requests can reuse earlier answers. Changes to the input, model, prompt or settings may require new paid calls. |
| Reallocation | Part of **Approve all**: Python keeps the dispatcher's choices fixed and plans the other ready work again around them, using the updated queues. **Review again** does the same on an approved table. |

## How it is built

AI handles the language in the messages. Python checks the facts and calculates dates, queues, costs and workshop rankings.

| Technology | Role |
|---|---|
| Next.js, React and TypeScript | Build the Chat and Dispatcher screens. |
| FastAPI | Lets the web interface save chat messages and snapshots, start processing, read saved runs, answer paused reviews, preview choices and approve them. |
| LangGraph | Runs the processing steps, repeats message batches and pauses until the dispatcher answers. |
| Python | Applies workshop rules and calculates the dispatch plan. |
| OpenAI models | Extract requests, connect follow-ups and assess the latest instructions for each task. |
| JSON files and SQLite | Store run records, model responses, paused reviews, and the chat's messages and snapshots. |

### Models used for each task

The processing models are configured in [backend/config.toml](backend/config.toml). These are the current settings; each saved run records the settings it actually used.

| Task | Model | Reasoning effort |
|---|---|---|
| Intake: identify requests and follow-ups in the chat | `gpt-5.6-luna` | High |
| Linking: attach a follow-up to the right task | `gpt-5.6-luna` | Medium |
| Verification: assess the latest instructions and their evidence | `gpt-5.6-luna` | Medium |

Python checks the model's proposed facts. Python also calculates dates, workshop eligibility, queues, costs, rankings and allocations. Structured dispatcher review and final approval make no model calls.

The earlier dispatcher experiment in [notebook 06](experiments/notebooks/06-dispatcher-workflow.ipynb) also has optional explanation calls:

| Explanation task | Model | Setting |
|---|---|---|
| Summarize why a workshop was recommended | `gpt-4o-mini` | Temperature 0 |
| Explain why a request needs attention | `gpt-6-luna` | Medium reasoning effort |

These explanation calls belong to the notebook prototype. They are separate from the current API's structured review, and a new explanation request can cost money. The older notebooks retain their historical model settings; [the experiment history](backend/docs/evaluation/PROMPT_TESTING_RESULTS.md) records the comparisons and changes.

### Reusing AI answers and checking decisions

A saved answer is reused only when the processing stage, model, prompt, settings, input and response format match. The answer is still checked, and the dispatch plan is calculated again. Allocation and structured dispatcher review do not make model calls.

Each run keeps its input messages, settings, tasks, model-call records and allocation plan. A separate report script summarizes outcomes, processing time and model cost. With an answer key, it can also score the run. These records help explain why a request was allocated, left unresolved or interpreted incorrectly.

## Testing and recorded results

The allocation rules were tested on 120 historical orders using the supplied simulator. The table below compares the default policy with choosing a random eligible workshop.

| Normal historical replay | Mean days | p90 days | Late | Defective | Cost | Maximum workshop share |
|---|---:|---:|---:|---:|---:|---:|
| Random eligible workshop | 21.5 | 45.6 | 34% | 4% | 111,780 | 23% |
| Default policy: reduce lateness | 8.1 | 13.7 | 2% | 6% | 115,360 | 25% |

The default policy delivered sooner and had fewer late batches in this test, but cost more and had more defective batches. The simulator requires a workshop for every batch, so the evaluation adapter chooses the least-late option when all options are late. The app instead asks the dispatcher to review the case. The [scheduling benchmark report](backend/eval_harness/results/harness_results_2026-10-15.md) includes the other policies and assumptions.

These results measure the scheduling rules, not the accuracy of AI's reading of a conversation. The backend's **170 offline tests passed on 24 October 2026**; later changes have their own checks in the engineering log.

### Chat-to-allocation results

**How we evaluated it:**
1. **Test set.** There are 100 synthetic cases in 149 chat messages. The 85 that should be allocated fit on time in one plan, as an offline check confirms. The other 15 are deliberate exceptions, such as a cancelled order or a suspended workshop. A human-reviewed answer key was frozen on 21 October 2026, before any run.
2. **Rules written first.** Before each paid run, the expected results and the scoring rules were written down and hashed. They were not changed afterwards.
3. **Fresh runs.** Each run processed the whole chat with an empty answer cache and the same models and settings, so every model call was new.
4. **Score before the review** (`backend/make_run_report.py`). Each case is matched to the task the app created from its first message. Under the frozen headline score, a case is **correct** when it is expected to be allocated and receives a recommendation respecting the key's requested and excluded workshops. Provisional recommendations count. Full field agreement, workshop eligibility and timeliness are separate checks; a lost preference can still count as allocated. A case is **missed** when it is expected to be allocated but receives no recommendation. An allocated exception or a broken requested/excluded destination is **unsafe**.
5. **Score after the review** (Test 11 only; `backend/score_dispatcher_review.py`). A simulated dispatcher who knows the answer key reviewed the paused run through the app's HTTP API. It sent one **Approve all** with 23 choices, then **Review again**, which plans the approved table again. Only approved rows count as allocated, with full quantity and the key's requested/excluded destinations checked. The final coverage headline does not require timeliness or every field to match; those are separate details. Split-part lateness/field details currently inspect only the main part.

| | Test 10, run 1 (21 Oct) | Test 10, run 2 (21 Oct) | Test 11 (22 Oct), before review | Test 11, after review |
|---|---:|---:|---:|---:|
| Correct allocations (of 85) | 73 | 80 | **81** | **85** |
| - every field matches the key | 71 | 77 | 78 | 85 |
| Missed (sent to a person) | 12 | 5 | 4 | 0 |
| Exceptions correctly held (of 15) | 14 | 14 | 14 | **15** |
| Unsafe allocations | 1 | 1 | 1 | **0** |
| Chat messages labelled correctly (of 149) | 140 | 145 | 146 | - |
| Follow-ups joined to their task (of 45) | 30 | 35 | 36 | - |
| Model calls, cost, time | 124, $0.0728, 10 min 52 s | 128, $0.0700, 10 min 1 s | 128, $0.0757, 9 min 23 s | no model calls |

**What the results show:**
- The model and Python on their own did best in Test 11 (81 of 85), and the allocator broke no workshop rule in any run.
- With the key-informed review, every expected case was covered and no exception was allocated. All 85 allocations separately matched the compared fields and were reported on time; 26 source rows remained unresolved.
- The "after review" column is the app's ceiling, not a measured human result, because the simulated dispatcher knew the answers.
- The cancelled order (CASE-097) was recommended in all three historical runs; the key-informed review stopped it by changing its intent to a question. Since 24 October, a Python check in verification sends recognized possible cancellation or hold wording for a known order to dispatcher review; it never cancels an order itself. The dispatcher can then select **Cancel this request**, which leaves the request out of the plan with no queue time reserved; an undo brings it back. A free replay of Test 11's saved model answers, with no model calls, held all 15 exceptions with no unsafe allocation and kept 81 of 85 allocations. It is a replay, not a fresh run, so the table above is unchanged.
- Scores varied from 73 to 81 across three identical setups, so a single run's score is indicative only.

The [evaluation guide](evaluation/README.md) explains the test data and scoring. The [Test 10 report](backend/docs/evaluation/GOLDEN_100_RUN_REPORT.md) analyses the failures of the first two runs, and the [Test 11 report](backend/docs/evaluation/END_TO_END_TEST_2026-10-22.md) records the dispatcher's review.

AI custom-created this test set after repeated project experiments. Its questions and dispatch requests span several difficulty levels, designed to resemble real-life situations and target weaknesses in our system. **Three team members divided the work and comprehensively hand-reviewed the entire set, line by line. This review was done by humans, not AI.** Their comments and the documented preference rules were reconciled into the [human-team golden key](backend/docs/evaluation/extended_dispatch_100_human_team_golden.json). The [review record](backend/docs/evaluation/extended_dispatch_100_REVIEW.md) preserves the source workbook, corrections and provenance.

The [feature overview](FEATURES.md) describes the recorded capabilities and evidence. The [backend guide](backend/README.md) covers implementation details.

## Run locally

Use an existing Node.js installation and `uv`. The backend requires Python 3.13.14 and does not download Python automatically. Project dependencies are installed inside the repository.

From the root of `AI-Assisted-Factory-Dispatcher` (the folder containing `backend/` and `frontend/`), start the backend:

```sh
cd backend
uv sync
uv run fastapi dev main.py --host 127.0.0.1 --port 8000
```

In a second terminal, starting from the repository root:

```sh
cd frontend
npm ci --cache ./.npm
npm run dev
```

Open `http://127.0.0.1:3000`. The API documentation is at `http://127.0.0.1:8000/docs`.

Starting these servers does not process a conversation or call an AI model. A fresh clone has no local run output or review checkpoints, so its run list starts empty. The [published results](evaluation/README.md) can be read without running the pipeline. Processing a new conversation is a separate action that can make paid calls; read the [backend guide](backend/README.md) before starting a run.

Selected [experiment notebooks and development notes](experiments/README.md) are included for reading through the earlier work. The original working notebooks, supplied reference documents and saved test snapshots remain local. Some comparison tests require those local files.

## Repository layout

| Location | Contents |
|---|---|
| `evaluation/` | Public guide to the datasets, answer key, recorded results and scoring method. |
| `experiments/` | Earlier notebooks, selected debugging examples and the development timeline. |
| [`frontend/`](frontend/README.md) | Web screens, API calls, local setup and browser tests. |
| `backend/` | Chat processing, allocation, dispatcher review and API code. |
| `backend/config.toml` | Input paths, model settings, batch sizes and dispatch date. |
| `backend/data/` | Orders, workshops, example conversations and the extended test dataset. |
| `backend/data/extended_dispatch_100/` | The 100-case test set: chat, orders and workshops. |
| `backend/docs/evaluation/` | Answer key, team review, run reports, charts and the log of paid test runs. |
| `backend/eval_harness/` | Harness evaluation of the allocation rules, and its results. |
| `backend/output/` | Local runs, cached answers and checkpoints; excluded from Git. |
| `harness/` | The supplied simulator, kept unchanged. |
| `docs/` | System design, project plan, presentation notes and the engineering log. |

API keys belong in the backend environment, never in browser code. Local environment files, application databases, generated run output and backups are excluded from version control. Selected synthetic test data is included. Optional LangSmith tracing sends run data to its external service when enabled.

Current work focuses on integrated journey verification, known correctness gaps and further evaluation. The latest recorded checks, on 24 October 2026 after the cancellation change, passed 170 backend and 66 browser tests. Docker and deployment are left until the end.
