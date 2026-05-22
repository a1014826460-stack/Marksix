# twcaibawang.com Integration Plan

## Goal

Integrate `frontend/public/vendor/twcaibawang.com/` into the current multi-site project with the least risky rollout path first, while keeping room for later migration of prediction modules to a Next.js data-driven implementation.

This plan is based on the current project structure:

- Frontend site config: `frontend/lib/sites.ts`
- Host-based entry routing: `frontend/proxy.ts`
- Public frontend compatibility routes: `frontend/app/api/**`
- Backend public data routes: `backend/src/routes/public_routes.py`
- Backend site isolation: `backend/src/app_http/site_context.py`
- Site-specific prediction blueprints: `backend/src/domains/prediction/site_module_blueprints.py`

## Key Conclusion

`twcaibawang.com` is not a full React/Next frontend. It is a legacy static vendor site with a small number of runtime data dependencies:

- `GET /wy.json`
- `GET /index/ajax/ttklsjl`
- `GET /index/index/history.html` or `wylhc.html`
- `GET /index_files/pub.js`
- `GET /index_files/gg.js`

That means the safest rollout is:

1. Reuse the existing multi-site shell and add `twcaibawang` as a new site.
2. Add a small compatibility layer in Next.js for the old runtime endpoints.
3. Keep the vendor static pages working first.
4. Migrate prediction modules later, module by module, to a Next.js data-driven implementation.

Do not start by rewriting the full site into React.

## Existing Architecture Reuse

## 1. Site registration and host mapping

The current frontend already supports host-aware site selection.

Relevant files:

- `frontend/lib/sites.ts`
- `frontend/proxy.ts`
- `frontend/app/page.tsx`

Reuse pattern:

- Add one more site config entry for `twcaibawang`
- Bind domain names to that site entry
- Route the matched host to a site-specific entry page

Recommended config fields:

- `siteKey: "twcaibawang"`
- `routePath: "/twcaibawang"`
- `vendorIndexPath: "/vendor/twcaibawang.com/index.html"`
- `legacyPublicBasePath: "/vendor/twcaibawang.com"`
- `domains: ["twcaibawang.com", "www.twcaibawang.com"]`
- `defaultLotteryTypeId`: use the final backend site config value, likely `1`
- `defaultWebId`: use the final backend site config value from `managed_sites`

Important:

- Do not infer `defaultWebId` from frontend files.
- Confirm the real `web_id` from `managed_sites`.
- Do not confuse `managed_sites.id` with `web_id`.

## 2. Public compatibility API layer

The current project already uses Next.js routes as the external frontend API layer.

Relevant files:

- `frontend/app/api/latest-draw/route.ts`
- `frontend/app/api/next-draw-deadline/route.ts`
- `frontend/app/api/draw-history/route.ts`
- `frontend/app/api/lottery-data/route.ts`
- `frontend/app/api/kaijiang/[[...path]]/route.ts`

Reuse pattern:

- Keep Python backend public routes as the data source
- Use Next.js routes to convert backend JSON into the old vendor site format
- Keep browser requests same-origin
- Avoid exposing Python backend address directly

## 3. Backend public data source

The current backend already provides the main public data building blocks.

Relevant files:

- `backend/src/routes/public_routes.py`
- `backend/src/public/api.py`
- `backend/API.md`

Directly reusable backend APIs:

- `GET /api/public/latest-draw`
- `GET /api/public/next-draw-deadline`
- `GET /api/public/draw-history`
- `GET /api/public/site-page`

These are enough to power:

- current draw area
- next draw deadline
- draw history page
- a future React/Next prediction-module page

## 4. Site-specific prediction blueprint

The current backend already supports site-specific module sets.

Relevant file:

- `backend/src/domains/prediction/site_module_blueprints.py`

Reuse pattern:

- add a `twcaibawang` blueprint only after the real frontend module mapping is confirmed
- keep it isolated from other sites
- do not alter other site route behavior to force compatibility

This is the same approach already used for `twsaimahui`.

