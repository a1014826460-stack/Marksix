# Vendor Five-Site Technical Audit and Rapid Onboarding Plan

**Audit date:** 2026-07-20  
**Scope:** `frontend/public/vendor/` public sites: `shengshi8800`, `twcaibawang.com`, `twcf888.com`, `twjinniu`, and `twsaimahui`.  
**Evidence basis:** repository source and configuration inspection; no production URLs were requested or accessed.

---

## 1. Executive Conclusion

### 1.1 Overall diagnosis

The five sites have reached **partial platform unification**:

- **Unified:** all five site identities are registered in one TypeScript registry; there is a common backend client, a canonical prediction schema, a path-based unified API family, common metadata/domain matching, and one Next.js/Docker build pipeline.
- **Not unified:** vendor UI, HTML structure, legacy JavaScript, route entries, data provider branching, API paths consumed by pages, footer/header/navigation composition, and client loading/error experience remain site-specific.
- **Practical classification:** this is a **"shared compatibility platform + five legacy presentations"**, not yet a configurable, template-driven multi-site frontend.

It is accurate to say that the project has a reusable **data/API integration base**, but it is not accurate to say that it already has a reusable **site template**. A new legacy site still requires code changes in the registry, route/page entry, runtime adapter, and often in the vendor JavaScript or an iframe wrapper.

### 1.2 Suitability for the requested new-site scenario

| Capability | Current state | Assessment |
| --- | --- | --- |
| Accept a supplied HTML/CSS/JS bundle | Yes, by copying to `public/vendor/<site>/` | Basic asset hosting is ready. |
| Attach prediction data without modifying site business code | Partly | The canonical API exists, but the old page must know how to read it or receive a generated legacy adapter. |
| Attach draw data without modifying site business code | Partly | `/api/latest-draw`, `/api/draw-history`, legacy `/api/kaijiang/*`, `wy.json`, and JSONP adapters exist, but are not one declarative profile. |
| Configure header, logo, nav, footer, contacts | No | These are mostly embedded in vendor HTML or per-site React components. |
| One configuration registration and build | No | Registry and deployment are centralized; page routing, host behaviour and legacy compatibility still contain hard-coded site lists. |
| One command with validation and deployment | No | Build commands exist; import, audit, config generation, host validation and smoke tests are manual. |

**Recommended target:** preserve each vendor site's visual shell, but introduce a declarative `site.manifest.ts` plus a shared `VendorSiteShell` and `SiteDataBridge`. The bridge exposes standard data, state, and UI configuration to legacy pages, while the manifest drives the registry, route, host mapping, compatibility aliases and validation.

---

## 2. Audit Method and Inventory

### 2.1 Inventory methodology

The audit counted recursively stored files, inspected index entries and static references, compared CSS/JS byte hashes where applicable, traced frontend API routes and backend proxy calls, and ran the current frontend contract checks. The `admin-history` directory is excluded because it is an administration/history asset bundle rather than one of the five public sites named in the registry and current design documentation.

### 2.2 Vendor asset inventory

| Site key / vendor directory | Files / size | HTML | JS | CSS | Current runtime strategy |
| --- | ---: | ---: | ---: | ---: | --- |
| `shengshi8800` | 60 / 1.59 MiB | 3 | 51 | 4 | Next legacy shell plus `embed.html` iframe |
| `twcaibawang` / `twcaibawang.com` | 107 / 23.86 MiB | 27 | 5 | 4 | React rebuilt homepage; static article assets remain |
| `twcf888` / `twcf888.com` | 70 / 1.98 MiB | 53 | 2 | 3 | React wrapper plus vendor homepage iframe; React article pages |
| `twjinniu` | 80 / 8.49 MiB | 34 | 6 | 3 | React wrapper plus vendor homepage iframe; React article pages |
| `twsaimahui` | 97 / 4.06 MiB | 2 | 77 | 1 | Vendor page iframe with legacy runtime/interceptor |

None of the five `vendor` directories contains `package.json`, Vite/Webpack/Rollup config, `tsconfig`, or a per-site `.env` file. They are archived static bundles, not independently buildable applications. They are built and served only by the parent Next.js project.

### 2.3 Directory patterns and site-specific differences

| Site | Representative layout | Primary page/data pattern | Important differences |
| --- | --- | --- | --- |
| `shengshi8800` | `index.html`, `embed.html`, `kj/local.html`, `static/css`, `static/js` | Dozens of jQuery `$.ajax` calls to `/api/kaijiang/*?web=&type=` | The densest module surface; has custom request de-duplication and presentation masking in `ajax_interceptor.js`. |
| `twsaimahui` | `index.html`, `kj/local.html`, `static/css`, `static/js` | Vue/jQuery/Axios legacy page with nearly 80 scripts | Provides a relatively mature legacy runtime (`legacy_runtime.js`) and `api_client.js`; still relies on many dynamically loaded third-party scripts. |
| `twcaibawang.com` | `index.html`, `wy.html`, `wylhc.html`, numbered article HTML, `static/*` | Static content plus draw JSON/JSONP; React homepage now replaces vendor index | Its current React component is very large and still calls non-unified API routes. |
| `twjinniu` | `index.html`, `amgst/*.html`, `index_files`, `static/*` | Vendor index dynamically calls `/api/twjinniu/*` | React host iframe handles sticky navigation; page itself has its own live-module loading and fallback. |
| `twcf888.com` | `index.html`, `amgst/*.html`, `index/*`, `index_files`, `static/*` | Vendor index dynamically calls `/api/twcf888/*` | React host iframe handles sticky navigation; vendor page implements its own loading skeleton/cache/fallback. |

