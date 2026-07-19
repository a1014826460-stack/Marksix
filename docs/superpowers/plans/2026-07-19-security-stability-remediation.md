# Security and Stability Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate confirmed credential exposure, enforce least-privilege administration, bound untrusted requests, protect sensitive data, and make operational work durable without changing established API success payloads.

**Architecture:** Security controls are centralized at the transport and authorization boundaries, while durable work moves from process memory to the existing scheduler task tables. Configuration and generated-prediction contracts remain compatible: new protection primarily returns existing error envelopes or improves internal persistence and observability.

**Tech Stack:** Python 3 stdlib HTTP server, PostgreSQL/psycopg, Next.js/TypeScript, Docker Compose/Nginx, pytest, pnpm TypeScript checks.

---

## Risk Order

1. Remove committed secrets and require environment/secret-file injection.
2. Limit request size/rate/CORS and redact sensitive values before logs or responses.
3. Enforce RBAC and site-level authorization for all administrative mutations and secret reads.
4. Persist manually requested background work and run it through the durable scheduler lifecycle.
5. Replace startup DDL with versioned migrations; make backup/restore observable and bounded.
6. Complete scheduler and prediction-domain decomposition while retaining API contracts.

## Task 1: Credential Eradication and Secret Scan

**Files:**
- Modify: `backend/scripts/restart-backend.ps1`
- Modify: `ops/frp-target-b/frpc.toml`
- Modify: `ops/frp-target-b/install-frpc-target-b.ps1`
- Modify: `backend/src/deprecated/tools/generate_missing_types.py`
- Modify: `backend/src/deprecated/tools/repair_created_mode_payload_197.py`
- Modify: `backend/src/tests/brain_teaser_image_generator.py`
- Create: `scripts/check-no-secrets.ps1`
- Modify: `.env.example`
- Modify: `DEPLOY.md`
- Test: `backend/src/tests/unit/test_secret_hygiene.py`

- [x] Add a failing repository scan test that rejects known DSN password and FRP token patterns in tracked source files.
- [x] Replace every plaintext secret with required environment variables or explicitly ignored local secret files; do not log DSNs.
- [x] Add a PowerShell scan command to CI/deployment documentation and verify it passes.
- [ ] Rotate the currently exposed production credentials outside the repository and record only the rotation procedure, never the new value.

## Task 2: HTTP Trust Boundary

**Files:**
- Modify: `backend/src/app_http/request_context.py`
- Modify: `backend/src/app_http/response.py`
- Create: `backend/src/app_http/security.py`
- Modify: `backend/src/app_http/server.py`
- Modify: `backend/src/routes/public_routes.py`
- Modify: `backend/src/routes/vendor_routes.py`
- Modify: `backend/src/routes/legacy_routes.py`
- Modify: `deploy/nginx.conf`
- Test: `backend/src/tests/unit/test_http_security_boundary.py`

- [x] Write failing tests for oversized JSON, malformed or negative content lengths, strict admin CORS, and clamped public history limits.
- [x] Add one request-size parser and one CORS policy helper; keep response JSON payloads unchanged.
- [~] Apply bounded integer parsing to public/vendor/legacy/admin list endpoints and Nginx connection/rate limits.
- [x] Verify existing API contract tests plus the new boundary tests.

## Task 3: Sensitive Data Redaction and Configuration Safety

**Files:**
- Create: `backend/src/security/redaction.py`
- Modify: `backend/src/app_http/router.py`
- Modify: `backend/src/logger.py`
- Modify: `backend/src/runtime_config.py`
- Modify: `backend/src/routes/admin_config_routes.py`
- Test: `backend/src/tests/unit/test_sensitive_data_redaction.py`

- [x] Write failing tests proving passwords, bearer tokens, captcha codes, future truth fields, and secret configuration values never enter error logs or read responses.
- [x] Redact sensitive request/log structures recursively before logging.
- [x] Make secret configuration values write-only and make the legacy `include_secrets` flag safe without changing list envelope fields.
- [x] Run regression tests for config and log contracts.

### Captcha reliability follow-up

- [x] Move captcha/lockout table setup from request handlers into auth schema bootstrap so `/api/auth/captcha` never runs DDL per refresh.
- [x] Preserve the existing `{ image, expires_in_seconds }` captcha response contract and remove insecure default credentials from the login form/documented examples.

