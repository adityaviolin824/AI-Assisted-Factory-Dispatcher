import { expect, type Page, type Route, test } from "@playwright/test";
import type { Review, ReviewEnvelope } from "@/lib/types";
import { makePlan, makeReview, OTHER_RUN, RUN, runDetails } from "./fixtures";

// The dispatcher's local staging. Every backend request is answered by the test, and every POST is
// recorded, so a test fails if a choice sends anything before Approve all.
let posts: { url: string; body: unknown }[] = [];

test.beforeEach(async ({ page }) => {
  posts = [];
  page.on("request", (request) => {
    if (request.method() === "POST") {
      posts.push({ url: request.url(), body: request.postDataJSON() });
    }
  });
  await page.route("**/api/backend/**", (route) => route.abort());
});

async function serve(page: Page, path: string, json: unknown) {
  await page.route(`**/api/backend${path}`, (route) => route.fulfill({ json }));
}

function envelope(review: Review, changes: Partial<ReviewEnvelope> = {}): ReviewEnvelope {
  return { status: "waiting", review, refused: null, ...changes };
}

// Opens run R1 and then the paused review thread TH1.
async function openReview(page: Page, review = makeReview()) {
  await serve(page, "/runs", [RUN]);
  await serve(page, `/runs/${RUN.run_id}`, runDetails(makePlan()));
  await serve(page, "/reviews/TH1", envelope(review));
  await page.goto(`/dispatcher?run=${RUN.run_id}`);
  await page.getByLabel("Paused review thread").fill("TH1");
  await page.getByRole("button", { name: "Open review" }).click();
  await expect(page.getByText("Reviewing thread TH1.")).toBeVisible();
}

function choicesFor(page: Page, taskId: string) {
  return page.getByRole("region", { name: `Your choices for ${taskId}` });
}

function staged(page: Page) {
  return page.getByRole("list", { name: "What Approve all would send" }).getByRole("listitem");
}

test("Chat's link opens the run and its paused review", async ({ page }) => {
  await serve(page, "/runs", [RUN]);
  await serve(page, `/runs/${RUN.run_id}`, runDetails(makePlan()));
  await serve(page, "/reviews/TH1", envelope(makeReview()));
  await page.goto(`/dispatcher?run=${RUN.run_id}&thread=TH1`);
  await expect(page.getByText("Reviewing thread TH1.")).toBeVisible();
  expect(posts).toHaveLength(0);
});

test("a review of another run is not opened", async ({ page }) => {
  await serve(page, "/runs", [RUN]);
  await serve(page, `/runs/${RUN.run_id}`, runDetails(makePlan()));
  await serve(page, "/reviews/TH2", envelope(makeReview({ source_run: "R2" })));
  await page.goto(`/dispatcher?run=${RUN.run_id}`);
  await page.getByLabel("Paused review thread").fill("TH2");
  await page.getByRole("button", { name: "Open review" }).click();
  await expect(page.getByText("Thread TH2 reviews run R2, not the open run R1.")).toBeVisible();
  await expect(page.getByText("Plan before the dispatcher's review")).toBeVisible();
  await page.getByRole("button", { name: "T:L0001:J1" }).click();
  await expect(choicesFor(page, "T:L0001:J1")).toHaveCount(0);
});

test("a review that answers after another run is opened is not shown", async ({ page }) => {
  let held: Route | null = null;
  await serve(page, "/runs", [RUN, OTHER_RUN]);
  await serve(page, `/runs/${RUN.run_id}`, runDetails(makePlan()));
  await serve(page, `/runs/${OTHER_RUN.run_id}`, runDetails(makePlan(), OTHER_RUN.run_id));
  await page.route("**/api/backend/reviews/TH1", (route) => {
    held = route;
  });
  await page.goto(`/dispatcher?run=${RUN.run_id}`);
  await page.getByLabel("Paused review thread").fill("TH1");
  await page.getByRole("button", { name: "Open review" }).click();
  await expect.poll(() => held).not.toBeNull();
  await page.getByLabel("Saved run").selectOption(OTHER_RUN.run_id);
  await expect(page.getByText("Plan before the dispatcher's review")).toBeVisible();
  await held!.fulfill({ json: envelope(makeReview()) }).catch(() => {});
  await expect(page.getByText("Draft under review")).toHaveCount(0);
  await expect(page.getByText("Reviewing thread TH1.")).toHaveCount(0);
});

