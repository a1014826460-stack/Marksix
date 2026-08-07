from __future__ import annotations

from datetime import datetime, timezone


def _setup(tmp_path):
    from database.bootstrap import ensure_admin_tables
    from db import connect

    db_path = str(tmp_path / "outbox-publisher.sqlite3")
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, status,
                is_opened, next_term, created_at, updated_at
            ) VALUES (3, 2026, 188, '01,02,03,04,05,06,07', '2026-08-07 22:32:00',
                      1, ?, 189, ?, ?)
            """,
            (1, "2026-08-07T14:32:00+00:00", "2026-08-07T14:32:00+00:00"),
        )
    return db_path


def _enqueue_opened_event(db_path):
    from db import connect
    from outbox.repository import enqueue_event

    with connect(db_path) as conn:
        enqueue_event(
            conn,
            event_key="draw-published:3:2026:188",
            event_type="draw.published",
            payload={"lottery_type_id": 3, "year": 2026, "term": 188},
            now="2026-08-07T14:32:00+00:00",
        )


def _publisher(db_path, snapshots):
    from outbox.publisher import DrawPublicationPublisher

    return DrawPublicationPublisher(
        db_path,
        snapshots=snapshots,
        owner="scheduler-a",
        now=lambda: datetime(2026, 8, 7, 14, 32, 5, tzinfo=timezone.utc),
    )


def test_publisher_uses_authoritative_opened_draw_and_marks_event_published(tmp_path):
    from cache.memory import MemoryCacheStore
    from cache.public_snapshots import PublicDrawSnapshots
    from db import connect

    db_path = _setup(tmp_path)
    _enqueue_opened_event(db_path)
    snapshots = PublicDrawSnapshots(MemoryCacheStore())

    assert _publisher(db_path, snapshots).drain(limit=4) == {"published": 1, "retried": 0}
    assert snapshots.get_latest_draw(3) == {
        "current_issue": "2026188",
        "draw_time": "2026-08-07 22:32:00",
        "result_balls": [
            {"value": "01", "zodiac": "", "color": "red"},
            {"value": "02", "zodiac": "", "color": "red"},
            {"value": "03", "zodiac": "", "color": "red"},
            {"value": "04", "zodiac": "", "color": "red"},
            {"value": "05", "zodiac": "", "color": "red"},
            {"value": "06", "zodiac": "", "color": "red"},
        ],
        "special_ball": {"value": "07", "zodiac": "", "color": "red"},
    }
    assert snapshots.get_current_period(3) == {
        "lottery_type_id": 3,
        "lottery_name": "台湾彩",
        "current_period": "2026188",
        "current_year": 2026,
        "current_term": 188,
    }
    with connect(db_path) as conn:
        event = conn.execute("SELECT status, attempts FROM publication_outbox").fetchone()
    assert dict(event) == {"status": "published", "attempts": 1}


def test_cache_failure_keeps_authoritative_draw_and_retries_event(tmp_path):
    from cache.contracts import CacheUnavailable
    from cache.public_snapshots import PublicDrawSnapshots
    from db import connect

    class BrokenCache:
        def publish_versioned(self, *args, **kwargs):
            raise CacheUnavailable("redis unavailable")

    db_path = _setup(tmp_path)
    _enqueue_opened_event(db_path)

    assert _publisher(db_path, PublicDrawSnapshots(BrokenCache())).drain(limit=4) == {"published": 0, "retried": 1}
    with connect(db_path) as conn:
        event = conn.execute("SELECT status, attempts, last_error FROM publication_outbox").fetchone()
        draw = conn.execute("SELECT is_opened, numbers FROM lottery_draws WHERE lottery_type_id = 3").fetchone()
    assert dict(event)["status"] == "pending"
    assert dict(event)["attempts"] == 1
    assert "redis unavailable" in str(dict(event)["last_error"])
    assert dict(draw) == {"is_opened": 1, "numbers": "01,02,03,04,05,06,07"}


def test_unopened_authoritative_draw_is_not_published_even_when_event_payload_claims_opened(tmp_path):
    from cache.memory import MemoryCacheStore
    from cache.public_snapshots import PublicDrawSnapshots
    from db import connect
    from outbox.repository import enqueue_event

    db_path = _setup(tmp_path)
    with connect(db_path) as conn:
        conn.execute("UPDATE lottery_draws SET is_opened = 0")
        enqueue_event(
            conn,
            event_key="draw-published:3:2026:188",
            event_type="draw.published",
            payload={"lottery_type_id": 3, "year": 2026, "term": 188, "is_opened": 1},
            now="2026-08-07T14:32:00+00:00",
        )
    snapshots = PublicDrawSnapshots(MemoryCacheStore())

    assert _publisher(db_path, snapshots).drain(limit=4) == {"published": 0, "retried": 1}
    assert snapshots.get_latest_draw(3) is None
    with connect(db_path) as conn:
        event = conn.execute("SELECT status FROM publication_outbox").fetchone()
    assert event["status"] == "pending"


def test_publisher_derives_draw_identity_from_event_key_not_untrusted_payload(tmp_path):
    from cache.memory import MemoryCacheStore
    from cache.public_snapshots import PublicDrawSnapshots, latest_draw_snapshot_keys
    from db import connect
    from outbox.repository import enqueue_event

    db_path = _setup(tmp_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, status,
                is_opened, next_term, created_at, updated_at
            ) VALUES (3, 2026, 189, '08,09,10,11,12,13,14', '2026-08-08 22:32:00',
                      1, 1, 190, ?, ?)
            """,
            ("2026-08-08T14:32:00+00:00", "2026-08-08T14:32:00+00:00"),
        )
        enqueue_event(
            conn,
            event_key="draw-published:3:2026:188",
            event_type="draw.published",
            payload={"lottery_type_id": 3, "year": 2026, "term": 189},
            now="2026-08-07T14:32:00+00:00",
        )
    cache = MemoryCacheStore()

    assert _publisher(db_path, PublicDrawSnapshots(cache)).drain(limit=4) == {"published": 1, "retried": 0}
    assert cache.get("public:draw-snapshot:v1:lottery:3:latest-draw:pointer") == (
        b"public:draw-snapshot:v1:lottery:3:latest-draw:version:2026-188-published"
    )


