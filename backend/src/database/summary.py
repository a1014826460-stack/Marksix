"""数据库内容摘要，用于监控和诊断。

仅查询已有表，不触发 side-effect。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from database.connection import connect, detect_database_engine, quote_identifier


def database_summary(db_path: str | Path) -> dict[str, Any]:
    """返回数据库内容轻量摘要，用于监控。

    不会调用 ``ensure_admin_tables``——仅查询已有表，
    避免 side-effect 并确保摘要准确。
    """
    with connect(db_path) as conn:

        def count_table(table_name: str) -> int:
            if not conn.table_exists(table_name):
                return 0
            row = conn.execute(
                f"SELECT COUNT(*) AS total FROM {quote_identifier(table_name)}"
            ).fetchone()
            return int(row["total"] or 0)

        # prediction_mechanisms: 从 PREDICTION_CONFIGS 获取机制数量
        try:
            from predict.mechanisms import list_prediction_configs
            prediction_count = len(list_prediction_configs())
        except Exception:
            prediction_count = 0

        return {
            "db_target": str(db_path),
            "db_engine": detect_database_engine(db_path),
            "admin_users": count_table("admin_users"),
            "lottery_types": count_table("lottery_types"),
            "lottery_draws": count_table("lottery_draws"),
            "sites": count_table("managed_sites"),
            "sites_with_web_id": _count_sites_with_web_id(conn) if conn.table_exists("managed_sites") else 0,
            "fetched_modes": count_table("fetched_modes"),
            "fetched_mode_records": count_table("fetched_mode_records"),
            "mode_payload_tables": count_table("mode_payload_tables"),
            "text_history_mappings": count_table("text_history_mappings"),
            "site_prediction_modules": count_table("site_prediction_modules"),
            "legacy_image_assets": count_table("legacy_image_assets"),
            "prediction_mechanisms": prediction_count,
        }


def _count_sites_with_web_id(conn: Any) -> int:
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM managed_sites WHERE web_id IS NOT NULL"
        ).fetchone()
        return int(row["total"] or 0)
    except Exception:
        return 0
