"""First-party public-site traffic event storage and metrics."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from db import connect, utc_now
from tables import ensure_admin_tables

TRAFFIC_EVENT_TYPES = {
    "site_page_view",
    "article_view",
    "vendor_page_view",
    "api_compat_hit",
}

DEDUPLICATED_EVENT_TYPES = {
    "site_page_view",
    "article_view",
    "vendor_page_view",
}
DEDUPLICATION_WINDOW_SECONDS = 300


def _clean_text(value: Any, *, max_length: int = 500) -> str:
    text = str(value or "").strip()
    return text[:max_length]


def _safe_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _hash_ip(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return utc_now()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return utc_now()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _date_expr(conn: Any, column_name: str) -> str:
    if conn.engine == "postgres":
        return f"DATE({column_name})"
    return f"substr({column_name}, 1, 10)"


def _where_period(date_from: str | None, date_to: str | None) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if date_from:
        clauses.append("occurred_at >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("occurred_at < ?")
        params.append(date_to)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def _event_row(row: Any) -> dict[str, Any]:
    data = dict(row)
    return {
        "id": int(data.get("id") or 0),
        "site_key": str(data.get("site_key") or ""),
        "site_id": data.get("site_id"),
        "web_id": data.get("web_id"),
        "lottery_type": data.get("lottery_type"),
        "event_type": str(data.get("event_type") or ""),
        "path": str(data.get("path") or ""),
        "visitor_id": str(data.get("visitor_id") or ""),
        "occurred_at": str(data.get("occurred_at") or ""),
        "ok": True,
    }


def _resolve_managed_site_context(conn: Any, site_key: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT id, web_id, lottery_type_id
        FROM managed_sites
        WHERE blueprint_name = ?
           OR domain = ?
           OR domain LIKE ?
        ORDER BY enabled DESC, id ASC
        LIMIT 1
        """,
        (site_key, site_key, f"%{site_key}%"),
    ).fetchone()
    if not row:
        return {}
    return {
        "site_id": row["id"],
        "web_id": row["web_id"],
        "lottery_type": row["lottery_type_id"],
    }


