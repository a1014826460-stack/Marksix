"""Deprecated site-level fetch chain.

The historical managed-site fetch path has been retired. Site data should now
be maintained through admin-managed module configuration and manual generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.errors import AppError


class DeprecatedSiteFetchError(AppError):
    status_code = 410
    code = "SITE_FETCH_DEPRECATED"


def deprecated_site_fetch_payload(site_id: int) -> dict[str, Any]:
    return {
        "ok": False,
        "code": "SITE_FETCH_DEPRECATED",
        "message": "站点抓取链路已废弃，请改用后台管理员手动维护模块并手动生成资料。",
        "site_id": int(site_id),
        "replacements": [
            "POST /api/admin/sites/{site_id}/prediction-modules/sync",
            "GET /api/admin/sites/{site_id}/prediction-modules",
            "POST /api/admin/sites/{site_id}/prediction-modules",
            "POST /api/admin/sites/{site_id}/prediction-modules/generate-all",
            "POST /api/admin/normalize",
            "POST /api/admin/text-mappings",
        ],
    }


def fetch_site_data(
    db_path: str | Path,
    site_id: int,
    *,
    normalize_after: bool = True,
    build_text_mappings_after: bool = True,
) -> dict[str, Any]:
    raise DeprecatedSiteFetchError(
        "站点抓取链路已废弃，请使用 prediction-modules/sync + generate-all 的人工路径。"
    )
