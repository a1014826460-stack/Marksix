"""routes 共享工具 —— 兼容导出入口。

后台任务管理、抓取运行逻辑已迁移到 jobs/ 包。
本文件保留向后兼容的导出。
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

from admin.crud import get_site
from crawler.crawler_service import crawl_and_generate_for_type
from db import connect, utc_now
from jobs.handlers import (  # noqa: F401 - 兼容导出
    start_background_job,
    get_background_job,
    create_fetch_run,
    finish_fetch_run,
    list_fetch_runs,
)
from tables import ensure_admin_tables
from utils.build_text_history_mappings import build_text_history_mappings
from utils.normalize_payload_tables import normalize_payload_tables


def crawl_and_generate(db_path: str | Path, lottery_type_id: int) -> dict[str, Any]:
    return crawl_and_generate_for_type(db_path, lottery_type_id)


def create_fetch_run(db_path: str | Path, site_id: int) -> int:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            INSERT INTO site_fetch_runs (site_id, status, message, started_at)
            VALUES (?, 'running', '', ?)
            RETURNING id
            """,
            (site_id, utc_now()),
        ).fetchone()
        return int(row["id"])


def finish_fetch_run(
    db_path: str | Path,
    run_id: int,
    status: str,
    message: str,
    modes_count: int,
    records_count: int,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE site_fetch_runs
            SET status = ?,
                message = ?,
                modes_count = ?,
                records_count = ?,
                finished_at = ?
            WHERE id = ?
            """,
            (status, message, modes_count, records_count, utc_now(), run_id),
        )


def _load_data_fetch_exports() -> tuple[Any, Any, Any, Any]:
    try:
        module = import_module("utils.data_fetch")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "utils.data_fetch 模块当前不存在，站点抓取接口暂不可用。"
        ) from exc
    return (
        module.ensure_fetch_tables,
        module.fetch_all_data_for_mode,
        module.fetch_web_id_list,
        module.save_mode_all_data,
    )


def fetch_site_data(
    db_path: str | Path,
    site_id: int,
    *,
    normalize_after: bool = True,
    build_text_mappings_after: bool = True,
) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    site = get_site(db_path, site_id, include_secret=True)
    if not site["enabled"]:
        raise ValueError("该站点已禁用，不能执行抓取")
    ensure_fetch_tables, fetch_all_data_for_mode, fetch_web_id_list, save_mode_all_data = _load_data_fetch_exports()

    run_id = create_fetch_run(db_path, site_id)
    modes_count = 0
    records_count = 0
    try:
        modes_by_web = fetch_web_id_list(
            start_web_id=int(site["start_web_id"]),
            end_web_id=int(site["end_web_id"]),
            url_template=str(site["manage_url_template"]),
            token=str(site.get("token") or "") or None,
        )
        fetched_at = utc_now()
        with connect(db_path) as conn:
            ensure_fetch_tables(conn)
            for web_id in range(int(site["start_web_id"]), int(site["end_web_id"]) + 1):
                for mode in modes_by_web.get(web_id, []):
                    all_data = fetch_all_data_for_mode(
                        web_id=web_id,
                        modes_id=int(mode["modes_id"]),
                        base_url=str(site["modes_data_url"]),
                        token=str(site.get("token") or "") or None,
                        limit=int(site["request_limit"]),
                        request_delay=float(site["request_delay"]),
                    )
                    save_mode_all_data(conn, web_id, mode, all_data, fetched_at)
                    conn.commit()
                    modes_count += 1
                    records_count += len(all_data)

        post_process: dict[str, Any] = {}
        if normalize_after:
            post_process["normalized_tables"] = len(normalize_payload_tables(db_path))
        if build_text_mappings_after:
            post_process["text_mappings"] = build_text_history_mappings(db_path, rebuild=True)

        message = "抓取完成"
        finish_fetch_run(db_path, run_id, "success", message, modes_count, records_count)
        return {
            "run_id": run_id,
            "status": "success",
            "message": message,
            "modes_count": modes_count,
            "records_count": records_count,
            "post_process": post_process,
        }
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        finish_fetch_run(db_path, run_id, "failed", message, modes_count, records_count)
        raise


def list_fetch_runs(db_path: str | Path, limit: int = 20) -> list[dict[str, Any]]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT r.*, s.name AS site_name
            FROM site_fetch_runs r
            LEFT JOIN managed_sites s ON s.id = r.site_id
            ORDER BY r.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
