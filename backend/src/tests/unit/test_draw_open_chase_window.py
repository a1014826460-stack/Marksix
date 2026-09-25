"""港澳彩准时开奖 P1 回归测试（2026-09-25 澳门彩 268 期延迟 367 秒的根因）。

覆盖四处修复：
1. 已开奖期的重复刷新（源站把旧期 next_time 前滚）不得改写排期；
2. 旧期刷新不得关闭追赶模式；
3. 到点后进入"固定追赶窗口"（独立定时器每 5 秒重试），不再依赖被污染的 next_time；
4. 追赶窗口内并发探测全部采集源（含备用源），任一新期先到即用。
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

from db import connect
from crawler import collectors
from crawler.scheduler import CrawlerScheduler

MACAU = 2
_PERIOD_267 = ("2026", 267)
_PERIOD_268 = ("2026", 268)
_NUMBERS = "16,20,25,22,09,41,40"


def _ms(dt: datetime) -> str:
    return str(int(dt.timestamp() * 1000))


def _setup_db(tmp_path, name: str):
    db_path = tmp_path / f"{name}.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE lottery_draws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lottery_type_id INTEGER, year INTEGER, term INTEGER,
                numbers TEXT, draw_time TEXT, status INTEGER,
                is_opened INTEGER DEFAULT 0, next_term INTEGER, next_time TEXT,
                created_at TEXT, updated_at TEXT,
                UNIQUE(lottery_type_id, year, term)
            )
            """
        )
        conn.execute(
            "CREATE TABLE lottery_types (id INTEGER PRIMARY KEY, name TEXT, collect_url TEXT, "
            "draw_time TEXT, next_time TEXT, updated_at TEXT)"
        )
        conn.execute(
            """
            CREATE TABLE system_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, value_text TEXT,
                value_type TEXT, description TEXT, is_secret INTEGER DEFAULT 0,
                created_at TEXT, updated_at TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO lottery_types (id, name, collect_url, draw_time, next_time, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (MACAU, "澳门彩", "https://www.lnlllt.com/api.php", "21:32", "", "2026-09-25T00:00:00+00:00"),
        )
    return db_path


def _set_config(db_path, key: str, value: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO system_config (key, value_text, value_type, description, "
            "is_secret, created_at, updated_at) VALUES (?, ?, 'string', '', 0, ?, ?)",
            (key, value, "2026-09-25T00:00:00+00:00", "2026-09-25T00:00:00+00:00"),
        )


def _set_lt_next_time(db_path, value: str) -> None:
    with connect(db_path) as conn:
        conn.execute("UPDATE lottery_types SET next_time = ? WHERE id = ?", (value, MACAU))


def _insert_draw(db_path, year: int, term: int, *, is_opened: int, next_time: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO lottery_draws (lottery_type_id, year, term, numbers, draw_time, "
            "status, is_opened, next_term, next_time, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)",
            (
                MACAU, year, term, _NUMBERS, f"{year}-09-25 21:32:32",
                is_opened, term + 1, next_time,
                "2026-09-25T13:38:39.697659+00:00", "2026-09-25T13:38:39.697659+00:00",
            ),
        )


# ── 1. 旧期刷新不得前滚 next_time ────────────────────────────────────


def test_refresh_of_published_period_does_not_advance_next_time(tmp_path, monkeypatch):
    """源站旧期刷新带来的被前滚 next_time 不得写回库，也不得同步到排期。"""
    db_path = _setup_db(tmp_path, "draw-refresh-next-time")
    next_25 = _ms(datetime(2026, 9, 25, 13, 32, tzinfo=timezone.utc))   # 09-25 21:32 北京
    next_26 = _ms(datetime(2026, 9, 26, 13, 32, tzinfo=timezone.utc))   # 被前滚到 09-26
    _insert_draw(db_path, 2026, 267, is_opened=1, next_time=next_25)
    _set_lt_next_time(db_path, next_25)
    _set_config(db_path, "lottery.macau_next_time", next_25)
    monkeypatch.setattr(collectors, "enqueue_draw_publication", lambda *a, **k: None)

    with connect(db_path) as conn:
        # 场景：源站在切到 268 之后仍回旧期 267，且带来的 next_time 已前滚到 09-26
        collectors._upsert_draw(
            conn, MACAU, 2026, 267, _NUMBERS, "2026-09-25 21:32:32", 1,
            "2026-09-25T13:38:40+00:00", next_time=next_26,
        )
        row = conn.execute(
            "SELECT next_time FROM lottery_draws WHERE lottery_type_id = ? AND year = 2026 AND term = 267",
            (MACAU,),
        ).fetchone()
        lt_row = conn.execute("SELECT next_time FROM lottery_types WHERE id = ?", (MACAU,)).fetchone()
        cfg_row = conn.execute(
            "SELECT value_text FROM system_config WHERE key = 'lottery.macau_next_time'"
        ).fetchone()

    assert row["next_time"] == next_25, "已开奖期刷新不得改写该行 next_time"
    assert lt_row["next_time"] == next_25, "lottery_types.next_time 不得被旧期刷新前滚"
    assert cfg_row["value_text"] == next_25, "system_config 排期不得被旧期刷新前滚"


def test_new_period_insert_still_advances_next_time(tmp_path, monkeypatch):
    """新期首次入库（真实排期推进）仍必须正常同步 next_time。"""
    db_path = _setup_db(tmp_path, "draw-new-period-next-time")
    next_25 = _ms(datetime(2026, 9, 25, 13, 32, tzinfo=timezone.utc))
    next_26 = _ms(datetime(2026, 9, 26, 13, 32, tzinfo=timezone.utc))
    _insert_draw(db_path, 2026, 267, is_opened=1, next_time=next_25)
    _set_lt_next_time(db_path, next_25)
    _set_config(db_path, "lottery.macau_next_time", next_25)
    monkeypatch.setattr(collectors, "enqueue_draw_publication", lambda *a, **k: None)

    with connect(db_path) as conn:
        collectors._upsert_draw(
            conn, MACAU, 2026, 268, _NUMBERS, "2026-09-25 21:32:32", 1,
            "2026-09-25T13:38:40+00:00", next_time=next_26,
        )
        row = conn.execute(
            "SELECT next_time FROM lottery_draws WHERE lottery_type_id = ? AND term = 268",
            (MACAU,),
        ).fetchone()
        lt_row = conn.execute("SELECT next_time FROM lottery_types WHERE id = ?", (MACAU,)).fetchone()

    assert row["next_time"] == next_26
    assert lt_row["next_time"] == next_26


# ── 2. 旧期刷新不得关闭追赶 ──────────────────────────────────────────


def _scheduler(db_path) -> CrawlerScheduler:
    scheduler = CrawlerScheduler(db_path)
    scheduler._running = True
    scheduler._arm_chase_timer = lambda lt: None  # 测试中不启动真实线程
    return scheduler


def test_old_period_refresh_keeps_chase_mode(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path, "chase-kept-on-refresh")
    _insert_draw(db_path, 2026, 267, is_opened=1, next_time="")
    scheduler = _scheduler(db_path)
    scheduler._set_lottery_chase_mode(MACAU, True)
    assert scheduler._chase_is_active(MACAU) is True

    monkeypatch.setattr(
        "crawler.scheduler._upsert_current_draw_records",
        lambda *_a, **_k: {
            "inserted": 0, "updated": 1, "skipped": 0,
            "latest_draw": {"year": 2026, "term": 267, "issue": "2026267",
                            "open_time": "2026-09-25 21:32:32"},
        },
    )
    scheduler._process_auto_crawl_batch(
        MACAU, "澳门彩", [{"issue": "2026267", "open_time": "2026-09-25 21:32:32",
                          "result": _NUMBERS}],
    )

    assert scheduler._chase_is_active(MACAU) is True, "旧期刷新不得关闭追赶窗口"


def test_new_period_open_closes_chase_mode(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path, "chase-closed-on-open")
    _insert_draw(db_path, 2026, 267, is_opened=1, next_time="")
    scheduler = _scheduler(db_path)
    scheduler._set_lottery_chase_mode(MACAU, True)

    monkeypatch.setattr(
        "crawler.scheduler._upsert_current_draw_records",
        lambda *_a, **_k: {
            "inserted": 1, "updated": 0, "skipped": 0,
            "latest_draw": {"year": 2026, "term": 268, "issue": "2026268",
                            "open_time": "2026-09-25 21:32:32"},
        },
    )
    monkeypatch.setattr(CrawlerScheduler, "_open_specific_records", lambda *_a, **_k: 1)
    monkeypatch.setattr("crawler.scheduler._schedule_backfill_after_draw", lambda *_a, **_k: None)
    scheduler._process_auto_crawl_batch(
        MACAU, "澳门彩", [{"issue": "2026268", "open_time": "2026-09-25 21:32:32",
                          "result": _NUMBERS}],
    )

    assert scheduler._chase_is_active(MACAU) is False


# ── 3. 到点后进入固定追赶窗口 ───────────────────────────────────────


def test_precise_fire_time_passed_arms_chase_window(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path, "chase-window-armed")
    past = _ms(datetime.now(timezone.utc) - timedelta(minutes=3))
    _set_config(db_path, "lottery.macau_next_time", past)
    _set_config(db_path, "lottery.macau_current_period", "2026267")

    scheduler = _scheduler(db_path)
    armed: list[int] = []
    scheduler._arm_chase_timer = lambda lt: armed.append(int(lt))
    monkeypatch.setattr(CrawlerScheduler, "_do_precise_draw_fetch_and_open", lambda *_a, **_k: {})
    monkeypatch.setattr(
        "crawler.scheduler.sync_all_lottery_type_next_times", lambda *_a, **_k: {}
    )
    monkeypatch.setattr(
        "crawler.scheduler._compute_hk_macau_default_next_time_ms", lambda *_a, **_k: ""
    )

    scheduler._reschedule_precise_checks_once()

    assert scheduler._chase_is_active(MACAU) is True
    assert scheduler._precise_expected.get(MACAU) == (2026, 268)
    assert MACAU in armed, "到点后必须武装独立追赶定时器"
    assert scheduler._chase_windows.get(MACAU) == 1


def test_chase_window_is_bounded_and_suppresses_after_budget(tmp_path, monkeypatch):
    """窗口到期按预算续期，用尽后对该期望期停用追赶（不会无限高频）。"""
    db_path = _setup_db(tmp_path, "chase-window-bound")
    _set_config(db_path, "crawler.chase_max_windows", "2")
    scheduler = _scheduler(db_path)
    scheduler._precise_expected[MACAU] = (2026, 268)
    monkeypatch.setattr(
        "crawler.scheduler._probe_sources_parallel", lambda *_a, **_k: None
    )

    scheduler._set_lottery_chase_mode(MACAU, True)
    assert scheduler._chase_windows.get(MACAU) == 1

    # 模拟第 1 个窗口自然到期
    scheduler._chase_deadlines[MACAU] = datetime.now(timezone.utc) - timedelta(seconds=1)
    scheduler._chase_tick(MACAU)
    assert scheduler._chase_windows.get(MACAU) == 2
    assert scheduler._chase_is_active(MACAU) is True

    # 第 2 个窗口到期 → 用尽预算 → 停用并记录抑制
    scheduler._chase_deadlines[MACAU] = datetime.now(timezone.utc) - timedelta(seconds=1)
    monkeypatch.setattr(CrawlerScheduler, "_reschedule_precise_checks", lambda self: None)
    scheduler._chase_tick(MACAU)
    assert scheduler._chase_is_active(MACAU) is False
    assert scheduler._chase_suppressed.get(MACAU) == "2026268"

    # 抑制期内再次请求开追单应被忽略
    scheduler._set_lottery_chase_mode(MACAU, True)
    assert scheduler._chase_is_active(MACAU) is False


# ── 4. 追赶窗口内并发探测全部源 ─────────────────────────────────────


def test_parallel_probe_returns_as_soon_as_any_source_has_the_period(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path, "chase-parallel-probe")
    _set_config(db_path, "draw.macau_backup_collect_url", "https://backup.example/api.php")
    from crawler import result_crawler

    expected = "2026268"

    def _fake_fetch(*, collect_url: str = "", **_kwargs):
        if "backup" in collect_url:
            return json.dumps({"issue": expected}), 200
        time.sleep(3)  # 主源很慢（模拟串行会把单轮拖到 3 秒以上）
        return json.dumps({"issue": expected}), 200

    monkeypatch.setattr(result_crawler, "fetch_current_term_data", _fake_fetch)
    monkeypatch.setattr(
        result_crawler,
        "transform_standard_list",
        lambda *_a, **_k: [{"issue": expected, "open_time": "2026-09-25 21:32:32"}],
    )

    started = time.monotonic()
    from crawler.scheduler import _probe_sources_parallel

    period = _probe_sources_parallel(MACAU, db_path, expected_period=expected)
    elapsed = time.monotonic() - started

    assert period == expected
    assert elapsed < 2.5, f"并发探测应在最慢源之前返回，实测 {elapsed:.2f}s"


def test_staged_alert_does_not_disable_chase_when_next_time_is_in_future(tmp_path, monkeypatch):
    """旧实现会在"next_time 还在未来"时关闭追赶；修复后必须保留追赶窗口。"""
    db_path = _setup_db(tmp_path, "staged-alert-keeps-chase")
    future = _ms(datetime.now(timezone.utc) + timedelta(hours=24))
    _set_config(db_path, "lottery.macau_next_time", future)
    _set_config(db_path, "lottery.macau_current_period", "2026267")

    scheduler = _scheduler(db_path)
    scheduler._set_lottery_chase_mode(MACAU, True)
    scheduler._check_staged_timeout_alerts()

    assert scheduler._chase_is_active(MACAU) is True


def test_stop_cancels_chase_timers(tmp_path):
    db_path = _setup_db(tmp_path, "chase-stop")
    scheduler = CrawlerScheduler(db_path)
    scheduler._running = True
    scheduler._set_lottery_chase_mode(MACAU, True)
    assert scheduler._chase_timers.get(MACAU) is not None

    scheduler.stop()

    assert scheduler._chase_timers == {}
    assert scheduler._chase_modes == {}
    assert scheduler._chase_deadlines == {}


# ── 5. 台湾彩开奖逻辑零改动护栏 ─────────────────────────────────────


def test_taiwan_chase_keeps_legacy_semantics(tmp_path, monkeypatch):
    """台湾彩必须保持改造前的追单语义：只置标记 + 重排 auto-crawl，不设窗口/定时器。"""
    db_path = _setup_db(tmp_path, "taiwan-legacy-chase")
    scheduler = _scheduler(db_path)
    rearmed: list[int] = []
    monkeypatch.setattr(scheduler, "_rearm_auto_crawl_for_chase", lambda: rearmed.append(3))

    scheduler._set_lottery_chase_mode(3, True)

    assert scheduler._chase_is_active(3) is True          # 标记为真即追赶（无截止时间）
    assert 3 not in scheduler._chase_timers                # 不启动独立追赶定时器
    assert 3 not in scheduler._chase_deadlines             # 不设追赶窗口
    assert rearmed == [3]                                  # 仍然重排 auto-crawl（旧行为）

    # 分级告警里"next_time 已在未来"必须照旧关闭台湾追单标记
    future = _ms(datetime.now(timezone.utc) + timedelta(hours=24))
    _set_config(db_path, "lottery.taiwan_next_time", future)
    scheduler._check_staged_timeout_alerts()

    assert scheduler._chase_is_active(3) is False


def test_taiwan_never_enters_parallel_probe(tmp_path, monkeypatch):
    """台湾彩不得进入港澳的并发多源探测/追赶心跳路径。"""
    db_path = _setup_db(tmp_path, "taiwan-no-probe")
    scheduler = _scheduler(db_path)
    scheduler._set_lottery_chase_mode(3, True)

    probed: list[int] = []
    monkeypatch.setattr(
        "crawler.scheduler._probe_sources_parallel",
        lambda lt, *_a, **_k: probed.append(int(lt)) or None,
    )

    assert scheduler._chase_timers.get(3) is None
    assert probed == []
