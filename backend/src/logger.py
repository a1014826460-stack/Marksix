"""Structured logging with file rotation, DB persistence, and cleanup."""

from __future__ import annotations

import functools
import json
import logging
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable

from db import auto_increment_primary_key, connect, utc_now
from runtime_config import get_config, get_config_from_conn

BACKEND_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = BACKEND_ROOT / "data" / "logs"

_initialized = False
_cleanup_thread: threading.Thread | None = None
_db_log_handler: "DatabaseLogHandler | None" = None
_db_path: str = ""
_runtime: dict[str, Any] = {
    "max_file_size_mb": 10,
    "backup_count": 10,
    "error_retention_days": 30,
    "warn_retention_days": 7,
    "info_retention_days": 3,
    "max_total_log_size_mb": 500,
    "cleanup_interval_seconds": 3600,
    "slow_call_warning_ms": 5000,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _load_runtime_settings(db_path: str = "") -> None:
    global _runtime
    if not db_path:
        return
    try:
        with connect(db_path) as conn:
            _runtime = {
                "max_file_size_mb": int(get_config_from_conn(conn, "logging.max_file_size_mb", 10)),
                "backup_count": int(get_config_from_conn(conn, "logging.backup_count", 10)),
                "error_retention_days": int(get_config_from_conn(conn, "logging.error_retention_days", 30)),
                "warn_retention_days": int(get_config_from_conn(conn, "logging.warn_retention_days", 7)),
                "info_retention_days": int(get_config_from_conn(conn, "logging.info_retention_days", 3)),
                "max_total_log_size_mb": int(get_config_from_conn(conn, "logging.max_total_log_size_mb", 500)),
                "cleanup_interval_seconds": int(get_config_from_conn(conn, "logging.cleanup_interval_seconds", 3600)),
                "slow_call_warning_ms": int(get_config_from_conn(conn, "logging.slow_call_warning_ms", 5000)),
            }
    except Exception:
        pass


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": _utc_now(),
            "level": record.levelname,
            "logger": record.name,
            "file": f"{record.pathname}:{record.lineno}",
            "func": record.funcName,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            payload["exc_type"] = type(record.exc_info[1]).__name__
            payload["exc_msg"] = str(record.exc_info[1])
            payload["stack"] = traceback.format_exception(*record.exc_info)
        for attr in (
            "duration_ms", "user_id", "module", "req_params", "result",
            "site_id", "web_id", "lottery_type_id", "year", "term",
            "task_key", "task_type", "request_path", "request_method",
        ):
            if hasattr(record, attr):
                value = getattr(record, attr)
                if value is not None and value != "" and value != 0:
                    payload[attr] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


class DatabaseLogHandler(logging.Handler):
    def __init__(self, db_path: str):
        super().__init__(level=logging.ERROR)
        self._db_path = db_path

    def _ensure_table(self, conn: Any) -> None:
        pk_sql = auto_increment_primary_key("id", conn.engine)
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS error_logs (
                {pk_sql},
                created_at TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'ERROR',
                logger_name TEXT NOT NULL DEFAULT '',
                module TEXT NOT NULL DEFAULT '',
                func_name TEXT NOT NULL DEFAULT '',
                file_path TEXT NOT NULL DEFAULT '',
                line_number INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                exc_type TEXT,
                exc_message TEXT,
                stack_trace TEXT,
                user_id TEXT,
                request_params TEXT,
                duration_ms REAL,
                extra_data TEXT
            )
            """
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            with connect(self._db_path) as conn:
                self._ensure_table(conn)
                conn.execute(
                    """
                    INSERT INTO error_logs (
                        created_at, level, logger_name, module, func_name,
                        file_path, line_number, message, exc_type, exc_message,
                        stack_trace, user_id, request_params, duration_ms, extra_data,
                        site_id, web_id, lottery_type_id, year, term,
                        task_key, task_type, request_path, request_method
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        utc_now(),
                        record.levelname,
                        record.name,
                        str(getattr(record, "module", "") or ""),
                        record.funcName,
                        record.pathname,
                        record.lineno,
                        record.getMessage(),
                        type(record.exc_info[1]).__name__ if record.exc_info and record.exc_info[1] else None,
                        str(record.exc_info[1]) if record.exc_info and record.exc_info[1] else None,
                        "".join(traceback.format_exception(*record.exc_info)) if record.exc_info else None,
                        str(getattr(record, "user_id", "") or ""),
                        json.dumps(getattr(record, "req_params", None), ensure_ascii=False, default=str)
                        if getattr(record, "req_params", None) is not None
                        else None,
                        float(getattr(record, "duration_ms", 0)) if getattr(record, "duration_ms", None) is not None else None,
                        json.dumps(getattr(record, "result", None), ensure_ascii=False, default=str)
                        if getattr(record, "result", None) is not None
                        else None,
                        # 业务上下文字段 — 从 logging.LogRecord extra 中读取
                        int(getattr(record, "site_id", 0)) if getattr(record, "site_id", None) is not None else None,
                        int(getattr(record, "web_id", 0)) if getattr(record, "web_id", None) is not None else None,
                        int(getattr(record, "lottery_type_id", 0)) if getattr(record, "lottery_type_id", None) is not None else None,
                        int(getattr(record, "year", 0)) if getattr(record, "year", None) is not None else None,
                        int(getattr(record, "term", 0)) if getattr(record, "term", None) is not None else None,
                        str(getattr(record, "task_key", "") or ""),
                        str(getattr(record, "task_type", "") or ""),
                        str(getattr(record, "request_path", "") or ""),
                        str(getattr(record, "request_method", "") or ""),
                    ),
                )
        except Exception:
            pass


