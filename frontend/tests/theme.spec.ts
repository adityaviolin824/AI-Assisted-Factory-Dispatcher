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

  // Dark is the default: loden-black page (#0e1611).
  await page.goto("/");
  await expect(lightSwitch).toHaveAttribute("aria-checked", "false");
  await expect(body).toHaveCSS("background-color", "rgb(14, 22, 17)");

  // On: pale sage page (#f1f6f2), and the choice is remembered.
  await lightSwitch.click();
  await expect(lightSwitch).toHaveAttribute("aria-checked", "true");
  await expect(html).toHaveAttribute("data-theme", "light");
  await expect(body).toHaveCSS("background-color", "rgb(241, 246, 242)");

  // A reload starts in light mode: the script in layout.tsx applies it before React starts.
  await page.reload();
  await expect(lightSwitch).toHaveAttribute("aria-checked", "true");
  await expect(body).toHaveCSS("background-color", "rgb(241, 246, 242)");

  // Off again: back to dark.
  await lightSwitch.click();
  await expect(lightSwitch).toHaveAttribute("aria-checked", "false");
  await expect(body).toHaveCSS("background-color", "rgb(14, 22, 17)");
  expect(errors).toEqual([]);
});

test("the mist drifts behind the page, never takes clicks, and stands still under reduced motion", async ({ page }) => {
  // The mist is the body's ::before layer; read its computed style.
  const mist = () =>
    page.evaluate(() => {
      const style = getComputedStyle(document.body, "::before");
      return { animation: style.animationName, clicks: style.pointerEvents };
    });

  await page.goto("/");
  expect(await mist()).toEqual({ animation: "mist-drift", clicks: "none" });

  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(await mist()).toEqual({ animation: "none", clicks: "none" });
});
