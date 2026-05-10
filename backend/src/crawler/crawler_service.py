"""Unified crawler service for lottery data.

Runs HK/Macau crawlers and imports Taiwan JSON data,
saving all results to the lottery_draws table.
"""

import json
import logging
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from HK_history_crawler import fetch_hongkong_history_data, transform_standard_list
from Macau_history_crawler import fetch_macau_history_data

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import connect as db_connect

_crawler_logger = logging.getLogger("crawler.scheduler")


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
    next_time: str = "",
) -> None:
    # 只有 next_time 非空时才写入/更新，防止历史数据覆盖有效的下次开奖时间
    if next_time:
        conn.execute(
            """
            INSERT INTO lottery_draws
                (lottery_type_id, year, term, numbers, draw_time,
                 status, is_opened, next_term, next_time, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
            ON CONFLICT(lottery_type_id, year, term) DO UPDATE SET
                numbers = excluded.numbers,
                draw_time = excluded.draw_time,
                is_opened = excluded.is_opened,
                next_time = excluded.next_time,
                updated_at = excluded.updated_at
            """,
            (lottery_type_id, year, term, numbers, draw_time,
             is_opened, term + 1, next_time, now, now),
        )
    else:
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
    # 同步更新 lottery_types.next_time，保持彩种管理页面数据一致
    if next_time:
        conn.execute(
            "UPDATE lottery_types SET next_time = ?, updated_at = ? WHERE id = ?",
            (next_time, now, lottery_type_id),
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
    if not records:
        return {"source": "hk", "fetched": 0, "saved": 0, "message": "API 返回空数据，将在下一周期自动重试"}
    now = datetime.now(timezone.utc).isoformat()
    saved = 0
    with db_connect(db_path) as conn:
        for item in records:
            try:
                open_time = item["open_time"]
                year = int(open_time[:4])
                term_num = int(item["issue"])
                _upsert_draw(conn, hk_meta["id"], year, term_num,
                             item["result"], open_time, 1, now,
                             next_time=str(item.get("next_time") or ""))
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

    records = transform_standard_list(raw)
    if not records:
        return {"source": "macau", "fetched": 0, "saved": 0, "message": "API 返回空数据或格式异常，将在下一周期自动重试"}
    now = datetime.now(timezone.utc).isoformat()
    saved = 0
    with db_connect(db_path) as conn:
        for item in records:
            try:
                expect = item["issue"]
                year = int(expect[:4])
                term_num = int(expect[4:])
                _upsert_draw(conn, macau_meta["id"], year, term_num,
                             item["result"], item["open_time"], 1, now,
                             next_time=str(item.get("next_time") or ""))
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
                             draw_time, is_opened, now,
                             next_time=str(item.get("next_time") or ""))
                saved += 1
            except (ValueError, KeyError) as e:
                print(f"  SKIP: {item.get('term', '?')} - {e}")
    return {"source": "taiwan", "total_in_file": total_in_file,
            "parsed": len(records), "saved": saved}


