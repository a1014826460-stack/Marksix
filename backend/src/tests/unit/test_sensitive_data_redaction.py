from __future__ import annotations

import json
import logging

from app_http import router
from app_http import server
from logger import JsonFormatter
from runtime_config import (
    get_config_effective,
    get_config_history,
    list_configs_effective,
    list_system_configs,
    upsert_system_config,
)
from tables import ensure_admin_tables
from tests.helpers.api_contract import make_ctx


def test_request_log_snapshot_redacts_nested_sensitive_values(monkeypatch):
    ctx = make_ctx(
        "/api/admin/system-config?token=query-token&safe=visible",
        method="POST",
        payload={
            "password": "plain-password",
            "captcha": "ABCD",
            "nested": {"authorization": "Bearer admin-token", "numbers": ["01", "02"]},
            "safe": "visible",
        },
    )
    ctx.state["current_user"] = {"id": 7}
    _ = ctx.body

    extra = router._build_request_log_extra(ctx)

    assert extra["req_params"] == {
        "path": "/api/admin/system-config",
        "query": {"token": "***REDACTED***", "safe": "visible"},
        "body": {
            "password": "***REDACTED***",
            "captcha": "***REDACTED***",
            "nested": {"authorization": "***REDACTED***", "numbers": "***REDACTED***"},
            "safe": "visible",
        },
    }


def test_log_formatter_redacts_sensitive_message_exception_and_stack_values():
    record = logging.LogRecord(
        "test.security",
        logging.ERROR,
        __file__,
        1,
        "request failed for postgresql://admin:db-password@example.test/liuhecai",
        (),
        None,
    )
    try:
        raise RuntimeError("token=session-token numbers=01,02,03,04,05,06,07")
    except RuntimeError:
        record.exc_info = __import__("sys").exc_info()

    serialized = JsonFormatter().format(record)

    assert "db-password" not in serialized
    assert "session-token" not in serialized
    assert "01,02,03,04,05,06,07" not in serialized
    assert "02,03,04,05,06,07" not in serialized


def test_unhandled_server_error_logs_only_the_normalized_path(monkeypatch):
    ctx = make_ctx("/api/admin/example?token=query-token&safe=visible")
    logger = logging.getLogger("test.unhandled")
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(logger, "exception", lambda *args, **kwargs: calls.append((args, kwargs)))

    server._dispatch_error_response(ctx, RuntimeError("password=plain-password"), logger)

    assert calls
    assert calls[0][0] == ("Unhandled error: %s", ctx.command)
    assert calls[0][1]["extra"]["req_params"]["query"]["token"] == "***REDACTED***"
    assert "plain-password" not in json.dumps(calls[0][1], ensure_ascii=False)


def test_secret_config_values_are_never_returned_from_read_apis(tmp_path):
    db_path = str(tmp_path / "config-secret-read.sqlite3")
    ensure_admin_tables(db_path)
    upsert_system_config(
        db_path,
        key="database.default_postgres_dsn",
        value="postgresql://admin:database-secret@db.example/liuhecai",
        value_type="string",
        is_secret=True,
    )

    listed = list_system_configs(db_path, include_secrets=True)
    effective = get_config_effective(db_path, "database.default_postgres_dsn")
    effective_list = list_configs_effective(db_path)
    effective_item = next(item for item in effective_list if item["key"] == "database.default_postgres_dsn")
    history = get_config_history(db_path, key="database.default_postgres_dsn")

    assert next(item for item in listed if item["key"] == "database.default_postgres_dsn")["value_text"] == ""
    assert effective["value"] is None
    assert effective["default_value"] is None
    assert effective["effective_value"] is None
    assert effective_item["value"] == "***已配置***"
    assert effective_item["raw_value"] is None
    assert effective_item["default_value"] is None
    assert effective_item["effective_value"] is None
    assert history["items"][0]["old_value"] == ""
    assert history["items"][0]["new_value"] == "***已配置***"


def test_smtp_password_is_classified_as_secret():
    from runtime_config import CONFIG_DEFAULTS

    assert CONFIG_DEFAULTS["alert.smtp_password"]["is_secret"] == 1


def test_custom_secret_config_is_redacted_from_effective_and_history_reads(tmp_path):
    db_path = str(tmp_path / "custom-config-secret-read.sqlite3")
    ensure_admin_tables(db_path)
    upsert_system_config(
        db_path,
        key="integration.vendor_access",
        value="custom-secret-value",
        value_type="string",
        is_secret=True,
    )

    effective = get_config_effective(db_path, "integration.vendor_access")
    history = get_config_history(db_path, key="integration.vendor_access")

    assert effective["is_secret"] is True
    assert effective["value"] is None
    assert effective["effective_value"] is None
    assert history["items"][0]["new_value"] == "***已配置***"


def test_secret_config_write_and_reset_responses_are_masked(tmp_path):
    from runtime_config import reset_config

    db_path = str(tmp_path / "config-secret-write.sqlite3")
    ensure_admin_tables(db_path)
    written = upsert_system_config(
        db_path,
        key="integration.vendor_access",
        value="write-only-secret",
        value_type="string",
        is_secret=True,
    )
    reset = reset_config(db_path, "admin.password")

    assert written["value_text"] == ""
    assert reset["value_text"] == ""


def test_structured_log_formatter_redacts_sensitive_extra_values():
    record = logging.LogRecord(
        "test.security",
        logging.ERROR,
        __file__,
        1,
        "request failed",
        (),
        None,
    )
    record.req_params = {
        "body": {
            "password": "plain-password",
            "nested": {"res_code": "01,02,03,04,05,06,07"},
        }
    }
    record.result = {"token": "session-token"}

    payload = json.loads(JsonFormatter().format(record))

    serialized = json.dumps(payload, ensure_ascii=False)
    assert "plain-password" not in serialized
    assert "01,02,03,04,05,06,07" not in serialized
    assert "session-token" not in serialized
    assert payload["req_params"]["body"]["password"] == "***REDACTED***"
    assert payload["result"]["token"] == "***REDACTED***"
