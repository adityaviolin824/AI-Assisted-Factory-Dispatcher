# 03. Order processing files explained: saved inputs, results and AI answers

Prepared: 13 October 2026.

Checked against the current Python modules: 19 October 2026. Processing-only runs, full pipeline runs, allocation history and optional reports are distinguished below.

Previous explanation: [02. Task verification demo](02-task-verification-demo.md).

The current application uses the Python modules. Notebook 05 remains their experimental reference, with intentional differences documented in the tests. Which files appear depends on the entry point:

| Entry point | What it does |
|---|---|
| `run_intake_and_processing.py` | Saves processing inputs, state and model-call records. It stops before allocation and does not create `plan.json`. |
| `run_allocation.py <run folder>` | Reads the explicitly selected run's processing files and saves its allocation plan and history. It makes no model call. |
| `run_full_pipeline.py` | Runs processing and allocation together, carrying the state directly between stages. The same run folder contains both processing files and the plan. Cache misses during processing can make paid model calls. |

These filenames describe entry points, not instructions to run them during this tutorial. The extra files from notebook 04 are historical and are listed separately at the end.

**These files preserve what came in, what AI proposed, and what the system accepted.** They are created during processing and are available when processing finishes.

The current modules and notebook **05** use fewer processing files than notebook **04**. The current files come first, followed by the extra files you may see from 04.

The examples below continue Elena’s conversation. They illustrate the contents rather than reproduce the complete files.

**1. `manifest.json` — what went into this processing session**

Think of this as the **original input record**.

It stores:

- The input’s name or label.
- All the original messages, with their message IDs.
- Which AI model each stage used, and its temperature or reasoning effort. A configured reasoning effort replaces temperature for that stage's request.
- The message date used for relative delivery words, and the default year for dates without a written year.
- The instructions given to AI for extraction, linking and verification.
- Settings such as how many messages are processed together.

For Elena’s example, part of its contents would mean:

```text
Input: our example conversation

Original messages:
    L0001: Elena asks for ORD-092 by November 20 at the lowest cost.
    L0002: Elena says to avoid BudgetWorks.
    L0003: Marcus asks for a separate order.
    ...
    L0008: Elena changes the final deadline to November 21.

Processing settings:
    Read three new messages together.
    Include up to two earlier messages for context.
```

The actual file keeps the **full original text**, including Elena’s wording, name and time.

Its purpose is to answer:

> “What exactly did we give the system?”

It preserves the original conversation even when later interpretation changes.

The manifest does **not** currently save complete source CSV snapshots, their hashes, the input data-folder path or every allocation setting. Allocation records its dispatch date, objective, workshop profiles and relevant order/queue snapshots in `plan.json`. Reproducing a run also requires its matching input data; the manifest alone is not the whole experiment.

**2. `state.json` — everything processing has established so far**

This is the **main processing record**.

It stores several kinds of information together:

| Information | Example |
|---|---|
| Which messages have been processed | `L0001` through `L0008` |
| Saved pieces extracted from those messages | Elena’s original request and each follow-up |
| The tasks created | Elena’s allocation task and Marcus’s separate task |
| Which pieces belong to each task | Elena’s task points to seven pieces |
| Each task’s current version | Elena’s task is version 7 |
| Its accepted verification | Final deadline November 21; fastest delivery |
| Missing details or questions | “What is the correct order ID?” if necessary |
| Problems requiring review | A follow-up whose intended task is unclear |
| Lists used to find related tasks | Order IDs, source message IDs and recent task IDs |
| Messages treated as unrelated to a task | A greeting, for example |

For Elena, the relevant contents would mean:

```text
Task: T:L0001:J1
Current version: 7
Verified version: 7

Connected pieces:
    L0001:J1
    L0002:J1
    L0004:J1
    L0005:J1
    L0006:J1
    L0007:J1
    L0008:J1

Accepted current requirements:
    Order: ORD-092
    Deadline: November 21, 2026
    Preference: fastest delivery
    No requested workshop
    BudgetWorks is no longer excluded

Original evidence:
    All seven connected messages remain available.
```

