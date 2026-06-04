"""Prediction generation helpers shared by admin and domain services."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from db import connect, utc_now
from domains.sites.repository import find_site_by_id
from domains.prediction.site_module_blueprints import (
    get_blocked_items_for_site,
    get_blueprint_name_for_site,
    get_known_unavailable_mode_ids_for_site,
    get_required_mode_ids_for_site,
)
from helpers import load_fixed_data_maps, parse_bool
from predict.mechanisms import (
    ensure_prediction_configs_loaded,
    get_prediction_config,
    list_prediction_configs,
)
from utils.created_prediction_store import (
    normalize_color_label,
    upsert_created_prediction_row,
)

_logger = logging.getLogger("domains.prediction.generation")


def _load_site_sync_context(conn: Any, site_id: int | None) -> dict[str, Any] | None:
    if site_id is None:
        return None
    return find_site_by_id(conn, int(site_id))


def _load_site_module_rows(conn: Any, site_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT mechanism_key, mode_id, status, sort_order, title
        FROM site_prediction_modules
        WHERE site_id = ?
        ORDER BY sort_order, id
        """,
        (int(site_id),),
    ).fetchall()
    return [dict(row) for row in rows]


def _list_prediction_configs_for_runtime(
    conn: Any | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    resolved_target = ""
    if db_path is not None:
        resolved_target = str(db_path)
    elif conn is not None:
        resolved_target = str(getattr(conn, "target", "") or "")

    if resolved_target:
        ensure_prediction_configs_loaded(resolved_target)
        return list_prediction_configs()
    return list_prediction_configs()


def get_site_prediction_module_blueprints(
    site: dict[str, Any] | None = None,
    *,
    conn: Any | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return the synced prediction-module blueprint for a site."""
    configs_by_mode_id: dict[int, dict[str, Any]] = {}
    for item in _list_prediction_configs_for_runtime(conn, db_path):
        try:
            configs_by_mode_id[int(item["default_modes_id"])] = item
        except (TypeError, ValueError):
            continue

    required_mode_ids = get_required_mode_ids_for_site(site)
    missing = [mode_id for mode_id in required_mode_ids if mode_id not in configs_by_mode_id]
    known_unavailable = set(get_known_unavailable_mode_ids_for_site(site))
    expected_missing = [mode_id for mode_id in missing if mode_id in known_unavailable]
    unexpected_missing = [mode_id for mode_id in missing if mode_id not in known_unavailable]
    if unexpected_missing:
        _logger.warning(
            "site blueprint=%s missing prediction configs for mode_ids: %s",
            get_blueprint_name_for_site(site),
            unexpected_missing,
        )
    if expected_missing:
        _logger.info(
            "site blueprint=%s skipping known unavailable mode_ids: %s",
            get_blueprint_name_for_site(site),
            expected_missing,
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


def get_site_prediction_modules_from_db_or_blueprint(
    conn: Any,
    site: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Use DB modules as the runtime source of truth; fall back to blueprint only for empty sites."""
    if site is not None:
        try:
            site_id = int(site.get("id") or 0)
        except (TypeError, ValueError):
            site_id = 0
        if site_id > 0:
            existing_rows = _load_site_module_rows(conn, site_id)
            if existing_rows:
                configs_by_key = {
                    str(item["key"]): dict(item)
                    for item in _list_prediction_configs_for_runtime(conn)
                }
                resolved: list[dict[str, Any]] = []
                for row in existing_rows:
                    mechanism_key = str(row.get("mechanism_key") or "").strip()
                    config = configs_by_key.get(mechanism_key)
                    if not config:
                        _logger.warning(
                            "site_id=%s has site_prediction_modules row with unknown mechanism_key=%s",
                            site_id,
                            mechanism_key,
                        )
                        continue
                    payload = dict(config)
                    payload["mode_id"] = int(row.get("mode_id") or config["default_modes_id"] or 0)
                    payload["sort_order"] = int(row.get("sort_order") or 0)
                    payload["status"] = int(row.get("status") or 0)
                    payload["title"] = str(row.get("title") or payload.get("title") or "")
                    payload["blueprint_name"] = "database"
                    resolved.append(payload)
                if resolved:
                    return resolved
    return get_site_prediction_module_blueprints(site, conn=conn)


def initialize_site_prediction_modules_from_blueprint(
    conn: Any,
    site: dict[str, Any] | None = None,
) -> int:
    """Populate site_prediction_modules only when the site has no runtime module rows yet."""
    if not site:
        return 0

    try:
        site_id = int(site.get("id") or 0)
    except (TypeError, ValueError):
        site_id = 0
    if site_id <= 0:
        return 0

    if _load_site_module_rows(conn, site_id):
        return 0

    now = utc_now()
    inserted = 0
    for item in get_site_prediction_module_blueprints(site, conn=conn):
        conn.execute(
            """
            INSERT INTO site_prediction_modules (
                site_id, mechanism_key, mode_id, status, sort_order, created_at, updated_at, title
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(site_id, mechanism_key) DO NOTHING
            """,
            (
                site_id,
                str(item["key"]),
                int(item["mode_id"]),
                1,
                int(item["sort_order"]),
                now,
                now,
                str(item.get("title") or ""),
            ),
        )
        inserted += 1
    return inserted


def get_site_prediction_module_blueprint_by_key(
    mechanism_key: str,
    site: dict[str, Any] | None = None,
    *,
    conn: Any | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    for item in get_site_prediction_module_blueprints(site, conn=conn, db_path=db_path):
        if str(item["key"]) == str(mechanism_key):
            return item
    raise ValueError(f"mechanism {mechanism_key} is not in the synced site blueprint")


def sync_site_prediction_modules(conn: Any, site_id: int | None = None) -> None:
    """Keep site_prediction_modules aligned with the site's blueprint.

    Existing rows remain the database source of truth. The sync only inserts
    blueprint modules that are missing, which lets a partially initialized site
    pick up newly confirmed modules without losing local status/sort choices.
    """
    site_query = """
        SELECT id
        FROM managed_sites
    """
    site_params: tuple[Any, ...] = ()
    if site_id is not None:
        site_query += " WHERE id = ?"
        site_params = (int(site_id),)
    site_rows = conn.execute(site_query, site_params).fetchall()

    for site_row in site_rows:
        current_site_id = int(site_row["id"])
        site_data = _load_site_sync_context(conn, current_site_id) or {"id": current_site_id}
        existing_rows = _load_site_module_rows(conn, current_site_id)
        if not existing_rows:
            initialize_site_prediction_modules_from_blueprint(conn, site_data)
        else:
            existing_keys = {
                str(row.get("mechanism_key") or "").strip()
                for row in existing_rows
                if str(row.get("mechanism_key") or "").strip()
            }
            now = utc_now()
            inserted = 0
            for item in get_site_prediction_module_blueprints(site_data, conn=conn):
                mechanism_key = str(item["key"])
                if mechanism_key in existing_keys:
                    continue
                conn.execute(
                    """
                    INSERT INTO site_prediction_modules (
                        site_id, mechanism_key, mode_id, status, sort_order, created_at, updated_at, title
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(site_id, mechanism_key) DO NOTHING
                    """,
                    (
                        current_site_id,
                        mechanism_key,
                        int(item["mode_id"]),
                        1,
                        int(item["sort_order"]),
                        now,
                        now,
                        str(item.get("title") or ""),
                    ),
                )
                inserted += 1
            if inserted:
                _logger.info(
                    "site_id=%s blueprint=%s inserted %s missing prediction modules",
                    current_site_id,
                    get_blueprint_name_for_site(site_data),
                    inserted,
                )

        blocked_items = get_blocked_items_for_site(site_data)
        if blocked_items:
            _logger.info(
                "site_id=%s blueprint=%s keeping blocked frontend items informational: %s",
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

    if int(mode_id or 0) == 198:
        label = str(generated_content or "").strip()
        if label in {"大数", "小数", "家禽", "野兽"}:
            row_data["dx"] = label
        elif label in {"单数", "双数"}:
            row_data["ds"] = label

    return row_data
