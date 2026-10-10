import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  use: {
    channel: "msedge",
    baseURL: "http://127.0.0.1:5173",
    viewport: { width: 1920, height: 1080 },
    screenshot: "only-on-failure",
  },
  reporter: [["list"], ["json", { outputFile: "docs/test-results.json" }]],
  timeout: 30000,
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: true,
  },
});
