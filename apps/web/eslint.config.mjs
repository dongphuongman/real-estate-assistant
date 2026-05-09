import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "coverage/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
    // Disable the pages directory check for monorepo setup
    "@next/next/no-html-link-for-pages": "off",
    // Allow unused vars with _ prefix (intentionally unused parameters)
    "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
    // Allow <img> for dynamic external URLs where Next.js Image optimization isn't applicable
    "@next/next/no-img-element": "off",
  },
  },
]);

export default eslintConfig;
