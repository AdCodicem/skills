import { defineConfig, devices } from "@playwright/test";

// End-to-end tests (complete tier) run against the production build, served by
// `vite preview`, so they test what is deployed.
const port = 4173;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://localhost:${String(port)}`,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `pnpm run build && pnpm exec vite preview --port ${String(port)} --strictPort`,
    port,
    reuseExistingServer: !process.env.CI,
  },
});
