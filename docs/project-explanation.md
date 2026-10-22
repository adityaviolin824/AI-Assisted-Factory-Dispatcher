# Project explanation for presentations

Development and presentation notes for [AI-Assisted-Factory-Dispatcher](../README.md). The application is named SweaterCo Dispatch Copilot.

Current implementation status updated: 13 October 2026; the graph's dispatcher review pause added 20 October 2026. The historical debugging and run evidence below retains its 10 October processing v3/allocation v4 baseline. Use this to explain the project to the professor. The [backend README](../backend/README.md) explains the implementation in more detail, and the [project plan](project-plan.md) distinguishes completed work from what comes next.

The [experiment guide](../experiments/README.md) gives a reading order for the earlier notebooks. Its [development notes](../experiments/development-notes.md) explain four investigations, and the [timeline](../experiments/timeline.md) connects them to the later modules and API.

**MVP goal and latest decision, 21 October 2026:** produce an explainable dispatch table that the dispatcher controls. The dispatcher finishes the whole choice set locally, then one **Approve all** authorizes Python to apply it, schedule flexible work, save immediately and show the final table with changed rows. The batch-finalization endpoint was implemented on 21 October. The older per-edit review description below records the earlier stage. Reallocation and the optional review/approval after it remain pending. Docker and deployment come at the absolute end.

## The problem we are solving

A factory sends batches to outside workshops when it needs extra capacity. The dispatcher must consider what each workshop can make, its available capacity and queue, whether it is allowed to receive the work, and the customer's requirements. Requests arrive as informal messages, sometimes with missing information or later corrections.

Our aim is to turn those messages into checked requests and produce an explainable workshop recommendation. Usually, avoiding late delivery and getting the work back promptly comes first. For delicate or expensive work, a lower risk of defects may deserve much more importance. Cost and workload distribution also affect the choice.

There are two different kinds of speed here: how quickly the software answers, and how quickly a workshop can deliver the batch. Improving the first does not prove that we improved the second.

## What the current prototype does

The current backend uses Python modules, run together by `run_full_pipeline.py` through an eight-node LangGraph graph:

1. Read a chat TXT snapshot and assign source-message IDs.
2. Extract jobs in owned batches and validate the original quotations and written order references.
3. Create separate requests or attach supported follow-ups. Corrections increase the task version and invalidate earlier verification.
4. Verify current task evidence, look up trusted order/workshop facts and calculate supported dates and readiness in Python.
5. Route ready allocation tasks to the deterministic scheduler and retain clarification, reference and review outcomes.
6. Plan earliest deadline first using a temporary queue copy, then save recommendations, calculations, review warnings and input accounting.
7. Pause for the dispatcher's review (since 20 October 2026). The paused review is kept in a SQLite checkpoint; the dispatcher corrects facts, chooses workshops or accepts shown lateness, sees the recalculated review, and finally approves it all. Approval saves the review last shown as JSON without planning again. No model is called in the review.

An unresolved follow-up no longer automatically stops the original task. A usable recommendation can be shown as provisional, with the unresolved message retained for dispatcher review. Missing essential facts and genuine verification failures still prevent allocation. A recommendation is a preview, not a committed assignment.

Notebook 05 remains an unchanged experimental reference. The current modules deliberately differ in model settings, provisional warnings, partial previews and plan history; the tests declare these differences. They do not use the earlier v3/v4 disk handoff or resume contract. The mock SQLite chat exports input manually and is not connected to the pipeline or an assignment database.

The model handles language interpretation. Python validates evidence and computes eligibility, dates, queues, cost, rankings and allocation. A well-formed model response can still misunderstand a request.

## Why duplicate counts were a real engineering problem

The earlier parser used overlapping message groups. In the saved run inspected on 6 October, 30 source requests appeared 48 times across those groups. The separate model deduplication step returned all 48 occurrences, and the code accepted them. Verification then checked each occurrence separately, sometimes giving different judgments to copies of the same request.

The proven problem was the missing acceptance rule around overlap duplicates. The investigation did not prove that the model itself was incapable, and the saved files did not establish which edited prompts had produced the results. More prompt editing alone could not provide a reliable guarantee.

V3 prevents the same source message from being accepted again just because it appears as context. It also checks evidence, tracks separate jobs and invalidates old verification after a correction. However, it still needs evaluation for semantic mistakes, such as misunderstanding whether two differently worded requests are the same job.

