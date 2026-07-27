# Taiwan Future Draw Scheduled Autofill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow administrators to configure a daily UTC schedule that keeps Taiwan lottery future draws at a requested count without manual entry.

**Architecture:** Persist three validated settings in `system_config`; expose them through authenticated draw-admin routes. Reuse durable scheduler task tables for one task per UTC date and invoke the existing locked Taiwan future-draw domain service only when the configured target is short.

**Tech Stack:** Python 3, PostgreSQL/SQLite compatibility layer, custom HTTP router, React/TypeScript, pnpm, pytest.

---

### Task 1: Settings Contract and Persistence

**Files:**
- Modify: `backend/src/runtime_config.py`
- Modify: `backend/src/domains/lottery/service.py`
- Test: `backend/src/tests/unit/test_admin_crud_lottery_compat.py`

- [ ] Add defaults for enabled, target count and UTC `HH:mm`, then write failing tests for default values and invalid setting payloads.
- [ ] Implement strict settings parsing and persistent reads/writes using existing config-history aware helpers.
- [ ] Run `python -m pytest backend/src/tests/unit/test_admin_crud_lottery_compat.py -q`.

### Task 2: Admin Settings API

**Files:**
- Modify: `backend/src/routes/admin_draw_routes.py`
- Modify: `backend/src/tests/unit/test_api_contract_admin_routes.py`
- Modify: `backend/src/tests/unit/test_rbac_enforcement.py`

- [ ] Write failing route-contract tests for reading, saving, validation and non-admin rejection.
- [ ] Register exact settings routes before draw-detail routing and implement authenticated handlers.
- [ ] Run the route and RBAC test modules.

### Task 3: Durable Scheduled Execution

**Files:**
- Modify: `backend/src/domains/scheduler/service.py`
- Modify: `backend/src/crawler/scheduler.py`
- Modify: `backend/src/tests/unit/test_scheduler_domain_service.py`
- Modify: `backend/src/tests/unit/test_scheduler_task_loop_runs.py`

- [ ] Write failing tests for UTC timing, missed-run catch-up, same-day idempotency and task execution.
- [ ] Add the task type, date-scoped key, scheduling helper and current task summary lookup.
- [ ] Ensure worker startup and polling schedule it; execute the domain auto-fill only when enabled and short.
- [ ] Run scheduler unit tests.

### Task 4: Management Page

**Files:**
- Modify: `backend/features/draws/DrawsPage.tsx`
- Modify: `backend/features/draws/draws-auto-fill-contract.mjs`

- [ ] Extend the contract test with the setting endpoints and visible controls, then observe its failure.
- [ ] Implement the settings card, loading and saving states, and server-provided schedule status.
- [ ] Run `pnpm --dir backend test:draws-auto-fill-contract` and the relevant backend test suite.