def init_logging(db_path: str = "", *, level: int = logging.INFO) -> None:
    global _initialized, _db_log_handler, _db_path, _cleanup_thread
    if _initialized:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _db_path = str(db_path or "")
    _load_runtime_settings(_db_path)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler(
        str(LOG_DIR / "app.log"),
        maxBytes=max(1, int(_runtime["max_file_size_mb"])) * 1024 * 1024,
        backupCount=max(1, int(_runtime["backup_count"])),
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(JsonFormatter())
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(JsonFormatter())
    root.addHandler(console)

    if _db_path:
        _db_log_handler = DatabaseLogHandler(_db_path)
        root.addHandler(_db_log_handler)

    _initialized = True
    _cleanup_thread = threading.Thread(target=_cleanup_loop, daemon=True, name="log-cleanup")
    _cleanup_thread.start()
    logging.getLogger("logger").info("Log system initialized: dir=%s db=%s", LOG_DIR, bool(_db_path))


def get_logger(name: str) -> logging.Logger:
    if not _initialized:
        init_logging()
    return logging.getLogger(name)


def log_execution(
    module: str = "",
    *,
    log_args: bool = False,
    log_result: bool = False,
):
    def decorator(func: Callable) -> Callable:
        logger = get_logger(module or func.__module__)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            extra: dict[str, Any] = {"module": module or func.__module__}
            if log_args:
                extra["req_params"] = {"args": str(args)[:500], "kwargs": str(kwargs)[:500]}
            try:
                result = func(*args, **kwargs)
                elapsed = round((time.perf_counter() - start) * 1000, 2)
                extra["duration_ms"] = elapsed
                if log_result:
                    extra["result"] = str(result)[:200]
                threshold_ms = int(_runtime.get("slow_call_warning_ms", 5000) or 5000)
                log_level = logging.WARNING if elapsed >= threshold_ms else logging.DEBUG
                logger.log(log_level, "%s completed (%.1fms)", func.__name__, elapsed, extra=extra)
                return result
            except Exception:
                elapsed = round((time.perf_counter() - start) * 1000, 2)
                extra["duration_ms"] = elapsed
                logger.exception("%s failed (%.1fms)", func.__name__, elapsed, extra=extra)
                raise

        return wrapper

    return decorator


def log_context(**ctx: Any) -> logging.LoggerAdapter:
    return logging.LoggerAdapter(get_logger(ctx.get("module", "app")), ctx)


def _cleanup_loop() -> None:
    while True:
        time.sleep(max(60, int(_runtime.get("cleanup_interval_seconds", 3600) or 3600)))
        try:
            _cleanup_expired_db_logs()
            _cleanup_oversized_log_files()
        except Exception:
            pass


def _cleanup_expired_db_logs() -> None:
    if not _db_path:
        return
    try:
        now = datetime.now(timezone.utc)
        error_cutoff = (now - timedelta(days=int(_runtime.get("error_retention_days", 30)))).isoformat()
        warn_cutoff = (now - timedelta(days=int(_runtime.get("warn_retention_days", 7)))).isoformat()
        info_cutoff = (now - timedelta(days=int(_runtime.get("info_retention_days", 3)))).isoformat()
        with connect(_db_path) as conn:
            conn.execute("DELETE FROM error_logs WHERE level = ? AND created_at < ?", ("ERROR", error_cutoff))
            conn.execute("DELETE FROM error_logs WHERE level = ? AND created_at < ?", ("WARNING", warn_cutoff))
            conn.execute("DELETE FROM error_logs WHERE level IN ('INFO', 'DEBUG') AND created_at < ?", (info_cutoff,))
    except Exception:
        pass


def _cleanup_oversized_log_files() -> None:
    try:
        max_bytes = max(1, int(_runtime.get("max_total_log_size_mb", 500) or 500)) * 1024 * 1024
        files = [f for f in LOG_DIR.iterdir() if f.is_file() and f.suffix in (".log", ".json")]
        total_size = sum(f.stat().st_size for f in files)
        if total_size <= max_bytes:
            return
        for file_path in sorted(files, key=lambda item: item.stat().st_mtime):
            if total_size <= int(max_bytes * 0.8):
                break
            try:
                size = file_path.stat().st_size
                file_path.unlink()
                total_size -= size
            except OSError:
                pass
    except Exception:
        pass


def trigger_cleanup() -> dict[str, Any]:
    before_db = _count_db_logs()
    _cleanup_expired_db_logs()
    _cleanup_oversized_log_files()
    after_db = _count_db_logs()
    return {"db_deleted": max(0, before_db - after_db), "db_remaining": after_db}


def _count_db_logs() -> int:
    if not _db_path:
        return 0
    try:
        with connect(_db_path) as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM error_logs").fetchone()
            return int(row["cnt"] or 0)
    except Exception:
        return -1


def query_error_logs(
    db_path: str,
    *,
    page: int = 1,
    page_size: int = 30,
    level: str = "",
    module: str = "",
    keyword: str = "",
    date_from: str = "",
    date_to: str = "",
    user_id: str = "",
    site_id: str = "",
    web_id: str = "",
    lottery_type_id: str = "",
    year: str = "",
    term: str = "",
    task_type: str = "",
    task_key: str = "",
    path: str = "",
) -> dict[str, Any]:
    """查询错误日志，支持按业务维度（站点、彩种、期号、任务等）筛选。"""
    filters: list[str] = []
    params: list[Any] = []
    engine = ""

    with connect(db_path) as conn:
        engine = conn.engine
        if level:
            filters.append("level = ?")
            params.append(level.upper())
        if module:
            clause = "module ILIKE ?" if engine == "postgres" else "LOWER(module) LIKE LOWER(?)"
            filters.append(clause)
            params.append(f"%{module}%")
        if keyword:
            clause = (
                "(message ILIKE ? OR exc_message ILIKE ? OR stack_trace ILIKE ?)"
                if engine == "postgres"
                else "(LOWER(message) LIKE LOWER(?) OR LOWER(exc_message) LIKE LOWER(?) OR LOWER(stack_trace) LIKE LOWER(?))"
            )
            filters.append(clause)
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        if date_from:
            filters.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            filters.append("created_at <= ?")
            params.append(date_to)
        # ── 业务维度筛选 ──
        if user_id:
            filters.append("user_id = ?")
            params.append(user_id)
        if site_id:
            filters.append("site_id = ?")
            params.append(int(site_id))
        if web_id:
            filters.append("web_id = ?")
            params.append(int(web_id))
        if lottery_type_id:
            filters.append("lottery_type_id = ?")
            params.append(int(lottery_type_id))
        if year:
            filters.append("year = ?")
            params.append(int(year))
        if term:
            filters.append("term = ?")
            params.append(int(term))
        if task_type:
            clause = "task_type ILIKE ?" if engine == "postgres" else "LOWER(task_type) LIKE LOWER(?)"
            filters.append(clause)
            params.append(f"%{task_type}%")
        if task_key:
            clause = "task_key ILIKE ?" if engine == "postgres" else "LOWER(task_key) LIKE LOWER(?)"
            filters.append(clause)
            params.append(f"%{task_key}%")
        if path:
            clause = "request_path ILIKE ?" if engine == "postgres" else "LOWER(request_path) LIKE LOWER(?)"
            filters.append(clause)
            params.append(f"%{path}%")

        where = (" WHERE " + " AND ".join(filters)) if filters else ""
        offset = max(0, page - 1) * page_size
        total = int(conn.execute(f"SELECT COUNT(*) AS cnt FROM error_logs{where}", params).fetchone()["cnt"] or 0)
        rows = conn.execute(
            f"SELECT * FROM error_logs{where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    # 获取可用的 level 和 module 列表（用于前端下拉筛选）
    available_levels: list[str] = []
    available_modules: list[str] = []
    try:
        with connect(db_path) as conn:
            lv_rows = conn.execute("SELECT DISTINCT level FROM error_logs ORDER BY level").fetchall()
            available_levels = [str(r["level"]) for r in lv_rows]
            mod_rows = conn.execute("SELECT DISTINCT module FROM error_logs WHERE module != '' ORDER BY module").fetchall()
            available_modules = [str(r["module"]) for r in mod_rows]
    except Exception:
        pass

    return {
        "items": [_serialize_row(row) for row in rows],
        "rows": [_serialize_row(row) for row in rows],  # 向后兼容旧字段名
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "available_levels": available_levels,
        "available_modules": available_modules,
    }


def get_error_log_detail(db_path: str, log_id: int) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM error_logs WHERE id = ?", (log_id,)).fetchone()
        return _serialize_row(row) if row else None


def export_error_logs(db_path: str, **filters: Any) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    with connect(db_path) as conn:
        engine = conn.engine
        for key, value in filters.items():
            if not value:
                continue
            if key == "level":
                clauses.append("level = ?")
                params.append(str(value).upper())
            elif key == "module":
                clauses.append("module ILIKE ?" if engine == "postgres" else "LOWER(module) LIKE LOWER(?)")
                params.append(f"%{value}%")
            elif key == "keyword":
                clauses.append(
                    "(message ILIKE ? OR exc_message ILIKE ?)"
                    if engine == "postgres"
                    else "(LOWER(message) LIKE LOWER(?) OR LOWER(exc_message) LIKE LOWER(?))"
                )
                params.extend([f"%{value}%", f"%{value}%"])
            elif key == "date_from":
                clauses.append("created_at >= ?")
                params.append(str(value))
            elif key == "date_to":
                clauses.append("created_at <= ?")
                params.append(str(value))
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM error_logs{where} ORDER BY created_at DESC LIMIT 5000",
            params,
        ).fetchall()
        return [_serialize_row(row) for row in rows]


def _serialize_row(row: Any) -> dict[str, Any]:
    """将数据库行转为 JSON 可序列化的字典，处理 datetime 等非标准类型。"""
    result: dict[str, Any] = {}
    for key, value in dict(row).items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, bytes):
            result[key] = value.decode("utf-8", errors="replace")
        else:
            result[key] = value
    return result


