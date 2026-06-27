from __future__ import annotations

from unittest.mock import patch

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
