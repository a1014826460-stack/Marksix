from __future__ import annotations

from datetime import datetime, timezone


def _setup(tmp_path):
    from database.bootstrap import ensure_admin_tables

    db_path = str(tmp_path / "hk-macau-fast-open.sqlite3")
    ensure_admin_tables(db_path)
    return db_path


def test_csjid_payload_is_normalized_with_beijing_draw_time():
    from crawler.result_crawler import transform_standard_list

    payload = {
        "errorCode": 0,
        "result": {
            "businessCode": 0,
            "data": {
                "preDrawIssue": "2026231",
                "preDrawCode": "39,46,23,11,08,13,20",
                "preDrawTime": "2026-08-19 21:32:32",
            },
        },
    }

    assert transform_standard_list(payload, crawler_type=2) == [
        {
            "issue": "231",
            "open_time": "2026-08-19 21:32:32",
            "result": "39,46,23,11,08,13,20",
            "next_time": "",
        }
    ]


def test_scheduler_fetch_records_normalizes_csjid_payload_before_upsert(tmp_path, monkeypatch):
    from crawler.scheduler import _fetch_current_draw_records

    payload = {
        "result": {
            "data": {
                "preDrawIssue": "2026231",
                "preDrawCode": "39,46,23,11,08,13,20",
                "preDrawTime": "2026-08-19 21:32:32",
            },
        },
    }
    monkeypatch.setattr(
        "crawler.result_crawler.fetch_current_term_data",
        lambda **_kwargs: (__import__("json").dumps(payload), 200),
    )
    monkeypatch.setattr(
        "crawler.scheduler._get_effective_collect_url",
        lambda *_args, **_kwargs: ("https://api.csjid.com/smallSix/findSmallSixInfo.do?lotCode=MACAO_2033", ""),
    )

    assert _fetch_current_draw_records(str(tmp_path / "db.sqlite3"), 2) == [
        {
            "issue": "231",
            "open_time": "2026-08-19 21:32:32",
            "result": "39,46,23,11,08,13,20",
            "next_time": "",
        }
    ]


def test_csjid_request_does_not_append_lnlllt_query_parameters(monkeypatch):
    from crawler.result_crawler import fetch_current_term_data

    observed: dict[str, object] = {}

    class Response:
        status_code = 200
        text = "{}"

    def fake_get(url, **kwargs):
        observed["url"] = url
        observed["params"] = kwargs["params"]
        return Response()

    monkeypatch.setattr("crawler.result_crawler.requests.get", fake_get)
    fetch_current_term_data(type=1, collect_url="https://api.csjid.com/smallSix/findSmallSixInfo.do?lotCode=10048")

    assert observed == {
        "url": "https://api.csjid.com/smallSix/findSmallSixInfo.do?lotCode=10048",
        "params": {},
    }


def test_csjid_payload_with_no_returned_numbers_is_rejected():
    from crawler.result_crawler import transform_standard_list

    payload = {
        "result": {
            "data": {
                "preDrawIssue": "2026232",
                "preDrawCode": "",
                "preDrawTime": "2026-08-20 21:32:00",
            },
        },
    }

    assert transform_standard_list(payload, crawler_type=2) == []


def test_upsert_only_opens_the_newly_returned_hk_draw(tmp_path):
    from crawler.scheduler import _upsert_current_draw_records
    from db import connect

    db_path = _setup(tmp_path)
    result = _upsert_current_draw_records(
        db_path,
        1,
        [{
            "issue": "2026091",
            "open_time": "2026-08-20 21:30:00",
            "result": "01,02,03,04,05,06,07",
            "next_time": "",
        }],
    )

    assert result == {
        "inserted": 1,
        "updated": 0,
        "skipped": 0,
        "latest_draw": {
            "year": 2026,
            "term": 91,
            "issue": "2026091",
            "open_time": "2026-08-20 21:30:00",
        },
    }
    with connect(db_path) as conn:
        assert conn.execute(
            "SELECT is_opened FROM lottery_draws WHERE lottery_type_id = 1 AND year = 2026 AND term = 91"
        ).fetchone()["is_opened"] == 0