The apparent `twcaibawang` / `twcf888` / `twjinniu` family shares a visual baseline, but it is not a component package. For example, `custom.css` is byte-identical in all three and certain jQuery/data files are identical, whereas `main.css`, `common.js`, and much of the HTML are divergent. `shengshi8800` and `twsaimahui` share identical bundled Vue and Axios files, but their interceptors and all presentation code are different. These copies should not be treated as a safe shared dependency without versioning and regression tests.

---

## 3. Current Unification Status

### 3.1 Directory, build, and deployment configuration

**Unified elements**

- A single pnpm workspace (`package.json`) builds `@liuhecai/frontend`; Next.js standalone output and Docker image assembly are centralized in `Dockerfile.frontend`.
- The frontend receives the Python API origin through `LOTTERY_BACKEND_BASE_URL`; Docker supplies `http://python-api:8000/api`.
- Nginx forwards public routes and `/api/*` to the single Next frontend service.
- Long-lived caching is defined for `/vendor/:siteKey/static/:path*`.

**Non-unified elements**

- Each vendor bundle embeds its own relative/absolute paths, external scripts, fixed links, styles and global variables. There is no asset manifest, integrity list, allowlist, or rewrite pipeline.
- Only static files under `/vendor/<site>/static/**` receive the one-year immutable cache rule. HTML and other vendor assets have no explicit content-version policy.
- `next.config.mjs` sets `typescript.ignoreBuildErrors: true`, so Docker build success is not a type-safety gate.
- `LOTTERY_SITE_ID` is a global fallback, while correct multi-site identity is actually carried by the registry's fixed `defaultSiteId`/`defaultWebId`. This dual source of truth is confusing for onboarding.
- Nginx works for all hosts by proxying to Next, but formal host routing and TLS certificates still require manual server-block configuration and validation.

### 3.2 Dependency diagnosis

| Dependency group | Observed use | Unified? | Risk / impact |
| --- | --- | --- | --- |
| Next.js 16 + React 19 | Parent frontend only | Yes | The main build/runtime platform. |
| jQuery 1.10/1.11 | All vendor families in different copies | No | Duplicate copies, mixed versions and global `$` dependencies. |
| Vue + Axios | `shengshi8800`, `twsaimahui` vendor bundles | No | Byte-identical copies exist but no managed shared version or SRI. |
| Static CSS | Each site `static/css/*` | No | Shared file names do not imply compatible content. |
| Legacy request globals | `httpApi`, `web`, `type`, `jy`, `pt`, ad globals | No | A new site needs a custom compatibility runtime or source edit. |
| External scripts/links | All bundles, especially `twsaimahui` and `twcf888` | No | Unpinned external behaviour breaks reproducibility and weakens CSP/Supply-chain control. |

The vendor content also contains many remote navigation/ad/tracker URLs. Before deploying a new archive, the import process must inventory remote URLs, allowlist approved domains, localize essential resources where permitted, and reject unexpected executable scripts. This is also necessary because several site packages use root-relative resources such as `/index_files/pub.js`, `/wy.json`, `/components/*` and `/api/*`, which can otherwise collide between sites.

### 3.3 API invocation and data contract diagnosis

The platform has three layers. They must remain explicitly distinguished:

```text
Legacy/vendor JS or React page
  -> Next compatibility routes under /api/*
  -> Python public/legacy APIs under LOTTERY_BACKEND_BASE_URL (/api)
```

**Existing unified API surface**

```text
GET  /api/sites/:siteKey/site-page
GET  /api/sites/:siteKey/homepage-modules
GET  /api/sites/:siteKey/prediction-modules
GET  /api/sites/:siteKey/article-detail?article_id=...
POST /api/sites/:siteKey/traffic-events
```

The successful response uses an envelope with `ok`, resolved site identity and `data`. The prediction endpoint returns both canonical modules and a compatibility section. Site identity is path-owned: query `site_id`, `web`, and `web_id` cannot override the registered site's identity.

**Canonical prediction pipeline already in place**

```text
Python /public/site-page + /vendor/homepage-modules
  -> CanonicalPredictionModule[]
  -> per-render compatibility payload
  -> vendor JS or React presentation
```