## Proposed Integration Strategy

## Phase 1: Minimum viable integration

Goal:

- make `twcaibawang.com` load as a working site in the current system
- preserve the vendor site structure
- supply only the runtime endpoints it truly needs

Frontend tasks:

1. Add site entry in `frontend/lib/sites.ts`
2. Update `frontend/proxy.ts` host rewrite rules
3. Add `frontend/app/twcaibawang/page.tsx`
4. Serve vendor files from `frontend/public/vendor/twcaibawang.com/**`
5. Add compatibility routes for old runtime endpoints

Suggested new routes:

- `frontend/app/wy.json/route.ts`
- `frontend/app/index/ajax/ttklsjl/route.ts`
- `frontend/app/index/index/history.html/route.ts`
- `frontend/app/index_files/pub.js/route.ts`
- `frontend/app/index_files/gg.js/route.ts`

Backend tasks:

1. Add or verify `managed_sites` record
2. Confirm real values for:
   - `domain`
   - `web_id`
   - `lottery_type_id`
   - `enabled`
3. Verify public draw APIs return correct source data for that lottery type

Expected result:

- `index.html` loads
- `wy.html` updates current draw every 2 seconds
- `wylhc.html` loads history data
- missing external scripts no longer break the page

## Phase 2: Stable compatibility and cleanup

Goal:

- reduce brittleness in the vendor runtime
- move external dependencies under project control

Tasks:

1. Replace or stub missing `pub.js`
2. Replace or stub missing `gg.js`
3. Remove any remaining dependence on remote vendor assets if possible
4. Add host-aware logic to compatibility routes so root-level legacy paths resolve correctly for this site
5. Add smoke tests for:
   - `/wy.json`
   - `/index/ajax/ttklsjl`
   - `/api/latest-draw`
   - `/api/draw-history`

Notes:

- `pub.js` and `gg.js` should be treated as site-specific compatibility assets, not global shared API contracts.
- If their original behavior is only cosmetic, a minimal stub is preferable to cloning opaque old code.

## Phase 3: Prediction module migration

Goal:

- stop treating prediction sections as static HTML
- use real backend prediction data for the site

Tasks:

1. Audit the prediction-related blocks in `index.html`
2. Map each visible block to:
   - a real `mode_id`
   - a real `mechanism_key`
   - a real source route in current backend/frontend compatibility APIs
3. Add `twcaibawang` site-specific blueprint in `backend/src/domains/prediction/site_module_blueprints.py`
4. Build the module display in Next.js using `GET /api/lottery-data`
5. Keep static article pages and image pages as vendor content until there is a real need to redesign them

Recommended UI strategy:

- keep the top-level site shell and static detail pages unchanged at first
- rewrite only:
  - latest draw block
  - draw history page
  - prediction module area

This matches the current project rule: do not rewrite the whole legacy JS site in one pass.

## Detailed Module and File Impact

## Frontend files to modify

### Existing files

- `frontend/lib/sites.ts`
  - register `twcaibawang`
  - set route path, domains, vendor base, default ids

- `frontend/proxy.ts`
  - add host match for `twcaibawang.com`
  - rewrite `/` to `/twcaibawang` when host matches

- `frontend/app/page.tsx`
  - no structural change required if host rewrite remains the entry mechanism

- `frontend/app/api/latest-draw/route.ts`
  - can likely be reused as-is

- `frontend/app/api/draw-history/route.ts`
  - can likely be reused as-is
  - may need small parameter normalization if this site uses a different default lottery type

- `frontend/app/api/lottery-data/route.ts`
  - reusable for future React prediction modules

- `frontend/app/api/kaijiang/[[...path]]/route.ts`
  - only extend if some later prediction blocks require old `kaijiang` route semantics

### New frontend files

- `frontend/app/twcaibawang/page.tsx`
  - site entry page

- `frontend/app/wy.json/route.ts`
  - transform current backend draw payload into legacy array format

- `frontend/app/index/ajax/ttklsjl/route.ts`
  - output `var historyAO = ...;`