def test_auto_crawl_never_fetches_or_opens_taiwan(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler
    from db import connect

    db_path = _setup(tmp_path)
    observed_lottery_types: list[int] = []
    scheduler = CrawlerScheduler(db_path)
    monkeypatch.setattr(
        "crawler.scheduler._fetch_current_draw_records",
        lambda _db_path, lottery_type_id, *, prefer_backup=False: observed_lottery_types.append(lottery_type_id) or [],
    )
    monkeypatch.setattr("crawler.scheduler.sync_all_lottery_type_next_times", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scheduler, "_reschedule_precise_checks", lambda: None)
    monkeypatch.setattr(scheduler, "_check_staged_timeout_alerts", lambda: None)

    scheduler._auto_crawl()

    assert observed_lottery_types == [1, 2]
    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) AS count FROM lottery_draws WHERE lottery_type_id = 3").fetchone()["count"] == 0


def test_auto_crawl_opens_a_new_hk_draw_in_the_same_cycle(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler
    from db import connect

    db_path = _setup(tmp_path)
    scheduler = CrawlerScheduler(db_path)
    monkeypatch.setattr(
        "crawler.scheduler._fetch_current_draw_records",
        lambda _db_path, _lottery_type_id, *, prefer_backup=False: [{
            "issue": "2026091",
            "open_time": "2026-08-20 21:30:00",
            "result": "01,02,03,04,05,06,07",
            "next_time": "",
        }],
    )
    monkeypatch.setattr("crawler.scheduler.sync_all_lottery_type_next_times", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scheduler, "_reschedule_precise_checks", lambda: None)
    monkeypatch.setattr(scheduler, "_check_staged_timeout_alerts", lambda: None)

    scheduler._auto_crawl()

    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT is_opened FROM lottery_draws WHERE lottery_type_id = 1 AND year = 2026 AND term = 91"
        ).fetchone()
        event = conn.execute(
            "SELECT event_key FROM publication_outbox WHERE event_key = 'draw-published:1:2026:91'"
        ).fetchone()
    assert row["is_opened"] == 1
    assert event["event_key"] == "draw-published:1:2026:91"


