"""开奖延迟修复的回归测试。

覆盖四组行为：
1. 追赶模式必须立即重排 auto-crawl 定时器，且“逾期未到”被判成 near 间隔。
2. 已开盘的一期不会因为同一期的数据刷新而回退，也不再产生假 ``auto_open`` 审计。
3. 号码完整性闸门：澳门彩/台湾彩不完整只入库不开盘不发布；香港彩按轮序发布。
4. 分级超时告警有独立的轮询定时器与基于历史入库时延的告警基线。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

HK = 1
MACAU = 2
TAIWAN = 3

COMPLETE = "01,02,03,04,05,06,07"


def _setup(tmp_path, name: str = "draw-delay-remediation.sqlite3"):
    from database.bootstrap import ensure_admin_tables
    from db import connect

    db_path = str(tmp_path / name)
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        for lottery_id, lottery_name in ((HK, "香港彩"), (MACAU, "澳门彩"), (TAIWAN, "台湾彩")):
            conn.execute(
                "INSERT OR IGNORE INTO lottery_types (id, name, status, created_at, updated_at) "
                "VALUES (?, ?, 1, ?, ?)",
                (lottery_id, lottery_name, "2026-08-07T14:00:00+00:00", "2026-08-07T14:00:00+00:00"),
            )
        conn.commit()
    return db_path


def _insert_draw(conn, lottery_type_id, year, term, numbers, draw_time, is_opened):
    conn.execute(
        """
        INSERT INTO lottery_draws (
            lottery_type_id, year, term, numbers, draw_time, next_time,
            status, is_opened, next_term, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lottery_type_id, year, term, numbers, draw_time, "",
            1, is_opened, term + 1,
            "2026-08-07T13:32:00+00:00", "2026-08-07T13:32:00+00:00",
        ),
    )


# ── 1. 追赶模式与动态间隔 ────────────────────────────────────────────

class _RecordingTimer:
    def __init__(self, interval, function):
        self.interval = interval
        self.function = function
        self.daemon = False
        self.cancelled = False
        self.started = False

    def cancel(self):
        self.cancelled = True

    def start(self):
        self.started = True


class _FakeThreading:
    Timer = _RecordingTimer


