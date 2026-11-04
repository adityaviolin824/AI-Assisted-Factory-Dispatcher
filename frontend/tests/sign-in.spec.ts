import { expect, type Page, test } from "@playwright/test";
import type { NewMessage } from "@/lib/types";
import { signIn } from "./fixtures";

// Signing in only stores a name and role in this tab's sessionStorage; it makes no backend request.
// The pages it opens are answered with empty lists, and any other backend request is aborted. The
// routes belong to the browser context, so they also cover a second tab.
test.beforeEach(async ({ context }) => {
  await context.route("**/api/backend/**", (route) => route.abort());
  await context.route("**/api/backend/chat/messages", (route) => route.fulfill({ json: [] }));
  await context.route("**/api/backend/chat/snapshots", (route) => route.fulfill({ json: [] }));
  await context.route("**/api/backend/runs", (route) => route.fulfill({ json: [] }));
  await context.route("**/api/backend/workshops", (route) => route.fulfill({ json: [] }));
});

async function signInWithForm(page: Page, name: string, role: "Team member" | "Dispatcher") {
  await page.goto("/sign-in");
  await page.getByLabel("Your name").fill(name);
  await page.getByRole("radio", { name: role }).check();
  await page.getByRole("button", { name: "Enter" }).click();
}

function modeLinks(page: Page) {
  return page.getByRole("navigation", { name: "Mode" }).getByRole("link");
}

function savedIdentity(page: Page) {
  return page.evaluate(() => sessionStorage.getItem("identity"));
}

test("a team member starts in the chat and is offered only the Chat page", async ({ page }) => {
  await signInWithForm(page, "  Priya ", "Team member");
  await expect(page).toHaveURL(/\/operations$/);
  await expect(modeLinks(page)).toHaveText(["Chat"]);
  await expect(page.getByRole("banner")).toContainText("Priya");
  await expect(page.getByRole("banner")).toContainText("Team member");
  // The name is saved without its surrounding spaces.
  expect(await savedIdentity(page)).toBe('{"name":"Priya","role":"team"}');
});

test("a dispatcher starts in Dispatcher and is offered only the Dispatcher page", async ({ page }) => {
  await signInWithForm(page, "Mei", "Dispatcher");
  await expect(page).toHaveURL(/\/dispatcher$/);
  await expect(modeLinks(page)).toHaveText(["Dispatcher"]);
  await expect(page.getByRole("banner")).toContainText("Dispatcher");
});

test("Enter explains a missing name, a colon in the name and a missing role", async ({ page }) => {
  await page.goto("/sign-in");
  const enter = page.getByRole("button", { name: "Enter" });
  await enter.click();
  await expect(page.locator("p.error")).toHaveText("Enter your name.");

  // A snapshot line reads "R01 [08:08] Name: text", so the backend refuses a colon in a name.
  await page.getByLabel("Your name").fill("Priya: line lead");
  await page.getByRole("radio", { name: "Team member" }).check();
  await enter.click();
  await expect(page.locator("p.error")).toHaveText("Use a name without a colon.");

  await page.reload();
  await page.getByLabel("Your name").fill("Priya");
  await enter.click();
  await expect(page.locator("p.error")).toHaveText("Choose a role.");
  await expect(page).toHaveURL(/\/sign-in$/);
  expect(await savedIdentity(page)).toBeNull();
});

test("Switch user forgets the name and role and returns to sign-in", async ({ page }) => {
  await signInWithForm(page, "Mei", "Dispatcher");
  await page.getByRole("button", { name: "Switch user" }).click();
  await expect(page).toHaveURL(/\/sign-in$/);
  await expect(page.getByRole("banner").getByRole("link", { name: "Sign in" })).toBeVisible();
  await expect(modeLinks(page)).toHaveCount(0);
  expect(await savedIdentity(page)).toBeNull();
});

test("each browser tab has its own sign-in, so one laptop can show both roles", async ({ context, page }) => {
  await signInWithForm(page, "Mei", "Dispatcher");
  const otherTab = await context.newPage();
  await otherTab.goto("/sign-in");
  await expect(otherTab.getByRole("banner").getByRole("link", { name: "Sign in" })).toBeVisible();

  await signInWithForm(otherTab, "Priya", "Team member");
  await expect(modeLinks(otherTab)).toHaveText(["Chat"]);
  await page.reload();
  await expect(modeLinks(page)).toHaveText(["Dispatcher"]);
});

test("without a sign-in, Chat, Dispatcher and Workshop open the sign-in page and read nothing from the backend", async ({ page }) => {
  const backendRequests: string[] = [];
  page.on("request", (request) => request.url().includes("/api/backend/") && backendRequests.push(request.url()));
  await page.goto("/dispatcher");
  await expect(page).toHaveURL(/\/sign-in$/);
  await page.goto("/operations");
  await expect(page).toHaveURL(/\/sign-in$/);
  await page.goto("/workshop");
  await expect(page).toHaveURL(/\/sign-in$/);
  expect(backendRequests).toEqual([]);
});

test("a team member who opens Dispatcher is sent to the chat, which has no processing panel", async ({ page }) => {
  const dispatchReads: string[] = [];
  page.on("request", (request) => {
    if (/\/api\/backend\/(runs|chat\/snapshots)/.test(request.url())) {
      dispatchReads.push(request.url());
    }
  });
  await signIn(page, "team", "Priya");
  await page.goto("/dispatcher");
  await expect(page).toHaveURL(/\/operations$/);
  await expect(page.getByRole("heading", { name: "Chat", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Prepare chat for dispatch" })).toHaveCount(0);
  expect(dispatchReads).toEqual([]);
});

test("a dispatcher who opens Chat is sent to Dispatcher, which shows the chat only read-only", async ({ page }) => {
  const chatWrites: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/chat/messages") && request.method() !== "GET") {
      chatWrites.push(`${request.method()} ${request.url()}`);
    }
  });
  await signIn(page, "dispatcher", "Mei");
  await page.goto("/operations");
  await expect(page).toHaveURL(/\/dispatcher$/);
  await expect(page.getByRole("heading", { name: "Dispatcher", exact: true })).toBeVisible();
  // No message box, Send or Clear chat anywhere on the dispatcher's page, even with the history open.
  await page.getByRole("button", { name: "See chat history" }).click();
  await expect(page.getByRole("region", { name: "Chat history" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Message", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Send" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Clear chat" })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Dispatch workflow" })).toBeVisible();
  expect(chatWrites).toEqual([]);
});

test("a team member's message is sent under the signed-in name", async ({ page }) => {
  // Answers this page's chat requests: a read returns what has been sent so far.
  const sent: Record<string, unknown>[] = [];
  await page.route("**/api/backend/chat/messages", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: sent });
    }
    const body = route.request().postDataJSON() as NewMessage;
    const message = { message_id: sent.length + 1, sender: body.sender, raw_text: body.raw_text, received_at_utc: "2026-10-21T01:10:00+00:00" };
    sent.push(message);
    return route.fulfill({ json: message });
  });
  await signInWithForm(page, "Priya", "Team member");
  await page.getByRole("textbox", { name: "Message", exact: true }).fill("Please allocate ORD-061.");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("list", { name: "Messages" }).getByRole("listitem")).toContainText("Priya");
  expect(sent.map((message) => message.sender)).toEqual(["Priya"]);
});
