import { expect, type Page, type Request, test } from "@playwright/test";
import type { ChatMessage, NewMessage } from "@/lib/types";
import { MESSAGES, signIn } from "./fixtures";

// Every backend request is answered by the test, as in dispatcher.spec.ts, so these tests never reach
// a real backend or a model. The Chat page belongs to team members, so each test signs in as one; the
// dispatcher's Dispatch workflow panel is tested in dispatcher.spec.ts.
test.beforeEach(async ({ page }) => {
  await signIn(page, "team", "Priya");
  await page.route("**/api/backend/**", (route) => route.abort());
});

async function serveMessages(page: Page, messages: ChatMessage[]) {
  await page.route("**/api/backend/chat/messages", (route) =>
    route.request().method() === "GET" ? route.fulfill({ json: messages }) : route.fallback(),
  );
}

// Records every POST /chat/messages body; `answer` decides each response in turn.
async function recordSends(page: Page, answer: (body: NewMessage, attempt: number) => object) {
  const bodies: NewMessage[] = [];
  await page.route("**/api/backend/chat/messages", (route) => {
    if (route.request().method() !== "POST") {
      return route.fallback();
    }
    const body = route.request().postDataJSON() as NewMessage;
    bodies.push(body);
    return route.fulfill(answer(body, bodies.length));
  });
  return bodies;
}

function saved(body: NewMessage, messageId: number) {
  return { json: { message_id: messageId, sender: body.sender, raw_text: body.raw_text, received_at_utc: "2026-10-21T01:10:00+00:00" } };
}

test("the conversation shows each message with its Singapore time, name and original text", async ({ page }) => {
  await serveMessages(page, MESSAGES);
  await page.goto("/operations");
  const first = page.getByRole("list", { name: "Messages" }).getByRole("listitem").first();
  await expect(first).toContainText("09:02");
  await expect(first).toContainText("Chen");
  // The original line break is kept.
  await expect(first.locator(".message-text")).toHaveText("Can someone place ORD-107?\n2000 cardigans, due Mar 16.");
  await expect(page.getByText("2 messages, the last at 09:05")).toBeVisible();
});

test("the chat says which date relative words count from", async ({ page }) => {
  await serveMessages(page, MESSAGES);
  await page.route("**/api/backend/chat/dates", (route) =>
    route.fulfill({ json: { message_date: "2026-04-01", dispatch_date: "2026-04-02" } }),
  );
  await page.goto("/operations");
  await expect(
    page.getByText(
      'Words such as "by Friday" count from 1 April 2026, when the supplied chat was written, not from today. ' +
        "Plans start from 2 April 2026.",
    ),
  ).toBeVisible();
});

test("one message is counted in the singular", async ({ page }) => {
  await serveMessages(page, [MESSAGES[0]]);
  await page.goto("/operations");
  await expect(page.getByText("1 message, the last at 09:02")).toBeVisible();
});