def get_log_modules(db_path: str) -> list[str]:
    """返回 error_logs 表中所有已记录的模块名，供前端下拉筛选使用。"""
    try:
        with connect(db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT module FROM error_logs WHERE module != '' ORDER BY module"
            ).fetchall()
            return [str(r["module"]) for r in rows]
    except Exception:
        return []


def get_log_levels(db_path: str) -> list[str]:
    """返回 error_logs 表中所有已记录的日志等级，供前端下拉筛选使用。"""
    try:
        with connect(db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT level FROM error_logs ORDER BY level"
            ).fetchall()
            return [str(r["level"]) for r in rows]
    except Exception:
        return []


def get_log_stats(db_path: str) -> dict[str, Any]:
    with connect(db_path) as conn:
        total = int(conn.execute("SELECT COUNT(*) AS cnt FROM error_logs").fetchone()["cnt"] or 0)
        by_level_rows = conn.execute(
            "SELECT level, COUNT(*) AS cnt FROM error_logs GROUP BY level ORDER BY cnt DESC"
        ).fetchall()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        recent = conn.execute(
            "SELECT COUNT(*) AS cnt FROM error_logs WHERE created_at >= ?",
            (cutoff,),
        ).fetchone()

    file_size_mb = 0.0
    file_count = 0
    if LOG_DIR.exists():
        for file_path in LOG_DIR.iterdir():
            if file_path.is_file() and file_path.suffix in (".log", ".json"):
                file_size_mb += file_path.stat().st_size / (1024 * 1024)
                file_count += 1

    return {
        "db_total_rows": total,
        "db_recent_24h": int(recent["cnt"] or 0) if recent else 0,
        "by_level": {str(row["level"]): int(row["cnt"]) for row in by_level_rows},
        "file_count": file_count,
        "file_size_mb": round(file_size_mb, 2),
        "log_dir": str(LOG_DIR),
    }
