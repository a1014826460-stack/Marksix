from __future__ import annotations

import json

import pytest


def _connection(tmp_path):
    from database.bootstrap import ensure_admin_tables
    from db import connect

    db_path = str(tmp_path / "outbox.sqlite3")
    ensure_admin_tables(db_path)
    return connect(db_path)


def test_sqlite_bootstrap_creates_draw_publication_outbox(tmp_path):
    with _connection(tmp_path) as conn:
        assert conn.table_exists("publication_outbox")
        columns = set(conn.table_columns("publication_outbox"))

    assert columns >= {
        "id", "event_key", "event_type", "payload_json", "status",
        "available_at", "lease_owner", "lease_until", "attempts",
        "last_error", "published_at", "created_at", "updated_at",
    }


def test_enqueue_is_idempotent_by_business_event_key(tmp_path):
    from outbox.repository import enqueue_event

    with _connection(tmp_path) as conn:
        inserted = enqueue_event(
            conn,
            event_key="draw-published:3:2026:188",
            event_type="draw.published",
            payload={"lottery_type_id": 3, "year": 2026, "term": 188},
            now="2026-08-07T14:32:00+00:00",
        )
        duplicate = enqueue_event(
            conn,
            event_key="draw-published:3:2026:188",
            event_type="draw.published",
            payload={"term": 188},
            now="2026-08-07T14:33:00+00:00",
        )
        rows = conn.execute("SELECT event_key, event_type, payload_json, status, attempts FROM publication_outbox").fetchall()

    assert inserted is True
    assert duplicate is False
    assert len(rows) == 1
    assert dict(rows[0]) == {
        "event_key": "draw-published:3:2026:188",
        "event_type": "draw.published",
        "payload_json": json.dumps({"lottery_type_id": 3, "year": 2026, "term": 188}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        "status": "pending",
        "attempts": 0,
    }


def test_enqueue_participates_in_callers_transaction_and_rolls_back(tmp_path):
    from outbox.repository import enqueue_event
    from db import connect

    db_path = str(tmp_path / "outbox-rollback.sqlite3")
    from database.bootstrap import ensure_admin_tables
    ensure_admin_tables(db_path)
    with pytest.raises(RuntimeError):
        with connect(db_path) as conn:
            enqueue_event(conn, event_key="draw-published:3:2026:189", event_type="draw.published", payload={})
            raise RuntimeError("abort the authoritative draw transaction")
    with connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) AS count FROM publication_outbox").fetchone()["count"]

    assert count == 0


def test_claim_retries_expired_lease_and_increments_attempts(tmp_path):
    from outbox.repository import claim_due_events, enqueue_event

    with _connection(tmp_path) as conn:
        enqueue_event(conn, event_key="draw-published:3:2026:190", event_type="draw.published", payload={"term": 190}, now="2026-08-07T14:32:00+00:00")
        first = claim_due_events(
            conn, owner="worker-a", now="2026-08-07T14:32:01+00:00",
            lease_until="2026-08-07T14:32:11+00:00", limit=10,
        )
        unavailable_to_other = claim_due_events(
            conn, owner="worker-b", now="2026-08-07T14:32:02+00:00",
            lease_until="2026-08-07T14:32:12+00:00", limit=10,
        )
        recovered = claim_due_events(
            conn, owner="worker-b", now="2026-08-07T14:32:12+00:00",
            lease_until="2026-08-07T14:32:22+00:00", limit=10,
        )

    assert [event["attempts"] for event in first] == [1]
    assert unavailable_to_other == []
    assert [(event["lease_owner"], event["attempts"], event["status"]) for event in recovered] == [("worker-b", 2, "processing")]


def test_retry_releases_claim_at_requested_time_and_completion_is_owner_guarded(tmp_path):
    from outbox.repository import claim_due_events, enqueue_event, mark_published, mark_retry

    with _connection(tmp_path) as conn:
        enqueue_event(
            conn,
            event_key="draw-published:3:2026:191",
            event_type="draw.published",
            payload={},
            now="2026-08-07T14:32:00+00:00",
        )
        event = claim_due_events(conn, owner="worker-a", now="2026-08-07T14:32:01+00:00", lease_until="2026-08-07T14:33:01+00:00", limit=1)[0]
        assert mark_retry(conn, event_id=event["id"], owner="worker-a", available_at="2026-08-07T14:32:31+00:00", error="redis unavailable", now="2026-08-07T14:32:02+00:00") is True
        assert claim_due_events(conn, owner="worker-b", now="2026-08-07T14:32:30+00:00", lease_until="2026-08-07T14:33:30+00:00", limit=1) == []
        retry = claim_due_events(conn, owner="worker-b", now="2026-08-07T14:32:31+00:00", lease_until="2026-08-07T14:33:31+00:00", limit=1)[0]
        assert mark_published(conn, event_id=retry["id"], owner="worker-a", now="2026-08-07T14:32:32+00:00") is False
        assert mark_published(conn, event_id=retry["id"], owner="worker-b", now="2026-08-07T14:32:32+00:00") is True
        row = conn.execute("SELECT status, lease_owner, lease_until, published_at, last_error, attempts FROM publication_outbox WHERE id = ?", (retry["id"],)).fetchone()

    assert dict(row) == {
        "status": "published", "lease_owner": None, "lease_until": None,
        "published_at": "2026-08-07T14:32:32+00:00", "last_error": None, "attempts": 2,
    }


def test_expired_lease_owner_cannot_retry_or_complete_an_event(tmp_path):
    from outbox.repository import claim_due_events, enqueue_event, mark_published, mark_retry

    with _connection(tmp_path) as conn:
        enqueue_event(
            conn,
            event_key="draw-published:3:2026:192",
            event_type="draw.published",
            payload={},
            now="2026-08-07T14:32:00+00:00",
        )
        event = claim_due_events(
            conn, owner="worker-a", now="2026-08-07T14:32:01+00:00",
            lease_until="2026-08-07T14:32:10+00:00", limit=1,
        )[0]

        assert mark_retry(
            conn, event_id=event["id"], owner="worker-a",
            available_at="2026-08-07T14:33:00+00:00", error="too late",
            now="2026-08-07T14:32:10+00:00",
        ) is False
        assert mark_published(
            conn, event_id=event["id"], owner="worker-a",
            now="2026-08-07T14:32:10+00:00",
        ) is False
        row = conn.execute(
            "SELECT status, lease_owner, lease_until FROM publication_outbox WHERE id = ?",
            (event["id"],),
        ).fetchone()

    assert dict(row) == {
        "status": "processing", "lease_owner": "worker-a",
        "lease_until": "2026-08-07T14:32:10+00:00",
    }


def test_postgres_outbox_migration_is_registered_at_current_version():
    from database import versioned_migrations

    migration = versioned_migrations.MIGRATIONS[-1]

    assert migration.name == "create_publication_outbox"
    assert migration.version == versioned_migrations.CURRENT_SCHEMA_VERSION
    assert migration.version == max(item.version for item in versioned_migrations.MIGRATIONS)
