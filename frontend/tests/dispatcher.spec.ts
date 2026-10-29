import { expect, type Page, type Route, test } from "@playwright/test";
import type { Plan } from "@/lib/types";
import { makePlan, makeUsage, OTHER_RUN, RUN, runDetails } from "./fixtures";

// Every backend request is answered by the test. A request without its own route is aborted, so
// these tests never reach a real FastAPI server. (A later route takes precedence over this one.)
test.beforeEach(async ({ page }) => {
  await page.route("**/api/backend/**", (route) => route.abort());
});

async function serve(page: Page, path: string, json: unknown, status = 200) {
  await page.route(`**/api/backend${path}`, (route) => route.fulfill({ status, json }));
}

async function openRun(page: Page, plan: Plan | null) {
  await serve(page, "/runs", [RUN]);
  await serve(page, `/runs/${RUN.run_id}`, runDetails(plan));
  await page.goto("/dispatcher");
  await page.getByLabel("Saved run").selectOption(RUN.run_id);
}

function details(page: Page, rowId: string) {
  return page.getByRole("region", { name: `Details of ${rowId}` });
}

function worklistRows(page: Page) {
  return page.getByRole("table", { name: "Worklist" }).locator("tbody tr");
}

test("filter counts add up to all rows", async ({ page }) => {
  await openRun(page, makePlan());
  await expect(page.getByRole("group", { name: "Worklist filter" })).toHaveText(
    "All (4)Needs attention (2)Suggested (1)Approved (0)No request or cancelled (1)",
  );
  await page.getByRole("button", { name: "No request or cancelled (1)" }).click();
  await expect(worklistRows(page)).toHaveCount(1);
  await expect(worklistRows(page)).toContainText("L0003");
});

test("a suggested row shows its selected workshop and the comparison", async ({ page }) => {
  await openRun(page, makePlan());
  await page.getByRole("button", { name: "T:L0001:J1" }).click();
  const comparison = details(page, "T:L0001:J1").getByRole("row");
  await expect(comparison.filter({ hasText: "W6" })).toContainText("Selected");
  await expect(comparison.filter({ hasText: "W1" })).toContainText("Ranked 2");
  await expect(comparison.filter({ hasText: "W4" })).toContainText("Rejected: cannot_make_category=TOPS");
  await expect(details(page, "T:L0001:J1")).toContainText("Pieces150, from orders.csv");
});

test("a batch the dispatcher added shows its facts as added, not corrected", async ({ page }) => {
  const plan = makePlan();
  const suggested = plan.decisions[0];
  const facts = { order_id: "ORD-001", quantity: "300" };
  const task = {
    ...suggested.task,
    task_id: "ADD-1",
    source_message_ids: [],
    added: true,
    quantity: 300,
    dispatcher: { facts, resolved: [], recorded: { order_id: null, quantity: null }, recorded_deadline: null },
  };
  plan.decisions.push({ ...suggested, task_id: "ADD-1", task });
  plan.summary_rows.unshift({ ...plan.summary_rows[0], id: "ADD-1", messages: [], reason: "Added by the dispatcher." });
  await openRun(page, plan);
  await page.getByRole("button", { name: "ADD-1" }).click();
  await expect(details(page, "ADD-1")).toContainText("Added by the dispatcher: no chat message.");
  await expect(details(page, "ADD-1")).toContainText("Added by the dispatcher: order_id ORD-001; quantity 300");
  await expect(details(page, "ADD-1")).not.toContainText("Corrected by the dispatcher");
});

test("an informational option is never shown as selected", async ({ page }) => {
  await openRun(page, makePlan());
  await expect(worklistRows(page).filter({ hasText: "T:L0002:J1" })).toContainText("W2 (option only)");
  await page.getByRole("button", { name: "T:L0002:J1" }).click();
  const panel = details(page, "T:L0002:J1");
  await expect(panel).toContainText("Closest late option (information only, not selected): W2 SteadyHands");
  await expect(panel.getByRole("cell", { name: "Selected", exact: true })).toHaveCount(0);
});

