# Vendor Site Bridge Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a configuration-driven legacy vendor bridge and validate it against `twsaimahui` without changing its UI.

**Architecture:** A manifest defines site identity, legacy runtime options and public bridge settings. Shared server routes expose that configuration and normalized draw data, while a browser bridge injects it into the existing vendor runtime and emits optional data events. Existing compatibility APIs remain the rendering/data path for the pilot.

**Tech Stack:** Next.js 16 route handlers, TypeScript, React 19, plain browser JavaScript, Node.js scripts, existing frontend contract-test pattern.

---

### Task 1: Add the typed manifest foundation

**Files:**
- Create: `frontend/lib/site-platform/site-manifest.ts`
- Create: `frontend/sites/twsaimahui/site.manifest.ts`
- Create: `frontend/sites/site-manifests.generated.ts`
- Create: `frontend/lib/site-platform/site-manifests.ts`
- Test: `frontend/test/run-site-platform-contract.mjs`

- [ ] **Step 1: Write failing manifest assertions**

Create a test that imports `defineVendorSiteManifest`, verifies a valid twsaimahui manifest, and asserts duplicate module keys and invalid site keys throw explicit validation errors.

- [ ] **Step 2: Run the focused test and verify it fails because the manifest module is absent**

Run: `node frontend/test/run-site-platform-contract.mjs`

Expected: failure mentioning missing `frontend/lib/site-platform/site-manifest.ts`.

- [ ] **Step 3: Implement minimal manifest validation and the twsaimahui manifest**

Implement a pure TypeScript validator with the manifest fields from the approved specification. Add the manifest with `siteId/webId=6`, default type `3`, vendor entry `/vendor/twsaimahui/index.html`, legacy API bases `""` and `/api/kaijiang`, and disabled bridge auto-load. Generate an index that exports the manifest map.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `node frontend/test/run-site-platform-contract.mjs`

Expected: exit code `0`.

### Task 2: Derive the twsaimahui registry configuration from its manifest

**Files:**
- Modify: `frontend/lib/sites.ts`
- Modify: `frontend/test/site-registry-contract.ts`
- Modify: `frontend/test/run-site-registry-contract.mjs`

- [ ] **Step 1: Extend the failing registry assertion**

Assert that `getSiteConfig("twsaimahui")` matches the manifest identity and vendor entry while preserving its current public route and web ID.

- [ ] **Step 2: Run the registry test and verify it fails before registry derivation exists**

Run: `node frontend/test/run-site-registry-contract.mjs`

Expected: failure because the manifest-derived identity cannot yet be resolved.

- [ ] **Step 3: Implement a narrow registry adapter**

Add `toFrontendSiteConfig(manifest)` and replace only the twsaimahui literal configuration with its manifest-derived config. Do not alter the other four site configurations.

- [ ] **Step 4: Re-run registry and platform tests**

Run: `node frontend/test/run-site-platform-contract.mjs; node frontend/test/run-site-registry-contract.mjs`

Expected: both commands exit `0`.

### Task 3: Add bridge configuration and normalized draw route handlers

**Files:**
- Create: `frontend/lib/site-platform/site-draw.ts`
- Create: `frontend/app/api/sites/[siteKey]/bridge-config/route.ts`
- Create: `frontend/app/api/sites/[siteKey]/draw/route.ts`
- Test: `frontend/test/run-site-platform-contract.mjs`

- [ ] **Step 1: Add failing assertions for bridge projection and draw mapping**

Assert that the public bridge projection excludes server-only values, that a configured site produces `/api/kaijiang`, and that a latest draw plus special ball maps to seven normalized two-digit balls with `is_special` on the final item.

- [ ] **Step 2: Run the test and verify it fails because route helpers do not exist**

Run: `node frontend/test/run-site-platform-contract.mjs`

Expected: failure naming the missing bridge projection or draw mapping export.

- [ ] **Step 3: Implement helpers and routes**

Use `resolveSiteApiContext` for path-owned identity. Fetch `/public/latest-draw` and `/public/next-draw-deadline` through `backendFetchJson`, normalize values and emit the common error envelope for errors. The config route exposes only public manifest configuration.

- [ ] **Step 4: Run focused tests**

Run: `node frontend/test/run-site-platform-contract.mjs; pnpm --filter @liuhecai/frontend exec tsc --noEmit`

Expected: both commands exit `0`.

### Task 4: Add the browser bridge and twsaimahui runtime adoption

**Files:**
- Create: `frontend/public/vendor/twsaimahui/site-bridge.js`
- Modify: `frontend/public/vendor/twsaimahui/index.html`
- Modify: `frontend/public/vendor/twsaimahui/static/js/legacy_runtime.js`
- Modify: `frontend/public/vendor/twsaimahui/static/js/lottery_config.js`
- Test: `frontend/test/run-site-bridge-contract.mjs`

- [ ] **Step 1: Create a failing browser-bridge harness**

