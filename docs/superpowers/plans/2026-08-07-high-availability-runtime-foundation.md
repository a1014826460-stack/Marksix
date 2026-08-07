# High-Availability Runtime Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backward-compatible PostgreSQL write/read runtime targets and load-balancer-safe health probes without changing draw, prediction, scheduler, or public API behavior.

**Architecture:** A focused `DatabaseTargets` value object resolves the write endpoint from `DATABASE_WRITE_URL` or legacy `DATABASE_URL` and resolves the read endpoint from `DATABASE_READ_URL` or the write endpoint. The HTTP server stores both targets while preserving `ctx.db_path` as the write target; dedicated liveness and readiness routes separate process health from dependency health so Docker and HAProxy can make correct decisions.

**Tech Stack:** Python 3, stdlib `http.server`, psycopg, PostgreSQL, pytest, Docker Compose, Nginx

---

## Scope Boundary

This is phase 1 of the approved high-availability design. It does not route public reads to the replica yet, because P0 latest-draw reads must first gain Redis/versioned snapshot protection. It does not add Redis, Outbox, S3, HAProxy deployment, CDN rules, production database migration, or remote server changes.

Subsequent plans execute in this order:

1. Redis cache adapters, safe public snapshot reads, rate limiting, and Traffic Event buffering.
2. PostgreSQL Outbox and idempotent draw/prediction cache publication.
3. S3-compatible Prediction Asset storage and 180-day lifecycle cleanup.
4. Application-node Compose, HAProxy, CDN cache policy, metrics, disk alerts, load tests, and controlled production migration.

## File Map

- Create `backend/src/database/runtime_targets.py`: resolve and validate write/read PostgreSQL targets without exposing credentials.
- Create `backend/src/database/health.py`: perform bounded `SELECT 1` dependency probes and return role-level status.
- Create `backend/src/tests/unit/test_database_runtime_targets.py`: define environment precedence and fallback contracts.
- Create `backend/src/tests/unit/test_database_health.py`: define dependency probe success/failure contracts.
- Modify `backend/src/app_http/request_context.py`: expose `write_db_path` and `read_db_path`; keep `db_path` as the write compatibility alias.
- Modify `backend/src/app_http/server.py`: resolve/store both targets and inject dependency health into request state.
- Modify `backend/src/main.py`: validate both runtime endpoints before startup.
- Modify `backend/src/routes/system_routes.py`: add liveness, readiness, and detailed dependency routes while preserving old contracts.
- Modify `backend/src/tests/unit/test_api_contract_system_routes.py`: cover new health routes and status codes.
- Modify `backend/src/tests/unit/test_server_parser.py`: protect CLI/legacy environment compatibility.
- Modify `docker-compose.yml`: point the Python container health check at dependency-free liveness.
- Modify `deploy/nginx.conf` and `deploy/nginx.domain.ssl.conf.example`: expose liveness and readiness without changing current `/health` compatibility.
- Modify `backend/README_CN.md` and `.env.example`: document endpoint precedence and local fallback.

### Task 1: Resolve PostgreSQL Write and Read Targets

**Files:**
- Create: `backend/src/database/runtime_targets.py`
- Create: `backend/src/tests/unit/test_database_runtime_targets.py`

- [ ] **Step 1: Write failing target-resolution tests**

