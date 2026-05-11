import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = [
  ...nextVitals,
  ...nextTs,
  {
    name: "global-ignores",
    ignores: [
      ".next/**",
      "out/**",
      "build/**",
      "coverage/**",
      "next-env.d.ts",
    ],
  },
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
];

export default eslintConfig;