test("the Chat page has no dispatch controls: dispatch starts on the Dispatcher page", async ({ page }) => {
  await serveMessages(page, MESSAGES);
  await page.goto("/operations");
  await expect(page.getByRole("list", { name: "Messages" }).getByRole("listitem")).toHaveCount(2);
  await expect(page.getByRole("region", { name: "Dispatch workflow" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Prepare chat for dispatch" })).toHaveCount(0);
});

test("Send stays disabled until there is a message, and the composer asks for no name", async ({ page }) => {
  await serveMessages(page, []);
  await page.goto("/operations");
  const send = page.getByRole("button", { name: "Send" });
  await expect(send).toBeDisabled();
  await expect(page.getByLabel("Your name")).toHaveCount(0);
  await page.getByRole("textbox", { name: "Message", exact: true }).fill("Please allocate ORD-061.");
  await expect(send).toBeEnabled();
});

test("Ctrl+Enter does not send while Send is disabled", async ({ page }) => {
  await serveMessages(page, MESSAGES);
  const bodies = await recordSends(page, (body) => saved(body, 3));
  await page.goto("/operations");
  const message = page.getByRole("textbox", { name: "Message", exact: true });
  await message.press("Control+Enter");
  // Only the message sent afterwards reaches the backend.
  await message.fill("Please allocate ORD-061.");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Please allocate ORD-061.")).toBeVisible();
  expect(bodies.map((body) => body.raw_text)).toEqual(["Please allocate ORD-061."]);
  await expect(page.locator("p.error")).toHaveCount(0);
});

test("Send saves the message, shows it and clears the draft", async ({ page }) => {
  await serveMessages(page, MESSAGES);
  const bodies = await recordSends(page, (body) => saved(body, 3));
  await page.goto("/operations");
  await page.getByRole("textbox", { name: "Message", exact: true }).fill("Please allocate ORD-061.");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByRole("list", { name: "Messages" }).getByRole("listitem")).toHaveCount(3);
  await expect(page.getByRole("textbox", { name: "Message", exact: true })).toHaveValue("");
  expect(bodies).toHaveLength(1);
  expect(bodies[0]).toMatchObject({ sender: "Priya", raw_text: "Please allocate ORD-061." });
  expect(bodies[0].submission_id).toBeTruthy();
});

test("a failed send keeps the draft, and a retry reuses its submission ID", async ({ page }) => {
  await serveMessages(page, MESSAGES);
  const bodies = await recordSends(page, (body, attempt) =>
    attempt === 1 ? { status: 503, json: { detail: "The chat store is busy." } } : saved(body, 3),
  );
  await page.goto("/operations");
  await page.getByRole("textbox", { name: "Message", exact: true }).fill("Please allocate ORD-061.");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("Not sent: The chat store is busy. Your message is still here.")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Message", exact: true })).toHaveValue("Please allocate ORD-061.");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("textbox", { name: "Message", exact: true })).toHaveValue("");
  expect(bodies[1].submission_id).toBe(bodies[0].submission_id);
});

test("editing a draft after a failed send makes it a new submission", async ({ page }) => {
  await serveMessages(page, MESSAGES);
  const bodies = await recordSends(page, () => ({ status: 503, json: { detail: "The chat store is busy." } }));
  await page.goto("/operations");
  await page.getByRole("textbox", { name: "Message", exact: true }).fill("Please allocate ORD-061.");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Not sent: The chat store is busy.")).toBeVisible();
  await page.getByRole("textbox", { name: "Message", exact: true }).fill("Please allocate ORD-062.");
  await page.getByRole("button", { name: "Send" }).click();
  await expect.poll(() => bodies.length).toBe(2);
  expect(bodies[1].submission_id).not.toBe(bodies[0].submission_id);
});

test("while a message sends, its text box cannot change", async ({ page }) => {
  // The saved answer clears the box, so a new draft typed during the send would be lost.
  await serveMessages(page, MESSAGES);
  let release = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/backend/chat/messages", async (route) => {
    if (route.request().method() !== "POST") {
      return route.fallback();
    }
    await held;
    await route.fulfill(saved(route.request().postDataJSON() as NewMessage, 3));
  });
  await page.goto("/operations");
  const box = page.getByRole("textbox", { name: "Message", exact: true });
  await box.fill("Please allocate ORD-061.");
  await box.press("Control+Enter");
  await expect(page.getByRole("button", { name: "Sending..." })).toBeVisible();
  // The box keeps its focus but takes no typing until the message is saved.
  await expect(box).not.toBeEditable();
  await expect(box).toBeFocused();
  await page.keyboard.type(" Also ORD-062.");
  await expect(box).toHaveValue("Please allocate ORD-061.");
  release();
  await expect(page.getByRole("list", { name: "Messages" }).getByRole("listitem")).toHaveCount(3);
  await expect(box).toHaveValue("");
  await expect(box).toBeEditable();
});

test("an open chat empties at the next read after the conversation is cleared", async ({ page }) => {
  await page.clock.install();
  let served = MESSAGES;
  await page.route("**/api/backend/chat/messages", (route) => route.fulfill({ json: served }));
  await page.goto("/operations");
  await expect(page.getByText("2 messages, the last at 09:05")).toBeVisible();

  // Another device clears the chat, so the backend now returns no messages.
  served = [];
  await page.clock.fastForward(3000);
  await expect(page.getByText("No messages yet.")).toBeVisible();
  await expect(page.getByText("0 messages")).toBeVisible();
});