def crawl_and_generate_for_type(db_path: str | Path, lottery_type_id: int) -> dict[str, Any]:
    """爬取指定彩种的开奖数据，然后自动生成所有启用站点的预测资料。

    供 HTTP API（app.py 的 _crawl_and_generate）和定时调度器
    （CrawlerScheduler._run_once）共同使用，避免逻辑重复。

    :param db_path: 数据库连接字符串
    :param lottery_type_id: 彩种 ID（1=香港, 2=澳门, 3=台湾）
    :return: 包含 lottery_name、crawl、generation 三部分的字典
    """
    from admin.prediction import bulk_generate_site_prediction_data as _bulk_gen
    from db import connect as _connect

    # ── 1. 确定彩种名称 ──
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT id, name FROM lottery_types WHERE id = ?", (lottery_type_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"lottery_type_id={lottery_type_id} 不存在")
        lottery_name = str(row["name"])

    # ── 2. 执行爬虫 ──
    crawl_result: dict[str, Any] = {"status": "skipped", "message": ""}
    if lottery_name in ("香港彩", "六合彩"):
        crawl_result = run_hk_crawler(db_path)
    elif lottery_name == "澳门彩":
        crawl_result = run_macau_crawler(db_path)
    else:
        crawl_result["message"] = f"台湾彩无在线爬虫，请使用 /api/admin/crawler/import-taiwan 导入 JSON"

    # ── 3. 自动生成预测资料 ──
    generation_results: list[dict[str, Any]] = []
    with _connect(db_path) as conn:
        sites = conn.execute(
            "SELECT id, name, lottery_type_id FROM managed_sites WHERE enabled = 1"
        ).fetchall()

        for site in sites:
            site_id = int(site["id"])
            modules = conn.execute(
                """
                SELECT id, mechanism_key, mode_id
                FROM site_prediction_modules
                WHERE site_id = ? AND status = 1
                ORDER BY sort_order, id
                """,
                (site_id,),
            ).fetchall()

            if not modules:
                continue

            latest_draw = conn.execute(
                """
                SELECT year, term FROM lottery_draws
                WHERE lottery_type_id = ? AND is_opened = 1
                ORDER BY year DESC, term DESC LIMIT 1
                """,
                (lottery_type_id,),
            ).fetchone()

            if not latest_draw:
                continue

            latest_term = int(latest_draw["term"])
            latest_year = int(latest_draw["year"])

            try:
                gen_result = _bulk_gen(
                    db_path,
                    site_id,
                    {
                        "lottery_type": lottery_type_id,
                        "start_issue": f"{latest_year}{max(1, latest_term):03d}",
                        "end_issue": f"{latest_year}{latest_term:03d}",
                        "mechanism_keys": [str(m["mechanism_key"]) for m in modules],
                    },
                )
                generation_results.append({
                    "site_id": site_id,
                    "site_name": str(site["name"]),
                    "inserted": gen_result.get("inserted", 0),
                    "updated": gen_result.get("updated", 0),
                    "errors": gen_result.get("errors", 0),
                })
            except Exception as exc:
                generation_results.append({
                    "site_id": site_id,
                    "site_name": str(site["name"]),
                    "error": str(exc),
                })

    return {
        "lottery_name": lottery_name,
        "crawl": crawl_result,
        "generation": generation_results,
    }


