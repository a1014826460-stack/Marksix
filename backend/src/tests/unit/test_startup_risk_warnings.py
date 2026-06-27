from __future__ import annotations

from unittest.mock import patch

from app_http import startup_warnings


def test_log_startup_risk_warnings_reports_default_admin_password():
    with patch("app_http.startup_warnings.logging.getLogger") as get_logger, \
         patch("app_http.startup_warnings.has_insecure_bootstrap_admin_password", return_value=True):
        startup_warnings.log_startup_risk_warnings()

    logger = get_logger.return_value
    logger.warning.assert_any_call(
        "Bootstrap admin password is still the default value; change it before exposing the service."
    )


def test_log_startup_risk_warnings_reports_single_process_scheduler():
    with patch("app_http.startup_warnings.logging.getLogger") as get_logger, \
         patch("app_http.startup_warnings.has_insecure_bootstrap_admin_password", return_value=False):
        startup_warnings.log_startup_risk_warnings()

    logger = get_logger.return_value
    logger.warning.assert_any_call(
        "CrawlerScheduler runs in-process and is suitable for a single active backend instance only."
    )