`CanonicalPredictionModule` includes a stable `moduleKey`, title, display kind, normalized rows and source; each row provides issue/year/term, prediction, result, status and raw fallback fields. This is the correct base for automatic new-site data integration.

**Remaining API inconsistencies**

- `shengshi8800` directly uses legacy `/api/kaijiang/*` endpoints and `web/type` parameters.
- `twsaimahui` uses the legacy Kaijiang family plus `/api/index/notice`; its runtime adds `site_key`, domain and source parameters.
- `twjinniu` vendor JS calls `/api/twjinniu/site-page` and `/api/twjinniu/homepage-modules`, not the preferred `/api/sites/twjinniu/*` routes.
- `twcf888` vendor JS does the same with `/api/twcf888/*`.
- `twcaibawang` React client refreshes through `/api/public/site-page` and `/api/vendor/homepage-modules`, bypassing its own unified site route. It also has a custom `wy.json` and JSONP history adapter.
- Draw data exists in several representations: modern JSON `/api/latest-draw`, `/api/next-draw-deadline`, `/api/draw-history`; `wy.json` array compatibility; JSONP `historyAO`; and legacy `/api/kaijiang/*` rows.

Thus data normalization is solid for prediction modules, but **draw data and legacy response profiles are not yet unified declaratively**.

### 3.4 UI, routing, state, and environment diagnosis

| Area | Current implementation | Diagnosis |
| --- | --- | --- |
| Shared components | `LegacyModulesFrame`, `SiteTrafficTracker`, basic render-mode helper | Only shell/traffic concerns are reusable; no shared Header/Footer/Nav/Logo component. |
| Routing | `app/<site>/page.tsx`, root host rewrite, standalone legacy aliases | Registry has route paths, but every current site has its own page/layout and special route code. |
| State | Local React `useState`, iframe DOM inspection, legacy globals | No shared state store; not inherently wrong, but no common site page-state contract. |
| Render modes | `legacy-shell`, `iframe-vendor`, `react-home` in registry | The type exists, but `renderSiteByMode()` is only used by a test, not by production page selection. |
| Environment | Backend base URL + global default site ID | No validated per-site environment schema; API profile and UI config are hard-coded. |
| Branding/public UI | Vendor HTML and per-site components | Logo, nav, footer notices, copyright, contacts and images are not config-injected. |
| Loading/errors | Each page decides itself | `twcf888` has skeleton/cache/error markup; `twjinniu` silently replaces failed data; `twcaibawang` retains previous state; legacy pages differ further. |

### 3.5 Route/state hard-coding evidence

- Five current configurations are centralized in `frontend/lib/sites.ts:40`, but `getSiteHomepageModules()` switches directly on `twjinniu` and `twcf888` in `frontend/lib/site-api-service.ts:63`.
- Article resolution defaults to a `twjinniu` provider for every non-`twcf888` site in `frontend/lib/site-api-service.ts:117`, which cannot scale safely to unknown sites.
- `renderSiteByMode()` exists at `frontend/lib/site-rendering.tsx:11`, yet has no production caller.
- `TwjinniuHomeClient` and `Twcf888HomeClient` duplicate nearly identical iframe/sticky-nav implementations with hard-coded vendor URLs at `frontend/components/twjinniu/TwjinniuHomeClient.tsx:5` and `frontend/components/twcf888/Twcf888HomeClient.tsx:5`.
- `TwcaibawangHomeClient` is 84 KiB and embeds route/API/footer/asset assumptions; it calls non-unified APIs at `frontend/components/twcaibawang/TwcaibawangHomeClient.tsx:1643`.
- Legacy shared root resources are selected through explicit three-site `matchSiteRequest()` lists, e.g. `frontend/app/index_files/pub.js/route.ts:8`; onboarding a fourth compatible static family requires source edits.

---

## 4. Site-by-Site Assessment

| Site | Existing API readiness | UI/config readiness | Onboarding reuse value | Main blocker |
| --- | --- | --- | --- | --- |
| `shengshi8800` | High legacy compatibility; many mapped Kaijiang modules | Low; header/nav are shell code and vendor HTML | Good for a legacy-module profile | Endpoint-to-module mapping and page globals remain specialized. |
| `twsaimahui` | Moderate/high; runtime centralizes request base and site params | Low; vendor content loads many scripts and embeds presentation data | Best source for a generic legacy bridge | Need to turn its site-specific runtime into a neutral runtime. |
| `twcaibawang` | High for draw adapters and server data loading | Low; React HTML builder has branding/footer/assets embedded | Good source for draw compatibility profiles | One huge component and bypassed unified API surface. |
| `twjinniu` | Moderate/high; site page and homepage endpoints present | Moderate; iframe wrapper can be generalized | Good source for an iframe vendor renderer | Vendor index consumes old site-specific routes and hard-coded paths. |
| `twcf888` | Moderate/high; richer homepage/article provider | Moderate; vendor has loading/cache experience | Good source for declarative profile concepts | Site-specific provider, article catalog and large remote dependency set. |