class CrawlerScheduler:
    """后台定时任务调度器。

    职责：
    - 每 60 秒检查到达开奖时间的记录并自动标记 is_opened=1
    - 每日北京时间 22:30:00 精准执行台湾彩开奖 + next_time 更新
    - 管理 run_crawl_only 触发的 6 小时延迟自动预测定时器

    注意：历史开奖数据爬取不再由调度器自动执行，
    应由管理员通过后台"更新开奖"按钮手动触发。
    """

    # 台湾彩开奖重试间隔（秒）：第1次重试60s，第2次300s，第3次900s
    _TAIWAN_RETRY_DELAYS = [60, 300, 900]
    _TAIWAN_MAX_RETRIES = 3

    def __init__(self, db_path: str | Path):
        self.db_path = db_path
        self._running = False
        self._taiwan_timer: threading.Timer | None = None
        self._auto_open_timer: threading.Timer | None = None
        self._auto_crawl_timer: threading.Timer | None = None
        self._taiwan_retry_count = 0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        _crawler_logger.info("Scheduler started (auto-open every 60s, auto-crawl every 10min)")
        self._schedule_auto_open()
        self._schedule_taiwan_precise_open()
        self._schedule_auto_crawl()

    def stop(self) -> None:
        _crawler_logger.info("Scheduler stopping")
        self._running = False
        if hasattr(self, "_auto_open_timer") and self._auto_open_timer:
            self._auto_open_timer.cancel()
            self._auto_open_timer = None
        if self._taiwan_timer:
            self._taiwan_timer.cancel()
            self._taiwan_timer = None
        if hasattr(self, "_auto_crawl_timer") and self._auto_crawl_timer:
            self._auto_crawl_timer.cancel()
            self._auto_crawl_timer = None

    def _auto_open_draws(self) -> None:
        """检查所有未开奖记录，若开奖时间已过则自动标记 is_opened=1。
        同时为 type=3 记录补充 next_time（作为精准调度器的兜底）。

        注意：draw_time 字段存储的是北京时间字符串，比较时也必须使用北京时间。"""
        try:
            now_utc_dt = datetime.now(timezone.utc)
            now_utc = now_utc_dt.strftime("%Y-%m-%d %H:%M:%S")
            now_beijing = (now_utc_dt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
            with db_connect(self.db_path) as conn:
                # 先查出即将被打开的记录，再执行 UPDATE，避免依赖脆弱的 updated_at 精确匹配
                pending = conn.execute(
                    """SELECT id, year, term, draw_time, lottery_type_id FROM lottery_draws
                       WHERE is_opened = 0 AND draw_time IS NOT NULL AND draw_time != ''
                       AND draw_time <= ?""",
                    (now_beijing,),
                ).fetchall()

                if pending:
                    ids = [row["id"] for row in pending]
                    placeholders = ",".join("?" for _ in ids)
                    conn.execute(
                        f"UPDATE lottery_draws SET is_opened = 1, updated_at = ? "
                        f"WHERE id IN ({placeholders})",
                        [now_utc] + ids,
                    )
                    print(f"[AutoOpen] Set is_opened=1 for {len(pending)} draw(s)")

                    # 为刚打开的 type=3 记录更新 next_time
                    taiwan_opened = [r for r in pending if r["lottery_type_id"] == 3]
                    for row in taiwan_opened:
                        self._calc_and_update_next_time(conn, row, now_utc)
                    if taiwan_opened:
                        conn.commit()
        except Exception as e:
            print(f"[AutoOpen] Error: {e}")

    def _schedule_auto_open(self) -> None:
        """每 60 秒检查一次是否有到达开奖时间的记录。"""
        if not self._running:
            return
        self._auto_open_draws()
        self._auto_open_timer = threading.Timer(60, self._schedule_auto_open)
        self._auto_open_timer.daemon = True
        self._auto_open_timer.start()

    def _schedule_auto_crawl(self) -> None:
        """每 10 分钟自动尝试爬取香港/澳门当前期开奖数据。"""
        if not self._running:
            return
        self._auto_crawl()
        self._auto_crawl_timer = threading.Timer(600, self._schedule_auto_crawl)
        self._auto_crawl_timer.daemon = True
        self._auto_crawl_timer.start()

    def _auto_crawl(self) -> None:
        """自动爬取：检查是否有到达开奖时间但未获取数据的记录，尝试爬取。

        设计思路：
        - 遍历所有启用的 HK/Macau 彩种
        - 如果该彩种最近 30 分钟内没有已开奖记录（is_opened=1），则触发爬取
        - 爬取成功后自动标记 is_opened 并安排 6h 延迟预测任务
        """
        try:
            with db_connect(self.db_path) as conn:
                lt_rows = conn.execute(
                    "SELECT id, name FROM lottery_types WHERE status = 1 AND id IN (1, 2)"
                ).fetchall()
                for lt_row in lt_rows:
                    lt_id = int(lt_row["id"])
                    lt_name = str(lt_row["name"])
                    # 检查最近是否有新开奖记录（30 分钟内）
                    recent = conn.execute(
                        """SELECT id FROM lottery_draws
                           WHERE lottery_type_id = ? AND is_opened = 1
                           AND updated_at::timestamptz > (NOW() - INTERVAL '30 minutes')
                           LIMIT 1""",
                        (lt_id,),
                    ).fetchone()
                    if recent:
                        continue  # 最近已有开奖，跳过
                    # 触发爬取
                    try:
                        result = run_crawl_only(self.db_path, lt_id)
                        saved = result.get("saved", 0)
                        if saved > 0:
                            _crawler_logger.info(
                                "Auto-crawl %s: saved %d draws", lt_name, saved
                            )
                    except Exception as exc:
                        _crawler_logger.warning(
                            "Auto-crawl %s failed: %s", lt_name, exc
                        )
        except Exception as e:
            _crawler_logger.error("Auto-crawl scheduler error: %s", e)

    # ── 台湾彩每日 22:30 精准开奖调度 ─────────────────────────────

    @staticmethod
    def _seconds_until_beijing(hour: int, minute: int) -> float:
        """计算距离下一个北京时间指定时刻的秒数。"""
        now_utc = datetime.now(timezone.utc)
        beijing_now = now_utc + timedelta(hours=8)
        target_beijing = beijing_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if beijing_now >= target_beijing:
            target_beijing += timedelta(days=1)
        target_utc = target_beijing - timedelta(hours=8)
        return max(0, (target_utc - now_utc).total_seconds())

    def _schedule_taiwan_precise_open(self) -> None:
        """调度下一次北京时间 22:30 的台湾彩精准开奖任务。"""
        if not self._running:
            return
        delay = self._seconds_until_beijing(22, 30)
        self._taiwan_timer = threading.Timer(delay, self._taiwan_precise_open_execute)
        self._taiwan_timer.daemon = True
        self._taiwan_timer.start()
        target_beijing = datetime.now(timezone.utc) + timedelta(hours=8) + timedelta(seconds=delay)
        print(f"[TaiwanScheduler] Next Taiwan open at {target_beijing.strftime('%Y-%m-%d %H:%M:%S')} Beijing (in {delay:.0f}s)")

    def _taiwan_precise_open_execute(self) -> None:
        """执行台湾彩开奖任务，含重试策略。
        成功则：调度次日 → 异步触发预测数据生成（回填结果 + 生成下一期预测）。
        失败则：按间隔重试。"""
        try:
            self._open_taiwan_draws_and_update_next_time()
            self._taiwan_retry_count = 0
            self._schedule_taiwan_precise_open()
            # 开奖成功后异步生成预测数据，填充 mode_payload_* 表
            _trigger_taiwan_prediction_generation(self.db_path)
        except Exception as e:
            self._taiwan_retry_count += 1
            _log_taiwan_task_error(f"Attempt {self._taiwan_retry_count}/{self._TAIWAN_MAX_RETRIES} failed: {e}")
            if self._taiwan_retry_count <= self._TAIWAN_MAX_RETRIES:
                delay = self._TAIWAN_RETRY_DELAYS[self._taiwan_retry_count - 1]
                print(f"[TaiwanScheduler] Retry in {delay}s (attempt {self._taiwan_retry_count}/{self._TAIWAN_MAX_RETRIES})")
                self._taiwan_timer = threading.Timer(delay, self._taiwan_precise_open_execute)
                self._taiwan_timer.daemon = True
                self._taiwan_timer.start()
            else:
                print(f"[TaiwanScheduler] All retries exhausted, scheduling next day")
                _log_taiwan_task_error(f"All {self._TAIWAN_MAX_RETRIES} retries exhausted")
                self._taiwan_retry_count = 0
                self._schedule_taiwan_precise_open()

    def _open_taiwan_draws_and_update_next_time(self) -> None:
        """北京时间 22:30 精准开奖：将 type=3 且 draw_time 已过的未开奖记录置为 is_opened=1，
        并立即计算下一期 draw_time 更新 next_time 为 Unix 秒级时间戳。

        注意：draw_time 字段存储的是北京时间字符串，比较时必须使用北京时间。"""
        from calendar import timegm

        now_utc_dt = datetime.now(timezone.utc)
        now_utc = now_utc_dt.strftime("%Y-%m-%d %H:%M:%S")
        now_beijing = (now_utc_dt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

        with db_connect(self.db_path) as conn:
            cur = conn.execute(
                """UPDATE lottery_draws SET is_opened = 1, updated_at = ?
                   WHERE lottery_type_id = 3 AND is_opened = 0
                   AND draw_time IS NOT NULL AND draw_time != ''
                   AND draw_time <= ?""",
                (now_utc, now_beijing),
            )
            opened_count = cur.rowcount
            if opened_count > 0:
                print(f"[TaiwanOpen] 22:30 Beijing — opened {opened_count} Taiwan draw(s)")
            else:
                print(f"[TaiwanOpen] 22:30 Beijing — no Taiwan draws to open")

            rows = conn.execute(
                """SELECT id, year, term, draw_time FROM lottery_draws
                   WHERE lottery_type_id = 3 AND updated_at = ?""",
                (now_utc,),
            ).fetchall()

            for row in rows:
                self._calc_and_update_next_time(conn, row, now_utc)

            if rows:
                conn.commit()

    def _calc_and_update_next_time(self, conn, row, now_str: str) -> None:
        """根据当期 draw_time + 1 天计算下一期 draw_time，将 next_time 更新为毫秒级时间戳。"""
        from calendar import timegm

        draw_time_str = row["draw_time"]
        draw_dt = datetime.strptime(draw_time_str, "%Y-%m-%d %H:%M:%S")
        next_dt = draw_dt + timedelta(days=1)
        # draw_time 存储的是北京时间，转为 UTC 后计算毫秒时间戳
        utc_dt = next_dt - timedelta(hours=8)
        unix_ms = int(timegm(utc_dt.timetuple()) * 1000)
        next_time_str = str(unix_ms)

        conn.execute(
            "UPDATE lottery_draws SET next_time = ?, updated_at = ? WHERE id = ?",
            (next_time_str, now_str, row["id"]),
        )
        conn.execute(
            "UPDATE lottery_types SET next_time = ?, updated_at = ? WHERE id = 3",
            (next_time_str, now_str),
        )
        print(f"[TaiwanOpen] Term {row['term']}: next_time={unix_ms} "
              f"({next_dt.strftime('%Y-%m-%d %H:%M:%S')} Beijing)")


# ─────────────────────────────────────────────────────────
# 独立爬取（不生成预测）+ 6 小时延迟自动预测任务
# ─────────────────────────────────────────────────────────

# 全局字典：跟踪已调度的自动预测定时器，按 (db_path, lottery_type_id) 索引
_auto_prediction_timers: dict[tuple[str, int], threading.Timer] = {}
_auto_timers_lock = threading.Lock()

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
ERROR_LOG_PATH = _BACKEND_ROOT / "data" / "error.log"


def _log_auto_task_error(message: str) -> None:
    """将自动预测任务错误追加写入 error.log。"""
    ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] AUTO_PREDICT_FAIL {message}\n")


def _log_taiwan_task_error(message: str) -> None:
    """将台湾彩每日定时开奖任务错误追加写入 error.log。"""
    ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] TAIWAN_OPEN_FAIL {message}\n")