- `frontend/app/index/index/history.html/route.ts`
  - optional alias to `wylhc.html` or redirect/rewrite

- `frontend/app/index_files/pub.js/route.ts`
  - compatibility script or stub

- `frontend/app/index_files/gg.js/route.ts`
  - compatibility script or stub

## Backend files to modify

### Likely unchanged in Phase 1

- `backend/src/routes/public_routes.py`
- `backend/src/app_http/site_context.py`

These are already sufficient if the site is configured correctly.

### Likely modified in Phase 3

- `backend/src/domains/prediction/site_module_blueprints.py`
  - add `twcaibawang` blueprint

- potentially route or service files only if:
  - a required prediction block does not match any current API shape
  - a new site-specific compatibility path is needed

## API Contract Assessment

## 1. Can the provided frontend API document be used directly?

Yes, but only as a compatibility target for the legacy site.

It should not be treated as the internal canonical API contract of the project.

Use it for:

- route names
- response shape conversion
- JSONP expectations
- vendor page compatibility

Do not use it as the system-standard contract for:

- backend public API design
- prediction API design
- authentication rules
- error handling standards

## 2. Interface design assessment

### Reasonable parts

- It correctly narrows the old site runtime to a very small set of critical endpoints.
- `wy.json` is simple and easy to generate from existing public APIs.
- `ttklsjl` clearly documents JSONP expectations and field names used by `wylhc.html`.

### Weak parts

- `wy.json` wraps data as an array and encodes multiple fields as CSV strings.
- history uses JSONP and a global variable, which is a legacy browser pattern, not a modern API pattern.
- there is no unified error payload.
- there is no versioning.
- there is no explicit cache policy beyond the old frontend polling pattern.

Conclusion:

- suitable as a legacy compatibility spec
- unsuitable as the new canonical application API

## 3. Data format compatibility with current system

Current system:

- structured JSON
- normalized public API outputs
- site-aware resolution via host or `site_id`

Legacy doc:

- CSV-packed values
- array wrapper for single draw payload
- JSONP script output for history

Compatibility result:

- compatible after transformation in Next.js
- not directly compatible without an adapter

## 4. Authentication compatibility

Old vendor runtime endpoints:

- should remain public
- should not require login

Current backend reality:

- public draw endpoints are already public
- prediction generation endpoints require auth and often admin role

Conclusion:

- draw display is compatible
- prediction execution is not directly compatible and should stay server-controlled

## Whether To Unify the New Site Under Next.js

## Recommendation

Yes for API unification.
No for immediate full-page React rewrite.

The best balance is:

- unify all external runtime requests through Next.js routes
- progressively replace prediction modules with Next.js components
- keep the rest of the vendor site static until needed

## Why this is necessary

Benefits:

- same deployment and host-routing model as current sites
- no direct exposure of Python backend origin
- no CORS complexity for browser requests
- easier host-based multi-site isolation
- easier field transformation from modern backend JSON to legacy frontend payloads
- easier phased migration

## Main advantages

- Fastest path to a working site
- Low risk to current online sites
- Clear separation:
  - Python backend = source of truth
  - Next.js = frontend compatibility and transformation layer
- Easy to migrate one module at a time

## Main disadvantages

- temporary dual model:
  - vendor static pages
  - Next.js compatibility routes
- old pages still carry static content debt
- some compatibility routes are root-style paths and need careful host-aware behavior

## Why full React migration should wait

- this vendor package is not API-driven in most sections
- many pages are static articles or image pages
- whole-site rewrite would cost much more than the business value of the initial integration
- prediction modules can be migrated independently first

## Prediction Module Support Matrix

## A. Features that current backend/public frontend APIs can support directly

These can be implemented now without new backend domain logic.

### Draw-related

- latest draw display
  - source: `GET /api/public/latest-draw`
  - frontend adapter: `GET /api/latest-draw`

- next draw deadline / countdown
  - source: `GET /api/public/next-draw-deadline`
  - frontend adapter: `GET /api/next-draw-deadline`

