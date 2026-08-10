# Unified Forced Announcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a backend-managed, Beijing-time, versioned forced announcement that appears on every public Site and is dismissible only per session or by browser-local acknowledgement.

**Architecture:** Store announcements independently from `managed_sites`, resolve one active announcement through the existing Site context, and inject a single static runtime into every Vendor Site through the common HTML injection path. The server sanitizes HTML and enforces conflict-free Site/time applicability; the browser never treats dismissal as a server-side acknowledgement.

**Tech Stack:** Python 3.12, PostgreSQL/SQLite-compatible schema migrations, existing HTTP router/admin React UI, static JavaScript, pytest, Node test tooling.

---

## File map

- Create `backend/src/database/schema/forced_announcements.py`: tables and indexes.
- Modify `backend/src/database/versioned_migrations.py`: migration and version increment.
- Create `backend/src/domains/announcements/service.py`: validation, Beijing clock, scope collision, sanitization and public/admin projections.
- Create `backend/src/routes/admin_forced_announcement_routes.py`: authenticated CRUD routes.
- Modify `backend/src/routes/public_routes.py`: public effective-announcement route.
- Modify `backend/src/app_http/server.py` and route registration module: register routes.
- Create `backend/features/forced-announcements/ForcedAnnouncementsPage.tsx`: management UI.
- Modify backend-admin navigation/types as required: route and menu registration.
- Create `frontend/public/vendor/_shared/forced-announcement.js`: session/local acknowledgement and modal runtime.
- Modify shared Vendor HTML injection/build script and affected fixture tests: load the shared runtime on every public page.
- Create focused backend and frontend tests under existing unit/test directories.

### Task 1: Schema and domain contract

- [ ] Write failing tests for active Beijing-time selection, selected/all Site scope, overlap rejection, version replacement and HTML sanitization.
- [ ] Run the focused pytest target; observe missing module/function failure.
- [ ] Add schema tables, indexes and versioned migration; implement service contract using explicit transaction scopes.
- [ ] Re-run focused tests; verify pass.
- [ ] Commit schema/domain change.

### Task 2: Public and admin HTTP contracts

- [ ] Write failing route tests proving public route returns only active sanitized fields and admin CRUD validates scope/time conflicts.
- [ ] Run focused pytest target; observe route failure.
- [ ] Register authenticated admin CRUD and public Site-context route; wire the backend-admin management screen.
- [ ] Re-run focused tests and admin frontend type/lint checks; verify pass.
- [ ] Commit HTTP/admin change.

### Task 3: Shared browser runtime

- [ ] Write failing Node/browser-unit tests for session close, local acknowledgement, new-version re-display and no overlay-close acknowledgement.
- [ ] Run the focused frontend test; observe missing runtime failure.
- [ ] Implement isolated `forced-announcement.js`; use only server-sanitized HTML and scoped storage keys.
- [ ] Re-run runtime tests; verify pass.
- [ ] Commit runtime change.

### Task 4: All-public-page injection

- [ ] Write failing injection inventory test proving every supported Vendor Site document loads `forced-announcement.js` exactly once.
- [ ] Run the inventory test; observe omissions.
- [ ] Extend the existing common Vendor injection mechanism rather than editing site pages manually.
- [ ] Re-run inventory and representative page tests; verify pass.
- [ ] Commit injection change.

### Task 5: Release validation

- [ ] Run focused announcement, migration, API contract and frontend tests.
- [ ] Run `pwsh -File .\skills\prediction-release-review\scripts\run-regression.ps1`.
- [ ] Inspect public responses and tests for Future Issue fields, logs or unsafe HTML; correct any finding before approval.
- [ ] Commit final test/document updates.
