# Web interface

The Next.js interface for [SweaterCo Dispatch Copilot](../README.md). Chat captures operations requests; Dispatcher reviews the resulting plan and applies the dispatcher's decisions. FastAPI owns processing, calculations and saved records.

## Pages

| Route | Purpose |
|---|---|
| `/` | Product introduction, worked dispatch example, recorded evaluation results and methodology. |
| `/operations` | Shared conversation, named senders, message history, optional voice input, fixed snapshots and an explicitly started dispatch workflow. |
| `/dispatcher` | Saved runs, source evidence, recommendations, exceptions, workshop comparisons, decisions, change reports and each run's model usage and estimated cost. |

## Run locally

Use an existing Node.js installation compatible with the locked dependencies. From the repository root:

```sh
cd frontend
npm ci --cache ./.npm
npm run dev
```

The development server binds to `http://127.0.0.1:3000`. Start the [backend](../backend/README.md#which-script-to-use) separately at `http://127.0.0.1:8000`.

Browser requests use `/api/backend/...`. The rewrite in [next.config.ts](next.config.ts) forwards them to `BACKEND_API_URL`, which defaults to `http://127.0.0.1:8000`. Changing that address requires restarting development or rebuilding production output. Model credentials remain in the backend.

Opening a page, sending messages, capturing snapshots, reading model usage and reviewing plans make no paid model calls; sending a Chinese message can use the backend's local translation model. Two Chat actions can incur model charges, and the backend refuses both unless it was started with `ALLOW_PAID_PROCESSING=1`: **Start dispatch workflow**, which processes a snapshot, and **Record**, which sends one recording for transcription.

### Use an Android phone without deployment

The laptop can serve the application while a connected Android phone runs the real interface. Start the frontend and backend normally; no public hosting or Wi-Fi connection between the devices is needed for Chrome's USB port forwarding.

1. Enable developer options and USB debugging on the Android phone. Connect a data-capable USB cable, open Chrome on the phone and approve the computer's debugging connection.
2. In desktop Chrome, open `chrome://inspect/#devices` and enable **Discover USB devices**.
3. Open **Port forwarding**, enable it and map device port `3000` to `127.0.0.1:3000` on the laptop.
4. In Chrome on the phone, open `http://localhost:3000/operations` or `http://localhost:3000/dispatcher`.
5. To display the real phone page on the laptop/projector, select **inspect** for that phone tab and enable **Toggle Screencast**. It mirrors page content, rather than the entire Android interface.

The existing Next.js rewrite forwards API requests to FastAPI on the laptop, so only frontend port 3000 needs forwarding. Backend credentials stay on the laptop. A fresh processing run still needs the normal paid-processing permission and provider connectivity.

Use forwarded `localhost` for this setup. A plain HTTP LAN address is not equivalent: the chat uses `crypto.randomUUID()` and recording uses `getUserMedia()`, which require a secure browser context. This setup is documented from [Chrome's port-forwarding guide](https://developer.chrome.com/docs/devtools/remote-debugging/local-server) and [remote debugging/screencasting guide](https://developer.chrome.com/docs/devtools/remote-debugging/); a physical phone has not yet been tested with this project.

## Chat interaction

1. Enter a name and type a message. Alternatively, select **Record**, speak one request and select **Stop recording**; recording stops by itself after one minute. The transcript is added to the message box and is never sent by itself.
2. Check and edit the text before **Send**, especially order IDs, quantities and dates. **Send** saves the message for everyone and makes no paid model call. With the backend's translation switch on, a message containing Chinese is saved, and then shown, as its English translation (30 October 2026); a translation that changed an order or workshop ID is refused with the reason, and the text stays in the box.
3. **Prepare chat for dispatch** captures a fixed copy of the whole conversation. It makes no model call.
4. **Start dispatch workflow** asks for confirmation, then processes that copy with paid models up to the dispatcher's review. The page links to the review when it is ready.

Voice input (29 October 2026): the browser records WebM (Chrome, Firefox) or MP4 (Safari). The backend sends the recording to OpenAI's `gpt-transcribe`, with English and Mandarin as language hints and the order-ID prefix, workshop IDs and names and product names as keywords, and returns only the text. Neither the recording nor the transcript is saved; a transcript becomes a message only when the worker sends it. English is the supported language. A transcript containing Chinese characters shows that Mandarin is experimental and that Send saves an English machine translation when translation is switched on. A refused or failed transcription keeps any typed text and shows the reason.

## Dispatcher interaction

1. Select a run or follow the Chat link to its paused review.
2. Inspect original messages, request facts, warnings and calculated workshop options.
3. Stage corrections, workshop choices, cancellations and added batches in page memory. Ordinary edits make no request and save nothing.
4. Optionally select **Check workshop options**. This submits the complete choice set for a calculation without saving it. A later edit invalidates the preview.
5. Select **Approve all** once. Python preserves manual destinations, replans flexible work from the original queues, saves the table and returns the changes.
6. Use **Review again** on a saved table to add or change decisions and save a new version. Earlier versions remain in plan history.

Reallocation is this recalculation of the dispatch table. It does not transfer work already in production. A saved table can retain unresolved rows. Informational alternatives and provisional suggestions are displayed separately from approved work.

**Model usage and cost** (29 October 2026), below the queue table, loads only when opened. It reads `GET /runs/{run_id}/usage` and shows the run's estimated model cost, paid and reused calls, model time, failed calls and what the same run would cost with no saved answers, with a per-stage table and a JSON download. The figures are estimates from the backend's stored price table (prices checked 14 October 2026), not a provider invoice. Model time is the sum of call durations, not elapsed time. Dispatcher review and approval make no model calls, so they add nothing.

## Structure

| Location | Responsibility |
|---|---|
| `app/` | Routes, layout and shared styles. |
| `components/` | Chat controls and voice recording, dispatch workflow status, dispatch tables, detail views, model usage and decision forms. |
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

The latest recorded checks, on 30 October 2026 after local translation, passed 72 Playwright tests, type checking, lint and the production build.

Playwright uses the Chromium executable configured in [playwright.config.ts](playwright.config.ts); `CHROMIUM_PATH` can select an existing compatible binary. The default references a locally installed browser, so a clean checkout needs an available browser executable. Tests simulate backend responses; they do not process paid requests or establish production accuracy. Voice tests record from Chromium's fake microphone (`--use-fake-ui-for-media-stream`, `--use-fake-device-for-media-stream`) and answer the transcription request themselves, so no real speech is recognised and no model is called. Some backend integration checks additionally depend on local saved runs and notebook references excluded from publication.

## Current limits

- One shared conversation and one dispatcher; authentication, permissions and multiple channels are not implemented.
- Source-linked clarification replies and general-purpose AI question answering are not implemented.
- Voice input sends audio to OpenAI and has not been measured on real speech. Mandarin is experimental; Singapore English pronunciation, Singlish and Mandarin-English code-switching are not evaluated. Local speech recognition remains future work.
- A translated message shows only its English; the original Chinese is not kept, and the page does not mark the message as translated.
- Internal navigation can discard unsaved dispatcher choices without a confirmation; browser reload/leave protection is separate.
- Recorded evaluation results describe fixed datasets and saved runs. Live factory assignments, production queue updates and measured dispatcher time savings are not established.

See the [system design](../docs/system-design.md), [project plan](../docs/project-plan.md) and [evaluation guide](../evaluation/README.md).
