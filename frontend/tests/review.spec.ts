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
  await expect(page.getByText("Nothing has been sent yet.")).toBeVisible();
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
