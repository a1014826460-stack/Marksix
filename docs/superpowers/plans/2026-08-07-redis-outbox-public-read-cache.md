# Redis Public Snapshot and Draw Outbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish confirmed Opened Draw data through an idempotent PostgreSQL Outbox to Redis versioned snapshots, and serve safe public draw reads from those snapshots without exposing Future Issue data.

**Architecture:** PostgreSQL remains the authority: every transition from `is_opened=0` to `is_opened=1` inserts a unique `draw-published:{lottery_type_id}:{year}:{term}` Outbox event in the same transaction. The lease-owning scheduler-worker claims and retries events, builds complete public snapshots, writes immutable version keys, then atomically switches a Redis pointer. Public P0 read handlers consult cache first, fall back to the write endpoint until a published snapshot exists, and never source just-opened data from a potentially lagged read replica.

**Tech Stack:** Python 3.11, stdlib HTTP server, psycopg/PostgreSQL, `redis` Python client, SQLite test bootstrap, pytest.

---

## Scope and Invariants

- Redis is a disposable read cache, not an authoritative draw store.
- Future Issue (`is_opened=0`) numbers, zodiacs, colors, and prediction result fields must not enter a public snapshot, cache key payload, API response, or log.
- All draw state transitions covered in this plan use one database connection and one transaction for the draw update and Outbox insert.
- The scheduler keeps its PostgreSQL worker lease and `scheduler_tasks`; Redis is not a task queue.
- Redis failures must not roll back or delay an Opened Draw database commit. Public reads use bounded in-process fallback and do not cause a hot-key database stampede.
- This phase preserves public JSON shapes. Cache metadata is internal and no HTTP cache headers are added here; CDN policy belongs to the later edge phase.
- PostgreSQL production schema changes are only exposed through `database.versioned_migrations`; SQLite test bootstrap receives compatible DDL.
- Public cache misses initially query `ctx.write_db_path`, rather than `ctx.read_db_path`, to guarantee the P0 post-draw consistency target. Replica routing comes after published snapshot coverage and replica-lag monitoring are deployed.

## File Map

- Create `backend/src/cache/contracts.py`: cache interface, cache-unavailable exception, JSON codec and versioned pointer contracts.
- Create `backend/src/cache/memory.py`: thread-safe local fallback implementation with TTL and atomic pointer replacement.
- Create `backend/src/cache/redis_store.py`: Redis client adapter, bounded timeouts and pipeline-backed atomic pointer publication.
- Create `backend/src/cache/runtime.py`: environment resolver (`memory` locally, explicit `redis` in production) and cache factory.
- Create `backend/src/cache/public_snapshots.py`: stable cache keys, snapshot validation, Future Issue sanitization, latest/current-period snapshot read/write.
- Create `backend/src/outbox/repository.py`: Outbox enqueue, due-event claim, retry and completion persistence.
- Create `backend/src/outbox/publisher.py`: processes confirmed draw events and publishes all P0 draw snapshots idempotently.
- Create `backend/src/database/schema/outbox.py`: SQLite-compatible Outbox table/index bootstrap.
- Create `backend/src/tests/unit/test_cache_runtime.py`: runtime selection and fail-closed production configuration tests.
- Create `backend/src/tests/unit/test_public_snapshots.py`: snapshot keys, atomic publication, pointer fallback and Future Issue redaction tests.
- Create `backend/src/tests/unit/test_outbox_repository.py`: unique business key, claim/retry/completion and SQLite transaction tests.
- Create `backend/src/tests/unit/test_outbox_publisher.py`: publishing behavior and Redis failure isolation tests.
- Create `backend/src/tests/unit/test_draw_publication_outbox.py`: each draw-opening path writes an Outbox event atomically.
- Modify `backend/requirements.txt`: add the supported Redis client dependency.
- Modify `.env.example` and `backend/README_CN.md`: document cache environment contracts without credentials.
- Modify `backend/src/database/bootstrap.py`: create the Outbox schema for explicit SQLite tests only.
- Modify `backend/src/database/versioned_migrations.py`: add a PostgreSQL migration to create the Outbox schema and bump the current version.
- Modify `backend/src/crawler/scheduler.py` and `backend/src/crawler/collectors.py`: enqueue/refresh Outbox events in every public Opened Draw write transaction and drain Outbox on the durable worker loop.
- Modify `backend/src/domains/lottery/service.py`: enqueue a publication event when a manual save creates a confirmed Opened Draw.
- Modify `backend/src/scheduler_worker.py`: supply the cache-backed publisher to the scheduler-worker runtime without changing lease ownership.
- Modify `backend/src/app_http/server.py`: construct one cache service at startup and inject it into request contexts.
- Modify `backend/src/routes/public_routes.py`: cache the P0 public latest/current-period endpoints and preserve source JSON contracts.
- Modify `backend/src/public/api.py`: accept reusable opened-draw snapshot construction helpers without changing public payload fields.
- Modify `backend/src/tests/unit/test_api_contract_public_routes.py`: protect cache-first routing and JSON contracts.

## Task 1: Define Cache Runtime and Local Adapter

**Files:** `backend/src/cache/contracts.py`, `backend/src/cache/memory.py`, `backend/src/cache/runtime.py`, `backend/src/tests/unit/test_cache_runtime.py`, `backend/requirements.txt`, `.env.example`, `backend/README_CN.md`

- [ ] Write tests for development-memory default, explicit Redis URL validation, production fail-closed memory rejection, failure mapping, and atomic pointer replacement.
- [ ] Run `python -m pytest tests/unit/test_cache_runtime.py -q` from `backend/src`; verify RED.
- [ ] Implement the cache interface plus locked local TTL adapter. `publish_versioned` writes immutable data before changing its pointer.
- [ ] Add `redis>=5,<6`; add an adapter with explicit socket timeouts and no import-time connection.
- [ ] Re-run the focused tests; commit `feat(cache): add runtime cache adapters`.

