"""Repository helpers for legacy compatibility endpoints."""

from __future__ import annotations

from typing import Any

from db import quote_identifier


def list_legacy_post_image_assets(
    conn: Any,
    *,
    source_pc: int | None = None,
    source_web: int | None = None,
    source_type: int | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    clauses = ["enabled = 1", "source_key = ?"]
    params: list[Any] = ["legacy-post-list"]

    if source_pc is not None:
        clauses.append("source_pc = ?")
        params.append(int(source_pc))
    if source_web is not None:
        clauses.append("source_web = ?")
        params.append(int(source_web))
    if source_type is not None:
        clauses.append("source_type = ?")
        params.append(int(source_type))

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


def list_frontend_post_images(
    conn: Any,
    *,
    pc: int,
    web_id: int,
    type_value: int,
) -> list[dict[str, Any]]:
    if not conn.table_exists("legacy_image_assets"):
        return []

    def query_rows(target_pc: int) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT id, title, cover_image, sort_order
            FROM legacy_image_assets
            WHERE enabled = 1
              AND source_key = ?
              AND source_pc = ?
              AND source_web = ?
              AND source_type = ?
            ORDER BY sort_order, id
            """,
            ("legacy-post-list", int(target_pc), int(web_id), int(type_value)),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "title": row["title"] or "",
                "cover_image": row["cover_image"] or "",
                "sort_order": row["sort_order"] or 0,
            }
            for row in rows
        ]

    rows = query_rows(pc)
    if not rows and int(pc) == 72:
        rows = query_rows(305)
    return rows


def get_latest_opened_term(conn: Any, *, lottery_type_id: int) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT year, term, next_term
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND is_opened = 1
        ORDER BY year DESC, term DESC, id DESC
        LIMIT 1
        """,
        (int(lottery_type_id),),
    ).fetchone()
    if not row:
        return {
            "lottery_type_id": int(lottery_type_id),
            "term": "",
            "issue": "",
            "next_term": "",
        }

    term = int(row["term"] or 0)
    next_term = row["next_term"] or (term + 1 if term else "")
    return {
        "lottery_type_id": int(lottery_type_id),
        "term": str(row["term"] or ""),
        "issue": f"{row['year'] or ''}{row['term'] or ''}",
        "next_term": str(next_term or ""),
    }


def get_mode_payload_table_name(conn: Any, *, modes_id: int) -> str:
    if not conn.table_exists("mode_payload_tables"):
        return ""
    row = conn.execute(
        """
        SELECT table_name
        FROM mode_payload_tables
        WHERE modes_id = ?
        LIMIT 1
        """,
        (int(modes_id),),
    ).fetchone()
    if not row:
        return ""
    table_name = str(row["table_name"] or "").strip()
    return table_name if table_name and conn.table_exists(table_name) else ""


def get_mode_payload_metadata(conn: Any, *, modes_id: int) -> dict[str, Any] | None:
    if not conn.table_exists("mode_payload_tables"):
        return None
    row = conn.execute(
        """
        SELECT modes_id, title, table_name, record_count
        FROM mode_payload_tables
        WHERE modes_id = ?
        LIMIT 1
        """,
        (int(modes_id),),
    ).fetchone()
    return dict(row) if row else None


def find_latest_result_term_in_payload_table(conn: Any, *, table_name: str) -> dict[str, Any] | None:
    if not table_name or not conn.table_exists(table_name):
        return None
    columns = set(conn.table_columns(table_name))
    if not {"year", "term", "res_code"}.issubset(columns):
        return None

    order_parts = [
        "CAST(NULLIF(year, '') AS INTEGER) DESC NULLS LAST",
        "CAST(NULLIF(term, '') AS INTEGER) DESC NULLS LAST",
    ]
    if "source_record_id" in columns:
        order_parts.append(
            "CAST(COALESCE(NULLIF(CAST(source_record_id AS TEXT), ''), CAST(id AS TEXT)) AS INTEGER) DESC"
        )
    elif "id" in columns:
        order_parts.append("CAST(id AS INTEGER) DESC")

    row = conn.execute(
        f"""
        SELECT year, term
        FROM {quote_identifier(table_name)}
        WHERE res_code IS NOT NULL
          AND res_code != ''
        ORDER BY {', '.join(order_parts)}
        LIMIT 1
        """
    ).fetchone()
    return dict(row) if row else None
