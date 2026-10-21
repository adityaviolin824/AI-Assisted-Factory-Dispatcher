# Frontend build steps

Started 21 October 2026. The working checklist for building the demo frontend described in [PROJECT_HANDOFF.md](../PROJECT_HANDOFF.md) and [FRONTEND_PLAN.md](FRONTEND_PLAN.md). Each step is finished and checked before the next one starts.

**Scope/design correction, 21 October 2026:** Operations chat and Dispatcher are both core deliverables, using the [existing mock chat](../backend/experimentation_notebooks/mock_frontend/README.md) and [its source](../backend/experimentation_notebooks/mock_frontend/app.py) for behavior. The original pending checklist wrongly reduced Operations to a saved-run viewer; that direction is superseded. Include its small API bridge and explicit snapshot-processing handoff, rather than leaving Send disabled. Both interfaces require a sophisticated, distinctive dark design following **build-web-apps:frontend-app-builder** and the broad guardrails in [the plan](FRONTEND_PLAN.md#3a-visual-direction-for-both-core-interfaces): no generic AI templates, purple accents, decorative gradients or prescribed palette/font/layout in this handoff.

**Review correction:** keep dispatcher choices local until one Approve all batch, then calculate/save immediately and show what changed and why. The old pending Save-and-recalculate/empty-approval steps are superseded. Backend contract changes are required; do not hide intermediate requests behind the final button. Completed steps/results below remain historical records and were not rerun by updating this checklist.

**Design and usability direction (Aditya, 21 October 2026, evening):** make the app very beautiful, unique and dark; beauty and usability come first in the design work. Starting a run from Chat must be easy, and a mode switch on every page moves between Chat and Dispatcher in one click ([plan section 3b](FRONTEND_PLAN.md#3b-modes-navigation-and-starting-a-run)). Authentication is deferred: a later sign-in can decide who is a dispatcher; for now there is no login and no role selection. Claude Code uses Aditya's skills whenever they fit ([plan section 3a](FRONTEND_PLAN.md#3a-visual-direction-for-both-core-interfaces)): `frontend-design` for every visual decision, `webapp-testing` for rendered-page checks, and `web-artifacts-builder` only for optional standalone concept mock-ups, never the app itself.

## Agreed setup (Aditya, 21 October 2026)

- Node: the existing Homebrew Node v26.6.0 and npm 11.18.0. Packages go only into `frontend/node_modules`; npm's download cache is `frontend/.npm` (gitignored). No global install, no scaffolder.
- Local servers that make no model call may be started: FastAPI on the real saved runs (read-only use), and a disposable offline paused review for testing edits and approval.
- Browser tests: `@playwright/test` in `frontend/`, reusing the Chromium already in `~/Library/Caches/ms-playwright`; nothing new is downloaded.
- For completed steps 1-3: no Docker, no Git, no paid model run and no backend source change. The corrected pending chat/batch work requires small backend integration changes; this plan update implements none. Docker/Git/paid-run restrictions remain in force.

## Versions (checked on npm, 21 October 2026)

| Package | Version | Why this one |
|---|---|---|
| next, eslint-config-next | 16.4.2 | Latest stable release (15 October 2026). Needs Node 20.9 or later. |
| react, react-dom | 19.3.1 | Latest stable release; Next.js 16 accepts React 19. |
| typescript | 6.0.3 | `typescript-eslint` (used by `eslint-config-next`) supports TypeScript below 6.1, so not 7.0. |
| eslint | 9.39.5 | `eslint-plugin-react` inside `eslint-config-next` lists ESLint up to 9 as a peer, so not 10. |
| @playwright/test | 1.64.1 | Latest stable release; uses the existing Chromium. |

## Steps

1. [x] **Shell.** `package.json`, Next.js configuration with the `/api/backend` rewrite, ESLint, layout with navigation, three placeholder pages and plain CSS. Check: type check, lint, build.
2. [x] **Read-only dispatcher on real saved runs.** `lib/types.ts`, `lib/api.ts`, run picker, counts, worklist with filters, detail panel (evidence, facts, uncertainty, workshop comparison) and queue table. Check: type check, lint, build; the real FastAPI through the rewrite; the page in a browser.
3. [x] **Browser tests for the read-only views.** Playwright with small synthetic fixtures: empty run list, missing plan, partial processing, backend unavailable, informational options not shown as selected.
   Then run `/code-simplifier` and `/systematic-debugging` on steps 1-3.
3a. [ ] **Design both full core interfaces.** Follow the named design skill and agree the visual direction before restyling/implementing the remaining surfaces. Use the mock for chat behavior, not appearance. Cover real chat and dispatcher states; keep the style distinctive and dark without adding unrelated features or hardcoding design choices in this checklist. In Claude Code: follow `frontend-design`'s two passes (a design plan with named colours, typefaces, layout wireframes and principles; then a review against the brief and generic defaults, saying what changed). Include the Chat/Dispatcher mode switch and the chat start-run path. Optionally show concepts as private mock-up pages with `web-artifacts-builder`, after checking its setup script. Aditya approves the design plan before any restyle code. **Update, 21 October 2026:** Aditya delegated frontend design decisions ("Don't ask me for clarifications when it comes to frontend"), so the plan is recorded in [DESIGN.md](DESIGN.md) and the restyle proceeds from it.
4. [ ] **Operations chat and required API bridge.** Implement the shared named-message timeline, usable composer/Send, history, stable snapshot/export and one explicit Process conversation handoff, preserving original text and message/run links. Reuse or narrowly extract the mock's Python helpers behind thin FastAPI routes. Send stores input only; processing a chosen snapshot is separate. Check input/storage/export with disposable data and processing with guarded offline fixtures; real paid model tests need separate authorization. A quote-only or disabled-composer page does not finish this step. Make starting a run obvious from Chat, and link the finished run straight into Dispatcher.
5. [ ] **Dispatcher local edits and one final submission.** Preserve the existing read-only views and implement local choices with zero pre-approval mutation/replanning/draft storage. Add/test the small batch-finalization contract before wiring Approve all: submit the whole set once, keep manual destinations fixed, calculate/rearrange, save immediately and display before/after reasons. No mandatory second approval or hidden per-edit requests. Verify with fixture tests and disposable offline runs; finished results reopen through `dispatcher_plan`. Reallocate and Review again after reallocation remain disabled until implemented.
   Then run `/code-simplifier` and `/systematic-debugging` on steps 4-5.
6. [ ] **Design/interaction verification for both interfaces and supporting introduction.** Use Browser/IAB first or document why Playwright is needed; compare accepted concepts and actual screenshots with `view_image` (both Codex tools). In Claude Code, use `webapp-testing` (its Python through `uv run`, servers only with permission) or the existing Playwright setup, and review the screenshots as images. Check that the mode switch works from every page and the chat-to-dispatcher path is short. Check responsive layouts, typography, dark palette/contrast, table/chat legibility and interaction states. Exercise chat-to-dispatcher source links and final submission. Keep the introduction secondary. Do not mark both frontends finished from a build alone.
7. [ ] **Handover.** Startup and demo commands that were actually run, implemented versus pending features, engineering log entry.

## Backend integration still required

| Gap | What the frontend does now |
|---|---|
| No run-to-thread lookup | A labelled thread ID field; the review is used only when its `source_run` is the selected run. |
| No original blocker numbers in the review | Blockers are listed; resolving them by number stays disabled. Facts can still be corrected. |
| No full transcript through the current run endpoint | Add the required chat/history/source-message bridge and snapshot/run mapping. Quotes are useful evidence but cannot stand in for a full conversation. |
| No chat bridge | Implement Send/history/snapshot/export support from the existing mock plus explicit pipeline handoff. The missing API is planned core integration work, not a reason to defer the chat frontend. |
| Existing approval forbids a mixed decision batch | Implement/test one-batch finalization. No mutation while the dispatcher chooses; no old edit requests followed by an empty approval. |

## Temporary features and later notes

- **Temporary, remove later (Aditya, 21 October 2026):** the Dispatcher's picker of all old saved runs stays for now, so reviews can be tested without processing new messages. Remove it or limit it to real dispatches once the chat-to-dispatcher path works ([plan, Dispatcher section](FRONTEND_PLAN.md#dispatcher-the-working-demo)). Build nothing new that depends on it.
- **Later, not now:** production run names a dispatcher can choose by date, time and possibly order count, for example "19 September 2026 Allocations - 15 Orders". Today the picker shows the run ID (processing start time), the source file name and a message count, not an order count. Decide later which date to show, what the count means and that the backend supplies the name.

## Results

Filled in as each step is checked.

**Step 1 (21 October 2026).** `npm install --save-exact --cache ./.npm ...` added the packages above to `frontend/node_modules` only. `npm run build` compiled four static routes and created `tsconfig.json` and `next-env.d.ts`; `"strict"` was then switched from `false` to `true` so that null values (unavailable metrics) are type-checked. `npm run typecheck` and `npm run lint` report no problems; ESLint checked all six source files.
- `npm audit` reports 5 high-severity advisories, all one issue: `braces` (stack-exhaustion denial of service from deeply nested glob patterns), reached only through the linting tools (`eslint-config-next` -> `@next/eslint-plugin-next` -> `fast-glob` -> `micromatch` -> `braces`). It affects local linting, not the browser bundle. npm's only fix downgrades `eslint-config-next` to 14, a breaking change, so it was not applied.
- npm 11 did not run the install script of `unrs-resolver` (used by ESLint's import resolver); it was not approved, and linting works without it.
- The npm scripts set `NEXT_TELEMETRY_DISABLED=1`, so Next.js sends no anonymous usage data. This is per command; no global Next.js setting was changed.

**Step 2 (21 October 2026).** Files: `components/RunPicker.tsx`, `components/TaskTable.tsx`, `components/TaskDetails.tsx`, `components/QueueTable.tsx`, `app/dispatcher/page.tsx`, styles in `app/globals.css`. `npm run typecheck`, `npm run lint` and `npm run build` pass.
- `tsconfig.json` had no `@/` import alias (the build-generated file has none), so every `@/...` import failed the type check. Added `"paths": {"@/*": ["./*"]}`, the standard Next.js alias, without the `baseUrl` that TypeScript 6 deprecates.
- Checked against the real read-only FastAPI (`cd backend && uv run fastapi dev main.py --host 127.0.0.1 --port 8000`) through the Next.js rewrite: `/api/backend/runs` lists 15 runs; an unknown run and an unknown thread return the backend's 404 `detail` unchanged. The first GET /reviews created the empty `output/dispatcher-review-checkpoints.sqlite`, as expected.
- A script compared every field the components read with all 13 saved plans. Only `review_warnings` was missing, in 12 plans made before 15 October 2026 (only `2026-10-19_11-25-25` has it). Reading `plan.review_warnings[row.id]` would have thrown on those runs. The field is now optional in `lib/types.ts`; strict TypeScript then found exactly the two reads (`lib/plan.ts`, `components/TaskDetails.tsx`), which now handle its absence, and the page says the warnings were not recorded, as the backend's run report does (`eval_run_report/run_summary.py`).
- "Deadline used" reads `order_snapshot.due_date`, which `recommend_one_task.py` sets from `task_deadline(task)`: the chat deadline when given, otherwise orders.csv.
- In Chromium: no page or console errors on an old plan, the newest 181-row plan and a run without `plan.json`. Filter counts add up to All after adding a "No request" filter for `non_task` rows (30 = 27 + 2 + 0 + 1; 181 = 165 + 4 + 0 + 12). Review rows show their workshop as "(option only)"; the comparison lists ranked, late-removed and rule-rejected workshops with the backend's reasons.
- At 390 px the page scrolled 248 px sideways. Measured cause: the run `<select>` (as wide as its longest option) and a navigation bar that did not wrap; wide tables were not a cause (they scroll inside `.table-scroll`). After `select { max-width: 100% }` and wrapping labels and navigation, the overflow is 0.
- With FastAPI stopped, the rewrite returns HTTP 500 with a plain-text body, and the page shows "The backend answered HTTP 500. Check that the FastAPI server is running." Next.js adds its own empty `role="alert"` route announcer, so tests find the error by its text.
- Playwright 1.64.1 expects Chromium revision 1248; revision 1234 is installed. As agreed, scripts and tests point `executablePath` at the existing `chromium_headless_shell-1234` binary; nothing is downloaded.

**Step 3 (21 October 2026).** Files: `playwright.config.ts`, `tests/fixtures.ts`, `tests/dispatcher.spec.ts`; `aria-label="Worklist"` on the worklist table. `npm test` runs 11 tests in about 4 seconds against the Next.js dev server. Each test answers every `/api/backend` request itself and aborts any other, so no test reaches a real FastAPI server.
- Tests: filter counts add up; a suggested row shows its selection, ranking and rule rejections; an informational option is never shown as selected; a warned suggestion needs attention and links to the warning row; a plan without `review_warnings` opens; a partial plan is labelled a preview; a run without a plan; an empty run list; an unreachable backend (the rewrite's plain-text HTTP 500); the backend's own 404 `detail`; a slow answer for an earlier run cannot replace the current run.
- First run: 10 of 11 passed. The failing filter test counted `tbody tr` and got 4 instead of 1; the failure snapshot showed 1 worklist row plus 3 queue-table rows, so the locator was too broad, not the filter. Tests now look inside the table named "Worklist".
- The stale-run test was checked by removing `runRequest.current?.abort()`: it then fails (the earlier request is never cancelled), and passes again with the line restored.
- `/code-simplifier`: one change, in `TaskDetails.tsx`: the comparison's workshop list is built as one list with nulls filtered out, and the "no workshop estimated" return follows it directly. Behaviour unchanged; all checks pass.
- `/systematic-debugging` audit against all 13 real plans, importing `lib/plan.ts` itself: no repeated row IDs, no task in two decision records, every row has evidence (181 rows give 223 non-empty quotes in the newest plan), every formatted number is a number or null, and no rendered text holds a local path (the same pattern matches all 58 unrendered `response_trace` values, so the check can detect one).
- `next build` saves the rewrite address in `.next/routes-manifest.json`, and `next start` with a different `BACKEND_API_URL` still reached port 8000 (HTTP 200 while 8009 had no server). The comments in `next.config.ts` and `.env.example` now say to rebuild after changing the address; `npm run dev` reads it at each start.
