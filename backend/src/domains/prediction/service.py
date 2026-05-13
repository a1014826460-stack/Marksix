"""Prediction domain services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.errors import ValidationError
from db import connect, utc_now
from helpers import parse_bool
from predict.common import predict
from predict.mechanisms import (
    ensure_prediction_configs_loaded,
    get_prediction_config,
    list_prediction_configs,
)
from runtime_config import get_config
from tables import ensure_admin_tables
from utils.created_prediction_store import (
    CREATED_SCHEMA_NAME,
    quote_identifier,
    quote_qualified_identifier,
    schema_table_exists,
    table_column_names,
    validate_mode_payload_table_name,
)

from .generation_service import parse_issue_range_value, resolve_prediction_table_for_mode
from .repository import (
    delete_module,
    find_site_module,
    get_enabled_module_rows,
    insert_module,
    list_site_modules,
    update_module,
)

MAX_BULK_DELETE_ROWS = 1000


def list_site_prediction_modules(db_path: str | Path, site_id: int) -> dict[str, Any]:
    from domains.sites.service import get_site

    ensure_prediction_configs_loaded(db_path)
    ensure_admin_tables(db_path)
    site = get_site(db_path, site_id)

    with connect(db_path) as conn:
        mode_titles: dict[int, str] = {}
        if conn.table_exists("mode_payload_tables"):
            for row in conn.execute(
                "SELECT modes_id, title FROM mode_payload_tables"
            ).fetchall():
                try:
                    mode_titles[int(row["modes_id"])] = str(row["title"] or "")
                except (TypeError, ValueError):
                    continue

        modules = list_site_modules(conn, site_id)
        for module in modules:
            mechanism_key = str(module.get("mechanism_key") or "").strip()
            try:
                config = get_prediction_config(mechanism_key)
            except ValueError:
                config = None

            if config is not None:
                module["default_modes_id"] = int(config.default_modes_id or 0)
                module["default_table"] = str(config.default_table or "")

            try:
                resolved_mode_id = int(module.get("mode_id") or 0)
            except (TypeError, ValueError):
                resolved_mode_id = 0
            if resolved_mode_id <= 0 and config is not None:
                resolved_mode_id = int(config.default_modes_id or 0)

            fallback_title = str(config.title or "") if config is not None else ""
            resolved_title = mode_titles.get(resolved_mode_id, fallback_title)
            if resolved_title:
                module["display_title"] = resolved_title
                module["tables_title"] = resolved_title
                module["title"] = resolved_title
            if resolved_mode_id > 0:
                module["resolved_mode_id"] = resolved_mode_id

        configured_keys = {str(module["mechanism_key"]) for module in modules}
        available_mechanisms: list[dict[str, Any]] = []
        for item in list_prediction_configs(db_path):
            key = str(item["key"])
            default_mode_id = int(item["default_modes_id"] or 0)
            available_mechanisms.append(
                {
                    "key": key,
                    "title": mode_titles.get(default_mode_id, str(item["title"] or "")),
                    "default_modes_id": default_mode_id,
                    "default_table": str(item["default_table"] or ""),
                    "configured": key in configured_keys,
                }
            )

        return {
            "site": site,
            "modules": modules,
            "available_mechanisms": available_mechanisms,
        }


def add_site_prediction_module(
    db_path: str | Path,
    site_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    ensure_prediction_configs_loaded(db_path)
    ensure_admin_tables(db_path)
    now = utc_now()
    mechanism_key = str(payload.get("mechanism_key") or "").strip()
    if not mechanism_key:
        raise ValueError("mechanism_key 不能为空")

    config = get_prediction_config(mechanism_key)
    mode_id = int(payload.get("mode_id") or 0)
    if mode_id <= 0:
        mode_id = int(config.default_modes_id or 0)

    status = 1 if parse_bool(payload.get("status"), True) else 0
    sort_order = int(payload.get("sort_order") or 0)

    with connect(db_path) as conn:
        return insert_module(conn, site_id, mechanism_key, mode_id, status, sort_order, now)


def update_site_prediction_module(
    db_path: str | Path,
    site_id: int,
    module_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    now = utc_now()

    with connect(db_path) as conn:
        existing = find_site_module(conn, site_id, module_id)
        if not existing:
            raise KeyError(f"module_id={module_id} 在 site_id={site_id} 下不存在")

        raw_existing_key = str(existing["mechanism_key"] or "").strip()
        raw_payload_key = payload.get("mechanism_key")
        mechanism_key = (
            str(raw_payload_key).strip()
            if raw_payload_key is not None
            else raw_existing_key
        )

        config = None
        if raw_payload_key is not None or payload.get("mode_id") is not None:
            config = get_prediction_config(mechanism_key)

        mode_id = int(payload.get("mode_id") or existing.get("mode_id") or 0)
        if mode_id <= 0 and config is not None:
            mode_id = int(config.default_modes_id or 0)

        status = 1 if parse_bool(payload.get("status"), bool(existing.get("status"))) else 0
        sort_order = int(payload.get("sort_order") or existing.get("sort_order") or 0)

        row = update_module(
            conn,
            module_id,
            site_id,
            mechanism_key,
            mode_id,
            status,
            sort_order,
            now,
        )
        if not row:
            raise KeyError(f"module_id={module_id} 在 site_id={site_id} 下不存在")
        return row


def delete_site_prediction_module(db_path: str | Path, site_id: int, module_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        if not delete_module(conn, module_id, site_id):
            raise KeyError(f"module_id={module_id} 在 site_id={site_id} 下不存在")


def _normalize_bulk_delete_module_keys(module_ids: list[str]) -> list[str]:
    normalized = [str(item).strip() for item in module_ids if str(item).strip()]
    if not normalized:
        raise ValidationError("moduleIds 不能为空")
    return normalized


def _build_issue_range(period_range: dict[str, Any]) -> tuple[tuple[int, int], tuple[int, int]]:
    start_issue = parse_issue_range_value(period_range.get("start"), "起始期数")
    end_issue = parse_issue_range_value(period_range.get("end"), "结束期数")
    if end_issue < start_issue:
        raise ValidationError("结束期数必须大于或等于起始期数")
    return start_issue, end_issue


def _build_site_bulk_delete_where_clause(
    columns: set[str],
    *,
    lottery_type_id: int,
    site_web_id: int,
    start_issue: tuple[int, int],
    end_issue: tuple[int, int],
) -> tuple[str, list[Any]] | None:
    if "year" not in columns or "term" not in columns:
        return None

    where_clauses = [
        "("
        f"CAST({quote_identifier('year')} AS INTEGER) > %s "
        "OR ("
        f"CAST({quote_identifier('year')} AS INTEGER) = %s "
        f"AND CAST({quote_identifier('term')} AS INTEGER) >= %s"
        ")"
        ")",
        "("
        f"CAST({quote_identifier('year')} AS INTEGER) < %s "
        "OR ("
        f"CAST({quote_identifier('year')} AS INTEGER) = %s "
        f"AND CAST({quote_identifier('term')} AS INTEGER) <= %s"
        ")"
        ")",
    ]
    params: list[Any] = [
        start_issue[0],
        start_issue[0],
        start_issue[1],
        end_issue[0],
        end_issue[0],
        end_issue[1],
    ]

    if lottery_type_id > 0 and "type" in columns:
        where_clauses.append(f"CAST({quote_identifier('type')} AS TEXT) = %s")
        params.append(str(lottery_type_id))

    if "web" in columns:
        where_clauses.append(f"CAST({quote_identifier('web')} AS TEXT) = %s")
        params.append(str(site_web_id))
    elif "web_id" in columns:
        where_clauses.append(f"CAST({quote_identifier('web_id')} AS TEXT) = %s")
        params.append(str(site_web_id))

    return " AND ".join(where_clauses), params


def _count_module_rows_in_range(
    conn: Any,
    table_name: str,
    *,
    lottery_type_id: int,
    site_web_id: int,
    start_issue: tuple[int, int],
    end_issue: tuple[int, int],
) -> int:
    if not schema_table_exists(conn, CREATED_SCHEMA_NAME, table_name):
        return 0

    columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
    where_clause = _build_site_bulk_delete_where_clause(
        columns,
        lottery_type_id=lottery_type_id,
        site_web_id=site_web_id,
        start_issue=start_issue,
        end_issue=end_issue,
    )
    if where_clause is None:
        return 0

    qualified_table = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
    where_sql, params = where_clause
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM {qualified_table}
        WHERE {where_sql}
        """,
        params,
    ).fetchone()
    return int(row["total"] or 0) if row else 0