Use a minimal fake `window`, `CustomEvent`, `fetch`, and event collector. Assert bridge configuration applies a configured web ID to the legacy runtime, a prediction request emits `lottery:prediction-ready`, and a failed draw request emits a retryable `lottery:error`.

- [ ] **Step 2: Run the harness and verify it fails because `site-bridge.js` is absent**

Run: `node frontend/test/run-site-bridge-contract.mjs`

Expected: failure opening `frontend/public/vendor/twsaimahui/site-bridge.js`.

- [ ] **Step 3: Implement the browser bridge**

Load `/api/sites/<siteKey>/bridge-config`, keep a state object, provide `getPredictionModules()` and `getDraw()`, dispatch the approved event names, and retain a safe fallback when configuration fails. Do not modify vendor DOM or vendor module rendering.

- [ ] **Step 4: Wire it before the legacy runtime and make runtime configuration mutable**

Add `data-site-key="twsaimahui"` to the bridge script tag. Add `applyBridgeConfig` to `legacy_runtime.js`; update `lottery_config.js` on the bridge-ready event. Preserve existing defaults and legacy endpoint behavior.

- [ ] **Step 5: Run the browser bridge test and type check**

Run: `node frontend/test/run-site-bridge-contract.mjs; pnpm --filter @liuhecai/frontend exec tsc --noEmit`

Expected: both commands exit `0`.

### Task 5: Add generic vendor page support

**Files:**
- Create: `frontend/components/site-platform/VendorSitePage.tsx`
- Create: `frontend/app/[siteKey]/page.tsx`
- Modify: `frontend/app/twsaimahui/page.tsx`
- Test: `frontend/test/site-rendering-contract.tsx`

- [ ] **Step 1: Extend the rendering contract with a failing manifest-backed page assertion**

Assert that a manifest-backed iframe renderer resolves the configured vendor index, title and site key rather than a hard-coded twsaimahui string.

- [ ] **Step 2: Run the TypeScript contract and verify it fails before the component exists**

Run: `pnpm --filter @liuhecai/frontend exec tsc --noEmit`

Expected: TypeScript error for missing `VendorSitePage`.

- [ ] **Step 3: Implement the shared iframe page component and dynamic route**

Use the existing traffic tracker and manifest entry. The dynamic route returns `notFound()` for unknown/non-manifest sites. Make the twsaimahui page delegate to the shared component so its iframe UI remains unchanged.

- [ ] **Step 4: Re-run TypeScript and focused contracts**

Run: `pnpm --filter @liuhecai/frontend exec tsc --noEmit; node frontend/test/run-site-platform-contract.mjs; node frontend/test/run-site-bridge-contract.mjs`

Expected: all commands exit `0`.

### Task 6: Add onboarding automation and repository skill

**Files:**
- Create: `scripts/sync-site-manifests.mjs`
- Create: `scripts/scaffold-vendor-site.mjs`
- Create: `scripts/validate-vendor-site.mjs`
- Modify: `package.json`
- Create: `skills/vendor-site-onboarding/SKILL.md`
- Create: `skills/vendor-site-onboarding/references/manifest-contract.md`
- Test: `frontend/test/run-site-platform-contract.mjs`

- [ ] **Step 1: Add failing script-level test cases**

Have the platform test invoke the validator for twsaimahui and assert success, then pass a malformed temporary manifest and assert non-zero exit with a validation message.

- [ ] **Step 2: Run it and verify it fails because the validation command is absent**

Run: `node frontend/test/run-site-platform-contract.mjs`

Expected: failure naming `scripts/validate-vendor-site.mjs`.

- [ ] **Step 3: Implement commands and Skill**

`site:sync-manifests` regenerates the manifest index; `site:scaffold` creates the manifest template and destination directory; `site:validate` checks identity, local entry paths and reports remote origins. The repository Skill tells future agents to run these commands, preserve vendor UI and demand explicit module mappings.

- [ ] **Step 4: Validate the Skill and commands**

Run: `python C:/Users/Administrator/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/vendor-site-onboarding; pnpm site:sync-manifests; pnpm site:validate --site-key twsaimahui`

Expected: each exits `0`.

### Task 7: Full verification and documentation

**Files:**
- Modify: `frontend/README.md`
- Modify: `frontend/docs/frontend-api-contract.md`
- Test: existing frontend contracts

- [ ] **Step 1: Document only the implemented onboarding workflow**

Document manifest location, bridge event/API contracts, the twsaimahui pilot status, commands and the explicit adapter requirement for unknown module payloads.

- [ ] **Step 2: Run full focused verification**

Run: `pnpm --filter @liuhecai/frontend exec tsc --noEmit; node frontend/test/run-site-registry-contract.mjs; node frontend/test/run-prediction-modules-route-contract.mjs; node frontend/test/run-site-platform-contract.mjs; node frontend/test/run-site-bridge-contract.mjs; pnpm site:validate --site-key twsaimahui`

Expected: all commands exit `0`.

- [ ] **Step 3: Run production build verification**

Run: `pnpm build:frontend`

Expected: Next.js build completes successfully.
