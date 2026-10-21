# Frontend implementation plan

Updated: 21 October 2026. This is a handoff for Claude Code, not a record of an implemented frontend. Read [AGENTS.md](AGENTS.md) first. No dependencies were installed to prepare this plan.

**Current priority:** read the root [project handoff](../PROJECT_HANDOFF.md). The only goal now is to design the frontend, connect it to the existing API and verify functionality through dispatcher review. Allocation rates, model quality and dedicated backend evaluation are later work. **Docker, containers, Compose and deployment are deferred to the absolute end and must be ignored for now.** This supersedes the earlier Docker-first setup instructions.

**Latest approved interaction:** keep the dispatcher's complete choice set in page memory until one **Approve all** click. Then submit the set once, calculate/rearrange, save immediately, and show the final table plus what changed and why. No per-click mutation, draft persistence or mandatory second approval. The existing backend still uses a different edit/checkpoint/empty-approval contract; section 7 describes the required target, not an implemented capability.

**Scope correction:** both the **Operations chat interface** and **Dispatcher console** are core frontend deliverables in this same Next.js application. A dispatcher-only screen or quote-only Operations placeholder is not the completed frontend. Use the existing [mock chat](../backend/experimentation_notebooks/mock_frontend/README.md) and its [implementation](../backend/experimentation_notebooks/mock_frontend/app.py) as the behavioral reference. Include the small chat/storage/processing API bridge in the work plan instead of using its absence to defer chat. Both interfaces need a sophisticated, distinctive dark design; section 3a records the broad visual guardrails.

**Design and usability direction (Aditya, 21 October 2026, evening):** the application should be very beautiful, unique and dark; beauty and usability are the priorities of the design phase. Starting a run from the chat must be easy, and switching between Chat and Dispatcher must take one obvious action from anywhere in the app (section 3b). Authentication comes later: a future sign-in can decide whether a person is a dispatcher. For now there is no login and anyone can switch modes. When Claude Code does this work, it uses the Claude skills Aditya added (`frontend-design`, `webapp-testing`, `web-artifacts-builder`) whenever they fit; section 3a says how.

## 1. What we are building and why

This is Track 2 of the factory project: help a dispatcher send batches of garments to outside workshops. Requests arrive as chat messages, often with follow-ups, corrections or incomplete instructions. The AI interprets those messages. Python checks the facts and calculates the allocation. The dispatcher makes the final decision.

For every suggested workshop, the interface should help answer three questions from the [Factory Primer](../reference-documents/Factory_Primer.md):

1. Can this workshop make the product?
2. Can it take this batch given its capacity and existing queue?
3. Is it allowed to take it, considering workshop status, limits and request restrictions?

For ordinary automated recommendations, eligibility and deadlines come before ranking. The dispatcher can explicitly override a workshop restriction or accept lateness; show the resulting reason and warnings. Never silently substitute another workshop for a supported dispatcher choice.

The original experiment has eight workshops, 120 historical orders and 30 chat requests. Those are dataset sizes, not allocation counts or accuracy scores. The extended evaluation and the team's golden-set review can continue independently of frontend development.

### Scope for this implementation

- Two core working interfaces: Operations chat and Dispatcher, plus a small supporting introduction page.
- Design both core interfaces together, then implement/connect the complete chat-to-dispatcher journey in small increments. Preserve the existing read-only dispatcher work rather than restarting it.
- Show original requests, extracted facts, uncertainty, workshop comparisons and the backend's reasons.
- Let the dispatcher finish all choices locally and submit them once; calculate, save and show the final dispatch table with its before/after explanation.
- Include chat entry, shared history and explicit snapshot processing in this MVP's implementation scope. Implement/test the necessary API support as part of that journey; a permanently disabled Send button is not the planned deliverable. Paid model testing still requires separate authorization.
- Keep reallocation and **Review again after reallocation** visible as disabled future controls. They must send no request.

Final approval currently saves JSON. It does not send work to a workshop, update an operational assignment database or change a live queue. The UI must say this plainly.

## 2. Sources and existing implementation

Use these documents for context, then check the source for the current contract:

| Source | What to take from it |
|---|---|
| [Project plan](../docs/project-plan.md) | Priorities, evaluation requirements and the three-page direction. |
| [System design](../docs/system-design.md), sections 6–8 | Dispatcher authority, future reallocation and page purposes. |
| [Backend instructions](../backend/AGENTS.md) and [README](../backend/README.md) | Rules, commands and implemented behavior. |
| [API build record](../backend/FASTAPI_BUILD.md) | The four existing endpoints, decisions, tests and limitations. |
| [Run routes](../backend/fastapi_routes/runs.py) and [review routes](../backend/fastapi_routes/dispatcher.py) | Actual HTTP responses. |
| [Dispatcher decisions](../backend/dispatcher_review/dispatcher_decisions.py) and [plan](../backend/dispatcher_review/dispatcher_plan.py) | Accepted commands and recalculation/finalization rules. |
| [Graph review plan](../backend/DISPATCHER_REVIEW_GRAPH_PLAN.md) | The agreed single-approval workflow. |
| [Mock chat README](../backend/experimentation_notebooks/mock_frontend/README.md), [approved mock plan](../backend/experimentation_notebooks/mock_frontend/PLAN.md) and [app.py](../backend/experimentation_notebooks/mock_frontend/app.py) | Existing shared-chat behavior, input preservation, Send semantics, stable snapshot/export and message identity. Reuse these responsibilities, not the old Streamlit styling or manual-only notebook handoff. |