def _trigger_taiwan_prediction_generation(db_path: str | Path) -> None:
    """台湾彩开奖后异步触发预测数据生成。

    后台线程执行：回填开奖结果到 mode_payload_* 表 →
    生成下一期预测数据。这样前端 JS 模块查询 mode_payload_*
    表时就能拿到最新预测内容，保证前端显示随数据库更新。
    """
    def _run():
        try:
            print("[TaiwanPredGen] Starting prediction generation after Taiwan draw open...")
            _run_auto_prediction(db_path, 3)
            print("[TaiwanPredGen] Prediction generation completed")
        except Exception as exc:
            print(f"[TaiwanPredGen] Prediction generation failed: {exc}")
            _log_taiwan_task_error(f"Prediction generation failed: {exc}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def _update_auto_task_status(
    db_path: str | Path, lottery_type_id: int, status: str, message: str
) -> None:
    """更新 lottery_types.last_auto_task_status 字段。"""
    ts = datetime.now(timezone.utc).isoformat()
    value = f"{status}|{message}|{ts}"
    try:
        with db_connect(db_path) as conn:
            conn.execute(
                "UPDATE lottery_types SET last_auto_task_status = ?, updated_at = ? WHERE id = ?",
                (value, ts, lottery_type_id),
            )
    except Exception as e:
        print(f"[AutoPred] Failed to update status for lt={lottery_type_id}: {e}")


