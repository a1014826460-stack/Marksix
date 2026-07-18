# Site Module Authorization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make enabled `site_prediction_modules` rows the enforced authorization source for site-private, vendor and legacy prediction reads without changing API payload contracts.

**Architecture:** Frontend site contexts are path-owned and use explicit fixed site/web identifiers. Backend prediction repository helpers resolve enabled mode IDs by `web_id`; vendor and legacy facades use those helpers to produce their existing empty-data shapes. A separate audit/reconciliation domain service compares declarative blueprints, vendor docs and runtime rows, while an explicit script performs safe status-only cleanup.

**Tech Stack:** TypeScript/Next.js route helpers, Python 3, PostgreSQL/SQLite `ConnectionAdapter`, pytest, existing vendor and legacy compatibility APIs.

---

### Task 1: Lock Site-Private Context to the Path Site

**Files:**
- Modify: `frontend/lib/sites.ts`
- Modify: `frontend/lib/site-registry.ts`
- Modify: `frontend/test/site-registry-contract.ts`

- [x] Add a failing test that passes `site_id=5&web=5` to `resolveSiteApiContext("twjinniu", ...)` and expects the fixed twjinniu identifiers.
- [x] Run the TypeScript contract check and confirm the assertion fails because query parameters currently override the context.
- [x] Add `defaultSiteId` to each registered site and construct `siteId`/`webId` exclusively from the path site configuration.
- [x] Re-run the contract check and verify the existing no-query behavior remains unchanged.

### Task 2: Add Enabled-Module Repository Checks

**Files:**
- Modify: `backend/src/domains/prediction/repository.py`
- Test: `backend/src/tests/unit/test_site_prediction_module_authorization.py`

- [x] Add failing SQLite tests for resolving a managed site by `web_id`, accepting an enabled `mode_id`, and rejecting disabled or missing rows.
- [x] Run the new test and confirm the repository functions are absent.
- [x] Add focused repository functions that return only mode identifiers and booleans; do not expose prediction rows or write SQL outside the repository.
- [x] Re-run the test file.

### Task 3: Preserve Empty Vendor and Legacy Responses for Disabled Modules

**Files:**
- Modify: `backend/src/vendor/homepage_modules.py`
- Modify: `backend/src/legacy/api.py`
- Modify: `backend/src/legacy/frontend_compat.py`
- Test: `backend/src/tests/unit/test_site_prediction_module_authorization.py`

- [x] Add failing tests proving a vendor composite with a disabled source returns the existing wrapper and `history: []`.
- [x] Add failing tests proving `/legacy/module-rows` preserves metadata with `rows: []`, and kaijiang preserves `{ "data": [] }` when `web` specifies a disabled source mode.
- [x] Add an internal authorization predicate shared by these facades; only enforce it when an explicit web is supplied.
- [x] Run the focused suite and existing vendor/legacy contract tests.

### Task 4: Reconcile Dedicated Runtime Module Sets

**Files:**
- Modify: `backend/src/domains/prediction/generation_service.py`
- Create: `backend/src/domains/prediction/site_module_audit.py`
- Create: `backend/scripts/reconcile_site_prediction_modules.py`
- Modify: `backend/src/domains/prediction/site_module_blueprints.py`
- Modify: `frontend/public/vendor/twcf888.com/TWCF888_PREDICTION_MODULES.md`
- Test: `backend/src/tests/unit/test_site_prediction_module_audit.py`

- [x] Add failing tests for status-only reconciliation of site 5-8 and for `twcf888` document/blueprint agreement.
- [x] Implement reconciliation as an explicit service that enables blueprint IDs and sets only surplus active rows to `status=0`.
- [x] Update the twcf888 document to list `51` and `197`, matching its existing live configuration declaration.
- [x] Add a script that defaults to audit-only and requires `--apply` for reconciliation; no connection string is printed.
- [x] Run the script in audit-only mode, then apply it to the configured database and re-run the audit. On 2026-07-19, only site 5 changed: six surplus mode IDs were set to `status=0`.

### Task 5: Continuous Cross-Layer Audit and Documentation

**Files:**
- Modify: `backend/CLAUDE.md`
- Modify: `backend/docs/API.md`
- Modify: `backend/README_CN.md`
- Test: `backend/src/tests/unit/test_site_prediction_module_audit.py`

- [x] Add tests that compare twcaibawang vendor composite source IDs and twjinniu hardcoded homepage IDs to their dedicated blueprints.
- [x] Document the database-authority rule, explicit reconciliation command, query override rule, and compatibility empty responses.
- [x] Run focused Python tests, frontend contract verification, static compile, then the full backend pytest suite (`412 passed, 10 skipped`).

### Task 6: Resolve Compatibility-Route Site Identity Explicitly

**Files:**
- Modify: `frontend/lib/site-registry.ts`
- Modify: `frontend/app/api/prediction-modules/route.ts`
- Modify: `frontend/test/run-site-registry-contract.mjs`
- Create: `frontend/test/run-prediction-modules-route-contract.mjs`
- Modify: `frontend/test/site-registry-contract.ts`
- Modify: `frontend/docs/prediction-contract-guide.md`
- Modify: `frontend/README.md`

- [x] Add a failing frontend contract test proving `site_id=5` resolves the registered `twcaibawang` context and conflicting `site_key=twjinniu&site_id=5` is rejected.
- [x] Add a registry helper that resolves the compatibility route from one registered identity source and rejects conflicts.
- [x] Route `/api/prediction-modules` through the helper, retaining its success payload field names and ordering.
- [x] Add a route-level contract that preserves the existing `400` missing-identity envelope, existing `500` conflict envelope, and correct `site_id` service context.
- [x] Run the frontend contract runners and TypeScript check.