### Conclusion on the requested "five sites" template question

There is **no fully reusable common template** for the five sites today. The closest reusable elements are:

1. `FrontendSiteConfig` registry and host/path resolution.
2. Unified site API envelope and canonical prediction schema.
3. `backendFetchJson()` error parsing and no-store backend requests.
4. Legacy compatibility endpoints and draw adapters.
5. `SiteTrafficTracker` and container deployment.

The missing template layer is exactly the one that controls UI configuration, asset mounting, compatibility API profile, a production renderer, a single per-site manifest, and automated validation/deployment.

---

## 5. Prioritized Problem List

### P0 - prevents a true zero-business-code onboarding path

1. **No declarative site manifest.** Registry fields only describe basic identity/render mode; they cannot describe API compatibility mappings, page insertion selectors, branding, navigation/footer or legacy globals. New sites require editing TypeScript implementation files.
2. **Prediction is canonicalized, but no generic injection bridge exists.** `/api/sites/:siteKey/prediction-modules` is usable only when the page is coded to consume the canonical envelope. A supplied legacy HTML/JS bundle will not automatically render it.
3. **Draw data has multiple ad hoc profiles.** Modern draw JSON, `wy.json`, JSONP `historyAO`, and Kaijiang rows need an explicit profile layer, rather than one-off route implementations.
4. **Public UI modules are hard-coded.** No configuration-driven Header/Nav/Footer renderer or legacy DOM injection strategy exists.

### P1 - material maintenance, correctness, and launch risk

5. **Partial registry adoption.** Runtime service branching, fixed three-site request matching, dedicated page entries, and duplicated iframe clients are still required.
6. **Inconsistent error/loading policies.** New pages cannot rely on a standard retry, timeout, cache, empty-state, or user-visible error contract.
7. **Legacy API alias ownership is scattered.** The preferred route is `/api/sites/:siteKey/*`, but vendor pages still use bespoke routes; aliases lack a manifest-driven mapping and deprecation telemetry plan.
8. **Per-site configuration lacks schema validation.** Wrong domain, `webId`, lottery type, static path or API profile can pass compilation and fail only in browser usage.
9. **Build is permitted with TypeScript errors.** `typescript.ignoreBuildErrors` masks integration regressions in image/route/manifest code.
10. **External resources are unmanaged.** HTML references remote scripts and opaque ad/navigation URLs; neither an allowlist nor an asset scan blocks surprise code or unavailable dependencies.

### P2 - efficiency and quality debt

11. **Duplicated vendor libraries and bespoke wrappers.** Shared byte-identical copies of jQuery, Vue, Axios and small CSS can be deduplicated only after controlled compatibility tests; immediate blind deduplication is not recommended.
12. **Large page components mix rendering, static content, data requests and branding.** `TwcaibawangHomeClient` makes regression tests and configuration injection difficult.
13. **Route-level tests are shallow.** Existing registry and prediction compatibility scripts validate identity/routing contracts, but do not smoke-test all new-site manifest permutations, data mappings or browser loading states.
14. **Asset path collisions are possible.** Root-relative legacy paths such as `/index_files/*`, `/wy.json`, and `/components/*` are selected by referer/host rules, not namespaced per vendor package.

---

## 6. Target Architecture for Rapid Deployment

### 6.1 Design principles

- Preserve vendor HTML/CSS/JS first; do not force a React rewrite to onboard a new site.
- Make **the manifest the only required code-like artifact** for a standard new site. Custom code is an explicit exception for unusual DOM/data semantics.
- Keep the current canonical prediction schema as the sole prediction truth.
- Introduce a canonical draw schema and generate both modern and legacy response profiles from it.
- Put branding, navigation, footer, contacts and static URLs in configuration; inject into React shells or legacy DOM slots.
- Default to same-origin frontend APIs; only the server knows `LOTTERY_BACKEND_BASE_URL`.
- Validate the manifest, referenced assets, host mapping, API response mapping and browser smoke result before deployment.

### 6.2 Proposed directory structure

