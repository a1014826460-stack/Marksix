"""Unified crawler service for lottery data.

Runs HK/Macau crawlers and imports Taiwan JSON data,
saving all results to the lottery_draws table.
"""

import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from HK_history_crawler import fetch_hongkong_history_data, transform_standard_list
from Macau_history_crawler import fetch_macau_history_data, transform_macau_api

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import connect as db_connect


def _get_lottery_meta(db_path: str | Path) -> dict[str, dict[str, Any]]:
    """
    从数据库 lottery_types 表中读取所有彩种的配置信息。

    返回一个字典，key 为彩种名称（如 "香港彩"、"澳门彩"），
    value 为包含 id, collect_url, draw_time 等字段的字典。

    这样采集地址（collect_url）和开奖时间（draw_time）就完全由数据库管理，
    不再硬编码在爬虫脚本中。
    """
    with db_connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, name, collect_url, draw_time FROM lottery_types"
        ).fetchall()
        return {
            row["name"]: {
                "id": row["id"],
                "collect_url": row["collect_url"] or "",
                "draw_time": row["draw_time"] or "",
            }
            for row in rows
        }


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
    """
    执行香港彩历史数据采集任务。

    工作流程：
    1. 从数据库 lottery_types 表读取香港彩的配置（采集地址 collect_url）
    2. 调用 fetch_hongkong_history_data() 拉取原始数据
    3. 转换数据格式后存入 lottery_draws 表

    注意：采集地址不再写死在脚本中，而是由管理员在后台"彩种管理"页面配置，
    存储在 PostgreSQL 数据库的 lottery_types.collect_url 字段中。
    """
    # ── 从数据库获取香港彩的配置信息 ──
    meta_map = _get_lottery_meta(db_path)
    hk_meta = meta_map.get("香港彩") or meta_map.get("六合彩")
    if hk_meta is None:
        raise ValueError("香港彩 lottery type not found - please ensure 香港彩 exists")

    # ── 使用数据库中的采集地址发起请求，
    #     如果数据库未配置采集地址则使用爬虫函数默认值（兼容旧数据） ──
    collect_url = hk_meta["collect_url"]
    if collect_url:
        raw, status_code = fetch_hongkong_history_data(collect_url=collect_url)
    else:
        raw, status_code = fetch_hongkong_history_data()

    if status_code != 200:
        raise RuntimeError(f"HK crawler returned status {status_code}")

    records = transform_standard_list(raw)
    now = datetime.now(timezone.utc).isoformat()
    saved = 0
    with db_connect(db_path) as conn:
        for item in records:
            try:
                open_time = item["open_time"]
                year = int(open_time[:4])
                term_num = int(item["issue"])
                _upsert_draw(conn, hk_meta["id"], year, term_num,
                             item["result"], open_time, 1, now)
                saved += 1
            except (ValueError, KeyError) as e:
                print(f"  SKIP: {item.get('issue', '?')} - {e}")
    return {"source": "hk", "fetched": len(records), "saved": saved}


def run_macau_crawler(db_path: str | Path) -> dict[str, Any]:
    """
    执行澳门彩历史数据采集任务。

    工作流程：
    1. 从数据库 lottery_types 表读取澳门彩的配置（采集地址 collect_url）
    2. 调用 fetch_macau_history_data() 拉取原始数据
    3. 转换数据格式后存入 lottery_draws 表

    注意：采集地址不再写死在脚本中，而是由管理员在后台"彩种管理"页面配置，
    存储在 PostgreSQL 数据库的 lottery_types.collect_url 字段中。
    """
    # ── 从数据库获取澳门彩的配置信息 ──
    meta_map = _get_lottery_meta(db_path)
    macau_meta = meta_map.get("澳门彩")
    if macau_meta is None:
        raise ValueError("澳门彩 lottery type not found")

    # ── 使用数据库中的采集地址发起请求 ──
    collect_url = macau_meta["collect_url"]
    if collect_url:
        raw, status_code = fetch_macau_history_data(collect_url=collect_url)
    else:
        raw, status_code = fetch_macau_history_data()

    if status_code != 200:
        raise RuntimeError(f"Macau crawler returned status {status_code}")

    records = transform_macau_api(raw)
    now = datetime.now(timezone.utc).isoformat()
    saved = 0
    with db_connect(db_path) as conn:
        for item in records:
            try:
                expect = item["issue"]
                year = int(expect[:4])
                term_num = int(expect[4:])
                _upsert_draw(conn, macau_meta["id"], year, term_num,
                             item["result"], item["open_time"], 1, now)
                saved += 1
            except (ValueError, KeyError) as e:
                print(f"  SKIP: {item.get('issue', '?')} - {e}")
    return {"source": "macau", "fetched": len(records), "saved": saved}


def import_taiwan_json(db_path: str | Path, json_path: str | Path) -> dict[str, Any]:
    """
    从 JSON 文件导入台湾彩历史开奖数据。

    台湾彩数据来源于本地 JSON 文件，不需要线上采集地址（collect_url），
    因此该函数不涉及爬虫调用，直接从文件读取并存入数据库。
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("data", [])
    total_in_file = data.get("total", len(records))

    # ── 台湾彩不需要采集地址，直接从数据库获取彩种ID即可 ──
    meta_map = _get_lottery_meta(db_path)
    taiwan_meta = meta_map.get("台湾彩")
    if taiwan_meta is None:
        raise ValueError("台湾彩 lottery type not found")

    now = datetime.now(timezone.utc).isoformat()
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
                _upsert_draw(conn, taiwan_meta["id"], year, term_num, numbers,
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
