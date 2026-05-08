"""抓取站点 modes 数据并写入本地 PostgreSQL 数据库。

该脚本会先从站点管理页解析出每个 `web_id` 下的 `modes_list`，
再按 `modes_id` 分页抓取 `all_data`，最终写入：

1. `fetched_modes`：保存模式基础信息与原始 payload
2. `fetched_mode_records`：保存每条历史记录与原始 payload

虽然项目底层 `db.connect()` 同时兼容 SQLite 和 PostgreSQL，
但这里默认目标已经切换为项目配置中的本地 PostgreSQL DSN。
"""

from __future__ import annotations

import argparse
import json
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

# 允许通过 `python backend/src/utils/data_fetch.py` 直接运行脚本。
# 这类运行方式下，Python 默认只会把 `utils` 目录加入 sys.path，
# 因此这里主动补上 `backend/src`，确保能导入同级公共模块。
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import config as app_config
from db import connect

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
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    ),
)
DEFAULT_POSTGRES_DSN = str(
    _db_cfg.get("default_postgres_dsn", "postgresql://postgres:2225427@localhost:5432/liuhecai")
)


def default_db_target() -> str:
    """返回默认数据库目标，优先使用 PostgreSQL 配置。

    Returns:
        str: 优先级依次为 `LOTTERY_DB_PATH`、`DATABASE_URL`、配置文件中的
        `default_postgres_dsn`，最后退回内置 PostgreSQL DSN。
    """

    return (
        str(os.environ.get("LOTTERY_DB_PATH") or "").strip()
        or str(os.environ.get("DATABASE_URL") or "").strip()
        or DEFAULT_POSTGRES_DSN
    )


DEFAULT_DB_TARGET = default_db_target()


def build_headers(token: str | None = DEFAULT_TOKEN) -> dict[str, str]:
    """构造抓取站点接口所需的请求头。

    Args:
        token: 后台登录 token。传入空值时不会附带 Cookie。

    Returns:
        dict[str, str]: `requests.get()` 可直接使用的请求头字典。
    """

    headers = {"User-Agent": str(DEFAULT_USER_AGENT)}
    if token:
        headers["Cookie"] = f"token={token}"
    return headers


def parse_js_modes_list(html: str) -> list[dict[str, Any]]:
    """从管理页面 HTML 中解析 `let modes = [...]` 结构。

    页面中的 `modes` 是 JavaScript 字面量，不一定是严格 JSON，
    因此这里会先将 key 和单引号转换成 JSON 兼容格式，再做反序列化。

    Args:
        html: 管理页面返回的完整 HTML 文本。

    Returns:
        list[dict[str, Any]]: 解析出的模式列表；如果未找到或解析失败则返回空列表。
    """

    match = re.search(r"let\s+modes\s*=\s*(\[\s*\{.*?\}\s*\]);", html, re.DOTALL)
    if not match:
        return []

    js_obj = match.group(1)
    json_str = re.sub(r"([,{]\s*)([A-Za-z_]\w*)\s*:", r'\1"\2":', js_obj)
    json_str = json_str.replace("'", '"')
    parsed = json.loads(json_str)
    return parsed if isinstance(parsed, list) else []


def normalize_mode(raw_mode: dict[str, Any], web_id: int) -> dict[str, Any] | None:
    """将原始 mode 数据规整成统一结构。

    Args:
        raw_mode: 页面里解析出来的单条模式原始数据。
        web_id: 当前站点编号。

    Returns:
        dict[str, Any] | None: 规整后的模式信息；如果缺少合法 `modes_id` 则返回 `None`。
    """

    modes_id = raw_mode.get("modes_id", raw_mode.get("id"))
    if modes_id is None:
        return None

    try:
        modes_id = int(modes_id)
    except (TypeError, ValueError):
        return None

    title = str(raw_mode.get("title", raw_mode.get("name", "")) or "")
    return {
        "web_id": web_id,
        "modes_id": modes_id,
        "title": title,
        "payload": raw_mode,
    }