def test_duplicate_drain_does_not_republish_an_already_completed_event(tmp_path):
    from cache.memory import MemoryCacheStore
    from cache.public_snapshots import PublicDrawSnapshots
    from db import connect

    db_path = _setup(tmp_path)
    _enqueue_opened_event(db_path)
    publisher = _publisher(db_path, PublicDrawSnapshots(MemoryCacheStore()))

    assert publisher.drain(limit=4) == {"published": 1, "retried": 0}
    assert publisher.drain(limit=4) == {"published": 0, "retried": 0}
    with connect(db_path) as conn:
        event = conn.execute("SELECT status, attempts FROM publication_outbox").fetchone()
    assert dict(event) == {"status": "published", "attempts": 1}


def test_scheduler_drain_is_opt_in_and_only_delegates_to_injected_publisher(tmp_path):
    from crawler.scheduler import CrawlerScheduler

    class Publisher:
        def __init__(self):
            self.limits = []

        def drain(self, *, limit):
            self.limits.append(limit)
            return {"published": 1, "retried": 0}

    publisher = Publisher()
    scheduler = CrawlerScheduler(str(tmp_path / "scheduler.sqlite3"), publication_publisher=publisher)

    assert scheduler.drain_publications_once(limit=7) == {"published": 1, "retried": 0}
    assert publisher.limits == [7]
    assert CrawlerScheduler(str(tmp_path / "no-publisher.sqlite3")).drain_publications_once() == {
        "published": 0,
        "retried": 0,
    }


def test_scheduler_worker_builds_publisher_from_injected_cache_store_without_redis(tmp_path):
    from cache.memory import MemoryCacheStore
    from scheduler_worker import create_publication_publisher

    publisher = create_publication_publisher(
        str(tmp_path / "worker.sqlite3"),
        holder_id="lease-holder",
        cache_store=MemoryCacheStore(),
    )

    assert publisher is not None


def test_refresh_event_uses_its_own_immutable_snapshot_version(tmp_path):
    from cache.memory import MemoryCacheStore
    from cache.public_snapshots import PublicDrawSnapshots
    from db import connect
    from outbox.repository import enqueue_event

    db_path = _setup(tmp_path)
    with connect(db_path) as conn:
        enqueue_event(
            conn,
            event_key="draw-refresh:3:2026:188:1",
            event_type="draw.refresh",
            payload={"lottery_type_id": 3, "year": 2026, "term": 188},
            now="2026-08-07T14:32:00+00:00",
        )
    cache = MemoryCacheStore()
    assert _publisher(db_path, PublicDrawSnapshots(cache)).drain(limit=4) == {"published": 1, "retried": 0}
    assert cache.get("public:draw-snapshot:v1:lottery:3:latest-draw:pointer") == (
        b"public:draw-snapshot:v1:lottery:3:latest-draw:version:2026-188-refresh-1"
    )