```text
frontend/
  app/
    (sites)/[siteKey]/page.tsx                 # one generic public entry
    api/sites/[siteKey]/
      bootstrap/route.ts                        # UI config + current data state
      draw/route.ts                             # canonical draw response
      prediction-modules/route.ts               # existing canonical prediction response
      legacy/[profile]/[[...path]]/route.ts     # generated compatibility profiles
  components/site-shell/
    VendorSiteShell.tsx                         # chooses renderer from manifest
    ConfiguredHeader.tsx
    ConfiguredFooter.tsx
    ConfiguredNavigation.tsx
    VendorIframeRenderer.tsx
    LegacyDomBridge.tsx
    SiteDataStatus.tsx
  lib/site-platform/
    manifest-schema.ts                          # Zod schema + validation
    manifest-loader.ts                          # loads manifests into registry
    api-client.ts                               # timeout/retry/error normalization
    draw-contract.ts                            # canonical draw schema
    draw-adapters.ts                            # modern/wy/jsonp/kaijiang profiles
    prediction-bridge.ts                        # canonical -> bridge payload
    legacy-profile.ts                           # aliases/params/response mapping
    asset-audit.ts                              # local refs + external allowlist scan
  sites/
    shengshi8800/site.manifest.ts
    twsaimahui/site.manifest.ts
    twcaibawang/site.manifest.ts
    twjinniu/site.manifest.ts
    twcf888/site.manifest.ts
    <new-site>/site.manifest.ts
  public/vendor/
    <siteKey>/                                 # unmodified supplied archive
      index.html
      static/
      site-bridge.js                            # generated/shared bridge only
      site-config.json                          # generated public subset only
scripts/
  import-vendor-site.mjs                        # intake, normalize paths, generate scaffold
  validate-site-manifest.mjs                    # schema/assets/routes/API checks
  smoke-site.mjs                                # browser/API smoke tests
```

`public/vendor/<siteKey>/` should contain the supplied files as faithfully as possible. Generated files live next to the bundle with clear generated headers, so vendor upgrades can replace original assets without losing the platform bridge.

### 6.3 One site manifest

Use TypeScript plus Zod validation because the existing frontend already uses TypeScript and Zod. Never expose backend credentials in this object; emit only a filtered browser configuration JSON.

```ts
// frontend/sites/demo-lottery/site.manifest.ts
import type { SiteManifest } from "@/lib/site-platform/manifest-schema"

export default {
  version: 1,
  identity: {
    siteKey: "demo-lottery",
    domains: ["www.demo-lottery.example", "demo-lottery.example"],
    routePath: "/demo-lottery",
    siteId: 12,
    webId: 12,
    defaultLotteryType: 3,
  },
  renderer: {
    kind: "vendor-iframe", // vendor-iframe | legacy-dom | react-template
    entry: "/vendor/demo-lottery/index.html",
    contentSelector: "#site-content",
    injectBridge: true,
  },
  api: {
    prediction: {
      endpoint: "/api/sites/demo-lottery/prediction-modules",
      query: { history_limit: 8 },
      legacyProfile: "canonical-dom-v1",
      moduleSlots: [
        { moduleKey: "public_yixiao_yima", selector: "#yixiao" },
        { moduleKey: "shuangbo_12ma", selector: "#shuangbo" },
      ],
    },
    draw: {
      profile: "wy-json-v1", // canonical-json-v1 | wy-json-v1 | history-jsonp-v1 | kaijiang-v1
      latestEndpoint: "/api/sites/demo-lottery/draw",
      pollMs: 30000,
    },
    legacyAliases: [
      { path: "/wy.json", profile: "wy-json-v1" },
      { path: "/index/ajax/ttklsjl", profile: "history-jsonp-v1" },
    ],
  },
  brand: {
    siteName: "示例六合资料站",
    logoUrl: "/vendor/demo-lottery/static/image/logo.png",
    faviconUrl: "/vendor/demo-lottery/static/favicon.ico",
    theme: { primary: "#0752cb", accent: "#e94335", background: "#ffffff" },
    navigation: [
      { label: "首页", href: "/demo-lottery" },
      { label: "开奖记录", href: "/demo-lottery/history" },
      { label: "高手资料", href: "#experts" },
    ],
    footer: {
      copyright: "Copyright 2026 示例六合资料站",
      icpImageUrl: "/vendor/demo-lottery/static/image/icp.png",
      contacts: [{ label: "Telegram", href: "https://t.me/example" }],
    },
  },
  security: {
    externalScriptAllowlist: [],
    externalNavigationAllowlist: ["https://t.me"],
  },
} satisfies SiteManifest
```

### 6.4 Generic runtime/data flow

```text
Host or /[siteKey]
  -> manifest loader validates site identity and assets
  -> VendorSiteShell selects renderer
  -> /api/sites/:siteKey/bootstrap returns public brand config and data state
  -> SiteDataBridge requests canonical draw + prediction APIs
  -> adapter selected by api.profile maps data to legacy callbacks/DOM slots
  -> shared header/footer renderer OR LegacyDomBridge injects configured blocks
```

The legacy bridge must expose a stable browser API without requiring vendor business code changes:

```js
// public/vendor/<siteKey>/site-bridge.js
window.LotterySiteBridge = {
  config: window.__SITE_CONFIG__,
  state: { prediction: "idle", draw: "idle" },
  on(eventName, listener) { /* subscribe to loading/ready/error */ },
  getPredictionModules(options) { /* GET /api/sites/:siteKey/prediction-modules */ },
  getDraw(options) { /* GET /api/sites/:siteKey/draw */ },
  mountBranding() { /* header/nav/footer selectors from manifest */ },
};
```

For an unchanged old page, `LegacyDomBridge` can populate selectors using manifest mappings. For a page with its own JS extension point, it can dispatch browser events instead:

