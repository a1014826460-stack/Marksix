from datetime import datetime, timezone

from domains.lottery.service import save_taiwan_future_autofill_settings
from domains.scheduler import service
from tables import ensure_admin_tables


def test_autofill_schedule_time_is_beijing_but_run_at_is_utc(tmp_path):
    db_path = tmp_path / "taiwan-beijing-schedule.sqlite3"
    ensure_admin_tables(db_path)
    save_taiwan_future_autofill_settings(
        db_path, {"enabled": True, "count": 12, "time": "07:45"}, changed_by="admin"
    )

    service.ensure_taiwan_future_autofill_task(
        db_path, now=datetime(2026, 7, 27, 0, 0, tzinfo=timezone.utc)
    )

    from db import connect
    with connect(db_path) as conn:
        task = conn.execute(
            "SELECT task_key, run_at FROM scheduler_tasks WHERE task_type = ?",
            (service.TASK_TYPE_TAIWAN_FUTURE_AUTOFILL,),
        ).fetchone()
    assert task["task_key"] == "taiwan_future_draw_autofill:2026-07-27"
    assert task["run_at"] == "2026-07-26T23:45:00+00:00"