def record_traffic_event(
    db_path: str | Path,
    payload: dict[str, Any],
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    event_type = _clean_text(payload.get("event_type"), max_length=64)
    if event_type not in TRAFFIC_EVENT_TYPES:
        raise ValueError(f"event_type must be one of {sorted(TRAFFIC_EVENT_TYPES)}")

    site_key = _clean_text(payload.get("site_key"), max_length=80)
    if not site_key:
        raise ValueError("site_key is required")

    ensure_admin_tables(db_path)
    occurred_at = _normalize_timestamp(payload.get("occurred_at"))
    created_at = utc_now()
    visitor_id = _clean_text(payload.get("visitor_id"), max_length=120)

    values = {
        "site_key": site_key,
        "site_id": _safe_int(payload.get("site_id")),
        "web_id": _safe_int(payload.get("web_id")),
        "lottery_type": _safe_int(payload.get("lottery_type") or payload.get("lottery_type_id")),
        "event_type": event_type,
        "path": _clean_text(payload.get("path"), max_length=500),
        "route": _clean_text(payload.get("route"), max_length=500),
        "article_id": _clean_text(payload.get("article_id") or payload.get("articleId"), max_length=120),
        "referrer": _clean_text(payload.get("referrer"), max_length=500),
        "utm_source": _clean_text(payload.get("utm_source"), max_length=120),
        "utm_medium": _clean_text(payload.get("utm_medium"), max_length=120),
        "utm_campaign": _clean_text(payload.get("utm_campaign"), max_length=120),
        "user_agent": _clean_text(user_agent or payload.get("user_agent"), max_length=500),
        "ip_hash": _hash_ip(ip_address),
        "visitor_id": visitor_id,
        "occurred_at": occurred_at,
        "created_at": created_at,
    }

    with connect(db_path) as conn:
        managed_site = _resolve_managed_site_context(conn, site_key)
        values["site_id"] = values["site_id"] or _safe_int(managed_site.get("site_id"))
        values["web_id"] = values["web_id"] or _safe_int(managed_site.get("web_id"))
        values["lottery_type"] = values["lottery_type"] or _safe_int(managed_site.get("lottery_type"))

        if event_type in DEDUPLICATED_EVENT_TYPES and visitor_id:
            occurred_dt = _parse_timestamp(occurred_at)
            window_start = (occurred_dt - timedelta(seconds=DEDUPLICATION_WINDOW_SECONDS)).isoformat()
            duplicate = conn.execute(
                """
                SELECT *
                FROM public_site_traffic_events
                WHERE site_key = ?
                  AND event_type = ?
                  AND path = ?
                  AND visitor_id = ?
                  AND occurred_at >= ?
                  AND occurred_at <= ?
                ORDER BY occurred_at DESC, id DESC
                LIMIT 1
                """,
                (
                    values["site_key"],
                    values["event_type"],
                    values["path"],
                    values["visitor_id"],
                    window_start,
                    values["occurred_at"],
                ),
            ).fetchone()
            if duplicate:
                return _event_row(duplicate)

        row = conn.execute(
            """
            INSERT INTO public_site_traffic_events (
                site_key, site_id, web_id, lottery_type, event_type, path, route,
                article_id, referrer, utm_source, utm_medium, utm_campaign,
                user_agent, ip_hash, visitor_id, occurred_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            (
                values["site_key"],
                values["site_id"],
                values["web_id"],
                values["lottery_type"],
                values["event_type"],
                values["path"],
                values["route"],
                values["article_id"],
                values["referrer"],
                values["utm_source"],
                values["utm_medium"],
                values["utm_campaign"],
                values["user_agent"],
                values["ip_hash"],
                values["visitor_id"],
                values["occurred_at"],
                values["created_at"],
            ),
        ).fetchone()
    return _event_row(row)


def _count_distinct_visitor_sql() -> str:
    return "COUNT(DISTINCT CASE WHEN visitor_id != '' THEN visitor_id ELSE ip_hash END)"


def get_traffic_overview(
    db_path: str | Path,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    where, params = _where_period(date_from, date_to)
    with connect(db_path) as conn:
        summary = conn.execute(
            f"""
            SELECT COUNT(*) AS pv,
                   {_count_distinct_visitor_sql()} AS uv,
                   SUM(CASE WHEN event_type = 'api_compat_hit' THEN 1 ELSE 0 END) AS api_compat_hits
            FROM public_site_traffic_events
            {where}
            """,
            params,
        ).fetchone()
        site_rows = conn.execute(
            f"""
            SELECT site_key,
                   COUNT(*) AS pv,
                   {_count_distinct_visitor_sql()} AS uv,
                   SUM(CASE WHEN event_type = 'api_compat_hit' THEN 1 ELSE 0 END) AS api_compat_hits
            FROM public_site_traffic_events
            {where}
            GROUP BY site_key
            ORDER BY pv DESC, site_key ASC
            """,
            params,
        ).fetchall()
        article_rows = conn.execute(
            f"""
            SELECT site_key, article_id, path, COUNT(*) AS views
            FROM public_site_traffic_events
            {where + (' AND' if where else ' WHERE')} event_type = 'article_view'
              AND article_id != ''
            GROUP BY site_key, article_id, path
            ORDER BY views DESC, site_key ASC, article_id ASC
            LIMIT 20
            """,
            params,
        ).fetchall()
        referrer_rows = conn.execute(
            f"""
            SELECT referrer, COUNT(*) AS views
            FROM public_site_traffic_events
            {where + (' AND' if where else ' WHERE')} referrer != ''
            GROUP BY referrer
            ORDER BY views DESC, referrer ASC
            LIMIT 20
            """,
            params,
        ).fetchall()
        compat_rows = conn.execute(
            f"""
            SELECT site_key, path, COUNT(*) AS hits
            FROM public_site_traffic_events
            {where + (' AND' if where else ' WHERE')} event_type = 'api_compat_hit'
            GROUP BY site_key, path
            ORDER BY hits DESC, site_key ASC, path ASC
            LIMIT 50
            """,
            params,
        ).fetchall()

    return {
        "summary": {
            "pv": int(summary["pv"] or 0) if summary else 0,
            "uv": int(summary["uv"] or 0) if summary else 0,
            "api_compat_hits": int(summary["api_compat_hits"] or 0) if summary else 0,
        },
        "sites": [
            {
                "site_key": str(row["site_key"] or ""),
                "pv": int(row["pv"] or 0),
                "uv": int(row["uv"] or 0),
                "api_compat_hits": int(row["api_compat_hits"] or 0),
            }
            for row in site_rows
        ],
        "article_rankings": [
            {
                "site_key": str(row["site_key"] or ""),
                "article_id": str(row["article_id"] or ""),
                "path": str(row["path"] or ""),
                "views": int(row["views"] or 0),
            }
            for row in article_rows
        ],
        "referrers": [
            {"referrer": str(row["referrer"] or ""), "views": int(row["views"] or 0)}
            for row in referrer_rows
        ],
        "compatibility_routes": [
            {
                "site_key": str(row["site_key"] or ""),
                "path": str(row["path"] or ""),
                "hits": int(row["hits"] or 0),
            }
            for row in compat_rows
        ],
    }


def get_traffic_sites(
    db_path: str | Path,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    overview = get_traffic_overview(db_path, date_from=date_from, date_to=date_to)
    return {"sites": overview["sites"]}


def get_traffic_timeseries(
    db_path: str | Path,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    where, params = _where_period(date_from, date_to)
    with connect(db_path) as conn:
        day_expr = _date_expr(conn, "occurred_at")
        rows = conn.execute(
            f"""
            SELECT {day_expr} AS date,
                   site_key,
                   COUNT(*) AS pv,
                   {_count_distinct_visitor_sql()} AS uv,
                   SUM(CASE WHEN event_type = 'api_compat_hit' THEN 1 ELSE 0 END) AS api_compat_hits
            FROM public_site_traffic_events
            {where}
            GROUP BY {day_expr}, site_key
            ORDER BY date ASC, site_key ASC
            """,
            params,
        ).fetchall()
    return {
        "items": [
            {
                "date": str(row["date"] or ""),
                "site_key": str(row["site_key"] or ""),
                "pv": int(row["pv"] or 0),
                "uv": int(row["uv"] or 0),
                "api_compat_hits": int(row["api_compat_hits"] or 0),
            }
            for row in rows
        ]
    }