test("a read that started before a Send does not hide the sent message when it answers late", async ({ page }) => {
  await page.clock.install();
  const bodies = await recordSends(page, (body) => saved(body, 3));
  let reads = 0;
  let answerLateRead: (() => Promise<void>) | undefined;
  await page.route("**/api/backend/chat/messages", (route) => {
    if (route.request().method() !== "GET") {
      return route.fallback();
    }
    reads += 1;
    if (reads === 2) {
      // The second read is held until after the Send, as on a slow connection.
      answerLateRead = () => route.fulfill({ json: MESSAGES });
      return;
    }
    return route.fulfill({ json: bodies.length ? [...MESSAGES, saved(bodies[0], 3).json] : MESSAGES });
  });
  await page.goto("/operations");
  await expect(page.getByText("2 messages")).toBeVisible();
  await page.clock.fastForward(3000);
  await expect.poll(() => answerLateRead).toBeDefined();

  await messageBox(page).fill("Please allocate ORD-061.");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("3 messages")).toBeVisible();

  // The held read answers with the two older messages; the page keeps all three.
  const lateAnswer = page.waitForResponse((response) => response.request().method() === "GET" && response.url().endsWith("/chat/messages"));
  await answerLateRead!();
  await lateAnswer;
  await page.waitForTimeout(300);
  // Counted once, not with a retrying check, which would wait for the next read to repair the list.
  expect(await page.getByRole("list", { name: "Messages" }).getByRole("listitem").count()).toBe(3);
});

// Serves a chat that a successful Clear chat really empties; returns the DELETE requests it received.
async function serveClearableChat(page: Page, succeed: boolean) {
  let served = MESSAGES;
  const deletes: Request[] = [];
  await page.route("**/api/backend/chat/messages", (route) => {
    if (route.request().method() !== "DELETE") {
      return route.fulfill({ json: served });
    }
    deletes.push(route.request());
    if (!succeed) {
      return route.fulfill({ status: 500, body: "Internal Server Error" });
    }
    served = [];
    return route.fulfill({ json: { deleted: MESSAGES.length } });
  });
  return deletes;
}

function confirmClear(page: Page) {
  return page.getByRole("group", { name: "Confirm Clear chat" });
}

test("Clear chat asks on the page first, and Cancel sends nothing", async ({ page }) => {
  const deletes = await serveClearableChat(page, true);
  // The question is part of the page, not a browser pop-up.
  const dialogs: string[] = [];
  page.on("dialog", (dialog) => {
    dialogs.push(dialog.message());
    return dialog.dismiss();
  });
  await page.goto("/operations");
  await page.getByRole("button", { name: "Clear chat" }).click();
  await expect(confirmClear(page)).toContainText(
    "Are you sure you want to delete all the chat messages up till now (2 messages)? They are deleted for " +
      "everyone and cannot be recovered. Saved snapshots and dispatch plans stay.",
  );
  await expect(page.getByRole("button", { name: "Clear chat" })).toBeDisabled();

  await confirmClear(page).getByRole("button", { name: "Cancel" }).click();
  await expect(confirmClear(page)).toHaveCount(0);
  await expect(page.getByRole("list", { name: "Messages" }).getByRole("listitem")).toHaveCount(2);
  await expect(page.getByRole("button", { name: "Clear chat" })).toBeEnabled();
  expect(deletes).toHaveLength(0);
  expect(dialogs).toEqual([]);
});

test("Yes, delete sends one request and empties the chat", async ({ page }) => {
  const deletes = await serveClearableChat(page, true);
  await page.goto("/operations");
  await page.getByRole("button", { name: "Clear chat" }).click();
  await confirmClear(page).getByRole("button", { name: "Yes, delete" }).click();
  await expect(page.getByText("No messages yet.")).toBeVisible();
  await expect(page.getByText("0 messages")).toBeVisible();
  await expect(confirmClear(page)).toHaveCount(0);
  // Nothing is left to clear.
  await expect(page.getByRole("button", { name: "Clear chat" })).toBeDisabled();
  expect(deletes).toHaveLength(1);
});