That keeps **the history and the current interpretation together**, while keeping them distinct.

For example, “avoid BudgetWorks” remains in the original evidence, even though it is no longer an active exclusion.

If a follow-up cannot be connected confidently, this file also retains something like:

```text
Unresolved follow-up:
    "Use the other workshop instead."

Possible tasks:
    Elena's request
    Marcus's request

Reason:
    It is unclear which request or workshop the message refers to.

Link outcome:
    Kept unresolved for the dispatcher.
```

The possible effect on other tasks is calculated later from these saved records. Those tasks continue through verification and planning; the plan marks their results provisional when this unresolved input might change them. The candidate list is not a confirmed link, and it is not a stored list of tasks automatically held from allocation.

**This file is updated as processing progresses.** We do not create a separate complete copy after every step. It holds the latest saved processing position, while the original messages and connected evidence remain preserved.

Its purpose is to answer:

> “What has the system done with the conversation, and what is the current result?”

**3. The `calls` folder — what AI was asked and what it answered**

This folder contains individual records of the AI requests.

There are three types:

| Filename begins with | What the request concerns |
|---|---|
| `intake-` | Finding requests and follow-ups inside messages |
| `link-` | Deciding which existing task a follow-up belongs to |
| `verify-` | Interpreting the task’s current requirements |

A linking record for Elena could contain:

```text
Stage: linking

New follow-up:
    "BudgetWorks is allowed again."

Possible tasks supplied:
    Elena's task, with its existing evidence
    Marcus's task, with its existing evidence

AI answer:
    Attach this follow-up to Elena's task.

Supporting quotation:
    "Update to my ORD-092 request..."
```

A verification record could contain:

```text
Stage: verification

Task supplied:
    Elena's task, version 7

Evidence supplied:
    All seven quotations and their evidence IDs

Order facts supplied:
    The recorded information for ORD-092

AI answer:
    Allocation request
    Current deadline: November 21, 2026
    Current preference: fastest delivery
    Earlier BudgetWorks exclusion has been replaced
```

For a completed model response, these records also store the model and settings, raw and parsed answers, token usage and elapsed model time. A locally reused answer has `reused_response: true`; its recorded tokens and time describe the original call, so they must not be counted as new spending or new model time. A failed API attempt can leave an incomplete record with an error type/status and no returned usage. Missing usage is unknown, not proof of zero cost.

**These are records of AI’s proposals. They are not automatically accepted results.**

Suppose AI wrongly proposes November 21, **2027**:

- The AI request record preserves that answer.
- Code rejects the unsupported year.
- `state.json` records the review outcome rather than accepting that deadline.

That distinction lets us investigate:

> “Did AI misunderstand the request, or did something go wrong when checking its answer?”

A `link-` file appears only when a follow-up actually needs an AI linking request. A conversation containing only independent requests may have no linking files.

**4. The `response-cache` folder — saved answers that can be reused**

This is a shared collection of saved AI answers, used across processing sessions.

Its purpose is to avoid asking and paying for **the same AI request again**.

For example:

```text
Earlier session:
    AI was given Elena's version 7 task,
    the seven messages,
    the same instructions and settings.

Saved answer:
    Deadline November 21.
    Fastest delivery.
    BudgetWorks exclusion withdrawn.
```

If another session asks that exact same question, the system can reuse the saved answer.

"Exact same" is checked using a fingerprint of the stage, its model, temperature or reasoning effort, prompt, payload and response schema. A change to any of these can require a fresh paid answer. The cache is shared only within the configured output folder.

If Elena adds a new correction, the verification request changes. The old answer does not qualify as an answer to the changed request.

There is an important distinction between this folder and `calls`:

| Location | Purpose |
|---|---|
| `calls` | Record what this particular processing session asked and received |
| `response-cache` | Keep answers available for reuse by later sessions |

Even when an answer is reused, the current session gets a record in `calls`.

**A cached answer can still contain a mistake.** Saving it does not mean its interpretation passed every check. Reused answers go through the checks again.