test("choosing a workshop stays in the page until Approve all", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "T:L0002:J1" }).click();
  await choicesFor(page, "T:L0002:J1").getByLabel("Workshop").selectOption("W2");
  await expect(choicesFor(page, "T:L0002:J1")).toContainText(
    "It ruled the workshop out (estimated_delivery_after_deadline). Your choice is used anyway",
  );
  await expect(page.getByRole("table", { name: "Worklist" })).toContainText("Unsaved: W2");
  await expect(staged(page)).toHaveText(["T:L0002:J1: send to W2"]);
  await expect(page.getByRole("button", { name: "Approve all" })).toBeEnabled();
  await expect(page.getByText("Nothing has been saved yet.")).toBeVisible();
  expect(posts).toEqual([]);
});

test("a chosen workshop is listed beside the review's workshop, whose figures stay", async ({ page }) => {
  // The row's delivery days are W6's (3.18), so the cell keeps W6 and adds the unsaved choice.
  await openReview(page);
  await page.getByRole("button", { name: "T:L0001:J1" }).click();
  await choicesFor(page, "T:L0001:J1").getByLabel("Workshop").selectOption("W1");
  const cells = page.getByRole("table", { name: "Worklist" }).getByRole("row").filter({ hasText: "ORD-001" }).getByRole("cell");
  await expect(cells.nth(3)).toHaveText("W6Unsaved: W1");
  await expect(cells.nth(4)).toHaveText("3.18");
});

test("reset clears one task's choices", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "T:L0001:J1" }).click();
  const choices = choicesFor(page, "T:L0001:J1");
  await choices.getByLabel("Workshop").selectOption("W1");
  await choices.getByLabel("Preference").selectOption("cheapest");
  await expect(staged(page)).toHaveCount(2);
  await choices.getByRole("button", { name: "Reset my choices for this task" }).click();
  await expect(staged(page)).toHaveCount(0);
  await expect(choices.getByLabel("Workshop")).toHaveValue("");
  await expect(choices.getByLabel("Preference")).toHaveValue("fastest");
  await expect(page.getByRole("button", { name: "Approve all" })).toBeEnabled();
  expect(posts).toEqual([]);
});

test("Refresh asks before discarding unsaved choices", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "T:L0001:J1" }).click();
  await choicesFor(page, "T:L0001:J1").getByLabel("Workshop").selectOption("W1");
  const dialogs: string[] = [];
  let accept = false;
  page.on("dialog", (dialog) => {
    dialogs.push(dialog.message());
    return accept ? dialog.accept() : dialog.dismiss();
  });
  await page.getByRole("button", { name: "Refresh" }).click();
  expect(dialogs).toEqual(["Discard your 1 unsaved choice?"]);
  await expect(staged(page)).toHaveText(["T:L0001:J1: send to W1"]);

  accept = true;
  await page.getByRole("button", { name: "Refresh" }).click();
  await expect(page.getByLabel("Paused review thread")).toBeVisible();
  await expect(page.getByText("Plan before the dispatcher's review")).toBeVisible();
});

test("a correction stages only the facts that differ from the review", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "T:L0001:J1" }).click();
  const choices = choicesFor(page, "T:L0001:J1");
  await choices.getByLabel("Preference").selectOption("cheapest");
  await choices.getByLabel("Deadline").fill("2026-04-12");
  await expect(staged(page)).toHaveText(["T:L0001:J1: correct preference to cheapest, due_date to 2026-04-12"]);
  await choices.getByLabel("Preference").selectOption("fastest");
  await expect(staged(page)).toHaveText(["T:L0001:J1: correct due_date to 2026-04-12"]);
  expect(posts).toEqual([]);
});

