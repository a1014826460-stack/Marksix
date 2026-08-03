# twssz Performance Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce `twssz` initial prediction traffic and main-thread rendering cost without changing its supplier DOM, 16-issue history, module set, or lottery switching behavior.

**Architecture:** Add an opt-in compact canonical response at the Next.js site API boundary so shared/full API consumers remain unchanged. Make `twssz` issue one compact 16-row request per lottery and render non-critical mappings through cancelable idle batches while preserving the existing synchronous visible sections.

**Tech Stack:** Next.js route/service TypeScript, legacy browser JavaScript, Node contract tests, Python Playwright browser contract.

---

### Task 1: Compact Query And Cache Isolation

**Files:**
- Modify: `frontend/public/vendor/_shared/lottery-site-data-client.js`
- Test: `frontend/test/site-data-client-contract.mjs`

- [ ] **Step 1: Write the failing client contract**

Add a prediction request using `{ compact: true }`, assert the URL contains `compact=1`, then request the same lottery/history without compact and assert it performs a separate fetch. This proves compact participates in both transport and cache identity.

```js
const beforeCompact = fetchCalls
await client.loadPredictions({ lotteryType: 3, historyLimit: 16, includeVendor: false, compact: true })
assert.match(lastUrl, /compact=1/)
await client.loadPredictions({ lotteryType: 3, historyLimit: 16, includeVendor: false })
assert.equal(fetchCalls, beforeCompact + 2)
```

- [ ] **Step 2: Run the client contract and verify RED**

Run: `node frontend/test/site-data-client-contract.mjs`

Expected: FAIL because the compact request URL lacks `compact=1` and aliases the non-compact cache key.

- [ ] **Step 3: Implement compact normalization and transport**

Extend prediction query normalization and URL construction:

```js
normalized.compact = query && query.compact === true;
if (query.compact) params.set("compact", "1");
```

The normalized object is already used by storage and in-flight keys, so no separate cache implementation is added.

- [ ] **Step 4: Run the client contract and verify GREEN**

Run: `node frontend/test/site-data-client-contract.mjs`

Expected: PASS.

### Task 2: Opt-In Compact Canonical Response

**Files:**
- Modify: `frontend/lib/prediction-contract.ts`
- Modify: `frontend/lib/site-api-service.ts`
- Test: `frontend/test/prediction-contract-dedup-contract.ts`
- Test runner: `frontend/test/run-prediction-contract-dedup.mjs`

- [ ] **Step 1: Write the failing compact response contract**

Create a canonical row containing `raw.xiao`, `raw.image_url`, and unrelated database fields. Call the desired helper and assert:

```ts
const compact = compactCanonicalPredictionModules(modules)
const row = compact[0].rows[0]
if ("raw" in row) throw new Error("compact rows must omit raw")
if (row.prediction.extra.xiao !== "兔,龙") throw new Error("structured xiao must survive")
if (row.prediction.imageUrl !== "/uploads/test.jpg") throw new Error("image URL must survive")
```

Also assert the original `modules[0].rows[0].raw` remains present, proving no mutation of the default/full contract.

- [ ] **Step 2: Run the contract and verify RED**

Run: `node frontend/test/run-prediction-contract-dedup.mjs`

Expected: FAIL because `compactCanonicalPredictionModules` is not exported.

- [ ] **Step 3: Implement the compact projection**

Add a compact row/module type based on `Omit<CanonicalPredictionRow, "raw">` and export a pure projection. Copy the canonical fields and merge only renderer-required structured values into `prediction.extra`:

```ts
export function compactCanonicalPredictionModules(modules: CanonicalPredictionModule[]) {
  return modules.map((module) => ({
    ...module,
    rows: module.rows.map(({ raw, ...row }) => ({
      ...row,
      prediction: {
        ...row.prediction,
        extra: {
          ...row.prediction.extra,
          xiao: raw.xiao,
        },
      },
    })),
  }))
}
```

Do not expose arbitrary raw keys.

- [ ] **Step 4: Apply compact only when explicitly requested**

In `getSitePredictionModules`, read `context.searchParams.get("compact") === "1"` and project only `canonical_modules`. For compact calls, omit the compatibility mirror because it duplicates the same rows; default requests retain the existing envelope exactly.

```ts
const compact = context.searchParams.get("compact") === "1"
return buildSiteEnvelope(context, compact
  ? { canonical_modules: compactCanonicalPredictionModules(canonicalModules) }
  : { canonical_modules: canonicalModules, compatibility: existingCompatibility })
```

- [ ] **Step 5: Run the contract and TypeScript check**

Run:

