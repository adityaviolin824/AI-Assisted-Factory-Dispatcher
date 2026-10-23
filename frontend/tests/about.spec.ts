import { expect, test } from "@playwright/test";

// The About page makes no backend request; any that did would be aborted, as in the other tests.
test.beforeEach(async ({ page }) => {
  await page.route("**/api/backend/**", (route) => route.abort());
});

test("View evaluation leads to the simulator's six measures, and the team is credited", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Dispatching at your fingertips");
  await expect(page.getByRole("list", { name: "Recorded results" }).getByRole("listitem")).toHaveCount(3);

  await page.getByRole("link", { name: "View evaluation" }).click();
  await expect(page).toHaveURL(/#how-we-measured$/);
  await expect(page.getByRole("heading", { name: "How we measured" })).toBeInViewport();
  await expect(page.locator(".measured th")).toHaveText([
    "Normal historical replay",
    "Mean days",
    "p90 days",
    "Late",
    "Defective",
    "Cost",
    "Maximum workshop share",
  ]);

  await expect(
    page.getByText("Brought to you by Cheng Shiqi, Song Zhuoyan, Zhang Chang, Zhang Hongyi and Aditya Bhattacharyya."),
  ).toBeVisible();
});
