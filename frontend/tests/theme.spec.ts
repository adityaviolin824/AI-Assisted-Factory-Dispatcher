import { expect, test } from "@playwright/test";

// The About page makes no backend request; any that did would be aborted, as in the other tests.
test.beforeEach(async ({ page }) => {
  await page.route("**/api/backend/**", (route) => route.abort());
});

test("the light mode switch changes the colours, and a reload keeps the choice without errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(message.text());
    }
  });
  const html = page.locator("html");
  const body = page.locator("body");
  const lightSwitch = page.getByRole("switch", { name: "Light mode" });

  // Dark is the default: raw indigo page.
  await page.goto("/");
  await expect(lightSwitch).toHaveAttribute("aria-checked", "false");
  await expect(body).toHaveCSS("background-color", "rgb(18, 26, 48)");

  // On: ecru page, and the choice is remembered.
  await lightSwitch.click();
  await expect(lightSwitch).toHaveAttribute("aria-checked", "true");
  await expect(html).toHaveAttribute("data-theme", "light");
  await expect(body).toHaveCSS("background-color", "rgb(244, 239, 226)");

  // A reload starts in light mode: the script in layout.tsx applies it before React starts.
  await page.reload();
  await expect(lightSwitch).toHaveAttribute("aria-checked", "true");
  await expect(body).toHaveCSS("background-color", "rgb(244, 239, 226)");

  // Off again: back to dark.
  await lightSwitch.click();
  await expect(lightSwitch).toHaveAttribute("aria-checked", "false");
  await expect(body).toHaveCSS("background-color", "rgb(18, 26, 48)");
  expect(errors).toEqual([]);
});
