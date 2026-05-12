"""后台任务处理器：内存任务管理、抓取/生成调度。

从 routes/common.py 中提取，供 routes 和 scheduler 层复用。
"""

from __future__ import annotations

import secrets
import threading
from pathlib import Path
from typing import Any, Callable

from db import connect, utc_now
from tables import ensure_admin_tables


# ── 内存后台任务存储 ──────────────────────────────────

_background_jobs: dict[str, dict[str, Any]] = {}
_background_jobs_lock = threading.Lock()


def start_background_job(
    target: Callable[..., Any],
    *args: Any,
    metadata: dict[str, Any] | None = None,
    **kwargs: Any,
) -> str:
    """启动一个后台线程任务，返回 job_id 供后续轮询。

    Args:
        target: 要在后台线程中执行的函数。
        *args: 传递给 target 的位置参数。
        metadata: 任务上下文字典，应包含 site_id、web_id、
                  lottery_type_id、task_type 等关键字段。
        **kwargs: 传递给 target 的关键字参数。

    Returns:
        job_id: 唯一的任务标识符（16 位 hex 字符串）。
    """
    job_id = secrets.token_hex(8)
    with _background_jobs_lock:
        _background_jobs[job_id] = {
            "status": "running",
            "started_at": utc_now(),
            "result": None,
            "metadata": dict(metadata or {}),
        }

    def _run() -> None:
        try:
            result = target(*args, **kwargs)
            with _background_jobs_lock:
                _background_jobs[job_id]["status"] = "done"
                _background_jobs[job_id]["result"] = result
        except Exception as exc:
            with _background_jobs_lock:
                _background_jobs[job_id]["status"] = "error"
                _background_jobs[job_id]["error"] = str(exc)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return job_id


def get_background_job(job_id: str) -> dict[str, Any] | None:
    """查询后台任务状态。

    Args:
        job_id: 任务标识符。

    Returns:
        任务状态字典（含 status、result、metadata 等字段），
        不存在时返回 None。
    """
    with _background_jobs_lock:
        job = _background_jobs.get(job_id)
        return dict(job) if job else None


def list_background_jobs() -> list[dict[str, Any]]:
    """列出所有后台任务（含运行中和已完成的）。"""
    with _background_jobs_lock:
        return [
            {"job_id": job_id, **dict(data)}
            for job_id, data in _background_jobs.items()
        ]


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