Some older paragraphs in the project plan still say there is no API or describe per-row approvals. The API now exists; the current modules use one final approval. Do not recreate the older workflow. Notebook 06 is an experimental reference with intentionally different approval behavior, not code to copy into React.

## 3. Keep the architecture small

Recommended: **Next.js App Router + React + TypeScript**, with ordinary CSS/CSS Modules, native form controls, React state and browser `fetch`. Next.js already supplies the frontend's Node.js server; we do not need Express or a second Node backend.

| Approach | Files and behavior | Trade-off and risk | Verification |
|---|---|---|---|
| Saved-run console only, incomplete scope | Existing dispatcher views and four existing endpoints. | Useful integration increment, but it omits the required chat frontend and is not the completed MVP journey. | Retain its checks and use it as a starting point. |
| **Two core interfaces in one app, required direction** | Design Operations chat and Dispatcher together; add the small chat API bridge, then connect snapshots, processing and final review in verified increments. | Reuses the mock chat behavior and existing Python pipeline without adding a second app or scheduler. | Check chat capture/history/export, snapshot-to-run identity, source links, local-only dispatcher edits and final submission. |
| Full application framework now | Add authentication, a job service, database-backed channels and live assignments. | Much larger scope and high risk; postpones the usable demo. Deferred. | Would need separate operational and deployment tests. |

Use the two-interface direction. This turn updates the plan; it does not implement the API bridge or authorize installations or paid model runs. Small required integration changes belong in the implementation plan rather than an indefinite future phase.

```text
Browser -> Next.js /api/backend/... -> existing FastAPI -> existing Python functions/LangGraph
```

The Next.js layer forwards requests. Python remains responsible for eligibility, task readiness, deadlines, queues, costs, rankings, reservations and final approval. React formats recorded results and collects structured decisions.

Use a Next.js rewrite from `/api/backend/:path*` to `${BACKEND_API_URL}/:path*`. For example, browser `GET /api/backend/runs` reaches FastAPI `GET /runs`. This uses one browser origin and avoids adding CORS for this first local demo. Do not add generic proxy code, Server Actions or duplicate API routes when a rewrite is sufficient. See the [official rewrite documentation](https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites).