def test_enabling_chase_mode_immediately_rearms_the_auto_crawl_timer(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler

    db_path = _setup(tmp_path)
    scheduler = CrawlerScheduler(db_path)
    scheduler._running = True
    stale_timer = _RecordingTimer(300, lambda: None)
    scheduler._auto_crawl_timer = stale_timer
    monkeypatch.setattr("crawler.scheduler.threading", _FakeThreading)
    monkeypatch.setattr(
        "crawler.scheduler._cfg",
        lambda _db, key, default: 5 if key == "crawler.crawl_interval_chase" else default,
    )

    scheduler._set_lottery_chase_mode(HK, True)

    assert stale_timer.cancelled is True
    assert scheduler._auto_crawl_timer is not stale_timer
    assert scheduler._auto_crawl_timer.interval == 5
    assert scheduler._auto_crawl_timer.started is True


def test_chase_rearm_is_a_noop_before_the_scheduler_starts(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler

    db_path = _setup(tmp_path)
    scheduler = CrawlerScheduler(db_path)
    scheduler._auto_crawl_timer = None
    monkeypatch.setattr("crawler.scheduler.threading", _FakeThreading)

    scheduler._set_lottery_chase_mode(HK, True)

    assert scheduler._auto_crawl_timer is None


def test_dynamic_interval_is_near_when_the_draw_is_overdue_and_unfilled(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler
    from db import connect

    db_path = _setup(tmp_path)
    scheduler = CrawlerScheduler(db_path)
    # 用 10 分钟前的时间，确保不会被 ±5 分钟“开奖窗口”规则命中。
    past_ms = int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp() * 1000)
    values = {
        "lottery.macau_current_period": "2026264",
        "lottery.macau_next_time": str(past_ms),
        "crawler.crawl_interval_near_draw": 10,
        "crawler.crawl_interval_far_draw": 300,
    }
    monkeypatch.setattr("crawler.scheduler._cfg", lambda _db, key, default: values.get(key, default))

    # 期望的第 265 期还没有入库 → 逾期未到，必须用 near 间隔。
    assert scheduler._compute_dynamic_crawl_interval() == 10

    with connect(db_path) as conn:
        _insert_draw(conn, MACAU, 2026, 265, COMPLETE, "2026-09-22 21:32:32", 1)
        conn.commit()

    # 期望期已开盘且号码完整 → 不再是逾期未到。
    assert scheduler._compute_dynamic_crawl_interval() == 300


def test_dynamic_interval_stays_near_while_expected_row_is_still_closed(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler
    from db import connect

    db_path = _setup(tmp_path)
    scheduler = CrawlerScheduler(db_path)
    past_ms = int((datetime.now(timezone.utc) - timedelta(minutes=3)).timestamp() * 1000)
    values = {
        "lottery.macau_current_period": "2026264",
        "lottery.macau_next_time": str(past_ms),
        "crawler.crawl_interval_near_draw": 10,
        "crawler.crawl_interval_far_draw": 300,
    }
    monkeypatch.setattr("crawler.scheduler._cfg", lambda _db, key, default: values.get(key, default))

    with connect(db_path) as conn:
        _insert_draw(conn, MACAU, 2026, 265, "", "2026-09-22 21:32:32", 0)
        conn.commit()

    assert scheduler._compute_dynamic_crawl_interval() == 10


# ── 2. 已开盘的一期不回退、不再产生假审计 ─────────────────────────────

def test_upsert_never_reverts_an_already_opened_draw(tmp_path):
    from crawler.collectors import _upsert_draw
    from db import connect

    db_path = _setup(tmp_path)
    with connect(db_path) as conn:
        _upsert_draw(conn, MACAU, 2026, 135, COMPLETE, "2026-08-07 21:30:00", 1, "2026-08-07T14:32:00+00:00")
        # 调度侧对“当前期”始终传 is_opened=0，这里模拟同一期的后续刷新。
        _upsert_draw(
            conn, MACAU, 2026, 135, "08,09,10,11,12,13,14",
            "2026-08-07 21:30:00", 0, "2026-08-07T14:33:00+00:00",
        )
        row = conn.execute(
            "SELECT is_opened, numbers FROM lottery_draws "
            "WHERE lottery_type_id = ? AND year = 2026 AND term = 135",
            (MACAU,),
        ).fetchone()

    assert row["is_opened"] == 1
    assert row["numbers"] == "08,09,10,11,12,13,14"


def test_refreshing_an_already_published_period_writes_no_auto_open_audit(tmp_path):
    from crawler.scheduler import CrawlerScheduler
    from db import connect

    db_path = _setup(tmp_path)
    with connect(db_path) as conn:
        _insert_draw(conn, HK, 2026, 91, COMPLETE, "2026-08-20 21:30:00", 1)
        conn.commit()

    scheduler = CrawlerScheduler(db_path)
    changed = scheduler._process_auto_crawl_batch(
        HK,
        "香港彩",
        [{
            "issue": "2026091",
            "open_time": "2026-08-20 21:30:00",
            "result": COMPLETE,
            "next_time": "1787405400000",
        }],
    )

    with connect(db_path) as conn:
        audit_count = conn.execute(
            "SELECT COUNT(*) AS count FROM draw_audit_log WHERE event = 'auto_open'"
        ).fetchone()["count"]
        row = conn.execute(
            "SELECT is_opened FROM lottery_draws WHERE lottery_type_id = ? AND year = 2026 AND term = 91",
            (HK,),
        ).fetchone()

    assert changed is True
    assert audit_count == 0
    assert row["is_opened"] == 1


def test_first_publication_of_a_new_period_still_writes_one_auto_open_audit(tmp_path):
    from crawler.scheduler import CrawlerScheduler
    from db import connect

    db_path = _setup(tmp_path)
    with connect(db_path) as conn:
        _insert_draw(conn, HK, 2026, 90, COMPLETE, "2026-08-18 21:30:00", 1)
        conn.commit()

    scheduler = CrawlerScheduler(db_path)
    scheduler._process_auto_crawl_batch(
        HK,
        "香港彩",
        [{
            "issue": "2026091",
            "open_time": "2026-08-20 21:30:00",
            "result": COMPLETE,
            "next_time": "",
        }],
    )

    with connect(db_path) as conn:
        audits = conn.execute(
            "SELECT lottery_type_id, year, term, detail FROM draw_audit_log WHERE event = 'auto_open'"
        ).fetchall()
        row = conn.execute(
            "SELECT is_opened FROM lottery_draws WHERE lottery_type_id = ? AND year = 2026 AND term = 91",
            (HK,),
        ).fetchone()

    assert len(audits) == 1
    audit = dict(audits[0])
    assert (audit["lottery_type_id"], audit["year"], audit["term"]) == (HK, 2026, 91)
    assert audit["detail"].startswith("opened=1 public_open_delay_seconds=")
    assert row["is_opened"] == 1


# ── 3. 号码完整性闸门与香港彩轮序发布 ────────────────────────────────

def test_enqueue_publication_rejects_incomplete_numbers_for_strict_lotteries(tmp_path):
    from db import connect
    from outbox.draw_publication import enqueue_draw_publication

    db_path = _setup(tmp_path)
    base = {
        "lottery_type_id": MACAU, "year": 2026, "term": 265,
        "draw_time": "2026-09-22 21:32:32", "next_time": "", "status": 1,
        "is_opened": 1, "next_term": 266,
    }
    with connect(db_path) as conn:
        assert enqueue_draw_publication(conn, previous=None, current={**base, "numbers": "11,22"}) is None
        assert enqueue_draw_publication(conn, previous=None, current={**base, "numbers": ""}) is None
        assert enqueue_draw_publication(
            conn, previous=None, current={**base, "numbers": "11,22,33,44,55,66,60"}
        ) is None
        assert enqueue_draw_publication(conn, previous=None, current={**base, "numbers": COMPLETE}) == "draw.published"

    # 香港彩允许按顺序轮序发布当前前缀。
    hk_base = {**base, "lottery_type_id": HK, "term": 103, "next_term": 104}
    with connect(db_path) as conn:
        assert enqueue_draw_publication(conn, previous=None, current={**hk_base, "numbers": "05"}) == "draw.published"


def test_strict_lottery_with_incomplete_numbers_is_not_opened(tmp_path):
    from crawler.scheduler import CrawlerScheduler
    from db import connect

    db_path = _setup(tmp_path)
    with connect(db_path) as conn:
        _insert_draw(conn, MACAU, 2026, 232, "11,22,33", "2026-08-20 21:32:00", 0)
        conn.commit()

    scheduler = CrawlerScheduler(db_path)
    opened = scheduler._open_specific_records(MACAU, {"year": 2026, "term": 232})

    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT is_opened FROM lottery_draws WHERE lottery_type_id = ? AND year = 2026 AND term = 232",
            (MACAU,),
        ).fetchone()
        outbox = conn.execute("SELECT COUNT(*) AS count FROM publication_outbox").fetchone()["count"]

    assert opened == 0
    assert row["is_opened"] == 0
    assert outbox == 0


def test_hk_progressive_prefix_is_opened_and_published_in_order(tmp_path):
    from crawler.scheduler import CrawlerScheduler
    from db import connect

    db_path = _setup(tmp_path)
    with connect(db_path) as conn:
        _insert_draw(conn, HK, 2026, 103, "05", "2026-09-22 21:33:00", 0)
        conn.commit()

    scheduler = CrawlerScheduler(db_path)
    opened = scheduler._open_specific_records(HK, {"year": 2026, "term": 103})

    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT is_opened, numbers FROM lottery_draws WHERE lottery_type_id = ? AND year = 2026 AND term = 103",
            (HK,),
        ).fetchone()
        event = conn.execute(
            "SELECT event_key FROM publication_outbox WHERE event_key = 'draw-published:1:2026:103'"
        ).fetchone()

    assert opened == 1
    assert row["is_opened"] == 1
    assert row["numbers"] == "05"
    assert event["event_key"] == "draw-published:1:2026:103"


def test_auto_open_keeps_incomplete_rows_closed(tmp_path):
    from crawler.scheduler import CrawlerScheduler
    from db import connect

    db_path = _setup(tmp_path)
    past = (datetime.now(timezone.utc) + timedelta(hours=8) - timedelta(minutes=5)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    with connect(db_path) as conn:
        _insert_draw(conn, TAIWAN, 2026, 300, "", past, 0)
        _insert_draw(conn, MACAU, 2026, 300, "11,22", past, 0)
        conn.commit()

    CrawlerScheduler(db_path)._auto_open_draws()

    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT lottery_type_id, is_opened FROM lottery_draws ORDER BY lottery_type_id"
        ).fetchall()

    assert [dict(row) for row in rows] == [
        {"lottery_type_id": MACAU, "is_opened": 0},
        {"lottery_type_id": TAIWAN, "is_opened": 0},
    ]


# ── 4. 分级告警独立轮询与历史时延基线 ────────────────────────────────

def test_staged_alert_check_has_its_own_timer_loop(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler

    db_path = _setup(tmp_path)
    scheduler = CrawlerScheduler(db_path)
    scheduler._running = True
    calls: list[int] = []
    monkeypatch.setattr("crawler.scheduler.threading", _FakeThreading)
    monkeypatch.setattr(scheduler, "_check_staged_timeout_alerts", lambda: calls.append(1))

    scheduler._schedule_staged_timeout_alerts()

    assert calls == [1]
    assert isinstance(scheduler._staged_alert_timer, _RecordingTimer)
    assert scheduler._staged_alert_timer.started is True


def test_staged_alert_thresholds_use_observed_latency_baseline(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler, _draw_alert_baseline_seconds
    from db import connect

    db_path = _setup(tmp_path)
    # 两期历史：源站开奖时间到入库都是 400 秒。
    with connect(db_path) as conn:
        for term in (134, 135):
            conn.execute(
                """
                INSERT INTO lottery_draws (
                    lottery_type_id, year, term, numbers, draw_time, next_time,
                    status, is_opened, next_term, created_at, updated_at
                ) VALUES (?, 2026, ?, ?, ?, '', 1, 1, ?, ?, ?)
                """,
                (
                    MACAU, term, COMPLETE, "2026-08-07 21:30:00", term + 1,
                    "2026-08-07T13:36:40+00:00",  # 21:30 Beijing = 13:30 UTC，入库晚 400 秒
                    "2026-08-07T13:36:40+00:00",
                ),
            )
        conn.commit()

    monkeypatch.setattr(
        "crawler.scheduler._cfg",
        lambda _db, key, default: 120 if key == "alert.draw_latency_baseline_seconds" else default,
    )
    baseline = _draw_alert_baseline_seconds(db_path, MACAU)

    assert baseline == 400

    # 基线之内不得触发黄色告警。
    scheduler = CrawlerScheduler(db_path)
    alerts: list[str] = []
    monkeypatch.setattr(
        "crawler.scheduler._cfg",
        lambda _db, key, default: {
            "lottery.macau_next_time": str(
                int((datetime.now(timezone.utc) - timedelta(seconds=200)).timestamp() * 1000)
            ),
            "alert.draw_latency_baseline_seconds": 120,
        }.get(key, default),
    )
    monkeypatch.setattr(
        "crawler.scheduler._fetch_current_draw_period", lambda *_args, **_kwargs: ("2026265", None)
    )
    monkeypatch.setattr(
        "crawler.scheduler.alert_crawler_failure", lambda *_a, **_k: alerts.append("alert")
    )

    scheduler._check_staged_timeout_alerts()

    assert alerts == []


# ── 5. 开奖后回填任务必须按期重排 ────────────────────────────────────

def test_backfill_after_draw_task_key_is_per_issue_so_it_rearms(tmp_path, monkeypatch):
    """回填任务 key 必须带期号；按彩种固定的 key 会在第一次 done 后永久停摆。"""
    from crawler.scheduler import _schedule_backfill_after_draw
    from db import connect

    db_path = _setup(tmp_path)
    monkeypatch.setattr(
        "crawler.scheduler._cfg",
        lambda _db, key, default: 1 if key == "history_backfill_delay_after_draw" else default,
    )
    with connect(db_path) as conn:
        _insert_draw(conn, MACAU, 2026, 264, COMPLETE, "2026-09-21 21:32:32", 1)
        conn.commit()

    _schedule_backfill_after_draw(db_path, MACAU)
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT task_key, status FROM scheduler_tasks WHERE task_type = 'backfill_after_draw'"
        ).fetchall()
    assert [dict(row) for row in rows] == [
        {"task_key": "backfill_after_draw:2:2026264", "status": "pending"}
    ]

    # 第一期已执行完成，随后出现下一期
    with connect(db_path) as conn:
        conn.execute("UPDATE scheduler_tasks SET status = 'done' WHERE task_type = 'backfill_after_draw'")
        _insert_draw(conn, MACAU, 2026, 265, COMPLETE, "2026-09-22 21:32:32", 1)
        conn.commit()

    _schedule_backfill_after_draw(db_path, MACAU)
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT task_key, status FROM scheduler_tasks WHERE task_type = 'backfill_after_draw' "
            "ORDER BY task_key"
        ).fetchall()
    assert [dict(row) for row in rows] == [
        {"task_key": "backfill_after_draw:2:2026264", "status": "done"},
        {"task_key": "backfill_after_draw:2:2026265", "status": "pending"},
    ]


# ── 6. 入库时延基线按“计划开奖钟点”衡量 ──────────────────────────────

def _insert_draw_with_created_at(conn, lottery_type_id, year, term, draw_time, created_at):
    conn.execute(
        """
        INSERT INTO lottery_draws (
            lottery_type_id, year, term, numbers, draw_time, next_time,
            status, is_opened, next_term, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lottery_type_id, year, term, COMPLETE, draw_time, "",
            1, 1, term + 1, created_at, created_at,
        ),
    )


def test_arrival_latency_baseline_uses_the_scheduled_draw_clock(tmp_path, monkeypatch):
    """香港彩先给部分号码，draw_time 晚于入库时间；基线必须相对计划钟点计算才不为 0。"""
    from crawler.scheduler import _observed_draw_arrival_latency_seconds
    from db import connect

    db_path = _setup(tmp_path)
    with connect(db_path) as conn:
        # 计划 21:30（=13:30 UTC），首次入库 13:33:19 → 相对计划时延 199 秒
        _insert_draw_with_created_at(
            conn, HK, 2026, 101, "2026-09-17 21:34:00", "2026-09-17T13:33:19+00:00"
        )
        _insert_draw_with_created_at(
            conn, HK, 2026, 102, "2026-09-19 21:34:00", "2026-09-19T13:33:19+00:00"
        )
        conn.commit()

    monkeypatch.setattr(
        "crawler.scheduler._cfg",
        lambda _db, key, default: {"draw.hk_default_draw_time": "21:30"}.get(key, default),
    )

    # 按 draw_time 口径会算成负数并夹到 0；按计划钟点口径为 199。
    assert _observed_draw_arrival_latency_seconds(db_path, HK) == 199


def test_scheduled_draw_utc_converts_beijing_clock_to_utc(tmp_path, monkeypatch):
    from crawler.scheduler import _scheduled_draw_utc

    monkeypatch.setattr(
        "crawler.scheduler._cfg",
        lambda _db, key, default: {"draw.macau_default_draw_time": "21:32"}.get(key, default),
    )
    assert _scheduled_draw_utc(str(tmp_path), MACAU, "2026-09-21") == datetime(
        2026, 9, 21, 13, 32, tzinfo=timezone.utc
    )