test("an unclear intent is shown as recorded and can be corrected", async ({ page }) => {
  // Processing records intent "unclear"; a correction may set only allocation or question.
  const review = makeReview();
  review.needs_clarification[0].intent = "unclear";
  await openReview(page, review);
  await page.getByRole("button", { name: "T:L0004:J1" }).click();
  const intent = choicesFor(page, "T:L0004:J1").getByLabel("Intent");
  await expect(intent).toHaveValue("unclear");
  await intent.selectOption("allocation");
  await expect(staged(page)).toHaveText(["T:L0004:J1: correct intent to allocation"]);
});

test("a completed request is sent as one complete decision with its facts", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "T:L0004:J1" }).click();
  const choices = choicesFor(page, "T:L0004:J1");
  await expect(choices.getByLabel("Preference").locator("option[value=quality]")).toHaveText(
    "quality (expensive or delicate item)",
  );
  await choices.getByLabel("Order").fill("ORD-041");
  await choices.getByLabel("Quantity").fill("250");
  await expect(staged(page)).toHaveText(["T:L0004:J1: correct order_id to ORD-041, quantity to 250"]);
  await choices.getByLabel("The request is complete: plan it with these facts").check();
  await expect(staged(page)).toHaveText(["T:L0004:J1: complete the request with order_id ORD-041, quantity 250"]);
  expect(posts).toEqual([]);
  const approved = makeReview({ status: "final" });
  await serve(page, "/reviews/TH1/finalize", envelope(approved, { status: "finished" }));
  await serve(page, `/runs/${RUN.run_id}`, { ...runDetails(makePlan()), dispatcher_plan: approved });
  await page.getByRole("button", { name: "Approve all" }).click();
  await expect(page.getByText("Approved dispatcher plan", { exact: true })).toBeVisible();
  expect(posts).toHaveLength(1);
  expect(posts[0].body).toEqual({
    decisions: [{ decision: "complete", task_id: "T:L0004:J1", facts: { order_id: "ORD-041", quantity: "250" } }],
  });
});

test("added batches stay in the page and are sent as add_batch decisions", async ({ page }) => {
  await openReview(page);
  const added = page.getByRole("region", { name: "Added batches" });
  async function addBatch(facts: Record<string, string>, workshop?: string) {
    await added.getByRole("button", { name: "Add a batch" }).click();
    await expect(added.getByRole("button", { name: "Add to my choices" })).toBeDisabled(); // the order is required
    for (const [label, value] of Object.entries(facts)) {
      await (label === "Preference" ? added.getByLabel(label).selectOption(value) : added.getByLabel(label).fill(value));
    }
    if (workshop) {
      await added.getByLabel("Workshop").selectOption(workshop);
    }
    await added.getByRole("button", { name: "Add to my choices" }).click();
  }
  // A split of ORD-041 into two batches of 300, after removing a batch added by mistake.
  await addBatch({ Order: "ORD-041", Quantity: "300", Preference: "quality" }, "W2");
  await addBatch({ Order: "ORD-099" });
  await expect(staged(page)).toHaveText([
    "New batch of ORD-041: quantity 300, preference quality, send to W2",
    "New batch of ORD-099",
  ]);
  await added.getByRole("button", { name: "Remove" }).nth(1).click();
  await addBatch({ Order: "ORD-041", Quantity: "300" });
  await expect(staged(page)).toHaveText([
    "New batch of ORD-041: quantity 300, preference quality, send to W2",
    "New batch of ORD-041: quantity 300",
  ]);
  expect(posts).toEqual([]);
  const reason = "Added by the dispatcher. Dispatcher's choice: W2 (SteadyHands), delivery in 5.83 of 20 available days.";
  const approved = makeReview({
    status: "final",
    changes: [
      {
        id: "ADD-1",
        order_id: "ORD-041",
        before: null,
        after: { outcome: "dispatcher_choice", workshop: "W2", delivery_days: 5.83, reason },
      },
    ],
  });
  await serve(page, "/reviews/TH1/finalize", envelope(approved, { status: "finished" }));
  await serve(page, `/runs/${RUN.run_id}`, { ...runDetails(makePlan()), dispatcher_plan: approved });
  await page.getByRole("button", { name: "Approve all" }).click();
  await expect(page.getByRole("table", { name: "What changed" }).getByRole("row").nth(1).getByRole("cell")).toHaveText([
    "ADD-1",
    "ORD-041",
    "New batch, added by the dispatcher",
    "Dispatcher's choice, W2, 5.83 days",
    reason,
  ]);
  expect(posts).toHaveLength(1);
  expect(posts[0].body).toEqual({
    decisions: [
      { decision: "add_batch", facts: { order_id: "ORD-041", quantity: "300", preference: "quality" }, workshop_id: "W2" },
      { decision: "add_batch", facts: { order_id: "ORD-041", quantity: "300" } },
    ],
  });
});

