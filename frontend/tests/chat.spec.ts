import { expect, type Page, type Request, test } from "@playwright/test";
import type { ChatMessage, NewMessage } from "@/lib/types";
import { makeSnapshot, MESSAGES } from "./fixtures";

// Every backend request is answered by the test, as in dispatcher.spec.ts: the chat endpoints are
// only proposed, and these tests never reach a real backend or a model.
test.beforeEach(async ({ page }) => {
  await page.route("**/api/backend/**", (route) => route.abort());
  await page.route("**/api/backend/chat/snapshots", (route) => route.fulfill({ json: [] }));
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

test("Send stays disabled until there is a name and a message", async ({ page }) => {
  await serveMessages(page, []);
  await page.goto("/operations");
  const send = page.getByRole("button", { name: "Send" });
  await expect(send).toBeDisabled();
  await page.getByLabel("Your name").fill("Chen");
  await expect(send).toBeDisabled();
  await page.getByRole("textbox", { name: "Message", exact: true }).fill("Please allocate ORD-061.");
  await expect(send).toBeEnabled();
});

test("Send saves the message, shows it and clears the draft", async ({ page }) => {
  await serveMessages(page, MESSAGES);
  const bodies = await recordSends(page, (body) => saved(body, 3));
  await page.goto("/operations");
  await page.getByLabel("Your name").fill("Priya");
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
  await page.getByLabel("Your name").fill("Priya");
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
  await page.getByLabel("Your name").fill("Priya");
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
  await page.getByLabel("Your name").fill("Priya");
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

test("the name is remembered in this tab", async ({ page }) => {
  await serveMessages(page, MESSAGES);
  await page.goto("/operations");
  await page.getByLabel("Your name").fill("Priya");
  await page.reload();
  await expect(page.getByLabel("Your name")).toHaveValue("Priya");
});

test("processing waits for a confirmation about paid models, then links the run to Dispatcher", async ({ page }) => {
  const processRequests: Request[] = [];
  page.on("request", (request) => request.url().endsWith("/process") && processRequests.push(request));
  await page.clock.install();
  await serveMessages(page, MESSAGES);
  await page.route("**/api/backend/chat/snapshots", (route) =>
    route.request().method() === "POST" ? route.fulfill({ json: makeSnapshot() }) : route.fulfill({ json: [] }),
  );
  await page.route("**/api/backend/chat/snapshots/S1/process", (route) =>
    route.fulfill({ json: makeSnapshot({ processing: "running" }) }),
  );
  await page.route("**/api/backend/chat/snapshots/S1", (route) =>
    route.fulfill({ json: makeSnapshot({ processing: "finished", run_id: "2026-10-21_09-10-00", thread_id: "T1" }) }),
  );
  await page.goto("/operations");

  await page.getByRole("button", { name: "Process conversation" }).click();
  await expect(page.getByText("Snapshot of 2 messages")).toBeVisible();
  await expect(page.getByText("Processing sends these messages to paid AI models")).toBeVisible();
  expect(processRequests).toHaveLength(0);

  await page.getByRole("button", { name: "Start processing" }).click();
  await expect(page.getByText("Processing. This takes several minutes")).toBeVisible();
  await page.clock.fastForward(5000);
  await expect(page.getByRole("link", { name: "Open in Dispatcher" })).toHaveAttribute(
    "href",
    "/dispatcher?run=2026-10-21_09-10-00&thread=T1",
  );
  expect(processRequests).toHaveLength(1);
});

test("Process conversation is disabled while the chat is empty", async ({ page }) => {
  await serveMessages(page, []);
  await page.goto("/operations");
  await expect(page.getByText("No messages yet.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Process conversation" })).toBeDisabled();
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
