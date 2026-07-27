from __future__ import annotations

import pytest

from db import connect
from domains.traffic.service import (
    TRAFFIC_EVENT_TYPES,
    get_traffic_overview,
    get_traffic_sites,
    get_traffic_timeseries,
    record_traffic_event,
)
from tables import ensure_admin_tables


def _insert_site(db_path, *, site_id: int = 7, web_id: int = 7, domain: str = "www.twjinniu.com") -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 3, 1, 'twjinniu', '', '', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                web_id = excluded.web_id,
                name = excluded.name,
                domain = excluded.domain,
                lottery_type_id = excluded.lottery_type_id,
                enabled = excluded.enabled,
                blueprint_name = excluded.blueprint_name,
                updated_at = excluded.updated_at
            """,
            (
                site_id,
                web_id,
                f"site-{site_id}",
                domain,
                "2026-06-28T00:00:00+00:00",
                "2026-06-28T00:00:00+00:00",
            ),
        )


def test_record_traffic_event_hashes_ip_and_preserves_site_context(tmp_path):
    db_path = tmp_path / "traffic.sqlite3"
    ensure_admin_tables(db_path)
    _insert_site(db_path)

    event = record_traffic_event(
        db_path,
        {
            "site_key": "twjinniu",
            "site_id": 7,
            "web_id": 7,
            "lottery_type": 3,
            "event_type": "site_page_view",
            "path": "/twjinniu",
            "route": "/twjinniu",
            "referrer": "https://example.test/from",
            "visitor_id": "visitor-1",
            "occurred_at": "2026-06-28T10:00:00+00:00",
        },
        ip_address="203.0.113.9",
        user_agent="UnitTest/1.0",
    )

    assert event["ok"] is True
    assert event["event_type"] == "site_page_view"

    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM public_site_traffic_events").fetchone()

    assert row["site_key"] == "twjinniu"
    assert row["site_id"] == 7
    assert row["web_id"] == 7
    assert row["lottery_type"] == 3
    assert row["ip_hash"]
    assert row["ip_hash"] != "203.0.113.9"
    assert "203.0.113.9" not in dict(row).values()
    assert row["user_agent"] == "UnitTest/1.0"


def test_record_traffic_event_resolves_managed_site_context_when_ids_missing(tmp_path):
    db_path = tmp_path / "traffic_resolve_site.sqlite3"
    ensure_admin_tables(db_path)
    _insert_site(db_path, site_id=7, web_id=77, domain="www.twjinniu.com")

    event = record_traffic_event(
        db_path,
        {
            "site_key": "twjinniu",
            "event_type": "site_page_view",
            "path": "/twjinniu",
            "visitor_id": "visitor-resolve",
            "occurred_at": "2026-06-28T10:00:00+00:00",
        },
        ip_address="203.0.113.9",
    )

    assert event["site_id"] == 7
    assert event["web_id"] == 77
    assert event["lottery_type"] == 3


def test_record_traffic_event_rejects_unknown_event_type(tmp_path):
    db_path = tmp_path / "traffic_invalid.sqlite3"
    ensure_admin_tables(db_path)
    _insert_site(db_path)

    with pytest.raises(ValueError, match="event_type"):
        record_traffic_event(
            db_path,
            {
                "site_key": "twjinniu",
                "site_id": 7,
                "event_type": "not_real",
                "path": "/twjinniu",
            },
            ip_address="203.0.113.10",
        )

    assert "api_compat_hit" in TRAFFIC_EVENT_TYPES


def test_traffic_metrics_aggregate_pv_uv_and_api_compat_hits(tmp_path):
    db_path = tmp_path / "traffic_metrics.sqlite3"
    ensure_admin_tables(db_path)
    _insert_site(db_path, site_id=7, web_id=7, domain="www.twjinniu.com")
    _insert_site(db_path, site_id=8, web_id=8, domain="www.twcf888.com")

    events = [
        ("twjinniu", 7, "site_page_view", "/twjinniu", "visitor-a", "2026-06-28T10:00:00+00:00"),
        ("twjinniu", 7, "site_page_view", "/twjinniu", "visitor-a", "2026-06-28T10:01:00+00:00"),
        ("twjinniu", 7, "article_view", "/twjinniu/amgst/7701", "visitor-b", "2026-06-28T10:02:00+00:00"),
        ("twjinniu", 7, "api_compat_hit", "/api/twjinniu/site-page", "api-1", "2026-06-28T10:03:00+00:00"),
        ("twcf888", 8, "vendor_page_view", "/twcf888", "visitor-c", "2026-06-28T11:00:00+00:00"),
    ]
    for site_key, site_id, event_type, path, visitor_id, occurred_at in events:
        record_traffic_event(
            db_path,
            {
                "site_key": site_key,
                "site_id": site_id,
                "web_id": site_id,
                "lottery_type": 3,
                "event_type": event_type,
                "path": path,
                "route": path,
                "article_id": "7701" if event_type == "article_view" else "",
                "visitor_id": visitor_id,
                "occurred_at": occurred_at,
            },
            ip_address=f"203.0.113.{site_id}",
        )

    overview = get_traffic_overview(
        db_path,
        date_from="2026-06-28T00:00:00+00:00",
        date_to="2026-06-29T00:00:00+00:00",
    )
    sites = get_traffic_sites(
        db_path,
        date_from="2026-06-28T00:00:00+00:00",
        date_to="2026-06-29T00:00:00+00:00",
    )
    timeseries = get_traffic_timeseries(
        db_path,
        date_from="2026-06-28T00:00:00+00:00",
        date_to="2026-06-29T00:00:00+00:00",
    )

    assert overview["summary"]["pv"] == 4
    assert overview["summary"]["uv"] == 4
    assert overview["summary"]["api_compat_hits"] == 1
    assert overview["article_rankings"][0]["article_id"] == "7701"
    assert overview["compatibility_routes"][0]["path"] == "/api/twjinniu/site-page"

    twjinniu = next(item for item in sites["sites"] if item["site_key"] == "twjinniu")
    assert twjinniu["pv"] == 3
    assert twjinniu["uv"] == 3
    assert twjinniu["api_compat_hits"] == 1
    assert twjinniu["web_id"] == 7
    assert twjinniu["name"] == "site-7"
    assert twjinniu["domain"] == "www.twjinniu.com"

    assert timeseries["items"] == [
        {
            "date": "2026-06-28",
            "site_key": "twcf888",
            "pv": 1,
            "uv": 1,
            "api_compat_hits": 0,
        },
        {
            "date": "2026-06-28",
            "site_key": "twjinniu",
            "pv": 3,
            "uv": 3,
            "api_compat_hits": 1,
        },
    ]


def test_record_traffic_event_deduplicates_rapid_page_retry_by_visitor(tmp_path):
    db_path = tmp_path / "traffic_dedupe.sqlite3"
    ensure_admin_tables(db_path)
    _insert_site(db_path)

    base_payload = {
        "site_key": "twjinniu",
        "site_id": 7,
        "web_id": 7,
        "lottery_type": 3,
        "event_type": "site_page_view",
        "path": "/twjinniu",
        "route": "/twjinniu",
        "visitor_id": "visitor-dedupe",
    }
    first = record_traffic_event(
        db_path,
        {**base_payload, "occurred_at": "2026-06-28T10:00:00+00:00"},
        ip_address="203.0.113.7",
    )
    second = record_traffic_event(
        db_path,
        {**base_payload, "occurred_at": "2026-06-28T10:03:00+00:00"},
        ip_address="203.0.113.7",
    )
    third = record_traffic_event(
        db_path,
        {**base_payload, "occurred_at": "2026-06-28T10:06:00+00:00"},
        ip_address="203.0.113.7",
    )

    assert second["id"] == first["id"]
    assert third["id"] != first["id"]

    overview = get_traffic_overview(db_path)
    assert overview["summary"]["pv"] == 2