**5. What allocation reads now**

Allocation receives the checked tasks directly from the processing record already carried through the run.

It uses their current verified requirements, such as Elena’s final deadline and preference.

The saved files provide an inspection record of that processing. Notebook 05 and `run_full_pipeline.py` do not need a separate transfer file to pass tasks into allocation. The standalone `run_allocation.py` instead reads `manifest.json` and `state.json` from the run folder explicitly named on the command line. It never chooses a run from a `current-run.json` pointer.

`plan.json` is created **after allocation planning**, so it belongs to the next stage. It contains workshop comparisons, recommendations, reviews, clarification/reference rows, source message IDs and the resulting tentative queues. It is a preview, not a set of committed assignments.

The plan also records `processing_complete` and any inputs without an outcome. A partial run can produce a partial preview; use complete runs for evaluation. Potentially affected tasks are listed in `review_warnings`. A raw decision can remain `recommendation` while its summary row says `provisional_recommendation`, so consumers must read the warning and summary fields too.

**6. Other current output files**

| File or folder | When it appears and what it means |
|---|---|
| `plan-history/` | A timestamped copy is saved whenever the module creates a plan. Earlier plans stay available. Replanning does not change `manifest.json` or `state.json`. |
| `plan-<objective>.json` | Setting an explicit allocation objective saves its plan separately instead of replacing the default `plan.json`. The plan history keeps a copy too. |
| `run_report.md` | The separate `make_run_report.py` command produces a readable report from a saved run, optionally scored against a supplied answer key and data folder. The pipeline does not currently invoke that command automatically. No model call is needed. |
| `dispatcher-decisions.json` and `dispatcher-plan.json` | Notebook 06 Part 8 saves these after dispatcher decisions are entered and its save cell is run, with history copies. They do not replace the original processing files or `plan.json`. |

Notebook 06 Part 9's Gradio screen keeps draft decisions in the browser session and recalculates without saving files or calling a model. This is separate from Parts 1-7's explanations, which can make paid calls on an explanation-cache miss. These are dispatcher prototype outputs and behaviour, not extra processing handoff files.

**7. The extra files from notebook 04**

If you are looking at outputs from **04**, you may also see these files:

| File | What it stores | Simple example |
|---|---|---|
| `summary.json` | Counts and processing completion status | “8 messages processed, 2 tasks, 1 ready, 1 requiring clarification.” |
| `verification-progress.json` | Accepted verification records, including those still needing clarification | Elena’s interpreted deadline and preference; another task’s missing details |
| `link-review.json` | Follow-ups that could not be connected confidently | “Use the other workshop” plus possible tasks and the reason for uncertainty |
| `task-review.json` | Tasks whose interpretation failed a check or was held because of unresolved input | Task version, original evidence, review reason and related AI request record |
| `order-tasks.json` | The completed processing results supplied to allocation | Accepted verified tasks plus the separate processing review lists |
| `current-run.json` | Which processing session allocation should look at | The identifier of the latest started session |
| `superseded-handoff-…json` | An older transfer file retired after a later incomplete save | A preserved older result that should no longer be used for allocation |

Those older files separate out information that notebook 05 mostly keeps together in `state.json`, or carries directly between stages.

The table describes historical notebook-04 behaviour. In the current modules, uncertain related inputs produce provisional warnings rather than automatic holds; complete tasks do not depend on an `order-tasks.json` handoff file.

In 04, **“processing complete” means every input has a recorded outcome**. That can include clarification or review. It does not mean every task is ready for allocation.

The easiest way to remember the current files is:

| File or folder | Question it answers |
|---|---|
| `manifest.json` | What did we start with? |
| `state.json` | What did processing establish? |
| `calls` | What did we ask AI, and what did it answer? |
| `response-cache` | Have we already asked this exact question before? |
| `plan.json` | What does the deterministic allocator recommend, and why? |
| `plan-history` | What did earlier previews contain? |
| `run_report.md`, when generated | How did the recorded run perform, including any key-based score? |
