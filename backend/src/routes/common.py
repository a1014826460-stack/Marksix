"""Shared route helpers and compatibility exports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crawler.crawler_service import crawl_and_generate_for_type
from jobs.handlers import (  # noqa: F401 - compatibility exports
    create_fetch_run,
    finish_fetch_run,
    get_background_job,
    list_fetch_runs,
    start_background_job,
)


def crawl_and_generate(db_path: str | Path, lottery_type_id: int) -> dict[str, Any]:
    return crawl_and_generate_for_type(db_path, lottery_type_id)


def fetch_site_data(
    db_path: str | Path,
    site_id: int,
    *,
    normalize_after: bool = True,
    build_text_mappings_after: bool = True,
) -> dict[str, Any]:
    del normalize_after, build_text_mappings_after
    message = (
        "fetch_site_data is deprecated: managed_sites no longer stores legacy "
        "crawler fields. Use prediction-modules sync/generate endpoints instead."
    )
    run_id = create_fetch_run(db_path, site_id)
    finish_fetch_run(db_path, run_id, "error", message, 0, 0)
    return {
        "ok": False,
        "run_id": run_id,
        "status": "deprecated",
        "message": message,
    }