// The draft a preview of "T:L0002:J1 to W2" returns: that row accepted late, listed as a change.
const LATE = "Lateness accepted by the dispatcher: W2, delivery in 9.50 of 4 available days.";

function previewDraft() {
  return makeReview({
    summary_rows: makePlan().summary_rows.map((row) =>
      row.id === "T:L0002:J1" ? { ...row, outcome: "accepted_late", reason: LATE } : row,
    ),
    changes: [
      {
        id: "T:L0002:J1",
        order_id: "ORD-002",
        before: { outcome: "review_required", workshop: "W2", delivery_days: 9.5, reason: "Late: W2." },
        after: { outcome: "accepted_late", workshop: "W2", delivery_days: 9.5, reason: LATE },
      },
    ],
  });
}

test("Check workshop options shows an unsaved preview, and a changed choice hides it", async ({ page }) => {
  await openReview(page);
  await expect(page.getByRole("button", { name: "Check workshop options" })).toBeDisabled(); // no choice yet
  await page.getByRole("button", { name: "T:L0002:J1" }).click();
  const choices = choicesFor(page, "T:L0002:J1");
  await choices.getByLabel("Workshop").selectOption("W2");
  await serve(page, "/reviews/TH1/preview", { review: previewDraft(), refused: null });
  await page.getByRole("button", { name: "Check workshop options" }).click();
  // The preview appears above the worklist, far from the button, so it is scrolled into view.
  await expect(page.getByRole("heading", { name: "Preview, not saved" })).toBeInViewport();
  await expect(page.getByText("Preview of your choices, not saved", { exact: true })).toBeVisible();
  await expect(page.getByRole("table", { name: "What would change" }).getByRole("row").nth(1).getByRole("cell")).toHaveText([
    "T:L0002:J1",
    "ORD-002",
    "Needs review, W2 (option only), 9.50 days",
    "Accepted late, W2, 9.50 days",
    LATE,
  ]);
  // The worklist and details show the preview; the review stays open with the choice still unsaved.
  await expect(page.getByRole("table", { name: "Worklist" })).toContainText(LATE);
  await expect(page.getByText("Reviewing thread TH1.")).toBeVisible();
  await expect(staged(page)).toHaveText(["T:L0002:J1: send to W2"]);
  expect(posts).toHaveLength(1);
  expect(posts[0].url).toMatch(/\/api\/backend\/reviews\/TH1\/preview$/);
  expect(posts[0].body).toEqual({ decisions: [{ decision: "choose_workshop", task_id: "T:L0002:J1", workshop_id: "W2" }] });
  // Any changed choice makes the preview out of date, so it is hidden and nothing more is sent.
  await choices.getByLabel("Workshop").selectOption("W1");
  await expect(page.getByRole("heading", { name: "Preview, not saved" })).toHaveCount(0);
  await expect(page.getByRole("table", { name: "Worklist" })).not.toContainText(LATE);
  expect(posts).toHaveLength(1);
});

