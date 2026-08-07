from __future__ import annotations

from unittest.mock import MagicMock, patch

from app_http import server, startup_warnings


def test_run_server_logs_startup_risk_warnings_without_starting_scheduler():
    with patch("app_http.server.ensure_prediction_configs_loaded"), \
         patch("app_http.server.ensure_admin_tables"), \
         patch("app_http.server.init_logging"), \
         patch("app_http.server.create_cache_store") as create_cache_store, \
         patch("app_http.server.ThreadingHTTPServer") as http_server, \
         patch("app_http.server.log_startup_risk_warnings") as warnings:
        http_server.return_value.serve_forever = MagicMock(side_effect=KeyboardInterrupt)

        try:
            server.run_server("127.0.0.1", 8000, "postgresql://test:test@localhost:5432/test")
        except KeyboardInterrupt:
            pass

    warnings.assert_called_once_with()
    create_cache_store.assert_called_once_with()
    assert http_server.return_value.public_draw_snapshots is not None
    http_server.return_value.server_close.assert_called_once_with()


def test_log_startup_risk_warnings_reports_dedicated_scheduler_worker():
    with patch("app_http.startup_warnings.logging.getLogger") as get_logger, \
         patch("app_http.startup_warnings.has_insecure_bootstrap_admin_password", return_value=False):
        startup_warnings.log_startup_risk_warnings()

    get_logger.return_value.warning.assert_any_call(
        "Run the scheduler-worker service exactly once (or use its database task locks); HTTP API instances do not execute scheduler timers."
    )
