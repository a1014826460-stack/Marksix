# Registry-Driven Multi-Site Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement registry-driven multi-site frontend APIs and first-party Traffic Events so all five public sites share a consistent extension and reporting architecture.

**Architecture:** Frontend site behavior is resolved through a typed Site Registry and Site Service layer. Unified `/api/sites/<siteKey>/...` routes delegate to shared service functions, while existing site-specific routes remain as compatibility forwarders. Traffic Events are stored in backend-managed tables and aggregated through dedicated admin endpoints.

**Tech Stack:** Next.js App Router, TypeScript, Python stdlib HTTP routes, SQLite/PostgreSQL compatibility helpers, pytest, pnpm TypeScript checking.

---

### Task 1: Backend Traffic Event Storage

**Files:**
- Create: `backend/src/database/schema/traffic.py`
- Modify: `backend/src/database/bootstrap.py`
- Modify: `backend/src/database/schema/indexes.py`
- Create: `backend/src/domains/traffic/__init__.py`
- Create: `backend/src/domains/traffic/service.py`
- Test: `backend/src/tests/unit/test_traffic_service.py`

- [x] **Step 1: Write failing tests for event insertion and privacy**

Create `backend/src/tests/unit/test_traffic_service.py` with tests that call `ensure_admin_tables()`, insert `site_page_view` and `api_compat_hit` events, assert raw IP is not persisted, and assert PV/UV aggregates by site.

- [x] **Step 2: Run traffic service tests and confirm failure**

Run: `python -m pytest backend/src/tests/unit/test_traffic_service.py -q`
Expected: FAIL because `domains.traffic` does not exist.

- [x] **Step 3: Add schema and service implementation**

Create `public_site_traffic_events` with fields from the design, hash IP before insert, validate event type, resolve managed site data when available, and aggregate overview/site/timeseries metrics.

- [x] **Step 4: Run traffic service tests and confirm pass**

Run: `python -m pytest backend/src/tests/unit/test_traffic_service.py -q`
Expected: PASS.

### Task 2: Backend Admin Traffic Routes

**Files:**
- Create: `backend/src/routes/admin_traffic_routes.py`
- Modify: `backend/src/app_http/server.py`
- Test: `backend/src/tests/unit/test_api_contract_admin_traffic_routes.py`

- [x] **Step 1: Write failing route contract tests**

Create tests that patch `domains.traffic.service` functions and assert these routes return JSON:
`/api/admin/traffic/overview`, `/api/admin/traffic/sites`, `/api/admin/traffic/timeseries`.

- [x] **Step 2: Run admin traffic route tests and confirm failure**

Run: `python -m pytest backend/src/tests/unit/test_api_contract_admin_traffic_routes.py -q`
Expected: FAIL because the route module does not exist.

- [x] **Step 3: Implement route module and register it**

Add `admin_traffic_routes.register(router)` in `backend/src/app_http/server.py`.

- [x] **Step 4: Run admin traffic route tests and confirm pass**

Run: `python -m pytest backend/src/tests/unit/test_api_contract_admin_traffic_routes.py -q`
Expected: PASS.

### Task 3: Frontend Site Registry and Services

**Files:**
- Modify: `frontend/lib/sites.ts`
- Create: `frontend/lib/site-registry.ts`
- Create: `frontend/lib/site-api-service.ts`
- Create: `frontend/lib/site-rendering.tsx`

- [x] **Step 1: Add typed registry without changing behavior**

Extend current site config with `renderMode` and `capabilities`, export helpers for all five site keys, and keep existing `getSiteConfig()` consumers working.

- [x] **Step 2: Add service functions**

Implement shared functions for `site-page`, `homepage-modules`, `article-detail`, `prediction-modules`, and traffic forwarding. Reuse existing backend-api, prediction adapter, and article provider functions.

- [x] **Step 3: Add render helpers**

Add a shared renderer for `legacy-shell`, `iframe-vendor`, and `react-home`, while preserving existing large UI components.

