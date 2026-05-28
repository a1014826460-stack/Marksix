from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from db import connect
from tables import ensure_admin_tables


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        normalized = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return normalized.astimezone(timezone.utc)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
          parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _iso(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.astimezone(timezone.utc).isoformat()


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def get_dashboard_overview(db_path: str | Path) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)
    timeline_cutoff = now - timedelta(days=30)

    with connect(db_path) as conn:
        sites = [dict(row) for row in conn.execute(
            """
            SELECT s.*, l.name AS lottery_name
            FROM managed_sites s
            LEFT JOIN lottery_types l ON l.id = s.lottery_type_id
            ORDER BY s.enabled DESC, s.id ASC
            """
        ).fetchall()]
        lottery_types = [dict(row) for row in conn.execute(
            "SELECT * FROM lottery_types ORDER BY id ASC"
        ).fetchall()]
        latest_draws = [dict(row) for row in conn.execute(
            """
            SELECT DISTINCT ON (lottery_type_id)
                lottery_type_id, year, term, draw_time, next_time, is_opened, updated_at
            FROM lottery_draws
            ORDER BY lottery_type_id, draw_time DESC, id DESC
            """
        ).fetchall()]
        fetched_modes_rows = [dict(row) for row in conn.execute(
            """
            SELECT web_id, COUNT(*) AS modes_count, COALESCE(SUM(record_count), 0) AS record_count,
                   MAX(fetched_at) AS latest_fetched_at
            FROM fetched_modes
            GROUP BY web_id
            ORDER BY web_id
            """
        ).fetchall()]
        fetched_records_rows = [dict(row) for row in conn.execute(
            """
            SELECT web_id, COUNT(*) AS records_count, MAX(fetched_at) AS latest_record_at
            FROM fetched_mode_records
            GROUP BY web_id
            ORDER BY web_id
            """
        ).fetchall()]
        prediction_rows = [dict(row) for row in conn.execute(
            """
            SELECT site_id,
                   COUNT(*) AS modules_total,
                   SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS modules_enabled
            FROM site_prediction_modules
            GROUP BY site_id
            ORDER BY site_id
            """
        ).fetchall()]
        fetch_run_rows = [dict(row) for row in conn.execute(
            """
            SELECT *
            FROM site_fetch_runs
            ORDER BY COALESCE(finished_at, started_at) DESC, id DESC
            LIMIT 20
            """
        ).fetchall()]
        scheduler_status_rows = [dict(row) for row in conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM scheduler_tasks
            GROUP BY status
            ORDER BY count DESC
            """
        ).fetchall()]
        scheduler_pending_rows = [dict(row) for row in conn.execute(
            """
            SELECT task_key, task_type, status, run_at, attempt_count, max_attempts, last_error, lottery_type_id, site_id
            FROM scheduler_tasks
            ORDER BY updated_at DESC, id DESC
            LIMIT 20
            """
        ).fetchall()]
        draw_audit_rows = [dict(row) for row in conn.execute(
            """
            SELECT *
            FROM draw_audit_log
            WHERE created_at >= ?
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """,
            (week_start.isoformat(),),
        ).fetchall()]
        error_log_rows = [dict(row) for row in conn.execute(
            """
            SELECT id, created_at, level, logger_name, module, message, site_id, web_id, lottery_type_id, request_path
            FROM error_logs
            WHERE created_at >= ?
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """,
            (timeline_cutoff.isoformat(),),
        ).fetchall()]
        alert_recipients = conn.execute(
            """
            SELECT value_text
            FROM system_config
            WHERE key = ?
            LIMIT 1
            """,
            ("alert.email_recipients",),
        ).fetchone()
        admin_user = conn.execute(
            """
            SELECT username, display_name, last_login_at
            FROM admin_users
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()
        session_count_row = conn.execute(
            "SELECT COUNT(*) AS count FROM admin_sessions"
        ).fetchone()
        login_attempts_rows = [dict(row) for row in conn.execute(
            """
            SELECT fingerprint, attempt_count, first_attempt_at, last_attempt_at, locked_until
            FROM admin_login_attempts
            ORDER BY last_attempt_at DESC
            LIMIT 20
            """
        ).fetchall()]

    latest_draw_by_type = {int(row["lottery_type_id"]): row for row in latest_draws}
    fetched_modes_by_web = {int(row["web_id"]): row for row in fetched_modes_rows}
    fetched_records_by_web = {int(row["web_id"]): row for row in fetched_records_rows}
    prediction_by_site = {int(row["site_id"]): row for row in prediction_rows}
    lottery_name_by_id = {int(row["id"]): str(row["name"] or "") for row in lottery_types}

    site_cards: list[dict[str, Any]] = []
    for site in sites:
        site_id = int(site["id"])
        web_id = _safe_int(site.get("web_id"))
        lottery_type_id = _safe_int(site.get("lottery_type_id"))
        fetched_modes = fetched_modes_by_web.get(web_id, {})
        fetched_records = fetched_records_by_web.get(web_id, {})
        prediction = prediction_by_site.get(site_id, {})
        latest_draw = latest_draw_by_type.get(lottery_type_id, {})
        site_cards.append(
            {
                "site_id": site_id,
                "web_id": web_id,
                "name": str(site.get("name") or ""),
                "domain": str(site.get("domain") or ""),
                "enabled": bool(site.get("enabled")),
                "lottery_name": str(site.get("lottery_name") or ""),
                "modes_count": _safe_int(fetched_modes.get("modes_count")),
                "records_count": _safe_int(fetched_records.get("records_count") or fetched_modes.get("record_count")),
                "prediction_modules": _safe_int(prediction.get("modules_total")),
                "enabled_prediction_modules": _safe_int(prediction.get("modules_enabled")),
                "latest_fetched_at": str(fetched_records.get("latest_record_at") or fetched_modes.get("latest_fetched_at") or ""),
                "latest_draw_time": str(latest_draw.get("draw_time") or ""),
                "latest_draw_term": _safe_int(latest_draw.get("term")),
                "next_time": str(latest_draw.get("next_time") or ""),
            }
        )

    total_modes = sum(item["modes_count"] for item in site_cards)
    total_records = sum(item["records_count"] for item in site_cards)
    total_prediction_modules = sum(item["prediction_modules"] for item in site_cards)
    enabled_sites = sum(1 for item in site_cards if item["enabled"])

    draw_audit_per_day: dict[str, int] = {(
        week_start + timedelta(days=i)
    ).date().isoformat(): 0 for i in range(7)}
    audit_timeline: list[dict[str, Any]] = []
    for row in draw_audit_rows:
        created = _parse_dt(row.get("created_at"))
        if created:
            key = created.date().isoformat()
            if key in draw_audit_per_day:
                draw_audit_per_day[key] += 1
        if len(audit_timeline) < 20:
            audit_timeline.append(
                {
                    "lottery_type_id": _safe_int(row.get("lottery_type_id")),
                    "lottery_name": lottery_name_by_id.get(_safe_int(row.get("lottery_type_id")), ""),
                    "event": str(row.get("event") or ""),
                    "status": str(row.get("status") or ""),
                    "detail": str(row.get("detail") or ""),
                    "duration_ms": _safe_int(row.get("duration_ms")),
                    "created_at": str(row.get("created_at") or ""),
                    "operator": str(row.get("operator") or ""),
                }
            )

    level_counts: dict[str, int] = defaultdict(int)
    error_timeline: list[dict[str, Any]] = []
    errors_per_day: dict[str, int] = {(
        week_start + timedelta(days=i)
    ).date().isoformat(): 0 for i in range(7)}
    auth_error_count = 0
    for row in error_log_rows:
        level = str(row.get("level") or "").upper()
        level_counts[level] += 1
        created = _parse_dt(row.get("created_at"))
        message = str(row.get("message") or "")
        request_path = str(row.get("request_path") or "")
        if created:
            day_key = created.date().isoformat()
            if day_key in errors_per_day:
                errors_per_day[day_key] += 1
        if "/api/auth/" in request_path or "未登录或登录已失效" in message:
            auth_error_count += 1
        if len(error_timeline) < 20:
            error_timeline.append(
                {
                    "created_at": str(row.get("created_at") or ""),
                    "level": level,
                    "logger_name": str(row.get("logger_name") or ""),
                    "module": str(row.get("module") or ""),
                    "message": message,
                    "site_id": _safe_int(row.get("site_id")),
                    "web_id": _safe_int(row.get("web_id")),
                    "lottery_type_id": _safe_int(row.get("lottery_type_id")),
                    "request_path": request_path,
                }
            )

    fetch_status_counts: dict[str, int] = defaultdict(int)
    fetch_log_timeline: list[dict[str, Any]] = []
    for row in fetch_run_rows:
        fetch_status_counts[str(row.get("status") or "")] += 1
        fetch_log_timeline.append(
            {
                "site_id": _safe_int(row.get("site_id")),
                "status": str(row.get("status") or ""),
                "message": str(row.get("message") or ""),
                "modes_count": _safe_int(row.get("modes_count")),
                "records_count": _safe_int(row.get("records_count")),
                "started_at": str(row.get("started_at") or ""),
                "finished_at": str(row.get("finished_at") or ""),
            }
        )

    pending_tasks = sum(_safe_int(row.get("count")) for row in scheduler_status_rows if str(row.get("status")) == "pending")
    failed_tasks = sum(_safe_int(row.get("count")) for row in scheduler_status_rows if str(row.get("status")) == "failed")
    done_tasks = sum(_safe_int(row.get("count")) for row in scheduler_status_rows if str(row.get("status")) == "done")

    unresolved_alerts: list[dict[str, Any]] = []
    if failed_tasks:
        unresolved_alerts.append(
            {
                "severity": "high",
                "name": "调度任务存在失败项",
                "source": "scheduler_tasks",
                "status": f"{failed_tasks} 个失败任务待处理",
            }
        )
    if fetch_status_counts.get("failed", 0):
        unresolved_alerts.append(
            {
                "severity": "medium",
                "name": "站点采集存在失败记录",
                "source": "site_fetch_runs",
                "status": f"{fetch_status_counts.get('failed', 0)} 条失败记录",
            }
        )
    if level_counts.get("ERROR", 0):
        unresolved_alerts.append(
            {
                "severity": "medium",
                "name": "系统错误日志需关注",
                "source": "error_logs",
                "status": f"{level_counts.get('ERROR', 0)} 条错误日志",
            }
        )
    for row in login_attempts_rows:
        if str(row.get("locked_until") or "").strip():
            unresolved_alerts.append(
                {
                    "severity": "low",
                    "name": "存在被锁定的登录指纹",
                    "source": "admin_login_attempts",
                    "status": str(row.get("locked_until") or ""),
                }
            )

    site_share = []
    for item in site_cards:
        share = round((item["records_count"] / total_records) * 100, 2) if total_records else 0
        site_share.append(
            {
                "site_id": item["site_id"],
                "name": item["name"],
                "value": item["records_count"],
                "share": share,
            }
        )

    latest_sync = ""
    latest_candidates = [
        _parse_dt(item["latest_fetched_at"]) for item in site_cards if item["latest_fetched_at"]
    ] + [
        _parse_dt(item["latest_draw_time"]) for item in site_cards if item["latest_draw_time"]
    ]
    latest_candidates = [item for item in latest_candidates if item]
    if latest_candidates:
        latest_sync = _iso(max(latest_candidates))

    return {
        "summary": {
            "enabled_sites": enabled_sites,
            "managed_sites": len(site_cards),
            "total_modes": total_modes,
            "total_records": total_records,
            "prediction_modules": total_prediction_modules,
            "today_success_login": 1 if admin_user and str(admin_user.get("last_login_at") or "") >= today_start.isoformat() else 0,
            "today_failed_login": sum(_safe_int(row.get("attempt_count")) for row in login_attempts_rows),
            "active_sessions": _safe_int(session_count_row["count"]) if session_count_row else 0,
            "error_logs_7d": sum(errors_per_day.values()),
            "scheduler_pending": pending_tasks,
            "scheduler_failed": failed_tasks,
            "scheduler_done": done_tasks,
            "latest_sync_at": latest_sync,
            "auth_warning_count": auth_error_count,
        },
        "sites": site_cards,
        "site_share": site_share,
        "lottery_types": [
            {
                "id": _safe_int(row.get("id")),
                "name": str(row.get("name") or ""),
                "draw_time": str(row.get("draw_time") or ""),
                "next_time": str(row.get("next_time") or ""),
                "status": _safe_int(row.get("status")),
                "last_auto_task_status": str(row.get("last_auto_task_status") or ""),
            }
            for row in lottery_types
        ],
        "trend": {
            "draw_audit_7d": [{"date": key, "count": value} for key, value in draw_audit_per_day.items()],
            "error_logs_7d": [{"date": key, "count": value} for key, value in errors_per_day.items()],
        },
        "security": {
            "current_failed_fingerprints": len(login_attempts_rows),
            "today_success_login": 1 if admin_user and str(admin_user.get("last_login_at") or "") >= today_start.isoformat() else 0,
            "today_failed_login": sum(_safe_int(row.get("attempt_count")) for row in login_attempts_rows),
            "auth_error_count": auth_error_count,
            "login_attempts": [
                {
                    "fingerprint": str(row.get("fingerprint") or ""),
                    "attempt_count": _safe_int(row.get("attempt_count")),
                    "first_attempt_at": str(row.get("first_attempt_at") or ""),
                    "last_attempt_at": str(row.get("last_attempt_at") or ""),
                    "locked_until": str(row.get("locked_until") or ""),
                }
                for row in login_attempts_rows
            ],
            "error_level_breakdown": dict(level_counts),
            "recent_events": error_timeline[:20],
        },
        "fetch": {
            "status_breakdown": dict(fetch_status_counts),
            "recent_runs": fetch_log_timeline,
        },
        "draw_audit": {
            "recent_events": audit_timeline,
        },
        "scheduler": {
            "status_breakdown": [
                {
                    "status": str(row.get("status") or ""),
                    "count": _safe_int(row.get("count")),
                }
                for row in scheduler_status_rows
            ],
            "recent_tasks": [
                {
                    "task_key": str(row.get("task_key") or ""),
                    "task_type": str(row.get("task_type") or ""),
                    "status": str(row.get("status") or ""),
                    "run_at": str(row.get("run_at") or ""),
                    "attempt_count": _safe_int(row.get("attempt_count")),
                    "max_attempts": _safe_int(row.get("max_attempts")),
                    "last_error": str(row.get("last_error") or ""),
                    "lottery_type_id": _safe_int(row.get("lottery_type_id")),
                    "site_id": _safe_int(row.get("site_id")),
                }
                for row in scheduler_pending_rows
            ],
        },
        "alerts": unresolved_alerts[:20],
        "meta": {
            "generated_at": now.isoformat(),
            "admin_user": {
                "username": str(admin_user.get("username") or "") if admin_user else "",
                "display_name": str(admin_user.get("display_name") or "") if admin_user else "",
                "last_login_at": str(admin_user.get("last_login_at") or "") if admin_user else "",
            },
            "alert_recipients_configured": bool(alert_recipients),
        },
    }
