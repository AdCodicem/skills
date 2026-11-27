// Loaded before every test file (vite.config.ts, test.setupFiles).
import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Testing Library unmounts after each test only when test globals are on; they are not.
afterEach(() => {
  cleanup();
});
