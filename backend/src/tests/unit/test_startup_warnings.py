from __future__ import annotations

from unittest.mock import MagicMock, patch

from app_http import server


def test_run_server_logs_startup_risk_warnings_before_scheduler_start():
    with patch("app_http.server.ensure_prediction_configs_loaded"), \
         patch("app_http.server.ensure_admin_tables"), \
         patch("app_http.server.init_logging"), \
         patch("app_http.server.ThreadingHTTPServer") as http_server, \
         patch("app_http.server.CrawlerScheduler") as scheduler, \
         patch("app_http.server.log_startup_risk_warnings") as warnings:
        http_server.return_value.serve_forever = MagicMock(side_effect=KeyboardInterrupt)

        try:
            server.run_server("127.0.0.1", 8000, "postgresql://test:test@localhost:5432/test")
        except KeyboardInterrupt:
            pass

    warnings.assert_called_once_with()
    scheduler.return_value.start.assert_called_once_with()