test("a preview that answers after a choice changed is not shown", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "T:L0002:J1" }).click();
  const choices = choicesFor(page, "T:L0002:J1");
  await choices.getByLabel("Workshop").selectOption("W2");
  let release = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/backend/reviews/TH1/preview", async (route) => {
    await held;
    await route.fulfill({ json: { review: previewDraft(), refused: null } });
  });
  const check = page.getByRole("button", { name: /Check workshop options|Checking/ });
  await check.click();
  await expect(check).toHaveText("Checking...");
  await choices.getByLabel("Workshop").selectOption("W1");
  release();
  await expect(check).toHaveText("Check workshop options");
  await expect(page.getByRole("heading", { name: "Preview, not saved" })).toHaveCount(0);
});

test("a refused check shows the reason, and no preview", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "Add a batch" }).click();
  await page.getByRole("region", { name: "Added batches" }).getByLabel("Order").fill("ORD-999");
  await page.getByRole("button", { name: "Add to my choices" }).click();
  const refused = "Not applied: ADD-1: ORD-999 is not in orders.csv.";
  await serve(page, "/reviews/TH1/preview", { review: makeReview(), refused });
  await page.getByRole("button", { name: "Check workshop options" }).click();
  await expect(page.getByText(`These choices would be refused; nothing was saved. ${refused}`)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Preview, not saved" })).toHaveCount(0);
  await expect(staged(page)).toHaveText(["New batch of ORD-999"]);
});

test("an added batch's workshop can be chosen after checking its options", async ({ page }) => {
  await openReview(page);
  const added = page.getByRole("region", { name: "Added batches" });
  await added.getByRole("button", { name: "Add a batch" }).click();
  await added.getByLabel("Order").fill("ORD-041");
  await added.getByRole("button", { name: "Add to my choices" }).click();
  // The preview names the batch ADD-1 and compares its workshops; the open review has no ADD-1 row.
  const review = makeReview();
  const first = review.decisions[0];
  const addedTask = { ...first.task, task_id: "ADD-1", order_id: "ORD-041", added: true, source_message_ids: [] };
  const preview = makeReview({
    summary_rows: [{ ...review.summary_rows[0], id: "ADD-1", order_id: "ORD-041", messages: [] }, ...review.summary_rows],
    decisions: [{ ...first, task_id: "ADD-1", order_id: "ORD-041", task: addedTask }, ...review.decisions],
    changes: [],
  });
  await serve(page, "/reviews/TH1/preview", { review: preview, refused: null });
  await page.getByRole("button", { name: "Check workshop options" }).click();
  await page.getByRole("button", { name: "ADD-1" }).click();
  await expect(page.getByRole("region", { name: "Details of ADD-1" })).toContainText(
    "choose its workshop under Added batches",
  );
  await added.getByLabel("Workshop for the new batch of ORD-041").selectOption("W2");
  await expect(staged(page)).toHaveText(["New batch of ORD-041: send to W2"]);
  // Like any changed choice, this hides the out-of-date preview and sends nothing.
  await expect(page.getByRole("heading", { name: "Preview, not saved" })).toHaveCount(0);
  expect(posts).toHaveLength(1);
});

test("a checked warning stages exactly its row ID", async ({ page }) => {
  await openReview(page, makeReview({ review_warnings: { "T:L0001:J1": ["T:L0004:J1"] } }));
  await page.getByRole("button", { name: "T:L0001:J1" }).click();
  await choicesFor(page, "T:L0001:J1").getByLabel("T:L0004:J1 does not change this request").check();
  await expect(staged(page)).toHaveText(["T:L0001:J1: not changed by T:L0004:J1"]);
  expect(posts).toEqual([]);
});

