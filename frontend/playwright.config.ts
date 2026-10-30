import { defineConfig } from "@playwright/test";

// Playwright 1.64 expects Chromium revision 1248. This reuses revision 1234, already installed,
// instead of downloading another browser. CHROMIUM_PATH can point at a different binary.
const chromiumPath =
  process.env.CHROMIUM_PATH ??
  `${process.env.HOME}/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell`;

export default defineConfig({
  testDir: "./tests",
  use: {
    baseURL: "http://127.0.0.1:3000",
    // The fake microphone lets the Record button record in tests, with no permission prompt.
    launchOptions: {
      executablePath: chromiumPath,
      args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
    },
  },
  // The tests answer every /api/backend request themselves, so only Next.js has to run.
  webServer: {
    command: "npm run dev -- --port 3000",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: true,
  },
});
