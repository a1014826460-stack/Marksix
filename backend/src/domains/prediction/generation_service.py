"""Prediction generation helpers shared by admin and domain services."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from db import connect, utc_now
from domains.prediction.site_module_blueprints import (
    get_blocked_items_for_site,
    get_blueprint_name_for_site,
    get_required_mode_ids_for_site,
)
from helpers import load_fixed_data_maps, parse_bool
from predict.mechanisms import get_prediction_config, list_prediction_configs
from utils.created_prediction_store import (
    normalize_color_label,
    upsert_created_prediction_row,
)

_logger = logging.getLogger("domains.prediction.generation")


def _load_site_sync_context(conn: Any, site_id: int | None) -> dict[str, Any] | None:
    if site_id is None:
        return None
    row = conn.execute(
        """
        SELECT id, name, domain, lottery_type_id, web_id, start_web_id, end_web_id
        FROM managed_sites
        WHERE id = ?
        """,
        (int(site_id),),
    ).fetchone()
    return dict(row) if row else None


def get_site_prediction_module_blueprints(site: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return the synced prediction-module blueprint for a site."""
    configs_by_mode_id: dict[int, dict[str, Any]] = {}
    for item in list_prediction_configs():
        try:
            configs_by_mode_id[int(item["default_modes_id"])] = item
        except (TypeError, ValueError):
            continue

    required_mode_ids = get_required_mode_ids_for_site(site)
    missing = [mode_id for mode_id in required_mode_ids if mode_id not in configs_by_mode_id]
    if missing:
        _logger.warning(
            "site blueprint=%s missing prediction configs for mode_ids: %s",
            get_blueprint_name_for_site(site),
            missing,
        )

    blueprints: list[dict[str, Any]] = []
    for index, mode_id in enumerate(required_mode_ids):
        item = configs_by_mode_id.get(mode_id)
        if item is None:
            continue
        payload = dict(item)
        payload["mode_id"] = int(mode_id)
        payload["sort_order"] = index * 10
        payload["blueprint_name"] = get_blueprint_name_for_site(site)
        blueprints.append(payload)
    return blueprints


def get_site_prediction_module_blueprint_by_key(
    mechanism_key: str,
    site: dict[str, Any] | None = None,
) -> dict[str, Any]:
    for item in get_site_prediction_module_blueprints(site):
        if str(item["key"]) == str(mechanism_key):
            return item
    raise ValueError(f"mechanism {mechanism_key} is not in the synced site blueprint")