- draw history list
  - source: `GET /api/public/draw-history`
  - frontend adapter: `GET /api/draw-history`

### Aggregated site page data

- site metadata
- active prediction modules
- recent module history rows

Source:

- `GET /api/public/site-page`
- frontend adapter: `GET /api/lottery-data`

### Prediction data operations already present in backend

- site prediction module sync
- single module generation
- bulk generation
- historical backfill

Source:

- `/api/admin/sites/{site_id}/prediction-modules/*`
- `/api/admin/backfill-predictions`

These are backend/admin capabilities and can support site operations, but they are not public frontend endpoints.

## B. Features that need a new compatibility route, but not new backend core logic

- `GET /wy.json`
- `GET /index/ajax/ttklsjl`
- `GET /index/index/history.html`
- `GET /index_files/pub.js`
- `GET /index_files/gg.js`

These are adapter-layer tasks.

## C. Features that likely need new development or extension

### Site-specific prediction module mapping

Need:

- confirm which homepage blocks are real prediction modules
- map each block to `mode_id` and `mechanism_key`
- build a `twcaibawang` site-specific module blueprint

Why:

- current site frontend is mostly static HTML
- static block names do not automatically imply a valid current backend payload

### Possible legacy `kaijiang` compatibility expansion

Need only if the site later requires old route semantics for prediction blocks.

Potential work:

- extend `frontend/app/api/kaijiang/[[...path]]/route.ts`
- add site-aware branch logic
- normalize payloads without breaking other sites

### Content/article management

Static pages like:

- `11169.html` to `11184.html`
- `4873.html` to `4879.html`
- image/gallery resources

If these must become editable from backend, new APIs are needed:

- article list
- article detail
- image gallery list
- image asset metadata
- optional admin CRUD

This is outside the scope of basic site integration.

## Recommended Development Checklist

## Phase 1 checklist

1. Confirm `managed_sites` row for `twcaibawang`
2. Add site config in `frontend/lib/sites.ts`
3. Add host rewrite in `frontend/proxy.ts`
4. Add `/twcaibawang` page entry
5. Add `/wy.json` route
6. Add `/index/ajax/ttklsjl` route
7. Add `pub.js` and `gg.js` compatibility handling
8. Verify `wy.html`, `wylhc.html`, `index.html` load without runtime errors

## Phase 2 checklist

1. Remove or replace remote script dependence
2. Add route-level smoke validation
3. Confirm caching behavior and `no-store` where needed
4. Confirm correct site isolation by host
5. Verify no regressions for `/` and `/twsaimahui`

## Phase 3 checklist

1. Audit homepage prediction blocks
2. Build `twcaibawang` module mapping table
3. Add backend site blueprint
4. Expose module area through `GET /api/lottery-data`
5. Implement Next.js prediction module rendering
6. Keep static article pages vendor-based unless business requires CMS support

## Risks and Attention Points

- Root-level compatibility paths can collide across sites if they are not host-aware.
- `web_id` must come from backend site config, not from guesswork.
- `lottery_type_id` must be confirmed from backend site config, even if the vendor text suggests Hong Kong.
- JSONP output must match old variable naming exactly for `wylhc.html`.
- Do not break other site compatibility routes while adding site-specific logic.
- Do not expose `/api/predict/{mechanism}` directly to public frontend pages as a public generation endpoint.
- Do not attempt full React migration before the module mapping is complete.

## Final Recommendation

For `twcaibawang.com`, the correct implementation path is:

1. Integrate it as a new site in the existing multi-site Next.js shell.
2. Add only the minimum old-runtime compatibility routes needed by the vendor package.
3. Treat prediction modules as a second-stage migration problem.
4. Use current backend public APIs as the source of truth.
5. Move prediction-module rendering to Next.js gradually, not the whole site at once.

This approach best matches the current repository architecture, minimizes cross-site regression risk, and gives a clean path from legacy compatibility to maintainable data-driven modules.
