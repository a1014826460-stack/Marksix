# UI-Preserving Site Data Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make draw, prediction, navigation behavior, and footer configuration maintainable across all five sites while preserving every existing site's HTML, CSS, DOM layout, assets, and visual output.

**Architecture:** The shared layer is data-only: canonical API access, request de-duplication, bounded cache and normalized loading/error state. Each current site retains its own renderer and receives data through an adapter which is permitted to update only approved existing DOM nodes. It may not create, replace, remove or style layout nodes.

**Tech Stack:** Next.js 16 route handlers, TypeScript, existing backend public APIs, legacy JavaScript, React 19, Node contract checks and Playwright.

---

## Guardrails

- Preserve the staged `.playwright-mcp/page-2026-07-21T15-58-04-300Z.yml`; do not amend, unstage or include it in feature commits.
- Do not change existing vendor HTML structure, CSS, logo, images, navigation labels, footer content, prediction script order or theme without explicit site-specific approval.
- Shared browser code must not call `document.createElement`, `appendChild`, `replaceChildren`, `innerHTML`, `document.write`, or inject CSS.
- Site adapters may only use selectors listed in their baseline. Missing nodes result in a scoped warning and no DOM mutation.
- Existing route and vendor entry mappings remain unchanged; for example `/twsaimahui` continues to use `/vendor/twsaimahui/index.html`.

## Current Baseline

| Site | Route | Current renderer | Draw sentinel | Navigation sentinel |
|---|---|---|---|---|
| shengshi8800 | `/` | legacy shell/vendor embed | existing `KJ-TabBox` | current shell navigation |
| twsaimahui | `/twsaimahui` | iframe vendor | `.KJ-TabBox` plus `kj/local.html` | `#nav2` |
| twcaibawang | `/twcaibawang` | React home | current React draw component | current React nav |
| twjinniu | `/twjinniu` | React home | current React draw component | current React nav |
| twcf888 | `/twcf888` | React home | current React draw component | current React nav |

## Task 1: Freeze UI Baselines

**Files:**
- Create: `frontend/lib/site-platform/site-ui-baseline.ts`
- Create: `frontend/test/site-ui-baseline-contract.ts`
- Create: `frontend/test/run-site-ui-baseline-contract.mjs`
- Modify: `package.json`

- [ ] **Step 1: Write the failing static contract**

```ts
import { SITE_UI_BASELINES } from "@/lib/site-platform/site-ui-baseline"

for (const siteKey of ["shengshi8800", "twsaimahui", "twcaibawang", "twjinniu", "twcf888"]) {
  const baseline = SITE_UI_BASELINES[siteKey]
  if (!baseline?.routePath || !baseline.vendorEntry) throw new Error(`missing route baseline: ${siteKey}`)
  if (!baseline.drawSentinel || !baseline.navigationSentinel || !baseline.footerSentinel) {
    throw new Error(`missing visual sentinels: ${siteKey}`)
  }
}
```

- [ ] **Step 2: Verify the test is red**

Run: `node frontend/test/run-site-ui-baseline-contract.mjs`

Expected: failure because the baseline registry does not exist.

- [ ] **Step 3: Implement immutable current-site baseline registry**

```ts
export type SiteUiBaseline = {
  routePath: string
  vendorEntry: string
  drawSentinel: string
  navigationSentinel: string
  footerSentinel: string
}

export const SITE_UI_BASELINES: Readonly<Record<string, SiteUiBaseline>> = Object.freeze({
  twsaimahui: {
    routePath: "/twsaimahui",
    vendorEntry: "/vendor/twsaimahui/index.html",
    drawSentinel: ".KJ-TabBox",
    navigationSentinel: "#nav2",
    footerSentinel: "static/picture/log1.jpg",
  },
  // Add the remaining four values from their committed current source.
})
```

The final registry must include all five sites and only existing selectors/content.

- [ ] **Step 4: Add executable contract and command**

Use the existing TypeScript `transpileModule` data URL convention from `frontend/test/run-site-platform-contract.mjs`. Add:

```json
"site:test-ui-baseline": "node frontend/test/run-site-ui-baseline-contract.mjs"
```

- [ ] **Step 5: Verify green and commit**

Run: `pnpm site:test-ui-baseline`

Expected: exit code 0.

```powershell
git add package.json frontend/lib/site-platform/site-ui-baseline.ts frontend/test/site-ui-baseline-contract.ts frontend/test/run-site-ui-baseline-contract.mjs
git commit -m "test: freeze five-site UI baseline"
```

## Task 2: Implement a DOM-Free Shared Data Client