Keep `BACKEND_API_URL` server-side. It is an address, not a model credential. Never put model keys in `NEXT_PUBLIC_*`: Next.js embeds those variables in browser JavaScript. See [environment variables](https://nextjs.org/docs/app/guides/environment-variables). Restart the frontend when changing its rewrite configuration. Do not use a static export: the forwarding server is needed.

## 3a. Visual direction for both core interfaces

Use the design skills of the tool doing the work. In Codex: **build-web-apps:frontend-app-builder**, the user-invoked `frontend-app-builder/SKILL.md` in the installed Build Web Apps plugin. In Claude Code: the **frontend-design**, **webapp-testing** and **web-artifacts-builder** skills in `~/.claude/skills/`, used whenever they fit (table below). Keep Next.js: no skill's default stack (Vite, Tailwind, shadcn/ui) overrides this existing project. The brief is deliberately broad; do not treat this plan as a prescribed palette, font, pixel layout or component arrangement.

| Claude Code skill | Use it for | Limits in this project |
|---|---|---|
| `frontend-design` | Every visual decision: its two-pass design plan (4-6 named colours, typefaces and their roles, layout with ASCII wireframes, principles), a review of that plan against this brief and against generic defaults, then building and critiquing with screenshots. | Keep the code plain CSS that a beginner can follow. A dark brief must still avoid the skill's listed defaults, such as a near-black page with a single acid-green or vermilion accent. Web fonts through `next/font` need no new package; choose them in the design plan. |
| `webapp-testing` | Checking rendered pages: start servers with its `with_server.py`, wait for the page to settle, take screenshots, read console errors and compare against the agreed design. | Run its Python through `uv run` from `backend/`. The Python `playwright` package may need `uv add` (ask first); reuse the existing Chromium and download no browser. Ask before starting servers. The Node `@playwright/test` suite remains the regression tests. |
| `web-artifacts-builder` | Optional standalone concept mock-ups, published as private claude.ai pages, to compare design directions before restyling the app. | Not for the application itself: its React 18, Vite, Tailwind and shadcn/ui stack conflicts with this app and its plain-CSS rule. Read what its setup script installs, and where, and ask before running it. |

Both Operations chat and Dispatcher should look sophisticated, distinctive and deliberately designed in a dark theme, with a coherent visual language and clear differences in their jobs. The existing mock supplies behavior, not a visual template.

- Do not use generic AI/SaaS dashboard templates, purple accents, decorative gradients, neon glows or a dark-mode reskin of an otherwise generic layout.
- Do not fill the screens with repeated rounded cards, bento grids, decorative pills, fake statistics, robot/sparkle motifs, marketing slogans or unnecessary icons.
- Do not make chat a token textbox beside the finished dispatcher. Design the conversation, composer, participant/time information, processing handoff and outcomes as a complete usable interface.
- Do not turn the dispatch table into decorative cards or sacrifice readable rows, evidence, pending choices and final change explanations for appearance.
- Do not use tiny low-contrast text, ambiguous statuses, cramped controls, excessive motion or layouts that break on a laptop/narrow screen.
- Do not impose exact colors, fonts or layouts in this handoff. Choose the visual concept during design, then keep typography, spacing, controls and states consistent across the two interfaces.

Follow the skill's concept-first workflow when visual design begins: cover both full primary interfaces and their necessary states, use Image Gen unless the user opts out, agree the visual direction, and derive a small shared design system before coding the restyle. Concept generation is separate from this documentation edit and must respect existing spending instructions. No provider setup should block layout/state work using clearly labelled fixtures. Claude Code has no image generation: there the concept is the `frontend-design` plan with wireframes, optionally a `web-artifacts-builder` mock-up, and Aditya agrees it before any restyle code.

During implementation, use Browser/IAB first in Codex; record the reason if Playwright is the fallback. In Claude Code, use `webapp-testing` or the existing Playwright setup and review the screenshots as images. Compare the accepted concepts and actual browser screenshots (`view_image` in Codex), including typography, layout, palette, legibility and interaction states. Do not claim visual verification from a successful build alone. Keep all real text, controls and tables code-native. Do not add unrelated screens/features to make a concept look complete.

## 3b. Modes, navigation and starting a run

The app has two working modes in one Next.js application: **Chat** (`/operations`) for the people sending requests and **Dispatcher** (`/dispatcher`) for the person deciding. The introduction stays secondary.

- A mode switch is visible on every page and moves between Chat and Dispatcher in one click. It is navigation, not a login or a role.
- Starting a run is a short, obvious path from Chat: write or paste messages, **Send**, then **Process conversation** for the chosen snapshot. Before processing, say that it may cost model calls; show the processing state; when it finishes, link straight to Dispatcher on that run and its paused review when available.
- Dispatcher links each row back to its source messages in Chat.
- Prefer keeping the selected run in the URL (for example `/dispatcher?run=<run_id>`), so refresh and shared links open the same view without a global store or browser storage.
- **Authentication is deferred.** Later, a sign-in can decide whether a person may use Dispatcher mode. Now there is no login, no roles, no per-user data and no placeholder sign-in screen; anyone can switch modes.

How this helps the dispatcher ([Factory Primer](../reference-documents/Factory_Primer.md)): the chat-to-dispatcher path keeps each request's original words next to Python's answers to the three questions (can the workshop make the batch, can it take it given capacity and queue, is it allowed to), so the person deciding can check the evidence without hunting for it.

## 4. Tooling now; Docker at the absolute end

**Ignore Docker and related infrastructure for now.** Do not start Docker Desktop, check its daemon as a prerequisite, create Dockerfiles/Compose files or spend this phase fixing container networking. Containerization and deployment come at the absolute end, after frontend integration and the dedicated backend work. Leave existing empty infrastructure files alone.

- Keep the backend in its existing project-local `uv` environment. Never replace it with system Python or global pip.
- Use an existing isolated Node environment or an explicitly agreed project-local Node setup. Python's `.venv` does not isolate Node.js. If the required runtime is unavailable, explain the missing prerequisite before installing anything; continue independent UI/design work rather than introducing Docker early.
- Install nothing globally or into the Mac's system environment. No Homebrew, sudo, global npm tools or host browser-binary installation. This plan itself authorizes no installation.
- Keep frontend packages and caches scoped to the project/approved isolated environment; keep dependencies, builds and test reports ignored. Record dependencies in `package.json` and `package-lock.json`.
- Use a non-secret `BACKEND_API_URL`, normally `http://127.0.0.1:8000` when both processes run in the same host environment. Verify the actual address when starting the services; container addresses are out of scope now.
- Select stable Next.js and a supported Node LTS using current official requirements at implementation time. Record actual versions; do not switch package managers or add unnecessary tooling.
- Keep this unauthenticated demo local. No deployment or public network exposure in this phase.

The Next.js app and read-only dispatcher now exist; Operations and Introduction currently contain placeholders. Preserve working source and recorded checks. Do not scaffold over the project, switch frameworks, overwrite instructions/ignore files or initialize Git. Read [BUILD_STEPS.md](BUILD_STEPS.md) for recorded implementation progress; old completed results are historical evidence, not newly rerun checks.

Follow the [current installation guide](https://nextjs.org/docs/app/getting-started/installation). Define separate scripts for development, build, start, type checking, linting and browser tests. Use ESLint directly; do not assume `next build` also runs linting.

## 5. Page specifications

### `/`: introduction

A short, useful entry page, not a large marketing project:

- Explain the factory problem and the AI → Python → dispatcher flow.
- Link to Operations and Dispatcher.
- Label implemented capabilities and pending work, especially reallocation and live assignments.
- Omit performance cards initially. Add metrics only with a named evaluation record, dataset and clear meaning. Never present offline test counts as model accuracy or human-assisted results as autonomous performance.

Keep this page secondary to the two working interfaces. It should not absorb the design effort into a marketing site or make paid explanation calls.

### `/operations`: the core chat interface

Rebuild the useful behavior of the existing mock chat inside the current Next.js application. One shared conversation is enough: participant/display name, full original messages in order, receipt times, a usable composer and a working **Send** action. Support corrections/follow-ups as new messages, preserve drafts on a failed send, and keep the timeline readable as it updates. Do not classify or rewrite messages in React, invent authenticated accounts or add multiple channels/voice.

**Send saves a chat message; it does not call a model.** This carries forward the mock's explicit input-storage behavior. The rule against pre-approval database writes concerns unfinished dispatcher allocation choices; it does not ban storing deliberately sent chat messages. Typing in either composer/form does not autosave unfinished text or decisions.

Keep the mock's stable snapshot/export behavior and a separate explicit **Process conversation** handoff for a chosen snapshot. That action runs the existing Python pipeline and links the captured conversation to its run and dispatcher review. Do not process on every Send, keystroke or page refresh. No manual notebook copy/paste should be required for the completed connected journey.

| Action | Input | Output/behavior |
|---|---|---|
| Send message | Display name, original text and one submission-event identity | Save one chat input; show it only on success and retain the draft on failure. This action makes no model call. |
| Read conversation | Conversation identity | Full ordered messages with names/times, not reconstructed quotations from a plan. |
| Snapshot/export | One captured conversation | Stable text input and message mapping, with preview/download as in the mock. No model call. |
| Process conversation | Explicit chosen snapshot and defined message-date context | One pipeline run, its run/thread identity, processing state and a link into Dispatcher. This action may incur model cost; use a guarded offline fixture/replay for no-paid development and separately authorize real model tests. |
| Open outcome | Source snapshot/message and resulting task identity | Navigate between the original chat and the corresponding dispatcher row without inventing a link. |
| Open clarification | Source message/task identity | Existing dispatcher fact-correction form for a supported task. |

The current four-route API does not provide this chat bridge yet. Implement the missing message/history/snapshot/processing capabilities as part of this frontend integration, reusing or narrowly extracting the mock's tested helpers behind thin FastAPI routes. Do not run Streamlit or a notebook kernel from the browser, access SQLite directly from React, copy scheduling logic into Node, or build a job platform for this step. Current API absence is an implementation task, not permission to ship a quote-only page as finished chat.

A continuously running clarification/reverification loop is still separate future behavior. Follow-up messages can be captured for an explicitly processed snapshot; do not falsely claim every reply automatically updates an existing paused review.

### `/dispatcher`: the working demo

One page with a run selector, a worklist and a detail panel. Filters are enough; do not make separate databases or copies for Review and Approved.

**Header:** selected run, its label, dispatch date, processing completeness, draft/final state and refresh. Initially provide a plainly labelled thread-ID field for interactive review because the API cannot look one up from a run. Verify `review.source_run` matches the selected run before enabling edits. A saved plan without a paused thread is read-only.

**Temporary feature, remove later (Aditya, 21 October 2026): choosing old saved runs.** For now Dispatcher keeps its picker of all saved runs, so reviews can be tested on earlier runs without processing new messages or spending on model calls. Once the chat-to-dispatcher path works, remove the picker or limit it to the dispatches a real dispatcher should see. Do not build new features that depend on it.

**Later, not now: production run names.** The picker currently shows `run_id: label (N messages)`, for example `2026-10-19_11-25-25: dispatch_requests_extended.txt (222 messages)`. The run ID is the processing start time, the label is the source file name and the count is chat messages, not orders. A production system needs names a dispatcher can choose by date and time, and possibly order count, for example "19 September 2026 Allocations - 15 Orders". Decide later which date it shows (dispatch date or processing time), what the count means (distinct orders, allocated batches or all requests) and where the name comes from (preferably the backend's run list, so every screen shows the same name).

**Counts:** messages and worklist outcomes separately, provisional items, final approved rows, unresolved rows and unprocessed inputs. An outcome count is not accuracy. Do not count every non-review row as an allocation or every missing outcome as a model failure.

**Worklist:** All, Needs attention, Suggested, Approved. Show row ID, order ID, outcome, selected workshop or informational option, delivery days, available days and reason. Keep filters derived from the same backend rows. Preserve unfamiliar outcome strings rather than hiding them.

**Detail panel:**

- Source message IDs and exact available quotations; complete transcript when the API supports it.
- Task ID and version, order ID, CSV quantity, deadline, interpreted preference, requested/excluded workshops and original versus dispatcher-corrected facts when available.
- Missing facts, questions, unsupported conditions and unresolved link warnings. Link candidates are possibilities, never confirmed relationships.
- Selected workshop, candidate metrics, backend ranking and rejected workshops with their reasons. Keep `closest_option`, `late_option` and `option_without_request` visibly labelled as information unless Python actually selected them.
- Show delivery, lateness, queue, production, expected rework, transport, cost and defect rate only when returned. Null means unavailable, not zero. Format days to two decimals and defect probabilities as percentages; preserve the underlying backend values. Do not invent a currency or round values before deciding eligibility.
- Pending local dispatcher choices, clearly separated from the original calculated suggestions; after final submission, the saved result and its before/after report. No free-text AI assistant is needed.

**Queue table:** starting queue days from `queues_before_plan`, draft queue days from `queues_after_plan`. A workshop with no reserved batch keeps the same queue. Production and expected rework add queue time; transport contributes to delivery but not workshop queue time. These are workshop rows, not order rows, and this is a tentative plan over a snapshot. Do not reproduce notebook 06's separate “after approved work” stage: the current graph has one final approval.

## 6. Existing HTTP contract

There are exactly four application endpoints today. The application is created in `backend/main.py`. `/docs` and `/openapi.json` expose FastAPI's documentation/schema.

This section records existing code. It does **not** authorize sending per-edit requests from the new UI: those checkpoint dispatcher drafts. The approved target is the one-batch submission in section 7, which requires a backend contract change before final submission can be connected.

| Endpoint | Current response and important limits |
|---|---|
| `GET /runs` | Array of `{run_id, label, messages}`; `messages` is a count. Oldest first. An empty list is valid. |
| `GET /runs/{run_id}` | `{run_id, plan, dispatcher_plan}`. Either plan may be null. Does not return the manifest, complete messages or thread ID. Unknown run: 404. |
| `GET /reviews/{thread_id}` | `{status: "waiting", review, refused}` for a paused review. Finished and unknown threads both return 404. |
| `POST /reviews/{thread_id}/answer` | Same envelope with `status: "waiting"` after an edit/refusal, or `"finished"` after final approval. A business refusal can be HTTP 200 with non-null `refused`. Non-object JSON gets 422. |

Run IDs, thread IDs, message IDs, item IDs, task IDs and order IDs are different identities. Use the backend's row/task ID for selection and commands; an order can have multiple tasks. Encode IDs when putting them in URLs. Never accept a filesystem path from the browser.

For display, read `summary_rows` together with `review_warnings`. A raw decision may still say `recommendation` while its summary says `provisional_recommendation`. Such a provisional recommendation reserves tentative queue time but cannot be silently approved while the warning is unchecked.

Important review fields include `source_run`, `dispatch_date`, `status`, `processing_complete`, `summary_rows`, `decisions`, `needs_clarification`, `duplicate_order_reviews`, `intake_review`, `task_review`, `link_review`, `not_processed`, `review_warnings`, `dispatcher_entries`, `decision_problems`, both queue maps, `reservation_order`, `final_ids` and `unresolved_ids`.

Summary rows contain `id`, `order_id`, `outcome`, `workshop`, `delivery_days`, `days_available`, `reason`, `messages`, plus `final` in dispatcher reviews. Crucially, `workshop` can be an informational option for a review row. Confirm selection through its decision's `selected_workshop`/`selected_metrics` and outcome before showing an assigned/suggested badge.

The backend reads its configured output folder at startup. A run in another output tree will not appear just because it exists on disk. Do not change `config.toml`, the dispatch date, source CSVs or code during a paused review. Changed data/date signatures refuse answers; code stability is also a working rule.

## 7. Editing and approval: exact behavior

**Approved target, not current API behavior:** all dropdown selections, corrections, warning checkboxes and resets update page memory only. Do not send an answer, resume the graph, recalculate in Python, autosave to SQLite/JSON/browser storage or append draft history while the dispatcher is choosing. A new local selection for a task replaces its earlier local selection. Clearly label pending choices as unsaved; closing the page can discard them. Existing source-run records remain intact.

Use one **Approve all** action. It submits the complete final choice set, lets Python preserve the dispatcher's destinations and fit flexible work around them, saves the result immediately and displays it with the before/after report. There is no Save-and-recalculate step or mandatory approval of a second preview.

Proposed minimal extension of the existing answer shape, using a real test task ID for illustration:

```json
{
  "decisions": [
    {"decision": "choose_workshop", "task_id": "T:L0008:J1", "workshop_id": "W6"}
  ],
  "then": "approve_all"
}
```

**The current validator refuses that example because it combines edits and approval.** Before connecting the final button, implement/test the small batch-finalization path through the existing Python functions. Do not work around the limit by silently sending individual `review_again` answers followed by an empty approval: that persists unfinished decisions and violates the user's requirement. No new operational database or draft service is needed.

Keep normal automatic eligibility/deadline checks for work Python chooses. For an identified batch and known workshop, the dispatcher's explicit destination wins even when it overrides a normal rule or is late. Show the consequences as information, without demanding a justification or additional confirmation. Structural errors and unidentified batches must be reported without inventing facts or silently dropping a decision.

| Locally staged action | Existing decision vocabulary | Rules |
|---|---|---|
| Correct facts / resolve a question | `decision: "correct"`, `task_id`, optional `facts`, optional `resolves` | `facts` permits only string values for `order_id`, `due_date`, `preference`, `intent`. Date: `YYYY-MM-DD`; preference: `none`, `fastest`, `cheapest`, `quality`; intent: `allocation`, `question`. `resolves` contains original zero-based blocker numbers; see section 9. Quantity is read from CSV and is not an editable fact. |
| Choose workshop | `decision: "choose_workshop"`, `task_id`, `workshop_id` | A later local choice replaces the earlier one. List known workshops, including override choices. Keep the submitted destination fixed and display the final recorded restriction/late warnings. |
| Accept shown late option | Existing `decision: "accept_late"`, `task_id`, optional `max_days` | The current helper requires a standalone answer tied to shown estimates; it cannot simply be copied into a mixed batch. Resolve/test that compatibility in the batch contract before enabling this control. Never send an intermediate request. A named workshop choice already accepts its resulting lateness. |
| Warning does not affect this task | `decision: "warnings_checked"`, `task_id`, `row_ids` | Send exact IDs from `review_warnings[task_id]`. This acknowledges that the unresolved input does not change this task; it does not resolve the link or mean “I read the warning.” If it does affect the task, keep it unresolved. |
| Reset dispatcher edits for this task | Local form reset; legacy backend vocabulary is `decision: "clear"`, `task_id` | Clear all pending choices/corrections for that task locally, not just the dropdown. It does not cancel the order. Do not send the legacy helper as a separate request while editing. |

The final submission is all or nothing for malformed/unsupported commands: no saved partial decision set. On `refused`, show the backend's message, retain local inputs and leave the last saved result unchanged. HTTP 200 alone does not mean success. Expected genuinely unresolved work can remain explicit in the final table; do not manufacture allocations.

- Pending local edits are exactly what approval submits; do not disable approval merely because choices are unsaved. Disable it while its one request is running.
- Calculate from the original snapshot once for the submitted batch, keep manual destinations fixed, fit other ready work around them, finalize that calculated result and save it. Never reserve the same work twice or recalculate again during the save itself.
- Show a before/after table with task/order ID, original/final workshop, original/final delivery estimate, deadline and the recorded reason. Include manually fixed, displaced, unchanged and unresolved work, with before/after workshop queue totals. Explain actual calculations; make no paid explanation call.
- A final review can still contain unresolved tasks. Do not call it “all orders dispatched.”
- Stop editing after `status: "finished"`. Retain the final response; on reopening, read `dispatcher_plan` through the run endpoint. A finished review endpoint returning 404 is expected.
- Keep one mutation in flight and disable repeated clicks. If a network failure leaves the outcome unknown, read the review/run before another attempt. Do not automatically retry POST requests.
- Do not add locking, multiple-instance coordination, WebSockets, optimistic assignments or approval-version machinery for this single-dispatcher demo.

Here, reallocation means rearranging unstarted batches in the proposed table after the submitted human choices. A fixed task can add queue time, make another task late, move that task elsewhere and affect further tasks. Use the existing deadline-based planner and recorded data; do not create an additional priority model or a live production-transfer system. The normal path saves immediately and shows the report. The optional future **Review again after reallocation** mode remains disabled until implemented; it is not a mandatory extra approval in this path.

## 8. Suggested source layout

Create files when their increment needs them; do not populate empty architecture layers in advance.

```text
frontend/
  AGENTS.md                    # Working rules
  FRONTEND_PLAN.md              # This handoff
  app/
    layout.tsx                 # Shared navigation
    globals.css                # Simple shared styling
    page.tsx                   # Introduction
    operations/page.tsx        # Core chat: messages, composer, snapshots and processing handoff
    dispatcher/page.tsx        # Run selection, worklist and review state
  components/
    RunPicker.tsx
    TaskTable.tsx
    TaskDetails.tsx            # Evidence, comparisons and decision form
    QueueTable.tsx
  lib/
    api.ts                     # Four small fetch functions; preserve refusal envelopes
    types.ts                   # Types matching the actual JSON
  tests/
    fixtures/                  # Small, sanitized, explicitly synthetic API responses
    dispatcher.spec.ts         # Browser behavior including error/refusal cases
  next.config.ts               # Backend rewrite
  package.json
  package-lock.json
  tsconfig.json
  eslint.config.mjs
  playwright.config.ts
  .env.example                 # Backend address only, no credentials
  .gitignore
```

Dockerfiles, Compose and container build exclusions are deliberately absent from this increment; add them only at the absolute end.

Keep the static introduction/layout as Server Components; interactive controls need Client Components. Use local React state for selection and unsaved forms. No Redux, global store, ORM, frontend database, AI SDK or generic repository/service layer. Split a component further only when it becomes difficult to read.

API reads should fetch fresh review data (`cache: "no-store"`), show loading/empty/error states and avoid mixing results from an old run with the currently selected run. Use a simple abort/ignore mechanism for stale GET results. Start independent reads together where useful; do not add polling without a processing-status endpoint that needs it.

Use accessible controls, keyboard labels, visible focus and meaningful text states rather than color alone. Follow section 3a for the dark visual design of both interfaces. Do not confuse a simple code structure with a requirement to leave either interface visually unfinished; do not add libraries or decorative components just to suggest sophistication.

## 9. Backend gaps to handle explicitly

These are separate proposed backend increments. They are not endpoints or fixes that exist today, and this planning task does not implement them. Read `backend/AGENTS.md` before changing backend files.

| Gap | Smallest reliable next step | Until available |
|---|---|---|
| One final batch, no persisted dispatcher drafts | Extend the current answer/finalization path to accept the complete submitted choice set, calculate once, finalize and save. Test no per-click requests, no partial saved decisions on refusal, fixed manual destinations and the before/after report. This is not implemented by editing this document. | Read-only screens and locally staged fixture UI can proceed. Do not connect the final button using hidden per-edit requests. |
| Run → paused thread lookup | Keep manual thread entry first. Later expose a read-only association using checkpoint state or saved metadata; choose one and test it. Do not guess a thread ID from the run name. | Saved runs remain readable; edits require a verified paused thread. |
| Full source messages and chat identity | Provide full ordered chat inputs through the required chat/history bridge and retain their mapping to snapshots/runs/tasks. Existing saved runs may also need their manifest messages exposed. Never return arbitrary files or credentials. | Do not reconstruct a conversation from quotations. Fixtures can support development, but full chat/history is a completion requirement. |
| Stable blocker numbers | Add `open_blockers_by_task` to the read response, with entries such as `{number, text}` derived from the existing helper and original verified tasks. Retain stable identities in final/refusal responses where needed. Test resolving several original blockers in one submitted set. | Stage only supported fact inputs; blocker-resolution checkboxes stay disabled until original numbers are available. Never number a filtered remaining list from zero. |
| Optional split request such as R23 | Backend policy decision required: a saved workshop choice currently can remain unused for an unsupported split. Either keep this explicitly unsupported, or separately approve/test an explicit whole-batch override. | Never display “assigned” solely because `refused` is null or `dispatcher_entries` contains a choice; inspect the returned allocation. |
| Repeated blocker text and stale deadline guidance | Preserve exact blockers and their identities. Fix duplication/reason text in a separate verified backend change; a named workshop choice can already allocate an overdue task. | Do not merge blockers by wording in React or hardcode “only a revised deadline can fix this.” |
| Chat capture, history and snapshot/export | Add the small FastAPI bridge needed by the core chat frontend. Reuse or narrowly extract the tested mock helpers for explicit message saving, ordering, retry identity, original text and stable snapshots; keep business rules in Python. | A fixture-backed UI is an intermediate design/test stage. A real Send/history/export path is required; do not make a disabled composer the final implementation. |
| Explicit snapshot processing | Include an endpoint/capability that takes a chosen snapshot into the existing parser/pipeline and returns its run/thread/review identity. Sending a chat message alone never invokes it. Preserve the snapshot/date context and keep model-cost authorization separate. | Use a guarded offline fixture/replay during development. Missing API support is planned implementation work, not a reason to remove chat from the MVP. Do not claim a live paid run occurred. |

The workshop list is **already available** in `GET /runs/{run_id}` under `plan.workshop_profiles`; use that same run's profiles for the dropdown. No workshop-list endpoint is needed. If a run has no plan/profiles, show unavailable data rather than inventing it. This corrects the earlier version of this plan.

For the first approved processing endpoint, prefer one explicit batch submission with a waiting state and final review response. Before choosing a long HTTP request, measure the existing run duration against proxy/server timeouts. If that cannot reliably cover the run, make processing a separate small backend increment with an explicit status resource; do not silently build a job platform. Preserve exact message/date semantics and define duplicate-submission behavior before enabling the button. Do not modify the global config per request.

A new input may miss the response cache and cost money. A frontend “test mode” label does not make the backend free. Development uses synthetic responses or an isolated offline fixture with network/model calls blocked; a real processing run requires explicit paid-run authorization.

## 10. Build and verify in small increments

1. **Retain the working base; design both interfaces.** Read the mock chat and current source/build record. Preserve the existing Next.js app and read-only dispatcher. Use the design skill (section 3a; `frontend-design` in Claude Code) to establish both complete dark interface concepts and their important states, including the mode switch and the chat start-run path (section 3b), before implementing the visual restyle. Keep palette/font/layout choices open until that design work; do not install tools or introduce Docker as a prerequisite.
2. **Build the core chat journey.** Implement the Operations conversation/composer and required FastAPI bridge for Send, history and stable snapshots/export, based on the mock. Connect one explicit Process conversation handoff to the existing pipeline, returning the run and review identity. Use offline guarded fixtures for model-backed behavior; actual paid execution remains separately authorized. Do not automatically process every Send or leave chat as a placeholder.
3. **Connect chat and dispatcher.** Use the existing saved-run views and profiles, full source messages and reliable snapshot/run/task links. Verify navigation from a message to its outcome and back. Keep real empty/error/processing states visible and do not fake successful ingestion.
4. **Stage choices and finalize once.** Implement local-only dispatcher forms and the required batch-finalization contract. Test zero writes/recalculation while choosing, one complete final submission, fixed manual destinations, flexible moves, before/after reasons, refusal without partial saving and reopening final JSON. No mandatory second approval; future reallocation controls stay disabled until implemented.
5. **Verify both interfaces against their accepted designs.** In Codex, use Browser/IAB first, record any Playwright fallback reason, and compare the concepts with actual rendered screenshots using `view_image`; in Claude Code, use `webapp-testing` or the existing Playwright setup and review the screenshots as images. Exercise chat capture/history/export/process-to-review and dispatcher final submission in safe fixtures. Check responsive behavior, readable text/tables, keyboard use and meaningful states; passing build/tests alone does not establish visual fidelity.
6. **Supporting introduction and handover.** Keep the introduction accurate and secondary. Update the build checklist and reproducible startup/demo instructions with actual checks, current progress and limitations. The frontend is not complete while either core interface is a placeholder. Dedicated backend results work follows separately; Docker/deployment remain at the absolute end.

Use Playwright browser tests with intercepted API responses for UI behavior when the agreed isolated environment already supplies the required browser tooling. Do not install host browser binaries or introduce Docker to satisfy this step; report unavailable checks honestly. For real HTTP integration, use a temporary backend fixture/checkpoint with tracing off, model/network access blocked and disposable output. Existing backend tests show this pattern in `backend/tests/test_fastapi_routes.py`; some older backend fixtures depend on ignored local run/notebook files, so check availability rather than assuming a fresh checkout contains them.

At each increment, run the checks relevant to that change. After an actual backend modification, also run its required offline suite from `backend/` using `uv run python -m unittest discover -s tests -v`. A cached replay establishes repeatability, not unseen AI accuracy. No backend test was rerun merely to write this document.

### Acceptance checklist

- [ ] Both Operations chat and Dispatcher have complete, distinctive dark designs following section 3a; neither is a token placeholder, generic purple/gradient template or unfinished plain view.
- [ ] A visible mode switch moves between Chat and Dispatcher in one click from every page. There is no login or role selection yet.
- [ ] From Chat, starting a run is a short, obvious path (Send, then Process conversation), and the finished run opens directly in Dispatcher.
- [ ] Participants can send real chat messages, see full ordered history and retain a draft on a failed Send. Chat input storage does not persist dispatcher allocation drafts or call a model.
- [ ] A stable conversation snapshot can be previewed/exported and explicitly passed to the pipeline; the resulting run/review links back to the original messages. Offline fixtures prove the integration without paid calls; live model execution is separately authorized and reported honestly.
- [ ] The mock's behavioral reference is preserved, without copying its old visual style, obsolete date-policy commentary or manual notebook handoff into the connected product.
- [ ] Saved runs load, missing/partial data is explicit, and a selected run never displays another run's review.
- [ ] All returned inputs/outcomes remain inspectable, including questions, link reviews, non-tasks and unprocessed messages.
- [ ] Suggestions, informational options, provisional results and final approved rows look different.
- [ ] Every currently supported decision has a working control or a clearly documented missing backend prerequisite.
- [ ] Blocker identity survives resolving an earlier blocker; the second checkbox resolves the correct original blocker.
- [ ] A supported named workshop choice remains fixed while Python fits other ready tasks around it; overrides and lateness remain visible.
- [ ] No legacy helper sends a standalone request during editing; any late-acceptance control has tested batch semantics, warning acknowledgements use exact row IDs and reset clears the complete local task edit.
- [ ] While choosing, there are zero mutation requests, graph resumes, Python recalculations, database/JSON draft writes or browser-storage saves of dispatcher decisions.
- [ ] A refused final submission preserves the last saved result, retains the local choices and shows the reason without a partial saved decision set.
- [ ] One approval submits the complete final choice set, calculates and saves immediately, and shows actual before/after changes and reasons without another approval. No unresolved row looks approved.
- [ ] Final JSON can be reopened without trying to resume the finished thread.
- [ ] Reallocation and **Review again after reallocation** are disabled and send zero requests.
- [ ] No page opening, refresh or normal review action makes a model call. No secret appears in browser assets, logs or fixtures.
- [ ] Type checking, linting, app build and relevant browser checks are run where tooling is available; actual passes, unavailable checks and limitations are recorded. Docker is not a completion prerequisite.

There is no target allocation percentage or evaluation-score gate for this frontend phase. Display existing results faithfully and verify the UI/API behavior. Put broader prompt, model and allocation-quality issues aside for Aditya's later dedicated backend work; do not conceal integration failures or fabricate better results.

Completion requires both the working chat interface and dispatcher, with the required API bridge and a verified snapshot-to-review path. Offline integration and actual model performance are reported separately. The current saved-run screen is a useful increment, not a replacement for the chat frontend. Do not claim that a disabled Send button or quoted-excerpt viewer completes this scope.

## 11. Repository safety and implementation handoff

The user currently prohibits **all Git commands**. Do not initialize a repository, stage, commit, push, inspect remotes or let a scaffolder initialize Git. Do not modify `.git` metadata.

The existing backend repository is to stay intact; the user intends a fresh repository for the whole application. The root ignore rule for nested `.git` metadata does not convert `backend/` into an ordinary directory for a future root commit. That needs a separate, explicitly agreed metadata-preservation step. Do not solve it by deleting `backend/.git` or creating an accidental submodule.

Keep source, instructions, manifests, the dependency lockfile and container configuration available to commit. Exclude real environment files, keys, generated output, dependencies, caches and browser reports. `.env.example` contains only a non-secret backend address. Keep the root's existing local-only reference/notebook exclusions; summarize relevant context here rather than assuming those ignored files are available in a fresh clone.

Suggested handoff message to Claude:

> Read PROJECT_HANDOFF.md, frontend/AGENTS.md, frontend/FRONTEND_PLAN.md and the mock chat under backend/experimentation_notebooks/mock_frontend/. Operations chat and Dispatcher are both core interfaces in the existing Next.js app. Use build-web-apps:frontend-app-builder (Codex) or the frontend-design, webapp-testing and web-artifacts-builder skills (Claude Code) to design both in a very beautiful, distinctive dark theme with an easy Chat/Dispatcher mode switch and no login yet; avoid generic AI templates, purple accents, decorative gradients, repetitive cards and low-contrast text. Do not prescribe exact fonts/colors/layout from this handoff. Carry forward the mock's Send/history/snapshot behavior and implement the small API bridge rather than leaving chat disabled. Sending stores chat only; processing a snapshot is explicit and real paid model tests need separate authorization. Keep dispatcher choices local until one Approve all submission, then calculate/save immediately and show what changed. Preserve the dispatcher’s authority, no mandatory second approval, Docker last, and no Git commands, exposed keys or global/system installs. Record actual progress and verify both rendered interfaces, not just the build.