```python
from __future__ import annotations

import pytest

from database.runtime_targets import resolve_database_targets


def test_write_url_overrides_legacy_database_url():
    targets = resolve_database_targets(
        environ={
            "DATABASE_URL": "postgresql://legacy/db",
            "DATABASE_WRITE_URL": "postgresql://writer/db",
            "DATABASE_READ_URL": "postgresql://reader/db",
        }
    )
    assert targets.write == "postgresql://writer/db"
    assert targets.read == "postgresql://reader/db"


def test_legacy_database_url_remains_the_local_write_and_read_default():
    targets = resolve_database_targets(environ={"DATABASE_URL": "postgresql://local/db"})
    assert targets.write == "postgresql://local/db"
    assert targets.read == "postgresql://local/db"


def test_explicit_cli_target_overrides_write_environment_but_keeps_read_environment():
    targets = resolve_database_targets(
        explicit_write="postgresql://cli/db",
        environ={
            "DATABASE_WRITE_URL": "postgresql://writer/db",
            "DATABASE_READ_URL": "postgresql://reader/db",
        },
    )
    assert targets.write == "postgresql://cli/db"
    assert targets.read == "postgresql://reader/db"


def test_missing_database_target_is_rejected():
    with pytest.raises(RuntimeError, match="DATABASE_WRITE_URL or DATABASE_URL"):
        resolve_database_targets(environ={})


@pytest.mark.parametrize("name", ["DATABASE_WRITE_URL", "DATABASE_READ_URL"])
def test_non_postgres_runtime_target_is_rejected(name):
    environ = {"DATABASE_URL": "postgresql://local/db", name: "sqlite:///runtime.db"}
    with pytest.raises(RuntimeError, match=name):
        resolve_database_targets(environ=environ)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
Push-Location backend/src
python -m pytest tests/unit/test_database_runtime_targets.py -q
Pop-Location
```

Expected: collection fails because `database.runtime_targets` does not exist.

- [ ] **Step 3: Implement the minimal resolver**

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from db import is_postgres_target


@dataclass(frozen=True)
class DatabaseTargets:
    write: str
    read: str


def _required_postgres_target(name: str, value: str) -> str:
    target = str(value or "").strip()
    if not is_postgres_target(target):
        raise RuntimeError(f"{name} must be a PostgreSQL DSN.")
    return target


