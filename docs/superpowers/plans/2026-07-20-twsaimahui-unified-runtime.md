# twsaimahui Unified Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make twsaimahui consume shared draw/prediction runtime data with cache-aware loading while preserving its vendor HTML presentation.

**Architecture:** A manifest projects site-specific DOM selectors, navigation entries, and footer assets to the browser bridge. A single reusable vendor runtime uses that configuration to render normalized draw and canonical prediction data, inject footer content, and make existing navigation sticky. The twsaimahui bundle loads this runtime and disables only its legacy dynamic prediction script tags.

**Tech Stack:** Next.js App Router, TypeScript manifests/routes, browser JavaScript, `sessionStorage`, Node VM contract tests.

---

### Task 1: Extend the manifest browser contract

**Files:**
- Modify: `frontend/lib/site-platform/site-manifest.ts`
- Modify: `frontend/lib/site-platform/site-bridge-config.ts`
- Modify: `frontend/sites/twsaimahui/site.manifest.ts`
- Modify: `frontend/test/run-site-platform-contract.mjs`

- [x] **Step 1: Write the failing manifest contract assertions**

Add an assertion that `projectPublicBridgeConfig()` includes a `runtime` object with
`draw_selector`, `prediction_selector`, `footer_selector`, and `navigation_selector`.

- [x] **Step 2: Run the contract test to verify it fails**

Run: `node frontend/test/run-site-platform-contract.mjs`

Expected: failure because `runtime` is absent from public bridge configuration.

- [x] **Step 3: Define and project the runtime configuration**

Add this typed shape to the manifest bridge contract:

```ts
runtime: {
  drawSelector: string
  predictionSelector: string
  footerSelector: string
  navigationSelector: string
  legacyPredictionScripts: "disabled" | "enabled"
}
```

Add optional `imageUrls` to `brand.footer` and project both runtime and footer
image data to the browser-safe configuration.

- [x] **Step 4: Configure twsaimahui without hardcoding it in shared code**

Use `.kaij`, `#content-area`, `#vendor-site-footer`, and `#nav2`; enable automatic
draw/prediction loading; select the six existing default vendor module keys; declare
the existing `log*.jpg` paths as footer images and configure the current anchor links.

- [x] **Step 5: Run the contract test to verify it passes**

Run: `node frontend/test/run-site-platform-contract.mjs`

Expected: process exits 0.

### Task 2: Build and test cache-aware browser bridge behavior

**Files:**
- Modify: `frontend/public/vendor/twsaimahui/site-bridge.js`
- Modify: `frontend/test/run-site-bridge-contract.mjs`

- [x] **Step 1: Write failing bridge tests**

Extend the VM harness with `sessionStorage`, a fetch-call counter, and a fake clock.
Assert concurrent `getDraw()` calls produce one request; a fresh cached response makes
no request; a stale cached response is returned immediately and starts one refresh.

- [x] **Step 2: Run the bridge contract test to verify it fails**

Run: `node frontend/test/run-site-bridge-contract.mjs`

Expected: failure because the bridge currently requests every call independently.

- [x] **Step 3: Implement the shared bridge cache**

Add per-resource TTLs, deterministic cache keys containing the site key/resource/query,
in-flight request de-duplication, memory cache, `sessionStorage` persistence, and
stale-while-revalidate events. Preserve `lottery:<resource>-loading`,
`lottery:<resource>-ready`, and `lottery:error`; add `cached` and `stale` fields to
event details.

- [x] **Step 4: Run the bridge contract test to verify it passes**

Run: `node frontend/test/run-site-bridge-contract.mjs`

Expected: process exits 0 and verifies cache/de-duplication behavior.

### Task 3: Create the reusable vendor runtime renderer

**Files:**
- Create: `frontend/public/vendor/_shared/lottery-site-runtime.js`
- Modify: `frontend/test/run-site-bridge-contract.mjs`