def _backfill_draw_to_predictions(
    db_path: str | Path, lottery_type_id: int, year: int, term: int, numbers_str: str
) -> int:
    """将开奖结果的生肖和波色回填到 created schema 的预测记录中。

    遍历所有 mode_payload 表，找到同 year+term+type 的 created 记录，
    用 fixed_data 映射计算 res_sx / res_color 并 UPDATE。

    :return: 回填影响的记录总数
    """
    from helpers import load_fixed_data_maps
    from admin.prediction import _compute_res_fields
    from utils.created_prediction_store import (
        CREATED_SCHEMA_NAME, quote_qualified_identifier, schema_table_exists,
    )

    total_updated = 0
    try:
        with db_connect(db_path) as conn:
            zodiac_map, color_map = load_fixed_data_maps(conn)
            res_sx, res_color = _compute_res_fields(numbers_str, zodiac_map, color_map)

            # 获取所有 mode_payload 表名
            tables = conn.list_tables("mode_payload_")
            for table_name in tables:
                if not schema_table_exists(conn, CREATED_SCHEMA_NAME, table_name):
                    continue
                qualified = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
                try:
                    cur = conn.execute(
                        f"UPDATE {qualified} SET res_sx = ?, res_color = ? "
                        "WHERE type = ? AND year = ? AND term = ? AND (res_sx IS NULL OR res_sx = '')",
                        (res_sx, res_color, str(lottery_type_id), str(year), str(term)),
                    )
                    total_updated += cur.rowcount
                except Exception:
                    continue  # 表可能缺少列，跳过
            conn.commit()
    except Exception as e:
        print(f"[AutoPred] Backfill error: {e}")
    return total_updated