def resolve_database_targets(
    *,
    explicit_write: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> DatabaseTargets:
    env = os.environ if environ is None else environ
    write_value = (
        str(explicit_write or "").strip()
        or str(env.get("DATABASE_WRITE_URL", "")).strip()
        or str(env.get("DATABASE_URL", "")).strip()
    )
    if not write_value:
        raise RuntimeError("Set DATABASE_WRITE_URL or DATABASE_URL before starting the service.")
    write = _required_postgres_target("DATABASE_WRITE_URL or DATABASE_URL", write_value)
    read_value = str(env.get("DATABASE_READ_URL", "")).strip() or write
    read = _required_postgres_target("DATABASE_READ_URL", read_value)
    return DatabaseTargets(write=write, read=read)
```

- [ ] **Step 4: Run the target-resolution tests and verify GREEN**

Run the same pytest command. Expected: `6 passed`.

- [ ] **Step 5: Commit the resolver**

```powershell
git add backend/src/database/runtime_targets.py backend/src/tests/unit/test_database_runtime_targets.py
git commit -m "feat(db): resolve write and read runtime targets"
```

### Task 2: Carry Both Targets Through the HTTP Runtime

**Files:**
- Modify: `backend/src/app_http/request_context.py`
- Modify: `backend/src/app_http/server.py`
- Modify: `backend/src/main.py`
- Modify: `backend/src/runtime_environment.py`
- Modify: `backend/src/tests/unit/test_database_runtime_targets.py`
- Modify: `backend/src/tests/unit/test_server_parser.py`
- Modify: `backend/src/tests/unit/test_runtime_environment.py`

- [ ] **Step 1: Write failing RequestContext and parser compatibility tests**

Add tests that construct a handler server with `write_db_path` and `read_db_path` and assert:

```python
assert ctx.write_db_path == "postgresql://writer/db"
assert ctx.read_db_path == "postgresql://reader/db"
assert ctx.db_path == "postgresql://writer/db"
```

Add a parser test:

```python
def test_build_parser_uses_write_url_before_legacy_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://legacy/db")
    monkeypatch.setenv("DATABASE_WRITE_URL", "postgresql://writer/db")
    args = build_parser().parse_args([])
    assert args.db_path == "postgresql://writer/db"
```

Add runtime isolation tests proving that the existing `compose` mode still only accepts `pgbouncer:6432`, while an explicit `managed` mode accepts a non-loopback managed endpoint and rejects localhost. `LIUHECAI_DATABASE_MODE` defaults to `compose` in production so existing deployments do not silently broaden database access.

- [ ] **Step 2: Run focused tests and verify RED**

```powershell
Push-Location backend/src
python -m pytest tests/unit/test_database_runtime_targets.py tests/unit/test_server_parser.py -q
Pop-Location
```

Expected: RequestContext lacks `write_db_path`/`read_db_path`, and parser ignores `DATABASE_WRITE_URL`.

- [ ] **Step 3: Add compatibility properties and server attributes**

Use these properties in `RequestContext`:

```python
@property
def write_db_path(self) -> str | Path:
    return getattr(self.handler.server, "write_db_path", self.handler.server.db_path)

@property
def read_db_path(self) -> str | Path:
    return getattr(self.handler.server, "read_db_path", self.write_db_path)

@property
def db_path(self) -> str | Path:
    return self.write_db_path
```

Change `run_server` to accept a `DatabaseTargets`, run bootstrap/logging against `targets.write`, and set:

```python
server.db_path = targets.write
server.write_db_path = targets.write
server.read_db_path = targets.read
```

Set the parser default to:

```python
default=os.environ.get("DATABASE_WRITE_URL", "").strip() or DEFAULT_POSTGRES_DSN or None
```

In `main.py`, resolve targets with `resolve_database_targets(explicit_write=args.db_path)`, validate both endpoints, and call `run_server(args.host, args.port, targets)`.

Extend `validate_runtime_database_target` with a `database_mode` argument/environment value:

```python
mode = (database_mode or os.getenv("LIUHECAI_DATABASE_MODE", "compose")).strip().lower()
if profile == PRODUCTION and mode == "managed":
    if host in _DEVELOPMENT_HOSTS:
        raise RuntimeEnvironmentError("managed production database cannot use a loopback host.")
    return
```

Reject mode values outside `compose|managed`; preserve the exact current compose host/port check for `compose`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the same focused command. Expected: all selected tests pass.

- [ ] **Step 5: Run current server/startup contracts**

```powershell
Push-Location backend/src
python -m pytest tests/unit/test_server_parser.py tests/unit/test_runtime_environment.py tests/unit/test_startup_warnings.py tests/unit/test_startup_risk_warnings.py -q
Pop-Location
```

Expected: all tests pass without changing scheduler warnings or production PostgreSQL validation.

- [ ] **Step 6: Commit HTTP target plumbing**

```powershell
git add backend/src/app_http/request_context.py backend/src/app_http/server.py backend/src/main.py backend/src/runtime_environment.py backend/src/tests/unit/test_database_runtime_targets.py backend/src/tests/unit/test_server_parser.py backend/src/tests/unit/test_runtime_environment.py docs/superpowers/plans/2026-08-07-high-availability-runtime-foundation.md
git commit -m "feat(api): carry database read and write targets"
```

### Task 3: Add Dependency-Probe Service

**Files:**
- Create: `backend/src/database/health.py`
- Create: `backend/src/tests/unit/test_database_health.py`

- [ ] **Step 1: Write failing database-probe tests**

```python
from database.health import collect_database_health


def test_database_health_reports_both_roles_without_exposing_targets(monkeypatch):
    monkeypatch.setattr("database.health._probe_target", lambda target: None)
    result = collect_database_health("postgresql://writer/secret", "postgresql://reader/secret")
    assert result == {
        "ok": True,
        "database": {
            "write": {"ok": True},
            "read": {"ok": True},
        },
    }
    assert "secret" not in repr(result)


def test_database_health_marks_a_failed_role_and_redacts_exception_text(monkeypatch):
    def fail_reader(target):
        if "reader" in target:
            raise RuntimeError(f"connection failed: {target}")

    monkeypatch.setattr("database.health._probe_target", fail_reader)
    result = collect_database_health("postgresql://writer/secret", "postgresql://reader/secret")
    assert result["ok"] is False
    assert result["database"]["write"] == {"ok": True}
    assert result["database"]["read"]["ok"] is False
    assert "postgresql://" not in result["database"]["read"]["error"]
```

- [ ] **Step 2: Run the test and verify RED**

```powershell
Push-Location backend/src
python -m pytest tests/unit/test_database_health.py -q
Pop-Location
```

Expected: collection fails because `database.health` does not exist.

- [ ] **Step 3: Implement bounded role probes**

Implement `_probe_target` with `connect(target)` and `SELECT 1`, and implement `collect_database_health` so each role is probed independently. Error payloads contain only the exception class name and a fixed message such as `dependency unavailable`; they never include a DSN, username, host, password, query, or traceback.

```python
def _probe_target(target: str) -> None:
    with connect(target) as conn:
        row = conn.execute("SELECT 1 AS ok").fetchone()
        if not row or int(row["ok"]) != 1:
            raise RuntimeError("database probe returned an invalid result")
```

- [ ] **Step 4: Run probe tests and verify GREEN**

Run the same pytest command. Expected: `2 passed`.

- [ ] **Step 5: Commit dependency probes**

```powershell
git add backend/src/database/health.py backend/src/tests/unit/test_database_health.py
git commit -m "feat(health): probe database runtime roles"
```

### Task 4: Add Liveness, Readiness, and Dependency Routes

**Files:**
- Modify: `backend/src/routes/system_routes.py`
- Modify: `backend/src/app_http/server.py`
- Modify: `backend/src/tests/unit/test_api_contract_system_routes.py`

- [ ] **Step 1: Write failing route contract tests**

Add these contracts:

```python
def test_liveness_does_not_call_dependency_health():
    ctx = _make_system_ctx("/health/live")
    ctx.state["dependency_health"] = lambda *_args: (_ for _ in ()).throw(AssertionError())
    system_routes.liveness(ctx)
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {"ok": True, "status": "alive"}


def test_readiness_returns_503_when_a_required_dependency_is_down():
    ctx = _make_system_ctx("/health/ready")
    ctx.state["dependency_health"] = lambda *_args: {
        "ok": False,
        "database": {"write": {"ok": True}, "read": {"ok": False}},
    }
    system_routes.readiness(ctx)
    assert ctx.handler.response_status == 503
    assert response_json(ctx)["ok"] is False


def test_dependency_health_returns_role_status_without_targets():
    ctx = _make_system_ctx("/health/dependencies")
    ctx.state["dependency_health"] = lambda *_args: {
        "ok": True,
        "database": {"write": {"ok": True}, "read": {"ok": True}},
    }
    system_routes.dependencies(ctx)
    assert ctx.handler.response_status == 200
    assert response_json(ctx)["database"]["write"] == {"ok": True}
```

- [ ] **Step 2: Run system route tests and verify RED**

```powershell
Push-Location backend/src
python -m pytest tests/unit/test_api_contract_system_routes.py -q
Pop-Location
```

Expected: new route handlers are missing.

- [ ] **Step 3: Register and implement probes**

Register:

```python
router.add("GET", "/health/live", liveness)
router.add("GET", "/health/ready", readiness)
router.add("GET", "/health/dependencies", dependencies)
```

Implement liveness without touching PostgreSQL. Readiness calls `dependency_health(ctx.write_db_path, ctx.read_db_path)` and returns HTTP 200/503. Dependencies returns the same role-level payload and is intended for Nginx allowlisting in the deployment phase. Preserve `/health` and `/api/health` response contracts unchanged.

Inject `collect_database_health` into `ctx.state["dependency_health"]` from `ApiHandler.dispatch`.

- [ ] **Step 4: Run route tests and verify GREEN**

Run the same pytest command. Expected: all system route contracts pass.

- [ ] **Step 5: Run API contract regression tests**

```powershell
Push-Location backend/src
python -m pytest tests/unit/test_api_contract_system_routes.py tests/unit/test_api_contract_public_routes.py tests/unit/test_api_contract_legacy_routes.py -q
Pop-Location
```

Expected: all selected contracts pass; existing `/health`, `/api/health`, public and legacy payloads remain unchanged.

- [ ] **Step 6: Commit health routes**

```powershell
git add backend/src/routes/system_routes.py backend/src/app_http/server.py backend/src/tests/unit/test_api_contract_system_routes.py
git commit -m "feat(health): separate liveness and readiness probes"
```

### Task 5: Update Local and Container Runtime Contracts

**Files:**
- Modify: `docker-compose.yml`
- Modify: `deploy/nginx.conf`
- Modify: `deploy/nginx.domain.ssl.conf.example`
- Modify: `.env.example`
- Modify: `backend/README_CN.md`
- Modify: `backend/src/tests/unit/test_scheduler_worker_separation.py`

- [ ] **Step 1: Write failing configuration contract assertions**

Add source-level assertions that:

```python
assert "/health/live" in compose_python_api_healthcheck
assert "location = /health/live" in nginx_config
assert "location = /health/ready" in nginx_config
assert "DATABASE_WRITE_URL" in env_example
assert "DATABASE_READ_URL" in env_example
```

Also assert the `scheduler-worker` command and lease behavior remain present; this phase must not add a scheduler to the API service.

- [ ] **Step 2: Run the configuration contract and verify RED**

```powershell
Push-Location backend/src
python -m pytest tests/unit/test_scheduler_worker_separation.py -q
Pop-Location
```

Expected: new liveness/readiness configuration assertions fail.

- [ ] **Step 3: Update configuration and documentation**

- Change only the Python API Docker healthcheck URL from `/health` to `/health/live` so a database outage does not restart every API container.
- Add exact-match Nginx locations for `/health/live` and `/health/ready` before existing `/health`; the deployment phase will apply source allowlists to the dependency detail route.
- Document that local Windows development may keep only `DATABASE_URL`, while production introduces secret-injected write/read endpoints.
- Do not add real DSNs, passwords, managed-service endpoints, CDN credentials, or production IP rules.

- [ ] **Step 4: Run configuration contracts and verify GREEN**

Run the same pytest command. Expected: all scheduler separation and configuration assertions pass.

- [ ] **Step 5: Validate configuration syntax locally**

```powershell
docker compose config --quiet
```

Expected: exit code 0. If Docker is unavailable, record that limitation and validate the YAML structure through the existing source contract tests; do not claim Compose validation passed.

- [ ] **Step 6: Commit runtime contracts**

```powershell
git add docker-compose.yml deploy/nginx.conf deploy/nginx.domain.ssl.conf.example .env.example backend/README_CN.md backend/src/tests/unit/test_scheduler_worker_separation.py
git commit -m "chore(ops): define API health probe contracts"
```

### Task 6: Verify the Phase Against Prediction Release Rules

**Files:**
- Modify only when a regression exposes a real issue.

- [ ] **Step 1: Run focused unit tests**

```powershell
Push-Location backend/src
python -m pytest tests/unit/test_database_runtime_targets.py tests/unit/test_database_health.py tests/unit/test_api_contract_system_routes.py tests/unit/test_server_parser.py tests/unit/test_runtime_environment.py tests/unit/test_scheduler_worker_separation.py -q
Pop-Location
```

Expected: all selected tests pass.

- [ ] **Step 2: Run the mandatory prediction release review**

```powershell
pwsh -File .\skills\prediction-release-review\scripts\run-regression.ps1
```

Expected: all four groups pass: `generation`, `missing-alert`, `scheduled-draw`, and `public-redaction`.

- [ ] **Step 3: Run the full backend unit suite**

```powershell
Push-Location backend/src
python -m pytest tests/unit -q
Pop-Location
```

Expected: zero failures. Existing environment-dependent skips are acceptable only when reported with their reasons.

- [ ] **Step 4: Run static validation**

```powershell
python -m compileall backend/src/database/runtime_targets.py backend/src/database/health.py backend/src/app_http backend/src/routes/system_routes.py
git diff --check
```

Expected: both commands exit 0.

- [ ] **Step 5: Review the complete phase diff**

Verify explicitly:

- no public route is switched to the read replica in this phase;
- `ctx.db_path` remains the write compatibility alias;
- API replicas still do not run scheduler timers;
- old `/health` and `/api/health` contracts remain unchanged;
- no DSN or exception secret is returned by health routes;
- no production server, managed service, database, or DNS setting was changed.

- [ ] **Step 6: Record the verification result in the implementation change description**

Record each command, exit code, pass/skip counts, and any environment-dependent skips. If a verification step exposes a defect, return to the task that owns the affected file and add a failing regression test before changing production code.