def fetch_web_id_list(
    start_web_id: int = 1,
    end_web_id: int = 22,
    url_template: str = WEB_MANAGE_URL_TEMPLATE,
    token: str | None = DEFAULT_TOKEN,
) -> dict[int, list[dict[str, Any]]]:
    """抓取指定站点区间内的 `modes_list`。

    Args:
        start_web_id: 起始站点编号，包含本值。
        end_web_id: 结束站点编号，包含本值。
        url_template: 管理页 URL 模板，需要支持 `web_id` 占位符。
        token: 后台登录 token。

    Returns:
        dict[int, list[dict[str, Any]]]: 以 `web_id` 为键、规整后的 modes 列表为值的映射。
        某个站点抓取失败时，该站点对应空列表。
    """

    headers = build_headers(token)
    result: dict[int, list[dict[str, Any]]] = {}

    for web_id in range(start_web_id, end_web_id + 1):
        url = url_template.format(web_id=web_id, id=web_id)
        try:
            print(f"正在请求 web_id={web_id} 的 modes_list...")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            modes_list = parse_js_modes_list(response.text)
        except requests.exceptions.RequestException as exc:
            print(f"web_id={web_id} 请求失败: {exc}")
            result[web_id] = []
            continue
        except json.JSONDecodeError as exc:
            print(f"web_id={web_id} modes_list 解析失败: {exc}")
            result[web_id] = []
            continue

        normalized = [
            mode
            for raw_mode in modes_list
            if (mode := normalize_mode(raw_mode, web_id)) is not None
        ]
        result[web_id] = normalized
        print(f"web_id={web_id} 获取到 {len(normalized)} 个 modes")
        time.sleep(0.2)

    return result


def ensure_fetch_tables(conn: Any) -> None:
    """确保抓取结果所需的数据表和索引已经创建。

    Args:
        conn: 由 `db.connect()` 返回的数据库连接适配器。

    Returns:
        None: 仅执行建表与建索引，不返回业务数据。
    """

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


def save_mode_all_data(
    conn: Any,
    web_id: int,
    mode: dict[str, Any],
    all_data: list[dict[str, Any]],
    fetched_at: str,
) -> None:
    """保存单个 mode 的基础信息和全部历史记录。

    这里采用“先更新模式主表，再整批替换明细表”的策略：
    1. `fetched_modes` 使用主键冲突更新，始终保留最新模式信息
    2. `fetched_mode_records` 先删旧数据，再插入本次抓取的完整分页结果

    Args:
        conn: 数据库连接适配器。
        web_id: 当前站点编号。
        mode: 规整后的模式信息。
        all_data: 该模式对应的全部分页历史记录。
        fetched_at: 本次抓取时间，建议传入统一的 UTC ISO 时间字符串。

    Returns:
        None: 数据直接写入数据库，不返回额外结果。
    """

    modes_id = int(mode["modes_id"])
    conn.execute(
        """
        INSERT INTO fetched_modes (
            web_id, modes_id, title, payload_json, record_count, fetched_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(web_id, modes_id) DO UPDATE SET
            title = excluded.title,
            payload_json = excluded.payload_json,
            record_count = excluded.record_count,
            fetched_at = excluded.fetched_at
        """,
        (
            web_id,
            modes_id,
            mode.get("title", ""),
            json.dumps(mode.get("payload", mode), ensure_ascii=False),
            len(all_data),
            fetched_at,
        ),
    )

    # 分页接口返回的是完整历史记录，因此先清空该 mode 旧明细，再整体写回最新快照。
    conn.execute(
        """
        DELETE FROM fetched_mode_records
        WHERE web_id = ? AND modes_id = ?
        """,
        (web_id, modes_id),
    )

    rows: list[tuple[Any, ...]] = []
    for index, payload in enumerate(all_data):
        # 某些站点记录没有稳定主键时，退化为本次抓取内的顺序编号，确保联合主键可写入。
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
                web_id,
                modes_id,
                source_record_id,
                year,
                term,
                status,
                content,
                payload_json,
                fetched_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def fetch_all_data_for_mode(
    web_id: int,
    modes_id: int,
    base_url: str = MODES_DATA_URL,
    token: str | None = DEFAULT_TOKEN,
    limit: int = 250,
    request_delay: float = 0.5,
) -> list[dict[str, Any]]:
    """抓取单个 `modes_id` 的全部分页数据。

    Args:
        web_id: 当前站点编号。
        modes_id: 当前模式编号。
        base_url: 分页数据接口地址。
        token: 后台登录 token。
        limit: 每页拉取条数。
        request_delay: 相邻分页请求之间的等待秒数，用于降低接口压力。

    Returns:
        list[dict[str, Any]]: 该模式抓取到的全部历史记录列表。
        若中途接口报错，则返回已成功抓到的部分结果。
    """

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
            print(f"  web_id={web_id}, modes_id={modes_id}, page={page} 请求失败: {exc}")
            break
        except json.JSONDecodeError as exc:
            print(f"  web_id={web_id}, modes_id={modes_id}, page={page} JSON 解析失败: {exc}")
            break

        if result.get("code") != 0:
            print(f"  web_id={web_id}, modes_id={modes_id} API 返回错误: {result.get('msg')}")
            break

        current_page_data = result.get("data", [])
        if not current_page_data:
            break

        all_data.extend(current_page_data)
        total_count = int(result.get("count", 0) or 0)
        print(
            f"  web_id={web_id}, modes_id={modes_id}, page={page}: "
            f"{len(current_page_data)} 条，累计 {len(all_data)}/{total_count}"
        )

        # 一旦达到总数，或者当前页不足整页，说明已经抓到最后一页。
        if page * limit >= total_count or len(current_page_data) < limit:
            break

        page += 1
        time.sleep(request_delay)

    return all_data


