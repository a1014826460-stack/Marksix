# API Contract Safe Backend Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add API contract protection tests and complete low-risk backend maintenance improvements without changing frontend-facing API response data.

**Architecture:** We will lock existing API response shapes first with focused unit tests around health, auth error/auth login edge cases, and legacy compatibility handlers. After that, we will make minimal internal-only changes to docs and startup warnings, keeping business logic and response payloads unchanged.

**Tech Stack:** Python stdlib HTTP server, pytest, PostgreSQL/SQLite compatibility adapter, existing backend unit/integration test suite

---

## File Structure

- `backend/src/tests/unit/test_api_contract_system_routes.py`
  Responsibility: Lock `/health` and `/api/health` response shapes.
- `backend/src/tests/unit/test_api_contract_auth_routes.py`
  Responsibility: Lock auth route response structures for captcha and login validation failures.
- `backend/src/tests/unit/test_api_contract_legacy_routes.py`
  Responsibility: Lock legacy compatibility handler response wrappers and key field sets.
- `backend/src/app_http/server.py`
  Responsibility: Add startup warnings only; do not alter API behavior.
- `backend/src/runtime_config.py`
  Responsibility: Provide helper(s) to detect risky bootstrap defaults for logging.
- `backend/README_CN.md`
  Responsibility: Align docs with real entrypoints, config sources, and scheduler implementation.

No production response-writing code should change shape as part of this plan.

---

### Task 1: Lock System Route Contracts

**Files:**
- Create: `backend/src/tests/unit/test_api_contract_system_routes.py`
- Modify: none
- Test: `backend/src/tests/unit/test_api_contract_system_routes.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import json
from unittest.mock import MagicMock

from app_http.request_context import RequestContext
from routes import system_routes


def _make_handler(path: str, method: str = "GET"):
    handler = MagicMock()
    handler.path = path
    handler.command = method
    handler.headers = {}
    handler.server.db_path = "postgresql://test:test@localhost:5432/test"
    handler.wfile = MagicMock()
    return handler


def _make_ctx(path: str, method: str = "GET") -> RequestContext:
    handler = _make_handler(path, method)
    ctx = RequestContext(handler, method)
    ctx.path = path.rstrip("/") or "/"
    ctx.state["detect_database_engine"] = lambda db_path: "postgres"
    ctx.state["database_summary"] = lambda db_path: {"tables": 12, "engine": "postgres"}
    return ctx


def _response_json(ctx: RequestContext) -> dict:
    call_args = ctx.handler.wfile.write.call_args
    assert call_args is not None
    body = call_args[0][0].decode("utf-8")
    return json.loads(body)


def test_health_route_contract():
    ctx = _make_ctx("/health")

    system_routes.health(ctx)

    assert ctx.handler.send_response.call_args[0][0] == 200
    assert _response_json(ctx) == {"status": "ok", "engine": "postgres"}


def test_api_health_route_contract():
    ctx = _make_ctx("/api/health")

    system_routes.api_health(ctx)

    payload = _response_json(ctx)
    assert ctx.handler.send_response.call_args[0][0] == 200
    assert payload["ok"] is True
    assert payload["summary"] == {"tables": 12, "engine": "postgres"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend/src; python -m pytest tests/unit/test_api_contract_system_routes.py -v`

Expected: `FAIL` because the new test file does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# No production code change is expected for this task.
# Create only the test file from Step 1.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend/src; python -m pytest tests/unit/test_api_contract_system_routes.py -v`

Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
git add backend/src/tests/unit/test_api_contract_system_routes.py
git commit -m "test: lock system route response contracts"
```

---

### Task 2: Lock Auth Route Contracts

**Files:**
- Create: `backend/src/tests/unit/test_api_contract_auth_routes.py`
- Modify: none
- Test: `backend/src/tests/unit/test_api_contract_auth_routes.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

from app_http.request_context import RequestContext
from routes import auth_routes


