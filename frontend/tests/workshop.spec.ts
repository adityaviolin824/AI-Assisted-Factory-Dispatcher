import { expect, type Page, test } from "@playwright/test";
import type { NewWorkshopReport, Workshop } from "@/lib/types";
import { makeWorkshop, signIn } from "./fixtures";

// The workshop page reads GET /workshops and saves with PUT /workshops/{id}. Every backend request is
// answered by the test; any other request is aborted. The routes belong to the browser context, so they
// also cover a second tab.
const NIMBLE = { workshopId: "W6", workshopName: "Nimble Needle" };

test.beforeEach(async ({ context }) => {
  await context.route("**/api/backend/**", (route) => route.abort());
  await context.route("**/api/backend/workshops", (route) =>
    route.fulfill({ json: [makeWorkshop({ workshop_id: "W1", name: "QuickStitch" }), makeWorkshop()] }),
  );
});

function modeLinks(page: Page) {
  return page.getByRole("navigation", { name: "Mode" }).getByRole("link");
}

function reportForm(page: Page) {
  return page.getByRole("form", { name: "Your report" });
}

test("a workshop chooses itself at sign-in and lands on its own page", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByLabel("Your name").fill("Arun");
  // The Dispatcher hint also mentions workshops, so the Workshop role is matched from the start of its name.
  await page.getByRole("radio", { name: /^Workshop/ }).check();
  await page.getByRole("button", { name: "Enter" }).click();
  await expect(page.locator("p.error")).toHaveText("Choose your workshop.");

  await page.getByRole("combobox", { name: "Your workshop" }).selectOption({ label: "W6 Nimble Needle" });
  await page.getByRole("button", { name: "Enter" }).click();
  await expect(page).toHaveURL(/\/workshop$/);
  await expect(modeLinks(page)).toHaveText(["Workshop"]);
  await expect(page.getByRole("banner")).toContainText("Workshop, Nimble Needle");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Nimble Needle W6");
  expect(await page.evaluate(() => sessionStorage.getItem("identity"))).toBe(
    '{"name":"Arun","role":"workshop","workshopId":"W6","workshopName":"Nimble Needle"}',
  );
});

test("if the workshop list fails to load, choosing Workshop again loads it", async ({ context, page }) => {
  // A sleeping free-tier backend can fail the first read; the second one succeeds.
  let reads = 0;
  await context.route("**/api/backend/workshops", (route) => {
    reads += 1;
    return reads === 1 ? route.abort() : route.fulfill({ json: [makeWorkshop()] });
  });
  await page.goto("/sign-in");
  await page.getByLabel("Your name").fill("Arun");
  const workshopRole = page.getByRole("radio", { name: /^Workshop/ });
  // click, not check: the failed read un-chooses Workshop, often before check could confirm the choice.
  await workshopRole.click();
  await expect(page.locator("p.error")).toContainText("Could not load the workshops");
  await expect(workshopRole).not.toBeChecked();
  await workshopRole.check();
  await page.getByRole("combobox", { name: "Your workshop" }).selectOption({ label: "W6 Nimble Needle" });
  // Two reads on the sign-in page; the Workshop page then reads the list again itself.
  expect(reads).toBe(2);
  await page.getByRole("button", { name: "Enter" }).click();
  await expect(page).toHaveURL(/\/workshop$/);
});

test("Save sends the report under the signed-in name and says it applies from the next run", async ({ page }) => {
  const sent: NewWorkshopReport[] = [];
  await page.route("**/api/backend/workshops/W6", (route) => {
    const report = route.request().postDataJSON() as NewWorkshopReport;
    sent.push(report);
    const saved: Workshop = makeWorkshop({
      current: {
        taking_new_work: report.taking_new_work,
        capacity: report.capacity,
        queue_days: report.queue_days,
        lead_days: report.lead_days,
      },
      last_report: { ...report, workshop_id: "W6", reported_at: "2026-11-03T02:00:00+00:00" },
    });
    return route.fulfill({ json: saved });
  });
  await signIn(page, "workshop", "Arun", NIMBLE);
  await page.goto("/workshop");

  const facts = page.getByRole("region", { name: "Set by the factory" });
  await expect(facts).toContainText("MakesDRESSES, TOPS");
  await expect(page.getByLabel("Pieces per day")).toHaveValue("60");

  await page.getByLabel("Taking new work").uncheck();
  await page.getByLabel("Pieces per day").fill("45");
  await page.getByLabel("Days of work already booked").fill("2.5");
  await page.getByLabel("Pickup lead time (days)").fill("2");
  await page.getByLabel("Note to the dispatcher").fill("Two machines down");
  await page.getByRole("button", { name: "Save" }).click();

  await expect(reportForm(page).getByRole("status")).toContainText("It applies from the dispatcher's next run.");
  expect(sent).toEqual([
    { taking_new_work: false, capacity: 45, queue_days: 2.5, lead_days: 2, note: "Two machines down", reported_by: "Arun" },
  ]);
  // Any further edit makes the "Saved" line out of date.
  await page.getByLabel("Pieces per day").fill("50");
  await expect(reportForm(page).getByRole("status")).toHaveCount(0);
});

test("the browser blocks a value Python would refuse, and a failed save is explained", async ({ page }) => {
  let puts = 0;
  await page.route("**/api/backend/workshops/W6", (route) => {
    puts += 1;
    return route.fulfill({ status: 502, body: "Bad gateway" });
  });
  await signIn(page, "workshop", "Arun", NIMBLE);
  await page.goto("/workshop");

  const capacity = page.getByLabel("Pieces per day");
  await capacity.fill("0");
  await page.getByRole("button", { name: "Save" }).click();
  expect(await capacity.evaluate((input: HTMLInputElement) => input.validity.valid)).toBe(false);
  expect(puts).toBe(0);

  await capacity.fill("45");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(reportForm(page).getByRole("alert")).toHaveText(
    "Could not save: The backend answered HTTP 502. Check that the FastAPI server is running.",
  );
  expect(puts).toBe(1);
  await expect(capacity).toHaveValue("45");
  await expect(reportForm(page).getByRole("status")).toHaveCount(0);
});

test("a suspended workshop is told that automatic planning skips it", async ({ context, page }) => {
  await context.route("**/api/backend/workshops", (route) =>
    route.fulfill({ json: [makeWorkshop({ workshop_id: "W7", name: "Budget Bob", status: "SUSPENDED" })] }),
  );
  await signIn(page, "workshop", "Arun", { workshopId: "W7", workshopName: "Budget Bob" });
  await page.goto("/workshop");
  await expect(page.locator("p.notice")).toContainText(
    "The factory has set this workshop to SUSPENDED, so automatic planning skips it whatever you report.",
  );
});

test("a workshop stays on its own page, and the other roles cannot open it", async ({ context, page }) => {
  await signIn(page, "workshop", "Arun", NIMBLE);
  await page.goto("/dispatcher");
  await expect(page).toHaveURL(/\/workshop$/);
  await page.goto("/operations");
  await expect(page).toHaveURL(/\/workshop$/);

  const dispatcherTab = await context.newPage();
  await signIn(dispatcherTab, "dispatcher", "Mei");
  await dispatcherTab.goto("/workshop");
  await expect(dispatcherTab).toHaveURL(/\/dispatcher$/);

  const teamTab = await context.newPage();
  await signIn(teamTab, "team", "Priya");
  await teamTab.goto("/workshop");
  await expect(teamTab).toHaveURL(/\/operations$/);
});