def test_refresh_replaces_initial_published_snapshot_and_completes_both_events(tmp_path):
    from cache.memory import MemoryCacheStore
    from cache.public_snapshots import PublicDrawSnapshots
    from db import connect
    from outbox.draw_publication import enqueue_draw_publication

    db_path = _setup(tmp_path)
    _enqueue_opened_event(db_path)
    snapshots = PublicDrawSnapshots(MemoryCacheStore())
    time = [datetime(2026, 8, 7, 14, 32, 5, tzinfo=timezone.utc)]
    from outbox.publisher import DrawPublicationPublisher
    publisher = DrawPublicationPublisher(
        db_path, snapshots=snapshots, owner="scheduler-a", now=lambda: time[0],
    )

    assert publisher.drain(limit=4) == {"published": 1, "retried": 0}
    initial = snapshots.get_latest_draw(3)
    assert initial["result_balls"][0]["value"] == "01"

    with connect(db_path) as conn:
        previous = dict(conn.execute(
            "SELECT * FROM lottery_draws WHERE lottery_type_id = 3 AND year = 2026 AND term = 188"
        ).fetchone())
        conn.execute(
            "UPDATE lottery_draws SET numbers = ? WHERE lottery_type_id = 3 AND year = 2026 AND term = 188",
            ("08,09,10,11,12,13,14",),
        )
        current = dict(conn.execute(
            "SELECT * FROM lottery_draws WHERE lottery_type_id = 3 AND year = 2026 AND term = 188"
        ).fetchone())
        assert enqueue_draw_publication(
            conn, previous=previous, current=current, now="2026-08-07T14:33:00+00:00",
        ) == "draw.refresh"

    time[0] = datetime(2026, 8, 7, 14, 33, 5, tzinfo=timezone.utc)
    assert publisher.drain(limit=4) == {"published": 1, "retried": 0}
    refreshed = snapshots.get_latest_draw(3)
    assert refreshed["result_balls"][0]["value"] == "08"
    with connect(db_path) as conn:
        events = conn.execute(
            "SELECT event_key, status FROM publication_outbox ORDER BY id"
        ).fetchall()
    assert [dict(event) for event in events] == [
        {"event_key": "draw-published:3:2026:188", "status": "published"},
        {"event_key": "draw-refresh:3:2026:188:1", "status": "published"},
    ]


def test_retry_after_cache_publish_reuses_identical_event_snapshot_bytes(tmp_path, monkeypatch):
    from cache.memory import MemoryCacheStore
    from cache.public_snapshots import PublicDrawSnapshots
    from db import connect
    from outbox.publisher import DrawPublicationPublisher

    db_path = _setup(tmp_path)
    _enqueue_opened_event(db_path)
    cache = MemoryCacheStore()
    time = [datetime(2026, 8, 7, 14, 32, 5, tzinfo=timezone.utc)]
    publisher = DrawPublicationPublisher(
        db_path, snapshots=PublicDrawSnapshots(cache, clock=lambda: time[0].timestamp()),
        owner="scheduler-a", now=lambda: time[0],
    )
    original_complete = publisher._complete
    monkeypatch.setattr(publisher, "_complete", lambda event: (_ for _ in ()).throw(RuntimeError("database lost")))
    assert publisher.drain(limit=4) == {"published": 0, "retried": 1}
    key = "public:draw-snapshot:v1:lottery:3:latest-draw:version:2026-188-published"
    first = cache.get(key)
    assert first is not None

    time[0] = datetime(2026, 8, 7, 14, 32, 11, tzinfo=timezone.utc)
    monkeypatch.setattr(publisher, "_complete", original_complete)
    assert publisher.drain(limit=4) == {"published": 1, "retried": 0}
    assert cache.get(key) == first
    with connect(db_path) as conn:
        assert conn.execute("SELECT status, attempts FROM publication_outbox").fetchone()["status"] == "published"


def test_scheduler_drains_publications_before_durable_tasks(tmp_path, monkeypatch):
    from crawler.scheduler import CrawlerScheduler

    scheduler = CrawlerScheduler(str(tmp_path / "scheduler.sqlite3"))
    scheduler._running = True
    order = []
    monkeypatch.setattr(scheduler, "drain_publications_once", lambda: order.append("outbox"))
    monkeypatch.setattr(scheduler, "_run_due_tasks", lambda: order.append("tasks"))
    monkeypatch.setattr("crawler.scheduler._ensure_taiwan_future_autofill_task", lambda _path: None)
    monkeypatch.setattr("crawler.scheduler._task_poll_interval_seconds", lambda _path: 999)
    monkeypatch.setattr("crawler.scheduler.threading.Timer", lambda *args: type("Timer", (), {"daemon": False, "start": lambda self: None})())

    scheduler._schedule_task_loop()
    assert order == ["outbox", "tasks"]
