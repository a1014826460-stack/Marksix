import { defineConfig, globalIgnores } from "eslint/config"
import nextVitals from "eslint-config-next/core-web-vitals"
import nextTs from "eslint-config-next/typescript"

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["frontend/**/*.{js,jsx,mjs,cjs,ts,tsx}"],
    settings: {
      next: {
        rootDir: "frontend/",
      },
    },
    rules: {
      "@next/next/no-css-tags": "off",
      "@next/next/no-html-link-for-pages": "off",
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/refs": "off",
      "react-hooks/purity": "off",
    },
  },
  {
    files: ["backend/**/*.{js,jsx,mjs,cjs,ts,tsx}"],
    settings: {
      next: {
        rootDir: "backend/",
      },
    },
    rules: {
      "@next/next/no-css-tags": "off",
      "@next/next/no-html-link-for-pages": "off",
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/refs": "off",
      "react-hooks/purity": "off",
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
  {
    files: ["frontend/test/**/*.js"],
    rules: {
      "@typescript-eslint/no-require-imports": "off",
    },
  },
  {
    files: [
      "frontend/**/*.{js,jsx,mjs,cjs,ts,tsx}",
      "backend/**/*.{js,jsx,mjs,cjs,ts,tsx}",
    ],
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
      "react-hooks/exhaustive-deps": "warn",
      "@next/next/no-img-element": "warn",
      "@next/next/no-html-link-for-pages": "off",
      "@next/next/no-css-tags": "off",
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
  {
    files: ["frontend/app/history/page.tsx"],
    rules: {
      "@next/next/no-html-link-for-pages": "off",
    },
  },
  {
    files: ["frontend/app/layout.tsx", "frontend/app/history/page.tsx"],
    rules: {
      "@next/next/no-css-tags": "off",
    },
  },
  {
    files: ["frontend/app/legacy-shell/page.tsx"],
    rules: {
      "@next/next/no-img-element": "off",
      "react-hooks/set-state-in-effect": "off",
    },
  },
  {
    files: ["frontend/components/LegacyModulesFrame.tsx"],
    rules: {
      "react-hooks/set-state-in-effect": "off",
    },
  },
  {
    files: ["backend/components/**/*.tsx", "backend/features/**/*.tsx", "backend/hooks/**/*.ts"],
    rules: {
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/refs": "off",
      "react-hooks/purity": "off",
    },
  },
  {
    files: ["backend/features/shared/types.ts"],
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
  {
    files: ["frontend/test/**/*.js"],
    languageOptions: {
      sourceType: "commonjs",
    },
  },
  {
    files: ["frontend/app/api/**/*.ts", "backend/app/api/**/*.ts"],
    rules: {
      "@next/next/no-html-link-for-pages": "off",
      "@next/next/no-img-element": "off",
      "@next/next/no-css-tags": "off",
    },
  },
  {
    files: ["frontend/app/**/*.{ts,tsx}", "backend/app/**/*.{ts,tsx}"],
    settings: {
      react: {
        version: "detect",
      },
    },
  },
  globalIgnores([
    ".next/**",
    "frontend/.next/**",
    "backend/.next/**",
    "frontend/public/**",
    "backend/public/**",
    "sites/**",
    "twsaimahui/**",
    "frontend/public/**/*.js",
    "frontend/public/**/*.min.js",
    "backend/public/**/*.js",
    "backend/public/**/*.min.js",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "frontend/_archived_unused_frontend/**",
    "backend/node_modules/**",
    "frontend/node_modules/**",
    "node_modules/**",
  ]),
])