test("a failed Clear chat shows the reason and keeps the messages", async ({ page }) => {
  await serveClearableChat(page, false);
  await page.goto("/operations");
  await page.getByRole("button", { name: "Clear chat" }).click();
  await confirmClear(page).getByRole("button", { name: "Yes, delete" }).click();
  await expect(page.locator("p.error")).toHaveText(
    "Could not clear the chat: The backend answered HTTP 500. Check that the FastAPI server is running.",
  );
  await expect(confirmClear(page)).toHaveCount(0);
  await expect(page.getByRole("list", { name: "Messages" }).getByRole("listitem")).toHaveCount(2);
  await expect(page.getByRole("button", { name: "Clear chat" })).toBeEnabled();
});

function messageBox(page: Page) {
  return page.getByRole("textbox", { name: "Message", exact: true });
}

// Answers POST /chat/transcriptions with `answer`; returns the recordings it received.
async function serveTranscription(page: Page, answer: { status?: number; json: object }) {
  const uploads: Request[] = [];
  await page.route("**/api/backend/chat/transcriptions", (route) => {
    uploads.push(route.request());
    return route.fulfill(answer);
  });
  return uploads;
}

async function recordOnce(page: Page) {
  await page.getByRole("button", { name: "Record", exact: true }).click();
  await expect(page.getByText("Recording. Speak one request")).toBeVisible();
  await page.getByRole("button", { name: "Stop recording" }).click();
}

test("a recording becomes text in the message box to check, and is never sent by itself", async ({ page }) => {
  await serveMessages(page, MESSAGES);
  const sends = await recordSends(page, saved);
  const uploads = await serveTranscription(page, { json: { text: "Please place ORD-045, 150 vests." } });
  await page.goto("/operations");
  await messageBox(page).fill("Urgent:");
  await recordOnce(page);
  await expect(messageBox(page)).toHaveValue("Urgent: Please place ORD-045, 150 vests.");
  await expect(page.getByText("Check the transcript before Send, especially order IDs")).toBeVisible();
  expect(uploads).toHaveLength(1);
  expect(uploads[0].headers()["content-type"]).toContain("multipart/form-data");
  expect(uploads[0].postDataBuffer()?.toString("latin1")).toContain('filename="speech.');
  expect(sends).toHaveLength(0);
});

test("a Mandarin transcript is marked experimental", async ({ page }) => {
  await serveMessages(page, MESSAGES);
  await serveTranscription(page, { json: { text: "ORD-045 要150件，不要用W7。" } });
  await page.goto("/operations");
  await recordOnce(page);
  await expect(messageBox(page)).toHaveValue("ORD-045 要150件，不要用W7。");
  await expect(page.getByText("Mandarin is experimental")).toBeVisible();
});

test("a refused transcription keeps the typed text and says why", async ({ page }) => {
  await serveMessages(page, MESSAGES);
  await serveTranscription(page, {
    status: 403,
    json: { detail: "Voice input is switched off because it calls a paid AI model." },
  });
  await page.goto("/operations");
  await messageBox(page).fill("Typed text");
  await recordOnce(page);
  await expect(page.locator("p.error")).toHaveText(
    "Not transcribed: Voice input is switched off because it calls a paid AI model.",
  );
  await expect(messageBox(page)).toHaveValue("Typed text");
  await expect(page.getByRole("button", { name: "Record", exact: true })).toBeEnabled();
});

test("the chat fits a phone screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await serveMessages(page, MESSAGES);
  await page.goto("/operations");
  await expect(page.getByRole("list", { name: "Messages" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBe(0);
});

test("an unreachable backend is reported without a loading message", async ({ page }) => {
  await page.goto("/operations");
  await expect(page.getByText("Could not read the conversation")).toBeVisible();
  await expect(page.getByText("Loading messages...")).toHaveCount(0);
});
