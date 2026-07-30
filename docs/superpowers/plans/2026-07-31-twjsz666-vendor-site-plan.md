# 台湾金手指（twjsz666）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `Zz_hdx.cp567.cc` 模板接入为 `twjsz666` 站点，保留供应商 DOM，并为台湾、澳门、香港三种彩票提供同源预测数据和完整浏览器契约。

**Architecture:** 使用现有 `iframe-vendor` 站点平台、site manifest、站点 TypeScript adapter 和 DOM-only `site-data-adapter.js`。后端使用统一 site API 与已有预测模块，所有动态输出写入模板既有文本/属性槽位并按彩票隔离。

**Tech Stack:** Next.js/TypeScript, legacy HTML/CSS/JavaScript, Node `pnpm` scripts, Python Playwright contracts, existing SQLite prediction migrations.

---

### Task 1: Scaffold and inventory the vendor page

**Files:**
- Create/Modify: `frontend/sites/twjsz666/site.manifest.ts`
- Create/Modify: `frontend/sites/twjsz666/site-adapter.ts`
- Create: `frontend/public/vendor/twjsz666/` (copied template)
- Test artifact: `frontend/test/twjsz666-template-inventory.mjs`

- [ ] **Step 1: Run the repository scaffold command**

Run `pnpm site:scaffold --site-key twjsz666`.

Expected: lower-case site directory and starter manifest/adapter are created without modifying unrelated dirty files.

- [ ] **Step 2: Copy the supplied template while preserving paths**

Copy all files from `frontend/public/vendor/Zz_hdx.cp567.cc/` to `frontend/public/vendor/twjsz666/`, keeping `index.html` as the manifest entry and retaining `kai.html`, `sx.html`, `wylhc.html`, CSS, JS and image paths.

- [ ] **Step 3: Inventory every visible prediction section and issue group**

Add a Node contract that parses `index.html`, records every visible prediction heading/container, counts complete issue groups, and fails on an unmapped visible section. Store the resulting selector/heading inventory in the adapter comments and test fixture rather than using sibling offsets.

- [ ] **Step 4: Run the inventory contract**

Run `node frontend/test/twjsz666-template-inventory.mjs`.

Expected: inventory lists all sections, maximum history group count is at most 20, and no external prediction/static sentinel is silently omitted.

### Task 2: Register the site manifest and backend authorization