- [x] **Step 1: Write a failing runtime contract test**

Create a minimal fake DOM target set and assert that a ready bridge config causes the
runtime to create a draw widget, canonical prediction cards, a configurable footer,
and a fixed navigation spacer.

- [x] **Step 2: Run the bridge/runtime contract test to verify it fails**

Run: `node frontend/test/run-site-bridge-contract.mjs`

Expected: failure because the shared runtime file does not exist.

- [x] **Step 3: Implement the reusable runtime**

Implement a browser-only renderer that reads `config.bridge.runtime`, mounts:

```js
window.LotterySiteRuntime.mount({ bridge: window.LotterySiteBridge })
```

Render normalized balls with color/special-ball classes, canonical module rows with
loading/error states, configured footer image/contact/copyright elements, and a
sticky nav that offsets anchor scrolling by its current height. Call the bridge APIs
with the selected `localStorage.selectedLottery` lottery type and refresh when the
user changes the selected game.

- [x] **Step 4: Run the bridge/runtime contract test to verify it passes**

Run: `node frontend/test/run-site-bridge-contract.mjs`

Expected: process exits 0.

### Task 4: Connect twsaimahui to the shared runtime

**Files:**
- Modify: `frontend/public/vendor/twsaimahui/index.html`
- Modify: `frontend/public/vendor/twsaimahui/static/js/kj.js`
- Modify: `frontend/public/vendor/twsaimahui/static/js/site_nav.js`
- Modify: `frontend/test/run-site-bridge-contract.mjs`

- [x] **Step 1: Write failing static integration assertions**

Assert the vendor index loads `/vendor/_shared/lottery-site-runtime.js`, contains the
footer mount, does not execute `static/js/0xx*.js` prediction scripts, and loads the
shared draw mount rather than `kj/local.html`.

- [x] **Step 2: Run the assertion runner to verify it fails**

Run: `node frontend/test/run-site-bridge-contract.mjs`

Expected: failure against the current legacy script tags and iframe draw widget.

- [x] **Step 3: Apply the minimal UI-preserving migration**

Load the shared runtime after the bridge. Replace `kj.js` output with the existing
three visual tabs plus a shared draw mount. Change legacy prediction script tags to
non-executing data attributes, retain their surrounding site containers/styles, and
let the shared renderer populate `#content-area`. Add `#vendor-site-footer` at the
end of the supplied document. Replace the legacy scroll handler with shared-runtime
sticky navigation behavior.

- [x] **Step 4: Run the assertion runner to verify it passes**

Run: `node frontend/test/run-site-bridge-contract.mjs`

Expected: process exits 0.

### Task 5: Verify API, build, and local runtime behavior

**Files:**
- Modify: `frontend/README.md`

- [x] **Step 1: Document the runtime onboarding requirements**

Add the required manifest runtime selectors, cache policy, footer image configuration,
and the rule that a migrated site must not execute independent prediction fetch scripts.

- [x] **Step 2: Run static and TypeScript verification**

Run:

```powershell
pnpm site:sync-manifests
pnpm site:validate --site-key twsaimahui --strict
node frontend/test/run-site-platform-contract.mjs
node frontend/test/run-site-bridge-contract.mjs
pnpm --filter @liuhecai/frontend exec tsc --noEmit
pnpm build:frontend
```

Expected: every command exits 0.

- [x] **Step 3: Run local API smoke checks**

Run:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health
Invoke-WebRequest http://127.0.0.1:3000/api/sites/twsaimahui/draw
Invoke-WebRequest http://127.0.0.1:3000/api/sites/twsaimahui/prediction-modules
```

Expected: HTTP 200 and `ok: true` for site APIs. If PostgreSQL is unavailable,
record the exact connectivity error as an external environment blocker.

- [ ] **Step 4: Commit implementation**

```powershell
git add frontend
git commit -m "feat: unify twsaimahui vendor runtime"
```