test("a suggestion that an unresolved message may change needs attention", async ({ page }) => {
  const plan = makePlan();
  plan.review_warnings = { "T:L0001:J1": ["T:L0004:J1"] };
  plan.summary_rows[0].outcome = "provisional_recommendation";
  await openRun(page, plan);
  await expect(page.getByRole("button", { name: "Suggested (0)" })).toBeVisible();
  await page.getByRole("button", { name: "T:L0001:J1" }).click();
  await expect(details(page, "T:L0001:J1")).toContainText("Provisional");
  await details(page, "T:L0001:J1").getByRole("button", { name: "T:L0004:J1" }).click();
  await expect(details(page, "T:L0004:J1")).toContainText("Missing: Order ID for the scarves");
});

test("a plan made before review warnings still opens", async ({ page }) => {
  const plan = makePlan();
  delete plan.review_warnings;
  await openRun(page, plan);
  await expect(page.getByText("made before review warnings were recorded")).toBeVisible();
  await page.getByRole("button", { name: "T:L0001:J1" }).click();
  await expect(details(page, "T:L0001:J1")).toBeVisible();
});

test("a partial plan is labelled a preview", async ({ page }) => {
  const plan = makePlan();
  plan.processing_complete = false;
  await openRun(page, plan);
  await expect(page.getByText("this plan is a partial preview")).toBeVisible();
});

test("a run without a plan says so", async ({ page }) => {
  await openRun(page, null);
  await expect(page.getByText("Run R1 has no plan")).toBeVisible();
});

test("an empty run list says so", async ({ page }) => {
  await serve(page, "/runs", []);
  await page.goto("/dispatcher");
  await expect(page.getByText("The backend has no saved runs.")).toBeVisible();
});

test("an unreachable backend is reported", async ({ page }) => {
  // What the Next.js rewrite answers when FastAPI is not running: HTTP 500 with a plain-text body.
  await page.route("**/api/backend/runs", (route) =>
    route.fulfill({ status: 500, contentType: "text/plain", body: "Internal Server Error" }),
  );
  await page.goto("/dispatcher");
  await expect(
    page.getByText("The backend answered HTTP 500. Check that the FastAPI server is running."),
  ).toBeVisible();
});

test("the backend's own error message is shown unchanged", async ({ page }) => {
  await serve(page, "/runs", [RUN]);
  await serve(page, "/runs/R1", { detail: "No saved run R1." }, 404);
  await page.goto("/dispatcher");
  await page.getByLabel("Saved run").selectOption("R1");
  await expect(page.getByText("No saved run R1.")).toBeVisible();
});

test("a slow answer for an earlier run cannot replace the current run", async ({ page }) => {
  const laterPlan = { ...makePlan(), dispatch_date: "2026-04-02" };
  let slowRoute: Route | null = null;
  await serve(page, "/runs", [RUN, OTHER_RUN]);
  await page.route("**/api/backend/runs/R1", (route) => {
    slowRoute = route;
  });
  await serve(page, "/runs/R2", runDetails(laterPlan, "R2"));
  await page.goto("/dispatcher");

  const picker = page.getByLabel("Saved run");
  await picker.selectOption("R1");
  await expect.poll(() => slowRoute).not.toBeNull();
  const aborted = page.waitForEvent("requestfailed", (request) => request.url().endsWith("/runs/R1"));
  await picker.selectOption("R2");
  await aborted;
  await expect(page.getByText("planned from 2026-04-02")).toBeVisible();
  await expect(page.getByText("planned from 2026-04-01")).toHaveCount(0);
});

test("a run of one message is counted in the singular", async ({ page }) => {
  await serve(page, "/runs", [{ ...RUN, messages: 1 }, OTHER_RUN]);
  await page.goto("/dispatcher");
  await expect(page.getByLabel("Saved run").locator("option")).toHaveText([
    "Choose a run",
    "R1: chat.txt (1 message)",
    "R2: other-chat.txt (4 messages)",
  ]);
});