## Task 4: RBAC and Site Permission Enforcement

**Files:**
- Modify: `backend/src/database/schema/auth.py`
- Modify: `backend/src/database/schema/sites.py`
- Modify: `backend/src/database/bootstrap.py`
- Modify: `backend/src/domains/users/service.py`
- Modify: `backend/src/domains/sites/permissions.py`
- Modify: `backend/src/app_http/auth.py`
- Modify: `backend/src/routes/admin_user_routes.py`
- Modify: `backend/src/routes/admin_config_routes.py`
- Modify: `backend/src/routes/admin_alert_routes.py`
- Modify: `backend/src/routes/admin_crawler_routes.py`
- Modify: `backend/src/routes/admin_lottery_routes_extra.py`
- Modify: `backend/src/routes/admin_log_routes.py`
- Modify: `backend/src/routes/admin_site_routes.py`
- Test: `backend/src/tests/unit/test_rbac_enforcement.py`

- [x] Write failing tests for role validation, super-admin-only user/config operations, site-scoped operator rejection, and preserving at least one active super-admin.
- [x] Add stable role validation and site permission persistence.
- [x] Add route guards for every high-risk admin mutation/read, preserving success response structures.
- [x] Verify all existing admin API contracts and new RBAC tests.

## Task 5: Durable Manual Jobs and Scheduler Separation

**Files:**
- Modify: `backend/src/domains/scheduler/service.py`
- Modify: `backend/src/domains/scheduler/repository.py`
- Modify: `backend/src/jobs/handlers.py`
- Modify: `backend/src/routes/common.py`
- Modify: `backend/src/routes/job_routes.py`
- Modify: `backend/src/app_http/server.py`
- Create: `backend/src/scheduler_worker.py`
- Modify: `docker-compose.yml`
- Test: `backend/src/tests/unit/test_durable_background_jobs.py`

- [x] Write failing tests for restart-safe job lookup, idempotent enqueue, and worker acquisition.
- [x] Persist job metadata/result-safe summaries in scheduler tables and expose existing job response shape from durable records.
- [x] Move scheduler startup into a dedicated worker command/service; API process no longer starts timers. The worker owns the complete legacy timer lifecycle (crawl, open, precise checks, missed-task recovery) and stops it on SIGTERM/SIGINT.
- [x] Guard the worker lifecycle with an exclusive renewable lease, and ensure Taiwan precise-open work is enqueued only through the durable task path (no duplicate in-memory Taiwan timer).
- [ ] Add PostgreSQL integration coverage for task acquisition and recovery.

## Task 6: Versioned Migration and Backup Hardening

**Files:**
- Create: `backend/src/database/versioned_migrations.py`
- Modify: `backend/src/database/bootstrap.py`
- Modify: `backend/src/app_http/server.py`
- Modify: `backend/src/crawler/postgres_backup.py`
- Modify: `docker-compose.yml`
- Modify: `DEPLOY.md`
- Test: `backend/src/tests/integration/test_versioned_migrations.py`
- Test: `backend/src/tests/unit/test_postgres_backup.py`

- [ ] Write failing migration lock/version tests and backup command timeout tests.
- [ ] Add a migration ledger and PostgreSQL advisory deployment lock; startup only validates current schema.
- [ ] Add dump timeout, checksum, disk-space guard, durable backup mount, and restore verification documentation.
- [ ] Run PostgreSQL integration tests in CI.

## Task 7: Maintainability Completion

**Files:**
- Modify: `backend/src/crawler/scheduler.py`
- Modify: `backend/src/prediction_generation/service.py`
- Modify: `backend/src/predict/mechanisms.py`
- Modify: `backend/src/domains/*/repository.py`
- Modify: `backend/CLAUDE.md`
- Modify: `backend/docs/API.md`
- Test: focused domain and API contract suites

- [ ] Extract remaining scheduler SQL into repositories and remove direct future-draw number logging.
- [ ] Reduce generation service to orchestration and preserve its control-savepoint invariants.
- [ ] Complete category/registry extraction from `mechanisms.py` one responsibility at a time.
- [ ] Update architecture/API documentation and run full Python, TypeScript, PostgreSQL integration, and secret-scan gates.