```js
window.dispatchEvent(new CustomEvent("lottery:prediction-ready", {
  detail: { modules, lotteryType, source: "canonical-v1" },
}));
```

This makes the no-business-logic-change promise realistic: onboarding configures selectors/events and profile names; only genuinely unknown data semantics need a new adapter module and an explicit test.

### 6.5 Canonical API, mapping, loading and error contract

#### Requests

```text
GET /api/sites/:siteKey/prediction-modules?lottery_type=3&history_limit=8
GET /api/sites/:siteKey/draw?lottery_type=3
GET /api/sites/:siteKey/bootstrap?lottery_type=3
```

The route owns `siteId` and `webId`; callers may select only allowed presentation options such as `lottery_type`, `history_limit`, `mode_ids` or declared module groups. No browser call passes a raw backend URL.

#### Canonical draw response

```ts
type CanonicalDraw = {
  currentIssue: string
  openedAt: string | null
  nextIssue: string | null
  nextDrawAt: string | null
  balls: Array<{
    value: string // always two digits
    color: "red" | "blue" | "green"
    zodiac: string
    element: string | null
    isSpecial: boolean
  }>
}
```

#### Mapping rules

| Source / target | Mapping |
| --- | --- |
| Python latest-draw result balls + special ball | `CanonicalDraw.balls`, marking the special ball with `isSpecial`. |
| Python next-draw deadline | `nextIssue`, `nextDrawAt`. |
| Canonical prediction module | Stable `moduleKey`, `title`, `displayKind`, ordered normalized rows. |
| `wy-json-v1` | Generates the legacy one-item array: `expect`, CSV `openCode/zodiac/wave/wuxin`, `nextexpect`, `nextTime`. |
| `history-jsonp-v1` | Generates `var historyAO = { year, data: [...] };`. |
| `kaijiang-v1` | Uses a declared endpoint-to-module mapping; validates required legacy fields and emits empty strings, never `null`, for fields legacy pages split/parse. |
| `canonical-dom-v1` | Uses `moduleSlots` to render shared table markup or dispatch normalized rows to a declared page event. |

#### Request state and failure policy

All bridge calls use one fetch wrapper:

```ts
type LoadState<T> =
  | { status: "loading"; data?: T }
  | { status: "ready"; data: T; updatedAt: string }
  | { status: "stale"; data: T; error: SiteApiError }
  | { status: "error"; error: SiteApiError }

type SiteApiError = {
  code: "NETWORK" | "TIMEOUT" | "BAD_RESPONSE" | "BACKEND" | "UNAUTHORIZED_PROFILE"
  message: string
  retryable: boolean
  requestId?: string
}
```

Required behaviour:

- timeout after 10 seconds, abort on superseded lottery-type switch, retry GET failures at most twice with exponential backoff;
- show skeleton on first load; retain valid cached data as `stale` on refresh failure; show a localized retry action only when there is no usable cached data;
- never let a tracking failure, missing optional module, or individual module mapping failure break the page;
- log structured server-side errors with `siteKey`, adapter/profile, endpoint, HTTP status and correlation/request ID;
- return `{ ok: false, error: { code, message, retryable } }` consistently from frontend APIs for expected errors.

### 6.6 Configuration-injected public UI

The chosen renderer determines how configuration is applied:

| Renderer | Header/nav/footer mechanism |
| --- | --- |
| `react-template` | Render `ConfiguredHeader`, `ConfiguredNavigation`, and `ConfiguredFooter` directly from `brand`. |
| `vendor-iframe` | Preserve visual fidelity; use the parent shell for optional shared top/bottom chrome, with an iframe configuration query or `postMessage` only for approved changes. |
| `legacy-dom` | Inject a generated, scoped block into declared `headerSelector`, `navSelector`, `footerSelector`; replace only `data-site-slot` placeholders where available. |

`LegacyDomBridge` must scope all generated selectors beneath a site root attribute such as `[data-site-key="demo-lottery"]`. It must not use broad document selectors that can conflict with vendor widgets. If a vendor page cannot safely expose slots, treat it as `vendor-iframe`; do not rewrite opaque minified vendor JS during routine onboarding.

---

## 7. Migration Plan for the Existing Five Sites

### Phase A - establish the platform seam (first)

1. Add manifest schema/loader and convert `FrontendSiteConfig` to a derived, read-only registry view.
2. Implement generic `/[siteKey]` site shell and make production use `renderSiteByMode`; retain existing route aliases as thin redirects/re-writes for SEO and backwards compatibility.
3. Introduce canonical draw schema and the four named profiles (`canonical-json-v1`, `wy-json-v1`, `history-jsonp-v1`, `kaijiang-v1`).
4. Move legacy alias ownership to manifest declarations; use a generic resolver rather than fixed `matchSiteRequest()` lists.
5. Add `site-bridge.js` and public `site-config.json` generation, then validate external resources before serving a site.

### Phase B - adopt without visual rewrite

