"""Compatibility facade for durable manual jobs and fetch-run persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from db import connect, utc_now
from tables import ensure_admin_tables


def start_background_job(*_args: Any, **_kwargs: Any) -> str:
    """Deprecated compatibility entrypoint; process-local jobs are disabled."""
    raise RuntimeError("后台任务必须使用持久化 scheduler job 类型入队")


def get_background_job(db_path: str | Path, job_id: str) -> dict[str, Any] | None:
    """查询后台任务状态。

    Args:
        job_id: 任务标识符。

    Returns:
        任务状态字典（含 status、result、metadata 等字段），
        不存在时返回 None。
    """
    from domains.scheduler.service import get_manual_job

    return get_manual_job(db_path, job_id)


def list_background_jobs() -> list[dict[str, Any]]:
    """列出所有后台任务（含运行中和已完成的）。"""
    return []


# ── 抓取运行记录 ──────────────────────────────────────


def create_fetch_run(db_path: str | Path, site_id: int) -> int:
    """创建一条抓取运行记录，返回 run_id。"""
    ensure_admin_tables(db_path)
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
    """更新抓取运行记录的状态和结果。"""
    ensure_admin_tables(db_path)
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


def list_fetch_runs(db_path: str | Path, limit: int = 20) -> list[dict[str, Any]]:
    """查询最近的抓取运行记录。"""
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