def fetch_modes_data(
    db_path: str | Path = DEFAULT_DB_TARGET,
    start_web_id: int = 1,
    end_web_id: int = 22,
    token: str | None = DEFAULT_TOKEN,
    limit: int = 250,
    request_delay: float = 0.5,
) -> None:
    """按 `web_id -> modes_id` 抓取全部数据并保存到本地 PostgreSQL。

    Args:
        db_path: 数据库目标。默认使用项目配置中的 PostgreSQL DSN，
            也兼容显式传入其他 PostgreSQL DSN 或 SQLite 路径。
        start_web_id: 起始站点编号，包含本值。
        end_web_id: 结束站点编号，包含本值。
        token: 后台登录 token。
        limit: 分页接口每页条数。
        request_delay: 相邻分页请求间隔秒数。

    Returns:
        None: 直接将抓取结果写入数据库。
    """

    db_target = str(db_path)
    modes_by_web = fetch_web_id_list(start_web_id, end_web_id, token=token)
    fetched_at = datetime.now(timezone.utc).isoformat()

    with connect(db_target) as conn:
        ensure_fetch_tables(conn)

        for web_id in range(start_web_id, end_web_id + 1):
            modes_list = modes_by_web.get(web_id, [])
            if not modes_list:
                print(f"web_id={web_id} 没有可用的 modes_list，跳过。")
                continue

            for mode in modes_list:
                modes_id = int(mode["modes_id"])
                print(f"\n--- 正在处理 web_id={web_id}, modes_id={modes_id} ---")
                all_data = fetch_all_data_for_mode(
                    web_id=web_id,
                    modes_id=modes_id,
                    token=token,
                    limit=limit,
                    request_delay=request_delay,
                )
                save_mode_all_data(conn, web_id, mode, all_data, fetched_at)
                conn.commit()
                print(
                    f"已保存 web_id={web_id}, modes_id={modes_id}: "
                    f"{len(all_data)} 条记录 -> {db_target}"
                )


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。

    Returns:
        argparse.ArgumentParser: 配置好的命令行解析器实例。
    """

    parser = argparse.ArgumentParser(
        description=(
            "抓取指定 web_id 区间内的 modes_list 及其 all_data，"
            "并默认保存到本地 PostgreSQL 数据库。"
        )
    )
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_TARGET,
        help="数据库目标，可传 PostgreSQL DSN 或 SQLite 路径；默认使用本地 PostgreSQL DSN。",
    )
    parser.add_argument("--start-web-id", type=int, default=11, help="起始 web_id。")
    parser.add_argument("--end-web-id", type=int, default=21, help="结束 web_id。")
    parser.add_argument(
        "--token",
        default=DEFAULT_TOKEN,
        help="后台 token；传空字符串时不会附带 Cookie。",
    )
    parser.add_argument("--limit", type=int, default=250, help="分页接口的每页条数。")
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.5,
        help="分页请求之间的间隔秒数。",
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
    )
