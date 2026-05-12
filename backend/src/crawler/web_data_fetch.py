"""抓取站点 modes 数据并写入本地 PostgreSQL 数据库。

该脚本会先从站点管理页解析出每个 `web_id` 下的 `modes_list`，
再按 `modes_id` 分页抓取 `all_data`，最终写入：

1. `fetched_modes`：保存模式基础信息与原始 payload
2. `fetched_mode_records`：保存每条历史记录与原始 payload
3. `public.mode_payload_{modes_id}`：将爬取数据直接写入业务表，供前端查询

数据库连接通过环境变量或 `config.yaml` 提供，不在脚本中硬编码。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = Path(__file__).resolve().parents[1]

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import config as app_config
from db import connect, default_postgres_target, quote_identifier

# ── 日志 ──────────────────────────────────────────────────
_logger = logging.getLogger("crawler.web_data_fetch")
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
_logger.addHandler(_log_handler)
_logger.setLevel(logging.DEBUG)

# ── 配置 ──────────────────────────────────────────────────
_db_cfg = app_config.section("database")
_site_cfg = app_config.section("site")
_fetch_cfg = app_config.section("fetch")

WEB_MANAGE_URL_TEMPLATE = _site_cfg.get(
    "manage_url_template",
    "https://admin.shengshi8800.com/ds67BvM/web/webManage?id={web_id}",
)
MODES_DATA_URL = _site_cfg.get(
    "modes_data_url",
    "https://admin.shengshi8800.com/ds67BvM/web/getModesDataList",
)
DEFAULT_TOKEN = _site_cfg.get("default_token", "")
DEFAULT_USER_AGENT = _fetch_cfg.get(
    "user_agent",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
)
def default_db_target() -> str:
    """返回默认数据库目标，优先使用环境变量，其次使用配置文件 PostgreSQL DSN。"""
    return default_postgres_target()


DEFAULT_DB_TARGET = default_db_target()

# ── 字段映射配置 ─────────────────────────────────────────
# 将爬取结果的原始字段映射到 mode_payload_{modes_id} 表字段。
# 键为爬取结果的 JSON key，值为数据库列名。
# 可根据不同数据源灵活调整此映射。
PAYLOAD_FIELD_MAP: dict[str, str] = {
    "id": "source_record_id",
    "year": "year",
    "term": "term",
    "status": "status",
    "content": "content",
    "code": "res_code",
    "pre_code": "res_code",
    "res_sx": "res_sx",
    "res_color": "res_color",
    "type": "type",
    "web": "web",
    "web_id": "web_id",
}

# 写入 mode_payload 表时必须包含的基础列（即使爬取数据中没有也会设默认值）
REQUIRED_PAYLOAD_COLUMNS: dict[str, Any] = {
    "web": "",
    "web_id": 0,
    "type": "",
    "year": "",
    "term": "",
    "status": 0,
    "content": "",
    "res_code": "",
    "res_sx": "",
    "res_color": "",
    "modes_id": 0,
    "source_record_id": "",
}

# 用于判断重复记录的业务唯一键（按此组合去重）
# 同一期次可有不同预测内容，因此加上 source_record_id 区分
DEDUP_COLUMNS = ("web_id", "type", "year", "term", "source_record_id")


# ── 工具函数 ──────────────────────────────────────────────

def build_headers(token: str | None = DEFAULT_TOKEN) -> dict[str, str]:
    """构造抓取站点接口所需的请求头。"""
    headers = {"User-Agent": str(DEFAULT_USER_AGENT)}
    if token:
        headers["Cookie"] = f"token={token}"
    return headers


def parse_js_modes_list(html: str) -> list[dict[str, Any]]:
    """从管理页面 HTML 中解析 `let modes = [...]` 结构。"""
    match = re.search(r"let\s+modes\s*=\s*(\[\s*\{.*?\}\s*\]);", html, re.DOTALL)
    if not match:
        return []
    js_obj = match.group(1)
    json_str = re.sub(r"([,{]\s*)([A-Za-z_]\w*)\s*:", r'\1"\2":', js_obj)
    json_str = json_str.replace("'", '"')
    parsed = json.loads(json_str)
    return parsed if isinstance(parsed, list) else []


def normalize_mode(raw_mode: dict[str, Any], web_id: int) -> dict[str, Any] | None:
    """将原始 mode 数据规整成统一结构。"""
    modes_id = raw_mode.get("modes_id", raw_mode.get("id"))
    if modes_id is None:
        return None
    try:
        modes_id = int(modes_id)
    except (TypeError, ValueError):
        return None
    title = str(raw_mode.get("title", raw_mode.get("name", "")) or "")
    return {"web_id": web_id, "modes_id": modes_id, "title": title, "payload": raw_mode}


# ── 数据清洗与校验 ────────────────────────────────────────

def _clean_value(value: Any, column: str) -> Any:
    """对单个字段值做清洗和类型规范化。"""
    if value is None:
        return REQUIRED_PAYLOAD_COLUMNS.get(column, "")
    if column in ("web_id", "modes_id", "status"):
        try:
            return int(value)
        except (TypeError, ValueError):
            return REQUIRED_PAYLOAD_COLUMNS.get(column, 0)
    if column in ("year", "term"):
        return str(value).strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _validate_row(row: dict[str, Any]) -> list[str]:
    """校验单行数据，返回错误描述列表（空列表表示通过）。"""
    errors: list[str] = []
    if not str(row.get("year", "")).strip():
        errors.append("year 为空")
    if not str(row.get("term", "")).strip():
        errors.append("term 为空")
    if row.get("web_id", 0) <= 0:
        errors.append(f"web_id 无效: {row.get('web_id')}")
    return errors


def _map_record_to_payload_row(
    record: dict[str, Any],
    web_id: int,
    modes_id: int,
    fetched_at: str,
) -> dict[str, Any] | None:
    """将单条爬取记录映射为 mode_payload 表行，失败返回 None。"""
    row: dict[str, Any] = dict(REQUIRED_PAYLOAD_COLUMNS)

    # 字段映射
    for src_key, db_col in PAYLOAD_FIELD_MAP.items():
        if src_key in record:
            row[db_col] = record[src_key]

    # 元数据字段
    row["modes_id"] = modes_id
    row["web_id"] = int(web_id)
    row["web"] = str(web_id)
    if not row.get("source_record_id"):
        row["source_record_id"] = str(record.get("id", record.get("source_record_id", "")))

    # 清洗
    for col in list(row.keys()):
        row[col] = _clean_value(row.get(col), col)

    # 记录爬取时间戳和来源
    row["fetched_at"] = fetched_at
    row["_source"] = "crawler"

    # 校验
    errors = _validate_row(row)
    if errors:
        _logger.debug("记录校验失败，跳过: %s", errors)
        return None

    return row


# ── 数据库表管理 ──────────────────────────────────────────

def ensure_fetch_tables(conn: Any) -> None:
    """确保抓取结果所需的数据表和索引已经创建。"""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fetched_modes (
            web_id INTEGER NOT NULL,
            modes_id INTEGER NOT NULL,
            title TEXT,
            payload_json TEXT NOT NULL,
            record_count INTEGER NOT NULL DEFAULT 0,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (web_id, modes_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fetched_mode_records (
            web_id INTEGER NOT NULL,
            modes_id INTEGER NOT NULL,
            source_record_id TEXT NOT NULL,
            year TEXT,
            term TEXT,
            status INTEGER,
            content TEXT,
            payload_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (web_id, modes_id, source_record_id),
            FOREIGN KEY (web_id, modes_id)
                REFERENCES fetched_modes(web_id, modes_id)
                ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fetched_mode_records_lookup
        ON fetched_mode_records(web_id, modes_id, year, term)
        """
    )


