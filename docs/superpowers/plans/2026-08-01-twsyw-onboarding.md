# 台湾神预网 Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `twsyw` (WEB_ID 13) as an isolated iframe-vendor site based on the supplied `Zz_xgg3.cp567.cc` bundle, with same-origin draw and prediction rendering for lottery types 3, 2, and 1.

**Architecture:** Preserve the vendor bundle's DOM and visual structure in `public/vendor/twsyw`; use the mature existing-DOM adapter structure only to write predeclared leaf slots. Register a separate manifest, frontend registry entry, backend blueprint profile, and page dependency list so site 13 has its own authorized API mapping without sharing site 12 identity.

**Tech Stack:** Next.js/TypeScript manifests, legacy HTML/JavaScript, Python backend migrations and pytest, Node static contracts, Playwright browser contract.

---

### Task 1: Lock Registration and Profile Behavior with Failing Tests

**Files:**
- Create: `frontend/test/twsyw-site-registration-contract.mjs`
- Create: `backend/src/tests/unit/test_twsyw_site_profile.py`

- [ ] **Step 1: Write tests that require the `twsyw` frontend manifest registration and a backend site-13 profile.**
- [ ] **Step 2: Run the Node and pytest contracts; expect failures because `twsyw` does not exist.**
- [ ] **Step 3: Register the independent manifest, adapter and site profile.**
- [ ] **Step 4: Re-run the contracts; expect pass.**

### Task 2: Materialize the Vendor Bundle and Existing-DOM Integration

**Files:**
- Create: `frontend/public/vendor/twsyw/**`
- Create: `frontend/sites/twsyw/site.manifest.ts`
- Create: `frontend/sites/twsyw/site-adapter.ts`
- Modify: `frontend/lib/sites.ts`
- Modify: `frontend/lib/site-platform/site-adapter-registry.ts`
- Modify: `frontend/sites/site-manifests.generated.ts`

- [ ] **Step 1: Copy the supplied template assets to the new site directory and apply only the already-reviewed legacy syntax/resource repairs required for local operation.**
- [ ] **Step 2: Add immutable `TwsywSiteConfig`, local draw iframe tabs, same-origin data client scripts, and an existing-DOM adapter without DOM construction APIs.**
- [ ] **Step 3: Add `data-prediction-section` and leaf slots to every mapped historical row; preserve static labels, table/card topology and approved terminal attribute gallery.**
- [ ] **Step 4: Generate manifests and verify `twsyw` resolves through the frontend registry.**

### Task 3: Authorize Only the Reviewed Prediction Data

**Files:**
- Modify: `backend/src/domains/prediction/site_page_dependencies.py`
- Modify: `backend/src/domains/prediction/site_module_blueprints.py`
- Modify: `backend/src/database/versioned_migrations.py`

- [ ] **Step 1: Reuse the reviewed mode IDs as independent `twsyw` page dependencies.**
- [ ] **Step 2: Add exact domain/WEB_ID 13 blueprint matching and migration seeding for managed site 13.**
- [ ] **Step 3: Verify profile lookup never shadows sites 11 or 12 and mode authorization comes from the new dependency inventory.**

### Task 4: Document and Enforce the DOM Contract

**Files:**
- Create: `docs/vendor-sites/twsyw-frontend-prediction-modules.md`
- Create: `frontend/test/twsyw-adapter-contract.mjs`
- Create: `frontend/test/twsyw-legacy-script-contract.mjs`
- Modify: `frontend/test/managed-site-links-mount-contract.mjs`
- Modify: `frontend/test/run-site-adapter-registry-contract.mjs`
- Modify: `frontend/test/site-adapter-registry-contract.ts`

- [ ] **Step 1: Document every visible prediction section, direct source HTML leaf pattern, module key, formatter, capacity, result and unavailable rules.**
- [ ] **Step 2: Create static contracts enumerating all `writeRow` sections and requiring exact issue/content/result slots per history group.**
- [ ] **Step 3: Check legacy scripts for local-image, calendar, SRI/beacon, and local draw-iframe regressions.**

### Task 5: Verify Cross-Frame Data Rendering

**Files:**
- Create: `frontend/test/twsyw-live-mapping-contract.py`

- [ ] **Step 1: Stub same-origin draw and prediction APIs with unique per-lottery rows.**
- [ ] **Step 2: Click types 3, 2 and 1 and return through cached state.**
- [ ] **Step 3: Assert selected type reaches both APIs, current issue updates, content/result slots render, hits reset, vendor sentinels disappear, and the approved centered sections retain computed center alignment.**

### Task 6: Final Validation

**Files:**
- Verify all files above.

- [ ] **Step 1: Run Node static contracts, focused pytest profile and browser contracts.**
- [ ] **Step 2: Run `pnpm site:validate --site-key twsyw`, TypeScript no-emit, and `git diff --check`.**
- [ ] **Step 3: Report precise modified paths, test evidence, and any remaining non-executable vendor origins reported by validation.**
