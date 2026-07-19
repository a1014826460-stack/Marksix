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
        "Run the scheduler-worker service exactly once (or use its database task locks); HTTP API instances do not execute scheduler timers."
    )
