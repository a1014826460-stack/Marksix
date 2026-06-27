from __future__ import annotations

import logging

from runtime_config import has_insecure_bootstrap_admin_password


def log_startup_risk_warnings() -> None:
    logger = logging.getLogger("app.startup")
    if has_insecure_bootstrap_admin_password():
        logger.warning(
            "Bootstrap admin password is still the default value; change it before exposing the service."
        )
    logger.warning(
        "CrawlerScheduler runs in-process and is suitable for a single active backend instance only."
    )
