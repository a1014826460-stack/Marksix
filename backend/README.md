# Liuhecai Backend Admin README

## Overview

This backend is a lightweight admin and API service for lottery data management, draw ingestion, prediction generation, logging, and legacy frontend compatibility.

The runtime architecture now uses two layers of configuration:

1. `backend/src/config.yaml`
   Used as bootstrap configuration so the service can start and reach the database.
2. `system_config` table
   Used as the runtime source of truth for most constants and operational parameters.

Runtime reads database configuration first and falls back to `config.yaml` when the key is missing or the database is unavailable.

## Startup Flow

Main entry: `backend/src/app.py`

Startup sequence:

1. Resolve database target from `LOTTERY_DB_PATH`, `DATABASE_URL`, configured PostgreSQL DSN, or local SQLite fallback.
2. Call `ensure_admin_tables()` to create core tables and seed baseline data.
3. Call `init_logging()` to enable structured file logs and database-backed error logs.
4. Start HTTP server.
5. Start `CrawlerScheduler` for polling-based scheduler tasks.

Important limitation:
The scheduler now persists delayed business tasks in `scheduler_tasks`, but the worker itself is still single-process and in-app. It is restart-safe for queued tasks, but not yet a distributed scheduler.

## Core Tables

Key tables:

- `admin_users`: admin accounts
- `admin_sessions`: login sessions and expiration
- `managed_sites`: managed site metadata and fetch configuration
- `site_fetch_runs`: site fetch execution records
- `lottery_types`: lottery metadata, draw time, source URL, automation status
- `lottery_draws`: draw history and open state
- `site_prediction_modules`: enabled prediction modules per site
- `legacy_image_assets`: legacy image mapping
- `error_logs`: persisted error logs
- `system_config`: centralized runtime configuration
- `scheduler_tasks`: persistent delayed and scheduled backend tasks

## Authentication And Authorization

File: `backend/src/auth.py`

Mechanism:

- Passwords are stored with `PBKDF2-SHA256`.
- Hash iteration count comes from `auth.password_iterations`.
- Login creates a session token in `admin_sessions`.
- Session expiration comes from `auth.session_ttl_seconds`.
- Expired or malformed sessions are deleted on access.

Main functions:

- `hash_password()`
- `verify_password()`
- `login_user()`
- `auth_user_from_token()`
- `logout_user()`
- `ensure_generation_permission()`

Authorization rules:

- All `/api/admin/*` endpoints require a valid bearer token.
- Active prediction generation requires role `admin` or `super_admin`.

## CRUD Data Flow

Main HTTP router: `backend/src/app.py`

CRUD modules:

- `backend/src/admin/crud.py`
- `backend/src/admin/payload.py`
- `backend/src/admin/prediction.py`

Typical flow:

1. HTTP request enters `ApiHandler.dispatch()`.
2. Route performs authentication if needed.
3. Request body is parsed by `read_json()`.
4. Business function from `admin/*` module validates payload and executes SQL.
5. Data is returned as JSON.

Managed site CRUD:

- `list_sites()`
- `get_site()`
- `save_site()`
- `delete_site()`

Lottery CRUD:

- `list_lottery_types()`
- `save_lottery_type()`
- `delete_lottery_type()`
- `list_draws()`
- `save_draw()`
- `delete_draw()`

User CRUD:

- `list_users()`
- `save_user()`
- `delete_user()`

Prediction module CRUD:

- `list_site_prediction_modules()`
- `add_site_prediction_module()`
- `update_site_prediction_module()`
- `delete_site_prediction_module()`

## Validation And Error Handling

Validation is implemented in business-layer functions instead of only in HTTP handlers.

Examples:

- `save_site()` validates name, web id range, and URL template placeholders.
- `regenerate_payload_data()` validates table name, issue, year, and `res_code` format.
- `bulk_generate_site_prediction_data()` validates issue range ordering.
- `auth_user_from_token()` validates session expiration and token usability.

Error handling strategy:

- Business functions raise `ValueError`, `KeyError`, or `PermissionError`.
- `ApiHandler.dispatch()` catches exceptions and maps them to JSON responses.
- Request exceptions are logged with `logger.exception(...)`.
- Database log persistence failures never break primary business flow.

## Scheduler, Draw Opening, And Crawlers

File: `backend/src/crawler/crawler_service.py`

Responsibilities:

- auto-open draws whose `draw_time` has passed
- precise Taiwan daily open scheduling
- auto-crawl HK and Macau draws
- delayed auto-prediction after draw ingestion

Current scheduler model:

- `CrawlerScheduler.start()`
- `_schedule_auto_open()`
- `_schedule_auto_crawl()`
- `_schedule_task_loop()`
- `scheduler_tasks` table for durable delayed execution

Key operational settings:

- `crawler.auto_open_interval_seconds`
- `crawler.auto_crawl_interval_seconds`
- `crawler.auto_crawl_recent_minutes`
- `crawler.taiwan_precise_open_hour`
- `crawler.taiwan_precise_open_minute`
- `crawler.taiwan_retry_delays_seconds`
- `crawler.taiwan_max_retries`
- `crawler.auto_prediction_delay_hours`

Data source rules:

- Hong Kong source URL comes from `lottery_types.collect_url`, with bootstrap default `draw.hk_default_collect_url`
- Macau source URL comes from `lottery_types.collect_url`, with bootstrap default `draw.macau_default_collect_url`
- Taiwan data is import-only and uses `draw.taiwan_import_file`

Crawler HTTP resilience:

- `crawler.http_timeout_seconds`
- `crawler.http_retry_count`
- `crawler.http_retry_delay_seconds`

Files:

- `backend/src/crawler/HK_history_crawler.py`
- `backend/src/crawler/Macau_history_crawler.py`
- `backend/src/crawler/crawler_service.py`

## Prediction Generation

Entry points:

- public prediction API: `ApiHandler.handle_prediction()`
- batch generation: `backend/src/admin/prediction.py::bulk_generate_site_prediction_data`
- shared generator: `backend/src/prediction_generation/service.py::generate_prediction_batch`
- delayed automation: `backend/src/crawler/crawler_service.py::_run_auto_prediction`

Prediction safety:

File: `backend/src/admin/prediction.py`

Safety functions:

- `lookup_draw_visibility()`
- `resolve_prediction_request_safety()`
- `apply_prediction_row_safety()`
- `redact_prediction_result_fields()`

Meaning:

- if a draw is not opened yet, request-side `res_code` is not trusted for historical-result visibility
- response fields like `res_code`, `res_sx`, and `res_color` can be redacted for unopened terms

Future prediction vs historical backfill:

- historical opened draws are read from `lottery_draws`
- future periods are created by `future_periods`
- delayed automation first backfills actual draw result into created prediction rows, then generates next period prediction

Important runtime settings:

- `prediction.default_target_hit_rate`
- `prediction.max_terms_per_year`

## Site Data Fetching

Files:

- `backend/src/utils/data_fetch.py`
- `backend/src/app.py::fetch_site_data`

Process:

1. Fetch mode list from site management pages
2. Fetch paged mode data
3. Persist `fetched_modes` and `fetched_mode_records`
4. Optional normalization
5. Optional text history mapping rebuild
6. Record run status in `site_fetch_runs`

Fetch run audit fields:

- `status`
- `message`
- `modes_count`
- `records_count`
- `started_at`
- `finished_at`

## Audit And Logging

File: `backend/src/logger.py`

Capabilities:

- JSON file logs with rotation
- `error_logs` DB persistence for `ERROR` and above
- slow-call timing logs through decorator
- background cleanup of expired DB logs and oversized log files

Key functions:

- `init_logging()`
- `log_execution()`
- `query_error_logs()`
- `get_error_log_detail()`
- `export_error_logs()`
- `get_log_stats()`
- `trigger_cleanup()`

Runtime settings:

- `logging.max_file_size_mb`
- `logging.backup_count`
- `logging.error_retention_days`
- `logging.warn_retention_days`
- `logging.info_retention_days`
- `logging.max_total_log_size_mb`
- `logging.cleanup_interval_seconds`
- `logging.slow_call_warning_ms`

Health endpoints:

- `/health`
- `/api/health`

## System Configuration Management

Runtime configuration storage:

- bootstrap: `backend/src/config.yaml`
- runtime: `system_config`

Core file:

- `backend/src/runtime_config.py`

Functions:

- `ensure_system_config_table()`
- `seed_system_config_defaults()`
- `get_config()`
- `get_config_from_conn()`
- `list_system_configs()`
- `upsert_system_config()`

Admin APIs:

- `GET /api/admin/system-config`
- `PUT /api/admin/system-config/{key}`
- `PATCH /api/admin/system-config/{key}`

Design note:

- Database connection bootstrap values cannot live only in the database.
- Therefore PostgreSQL DSN remains bootstrapped from `config.yaml` or environment variables.

## Scheduler Task Model

Persistent scheduler tasks are stored in `scheduler_tasks`.

Current task types:

- `auto_prediction`
- `taiwan_precise_open`

Task lifecycle fields:

- `task_key`
- `task_type`
- `payload_json`
- `status`
- `run_at`
- `locked_at`
- `locked_by`
- `attempt_count`
- `max_attempts`
- `last_error`
- `last_finished_at`

Execution model:

1. Business flow writes or updates a task row.
2. Scheduler polling loop acquires due tasks.
3. Task row is marked `running`.
4. Task succeeds and becomes `done`, or fails and is retried / marked `failed`.

Related runtime settings:

- `crawler.task_poll_interval_seconds`
- `crawler.task_lock_timeout_seconds`
- `crawler.task_retry_delay_seconds`

## Known Operational Risks

Current remaining risks:

- Scheduler is still single-process and in-memory, not durable across multi-instance deployment.
- Startup still depends on `config.yaml` for first database reachability.
- Some legacy scripts and tooling files outside main admin runtime may still contain local defaults and should be aligned if they are used in production workflows.

## Recommended Deployment Practice

1. Set `DATABASE_URL` or `LOTTERY_DB_PATH` explicitly in production.
2. Change bootstrap admin password before exposure.
3. Review `system_config` values after first startup.
4. Monitor `/api/health` and `error_logs`.
5. Run the service as a supervised process so restart can recover from crashes.
