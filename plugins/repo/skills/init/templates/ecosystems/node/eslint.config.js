// @ts-check
// ESLint 10 reads flat config only. Type-aware rules load the TypeScript 6 API
// (`typescript` is aliased to @typescript/typescript6, see references/ecosystems/node.md).
import js from "@eslint/js";
import { defineConfig, globalIgnores } from "eslint/config";
import prettier from "eslint-config-prettier/flat";
import globals from "globals";
import tseslint from "typescript-eslint";

export default defineConfig(
  globalIgnores(["lib/", "coverage/", ".vitest/", "docs/website/", "dist/"]),
  js.configs.recommended,
  tseslint.configs.strictTypeChecked,
  tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      globals: globals.node,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    files: ["**/*.js", "**/*.mjs"],
    extends: [tseslint.configs.disableTypeChecked],
  },
  // Last: turns off every rule that would fight Prettier.
  prettier,
);
