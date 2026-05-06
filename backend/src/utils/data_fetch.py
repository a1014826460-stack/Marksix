import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from db import connect
import config as app_config


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BACKEND_ROOT / "data" / "lottery_modes.sqlite3"

# Load site configuration from config.yaml
_cfg = app_config.section("site")
WEB_MANAGE_URL_TEMPLATE = _cfg.get("manage_url_template",
    "https://admin.shengshi8800.com/ds67BvM/web/webManage?id={web_id}")
MODES_DATA_URL = _cfg.get("modes_data_url",
    "https://admin.shengshi8800.com/ds67BvM/web/getModesDataList")
DEFAULT_TOKEN = _cfg.get("default_token", "")


def build_headers(token: str | None = DEFAULT_TOKEN) -> dict[str, str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    if token:
        headers["Cookie"] = f"token={token}"
    return headers


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def parse_js_modes_list(html: str) -> list[dict[str, Any]]:
    match = re.search(r"let\s+modes\s*=\s*(\[\s*\{.*?\}\s*\]);", html, re.DOTALL)
    if not match:
        return []

    js_obj = match.group(1)
    json_str = re.sub(r"([,{]\s*)([A-Za-z_]\w*)\s*:", r'\1"\2":', js_obj)
    json_str = json_str.replace("'", '"')
    parsed = json.loads(json_str)
    return parsed if isinstance(parsed, list) else []


def normalize_mode(raw_mode: dict[str, Any], web_id: int) -> dict[str, Any] | None:
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
    end_web_id: int = 10,
    url_template: str = WEB_MANAGE_URL_TEMPLATE,
    token: str | None = DEFAULT_TOKEN,
) -> dict[int, list[dict[str, Any]]]:
    """遍历站点 id=1..10，返回每个站点的 modes_list。"""
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
            print(f"web_id={web_id} 请求出错: {exc}")
            result[web_id] = []
            continue
        except json.JSONDecodeError as exc:
            print(f"web_id={web_id} modes_list 解析出错: {exc}")
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

    conn.execute(
        """
        DELETE FROM fetched_mode_records
        WHERE web_id = ? AND modes_id = ?
        """,
        (web_id, modes_id),
    )

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
            print(f"  web_id={web_id}, modes_id={modes_id}, page={page} 请求出错: {exc}")
            break
        except json.JSONDecodeError as exc:
            print(f"  web_id={web_id}, modes_id={modes_id}, page={page} JSON 解析出错: {exc}")
            break

        if result.get("code") != 0:
            print(
                f"  web_id={web_id}, modes_id={modes_id} API 返回错误: {result.get('msg')}"
            )
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

        if page * limit >= total_count or len(current_page_data) < limit:
            break

        page += 1
        time.sleep(request_delay)

    return all_data


def fetch_modes_data(
    db_path: str | Path = DEFAULT_DB_PATH,
    start_web_id: int = 1,
    end_web_id: int = 10,
    token: str | None = DEFAULT_TOKEN,
    limit: int = 250,
    request_delay: float = 0.5,
) -> None:
    """按 web_id -> modes_id 抓取 all_data，并保存到本地 SQLite。"""
    modes_by_web = fetch_web_id_list(start_web_id, end_web_id, token=token)
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()

    with connect(db_path) as conn:
        ensure_fetch_tables(conn)

        for web_id in range(start_web_id, end_web_id + 1):
            modes_list = modes_by_web.get(web_id, [])
            if not modes_list:
                print(f"web_id={web_id} 没有 modes_list，跳过。")
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
                    f"{len(all_data)} 条记录 -> {db_path}"
                )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="抓取 web_id=1..10 的 modes_list 与 all_data，并按站点和 modes_id 保存到 SQLite。"
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="SQLite 数据库路径。")
    parser.add_argument("--start-web-id", type=int, default=1, help="起始 web_id。")
    parser.add_argument("--end-web-id", type=int, default=10, help="结束 web_id。")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="后台 token；传空字符串可不带 Cookie。")
    parser.add_argument("--limit", type=int, default=250, help="分页 limit。")
    parser.add_argument("--request-delay", type=float, default=0.5, help="分页请求间隔秒数。")
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