def _run_auto_prediction(db_path: str | Path, lottery_type_id: int) -> None:
    """6 小时延迟后自动执行：回填开奖 + 生成下一期预测。"""
    print(f"[AutoPred] Starting for lt={lottery_type_id}...")
    try:
        # 1. 读取最新开奖结果
        with db_connect(db_path) as conn:
            row = conn.execute(
                """SELECT year, term, numbers FROM lottery_draws
                   WHERE lottery_type_id = ? AND is_opened = 1
                   ORDER BY year DESC, term DESC LIMIT 1""",
                (lottery_type_id,),
            ).fetchone()
            if not row:
                raise ValueError("no opened draw found")
            year = int(row["year"])
            term = int(row["term"])
            numbers_str = str(row["numbers"] or "")

        # 2. 回填开奖结果到预测记录
        backfilled = _backfill_draw_to_predictions(db_path, lottery_type_id, year, term, numbers_str)
        print(f"[AutoPred] Backfilled {backfilled} prediction records for lt={lottery_type_id} year={year} term={term}")

        # 3. 生成未来下一期预测（遍历所有启用站点）
        from admin.prediction import bulk_generate_site_prediction_data as _bulk_gen
        issue_str = f"{year}{term:03d}"
        total_inserted = 0
        total_pred_errors = 0
        with db_connect(db_path) as conn:
            sites = conn.execute(
                "SELECT id FROM managed_sites WHERE enabled = 1"
            ).fetchall()
            for site in sites:
                site_id = int(site["id"])
                try:
                    gen = _bulk_gen(
                        db_path, site_id,
                        {
                            "lottery_type": lottery_type_id,
                            "start_issue": issue_str,
                            "end_issue": issue_str,
                            "future_periods": 1,
                        },
                    )
                    total_inserted += gen.get("inserted", 0)
                    total_pred_errors += gen.get("errors", 0)
                except Exception as e:
                    total_pred_errors += 1
                    print(f"[AutoPred] site={site_id} error: {e}")

        _update_auto_task_status(db_path, lottery_type_id, "ok",
                                 f"backfilled={backfilled} inserted={total_inserted} errors={total_pred_errors}")
        print(f"[AutoPred] Done lt={lottery_type_id}: backfilled={backfilled} inserted={total_inserted} errors={total_pred_errors}")

    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"
        _log_auto_task_error(f"lt_id={lottery_type_id} {err_msg}")
        _update_auto_task_status(db_path, lottery_type_id, "error", err_msg)
        print(f"[AutoPred] FAILED lt={lottery_type_id}: {err_msg}")
    finally:
        # 清理已完成的定时器
        with _auto_timers_lock:
            _auto_prediction_timers.pop((str(db_path), lottery_type_id), None)


