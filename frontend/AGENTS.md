# Frontend instructions

The [root instructions](../AGENTS.md) apply here. These rules adapt the relevant [backend instructions](../backend/AGENTS.md) for frontend work. Start with the root [project handoff](../PROJECT_HANDOFF.md), then [FRONTEND_PLAN.md](FRONTEND_PLAN.md), for current scope, context, API contracts and implementation steps.

## Scope and source of truth

- Build both core interfaces in the existing Next.js/React app: Operations chat and Dispatcher. Preserve the existing read-only dispatcher and complete the chat journey; the introduction is supporting work. Read the [mock chat](../backend/experimentation_notebooks/mock_frontend/README.md) and [app.py](../backend/experimentation_notebooks/mock_frontend/app.py) for its already-implemented behavior, not its old styling.
- Missing chat endpoints are required integration tasks, not permission to leave Operations as a quote-only viewer or disabled Send placeholder. Include a small FastAPI bridge for explicit Send/history/snapshot/export and explicit snapshot processing through the existing pipeline. Sending stores chat without model calls; a real paid processing test remains separately authorized. Do not rewrite scheduling in React/Node, run notebooks from the browser or add a job platform.
- The only goal now is frontend design, API connection and functional verification through dispatcher review. Leave allocation-rate improvements, prompt/model tuning and dedicated evaluation to Aditya's later backend work. Existing weak results do not block frontend development; display them faithfully and still fix actual integration failures.
- The assignment MVP's output is an explainable dispatch table under the dispatcher's control. Do not grow it into a factory execution/deployment project. The latest approved interaction is one complete local choice set, one **Approve all** submission, immediate calculation/save, then the final table and what changed and why. No mandatory second approval.
- **Docker, containers, Compose, deployment and related infrastructure are deferred to the absolute end. Ignore them for now.** Do not start Docker, create container configuration or require a running daemon before frontend work. This replaces the earlier Docker-first setup direction.
- Read the [project plan](../docs/project-plan.md) and [system design](../docs/system-design.md) before changing workflow or scope. Check actual route/decision source when older prose disagrees with implemented behavior.
- Reallocation, operational assignment writes, live queue updates and a second review after reallocation are not implemented. Keep **Reallocate** and **Review again after reallocation** disabled and make no request from them.
- Do not add authentication, roles, multiple channels, voice, a general-purpose AI assistant, an operational assignment database, a job platform or dispatcher session coordination merely because they might be useful later. One shared operations conversation with named participants and explicit message storage, as in the mock, is in scope.
- Do not change backend behavior as an incidental frontend fix. Before backend edits, read `../backend/AGENTS.md`, establish the actual issue and agree the small contract change. No endpoint currently starts processing or accepts chat.

## Visual design for both interfaces

