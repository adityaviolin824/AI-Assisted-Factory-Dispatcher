# Project handoff: frontend and API connection

Updated: 21 October 2026. Start here when working on the frontend. This summarizes the existing backend plans and progress so a new coding agent does not need to reconstruct the project from old conversations.

## Current instruction from Aditya

**The goal for this phase is to design and connect both core interfaces—Operations chat and Dispatcher—in one Next.js application, and verify the journey through dispatcher review.** Include the small required chat API bridge; today's four endpoints are a starting point, not the finished scope. Do not treat chat as an optional later page or call a quote-only viewer the completed chat frontend.

**Design direction:** both interfaces should have sophisticated, distinctive dark themes. Use **build-web-apps:frontend-app-builder** as described in the [frontend plan](frontend/FRONTEND_PLAN.md#3a-visual-direction-for-both-core-interfaces). Avoid generic AI/SaaS templates, purple accents, decorative gradients, filler cards, fake statistics and unreadable dark styling. This handoff does not prescribe exact colors, fonts or layouts. Preserve working functionality while designing both surfaces together.

**Latest review decision:** the dispatcher completes the whole set of choices locally, then clicks **Approve all** once. Python applies that complete set, rearranges the other work, saves the final result immediately and shows what changed and why. There is no mandatory second approval. Nothing containing unfinished dispatcher choices is sent to the backend or saved before that click. This supersedes the earlier save-and-recalculate-each-edit workflow.

**Docker, containers, Compose, deployment and related infrastructure belong at the absolute end, after the frontend integration and the later dedicated backend work. Ignore them for now. Do not start Docker, create container configuration or make Docker availability a prerequisite for frontend work.** Existing empty infrastructure files can stay untouched.

Do not spend this phase improving allocation rates, comparing models, tuning prompts, running the golden dataset or investigating every old backend result. Aditya will do dedicated backend improvement and evaluation work later. Keep current results visible and honest; a low allocation count does not block building the interface.

This changes the earlier Docker-first frontend plan. It does not relax secret protection, Git safety, isolation or verification of the actual UI/API behavior.

## The end goal of this assignment MVP

Produce an **explainable dispatch table that helps the dispatcher choose where each batch should go**. It should show the chosen workshop, expected delivery, relevant costs/quality facts and why a row was selected or left unresolved. Let the dispatcher finish his choices and produce the final table, including a before/after explanation of any rearrangement.

The human-facing journey includes entering the conversation in Operations chat, explicitly passing a stable snapshot into processing, then opening the corresponding Dispatcher result. The final table does not remove the need for its chat input interface.

This is an assignment demonstration with room for later real-world improvements. It is not a manufacturing execution system: no production tracking, real workshop notifications, live queue ownership or deployment-readiness project is required for this increment. The separate assignment evidence still matters: demonstrate the workflow and compare the automatic scheduler with the supplied baselines, while evaluating message interpretation separately. That backend evaluation comes later, not as a prerequisite for designing the frontend. Do not promise a particular grade or call the current prototype production-ready.

## What the product does

The factory receives garment-order requests in chat and needs to choose an outside workshop. The [Factory Primer](reference-documents/Factory_Primer.md) describes three questions: can the workshop make the batch, can it take the work given capacity and queue, and is it allowed to take it?

- The **LLM reads the conversation** and extracts requests, follow-ups, constraints and questions.
- **Python checks facts and calculates** eligibility, dates, delivery estimates, costs, rankings and allocation previews.
- The **dispatcher reviews and decides**. For an identified batch and known workshop, assume he knows why he chose it. Keep that workshop fixed, even if it is late or overrides normal automatic-selection restrictions, and fit other work around it. Record the consequences without demanding justification or adding a second confirmation. Do not invent missing batch identity or pretend an unimplemented operation succeeded.
- The **frontend displays this information and sends structured decisions**. It must not recreate the allocator in JavaScript.

The agreed frontend direction is Next.js, React and TypeScript, with a readable implementation and a polished dark design for both interfaces. FastAPI remains the backend; there is no need for an additional Express server or another business-logic layer.

## Progress: what already exists

| Area | Implemented behavior | Important boundary |
|---|---|---|
| Intake and processing | Read chat, extract requests, link supported follow-ups, verify tasks and retain source evidence. | Uncertainty can remain for review. A new processing run can make paid model calls. |
| Routing and allocation | Route tasks, check workshop rules, calculate comparisons and build a tentative shared plan. | A preview does not commit workshop workload or change the source CSVs. |
| LangGraph | Run processing and allocation, then pause for dispatcher decisions; resume the same review. | A saved plan is different from an editable paused thread. |
| Dispatcher review, existing code | Correct facts, choose workshops and recalculate a review after submitted edits; accepted edits are checkpointed. | This existing per-edit persistence is superseded as a product requirement. Do not wire frontend selections to it. |
| Final approval | An empty `approve_all` labels and saves the previously calculated review. Since 21 October 2026, `"then": "finalize"` applies a whole batch of choices with one calculation, then approves and saves it with `changes` (rows that differ from the review shown). | A refused batch saves nothing. No operational assignment database or live dispatch exists. |
| FastAPI | Five endpoints read saved runs and show, answer or finalize paused reviews; review reads create no checkpoint file (21 October 2026). | No chat-submission or processing-start endpoint yet. |
| Verification | The latest recorded backend suite passed 127 offline tests on 21 October 2026. | Historical evidence, not a newly rerun test result or a model-accuracy score. |
| Frontend | The Next.js app and read-only dispatcher are present. [BUILD_STEPS.md](frontend/BUILD_STEPS.md) records their earlier checks. | Operations and Introduction are currently placeholder source pages. This planning update implements neither interface nor a new API; chat remains required work. |
| Existing mock chat | A Streamlit prototype already stores named participants' messages, shows shared history and exports stable snapshots. | It is the behavioral reference for the core chat frontend; its manual notebook handoff is not the completed connected journey. |

The backend implementation and HTTP contract are the starting point. Notebook 06 is a historical experimental reference; its older per-row approvals must not replace the module's current single final approval.

**Required integration work:** the chat message/history/snapshot/processing bridge and one-click dispatcher batch submission need small backend contract changes. These Markdown changes implement neither. Keep current behavior, historical checks and the required target separate; do not remove chat from scope because the bridge is missing.

## Chat behavior to carry forward from the mock

Read the [mock README](backend/experimentation_notebooks/mock_frontend/README.md), [approved plan](backend/experimentation_notebooks/mock_frontend/PLAN.md) and [source](backend/experimentation_notebooks/mock_frontend/app.py). Preserve names, receipt times, original text, ordered shared history, Send success/failure behavior, retry identity and a stable conversation snapshot/export. Start with one room and no authentication/voice/channel-management expansion. Reuse or narrowly extract these responsibilities behind FastAPI; do not copy the old Streamlit appearance or run notebooks from the browser.

**Send stores chat input without model calls. Process conversation is a separate explicit action** for a chosen snapshot. It must return the linked run/review and full source context. Use a guarded offline fixture/replay to test model-backed processing without spending; a real paid run still requires separate authorization. Explicitly sent chat inputs may be stored as in the mock; unfinished dispatcher allocation choices remain local until Approve all. Do not process on each Send/keystroke or reconstruct complete messages from plan quotations.

## The API the frontend can use now

| Request | Purpose |
|---|---|
| `GET /runs` | List saved runs, their labels and message counts. |
| `GET /runs/{run_id}` | Read the original plan and the final dispatcher plan when one exists. `plan.workshop_profiles` already supplies the workshop dropdown data. |
| `GET /reviews/{thread_id}` | Read a review waiting for dispatcher input. |
| `POST /reviews/{thread_id}/answer` | Applies/checkpoints edits, or accepts an empty final approval. Returns the current review and any refusal. The frontend sends only the empty approval here. |
| `POST /reviews/{thread_id}/finalize` | Accepts the complete decision set `{"decisions": [...]}` and finalizes it in one submission (21 October 2026), or refuses it with the reason and saves nothing. |

Run IDs and thread IDs are different. A finished or unknown thread has no paused review and returns 404. On the last filesystem check, the API's configured output folder had saved plans but no paused review; editing tests therefore need a disposable paused fixture rather than a paid processing run.

The Python review calculation makes no model call. An HTTP 200 can still contain `refused`: show it as **Last answer was refused**, preserve the last saved result and let the dispatcher correct the local input. Do not treat a successful HTTP status as proof that decisions were applied.

### The user interaction to build

1. Select a saved run and inspect its outcomes, source evidence and workshop comparisons.
2. Open a matching paused review when available.
3. Make all supported fact corrections and workshop choices in local page memory. A later choice replaces the earlier local choice for that task. Show pending choices, without claiming recalculated estimates or saved decisions.
4. Dropdown clicks, checkboxes and form edits make no mutation request, trigger no Python replanning, resume no graph and write no database/checkpoint, JSON draft, browser storage or draft history. There is no autosave or per-row Apply action. Unsaved choices may be lost when the page closes; make their unsaved status clear.
5. Click **Approve all** once. Submit the complete final set of choices as one batch, not a series of per-task requests. Python validates structural inputs, preserves the dispatcher's destinations, rebuilds from the original queue snapshot and fits the remaining work around them.
6. Save the resulting final dispatch table immediately and return it with the change report. The dispatcher authorized this rearrangement by submitting the set; do not require approval of another preview.
7. Display approved and unresolved rows honestly. Reopening reads the final saved result. Existing saved input/automatic-plan records are preserved; the no-write rule concerns unfinished dispatcher decisions, not deletion of the source run.

The current `accept_late` helper requires a separate answer, and current approval takes no edits. Those are implementation limits to resolve in the batch contract, not instructions to send hidden intermediate requests. Keep original blocker/task identities and source facts. Until the batch path is implemented and checked, use read-only views and fixtures for the target UI rather than violating the no-write rule.

Opening the page and reading a saved run/review must not create or update dispatcher storage merely as a side effect. The existing checkpoint-opening behavior also needs checking against this boundary when the batch API is implemented.

## What reallocation means here

For this MVP, rearrange batches in the proposed dispatch table; do not model recalling work already started at a real workshop.

An illustrative chain: the dispatcher fixes order A at W1; it adds two queue days there; order B would now miss its deadline at W1, so Python finds an on-time W2 option; that changes W2's queue and can move order C. Keep the dispatcher's explicit destinations fixed throughout and use the existing deadline-based scheduling policy for the flexible work. Do not invent a new priority model from this example.

After processing the whole submitted set, show one before/after table with task/order ID, previous and final workshop, previous and final delivery estimate, deadline, and the recorded reason for each change. Include unchanged manually fixed rows and unresolved rows; show workshop queue totals before/after as well. Explain actual calculated effects without paid model calls. If no allowed on-time option exists for flexible work, show that outcome honestly rather than inventing a successful move.

The current path is **approve once, save immediately, then inspect the report**. The previously requested optional **Review again after reallocation** remains a parked future mode, not a mandatory second approval. Reallocation controls remain disabled until their actual behavior is implemented and tested.

## Frontend scope and build order

1. **Design both core interfaces together:** preserve the existing dispatcher implementation, use the mock for chat behavior and follow the named design skill with broad dark-theme guardrails rather than a generic template or a fixed palette/layout imposed here.
2. **Complete Operations chat and its API bridge:** working Send/history/snapshot/export plus an explicit snapshot-processing handoff returning the corresponding run/review. Fixture-backed development can proceed without paid calls; a disabled chat placeholder is not the final deliverable.
3. **Connect Dispatcher and final submission:** show the full source conversation and outcomes, stage choices locally, implement/test the batch-finalization contract and return the saved table/change report. Do not alter retained team runs for testing.
4. **Verify both real interfaces:** check core interactions, source links, keyboard/responsive behavior and accepted-concept versus browser-rendered fidelity. Keep the introduction secondary, and report implementation/test limits honestly.

Required integration work includes the chat capture/history/snapshot/processing bridge and one-batch approval path. Smaller read-only additions can expose waiting reviews, original blocker numbers or saved source messages. Verify backend changes in small steps and keep paid execution separately authorized. The workshop list already exists. Do not expand into model-quality tuning, a dispatcher draft service, an operational assignment database or a second frontend application.

## What “working” means in this phase

- The screen shows the selected run's actual backend results, including unresolved work.
- Both core interfaces are fully designed and usable: chat captures the real conversation and connects it to the dispatcher; neither is an indefinite placeholder. The existing mock's behavior is the starting reference, not its visual styling.
- Choices stay in page memory until the single final submission; refusals preserve the last saved result and keep the local form available for correction.
- Supported dispatcher choices and their effects on other tasks are visible.
- Approval applies the complete local choice set, performs the authorized rearrangement once, saves immediately and displays the final table with what changed and why.
- No recommendation, informational alternative or provisional result is falsely shown as a committed assignment.
- A small count of automatic allocations is recorded as existing backend behavior, not hidden or optimized during frontend work.

Functional tests still matter. If a button sends the wrong task ID, a response is misread or the displayed plan becomes stale, investigate and fix that integration issue. Broader allocation performance, interpretation errors and policy improvements go into the later backend work list.

## Explicitly deferred

- Docker, containers, Compose, infrastructure setup and deployment: **absolute end; ignore for now**.
- Dedicated backend performance work: prompts/models, allocation-rate improvements, benchmarks, golden-set runs and explanation evaluation.
- Reallocation, committed assignments, live queues, multiple channels, voice and a general-purpose AI assistant. The core Operations chat is required now, not part of this deferred list.
- **Reallocate** and **Review again after reallocation** remain disabled placeholders with no API request. Preserve the second-review requirement for later.

## Safety and environment rules still apply

- No Git commands, including read-only commands or automatic repository initialization by a scaffolder. The user backed up the backend outside the project and removed its top-level `.git` on 21 October 2026; no root repository exists yet. Leave remaining metadata alone and all Git operations to the user. See [public repository check](docs/public-repository-check.md) for the ignore rules and publication limits.
- Never expose keys or inspect real environment files for frontend work. Keep model credentials in Python, never in browser code, public environment variables, fixtures or logs. If a secret appears, stop without repeating it.
- No global/system installations, sudo or Homebrew. Python uses the existing project-local `uv` environment. Frontend tooling needs an existing isolated Node environment or an explicitly agreed project-local setup; Python's `.venv` does not itself isolate Node. If that prerequisite is missing, report it before installing anything and continue independent design work. Do not bring Docker forward as a workaround.
- No dependency installation or paid model run is authorized by this document. Frontend development must not automatically process chats, call explanation models or rely on a cache hit to prevent spending.
- Keep source CSVs, supplied documents and `harness/simulate.py` unchanged. Preserve ignore rules for secrets, dependencies, caches, generated outputs and local databases.
- Work in small steps, verify what changed, report exact files and actual test results, and keep meaningful decisions in the engineering log.

## Where to read more

| Document | Use it for |
|---|---|
| [Frontend instructions](frontend/AGENTS.md) | Rules for the coding agent. |
| [Detailed frontend plan](frontend/FRONTEND_PLAN.md) | Screen details, exact decisions, payloads and acceptance tests. |
| [Backend implementation](backend/README.md) | Existing modules, scripts and run commands. |
| [FastAPI build record](backend/FASTAPI_BUILD.md) | Existing routes, API decisions, tests and limitations. |
| [Final dispatcher graph plan](backend/DISPATCHER_REVIEW_GRAPH_PLAN.md) | Current review and one-approval design. |
| [Overall project plan](docs/project-plan.md) | Broader goals and the later evaluation work. |
| [System design](docs/system-design.md) | Scheduling rules and future application behavior. |
| [Engineering log](docs/engineering-log.md) | Dated progress, decisions and verification evidence. |
| [Backend backlog](backend/docs/Pending_Improvements.md) | Later backend issues; not a checklist to finish before the UI. |

This handoff summarizes and links the backend records rather than duplicating their full history. Follow the latest user instruction when an older document still describes a different priority.