def ensure_mode_payload_table(conn: Any, modes_id: int) -> str:
    """确保 `public.mode_payload_{modes_id}` 表存在，返回表名。"""
    table_name = f"mode_payload_{modes_id}"
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {quote_identifier(table_name)} (
            id BIGSERIAL PRIMARY KEY,
            web_id INTEGER NOT NULL DEFAULT 0,
            web TEXT NOT NULL DEFAULT '',
            type TEXT NOT NULL DEFAULT '',
            year TEXT NOT NULL DEFAULT '',
            term TEXT NOT NULL DEFAULT '',
            status INTEGER NOT NULL DEFAULT 0,
            content TEXT NOT NULL DEFAULT '',
            res_code TEXT NOT NULL DEFAULT '',
            res_sx TEXT NOT NULL DEFAULT '',
            res_color TEXT NOT NULL DEFAULT '',
            modes_id INTEGER NOT NULL DEFAULT 0,
            source_record_id TEXT NOT NULL DEFAULT '',
            fetched_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    # 创建普通索引加速去重查询（非唯一索引，容忍历史数据中的重复）
    try:
        conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_dedup
            ON {quote_identifier(table_name)} (web_id, type, year, term, source_record_id)
            """
        )
    except Exception:
        # 索引创建失败不影响数据写入，去重逻辑由应用层 _row_exists() 保证
        _logger.debug("索引 idx_%s_dedup 创建失败，继续写入流程", table_name)
    return table_name


# ── 写入 mode_payload 表 ─────────────────────────────────

def _get_table_columns(conn: Any, table_name: str) -> set[str]:
    """获取表的所有列名。"""
    rows = conn.table_columns(table_name)
    return set(rows) if rows else set()


def save_to_mode_payload_table(
    conn: Any,
    web_id: int,
    modes_id: int,
    records: list[dict[str, Any]],
    fetched_at: str,
    *,
    dedup: bool = True,
) -> dict[str, int]:
    """将爬取数据写入 `public.mode_payload_{modes_id}` 表。

    特性：
    - 自动创建表（如不存在）
    - 按 (web_id, type, year, term, source_record_id) 去重
    - 相同业务键的记录先删除再插入，实现覆盖写入
    - 数据清洗 + 字段映射 + 校验
    - 记录爬取时间戳和来源标识

    Args:
        conn: 数据库连接适配器。
        web_id: 站点编号。
        modes_id: 模式编号。
        records: 原始爬取记录列表。
        fetched_at: UTC ISO 时间戳。
        dedup: 是否启用在内存去重（默认开启）。

    Returns:
        dict: {"total": 总条数, "inserted": 写入数, "skipped": 内存去重跳过数, "invalid": 无效数}
    """
    stats = {"total": len(records), "inserted": 0, "skipped": 0, "invalid": 0}

    # 确保表存在
    table_name = ensure_mode_payload_table(conn, modes_id)
    columns = _get_table_columns(conn, table_name)
    if not columns:
        _logger.warning("mode_payload_%d 表无列信息，跳过写入", modes_id)
        stats["invalid"] = len(records)
        return stats

    # 映射、清洗、校验
    mapped_rows: list[dict[str, Any]] = []
    for record in records:
        row = _map_record_to_payload_row(record, web_id, modes_id, fetched_at)
        if row is None:
            stats["invalid"] += 1
            continue
        # 去掉内部标记字段
        row.pop("_source", None)
        mapped_rows.append(row)

    if not mapped_rows:
        _logger.info("mode_payload_%d web_id=%d: 无有效记录可写入", modes_id, web_id)
        return stats

    # 按 (web_id, type, year, term, source_record_id) 去重，保留首次出现的记录
    if dedup:
        seen: set[tuple] = set()
        deduped: list[dict[str, Any]] = []
        for row in mapped_rows:
            key = (
                int(row.get("web_id", 0)),
                str(row.get("type", "")),
                str(row.get("year", "")),
                str(row.get("term", "")),
                str(row.get("source_record_id", "")),
            )
            if key in seen:
                stats["skipped"] += 1
                continue
            seen.add(key)
            deduped.append(row)
    else:
        deduped = mapped_rows

    if not deduped:
        _logger.info("mode_payload_%d web_id=%d: 去重后无新记录", modes_id, web_id)
        stats["skipped"] = len(mapped_rows)
        return stats

    # 只包含表实际存在的列
    insertable_columns = [
        col for col in REQUIRED_PAYLOAD_COLUMNS if col in columns
    ]
    if "fetched_at" in columns and "fetched_at" not in insertable_columns:
        insertable_columns.append("fetched_at")

    placeholders = ", ".join(["?"] * len(insertable_columns))
    quoted_cols = ", ".join(quote_identifier(c) for c in insertable_columns)
    insert_sql = (
        f"INSERT INTO {quote_identifier(table_name)} "
        f"({quoted_cols}) VALUES ({placeholders})"
    )

    # 先删除匹配 (web_id, type, year, term, source_record_id) 的已有记录，实现覆盖写入
    dedup_keys = list({(
        int(row.get("web_id", 0)),
        str(row.get("type", "")),
        str(row.get("year", "")),
        str(row.get("term", "")),
        str(row.get("source_record_id", "")),
    ) for row in deduped})

    if dedup_keys:
        key_placeholders = ", ".join(["(?, ?, ?, ?, ?)"] * len(dedup_keys))
        flat_params: list[Any] = []
        for k in dedup_keys:
            flat_params.extend(k)
        deleted = conn.execute(
            f"""
            DELETE FROM {quote_identifier(table_name)}
            WHERE (web_id, type, year, term, source_record_id) IN ({key_placeholders})
            """,
            flat_params,
        ).rowcount
        if deleted:
            _logger.debug("mode_payload_%d web_id=%d: 已删除 %d 条旧记录", modes_id, web_id, deleted)

    rows_data = [
        [row.get(col, REQUIRED_PAYLOAD_COLUMNS.get(col, "")) for col in insertable_columns]
        for row in deduped
    ]

    try:
        conn.executemany(insert_sql, rows_data)
        stats["inserted"] = len(deduped)
        _logger.info(
            "mode_payload_%d web_id=%d: 写入 %d 条记录",
            modes_id, web_id, stats["inserted"],
        )
    except Exception as exc:
        _logger.error(
            "mode_payload_%d web_id=%d 批量插入失败: %s",
            modes_id, web_id, exc,
        )
        stats["inserted"] = 0
        for row in deduped:
            try:
                conn.execute(insert_sql, [
                    row.get(col, REQUIRED_PAYLOAD_COLUMNS.get(col, ""))
                    for col in insertable_columns
                ])
                stats["inserted"] += 1
            except Exception as row_exc:
                _logger.debug(
                    "mode_payload_%d 单条插入失败 year=%s term=%s: %s",
                    modes_id, row.get("year"), row.get("term"), row_exc,
                )
        _logger.warning(
            "mode_payload_%d web_id=%d: 逐条插入完成，成功 %d 条",
            modes_id, web_id, stats["inserted"],
        )

    return stats


# ── 抓取逻辑 ──────────────────────────────────────────────

def fetch_web_id_list(
    start_web_id: int = 2,
    end_web_id: int = 4,
    url_template: str = WEB_MANAGE_URL_TEMPLATE,
    token: str | None = DEFAULT_TOKEN,
) -> dict[int, list[dict[str, Any]]]:
    """抓取指定站点区间内的 `modes_list`。"""
    headers = build_headers(token)
    result: dict[int, list[dict[str, Any]]] = {}

    for web_id in range(start_web_id, end_web_id + 1):
        url = url_template.format(web_id=web_id, id=web_id)
        try:
            _logger.info("正在请求 web_id=%d 的 modes_list...", web_id)
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            modes_list = parse_js_modes_list(response.text)
        except requests.exceptions.RequestException as exc:
            _logger.error("web_id=%d 请求失败: %s", web_id, exc)
            result[web_id] = []
            continue
        except json.JSONDecodeError as exc:
            _logger.error("web_id=%d modes_list 解析失败: %s", web_id, exc)
            result[web_id] = []
            continue

        normalized = [
            mode
            for raw_mode in modes_list
            if (mode := normalize_mode(raw_mode, web_id)) is not None
        ]
        result[web_id] = normalized
        _logger.info("web_id=%d 获取到 %d 个 modes", web_id, len(normalized))
        time.sleep(0.2)

    return result


def fetch_all_data_for_mode(
    web_id: int,
    modes_id: int,
    base_url: str = MODES_DATA_URL,
    token: str | None = DEFAULT_TOKEN,
    limit: int = 250,
    request_delay: float = 0.5,
) -> list[dict[str, Any]]:
    """抓取单个 `modes_id` 的全部分页数据。"""
    headers = build_headers(token)
    page = 1
    all_data: list[dict[str, Any]] = []

    while True:
        params = {
            "page": page,
            "limit": limit,
            "web_id": web_id,
            "modes_id": modes_id,
        }
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as exc:
            _logger.error("web_id=%d, modes_id=%d, page=%d 请求失败: %s", web_id, modes_id, page, exc)
            break
        except json.JSONDecodeError as exc:
            _logger.error("web_id=%d, modes_id=%d, page=%d JSON 解析失败: %s", web_id, modes_id, page, exc)
            break

        if result.get("code") != 0:
            _logger.error("web_id=%d, modes_id=%d API 返回错误: %s", web_id, modes_id, result.get("msg"))
            break

        current_page_data = result.get("data", [])
        if not current_page_data:
            break

        all_data.extend(current_page_data)
        total_count = int(result.get("count", 0) or 0)
        _logger.debug(
            "web_id=%d, modes_id=%d, page=%d: %d 条，累计 %d/%d",
            web_id, modes_id, page, len(current_page_data), len(all_data), total_count,
        )

        if page * limit >= total_count or len(current_page_data) < limit:
            break

        page += 1
        time.sleep(request_delay)

    return all_data


def save_mode_all_data(
    conn: Any,
    web_id: int,
    mode: dict[str, Any],
    all_data: list[dict[str, Any]],
    fetched_at: str,
) -> None:
    """保存单个 mode 的基础信息和全部历史记录到 fetched_mode_records。"""
    modes_id = int(mode["modes_id"])

    rows: list[tuple[Any, ...]] = []
    for index, payload in enumerate(all_data):
        source_record_id = str(payload.get("id", payload.get("source_record_id", index)))
        rows.append(
            (
                web_id,
                modes_id,
                source_record_id,
                str(payload.get("year", "") or ""),
                str(payload.get("term", "") or ""),
                payload.get("status"),
                str(payload.get("content", "") or ""),
                json.dumps(payload, ensure_ascii=False),
                fetched_at,
            )
        )

    if rows:
        conn.executemany(
            """
            INSERT INTO fetched_mode_records (
                web_id, modes_id, source_record_id, year, term,
                status, content, payload_json, fetched_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (web_id, modes_id, source_record_id) DO NOTHING
            """,
            rows,
        )


# ── JSON 本地备份 ──────────────────────────────────────────

LOTTERY_DATA_DIR = BACKEND_ROOT / "lottery_data"


def save_data_to_json(
    web_id: int,
    modes_id: int,
    all_data: list[dict[str, Any]],
    fetched_at: str,
) -> Path:
    """将爬取数据同步保存一份 JSON 到本地 lottery_data 目录。

    文件命名格式：lottery_web{w}_mode{m}_{timestamp}.json
    """
    LOTTERY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    ts = fetched_at.replace(":", "").replace("-", "").replace("T", "_")[:15]
    filename = f"lottery_web{web_id}_mode{modes_id}_{ts}.json"
    filepath = LOTTERY_DATA_DIR / filename
    payload = {
        "web_id": web_id,
        "modes_id": modes_id,
        "fetched_at": fetched_at,
        "count": len(all_data),
        "data": all_data,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    _logger.info("JSON 已保存: %s (%d 条)", filepath, len(all_data))
    return filepath


# ── 主流程 ────────────────────────────────────────────────

def fetch_modes_data(
    db_path: str | Path = DEFAULT_DB_TARGET,
    start_web_id: int = 2,
    end_web_id: int = 4,
    token: str | None = DEFAULT_TOKEN,
    limit: int = 20,
    request_delay: float = 0.5,
    *,
    save_to_payload: bool = True,
) -> None:
    """按 `web_id -> modes_id` 抓取全部数据并保存到本地 PostgreSQL。

    写入目标：
    1. `lottery_data/`：本地 JSON 备份
    2. `fetched_mode_records`：原始快照
    3. `public.mode_payload_{modes_id}`：业务查询表（覆盖写入）

    Args:
        db_path: 数据库目标（PostgreSQL DSN 或 SQLite 路径）。
        start_web_id: 起始站点编号。
        end_web_id: 结束站点编号。
        token: 后台登录 token。
        limit: 分页接口每页条数。
        request_delay: 分页请求间隔秒数。
        save_to_payload: 是否自动写入 mode_payload_{modes_id} 表（默认开启）。
    """
    db_target = str(db_path)
    modes_by_web = fetch_web_id_list(start_web_id, end_web_id, token=token)
    fetched_at = datetime.now(timezone.utc).isoformat()

    # 全局统计
    total_payload_inserted = 0
    total_payload_skipped = 0
    total_payload_invalid = 0

    with connect(db_target) as conn:
        for web_id in range(start_web_id, end_web_id + 1):
            modes_list = modes_by_web.get(web_id, [])
            if not modes_list:
                _logger.info("web_id=%d 没有可用的 modes_list，跳过。", web_id)
                continue

            for mode in modes_list:
                modes_id = int(mode["modes_id"])
                _logger.info("--- 正在处理 web_id=%d, modes_id=%d ---", web_id, modes_id)

                all_data = fetch_all_data_for_mode(
                    web_id=web_id,
                    modes_id=modes_id,
                    token=token,
                    limit=limit,
                    request_delay=request_delay,
                )

                if not all_data:
                    _logger.info("web_id=%d, modes_id=%d: 无数据", web_id, modes_id)
                    continue

                # 同步保存 JSON 到本地
                save_data_to_json(web_id, modes_id, all_data, fetched_at)

                # 写入原始快照表
                save_mode_all_data(conn, web_id, mode, all_data, fetched_at)

                # 写入 mode_payload 业务表（事务保护）
                if save_to_payload:
                    try:
                        payload_stats = save_to_mode_payload_table(
                            conn, web_id, modes_id, all_data, fetched_at,
                        )
                        total_payload_inserted += payload_stats["inserted"]
                        total_payload_skipped += payload_stats["skipped"]
                        total_payload_invalid += payload_stats["invalid"]
                    except Exception as exc:
                        _logger.exception(
                            "web_id=%d, modes_id=%d 写入 mode_payload 表失败: %s",
                            web_id, modes_id, exc,
                        )

                conn.commit()
                _logger.info(
                    "已保存 web_id=%d, modes_id=%d: %d 条记录 -> %s",
                    web_id, modes_id, len(all_data), db_target,
                )

    _logger.info(
        "全部完成: mode_payload 新增 %d, 跳过 %d, 无效 %d",
        total_payload_inserted, total_payload_skipped, total_payload_invalid,
    )


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="抓取指定 web_id 区间内的 modes_list 及其 all_data，写入 PostgreSQL。"
    )
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_TARGET,
        help="数据库目标，可传 PostgreSQL DSN 或 SQLite 路径；默认使用环境变量或配置文件。",
    )
    parser.add_argument("--start-web-id", type=int, default=2, help="起始 web_id。")
    parser.add_argument("--end-web-id", type=int, default=4, help="结束 web_id。")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="后台 token。")
    parser.add_argument("--limit", type=int, default=250, help="分页接口每页条数。")
    parser.add_argument("--request-delay", type=float, default=0.5, help="分页请求间隔秒数。")
    parser.add_argument(
        "--skip-payload-insert",
        action="store_true",
        help="跳过写入 mode_payload_{modes_id} 表，仅写入原始快照表。",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    fetch_modes_data(
        db_path=args.db_path,
        start_web_id=args.start_web_id,
        end_web_id=args.end_web_id,
        token=args.token or None,
        limit=args.limit,
        request_delay=args.request_delay,
        save_to_payload=not args.skip_payload_insert,
    )
