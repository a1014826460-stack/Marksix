"""旧站兼容 API — post-list / current-term / module-rows。

从 app.py 提取，不改变任何函数签名与行为。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PREDICT_ROOT = Path(__file__).resolve().parents[1] / "predict"
if str(_PREDICT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PREDICT_ROOT))

from db import connect as db_connect, quote_identifier
from helpers import (
    apply_lottery_draw_overlay,
    build_mode_payload_filters, build_mode_payload_order_clause, load_fixed_data_maps,
    merge_preferred_mode_payload_rows, load_mode_payload_rows_from_source,
    normalize_issue_part, parse_issue_int, split_csv,
)
from mechanisms import get_prediction_config  # noqa: E402
from utils.created_prediction_store import (  # noqa: E402
    CREATED_SCHEMA_NAME, created_table_exists, normalize_color_label,
    quote_qualified_identifier as quote_schema_table, schema_table_exists,
    table_column_names,
)


def connect(db_path: str | Path) -> Any:
    return db_connect(db_path)

def _ensure_tables(db_path):
    from tables import ensure_admin_tables as _eat
    _eat(db_path)


def list_legacy_post_images(
    db_path: str | Path,
    *,
    source_pc: int | None = None,
    source_web: int | None = None,
    source_type: int | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return old page image cards using stored PostgreSQL path mappings.

    We only expose persisted rows here. If a mapping is missing, the sync step in
    `ensure_admin_tables` is responsible for repairing it from disk.
    """
    _ensure_tables(db_path)
    with connect(db_path) as conn:
        clauses = ["enabled = 1", "source_key = ?"]
        params: list[Any] = ["legacy-post-list"]

        if source_pc is not None:
            clauses.append("source_pc = ?")
            params.append(source_pc)
        if source_web is not None:
            clauses.append("source_web = ?")
            params.append(source_web)
        if source_type is not None:
            clauses.append("source_type = ?")
            params.append(source_type)

        params.append(max(1, int(limit)))
        rows = conn.execute(
            f"""
            SELECT id, title, file_name, storage_path, legacy_upload_path, cover_image,
                   mime_type, file_size, sort_order, enabled
            FROM legacy_image_assets
            WHERE {' AND '.join(clauses)}
            ORDER BY sort_order, id
            LIMIT ?
            """,
            params,
        ).fetchall()

    return [dict(row) for row in rows]


def get_legacy_current_term(db_path: str | Path, lottery_type_id: int = 1) -> dict[str, Any]:
    """旧静态页会先读取当前已开奖期号，再自行推导下一预测期。"""
    _ensure_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT year, term, next_term
            FROM lottery_draws
            WHERE lottery_type_id = ?
              AND is_opened = 1
            ORDER BY year DESC, term DESC, id DESC
            LIMIT 1
            """,
            (lottery_type_id,),
        ).fetchone()
        if row:
            data = dict(row)
            current_term = int(data.get("term") or 0)
            next_term = data.get("next_term") or (current_term + 1 if current_term else "")
            return {
                "lottery_type_id": lottery_type_id,
                "term": str(data.get("term") or ""),
                "issue": f"{data.get('year') or ''}{data.get('term') or ''}",
                "next_term": str(next_term or ""),
            }

        # 旧库迁移后如果还没补 lottery_draws，也允许从历史预测表回退推导当前期号。
        # 这里选用旧前台确实展示的常用玩法表，优先找到任意一条已开奖记录。
        fallback_modes = (43, 38, 46, 50)
        for modes_id in fallback_modes:
            meta = conn.execute(
                """
                SELECT table_name
                FROM mode_payload_tables
                WHERE modes_id = ?
                LIMIT 1
                """,
                (modes_id,),
            ).fetchone()
            if not meta:
                continue

            table_name = str(meta["table_name"])
            if not conn.table_exists(table_name):
                continue

            legacy_row = conn.execute(
                f"""
                SELECT year, term
                FROM {quote_identifier(table_name)}
                WHERE res_code IS NOT NULL
                  AND res_code != ''
                ORDER BY CAST(NULLIF(year, '') AS INTEGER) DESC NULLS LAST,
                         CAST(NULLIF(term, '') AS INTEGER) DESC NULLS LAST,
                         CAST(
                             COALESCE(NULLIF(CAST(source_record_id AS TEXT), ''), CAST(id AS TEXT))
                             AS INTEGER
                         ) DESC
                LIMIT 1
                """
            ).fetchone()
            if not legacy_row:
                continue

            year = str(legacy_row["year"] or "")
            term = str(legacy_row["term"] or "")
            next_term = ""
            try:
                next_term = str(int(term) + 1) if term else ""
            except ValueError:
                next_term = ""

            return {
                "lottery_type_id": lottery_type_id,
                "term": term,
                "issue": f"{year}{term}",
                "next_term": next_term,
            }

        return {
            "lottery_type_id": lottery_type_id,
            "term": "",
            "issue": "",
            "next_term": "",
        }


def load_legacy_mode_rows(
    db_path: str | Path,
    *,
    modes_id: int,
    limit: int = 10,
    web: int | None = None,
    type_value: int | None = None,
) -> dict[str, Any]:
    """给旧前端模块提供原始历史表数据，优先返回 created 预测结果。"""
    with connect(db_path) as conn:
        meta = conn.execute(
            """
            SELECT modes_id, title, table_name, record_count
            FROM mode_payload_tables
            WHERE modes_id = ?
            LIMIT 1
            """,
            (modes_id,),
        ).fetchone()
        if not meta:
            raise KeyError(f"modes_id={modes_id} 不存在")

        meta_dict = dict(meta)
        table_name = str(meta_dict["table_name"])
        has_public_table = conn.table_exists(table_name)
        has_created_table = (
            getattr(conn, "engine", "") == "postgres"
            and created_table_exists(conn, table_name)
        )
        if not has_public_table and not has_created_table:
            return {
                **meta_dict,
                "rows": [],
            }

        preferred_rows: list[dict[str, Any]] = []
        if has_created_table:
            preferred_rows = load_mode_payload_rows_from_source(
                conn,
                table_name=table_name,
                schema_name=CREATED_SCHEMA_NAME,
                limit=max(limit * 2, limit),
                lottery_type_id=type_value,
                web_exact=web,
                require_result_consistency=True,
            )

        fallback_rows: list[dict[str, Any]] = []
        if len(preferred_rows) < limit and has_public_table:
            fallback_rows = load_mode_payload_rows_from_source(
                conn,
                table_name=table_name,
                limit=max(limit * 3, limit),
                lottery_type_id=type_value,
                web_exact=web,
                require_result_consistency=True,
            )

        rows = merge_preferred_mode_payload_rows(preferred_rows, fallback_rows, limit)
        rows = apply_lottery_draw_overlay(
            conn,
            rows,
            default_lottery_type_id=type_value,
        )

        return {
            **meta_dict,
            "rows": rows,
        }

