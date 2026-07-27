from __future__ import annotations

from datetime import datetime, timedelta, timezone

from db import connect
from domains.dashboard.service import get_dashboard_overview
from domains.scheduler import service as scheduler_service
from domains.traffic.service import record_traffic_event
from routes import admin_dashboard_routes
from tables import ensure_admin_tables


def test_dashboard_reports_worker_draw_health_and_overdue_alert(tmp_path):
    db_path = tmp_path / "dashboard-operations.sqlite3"
    ensure_admin_tables(db_path)
    now = datetime.now(timezone.utc)
    today_beijing = (now + timedelta(hours=8)).strftime("%Y-%m-%d")

    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE fetched_modes (
                web_id INTEGER, record_count INTEGER, fetched_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE fetched_mode_records (
                web_id INTEGER, fetched_at TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, next_time, status,
                is_opened, next_term, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3, 2026, 171, "01,02,03,04,05,06,07", f"{today_beijing} 22:30:00",
                str(int((now - timedelta(minutes=5)).timestamp() * 1000)), 1, 1, 172,
                now.isoformat(), now.isoformat(),
            ),
        )

    payload = get_dashboard_overview(db_path)

    assert payload["worker"]["status"] == "missing"
    assert payload["draw_health"]["status"] == "degraded"
    assert payload["today_draws"][0]["lottery_type_id"] == 3
    assert payload["today_draws"][0]["is_opened"] is True
    assert any(item["source"] == "lottery_draw_health" for item in payload["alerts"])


def test_dashboard_prioritizes_public_site_traffic_metrics(tmp_path):
    db_path = tmp_path / "dashboard-traffic.sqlite3"
    ensure_admin_tables(db_path)
    now = datetime.now(timezone.utc)
    with connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE fetched_modes (web_id INTEGER, record_count INTEGER, fetched_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE fetched_mode_records (web_id INTEGER, fetched_at TEXT)"
        )

    record_traffic_event(
        db_path,
        {
            "site_key": "twjinniu",
            "event_type": "vendor_page_view",
            "path": "/twjinniu",
            "route": "/twjinniu",
            "visitor_id": "traffic-test-visitor",
            "occurred_at": now.isoformat(),
        },
    )
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE managed_sites
            SET web_id = 9, name = '台湾神算子', domain = 'www.twssz.com'
            WHERE blueprint_name = 'twssz'
            """,
        )
    record_traffic_event(
        db_path,
        {
            "site_key": "twssz",
            "event_type": "vendor_page_view",
            "path": "/twssz",
            "route": "/twssz",
            "visitor_id": "traffic-test-visitor-2",
            "occurred_at": now.isoformat(),
        },
    )
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE public_site_traffic_events SET site_id = NULL, web_id = NULL WHERE site_key = 'twssz'"
        )

    payload = get_dashboard_overview(db_path)

    assert payload["traffic"]["today"]["pv"] == 2
    assert payload["traffic"]["today"]["uv"] == 2
    assert payload["traffic"]["last_7_days"]["sites"] == [
        {
            "site_key": "twjinniu",
            "web_id": 7,
            "name": "台湾金牛论坛",
            "domain": "www.twtongtian.com",
            "pv": 1,
            "uv": 1,
            "api_compat_hits": 0,
        },
        {
            "site_key": "twssz",
            "web_id": 9,
            "name": "台湾神算子",
            "domain": "www.twssz.com",
            "pv": 1,
            "uv": 1,
            "api_compat_hits": 0,
        },
    ]


def test_retry_failed_scheduler_task_makes_task_pending(tmp_path):
    db_path = tmp_path / "dashboard-retry.sqlite3"
    ensure_admin_tables(db_path)
    scheduler_service.upsert_scheduler_task(
        db_path,
        task_type=scheduler_service.TASK_TYPE_DAILY_PREDICTION,
        payload={"schedule_date": "2026-07-22"},
        run_at="2026-07-22T00:00:00+00:00",
        max_attempts=1,
    )
    with connect(db_path) as conn:
        row = conn.execute("SELECT id FROM scheduler_tasks LIMIT 1").fetchone()
        task_id = int(row["id"])
        conn.execute(
            "UPDATE scheduler_tasks SET status = 'failed', attempt_count = 1, last_error = 'boom' WHERE id = ?",
            (task_id,),
        )

    task = scheduler_service.retry_failed_scheduler_task(db_path, task_id=task_id)

    assert task["status"] == "pending"
    assert task["attempt_count"] == 0
    assert task["last_error"] == ""


def test_dashboard_retry_route_accepts_only_retry_suffix(monkeypatch):
    calls: list[int] = []

    class Ctx:
        path = "/api/admin/dashboard/scheduler-tasks/42/retry"
        db_path = "test-db"

        def send_json(self, payload):
            self.payload = payload

    monkeypatch.setattr(
        admin_dashboard_routes,
        "retry_failed_scheduler_task",
        lambda _db_path, *, task_id: calls.append(task_id) or {"id": task_id, "status": "pending"},
    )
    ctx = Ctx()
    admin_dashboard_routes.retry_scheduler_task(ctx)

    assert calls == [42]
    assert ctx.payload["task"]["status"] == "pending"