| Site | Migration action |
| --- | --- |
| `shengshi8800` | Manifest: `legacy-shell`; translate existing `web/type` and Kaijiang endpoint mappings to `kaijiang-v1`; keep the current shell while replacing hard-coded defaults with manifest values. |
| `twsaimahui` | Extract generic portions of `legacy_runtime.js` and `api_client.js` into `site-bridge.js`; manifest supplies `siteKey`, API base, web/type profile and brand slots. |
| `twcaibawang` | Move draw compatibility aliases into the manifest; make client refresh call `/api/sites/twcaibawang/*`; extract footer/header/nav strings/assets into `brand`. Split the 84 KiB component by data, page sections and chrome. |
| `twjinniu` | Replace duplicated iframe host with `VendorIframeRenderer`; switch vendor index requests to aliases generated from the manifest, then later switch to `/api/sites/*`. |
| `twcf888` | Same renderer consolidation; declare its homepage/article provider in manifest capability/provider metadata rather than service `if` branches. Preserve its loading-cache UX as a reusable bridge policy. |

### Phase C - remove adoption blockers

1. Replace service `if (siteKey === ...)` branches with registered provider interfaces:

```ts
type SiteProvider = {
  getHomepageModules(context: SiteApiContext): Promise<unknown>
  getArticleDetail?(context: SiteApiContext, articleId: string): Promise<unknown>
}
```

2. Replace duplicated Twjinniu/Twcf888 iframe components with one parameterized renderer.
3. Make all active clients request `/api/sites/:siteKey/*`; retain old aliases only for vendor compatibility and measure `api_compat_hit` until unused.
4. Set `typescript.ignoreBuildErrors` to `false` after correcting existing errors; run `tsc --noEmit` before build in CI and release scripts.
5. Add Playwright browser smoke tests at each configured domain/route with mocked backend fixtures and a production-like API test.

---

## 8. New-Site One-Command Deployment Manual

### 8.1 Precondition

The incoming package must contain only the new site's HTML, JS, CSS, images and fonts, plus a list of intended domain names and a backend `siteId`/`webId` that already exists in the database. The new site must have a known prediction module mapping or an explicit decision that a module remains static/snapshot-only. Do not infer `webId` from a display name.

### 8.2 Static configuration checklist

Fill these fields before import:

| Group | Required fields |
| --- | --- |
| Identity | `siteKey`, `siteName`, domains, route path, `siteId`, `webId`, default lottery type |
| Renderer | `vendor-iframe` / `legacy-dom` / `react-template`, vendor entry path, root/content/header/nav/footer selectors if DOM mode |
| Backend integration | prediction module keys/slot selectors, draw profile, history limit, optional legacy aliases |
| Branding | favicon URL, logo URL, primary/accent/background colors, navigation items |
| Footer | copyright text, ICP/registration image URL, contact labels/URLs |
| Assets/security | vendor asset root, approved remote script origins, approved outbound navigation origins |
| Operations | cache policy, production host/TLS configuration, analytics/traffic enabled flag |

### 8.3 File placement convention

```text
incoming/demo-lottery/                    # untouched supplied archive
frontend/public/vendor/demo-lottery/      # imported archive destination
frontend/sites/demo-lottery/site.manifest.ts
frontend/sites/demo-lottery/README.md     # generated operation notes
frontend/test/fixtures/demo-lottery/      # expected API/DOM fixtures
```

Rules:

- Use lowercase kebab-case `siteKey`; it becomes the asset directory, route key and manifest directory.
- Keep vendor assets under `public/vendor/<siteKey>/`; never scatter new files under root `/index_files`, `/components`, or `/static`.
- Any site-specific injected bridge/config must be generated as `public/vendor/<siteKey>/site-bridge.js` and `site-config.json`.
- Root-relative references in imported HTML must be rewritten to `/<vendor-base>/...` or represented as manifest legacy aliases. Relative references may stay relative.
- Do not hand-edit original vendor sources for branding/data wiring except a deliberate, reviewed migration. Prefer declared slots or iframe rendering.

### 8.4 Import, validate, develop, and package

After the target platform changes described in this report are implemented, the standard flow is:

```powershell
# 1. Import archive, copy assets, rewrite only unsafe root-relative paths,
#    scan external URLs, and scaffold the manifest.
pnpm site:import --source .\incoming\demo-lottery --site-key demo-lottery

# 2. Complete the generated manifest, then validate schema, files, URL allowlists,
#    backend site identity, prediction mappings and legacy alias conflicts.
pnpm site:validate --site-key demo-lottery

# 3. Run API contract + browser smoke checks for all declared lottery types.
pnpm site:smoke --site-key demo-lottery

# 4. Run project quality checks and production build.
pnpm --filter @liuhecai/frontend exec tsc --noEmit
pnpm lint:frontend
pnpm build:frontend

# 5. Build and publish the deployment image.
docker compose build frontend
docker compose up -d --force-recreate frontend nginx
docker compose exec nginx nginx -t
```