def _schedule_auto_prediction(
    db_path: str | Path, lottery_type_id: int, draw_time_str: str
) -> float:
    """安排一次 6 小时后的自动预测任务。

    :param draw_time_str: 开奖时间字符串，格式 \"2026-05-10 21:32:59\"
    :return: 延迟秒数
    """
    from datetime import timedelta

    # 解析开奖时间
    try:
        draw_dt = datetime.strptime(draw_time_str.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        # 回退：30 分钟后
        draw_dt = datetime.now(timezone.utc) + timedelta(minutes=30)

    target_dt = draw_dt + timedelta(hours=6)
    now_dt = datetime.now(timezone.utc)
    delay = max(60.0, (target_dt - now_dt).total_seconds())

    key = (str(db_path), lottery_type_id)
    with _auto_timers_lock:
        old = _auto_prediction_timers.pop(key, None)
        if old:
            old.cancel()
        timer = threading.Timer(delay, _run_auto_prediction, args=(db_path, lottery_type_id))
        timer.daemon = True
        timer.start()
        _auto_prediction_timers[key] = timer

    target_iso = target_dt.isoformat()
    print(f"[AutoPred] Scheduled for lt={lottery_type_id} at {target_iso} (delay={delay:.0f}s)")
    return delay


def run_crawl_only(db_path: str | Path, lottery_type_id: int) -> dict[str, Any]:
    """仅执行爬取并存储到 lottery_draws，不生成预测资料。

    使用 result_crawler.fetch_current_term_data 获取当前期开奖数据，
    写入 lottery_draws 后安排 6 小时后的自动预测任务。

    :param db_path: 数据库连接字符串
    :param lottery_type_id: 彩种 ID（1=香港, 2=澳门, 3=台湾）
    :return: 包含 draw 信息和 auto_task 调度信息的字典
    """
    meta_map = _get_lottery_meta(db_path)
    lt_name_map = {1: "香港彩", 2: "澳门彩", 3: "台湾彩"}
    lt_name = lt_name_map.get(lottery_type_id, str(lottery_type_id))
    lt_meta = meta_map.get(lt_name)
    if lt_meta is None:
        raise ValueError(f"彩种 {lt_name} 不存在")

    # 台湾彩无在线爬虫
    if lottery_type_id == 3:
        return {
            "ok": True,
            "draw": None,
            "message": "台湾彩无在线爬虫，请使用 /api/admin/crawler/import-taiwan 导入 JSON",
        }

    # 调用 result_crawler 获取当前期数据（传入数据库配置的采集地址）
    from result_crawler import fetch_current_term_data, transform_standard_list

    crawler_type = 1 if lottery_type_id == 1 else 2
    raw, status_code = fetch_current_term_data(
        type=crawler_type,
        collect_url=lt_meta.get("collect_url", ""),
    )

    if status_code != 200:
        raise RuntimeError(f"爬虫返回 HTTP {status_code}")

    # result_crawler 返回单个 JSON 对象（非数组），包装为列表
    import json as _json
    parsed = _json.loads(raw) if isinstance(raw, str) else raw
    if isinstance(parsed, dict):
        parsed = [parsed]
    records = transform_standard_list(parsed, crawler_type=crawler_type)
    if not records:
        raise ValueError("爬虫未返回任何开奖记录")

    now = datetime.now(timezone.utc).isoformat()
    saved = 0
    draw_info: dict[str, Any] = {}
    with db_connect(db_path) as conn:
        for item in records:
            try:
                open_time = item["open_time"]
                year = int(open_time[:4])
                issue = item["issue"]
                try:
                    term_num = int(issue)
                except ValueError:
                    # issue 可能是 "2026128" 格式
                    term_num = int(str(issue)[4:]) if len(str(issue)) > 4 else int(issue)
                _upsert_draw(conn, lt_meta["id"], year, term_num,
                             item["result"], open_time, 1, now,
                             next_time=str(item.get("next_time") or ""))
                saved += 1
                if saved == 1:
                    draw_info = {"year": year, "term": term_num, "issue": issue, "open_time": open_time}
            except (ValueError, KeyError) as e:
                print(f"  [CrawlOnly] SKIP: {item.get('issue', '?')} - {e}")

    # 爬取成功后安排 6 小时后自动预测
    auto_delay = 0.0
    if saved > 0 and draw_info.get("open_time"):
        auto_delay = _schedule_auto_prediction(db_path, lottery_type_id, draw_info["open_time"])

    return {
        "ok": True,
        "draw": draw_info,
        "saved": saved,
        "fetched": len(records),
        "auto_task_scheduled_seconds": round(auto_delay, 0) if auto_delay > 0 else None,
    }