- Follow the user-invoked **build-web-apps:frontend-app-builder** skill and [the plan's design brief](FRONTEND_PLAN.md#3a-visual-direction-for-both-core-interfaces). Keep the existing Next.js framework. Design both full primary interfaces and their important states, not just a landing page/header or the dispatcher alone.
- Both must be sophisticated, distinctive dark interfaces. Do not use generic AI/SaaS templates, purple accents, decorative gradients/glows, repeated card/bento grids, fake statistics, decorative jargon or a merely recolored generic layout.
- Do not prescribe exact colors, fonts, spacing or panel arrangements in this handoff. Choose the concept during design, then use a consistent visual system across chat and dispatcher. The mock is a behavior reference, not a style template.
- Do not sacrifice conversation/table legibility, source evidence, usable controls, contrast or responsive/keyboard access for decoration. Keep text, tables and controls code-native.
- Follow the skill's concept-first process during actual design, including Image Gen unless the user opts out, with existing spending instructions still in force. Verify the accepted concept against the browser-rendered result using `view_image`; use Browser/IAB first and record a Playwright fallback reason if needed. Do not claim visual QA from a build alone or generate/copy a static screenshot as the functioning UI.

## Environments, secrets and Git

- Install nothing globally or into the Mac's system environment. Python `.venv` does not isolate JavaScript. Use an existing isolated Node environment or an explicitly agreed project-local setup. If unavailable, explain the prerequisite before any installation and continue independent design work. Do not introduce Docker as a workaround.
- Keep Python work in `backend/` with `uv run` and its project-local `.venv`; use `uv add` only for a needed, authorized dependency. Never use global pip, npm installations, Homebrew or sudo.
- No dependency installation is authorized merely by this planning document. When implementation/setup is authorized, keep packages project-local in the agreed isolated environment and record versions in `package-lock.json`; no global/system package or host browser-binary installation.
- Never display, copy or inspect secret values. Do not open real `.env` files to build the UI. If a secret appears, stop and tell the user without repeating it.
- All model credentials stay in the backend. Never put keys in browser code, `NEXT_PUBLIC_*`, fixtures, screenshots, logs, repository files or container images. Frontend configuration needs only a non-secret backend URL.
- Frontend configuration needs no access to backend secret files, `.git` or SSH credentials. When container work eventually begins, exclude secrets and metadata from its mounts and build context; do not do that infrastructure work now.
- **Do not run any Git command while the user's current ban applies.** This includes read-only commands and automatic Git initialization by scaffolders. Do not alter repository metadata, remove `backend/.git`, create a submodule, commit or push.
- The user backed up the backend outside this project and removed its top-level `.git` on 21 October 2026. Root Git has not been initialized. Do not restore or initialize metadata; leave Git operations to the user. The old nested evaluation repository remains ignored. Follow the root public-repository check before publishing.
- Preserve this file, the plan and existing ignore rules during setup. Keep source, package manifests, lockfiles, safe example configuration and container files available to commit. Keep dependencies, builds, test reports and actual environment files ignored. Do not change root reference/notebook exclusions casually.

## Rules the UI must preserve

- Python calculates readiness, eligibility, dates, queues, cost, defect comparisons, ranking and allocations. React displays results and sends structured decisions; never recreate the scheduler in JavaScript.
- Keep run, thread, message, item, task and order IDs separate. Use actual backend task IDs for decisions. An order ID alone does not identify one task.
- Preserve exact source evidence and uncertainty. Never show an unresolved link candidate as a confirmed follow-up or silently discard a source message/outcome.
- Read `summary_rows` and `review_warnings`, not just raw decision statuses. A provisional recommendation still reserves tentative queue time. An informational alternative is not a selected workshop.
- The dispatcher is authoritative for the destination of an identified batch. Assume he knows why he chose it; keep his workshop fixed and fit other work around it. Do not veto or demand justification for a manual rule/lateness override. Show calculated consequences and unresolved technical limitations without inventing facts or silently dropping his choice.
- `correct` permits order ID, due date, preference and intent. Quantity comes from the CSV and is never typed over. Blocker resolution must use the original backend blocker numbers, never positions in a filtered display list.
- `warnings_checked` means the unresolved input does not affect that task. It is not a generic “warning read” checkbox. Use exact warning row IDs.
- Keep all unfinished choices in page memory. Dropdowns, checkboxes, corrections and resets send no mutation request, resume no graph, trigger no Python replanning and save no database/checkpoint, JSON draft, browser storage or history. No autosave/per-row Apply; label local choices unsaved.
- That no-write rule concerns unfinished dispatcher allocation choices. Explicit Send may persist chat messages as the original mock does; typing does not autosave a draft. Keep Send separate from Process conversation, preserve original messages and use snapshot/run/task identities for source links.
- **Approve all** submits the complete final set once, including pending local changes. Python applies the set, recalculates from the original queues with manual choices fixed, finalizes and saves that result immediately. Show the final table and before/after reasons; do not request approval again. Disable repeat submission while the one request runs.
- The existing API still requires edits to be sent separately and checkpoints them; its empty `approve_all` cannot apply a choice set. This conflicts with the latest target and needs a small backend contract change before wiring the final button. Do not hide intermediate edit requests behind one UI click.
- The current `accept_late` helper also requires a standalone answer; account for that in the batch-contract work rather than sending a separate request during editing. A named manual workshop choice already accepts its resulting lateness. Reset local choices locally; the legacy `clear` command removes the task's whole backend decision entry and does not cancel an order.
- An HTTP 200 can contain a business refusal. Show `refused`, keep accepted state unchanged and do not report success from status code alone. No automatic retry of mutation requests.
- After successful final submission, use the returned saved result as truth. A final table can contain unresolved rows. The MVP saves a dispatch table; do not claim operational assignment or live queue updates. Explain queue-induced moves using recorded calculations without paid model calls.
- One dispatcher is assumed. Keep one mutation in flight and disable repeat clicks; do not invent concurrency infrastructure. A finished or unknown thread has no paused review and returns 404.
- Do not change dispatch date, input CSVs or backend code while a review is paused. Never edit the supplied reference materials or `../harness/simulate.py`.

## Simple implementation and verification

- Use the App Router, TypeScript, ordinary CSS, native controls, local React state and a small `fetch` helper. Prefer a Next.js rewrite to the existing FastAPI server over a new business-logic proxy/backend.
- Read current official documentation before choosing library APIs. Select stable versions, preserve the lockfile and avoid unnecessary dependencies or empty layers.
- Work incrementally, verifying each step. Diagnose and prove a bug before fixing it. Add exception handling only for expected failures with useful messages.
- Always show loading, empty, partial-data, unavailable-backend and refusal states. Null metrics are unavailable, not zero. Do not invent missing messages, workshop data or API routes.
- No page opening, refresh, explanation button or test may trigger paid model calls. Processing may incur cost even with caching. A paid run needs explicit authorization; keep tracing off for offline testing.
- Use sanitized synthetic API fixtures for browser tests. Real review integration tests need disposable runs/checkpoints with model/network access blocked. Never approve or overwrite a retained team run as a test shortcut.
- Run type checking, linting, an app build and relevant browser checks in the available agreed environment after meaningful source changes. If isolated tooling is missing, report the unavailable checks without installing system tools or making Docker a prerequisite. After backend changes, run required offline backend checks using `uv run`. Do not claim checks passed unless actually run.
- Report exact files and edits, validation and limitations. Keep meaningful findings and decisions in [the engineering log](../docs/engineering-log.md), distinguishing user decisions from AI implementation assistance.
- At meaningful feature milestones, follow the root interview-preparation rules: one grounded question at a time, wait for the user's answer, and defer checkpoints only in explicit deadline mode. Routine documentation edits need no interview interruption.
- Use no emojis in code or Markdown. Keep explanations and UI language simple; distinguish existing features from plans and measured results from accuracy claims.

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