**Files:**
- Create: `frontend/public/vendor/_shared/lottery-site-data-client.js`
- Create: `frontend/test/site-data-client-contract.mjs`
- Modify: `package.json`

- [ ] **Step 1: Write a failing data-client contract**

```js
const first = client.loadDraw({ lotteryType: 3 })
const second = client.loadDraw({ lotteryType: 3 })
await Promise.all([first, second])
if (fetchCalls !== 1) throw new Error("same draw request must be de-duplicated")

clock.advance(6000)
fetchMode = "offline"
const stale = await client.loadDraw({ lotteryType: 3 })
if (stale.state !== "stale" || stale.data.current_issue !== "2026170") {
  throw new Error("expired cached draw must provide bounded stale fallback")
}
```

Also assert an uncached offline prediction response is `{ state: "error", error: { retryable: true } }`.

- [ ] **Step 2: Verify red**

Run: `node frontend/test/site-data-client-contract.mjs`

Expected: failure because `LotterySiteDataClient` is absent.

- [ ] **Step 3: Implement the UMD data-only client**

```js
window.LotterySiteDataClient = {
  create: function create(options) {
    return {
      loadDraw: function loadDraw(query) {},
      loadPredictions: function loadPredictions(query) {},
      clear: function clear(resource) {},
    };
  },
};
```

Rules:
- Draw request: `/api/sites/<siteKey>/draw?lottery_type=<id>`.
- Prediction request: `/api/sites/<siteKey>/prediction-modules?lottery_type=<id>&history_limit=<n>`.
- Draw fresh TTL 5 seconds; stale fallback max age 60 seconds.
- Prediction fresh TTL 60 seconds; stale fallback max age 15 minutes.
- De-duplicate in-flight keys using `siteKey + resource + normalized query`.
- Persist `{ cachedAt, data }` to session storage under `liuhecai:site-data:v1:*`.
- Return only `{ state: "ready" | "stale" | "error", data?, error?, source }`; no DOM references.

- [ ] **Step 4: Verify green and commit**

Run:

```powershell
node --check frontend/public/vendor/_shared/lottery-site-data-client.js
node frontend/test/site-data-client-contract.mjs
```

Expected: both commands exit 0.

```powershell
git add package.json frontend/public/vendor/_shared/lottery-site-data-client.js frontend/test/site-data-client-contract.mjs
git commit -m "feat: add DOM-free shared site data client"
```

## Task 3: Add Canonical Route Cache Headers Without Changing Bodies

**Files:**
- Create: `frontend/lib/site-platform/site-data-cache.ts`
- Modify: `frontend/app/api/sites/[siteKey]/draw/route.ts`
- Modify: `frontend/app/api/sites/[siteKey]/prediction-modules/route.ts`
- Create: `frontend/test/site-data-cache-contract.ts`
- Create: `frontend/test/run-site-data-cache-contract.mjs`

- [ ] **Step 1: Write a failing cache header test**

```ts
import { siteDataCacheHeaders } from "@/lib/site-platform/site-data-cache"

if (siteDataCacheHeaders("draw")["Cache-Control"] !== "private, max-age=5, stale-while-revalidate=55") {
  throw new Error("draw cache policy changed")
}
if (siteDataCacheHeaders("predictions")["Cache-Control"] !== "private, max-age=60, stale-while-revalidate=840") {
  throw new Error("prediction cache policy changed")
}
```

- [ ] **Step 2: Verify red**

Run: `node frontend/test/run-site-data-cache-contract.mjs`

Expected: failure because the helper does not exist.

- [ ] **Step 3: Implement helper and apply it to existing JSON responses**

```ts
export type SiteDataResource = "draw" | "predictions"

export function siteDataCacheHeaders(resource: SiteDataResource) {
  return resource === "draw"
    ? { "Cache-Control": "private, max-age=5, stale-while-revalidate=55" }
    : { "Cache-Control": "private, max-age=60, stale-while-revalidate=840" }
}
```

Pass headers to `jsonWithCors` while retaining the current response envelope. If that helper lacks header support, extend it and assert CORS headers remain intact.

- [ ] **Step 4: Verify real endpoint and commit**

Run:

```powershell
node frontend/test/run-site-data-cache-contract.mjs
(Invoke-WebRequest http://127.0.0.1:3000/api/sites/twsaimahui/draw -UseBasicParsing).Headers["Cache-Control"]
```

Expected: `private, max-age=5, stale-while-revalidate=55` and unchanged JSON structure.