test("a long run name fits a phone screen", async ({ page }) => {
  // Real run labels are long, such as "dispatch_requests_extended.txt (222 messages)".
  const longRun = { ...RUN, label: "dispatch_requests_extended_with_follow_ups.txt", messages: 222 };
  await page.setViewportSize({ width: 390, height: 844 });
  await serve(page, "/runs", [longRun]);
  await serve(page, `/runs/${RUN.run_id}`, runDetails(makePlan()));
  await page.goto("/dispatcher");
  await page.getByLabel("Saved run").selectOption(RUN.run_id);
  await expect(page.getByRole("table", { name: "Worklist" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBe(0);
});

test("on a phone, choosing a row brings its details into view", async ({ page }) => {
  // Real runs have up to 181 rows; on a narrow screen the details come after all of them.
  const plan = makePlan();
  const message = plan.summary_rows[2];
  plan.summary_rows.push(...Array.from({ length: 60 }, (_, index) => ({ ...message, id: `L09${index}` })));
  await page.setViewportSize({ width: 390, height: 844 });
  await openRun(page, plan);
  await page.getByRole("button", { name: "T:L0001:J1" }).click();
  await expect(details(page, "T:L0001:J1").getByRole("heading", { name: "T:L0001:J1" })).toBeInViewport();
});

test("a run named in the address opens directly", async ({ page }) => {
  await serve(page, "/runs", [RUN, OTHER_RUN]);
  await serve(page, "/runs/R2", runDetails({ ...makePlan(), dispatch_date: "2026-04-02" }, "R2"));
  await page.goto("/dispatcher?run=R2");
  await expect(page.getByText("planned from 2026-04-02")).toBeVisible();
  await expect(page.getByLabel("Saved run")).toHaveValue("R2");
});

test("choosing a run puts it in the address", async ({ page }) => {
  await openRun(page, makePlan());
  await expect(page).toHaveURL(/\/dispatcher\?run=R1$/);
});

function usagePanel(page: Page) {
  return page.getByRole("region", { name: "Model usage and cost" });
}

test("model usage is read only when its section is opened, and separates paid and saved answers", async ({ page }) => {
  const usageRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/usage")) {
      usageRequests.push(request.url());
    }
  });
  await serve(page, `/runs/${RUN.run_id}/usage`, makeUsage());
  await openRun(page, makePlan());
  await expect(page.getByRole("table", { name: "Worklist" })).toBeVisible();
  expect(usageRequests).toHaveLength(0);

  await usagePanel(page).getByText("Show calls, tokens and cost").click();
  const facts = usagePanel(page).locator("dl");
  await expect(facts).toContainText("Estimated model cost this run$0.0021");
  await expect(facts).toContainText("Paid model calls3 of 10 calls; 7 reused saved answers at no new cost");
  await expect(facts).toContainText("Model time this run2 min 5 s");
  await expect(facts).toContainText("With no saved answers$0.0072, 6 min 1 s of model time");
  await expect(facts).toContainText("Dispatcher review and approvalNo model calls, $0");
  await expect(usagePanel(page)).toContainText("prices checked on 14 October 2026");
  const total = usagePanel(page).getByRole("table", { name: "Model usage by stage" }).getByRole("row", { name: /Total/ });
  await expect(total).toContainText("gpt-5.6-luna1039,0001,5002,400$0.0021$0.0072");
  await expect(usagePanel(page).getByRole("link", { name: /Download usage as JSON/ })).toHaveAttribute(
    "href",
    "/api/backend/runs/R1/usage",
  );
  expect(usageRequests).toHaveLength(1);
});

test("model usage that cannot be read is shown as unavailable", async ({ page }) => {
  await serve(page, `/runs/${RUN.run_id}/usage`, { detail: "No saved run R1." }, 404);
  await openRun(page, makePlan());
  await usagePanel(page).getByText("Show calls, tokens and cost").click();
  await expect(usagePanel(page)).toContainText("Model usage is unavailable: No saved run R1.");
  await expect(usagePanel(page).locator("dl")).toHaveCount(0);
});

test("a model without a listed price has an unavailable cost, never $0", async ({ page }) => {
  const usage = makeUsage();
  for (const stage of usage.stages) {
    stage.cost_this_run = null;
    stage.cost_fresh = null;
  }
  await serve(page, `/runs/${RUN.run_id}/usage`, usage);
  await openRun(page, makePlan());
  await usagePanel(page).getByText("Show calls, tokens and cost").click();
  await expect(usagePanel(page).locator("dl")).toContainText(
    "Estimated model cost this rununavailable: a model in this run has no listed price",
  );
  const total = usagePanel(page).getByRole("row", { name: /Total/ });
  await expect(total).toContainText("2,400--");
});