The initial codebase does not yet define the `site:import`, `site:validate`, or `site:smoke` scripts. Add them as part of Phase A; until then use the current manual equivalent: copy files, register the site in `frontend/lib/sites.ts`, add needed route/page behavior, run TypeScript plus contract tests, build the frontend, then update Nginx domain/TLS configuration.

### 8.5 Required acceptance gates

| Gate | Expected result |
| --- | --- |
| Manifest validation | No duplicate domain/route/alias, valid IDs/types/selectors, all local assets exist. |
| API validation | Canonical prediction and draw endpoints return `ok: true`; `moduleKey` and draw ball contracts match fixtures. |
| Legacy profile validation | `wy.json` is one array item; JSONP defines `historyAO`; legacy fields required by page JavaScript are non-null strings. |
| Browser smoke | Homepage loads with no failed local asset, selected lottery type updates data, loading/retry state is visible, footer/nav/contacts use manifest values. |
| Security scan | Every remote executable/navigation origin is allowlisted; no unexpected HTTP mixed content. |
| Release health | `GET /health` remains healthy; new host resolves to the configured site rather than the root default. |

### 8.6 Rollback

The manifest should include `enabled: false` and an optional stable `fallbackUrl`. Disabling a site removes host/route selection and generated legacy aliases without deleting vendor assets or prediction history. Deployment rollback remains an image/version rollback through Docker Compose; database site data is not rolled back by frontend asset changes.

---

## 9. Suggested Implementation Backlog

| Priority | Deliverable | Acceptance condition |
| --- | --- | --- |
| P0 | `SiteManifest` Zod schema and loader | All five current sites load through manifests; duplicate domain/alias rejected in tests. |
| P0 | Generic site page and `VendorSiteShell` | A new iframe site needs no new `app/<site>/page.tsx`. |
| P0 | Canonical draw contract plus adapters | Existing `/wy.json`, JSONP and Kaijiang output pass fixture tests generated from one draw input. |
| P0 | `SiteDataBridge` / `site-bridge.js` | A fixture legacy HTML page renders configured prediction and draw data using selectors/events only. |
| P0 | Configured UI chrome | Logo/nav/footer/contact values render from manifest in React and DOM-slot modes. |
| P1 | Generic provider registry | `site-api-service` has no hard-coded site-key branch for standard providers. |
| P1 | Asset import/validation scripts | Import reports root-relative rewrites, remote origins, missing assets and collisions. |
| P1 | Browser/API smoke suite | Each manifest is tested for all enabled lottery types and defined aliases. |
| P1 | Strict build gate | `tsc --noEmit`, lint and manifest validation precede Docker build; disable ignored TS build errors. |
| P2 | Vendor common library strategy | Only after compatibility tests, extract versioned immutable shared copies or retain per-site copies deliberately. |

---

## 10. Verification Performed During This Audit

The current frontend type check and the focused registry/prediction compatibility contracts passed:

```powershell
pnpm --filter @liuhecai/frontend exec tsc --noEmit
node frontend/test/run-site-registry-contract.mjs
node frontend/test/run-prediction-modules-route-contract.mjs
```

These checks establish that the existing five-site registry and the legacy prediction identity compatibility route are internally consistent. They do **not** verify browser rendering, availability of external vendor dependencies, live backend data, Nginx domain/TLS setup, or the proposed manifest architecture, which has not yet been implemented.

## 11. Evidence References

- Central site registry and current five entries: `frontend/lib/sites.ts:40`.
- Context resolution, identity protection and success envelope: `frontend/lib/site-registry.ts:59`.
- Unified site service and remaining site-key branches: `frontend/lib/site-api-service.ts:63`.
- Canonical prediction types and normalization functions: `frontend/lib/prediction-contract.ts:4`, `frontend/lib/prediction-contract.ts:286`.
- Backend API client and environment base URL: `frontend/lib/backend-api.ts:41`, `frontend/lib/backend-api.ts:141`.
- Unified prediction endpoint: `frontend/app/api/sites/[siteKey]/prediction-modules/route.ts:11`.
- Registry render helper currently unused by production code: `frontend/lib/site-rendering.tsx:11`.
- Dedicated vendor page implementations: `frontend/app/twcaibawang/page.tsx:7`, `frontend/components/twjinniu/TwjinniuHomeClient.tsx:5`, `frontend/components/twcf888/Twcf888HomeClient.tsx:5`.
- `twcaibawang` direct, non-unified refresh calls: `frontend/components/twcaibawang/TwcaibawangHomeClient.tsx:1643`.
- Site-specific vendor calls: `frontend/public/vendor/twjinniu/index.html:486`, `frontend/public/vendor/twcf888.com/index.html:1681`.
- Deployment API environment: `docker-compose.yml:164`; Docker build: `Dockerfile.frontend:23`; TypeScript errors ignored by production build: `frontend/next.config.mjs:14`.