def sync_site_prediction_modules(conn: Any, site_id: int | None = None) -> None:
    """Keep site_prediction_modules aligned with the resolved site blueprint."""
    now = utc_now()

    site_query = """
        SELECT id, name, domain, lottery_type_id, web_id, start_web_id, end_web_id
        FROM managed_sites
    """
    site_params: tuple[Any, ...] = ()
    if site_id is not None:
        site_query += " WHERE id = ?"
        site_params = (int(site_id),)
    site_rows = conn.execute(site_query, site_params).fetchall()

    for site_row in site_rows:
        site_data = dict(site_row)
        current_site_id = int(site_data["id"])
        blueprints = get_site_prediction_module_blueprints(site_data)
        existing_rows = conn.execute(
            """
            SELECT mechanism_key, status, created_at
            FROM site_prediction_modules
            WHERE site_id = ?
            """,
            (current_site_id,),
        ).fetchall()
        existing_by_key = {str(row["mechanism_key"]): dict(row) for row in existing_rows}

        for item in blueprints:
            existing = existing_by_key.get(str(item["key"]))
            if existing:
                conn.execute(
                    """
                    UPDATE site_prediction_modules
                    SET mode_id = ?, sort_order = ?, updated_at = ?
                    WHERE site_id = ? AND mechanism_key = ?
                    """,
                    (
                        int(item["mode_id"]),
                        int(item["sort_order"]),
                        now,
                        current_site_id,
                        str(item["key"]),
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO site_prediction_modules (
                        site_id, mechanism_key, mode_id, status, sort_order, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        current_site_id,
                        str(item["key"]),
                        int(item["mode_id"]),
                        1,
                        int(item["sort_order"]),
                        now,
                        now,
                    ),
                )

        blocked_items = get_blocked_items_for_site(site_data)
        if blocked_items:
            _logger.warning(
                "site_id=%s blueprint=%s blocked frontend items not synced into site_prediction_modules: %s",
                current_site_id,
                get_blueprint_name_for_site(site_data),
                [str(item.get("page_title") or item.get("frontend_module") or "") for item in blocked_items],
            )


def resolve_prediction_table_for_mode(
    conn: Any,
    mode_id: int,
    fallback_table: str = "",
) -> str:
    """Resolve the payload table name for one mode_id."""
    resolved_mode_id = int(mode_id or 0)
    if resolved_mode_id > 0 and conn.table_exists("mode_payload_tables"):
        row = conn.execute(
            """
            SELECT table_name
            FROM mode_payload_tables
            WHERE modes_id = ?
            LIMIT 1
            """,
            (resolved_mode_id,),
        ).fetchone()
        if row and str(row["table_name"] or "").strip():
            return str(row["table_name"]).strip()
    if fallback_table:
        return str(fallback_table)
    if resolved_mode_id > 0:
        return f"mode_payload_{resolved_mode_id}"
    return ""


def parse_issue_range_value(value: Any, label: str) -> tuple[int, int]:
    """Parse a frontend issue string like 2026001 into (year, term)."""
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) < 5:
        raise ValueError(f"{label} format is invalid, expected a full issue like 2026001")

    year_text = digits[:4]
    term_text = digits[4:]
    if not year_text.isdigit():
        raise ValueError(f"{label} year format is invalid")
    if not term_text.isdigit():
        raise ValueError(f"{label} term format is invalid")

    year = int(year_text)
    term = int(term_text)
    if term == 0:
        raise ValueError(f"{label} term cannot be 0")
    return year, term


def build_generated_prediction_row_data(
    *,
    mode_id: int,
    lottery_type: str = "",
    year: str = "",
    term: str = "",
    web_value: str = "",
    res_code: str = "",
    generated_content: Any,
    db_path: str | Path = "",
) -> dict[str, Any]:
    """Convert predict() output into one created-schema row payload."""
    web_val = str(web_value or "").strip()
    if not web_val:
        raise ValueError("web_value cannot be empty")
    if not web_val.isdigit():
        raise ValueError("web_value must be an integer string")

    row_data: dict[str, Any] = {
        "type": str(lottery_type or ""),
        "year": str(year or ""),
        "term": str(term or ""),
        "web": web_val,
        "web_id": int(web_val),
        "modes_id": int(mode_id) if mode_id else 0,
        "res_code": str(res_code or ""),
    }

    if res_code and db_path:
        codes = [c.strip() for c in str(res_code).split(",") if c.strip()]
        if len(codes) == 7:
            special = codes[-1]
            with connect(db_path) as tmp_conn:
                zmap, cmap = load_fixed_data_maps(tmp_conn)
            row_data["res_sx"] = zmap.get(special, "")
            color = cmap.get(special, "")
            if color:
                row_data["res_color"] = normalize_color_label(color)

    term_int = int(term) if str(term or "").strip().isdigit() else 0
    if term_int > 0:
        rem = term_int % 3
        if rem == 2:
            start_val = term_int
        elif rem == 0:
            start_val = max(1, term_int - 1)
        else:
            start_val = max(1, term_int - 2)
        end_val = start_val + 2
        if isinstance(generated_content, dict):
            generated_content["start"] = str(start_val)
            generated_content["end"] = str(end_val)

    if isinstance(generated_content, dict):
        for key, value in generated_content.items():
            if key == "_labels":
                continue
            if isinstance(value, (list, dict, tuple, set)):
                row_data[key] = json.dumps(value, ensure_ascii=False)
            else:
                row_data[key] = value
    elif isinstance(generated_content, list):
        row_data["content"] = json.dumps(generated_content, ensure_ascii=False)
    else:
        row_data["content"] = str(generated_content or "")

    return row_data