test("Approve all sends one empty approval and then shows the saved plan", async ({ page }) => {
  await openReview(page);
  const approved = makeReview({ status: "final" });
  await serve(page, "/reviews/TH1/answer", envelope(approved, { status: "finished" }));
  await serve(page, `/runs/${RUN.run_id}`, { ...runDetails(makePlan()), dispatcher_plan: approved });
  await page.getByRole("button", { name: "Approve all" }).click();
  await expect(page.getByText("Approved and saved.")).toBeVisible();
  await expect(page.getByText("Approved dispatcher plan", { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Dispatcher review" })).toHaveCount(0);
  await expect(page.getByRole("table", { name: "What changed" })).toHaveCount(0);
  expect(posts).toHaveLength(1);
  expect(posts[0].url).toMatch(/\/api\/backend\/reviews\/TH1\/answer$/);
  expect(posts[0].body).toEqual({ decisions: [], then: "approve_all" });
});

test("Approve all sends every choice in one request and then shows what changed", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "T:L0002:J1" }).click();
  await choicesFor(page, "T:L0002:J1").getByLabel("Workshop").selectOption("W2");
  const late = "Lateness accepted by the dispatcher: W2, delivery in 9.50 of 4 available days.";
  const approved = makeReview({
    status: "final",
    changes: [
      {
        id: "T:L0002:J1",
        order_id: "ORD-002",
        before: { outcome: "review_required", workshop: "W2", delivery_days: 9.5, reason: "Late: W2." },
        after: { outcome: "accepted_late", workshop: "W2", delivery_days: 9.5, reason: late },
      },
    ],
  });
  await serve(page, "/reviews/TH1/finalize", envelope(approved, { status: "finished" }));
  await serve(page, `/runs/${RUN.run_id}`, { ...runDetails(makePlan()), dispatcher_plan: approved });
  await page.getByRole("button", { name: "Approve all" }).click();
  await expect(page.getByText("Approved dispatcher plan", { exact: true })).toBeVisible();
  const rows = page.getByRole("table", { name: "What changed" }).getByRole("row");
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(1).getByRole("cell")).toHaveText([
    "T:L0002:J1",
    "ORD-002",
    "Needs review, W2 (option only), 9.50 days",
    "Accepted late, W2, 9.50 days",
    late,
  ]);
  expect(posts).toHaveLength(1);
  expect(posts[0].url).toMatch(/\/api\/backend\/reviews\/TH1\/finalize$/);
  expect(posts[0].body).toEqual({ decisions: [{ decision: "choose_workshop", task_id: "T:L0002:J1", workshop_id: "W2" }] });
});

test("a refused batch keeps the choices so they can be changed", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "T:L0002:J1" }).click();
  await choicesFor(page, "T:L0002:J1").getByLabel("Workshop").selectOption("W2");
  await serve(page, "/reviews/TH1/finalize", envelope(makeReview(), { refused: "Not applied: T:L0002:J1: Late." }));
  await page.getByRole("button", { name: "Approve all" }).click();
  await expect(page.getByText("Not approved: nothing was saved. Not applied: T:L0002:J1: Late.")).toBeVisible();
  await expect(staged(page)).toHaveText(["T:L0002:J1: send to W2"]);
  await expect(page.getByRole("button", { name: "Approve all" })).toBeEnabled();
});

test("a refused approval keeps the review open with the backend's reason", async ({ page }) => {
  await openReview(page);
  await serve(page, "/reviews/TH1/answer", envelope(makeReview(), { refused: "T:L0002:J1 has no workshop." }));
  await page.getByRole("button", { name: "Approve all" }).click();
  await expect(page.getByText("Not approved: nothing was saved. T:L0002:J1 has no workshop.")).toBeVisible();
  await expect(page.getByText("Reviewing thread TH1.")).toBeVisible();
  await expect(page.getByText("Draft under review")).toBeVisible();
});