```powershell
git add frontend/lib/site-platform/site-data-cache.ts frontend/app/api/sites/[siteKey]/draw/route.ts frontend/app/api/sites/[siteKey]/prediction-modules/route.ts frontend/test/site-data-cache-contract.ts frontend/test/run-site-data-cache-contract.mjs
git commit -m "feat: cache canonical site data responses"
```

## Task 4: Add a `twsaimahui` Preload-Only Pilot

**Files:**
- Create: `frontend/public/vendor/twsaimahui/site-data-adapter.js`
- Modify: `frontend/public/vendor/twsaimahui/index.html`
- Create: `frontend/test/twsaimahui-adapter-contract.mjs`

- [ ] **Step 1: Write a failing no-UI-mutation contract**

```js
const adapter = fs.readFileSync("frontend/public/vendor/twsaimahui/site-data-adapter.js", "utf8")
for (const token of ["createElement", "appendChild", "replaceChildren", "innerHTML", "document.write", "<style"]) {
  if (adapter.includes(token)) throw new Error(`adapter must not mutate UI: ${token}`)
}
if (!adapter.includes("LotterySiteDataClient")) throw new Error("adapter must use shared client")
```

- [ ] **Step 2: Verify red**

Run: `node frontend/test/twsaimahui-adapter-contract.mjs`

Expected: failure because the adapter does not exist.

- [ ] **Step 3: Implement preload-only adapter**

```js
(function (window) {
  "use strict";
  var client = window.LotterySiteDataClient.create({ siteKey: "twsaimahui" });
  window.TwsaimahuiSiteData = {
    preloadDraw: function () { return client.loadDraw({ lotteryType: 3 }); },
    preloadPredictions: function () { return client.loadPredictions({ lotteryType: 3, historyLimit: 8 }); },
  };
})(window);
```

- [ ] **Step 4: Add scripts without touching current renderer**

Add exactly these two script tags after existing `site-bridge.js` and before legacy scripts:

```html
<script src="/vendor/_shared/lottery-site-data-client.js"></script>
<script src="site-data-adapter.js"></script>
```

Do not alter `.KJ-TabBox`, `kj/local.html`, legacy prediction script tags, `#nav2`, or footer image markup.

- [ ] **Step 5: Verify browser output and commit**

Run source checks:

```powershell
node --check frontend/public/vendor/_shared/lottery-site-data-client.js
node --check frontend/public/vendor/twsaimahui/site-data-adapter.js
node frontend/test/twsaimahui-adapter-contract.mjs
```

Use Playwright to assert that the child frame still has a current issue and seven ball values, and that `#nav2` and `static/picture/log1.jpg` remain in the vendor page.

```powershell
git add frontend/public/vendor/twsaimahui/index.html frontend/public/vendor/twsaimahui/site-data-adapter.js frontend/test/twsaimahui-adapter-contract.mjs
git commit -m "feat: preload twsaimahui data without changing UI"
```

## Task 5: Register Existing-DOM-Only Adapters for All Five Sites

**Files:**
- Create: `frontend/sites/shengshi8800/site-adapter.ts`
- Create: `frontend/sites/twsaimahui/site-adapter.ts`
- Create: `frontend/sites/twcaibawang/site-adapter.ts`
- Create: `frontend/sites/twjinniu/site-adapter.ts`
- Create: `frontend/sites/twcf888/site-adapter.ts`
- Create: `frontend/lib/site-platform/site-adapter-registry.ts`
- Create: `frontend/test/site-adapter-registry-contract.ts`
- Create: `frontend/test/run-site-adapter-registry-contract.mjs`

- [ ] **Step 1: Write a failing registry test**

```ts
import { getSiteAdapter } from "@/lib/site-platform/site-adapter-registry"

for (const siteKey of ["shengshi8800", "twsaimahui", "twcaibawang", "twjinniu", "twcf888"]) {
  const adapter = getSiteAdapter(siteKey)
  if (!adapter || adapter.mode !== "existing-dom-only") throw new Error(`missing safe adapter: ${siteKey}`)
  if (!adapter.draw || !adapter.predictions || !adapter.navigation || !adapter.footer) {
    throw new Error(`incomplete adapter: ${siteKey}`)
  }
}
```

- [ ] **Step 2: Verify red**

Run: `node frontend/test/run-site-adapter-registry-contract.mjs`

Expected: failure because the registry is absent.

- [ ] **Step 3: Implement config-only adapter records**

```ts
export type ExistingDomAdapter = {
  siteKey: string
  mode: "existing-dom-only"
  draw: { resource: "draw"; selectors: readonly string[] }
  predictions: { resource: "predictions"; selectors: readonly string[] }
  navigation: { selector: string; fixedBehavior: "existing-script" | "css-sticky" }
  footer: { selector: string; imageUrls: readonly string[]; behavior: "existing-markup" }
}
```

