"""Unified crawler service for lottery data.

Runs HK/Macau crawlers and imports Taiwan JSON data,
saving all results to the lottery_draws table.
"""

import json
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from HK_history_crawler import fetch_hongkong_history_data, transform_standard_list
from Macau_history_crawler import fetch_macau_history_data, transform_macau_api

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import connect as db_connect


def _get_lottery_ids(db_path: str | Path) -> dict[str, int]:
    with db_connect(db_path) as conn:
        rows = conn.execute("SELECT id, name FROM lottery_types").fetchall()
        return {row["name"]: row["id"] for row in rows}


def _upsert_draw(
    conn: Any,
    lottery_type_id: int,
    year: int,
    term: int,
    numbers: str,
    draw_time: str,
    is_opened: int,
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO lottery_draws
            (lottery_type_id, year, term, numbers, draw_time,
             status, is_opened, next_term, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
        ON CONFLICT(lottery_type_id, year, term) DO UPDATE SET
            numbers = excluded.numbers,
            draw_time = excluded.draw_time,
            is_opened = excluded.is_opened,
            updated_at = excluded.updated_at
        """,
        (lottery_type_id, year, term, numbers, draw_time,
         is_opened, term + 1, now, now),
    )


def run_hk_crawler(db_path: str | Path) -> dict[str, Any]:
    """Fetch Hong Kong lottery data and save to lottery_draws table."""
    raw, status_code = fetch_hongkong_history_data()
    if status_code != 200:
        raise RuntimeError(f"HK crawler returned status {status_code}")
    records = transform_standard_list(raw)
    ids = _get_lottery_ids(db_path)
    hk_id = ids.get("香港彩", ids.get("六合彩"))
    if hk_id is None:
        raise ValueError("香港彩 lottery type not found - please ensure 香港彩 exists")
    now = datetime.now(UTC).isoformat()
    saved = 0
    with db_connect(db_path) as conn:
        for item in records:
            try:
                open_time = item["open_time"]
                year = int(open_time[:4])
                term_num = int(item["issue"])
                _upsert_draw(conn, hk_id, year, term_num, item["result"],
                             open_time, 1, now)
                saved += 1
            except (ValueError, KeyError) as e:
                print(f"  SKIP: {item.get('issue', '?')} - {e}")
    return {"source": "hk", "fetched": len(records), "saved": saved}


def run_macau_crawler(db_path: str | Path) -> dict[str, Any]:
    """Fetch Macau lottery data and save to lottery_draws table."""
    raw, status_code = fetch_macau_history_data()
    if status_code != 200:
        raise RuntimeError(f"Macau crawler returned status {status_code}")
    records = transform_macau_api(raw)
    ids = _get_lottery_ids(db_path)
    macau_id = ids.get("澳门彩")
    if macau_id is None:
        raise ValueError("澳门彩 lottery type not found")
    now = datetime.now(UTC).isoformat()
    saved = 0
    with db_connect(db_path) as conn:
        for item in records:
            try:
                expect = item["issue"]
                year = int(expect[:4])
                term_num = int(expect[4:])
                _upsert_draw(conn, macau_id, year, term_num, item["result"],
                             item["open_time"], 1, now)
                saved += 1
            except (ValueError, KeyError) as e:
                print(f"  SKIP: {item.get('issue', '?')} - {e}")
    return {"source": "macau", "fetched": len(records), "saved": saved}


def import_taiwan_json(db_path: str | Path, json_path: str | Path) -> dict[str, Any]:
    """Import Taiwan lottery data from JSON file to lottery_draws table."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("data", [])
    total_in_file = data.get("total", len(records))
    ids = _get_lottery_ids(db_path)
    taiwan_id = ids.get("台湾彩")
    if taiwan_id is None:
        raise ValueError("台湾彩 lottery type not found")
    now = datetime.now(UTC).isoformat()
    saved = 0
    with db_connect(db_path) as conn:
        for item in records:
            try:
                year = int(item["year"])
                term_num = int(item["term"])
                numbers = str(item.get("code") or item.get("pre_code", "")).strip()
                draw_time = item.get("open_time", "")
                is_opened = 1 if item.get("is_kj") == 1 else 0
                if not numbers:
                    continue
                _upsert_draw(conn, taiwan_id, year, term_num, numbers,
                             draw_time, is_opened, now)
                saved += 1
            except (ValueError, KeyError) as e:
                print(f"  SKIP: {item.get('term', '?')} - {e}")
    return {"source": "taiwan", "total_in_file": total_in_file,
            "parsed": len(records), "saved": saved}


class CrawlerScheduler:
    """Runs HK and Macau crawlers on a background thread periodically."""

    def __init__(self, db_path: str | Path, interval_seconds: int = 3600):
        self.db_path = db_path
        self.interval = interval_seconds
        self._timer: threading.Timer | None = None
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        print(f"[CrawlerScheduler] Started, interval={self.interval}s")
        # Run once immediately on startup
        self._run()
        self._schedule_next()

    def stop(self) -> None:
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule_next(self) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(self.interval, self._run)
        self._timer.daemon = True
        self._timer.start()

    def _run_once(self) -> None:
        with self._lock:
            for name, fn in [("HK", run_hk_crawler), ("Macau", run_macau_crawler)]:
                try:
                    result = fn(self.db_path)
                    print(f"  [{name}] {result}")
                except Exception as e:
                    print(f"  [{name}] error: {e}")

    def _run(self) -> None:
        if not self._running:
            return
        print("[CrawlerScheduler] Running scheduled crawl...")
        self._run_once()
        self._schedule_next()