def _load_site_bulk_delete_modules(
    conn: Any,
    site_id: int,
    module_ids: list[str],
) -> list[dict[str, Any]]:
    normalized_keys = _normalize_bulk_delete_module_keys(module_ids)
    selected_rows = get_enabled_module_rows(conn, site_id, normalized_keys)
    selected_map = {str(row["mechanism_key"]): dict(row) for row in selected_rows}

    selected: list[dict[str, Any]] = []
    missing: list[str] = []

    for mechanism_key in normalized_keys:
        module_row = selected_map.get(mechanism_key)
        if not module_row:
            missing.append(mechanism_key)
            continue

        config = get_prediction_config(mechanism_key)
        resolved_mode_id = int(module_row.get("mode_id") or config.default_modes_id or 0)
        default_table = resolve_prediction_table_for_mode(
            conn,
            resolved_mode_id,
            str(config.default_table or ""),
        )
        selected.append(
            {
                **module_row,
                "mechanism_key": mechanism_key,
                "mode_id": resolved_mode_id,
                "default_table": validate_mode_payload_table_name(default_table),
            }
        )

    if missing:
        raise ValidationError(
            f"以下模块不存在、未启用或不属于当前站点: {', '.join(missing)}"
        )

    return selected


def estimate_site_prediction_modules_bulk_delete(
    db_path: str | Path,
    site_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from domains.sites.service import get_site

    ensure_prediction_configs_loaded(db_path)
    site = get_site(db_path, site_id)
    module_ids = payload.get("moduleIds") or []
    period_range = payload.get("periodRange") or {}
    start_issue, end_issue = _build_issue_range(period_range)
    period_count = ((end_issue[0] - start_issue[0]) * 1000) + (
        end_issue[1] - start_issue[1] + 1
    )
    lottery_type_id = int(site.get("lottery_type_id") or 0)
    site_web_id = int(site.get("web_id") or site.get("start_web_id") or 0)
    if site_web_id <= 0:
        raise ValidationError("当前站点缺少有效的 web_id 配置")

    with connect(db_path) as conn:
        modules = _load_site_bulk_delete_modules(conn, site_id, list(module_ids))
        estimated_rows = sum(
            _count_module_rows_in_range(
                conn,
                str(item["default_table"] or ""),
                lottery_type_id=lottery_type_id,
                site_web_id=site_web_id,
                start_issue=start_issue,
                end_issue=end_issue,
            )
            for item in modules
        )

    return {
        "moduleCount": len(modules),
        "periodCount": max(period_count, 0),
        "estimatedRows": estimated_rows,
        "limitExceeded": estimated_rows > MAX_BULK_DELETE_ROWS,
    }


def bulk_delete_site_prediction_modules(
    db_path: str | Path,
    site_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from domains.sites.service import get_site

    ensure_prediction_configs_loaded(db_path)
    site = get_site(db_path, site_id)
    estimate = estimate_site_prediction_modules_bulk_delete(db_path, site_id, payload)
    if estimate["limitExceeded"]:
        raise ValidationError(
            f"预计删除约 {estimate['estimatedRows']} 条记录，已超过单次 {MAX_BULK_DELETE_ROWS} 条限制"
        )

    module_ids = payload.get("moduleIds") or []
    period_range = payload.get("periodRange") or {}
    start_issue, end_issue = _build_issue_range(period_range)
    lottery_type_id = int(site.get("lottery_type_id") or 0)
    site_web_id = int(site.get("web_id") or site.get("start_web_id") or 0)
    if site_web_id <= 0:
        raise ValidationError("当前站点缺少有效的 web_id 配置")

    with connect(db_path) as conn:
        modules = _load_site_bulk_delete_modules(conn, site_id, list(module_ids))
        details: list[dict[str, Any]] = []
        deleted_total = 0

        for item in modules:
            table_name = str(item["default_table"] or "")
            if not schema_table_exists(conn, CREATED_SCHEMA_NAME, table_name):
                details.append(
                    {"moduleId": str(item["mechanism_key"]), "tableName": table_name, "deleted": 0}
                )
                continue

            columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
            where_clause = _build_site_bulk_delete_where_clause(
                columns,
                lottery_type_id=lottery_type_id,
                site_web_id=site_web_id,
                start_issue=start_issue,
                end_issue=end_issue,
            )
            if where_clause is None:
                details.append(
                    {"moduleId": str(item["mechanism_key"]), "tableName": table_name, "deleted": 0}
                )
                continue

            qualified_table = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
            where_sql, params = where_clause
            rows = conn.execute(
                f"""
                DELETE FROM {qualified_table}
                WHERE {where_sql}
                RETURNING 1
                """,
                params,
            ).fetchall()
            deleted = len(rows)
            deleted_total += deleted
            details.append(
                {
                    "moduleId": str(item["mechanism_key"]),
                    "tableName": table_name,
                    "deleted": deleted,
                }
            )

    return {
        "ok": True,
        "deleted": deleted_total,
        "estimated": estimate["estimatedRows"],
        "modules": details,
    }


def run_prediction(db_path: str | Path, site_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    mechanism_key = str(payload.get("mechanism_key") or "").strip()
    if not mechanism_key:
        raise ValueError("mechanism_key 不能为空")

    config = get_prediction_config(mechanism_key)
    return predict(
        config=config,
        res_code=str(payload.get("res_code") or "").strip() or None,
        content=str(payload.get("content") or "").strip() or None,
        source_table=str(payload.get("source_table") or "").strip() or None,
        db_path=db_path,
        target_hit_rate=float(
            payload.get("target_hit_rate")
            or get_config(db_path, "prediction.default_target_hit_rate", 0.65)
        ),
    )


def sync_site_prediction_modules(db_path: str | Path, site_id: int) -> None:
    from domains.prediction.generation_service import sync_site_prediction_modules as _impl

    with connect(db_path) as conn:
        _impl(conn, site_id=site_id)


def bulk_generate_site_predictions(
    db_path: str | Path,
    site_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from domains.prediction.generation_service import (
        build_generated_prediction_row_data,
        resolve_prediction_table_for_mode,
        sync_site_prediction_modules as _sync_site_prediction_modules,
    )
    from domains.sites.service import get_site
    from prediction_generation.service import generate_prediction_batch

    site = get_site(db_path, site_id)
    lottery_type = int(payload.get("lottery_type") or site.get("lottery_type_id") or 3)
    start_issue = parse_issue_range_value(payload.get("start_issue"), "起始期号")
    end_issue = parse_issue_range_value(payload.get("end_issue"), "结束期号")

    if start_issue > end_issue:
        raise ValueError("起始期号不能大于结束期号")

    requested_keys = payload.get("mechanism_keys") or []
    if isinstance(requested_keys, str):
        requested_keys = [key.strip() for key in requested_keys.split(",") if key.strip()]

    return generate_prediction_batch(
        db_path,
        site_id=int(site_id),
        lottery_type=int(lottery_type),
        start_issue=start_issue,
        end_issue=end_issue,
        mechanism_keys=list(requested_keys),
        future_periods=int(payload.get("future_periods") or 0),
        future_only=parse_bool(payload.get("future_only"), False),
        trigger="admin_generate_all",
        sync_site_modules=_sync_site_prediction_modules,
        resolve_prediction_table_for_mode=resolve_prediction_table_for_mode,
        build_generated_prediction_row_data=build_generated_prediction_row_data,
    )