Every selector must be verified from the current site source. If prediction or footer has no safe existing selector, use an empty selector array and `existing-markup`; never create a mount node.

- [ ] **Step 4: Verify green and commit**

Run: `pnpm site:test-adapter-registry`

Expected: exit code 0.

```powershell
git add package.json frontend/sites frontend/lib/site-platform/site-adapter-registry.ts frontend/test/site-adapter-registry-contract.ts frontend/test/run-site-adapter-registry-contract.mjs
git commit -m "feat: register UI-preserving site adapters"
```

## Task 6: Integrate and Verify One Site at a Time

**Files:**
- Create: `frontend/tests/e2e/site-ui-baseline.spec.ts`
- Modify: only the selected site's adapter or existing data request hook.

- [ ] **Step 1: Write a failing browser test for one site**

```ts
await page.goto(`http://127.0.0.1:3000${baseline.routePath}`)
await expect(page.locator(baseline.navigationSentinel)).toBeVisible()
await expect(page.locator(`text=${baseline.footerSentinel}`)).toBeVisible()
```

For vendor iframe pages, assert original child-frame nodes, not new shared DOM nodes.

- [ ] **Step 2: Verify red**

Run: `pnpm exec playwright test frontend/tests/e2e/site-ui-baseline.spec.ts --grep "<siteKey>"`

Expected: failure because the selected adapter has not emitted its data readiness signal.

- [ ] **Step 3: Add readiness-only integration**

After receiving data, dispatch a non-visual event:

```js
window.dispatchEvent(new CustomEvent("site-data:ready", {
  detail: { siteKey: "<siteKey>", resource: "draw", state: result.state },
}))
```

Do not replace legacy fetch/render logic in this phase. Existing renderer behavior remains source of visual truth.

- [ ] **Step 4: Verify green, review UI, and commit per site**

Run the same Playwright test. It must show the original draw/navigation/footer sentinels and the `site-data:ready` event.

Commit each site separately in this order: `twsaimahui`, `shengshi8800`, `twcaibawang`, `twjinniu`, `twcf888`.

```powershell
git add frontend/sites/<siteKey> frontend/public/vendor/<vendor-directory> frontend/tests/e2e/site-ui-baseline.spec.ts
git commit -m "feat: add UI-preserving data adapter for <siteKey>"
```

## Task 7: Documentation and Final Verification

**Files:**
- Modify: `frontend/README.md`
- Modify: `skills/vendor-site-onboarding/SKILL.md`
- Modify: `skills/vendor-site-onboarding/references/manifest-contract.md`

- [ ] **Step 1: Document enforced onboarding rules**

Add:

```md
- Treat supplied vendor HTML, CSS and JS as visual truth.
- Use `existing-dom-only` adapters by default.
- Shared code may fetch, cache and normalize data but may not mount UI.
- Changing selectors, CSS, navigation labels, footer images or prediction layout requires explicit user approval.
```

- [ ] **Step 2: Run all non-browser contracts**

```powershell
pnpm site:test-ui-baseline
pnpm site:test-data-client
pnpm site:test-adapter-registry
node frontend/test/run-site-registry-contract.mjs
node frontend/test/run-site-platform-contract.mjs
```

Expected: every command exits 0.

- [ ] **Step 3: Run browser suite and production build**

```powershell
pnpm exec playwright test frontend/tests/e2e/site-ui-baseline.spec.ts
pnpm build:frontend
```

Expected: both commands exit 0. The browser suite must explicitly reject a new shared visual container as a substitute for each site's baseline sentinels.

- [ ] **Step 4: Commit documentation only**

```powershell
git add frontend/README.md skills/vendor-site-onboarding/SKILL.md skills/vendor-site-onboarding/references/manifest-contract.md frontend/tests/e2e/site-ui-baseline.spec.ts
git commit -m "docs: require UI-preserving vendor adapters"
```

## Coverage Review

- Shared draw functionality with different UI: Tasks 2, 3, 5 and 6.
- Shared prediction loading/cache with different UI: Tasks 2, 3, 5 and 6.
- Sticky navigation and functioning navigation: Tasks 1 and 6 preserve/verify existing site behavior.
- Same prediction format with site-specific output: Tasks 2, 3 and 5.
- Shared footer behavior without visual replacement: Tasks 1, 5 and 6.
- Current five-site UI unchanged: Guardrails, Task 1 and Task 7.