```powershell
node frontend/test/run-prediction-contract-dedup.mjs
pnpm --filter @liuhecai/frontend exec tsc --noEmit
```

Expected: both PASS.

### Task 3: One Prediction Request Per Lottery

**Files:**
- Modify: `frontend/public/vendor/twssz/site-data-adapter.js`
- Modify: `frontend/test/twssz-adapter-contract.mjs`
- Modify: `frontend/test/twssz-live-mapping-contract.py`

- [ ] **Step 1: Write failing static and browser contracts**

Change the static contract to prohibit `historyLimit: 1`, require `compact: true`, and require exactly one history loader path. Change browser assertions so each selected lottery requests exactly `type:16`, never `type:1`, and each URL contains `compact=1`.

```js
if (adapter.includes("historyLimit: 1")) throw new Error("twssz must not duplicate prediction requests")
if (!adapter.includes("compact: true")) throw new Error("twssz must request compact rows")
```

```python
assert prediction_requests.count("3:16:1") == 1
assert not any(item.startswith("3:1:") for item in prediction_requests)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
node frontend/test/twssz-adapter-contract.mjs
D:\python\python.exe frontend/test/twssz-live-mapping-contract.py
```

Expected: static contract fails on the old latest request; browser contract reports `history_limit=1`.

- [ ] **Step 3: Remove the latest request path**

Delete `latestModulesByLottery` and `loadLatestPredictions`. Make `preloadPredictions` point to `loadHistoricalPredictions`. Initialize and switch lotteries with only:

```js
preload("predictions", {
  lotteryType: lotteryType,
  historyLimit: TWSSZ_HISTORY_LIMIT,
  includeVendor: false,
  compact: true,
})
```

Do not change `TWSSZ_HISTORY_LIMIT = 16`.

- [ ] **Step 4: Remove renderer dependence on `raw`**

Update `predictionImageUrl` to use canonical `prediction.imageUrl` or top-level `image_url`. Update `renderTiandiHistory` to obtain the pair from `prediction.extra.xiao`, falling back to canonical tokens. No compact renderer may read `row.raw`.

- [ ] **Step 5: Run static and browser contracts and verify GREEN**

Run the two commands from Step 2. Expected: PASS with one request per lottery and complete 16-row rendering.

### Task 4: Cancelable Idle Rendering Batches

**Files:**
- Modify: `frontend/public/vendor/twssz/site-data-adapter.js`
- Modify: `frontend/test/twssz-adapter-contract.mjs`
- Modify: `frontend/test/twssz-live-mapping-contract.py`

- [ ] **Step 1: Add failing batch-render contract**

Require named `renderGeneration`, `scheduleMappingBatch`, and active-lottery guards. In the browser contract, switch 3 -> 2 -> 1 quickly and assert final DOM contains only Hong Kong markers after all idle batches settle.

- [ ] **Step 2: Run tests and verify RED**

Run the static and browser contracts. Expected: FAIL because rendering is synchronous and has no generation guard.

- [ ] **Step 3: Implement fixed idle batches**

Keep `renderGradeHistory`, `renderAaaGradeHistory`, and the first visible mappings synchronous. Increment `renderGeneration` for every accepted response/switch. Schedule remaining mappings in batches of four using `requestIdleCallback` with `setTimeout` fallback; each callback exits when its captured generation or lottery type is stale.

- [ ] **Step 4: Run tests and verify GREEN**

Run the static and browser contracts. Expected: PASS, with complete final DOM and no cross-lottery markers.

### Task 5: Full Regression And Measured Performance

**Files:**
- Modify only if a regression requires a scoped correction.

- [ ] **Step 1: Run contract suites**

```powershell
node frontend/test/site-data-client-contract.mjs
node frontend/test/run-prediction-contract-dedup.mjs
node frontend/test/twssz-adapter-contract.mjs
pnpm site:test-data-client
pnpm site:test-adapter-registry
pnpm site:validate --site-key twssz
pnpm --filter @liuhecai/frontend exec tsc --noEmit
```

- [ ] **Step 2: Run browser verification**

```powershell
D:\python\python.exe frontend/test/twssz-live-mapping-contract.py
```

Assert no console/page errors, all three lotteries render 16 issues, cached return works, and only one prediction request occurs per lottery.

- [ ] **Step 3: Measure payload reduction**

Compare local `history_limit=16&include_vendor=0` against the same URL with `compact=1`. Record bytes and require the compact payload to omit compatibility duplication and row `raw`; report the actual reduction rather than a guessed target.

- [ ] **Step 4: Final repository checks**

```powershell
git diff --check
git status --short
```

Preserve the pre-existing image changes and report them separately from the optimization.
