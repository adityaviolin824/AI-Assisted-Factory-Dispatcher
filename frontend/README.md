# Web interface

The Next.js interface for [SweaterCo Dispatch Copilot](../README.md). Chat captures operations requests; Dispatcher reviews the resulting plan and applies the dispatcher's decisions. FastAPI owns processing, calculations and saved records.

## Pages

| Route | Purpose |
|---|---|
| `/` | Product introduction, worked dispatch example, recorded evaluation results and methodology. |
| `/operations` | Shared conversation, named senders, message history, fixed snapshots and explicit processing. |
| `/dispatcher` | Saved runs, source evidence, recommendations, exceptions, workshop comparisons, decisions and change reports. |

## Run locally

Use an existing Node.js installation compatible with the locked dependencies. From the repository root:

```sh
cd frontend
npm ci --cache ./.npm
npm run dev
```

The development server binds to `http://127.0.0.1:3000`. Start the [backend](../backend/README.md#which-script-to-use) separately at `http://127.0.0.1:8000`.

Browser requests use `/api/backend/...`. The rewrite in [next.config.ts](next.config.ts) forwards them to `BACKEND_API_URL`, which defaults to `http://127.0.0.1:8000`. Changing that address requires restarting development or rebuilding production output. Model credentials remain in the backend.

Opening a page, sending messages, capturing snapshots and reviewing plans make no model calls. Processing a snapshot can incur model charges and requires the backend to start with `ALLOW_PAID_PROCESSING=1`.

## Dispatcher interaction

1. Select a run or follow the Chat link to its paused review.
2. Inspect original messages, request facts, warnings and calculated workshop options.
3. Stage corrections, workshop choices, cancellations and added batches in page memory. Ordinary edits make no request and save nothing.
4. Optionally select **Check workshop options**. This submits the complete choice set for a calculation without saving it. A later edit invalidates the preview.
5. Select **Approve all** once. Python preserves manual destinations, replans flexible work from the original queues, saves the table and returns the changes.
6. Use **Review again** on a saved table to add or change decisions and save a new version. Earlier versions remain in plan history.

Reallocation is this recalculation of the dispatch table. It does not transfer work already in production. A saved table can retain unresolved rows. Informational alternatives and provisional suggestions are displayed separately from approved work.

## Structure

| Location | Responsibility |
|---|---|
| `app/` | Routes, layout and shared styles. |
| `components/` | Chat controls, processing status, dispatch tables, detail views and decision forms. |
| `lib/api.ts` | Calls to the existing FastAPI endpoints. |
| `lib/choices.ts` | Convert local form choices into structured dispatcher decisions. |
| `lib/types.ts` | API and display types. |
| `tests/` | Playwright interactions with controlled API responses. |

React displays backend results; it does not calculate workshop rankings, production time, cost or queue reservations. The **Cancel this request** checkbox stages a `cancel` decision, which Approve all sends alone for that row. The saved row shows as Cancelled under the "No request or cancelled" filter and reserves no workshop time; on a saved table, Review again offers only its undo (`clear`). Cancelling is distinct from removing an added batch or leaving a row unresolved.

## Verification

From `frontend/`:

```sh
npm run typecheck
npm run lint
npm run build
npm test
```

The latest recorded checks, on 24 October 2026 after the cancellation change, passed 66 Playwright tests, type checking, lint and the production build.

Playwright uses the Chromium executable configured in [playwright.config.ts](playwright.config.ts); `CHROMIUM_PATH` can select an existing compatible binary. The default references a locally installed browser, so a clean checkout needs an available browser executable. Tests simulate backend responses; they do not process paid requests or establish production accuracy. Some backend integration checks additionally depend on local saved runs and notebook references excluded from publication.

## Current limits

- One shared conversation and one dispatcher; authentication, permissions and multiple channels are not implemented.
- Source-linked clarification replies and general-purpose AI question answering are not implemented.
- Internal navigation can discard unsaved dispatcher choices without a confirmation; browser reload/leave protection is separate.
- Recorded evaluation results describe fixed datasets and saved runs. Live factory assignments, production queue updates and measured dispatcher time savings are not established.

See the [system design](../docs/system-design.md), [project plan](../docs/project-plan.md) and [evaluation guide](../evaluation/README.md).