An order ID is not a safe deduplication key. A status question and an allocation request can mention the same order and remain different tasks. Likewise, two jobs inside one message must not collapse into one just because they share a source line. Message, item, task and order counts describe different things.

The detailed historical audit records the failure and its limits. It is not a claim about today's model accuracy.

## What the latest fixes show

Two observed processing failures were addressed: context-only messages in the model's non-task list caused valid intake batches to be rejected (P1), and equivalent date wording such as `Mar 23` / `March 23, 2026` failed an exact-text deadline check (P5). The current date check still requires the selected source to support the same calendar date, including any written year. The issues record preserves the causes, changes and recorded verification.

Expected interpretation failures are preserved as review records while other work continues. The latest change replaced automatic holds with provisional allocation previews: the original request can be checked and planned, and a warning asks whether an unresolved input changes it. Warnings are saved in `review_warnings`; provisional labels appear in `summary_rows`. Review records reserve no capacity, while provisional recommendations reserve tentative workload like other recommendations. No candidate relationship is presented as a confirmed link.

Luna intake also fixed the recorded demo's follow-up detection: correct labels improved from 3/7 to 7/7 under the same prompt and context window, retaining the previously dropped deadline. That did not fix every downstream link: the quality addition and short replies can still require review. The [problem records](../backend/problems_solved/followup_detection_fixed_with_luna.md) distinguish the measured improvement from remaining failures. API, file and programming errors still stop execution visibly.

The complete third run also exposed a remaining language error: R12 said nothing new should go to QuickStitch, but processing recorded QuickStitch as a reference rather than an exclusion. The first v4 plan consequently recommended it. B17 now requires review when the winning workshop is recorded only as a reference, leaving its queue unchanged. That prevents this observed unsafe recommendation; it does not prove that workshop-role interpretation is correct in every case or apply the instruction globally to other requests.

## How the workshop recommendation is made

The system first removes workshops that fail status, product category, batch cap or the request's workshop restrictions. The normal plan also requires estimated on-time delivery. If no allowed workshop meets the request, it records the issue for review and reserves nothing.

V4 names the least-late option when the deadline cannot be met, and can show an on-time alternative without an unusable requested destination. These options support the dispatcher's next decision; they do not silently change the request or make an assignment. The same distinction must remain visible in the eventual interface.

Estimated delivery time combines the existing queue, production time, expected rework and transport. This means choosing the lowest queue alone would be insufficient: a workshop could have a short queue but slow production or greater expected rework.

For the default or fastest preference, candidates are compared by lateness, then estimated delivery time, then cost. Since the normal plan has already removed late candidates, delivery time and cost distinguish the survivors. A cheapest preference starts with cost. A quality preference starts with defect rate, then delivery time and cost.

This already supports an explicit request to prioritise quality. A general rule that recognises delicate or expensive work still needs a defined input and evaluation. The current hybrid combines lateness, cost and planned piece share; it has no direct defect-rate weight. We should not present task-specific quality weighting as completed work.

Workshop defect rates and delivery estimates are uncertain business inputs. The calculation makes the decision inspectable; it does not guarantee a particular batch will arrive on time or without defects.

## What we can honestly claim from the evidence

- **Implementation:** 69 offline tests pass across processing, allocation, the harness adapter and the full graph. They check source/schema contracts, deterministic rules, queues, cached end-to-end equivalence, failures, partial accounting, history and provisional warnings.
- **Saved-state regression:** an independent review replayed all 14 saved states without changing them. Decisions and tentative queues matched the earlier reference for those same tasks; R14's summary gained its intended provisional warning. The formerly held tasks were not freshly verified.
- **Language interpretation:** the recorded all-Luna run on the supplied 30 requests achieved 30/30 intake labels and 28/30 readiness agreement with the development key. It contains no follow-ups, so it does not establish linking accuracy. Model comparisons and failures are recorded in [the experiments](../backend/docs/evaluation/PROMPT_TESTING_RESULTS.md).
- **Scheduling:** the unchanged 120-order harness replay compares six policies with three baselines under normal and shock conditions. In the normal replay, the default records 8.1 mean delivery days and 2% late versus random's 21.5 days and 34% late. Baselines still win on some cost and defect metrics. Preserve all six official metrics and [the complete tables](../backend/eval_harness/results/harness_results_2026-10-15.md).
- **Observability:** local manifests, state, call records and plan/history make the decisions inspectable. The 15 October 21:19:26 cached full-pipeline run was confirmed remotely in LangSmith, including its final plan and 34 chain spans.