test("while Approve all runs, the run cannot be changed", async ({ page }) => {
  // A refusal that arrived after a switch would otherwise show this run's review over the other run.
  let held: Route | null = null;
  await openReview(page);
  await page.route("**/api/backend/reviews/TH1/answer", (route) => {
    held = route;
  });
  await page.getByRole("button", { name: "Approve all" }).click();
  await expect.poll(() => held).not.toBeNull();
  await expect(page.getByLabel("Saved run")).toBeDisabled();
  await expect(page.getByRole("button", { name: "Refresh" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Approving..." })).toBeDisabled();
  await held!.fulfill({ json: envelope(makeReview(), { refused: "No." }) });
  await expect(page.getByText("Not approved: nothing was saved. No.")).toBeVisible();
  await expect(page.getByLabel("Saved run")).toBeEnabled();
});

test("an approval with no answer closes the review", async ({ page }) => {
  // The answer route is not served, so the request is aborted as when the backend stops mid-request.
  await openReview(page);
  await page.getByRole("button", { name: "Approve all" }).click();
  await expect(page.getByText("The approval may not have been saved")).toBeVisible();
  await expect(page.getByLabel("Paused review thread")).toBeVisible();
  expect(posts).toHaveLength(1);
});

// Review again. An approved plan of R1: the dispatcher sent T:L0001:J1 to W6 and added ADD-1, an
// approved batch of ORD-041; the other rows are makeReview's.
function approvedPlan(changes: Partial<Review> = {}): Review {
  const plan = makeReview({ status: "final" });
  const first = plan.decisions[0];
  const addedTask = { ...first.task, task_id: "ADD-1", order_id: "ORD-041", added: true, source_message_ids: [] };
  return {
    ...plan,
    summary_rows: [
      { ...plan.summary_rows[0], id: "ADD-1", order_id: "ORD-041", outcome: "approved", final: true, messages: [] },
      ...plan.summary_rows,
    ],
    decisions: [{ ...first, task_id: "ADD-1", order_id: "ORD-041", status: "approved", task: addedTask }, ...plan.decisions],
    dispatcher_entries: {
      "T:L0001:J1": { source_version: 1, workshop: "W6" },
      "ADD-1": { source_version: 0, added: true, facts: { order_id: "ORD-041" } },
    },
    ...changes,
  };
}

// Opens run R1, approved, and its Review again.
async function openReviewAgain(page: Page) {
  await serve(page, "/runs", [RUN]);
  await serve(page, `/runs/${RUN.run_id}`, { ...runDetails(makePlan()), dispatcher_plan: approvedPlan() });
  await page.goto(`/dispatcher?run=${RUN.run_id}`);
  await expect(page.getByText("Approved dispatcher plan", { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Dispatcher review" })).toHaveCount(0);
  await page.getByRole("button", { name: "Review again" }).click();
  await expect(page.getByText("Reviewing the approved plan again.")).toBeVisible();
  await expect(page.getByText("Approved plan, open for new choices")).toBeVisible();
}

test("Review again sends undo, removal and new choices to the run, and shows the new version", async ({ page }) => {
  await openReviewAgain(page);
  // No thread and no reallocation here, and Approve all waits for a choice.
  await expect(page.getByRole("button", { name: "Approve all" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Reallocate" })).toHaveCount(0);

  await page.getByRole("button", { name: "ADD-1" }).click();
  const added = choicesFor(page, "ADD-1");
  await expect(added.getByLabel("The request is complete: plan it with these facts")).toHaveCount(0);
  await added.getByLabel("Remove this added batch").check();
  await page.getByRole("button", { name: "T:L0001:J1" }).click();
  const placed = choicesFor(page, "T:L0001:J1");
  await placed.getByLabel("Undo my saved choices for this task").check();
  await expect(placed.getByLabel("Workshop")).toBeDisabled();
  await page.getByRole("button", { name: "T:L0002:J1" }).click();
  await choicesFor(page, "T:L0002:J1").getByLabel("Workshop").selectOption("W2");
  await expect(staged(page)).toHaveText([
    "ADD-1: remove this added batch",
    "T:L0001:J1: undo your saved choices",
    "T:L0002:J1: send to W2",
  ]);
  await expect(page.getByRole("table", { name: "Worklist" })).toContainText("Unsaved: undo");
  expect(posts).toEqual([]);

  const removed = { outcome: "approved", workshop: "W6", delivery_days: 3.18, reason: "Reason for ADD-1." };
  const saved = approvedPlan({ changes: [{ id: "ADD-1", order_id: "ORD-041", before: removed, after: null }] });
  await serve(page, `/runs/${RUN.run_id}/finalize`, { review: saved, refused: null });
  await serve(page, `/runs/${RUN.run_id}`, { ...runDetails(makePlan()), dispatcher_plan: saved });
  await page.getByRole("button", { name: "Approve all" }).click();
  await expect(page.getByText("Saved as a new version.")).toBeVisible();
  await expect(page.getByText("Approved dispatcher plan", { exact: true })).toBeVisible();
  await expect(page.getByRole("table", { name: "What changed" }).getByRole("row").nth(1).getByRole("cell")).toHaveText([
    "ADD-1",
    "ORD-041",
    "Approved (final), W6, 3.18 days",
    "Removed by the dispatcher",
    "The dispatcher removed this added batch.",
  ]);
  expect(posts).toHaveLength(1);
  expect(posts[0].url).toMatch(/\/api\/backend\/runs\/R1\/finalize$/);
  expect(posts[0].body).toEqual({
    decisions: [
      { decision: "clear", task_id: "ADD-1" },
      { decision: "clear", task_id: "T:L0001:J1" },
      { decision: "choose_workshop", task_id: "T:L0002:J1", workshop_id: "W2" },
    ],
  });
});

test("Review again checks options on the run, keeps choices after a refusal and closes without saving", async ({
  page,
}) => {
  await openReviewAgain(page);
  await page.getByRole("button", { name: "T:L0002:J1" }).click();
  await choicesFor(page, "T:L0002:J1").getByLabel("Workshop").selectOption("W2");
  await serve(page, `/runs/${RUN.run_id}/preview`, { review: makeReview({ changes: [] }), refused: null });
  await page.getByRole("button", { name: "Check workshop options" }).click();
  await expect(page.getByRole("heading", { name: "Preview, not saved" })).toBeVisible();

  await serve(page, `/runs/${RUN.run_id}/finalize`, { review: approvedPlan(), refused: "Not applied: T:L0002:J1: Late." });
  await page.getByRole("button", { name: "Approve all" }).click();
  await expect(page.getByText("Not saved: the approved plan is unchanged. Not applied: T:L0002:J1: Late.")).toBeVisible();
  await expect(staged(page)).toHaveText(["T:L0002:J1: send to W2"]);

  page.on("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Close without saving" }).click();
  await expect(page.getByRole("button", { name: "Review again" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Dispatcher review" })).toHaveCount(0);
  expect(posts.map((post) => post.url.replace(/.*\/api\/backend/, ""))).toEqual(["/runs/R1/preview", "/runs/R1/finalize"]);
  expect(posts[0].body).toEqual({ decisions: [{ decision: "choose_workshop", task_id: "T:L0002:J1", workshop_id: "W2" }] });
});

test("while Approve all runs, the choices cannot be changed", async ({ page }) => {
  // A choice changed during the save would not be in the request, and the saved plan would replace it.
  let held: Route | null = null;
  await openReview(page);
  await page.getByRole("button", { name: "T:L0002:J1" }).click();
  await choicesFor(page, "T:L0002:J1").getByLabel("Workshop").selectOption("W2");
  await page.route("**/api/backend/reviews/TH1/finalize", (route) => {
    held = route;
  });
  await page.getByRole("button", { name: "Approve all" }).click();
  await expect.poll(() => held).not.toBeNull();
  await expect(choicesFor(page, "T:L0002:J1").getByLabel("Workshop")).toBeDisabled();
  await expect(page.getByRole("region", { name: "Added batches" }).getByRole("button", { name: "Add a batch" })).toBeDisabled();
  await held!.fulfill({ json: envelope(makeReview(), { refused: "No." }) });
  await expect(page.getByText("Not approved: nothing was saved. No.")).toBeVisible();
  await expect(choicesFor(page, "T:L0002:J1").getByLabel("Workshop")).toBeEnabled();
});