def _make_handler(path: str, method: str = "POST", body: bytes = b""):
    handler = MagicMock()
    handler.path = path
    handler.command = method
    handler.headers = {"Content-Length": str(len(body))}
    handler.server.db_path = "postgresql://test:test@localhost:5432/test"
    handler.wfile = MagicMock()
    handler.rfile = io.BytesIO(body)
    handler.client_address = ("127.0.0.1", 12345)
    return handler


def _make_ctx(path: str, method: str = "POST", payload: dict | None = None) -> RequestContext:
    raw = json.dumps(payload or {}).encode("utf-8")
    handler = _make_handler(path, method, raw)
    ctx = RequestContext(handler, method)
    ctx.path = path.rstrip("/") or "/"
    return ctx


def _response_json(ctx: RequestContext) -> dict:
    call_args = ctx.handler.wfile.write.call_args
    assert call_args is not None
    body = call_args[0][0].decode("utf-8")
    return json.loads(body)


def test_captcha_route_contract():
    ctx = _make_ctx("/api/auth/captcha", method="GET")

    with patch("routes.auth_routes.generate_captcha", return_value=("1234", "data:image/svg+xml;base64,abc")), \
         patch("routes.auth_routes.store_captcha") as store_mock:
        auth_routes.captcha(ctx)

    payload = _response_json(ctx)
    assert ctx.handler.send_response.call_args[0][0] == 200
    assert payload == {
        "image": "data:image/svg+xml;base64,abc",
        "expires_in_seconds": 300,
    }
    assert store_mock.called


def test_login_missing_captcha_contract():
    ctx = _make_ctx("/api/auth/login", payload={"username": "admin", "password": "secret"})

    with patch("routes.auth_routes.check_login_locked", return_value=(False, "")):
        auth_routes.login(ctx)

    payload = _response_json(ctx)
    assert ctx.handler.send_response.call_args[0][0] == 400
    assert payload == {"ok": False, "error": "请输入验证码"}


