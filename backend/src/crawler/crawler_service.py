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
    next_time: str = "",
) -> None:
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

    records = transform_macau_api(raw)
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
        # 启动定时器：每 60 秒检查是否有到达开奖时间的记录
        self._schedule_auto_open()

    def stop(self) -> None:
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if hasattr(self, "_auto_open_timer") and self._auto_open_timer:
            self._auto_open_timer.cancel()
            self._auto_open_timer = None

    def _schedule_next(self) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(self.interval, self._run)
        self._timer.daemon = True
        self._timer.start()

    def _auto_open_draws(self) -> None:
        """检查所有未开奖记录，若开奖时间已过则自动标记 is_opened=1。"""
        try:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            with db_connect(self.db_path) as conn:
                cur = conn.execute(
                    """UPDATE lottery_draws SET is_opened = 1, updated_at = ?
                       WHERE is_opened = 0 AND draw_time IS NOT NULL AND draw_time != ''
                       AND draw_time <= ?""",
                    (now, now),
                )
                if cur.rowcount > 0:
                    print(f"[AutoOpen] Set is_opened=1 for {cur.rowcount} draw(s)")
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

    def _run_once(self) -> None:
        """执行一轮爬取：香港彩 → 澳门彩，爬取后自动生成预测数据。"""
        crawled_type_ids: list[int] = []

        with self._lock:
            for lt_id, label in [(1, "HK"), (2, "Macau")]:
                try:
                    result = crawl_and_generate_for_type(self.db_path, lt_id)
                    print(f"  [{label}] crawl={result.get('crawl',{})} generation_count={len(result.get('generation',[]))}")
                    crawled_type_ids.append(lt_id)
                except Exception as e:
                    print(f"  [{label}] error: {e}")

    def _run(self) -> None:
        """定时执行爬取（由内部定时器调用）。"""
        if not self._running:
            return
        print("[CrawlerScheduler] Running scheduled crawl...")
        self._run_once()
        self._schedule_next()


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

    # 调用 result_crawler 获取当前期数据
    from result_crawler import fetch_current_term_data, transform_standard_list

    crawler_type = 1 if lottery_type_id == 1 else 2
    raw, status_code = fetch_current_term_data(type=crawler_type)

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