def test_precise_fetch_enters_chase_mode_when_source_still_has_current_period(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler

    db_path = _setup(tmp_path)
    scheduler = CrawlerScheduler(db_path)
    values = {"lottery.hk_current_period": "2026090"}
    monkeypatch.setattr("crawler.scheduler._cfg", lambda _db_path, key, default: values.get(key, default))
    monkeypatch.setattr("crawler.scheduler._fetch_current_draw_period", lambda *_args: ("2026090", None))

    result = scheduler._do_precise_draw_fetch_and_open(1)

    assert result["status"] == "deferred"
    assert scheduler._chase_modes == {1: True}


def test_draw_latency_metrics_compare_beijing_draw_time_with_utc_event_time():
    from crawler.scheduler import _draw_latency_seconds

    assert _draw_latency_seconds(
        "2026-08-20 21:30:00",
        datetime(2026, 8, 20, 13, 30, 5, tzinfo=timezone.utc),
    ) == 5


def test_precise_fetch_uses_backup_when_primary_still_has_current_period(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler

    db_path = _setup(tmp_path)
    scheduler = CrawlerScheduler(db_path)
    monkeypatch.setattr(
        "crawler.scheduler._cfg",
        lambda _db_path, key, default: {"lottery.hk_current_period": "2026090"}.get(key, default),
    )
    calls: list[bool] = []

    def fetch_period(_lottery_type_id, _db_path, *, prefer_backup=False):
        calls.append(prefer_backup)
        return ("2026091" if prefer_backup else "2026090"), None

    monkeypatch.setattr("crawler.scheduler._fetch_current_draw_period", fetch_period)
    monkeypatch.setattr("crawler.scheduler._has_backup_collect_url", lambda *_args: True)
    record_fetch_preferences: list[bool] = []

    def fetch_records(*_args, **kwargs):
        record_fetch_preferences.append(kwargs["prefer_backup"])
        return [{
            "issue": "2026091", "open_time": "2026-08-20 21:30:00",
            "result": "01,02,03,04,05,06,07", "next_time": "",
        }]

    monkeypatch.setattr("crawler.scheduler._fetch_current_draw_records", fetch_records)
    monkeypatch.setattr(
        "crawler.scheduler._upsert_current_draw_records",
        lambda *_args: {"inserted": 1, "updated": 0, "skipped": 0, "latest_draw": {"year": 2026, "term": 91}},
    )
    monkeypatch.setattr(scheduler, "_open_specific_records", lambda *_args: 1)
    monkeypatch.setattr("crawler.scheduler._schedule_backfill_after_draw", lambda *_args: None)
    monkeypatch.setattr("crawler.scheduler.reset_crawler_fail_count", lambda *_args: None)

    assert scheduler._do_precise_draw_fetch_and_open(1)["status"] == "ok"
    assert calls == [False, True]
    assert record_fetch_preferences == [True]


def test_chase_mode_auto_crawl_probes_backup_then_primary_when_both_stale(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler

    db_path = _setup(tmp_path)
    scheduler = CrawlerScheduler(db_path)
    scheduler._set_lottery_chase_mode(1, True)
    preferences: list[bool] = []
    monkeypatch.setattr("crawler.scheduler._has_backup_collect_url", lambda *_args: True)
    monkeypatch.setattr("crawler.scheduler.alert_crawler_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "crawler.scheduler._fetch_current_draw_records",
        lambda _db_path, _lottery_type_id, *, prefer_backup=False: preferences.append(prefer_backup) or [],
    )
    monkeypatch.setattr("crawler.scheduler.sync_all_lottery_type_next_times", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scheduler, "_reschedule_precise_checks", lambda: None)
    monkeypatch.setattr(scheduler, "_check_staged_timeout_alerts", lambda: None)

    scheduler._auto_crawl()

    # 追赶的 HK 依次探测备用源(True)与主源(False)；未追赶的 Macau 仅探测主源。
    assert preferences == [True, False, False]


def test_chase_mode_auto_crawl_opens_from_backup_without_probing_primary(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler
    from db import connect

    db_path = _setup(tmp_path)
    scheduler = CrawlerScheduler(db_path)
    scheduler._set_lottery_chase_mode(1, True)
    probes: list[tuple[int, bool]] = []

    def fetch_records(_db_path, lottery_type_id, *, prefer_backup=False):
        probes.append((lottery_type_id, prefer_backup))
        if lottery_type_id == 1 and prefer_backup is True:
            return [{
                "issue": "2026091",
                "open_time": "2026-08-20 21:30:00",
                "result": "01,02,03,04,05,06,07",
                "next_time": "",
            }]
        return []

    monkeypatch.setattr("crawler.scheduler._has_backup_collect_url", lambda *_args: True)
    monkeypatch.setattr("crawler.scheduler._fetch_current_draw_records", fetch_records)
    monkeypatch.setattr("crawler.scheduler.alert_crawler_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("crawler.scheduler.sync_all_lottery_type_next_times", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scheduler, "_reschedule_precise_checks", lambda: None)
    monkeypatch.setattr(scheduler, "_check_staged_timeout_alerts", lambda: None)

    scheduler._auto_crawl()

    with connect(db_path) as conn:
        hk = conn.execute(
            "SELECT is_opened FROM lottery_draws WHERE lottery_type_id = 1 AND year = 2026 AND term = 91"
        ).fetchone()
        event = conn.execute(
            "SELECT event_key FROM publication_outbox WHERE event_key = 'draw-published:1:2026:91'"
        ).fetchone()
    assert hk["is_opened"] == 1
    assert event["event_key"] == "draw-published:1:2026:91"
    # 备用源命中后不再探测主源（避免双源覆盖）；Macau 仍独立探测一次。
    assert probes == [(1, True), (2, False)]


def test_auto_crawl_opens_hk_when_only_hk_data_has_arrived(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler
    from db import connect

    db_path = _setup(tmp_path)
    scheduler = CrawlerScheduler(db_path)

    def fetch_records(_db_path, lottery_type_id, *, prefer_backup=False):
        if lottery_type_id == 1:
            return [{
                "issue": "2026091",
                "open_time": "2026-08-20 21:30:00",
                "result": "01,02,03,04,05,06,07",
                "next_time": "",
            }]
        return []  # 澳门彩数据尚未到达

    monkeypatch.setattr("crawler.scheduler._fetch_current_draw_records", fetch_records)
    monkeypatch.setattr("crawler.scheduler.alert_crawler_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("crawler.scheduler.sync_all_lottery_type_next_times", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scheduler, "_reschedule_precise_checks", lambda: None)
    monkeypatch.setattr(scheduler, "_check_staged_timeout_alerts", lambda: None)

    scheduler._auto_crawl()

    with connect(db_path) as conn:
        hk = conn.execute(
            "SELECT is_opened FROM lottery_draws WHERE lottery_type_id = 1 AND year = 2026 AND term = 91"
        ).fetchone()
        event = conn.execute(
            "SELECT event_key FROM publication_outbox WHERE event_key = 'draw-published:1:2026:91'"
        ).fetchone()
        macau_count = conn.execute(
            "SELECT COUNT(*) AS count FROM lottery_draws WHERE lottery_type_id = 2"
        ).fetchone()["count"]
    assert hk["is_opened"] == 1
    assert event["event_key"] == "draw-published:1:2026:91"
    assert macau_count == 0


def test_auto_crawl_opens_macau_when_only_macau_data_has_arrived(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler
    from db import connect

    db_path = _setup(tmp_path)
    scheduler = CrawlerScheduler(db_path)

    def fetch_records(_db_path, lottery_type_id, *, prefer_backup=False):
        if lottery_type_id == 2:
            return [{
                "issue": "2026232",
                "open_time": "2026-08-20 21:32:00",
                "result": "11,22,33,44,55,66,77",
                "next_time": "",
            }]
        return []  # 香港彩数据尚未到达

    monkeypatch.setattr("crawler.scheduler._fetch_current_draw_records", fetch_records)
    monkeypatch.setattr("crawler.scheduler.alert_crawler_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("crawler.scheduler.sync_all_lottery_type_next_times", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scheduler, "_reschedule_precise_checks", lambda: None)
    monkeypatch.setattr(scheduler, "_check_staged_timeout_alerts", lambda: None)

    scheduler._auto_crawl()

    with connect(db_path) as conn:
        macau = conn.execute(
            "SELECT is_opened FROM lottery_draws WHERE lottery_type_id = 2 AND year = 2026 AND term = 232"
        ).fetchone()
        event = conn.execute(
            "SELECT event_key FROM publication_outbox WHERE event_key = 'draw-published:2:2026:232'"
        ).fetchone()
        hk_count = conn.execute(
            "SELECT COUNT(*) AS count FROM lottery_draws WHERE lottery_type_id = 1"
        ).fetchone()["count"]
    assert macau["is_opened"] == 1
    assert event["event_key"] == "draw-published:2:2026:232"
    assert hk_count == 0


def test_precise_fetch_turns_off_chase_mode_when_primary_recovers(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler

    db_path = _setup(tmp_path)
    scheduler = CrawlerScheduler(db_path)
    scheduler._set_lottery_chase_mode(1, True)
    monkeypatch.setattr(
        "crawler.scheduler._cfg",
        lambda _db_path, key, default: {"lottery.hk_current_period": "2026090"}.get(key, default),
    )
    # 主源恢复：返回预期新期号
    monkeypatch.setattr("crawler.scheduler._fetch_current_draw_period", lambda *_args: ("2026091", None))
    monkeypatch.setattr(
        "crawler.scheduler._fetch_current_draw_records",
        lambda *_args, **_kwargs: [{
            "issue": "2026091",
            "open_time": "2026-08-20 21:30:00",
            "result": "01,02,03,04,05,06,07",
            "next_time": "",
        }],
    )
    monkeypatch.setattr(
        "crawler.scheduler._upsert_current_draw_records",
        lambda *_args: {"inserted": 1, "updated": 0, "skipped": 0, "latest_draw": {"year": 2026, "term": 91}},
    )
    monkeypatch.setattr(scheduler, "_open_specific_records", lambda *_args: 1)
    monkeypatch.setattr("crawler.scheduler._schedule_backfill_after_draw", lambda *_args: None)
    monkeypatch.setattr("crawler.scheduler.reset_crawler_fail_count", lambda *_args: None)

    result = scheduler._do_precise_draw_fetch_and_open(1)

    assert result["status"] == "ok"
    assert scheduler._chase_modes == {1: False}


def test_open_specific_records_fallback_opens_past_due_draws(tmp_path):
    from crawler.scheduler import CrawlerScheduler
    from db import connect

    db_path = _setup(tmp_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, next_time,
                status, is_opened, next_term, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1, 2026, 90,
                "01,02,03,04,05,06,07", "2026-08-19 21:30:00", "",
                1, 0, 91,
                "2026-08-19T13:30:00+00:00", "2026-08-19T13:30:00+00:00",
            ),
        )

    scheduler = CrawlerScheduler(db_path)
    opened = scheduler._open_specific_records(1)

    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT is_opened FROM lottery_draws WHERE lottery_type_id = 1 AND year = 2026 AND term = 90"
        ).fetchone()
    assert opened == 1
    assert row["is_opened"] == 1
