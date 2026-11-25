import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["src/**/*.test.ts", "test/**/*.test.ts"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.ts"],
      exclude: ["src/**/*.test.ts"],
      // lcov for Codecov, json-summary for the CI job summary.
      reporter: ["text", "lcov", "json-summary"],
      // Explicit, so CI uploads from a known path whatever Vitest's default output folder.
      reportsDirectory: "coverage",
    },
  },
});