- [x] **Step 4: Run TypeScript check**

Run: `pnpm --filter @liuhecai/frontend exec tsc --noEmit`
Expected: PASS or only unrelated pre-existing failures; if failures are caused by this task, fix them before continuing.

### Task 4: Unified Frontend API Routes and Forwarders

**Files:**
- Create: `frontend/app/api/sites/[siteKey]/site-page/route.ts`
- Create: `frontend/app/api/sites/[siteKey]/homepage-modules/route.ts`
- Create: `frontend/app/api/sites/[siteKey]/article-detail/route.ts`
- Create: `frontend/app/api/sites/[siteKey]/prediction-modules/route.ts`
- Create: `frontend/app/api/sites/[siteKey]/traffic-events/route.ts`
- Modify: `frontend/app/api/twjinniu/site-page/route.ts`
- Modify: `frontend/app/api/twjinniu/homepage-modules/route.ts`
- Modify: `frontend/app/api/twcf888/site-page/route.ts`
- Modify: `frontend/app/api/twcf888/homepage-modules/route.ts`
- Modify: `frontend/app/api/vendor/article-detail/route.ts`
- Modify: `frontend/app/api/prediction-modules/route.ts`

- [x] **Step 1: Add unified route handlers**

Each route resolves `siteKey`, calls `frontend/lib/site-api-service.ts`, returns the stable envelope, and uses `{ ok:false, error }` for failures.

- [x] **Step 2: Convert compatibility routes into forwarders**

Keep legacy response shapes where needed, but source data from shared service functions. Track `api_compat_hit` for the forwarders.

- [x] **Step 3: Run TypeScript check**

Run: `pnpm --filter @liuhecai/frontend exec tsc --noEmit`
Expected: PASS or only unrelated pre-existing failures; if failures are caused by this task, fix them before continuing.

### Task 5: Frontend Tracker and Page Integration

**Files:**
- Create: `frontend/components/SiteTrafficTracker.tsx`
- Modify: `frontend/app/legacy-shell/page.tsx`
- Modify: `frontend/app/twsaimahui/page.tsx`
- Modify: `frontend/app/twcaibawang/page.tsx`
- Modify: `frontend/app/twjinniu/page.tsx`
- Modify: `frontend/app/twcf888/page.tsx`
- Modify: article pages under `frontend/app/twjinniu` and `frontend/app/twcf888`

- [x] **Step 1: Implement non-blocking tracker**

Use `navigator.sendBeacon` when available and `fetch(..., { keepalive: true })` as fallback. Generate or reuse a local `visitor_id`.

- [x] **Step 2: Add page and article events**

Record `site_page_view`, `vendor_page_view`, and `article_view` events in the appropriate pages without changing UI.

- [x] **Step 3: Run TypeScript check**

Run: `pnpm --filter @liuhecai/frontend exec tsc --noEmit`
Expected: PASS or only unrelated pre-existing failures; if failures are caused by this task, fix them before continuing.

### Task 6: Documentation and Verification

**Files:**
- Modify: `frontend/README.md`
- Modify: `frontend/docs/frontend-api-contract.md`
- Modify: `frontend/docs/prediction-contract-guide.md`

- [x] **Step 1: Update docs**

Document `/api/sites/<siteKey>/...`, registry-driven onboarding, legacy forwarders, and Traffic Events.

- [x] **Step 2: Run focused backend tests**

Run: `python -m pytest backend/src/tests/unit/test_traffic_service.py backend/src/tests/unit/test_api_contract_admin_traffic_routes.py -q`
Expected: PASS.

- [x] **Step 3: Run frontend TypeScript check**

Run: `pnpm --filter @liuhecai/frontend exec tsc --noEmit`
Expected: PASS or report exact unrelated pre-existing failures.

- [x] **Step 4: Audit spec coverage**

Check every requirement in `docs/superpowers/specs/2026-06-28-registry-driven-multi-site-frontend-design.md` against implemented files and verification output.