def test_login_invalid_captcha_contract():
    ctx = _make_ctx(
        "/api/auth/login",
        payload={"username": "admin", "password": "secret", "captcha": "0000"},
    )

    with patch("routes.auth_routes.check_login_locked", return_value=(False, "")), \
         patch("routes.auth_routes.verify_captcha", return_value=False), \
         patch("routes.auth_routes.record_login_failure", return_value={
             "attempt_count": 1,
             "max_attempts": 5,
             "locked": False,
             "locked_minutes": 0,
         }):
        auth_routes.login(ctx)

    payload = _response_json(ctx)
    assert ctx.handler.send_response.call_args[0][0] == 400
    assert payload == {"ok": False, "error": "验证码错误"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend/src; python -m pytest tests/unit/test_api_contract_auth_routes.py -v`

Expected: `FAIL` because the new test file does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# No production code change is expected for this task.
# Create only the test file from Step 1.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend/src; python -m pytest tests/unit/test_api_contract_auth_routes.py -v`

Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
git add backend/src/tests/unit/test_api_contract_auth_routes.py
git commit -m "test: lock auth route response contracts"
```

---

### Task 3: Extend Legacy Contract Coverage

**Files:**
- Create: `backend/src/tests/unit/test_api_contract_legacy_routes.py`
- Modify: none
- Test: `backend/src/tests/unit/test_api_contract_legacy_routes.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from pathlib import Path

from db import connect
from legacy.frontend_compat import handle_frontend_kaijiang_api


def _setup_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "legacy_contract.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY,
                table_name TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO mode_payload_tables (modes_id, table_name) VALUES (?, ?)",
            (251, "mode_payload_251"),
        )
        conn.execute(
            """
            CREATE TABLE mode_payload_251 (
                year TEXT,
                term TEXT,
                web INTEGER,
                type INTEGER,
                content TEXT,
                xiao TEXT,
                code TEXT,
                res_code TEXT,
                res_sx TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO mode_payload_251 (
                year, term, web, type, content, xiao, code, res_code, res_sx
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026", "12", 6, 3, "[\"鼠|05,17\"]", "鼠,牛,虎,兔", "01,02", "01,02,03,04,05,06,07", "鼠,牛,虎,兔,龙,蛇,马"),
        )
        conn.commit()
    return db_path


def test_legacy_result_keeps_data_wrapper(tmp_path: Path):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        result = handle_frontend_kaijiang_api(
            "/api/kaijiang/getJyxiao2",
            {"web": ["6"], "type": ["3"], "num": ["1"]},
            conn,
        )

    assert list(result.keys()) == ["data"]
    assert isinstance(result["data"], list)
    assert result["data"][0]["term"] == "12"


def test_legacy_result_keeps_expected_field_order_and_names(tmp_path: Path):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        result = handle_frontend_kaijiang_api(
            "/api/kaijiang/getJyxiao2",
            {"web": ["6"], "type": ["3"], "num": ["1"]},
            conn,
        )

    assert list(result["data"][0].keys()) == ["content", "res_code", "res_sx", "term", "xiao"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend/src; python -m pytest tests/unit/test_api_contract_legacy_routes.py -v`

Expected: `FAIL` because the new test file does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# No production code change is expected for this task.
# Create only the test file from Step 1.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend/src; python -m pytest tests/unit/test_api_contract_legacy_routes.py -v`

Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
git add backend/src/tests/unit/test_api_contract_legacy_routes.py
git commit -m "test: lock legacy route response contracts"
```

---

### Task 4: Add Startup Warning Coverage

**Files:**
- Create: `backend/src/tests/unit/test_startup_warnings.py`
- Modify: `backend/src/runtime_config.py`
- Modify: `backend/src/app_http/server.py`
- Test: `backend/src/tests/unit/test_startup_warnings.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app_http import server


def test_warns_when_default_admin_password_is_active():
    with patch("app_http.server.logging.getLogger") as get_logger, \
         patch("app_http.server.has_insecure_bootstrap_admin_password", return_value=True):
        server._log_startup_risk_warnings("postgresql://test:test@localhost:5432/test")

    logger = get_logger.return_value
    logger.warning.assert_any_call(
        "Bootstrap admin password is still the default value; change it before exposing the service."
    )


def test_warns_about_single_process_scheduler_model():
    with patch("app_http.server.logging.getLogger") as get_logger, \
         patch("app_http.server.has_insecure_bootstrap_admin_password", return_value=False):
        server._log_startup_risk_warnings("postgresql://test:test@localhost:5432/test")

    logger = get_logger.return_value
    logger.warning.assert_any_call(
        "CrawlerScheduler runs in-process and is suitable for a single active backend instance only."
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend/src; python -m pytest tests/unit/test_startup_warnings.py -v`

Expected: `FAIL` because the helper function does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/runtime_config.py
def has_insecure_bootstrap_admin_password() -> bool:
    value = CONFIG_DEFAULTS.get("admin.password", {}).get("value")
    return str(value or "") == "admin123"
```

```python
# backend/src/app_http/server.py
def _log_startup_risk_warnings(db_path: str | Path) -> None:
    logger = logging.getLogger("app.startup")
    if has_insecure_bootstrap_admin_password():
        logger.warning(
            "Bootstrap admin password is still the default value; change it before exposing the service."
        )
    logger.warning(
        "CrawlerScheduler runs in-process and is suitable for a single active backend instance only."
    )
```

And call it in `run_server()` before constructing `CrawlerScheduler`:

```python
    _log_startup_risk_warnings(db_path)
    scheduler = CrawlerScheduler(db_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend/src; python -m pytest tests/unit/test_startup_warnings.py -v`

Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
git add backend/src/runtime_config.py backend/src/app_http/server.py backend/src/tests/unit/test_startup_warnings.py
git commit -m "chore: add startup risk warnings"
```

---

### Task 5: Align README With Real Runtime

**Files:**
- Modify: `backend/README_CN.md`
- Test: none

- [ ] **Step 1: Write the failing test**

```python
# No automated test for this doc-only task.
# Verification will be done via exact content review with rg.
```

- [ ] **Step 2: Run verification to confirm current doc is wrong**

Run: `rg -n "backend/src/config.yaml|http/|crawler/crawler_service.py|app.py" backend/README_CN.md`

Expected: matches showing outdated or misleading references.

- [ ] **Step 3: Write minimal implementation**

Update `backend/README_CN.md` so that it:

```text
- states `backend/src/main.py` is the canonical entry point
- states `backend/src/app.py` is a compatibility entry point
- points actual HTTP implementation to `backend/src/app_http/server.py`
- replaces `http/` directory references with `app_http/`
- replaces nonexistent `backend/src/config.yaml` wording with `DATABASE_URL` + `runtime_config.py` + `system_config`
- clarifies `backend/src/crawler/crawler_service.py` is a compatibility re-export and real scheduler logic is in `backend/src/crawler/scheduler.py`
```

- [ ] **Step 4: Run verification to confirm the doc is aligned**

Run: `rg -n "backend/src/config.yaml|http/|crawler/crawler_service.py" backend/README_CN.md`

Expected: no stale references remain, or only intentionally retained historical context with explicit wording.

- [ ] **Step 5: Commit**

```bash
git add backend/README_CN.md
git commit -m "docs: align backend readme with runtime implementation"
```

---

### Task 6: Run Focused Regression Suite

**Files:**
- Modify: none
- Test: existing and new tests

- [ ] **Step 1: Run the new contract tests**

Run:

```bash
cd backend/src
python -m pytest tests/unit/test_api_contract_system_routes.py -v
python -m pytest tests/unit/test_api_contract_auth_routes.py -v
python -m pytest tests/unit/test_api_contract_legacy_routes.py -v
python -m pytest tests/unit/test_startup_warnings.py -v
```

Expected: all `PASS`

- [ ] **Step 2: Run adjacent existing regression tests**

Run:

```bash
cd backend/src
python -m pytest tests/unit/test_router.py -v
python -m pytest tests/unit/test_admin_auth_error.py -v
python -m pytest tests/unit/test_legacy_frontend_compat.py -v
python -m pytest tests/unit/test_legacy_frontend_compat_image_url.py -v
```

Expected: all `PASS`

- [ ] **Step 3: Run lightweight integration verification if PostgreSQL test target is available**

Run:

```bash
cd backend/src
python -m pytest tests/integration/test_prediction_generation.py -v
```

Expected: `PASS` if `TEST_DATABASE_URL` is configured, otherwise `SKIPPED`

- [ ] **Step 4: Review git diff for response-shape safety**

Run:

```bash
git diff -- backend/src/app_http/server.py backend/src/runtime_config.py backend/README_CN.md backend/src/tests/unit
```

Expected: only tests, logging warnings, and docs changed; no response payload shape changes in route handlers.

- [ ] **Step 5: Commit final verification checkpoint**

```bash
git add backend/src/tests/unit backend/src/app_http/server.py backend/src/runtime_config.py backend/README_CN.md
git commit -m "chore: verify api-contract-safe backend optimization"
```

---

## Self-Review

### Spec coverage

- API contract tests: covered by Tasks 1, 2, 3
- Docs alignment: covered by Task 5
- Startup safety/risk visibility: covered by Task 4
- Final regression proving frontend API shape safety: covered by Task 6

No spec gap remains.

### Placeholder scan

- No `TODO`, `TBD`, or “similar to task N” placeholders remain.
- Commands and file paths are concrete.
- Production code steps are minimal and explicit.

### Type consistency

- Warning helper name is consistent: `has_insecure_bootstrap_admin_password`
- Startup logging helper name is consistent: `_log_startup_risk_warnings`
- Test file names align with the implementation tasks