**Files:**
- Modify: `frontend/sites/twjsz666/site.manifest.ts`
- Modify: `frontend/sites/index.ts` (or the repository's generated site registry)
- Modify: `backend/src/database/versioned_migrations.py`
- Modify: `backend/src/database/schema/prediction.py`
- Modify: `backend/src/domains/prediction/site_page_dependencies.py`
- Modify: `backend/src/vendor/homepage_modules.py` only if an existing homepage module registry requires the site key
- Test: `backend/src/tests/unit/test_twjsz666_site_profile.py`

- [ ] **Step 1: Write the failing site profile test**

Assert the manifest has `siteKey: "twjsz666"`, domains `www.twjsz666.com` and `twjsz666.com`, `/twjsz666`, a unique next `siteId/webId`, default lottery `3`, exactly three lottery definitions, and only same-origin security origins.

- [ ] **Step 2: Implement the manifest and generated registry entry**

Use `defineVendorSiteManifest` with `renderMode: "iframe-vendor"`, `/vendor/twjsz666/index.html`, `/vendor/twjsz666`, site name metadata, existing draw/prediction/navigation/footer selectors, enabled legacy scripts, and the existing backend module keys selected during inventory.

- [ ] **Step 3: Add versioned migration and dependency authorization**

Allocate the next available profile ID, authorize all selected existing module mode IDs for `twjsz666`, and register the target `web_id` for lottery types `1`, `2`, and `3`. Do not authorize modules that are not rendered by this site.

- [ ] **Step 4: Run the profile test and manifest synchronization**

Run `pytest -q backend/src/tests/unit/test_twjsz666_site_profile.py` and `pnpm site:sync-manifests`.

Expected: the test passes, generated registries include `twjsz666`, and existing site entries are unchanged.

### Task 3: Sanitize template origins and add shared data scripts

**Files:**
- Modify: `frontend/public/vendor/twjsz666/index.html`
- Modify: `frontend/public/vendor/twjsz666/kai.html`
- Modify: `frontend/public/vendor/twjsz666/sx.html`
- Modify: `frontend/public/vendor/twjsz666/wylhc.html`
- Modify: template JS files only where required to remove external execution or send lottery messages
- Create: `frontend/public/vendor/twjsz666/site-data-adapter.js`
- Test: `frontend/test/twjsz666-static-contract.mjs`

- [ ] **Step 1: Write static origin and sentinel assertions**

Assert no `http://`, `https://`, external `src`/`href`, `eval(atob(...))`, old site name/domain, old regional prefix, static `????`, or static historical result remains in active vendor scripts/HTML. Assert supplied navigation, draw iframe, footer and image nodes remain.

- [ ] **Step 2: Add the required script order**

Insert `/vendor/_shared/lottery-site-data-client.js` followed by `site-data-adapter.js` before supplied dynamic scripts, without changing the remaining script order.

- [ ] **Step 3: Sanitize only unsafe origins**

Remove external script execution and convert approved internal navigation to configured frontend routes. Keep external-looking supplier text only when it is a retained label, and replace visible site identity through `siteConfig`.

- [ ] **Step 4: Run the static contract and strict validation**

Run `node frontend/test/twjsz666-static-contract.mjs` and `pnpm site:validate --site-key twjsz666 --strict`.

Expected: no external-origin findings and no missing required template node.

### Task 4: Implement the TypeScript adapter contract

**Files:**
- Modify: `frontend/sites/twjsz666/site-adapter.ts`
- Test: `frontend/test/run-site-adapter-registry-contract.mjs`

- [ ] **Step 1: Write adapter registry assertions**

Assert `mode: "existing-dom-only"`, draw selector for the supplied tab box, all inventoried prediction selectors, original navigation behavior, footer selector/image contract if present, and no shared runtime mount.

- [ ] **Step 2: Implement the adapter metadata**

Declare the site key, draw/prediction/navigation/footer selectors and existing-script behavior. Keep this file declarative; renderers remain in the site-owned public adapter.

- [ ] **Step 3: Run the registry contract**

Run `node frontend/test/run-site-adapter-registry-contract.mjs`.

Expected: all existing sites and `twjsz666` pass.

### Task 5: Implement dedicated DOM slot renderers and lottery isolation

**Files:**
- Modify: `frontend/public/vendor/twjsz666/site-data-adapter.js`
- Test: `frontend/test/twjsz666-adapter-contract.mjs`

- [ ] **Step 1: Write failing renderer assertions**

Build fixture responses with at least eight distinct issues, duplicate records, structured `extra` fields, opened and future results, known hits, and distinct markers for lottery types `3`, `2`, and `1`. Assert exact section containers, issue headers, child slots, line breaks, hit backgrounds, no raw separators, and no supplier sentinel.

- [ ] **Step 2: Define immutable site configuration and request state**

Expose one `siteConfig` containing only the three required lotteries. Track `activeLottery`, `historyByLottery`, and `historyRequests` keyed by numeric `lotteryType`; use `loadDraw({ lotteryType })` and `loadPredictions({ lotteryType, historyLimit })`.

- [ ] **Step 3: Implement named formatters for every inventoried section**

For each section, locate the unique heading/container, retain labels and punctuation, write only pre-existing text leaves/attributes, cap values to visible capacity, parse structured values, clear unused rows, and render `暂无后端资料` per missing slot. Do not use a generic whole-row renderer as a section fallback.

- [ ] **Step 4: Implement draw iframe message handling**

Have the draw tab handler send `{ type: "lottery-change", siteKey, lotteryType }` to the parent. In the parent, verify both `event.origin` and `event.source` against the known draw iframe before calling `selectLottery`.

- [ ] **Step 5: Implement title/result/highlight isolation**

Derive `titlePrefix` and generic regional prefixes from `siteConfig`; clear old dynamic text and hit markers before each render; render only special-ball result and `开:待开奖` for future rows; ignore responses whose lottery type is not active.

- [ ] **Step 6: Run adapter contract tests**

Run `node frontend/test/twjsz666-adapter-contract.mjs`.

Expected: all mapped sections use their named renderer and all fixture assertions pass.

### Task 6: Add browser contract across all tabs and cached return

**Files:**
- Create: `frontend/test/twjsz666-live-mapping-contract.py`
- Modify: `package.json` only if a named test script is required

- [ ] **Step 1: Write the browser test with intercepted same-origin APIs**

Launch the local app, intercept `/api/sites/twjsz666/draw` and `/prediction-modules`, return distinct selected-lottery markers, click all three draw tabs, and assert every request uses the clicked `lottery_type`.

- [ ] **Step 2: Assert DOM topology rather than global text**

For each section, assert exact issue-group/row/cell counts, issue order, retained labels and line breaks, values in the documented child slots, selected marker and result label, hit background behavior, no blank secondary slot, and no raw transport delimiters or vendor sentinels.

- [ ] **Step 3: Assert cache and late-response behavior**

Return a delayed response for one lottery, switch tabs, and prove the delayed payload cannot overwrite the active table; switch back and assert the cached response renders without a duplicate request.

- [ ] **Step 4: Run the browser contract**

Run the repository's Python Playwright command with UTF-8 environment variables and the new `twjsz666` test.

Expected: all three tabs pass with selected data and no cross-lottery leakage.

### Task 7: Verify backend data and full repository gates

**Files:**
- Test/Modify: `backend/src/tests/unit/test_twjsz666_site_profile.py` and any focused data-row fixture tests
- No unrelated dirty files

- [ ] **Step 1: Verify target-site data rows**

Query the local test database through existing repository helpers by both `web_id` and `lottery_type`; assert each authorized module has target-site rows or an explicit unavailable state.

- [ ] **Step 2: Run focused backend and frontend tests**

Run the site profile tests, adapter/static/browser contracts, `pnpm site:test-ui-baseline`, `pnpm site:test-data-client`, and `pnpm site:test-adapter-registry`.

- [ ] **Step 3: Run typecheck, validation, and production build**

Run `pnpm exec tsc --noEmit`, `pnpm site:validate --site-key twjsz666 --strict`, and the repository production build command.

- [ ] **Step 4: Review the final diff**

Run `git diff --check`, `git status --short`, and inspect only files changed for `twjsz666`; confirm pre-existing dirty files remain untouched.

- [ ] **Step 5: Commit the onboarding change**

Commit only the new/modified `twjsz666` files and related generated registry/migration/test files with message `feat(vendor): onboard twjsz666 Taiwan Golden Finger site`.