## Task 2: Define Safe Public Draw Snapshot Contracts

**Files:** `backend/src/cache/public_snapshots.py`, `backend/src/tests/unit/test_public_snapshots.py`, `backend/src/public/api.py`

- [ ] Write tests for typed versioned keys, Opened Draw-only serialization, Future Issue redaction, invalid-pointer cache miss, and atomic complete payload publication.
- [ ] Run `python -m pytest tests/unit/test_public_snapshots.py -q`; verify RED.
- [ ] Build only existing latest-draw/current-period JSON payloads. Internal envelopes may contain `published_at`; they reject raw `numbers`, `res_sx`, `res_color`, and `is_opened` fields.
- [ ] Re-run `test_public_snapshots.py` and `test_taiwan_next_issue_logic.py`; commit `feat(cache): define safe public draw snapshots`.

## Task 3: Add the Atomic PostgreSQL Outbox

**Files:** `backend/src/database/schema/outbox.py`, `backend/src/outbox/repository.py`, `backend/src/tests/unit/test_outbox_repository.py`, `backend/src/database/bootstrap.py`, `backend/src/database/versioned_migrations.py`

- [ ] Write tests for unique idempotent enqueue, rollback, due-event leases, retry, completion, SQLite bootstrap, and registered PostgreSQL migration.
- [ ] Run `python -m pytest tests/unit/test_outbox_repository.py -q`; verify RED.
- [ ] Implement table fields `id`, `event_key UNIQUE`, `event_type`, `payload_json`, `status`, `available_at`, `lease_owner`, `lease_until`, `attempts`, `last_error`, `published_at`, `created_at`, `updated_at`; use portable qmark SQL.
- [ ] Register the next versioned PostgreSQL migration and update `CURRENT_SCHEMA_VERSION`.
- [ ] Re-run focused tests; commit `feat(outbox): persist draw publication events`.

## Task 4: Enqueue Publication Events with Every Opening Path

**Files:** `backend/src/tests/unit/test_draw_publication_outbox.py`, `backend/src/crawler/scheduler.py`, `backend/src/crawler/collectors.py`, `backend/src/domains/lottery/service.py`

- [ ] Write SQLite tests for `_open_specific_records`, `_auto_open_draws`, `_open_taiwan_draws_and_update_next_time`, direct collector/upsert publication, and `save_draw` creating an Opened Draw. Each transition writes exactly one `draw-published:{lottery_type_id}:{year}:{term}` event; no transition creates no event. A correction to an existing Opened Draw creates an idempotent refresh/republish event so Redis cannot remain stale.
- [ ] Run the test file; verify RED.
- [ ] Select authoritative identities before updates and enqueue each event on the same connection. Ensure `collectors._upsert_draw` and legacy direct-open paths cannot bypass publication. Do not publish Redis here. An Outbox database error aborts the draw transaction.
- [ ] Run the draw-outbox test plus HK/Macau, Taiwan, and admin lottery regression; commit `feat(draw): enqueue publication events atomically`.

## Task 5: Publish Outbox Events from the Lease-Holding Worker

**Files:** `backend/src/outbox/publisher.py`, `backend/src/tests/unit/test_outbox_publisher.py`, `backend/src/crawler/scheduler.py`, `backend/src/scheduler_worker.py`

- [ ] Write tests that claimed `draw.published` events read only Opened Draws, publish versioned latest/current-period snapshots, complete once, retry cache errors without touching the committed draw, and reject Future Issue data.
- [ ] Run `python -m pytest tests/unit/test_outbox_publisher.py -q`; verify RED.
- [ ] Add a bounded drain to the existing PostgreSQL lease-owner task loop. It writes immutable snapshots then pointers, marks completion only on success, uses capped retry delay, and never prevents normal scheduler tasks.
- [ ] Re-run publisher and scheduler-separation tests; commit `feat(worker): publish draw snapshots from outbox`.

## Task 6: Serve P0 Public Reads from Snapshots

**Files:** `backend/src/app_http/server.py`, `backend/src/routes/public_routes.py`, `backend/src/tests/unit/test_api_contract_public_routes.py`

- [ ] Write request-contract tests for cache hits without DB calls, cache-miss write-target fallback, cache-failure graceful fallback, unchanged payload shape, and cache-first current-period.
- [ ] Run public-route tests; verify RED.
- [ ] Create one cache service in `run_server`, attach it to request state, and cache only `latest_draw` and `current_period`. A miss uses `ctx.write_db_path`; safe confirmed responses may backfill cache. Do not cache site-page, predictions, history, notices, or Traffic Events in this phase.
- [ ] Re-run public cache contracts and Taiwan regression; commit `feat(api): serve public draw reads from snapshots`.

## Task 7: Final Verification and Review

- [ ] Run phase tests from `backend/src`: `test_cache_runtime.py`, `test_public_snapshots.py`, `test_outbox_repository.py`, `test_draw_publication_outbox.py`, `test_outbox_publisher.py`, `test_api_contract_public_routes.py`, `test_hk_macau_precise_open_state.py`, `test_taiwan_next_issue_logic.py`, and `test_scheduler_worker_separation.py`.
- [ ] Run `pwsh -File .\skills\prediction-release-review\scripts\run-regression.ps1`; all four required suites must pass.
- [ ] Inspect `git diff --check main...HEAD`, obtain review, then locally integrate only after review passes.
- [ ] Never run remote migrations, deploy, inspect servers, or restart services under this plan.

