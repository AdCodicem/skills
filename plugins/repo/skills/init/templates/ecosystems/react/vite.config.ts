/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // A GitHub Pages project site is served under /<repository>/: the deployment
  // workflow sets VITE_BASE_PATH. Everything else serves the app at the root.
  base: process.env.VITE_BASE_PATH ?? "/",
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.test.{ts,tsx}", "src/test/**", "src/main.tsx"],
      // lcov for Codecov, json-summary for the CI job summary.
      reporter: ["text", "lcov", "json-summary"],
      reportsDirectory: "coverage",
    },
  },
});