The supplied chats have informed development. Unseen examples, repeated fresh-model samples, separate explanation scores and at least ten analysed failure cases are required before broader claims. Cached replay establishes repeatability of saved answers, not model stability. DeepEval code is retained for reference but is not integrated. The current docs update made no paid model calls.

## What is still to be built

The working pipeline is modularized, including routing, allocation, the batch graph and its dispatcher review pause. Persistent assignments, live order-status enforcement, clarification replies, reallocation, safe changes of workshop and the product interface remain future work; the dispatcher's approval is saved JSON, not a committed assignment. The allocator records order status/stage and warns for completed historical orders; it does not enforce a live status policy or calculate remaining-stage work. Calendar handling, standing instructions and quality-sensitive policy choices also need explicit decisions.

The planned reallocation workflow keeps the existing assignment active while a proposed move is checked. A confirmed move must change the assignment and its reservations together, preserve history and resist repeated submissions. Started or completed work needs a separate policy; we cannot simply erase its production time.

The [system design](system-design.md) preserves these requirements without presenting them as implemented features.

One recognized edge case for the professor is a deadline mismatch between a chat message and the order CSV. For example, the CSV might say April 10 while the message says April 8. Our preferred future approach is to use the trusted CSV date until an authorized update and explicitly show the discrepancy to the dispatcher, because either source could be outdated. We have deferred automatic comparison and alerts to keep the prototype manageable. The current code still allows a confirmed chat-date override; documenting this limitation does not implement the future policy.

## How the planned app should work

The product direction has three pages:

- **Landing/demo page:** explain the factory problem, actual capabilities, architecture, measured results and limits, then provide demo access.
- **Operations page:** factory users submit messages in chat channels, see processing outcomes and answer source-linked clarifications. Later voice input produces a transcript for confirmation before entering the same text pipeline.
- **Dispatcher console:** one dispatcher reviews the unified work list, original evidence, allowed/rejected workshops, calculated alternatives and warnings, then takes a permitted assignment or reallocation action. A supported assistant explains recorded choices and calls code for new comparisons.

Build the text journey first. An allocated order can also need review of a proposed move; its current assignment remains visible and active until a valid replacement commits. Voice and multiple live channels follow a measured core flow. Exact visual styling is still to be designed. The [frontend plan](system-design.md#8-planned-frontend-pages) records the page purposes and state distinctions.

LangGraph already connects the module processing and allocation steps in `backend/app_full_pipeline/pipeline_graph.py`, as it does in notebook 05. Since 20 October 2026 it also waits for the dispatcher's review with `interrupt()`, keeping the paused review in a SQLite checkpoint so it can be answered after the program ends. Waiting for a clarification reply is still planned. It does not choose workshops through model arithmetic. In the planned workflow, a reply resumes the same request, a correction invalidates the old verified version, and a commit needs a database transaction with fresh task/queue checks. See the [planned architecture](system-design.md#7-planned-application-architecture-and-langgraph).

The recorded technical direction is Next.js/React for the interface, Python with likely FastAPI for the backend, and project-local SQLite for the first operational store. These are planned choices. Their purpose is to keep the same verifiable capability, capacity/queue and permission checks behind every input channel and visible to the dispatcher.

## Contributions and questions to prepare

Aditya identified the confusing counts, proposed ownership/set-based handling and batching, and set the requirements for understandable code, visible execution and task-dependent quality priorities. Codex and Claude Code assisted with investigation, implementation, controlled verification and documentation; the engineering log attributes individual changes. Earlier log entries also record allocation work adapted from Zhang. Use that history to describe individual contributions accurately; do not claim that AI-generated work was independently written or verified by a team member.

Before presenting, be ready to answer:

- Why can one message contain several tasks, while several messages can describe one task?
- What proved the old deduplication failure, and what remains uncertain about model interpretation?
- Why must a correction invalidate the old verification?
- How do queue, capacity, expected rework, transport and hard restrictions affect ranking?
- When should quality outrank speed, and what evidence would justify the policy?
- Why must a review item reserve no capacity, and how is a preview different from an assignment?
- Why does B17 ask for review, and which interpretation errors can still get past that safeguard?
- What belongs in LangGraph state, and why does an assignment still need a database transaction?
- Why should voice enter the same pipeline, and how will the operations page differ from the dispatcher console?
- What did you personally investigate or change, what did the AI assist with, and how would you verify the result again?

The interview preparation rules describe how to practise these explanations one question at a time.
