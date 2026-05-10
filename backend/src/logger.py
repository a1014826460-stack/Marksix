"""
集中式日志系统 — 文件轮转存储 + 数据库错误持久化 + 自动清理。

功能：
- 结构化 JSON 格式日志输出到本地文件（按大小轮转）
- ERROR 及以上级别自动写入数据库 error_logs 表供后台检索
- 装饰器 @log_execution 自动记录函数耗时和异常
- 后台线程定期清理过期日志（按保留天数和总大小限制）
"""
from __future__ import annotations

import functools
import json
import logging
import os
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable

BACKEND_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = BACKEND_ROOT / "data" / "logs"

# ── 可配置常量 ──────────────────────────────────────────
MAX_FILE_SIZE = 10 * 1024 * 1024      # 单个日志文件最大 10 MB
BACKUP_COUNT = 10                      # 最多保留 10 个轮转文件
ERROR_RETENTION_DAYS = 30              # ERROR 级别数据库保留天数
WARN_RETENTION_DAYS = 7                # WARN 级别数据库保留天数
INFO_RETENTION_DAYS = 3                # INFO/DEBUG 级别数据库保留天数
MAX_TOTAL_LOG_SIZE_MB = 500            # 日志目录总大小上限
CLEANUP_INTERVAL_SECONDS = 3600        # 自动清理间隔（1 小时）

# ── 全局状态 ────────────────────────────────────────────
_initialized = False
_cleanup_thread: threading.Thread | None = None
_db_log_handler: "DatabaseLogHandler | None" = None
_db_path: str = ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class JsonFormatter(logging.Formatter):
    """将日志记录格式化为单行 JSON，便于机器解析和人工阅读。"""

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
        for attr in ("duration_ms", "user_id", "module", "req_params"):
            if hasattr(record, attr):
                val = getattr(record, attr)
                if val is not None:
                    payload[attr] = val
        return json.dumps(payload, ensure_ascii=False, default=str)


class DatabaseLogHandler(logging.Handler):
    """将 ERROR 及以上日志写入数据库 error_logs 表。"""

    def __init__(self, db_path: str):
        super().__init__(level=logging.ERROR)
        self._db_path = db_path

    def _ensure_table(self, conn) -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id              SERIAL PRIMARY KEY,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                level           TEXT NOT NULL DEFAULT 'ERROR',
                logger_name     TEXT NOT NULL DEFAULT '',
                module          TEXT NOT NULL DEFAULT '',
                func_name       TEXT NOT NULL DEFAULT '',
                file_path       TEXT NOT NULL DEFAULT '',
                line_number     INTEGER NOT NULL DEFAULT 0,
                message         TEXT NOT NULL DEFAULT '',
                exc_type        TEXT,
                exc_message     TEXT,
                stack_trace     TEXT,
                user_id         TEXT,
                request_params  TEXT,
                duration_ms     REAL,
                extra_data      TEXT
            )
        """)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            from db import connect
            with connect(self._db_path) as conn:
                self._ensure_table(conn)
                conn.execute(
                    """
                    INSERT INTO error_logs (
                        level, logger_name, module, func_name,
                        file_path, line_number, message,
                        exc_type, exc_message, stack_trace,
                        user_id, request_params, duration_ms
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.levelname,
                        getattr(record, "logger_name", record.name),
                        getattr(record, "module", ""),
                        record.funcName,
                        record.pathname,
                        record.lineno,
                        record.getMessage(),
                        type(record.exc_info[1]).__name__ if record.exc_info and record.exc_info[1] else None,
                        str(record.exc_info[1]) if record.exc_info and record.exc_info[1] else None,
                        "".join(traceback.format_exception(*record.exc_info)) if record.exc_info else None,
                        str(getattr(record, "user_id", "") or ""),
                        json.dumps(getattr(record, "req_params", None), ensure_ascii=False, default=str) if getattr(record, "req_params", None) else None,
                        float(getattr(record, "duration_ms", 0)) if getattr(record, "duration_ms", None) else None,
                    ),
                )
        except Exception:
            # 数据库写入失败不应中断主业务
            pass


def init_logging(db_path: str = "", *, level: int = logging.INFO) -> None:
    """初始化日志系统（幂等，多次调用只会执行一次）。

    :param db_path: 数据库连接字符串，用于 DatabaseLogHandler
    :param level: 文件日志最低级别
    """
    global _initialized, _db_log_handler, _db_path, _cleanup_thread
    if _initialized:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _db_path = str(db_path) if db_path else ""

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # 文件 Handler — 所有级别
    file_handler = RotatingFileHandler(
        str(LOG_DIR / "app.log"),
        maxBytes=MAX_FILE_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(JsonFormatter())
    root.addHandler(file_handler)

    # 控制台 Handler — INFO 及以上
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(JsonFormatter())
    root.addHandler(console)

    # 数据库 Handler — ERROR 及以上
    if _db_path:
        _db_log_handler = DatabaseLogHandler(_db_path)
        root.addHandler(_db_log_handler)

    _initialized = True

    # 启动自动清理线程
    _cleanup_thread = threading.Thread(target=_cleanup_loop, daemon=True, name="log-cleanup")
    _cleanup_thread.start()

    logging.getLogger("logger").info("Log system initialized: dir=%s, db=%s", LOG_DIR, bool(_db_path))


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 Logger 实例。"""
    if not _initialized:
        init_logging()
    return logging.getLogger(name)


# ── 装饰器 ──────────────────────────────────────────────

def log_execution(
    module: str = "",
    *,
    log_args: bool = False,
    log_result: bool = False,
):
    """装饰器：自动记录函数执行耗时和异常。

    :param module: 业务模块名称（如 'prediction', 'crawler'）
    :param log_args: 是否记录函数参数
    :param log_result: 是否记录返回值
    """
    def decorator(func: Callable) -> Callable:
        logger = get_logger(module or func.__module__)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            extra: dict[str, Any] = {"module": module}
            if log_args:
                extra["req_params"] = {"args": str(args)[:500], "kwargs": str(kwargs)[:500]}
            try:
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                extra["duration_ms"] = round(elapsed, 2)
                log_level = logging.WARNING if elapsed > 5000 else logging.DEBUG
                logger.log(log_level, "%s completed (%.1fms)", func.__name__, elapsed, extra=extra)
                if log_result:
                    extra["result"] = str(result)[:200]
                return result
            except Exception:
                elapsed = (time.perf_counter() - start) * 1000
                extra["duration_ms"] = round(elapsed, 2)
                logger.exception("%s failed (%.1fms)", func.__name__, elapsed, extra=extra)
                raise
        return wrapper
    return decorator


def log_context(**ctx: Any) -> logging.LoggerAdapter:
    """创建携带固定上下文的 LoggerAdapter。

    用法::

        logger = log_context(user_id="admin", module="prediction")
        logger.info("生成预测")
    """
    base = get_logger(ctx.get("module", "app"))
    return logging.LoggerAdapter(base, ctx)


# ── 自动清理 ────────────────────────────────────────────

def _cleanup_loop() -> None:
    """后台清理线程：定期删除过期日志。"""
    while True:
        time.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            _cleanup_expired_db_logs()
            _cleanup_oversized_log_files()
        except Exception:
            pass


def _cleanup_expired_db_logs() -> None:
    """删除数据库中过期的日志记录。"""
    if not _db_path:
        return
    try:
        from db import connect
        with connect(_db_path) as conn:
            now = datetime.now(timezone.utc)
            error_cutoff = (now - timedelta(days=ERROR_RETENTION_DAYS)).isoformat()
            warn_cutoff = (now - timedelta(days=WARN_RETENTION_DAYS)).isoformat()
            info_cutoff = (now - timedelta(days=INFO_RETENTION_DAYS)).isoformat()

            deleted = 0
            deleted += conn.execute(
                "DELETE FROM error_logs WHERE level = 'ERROR' AND created_at < %s", (error_cutoff,)
            ).rowcount
            deleted += conn.execute(
                "DELETE FROM error_logs WHERE level = 'WARNING' AND created_at < %s", (warn_cutoff,)
            ).rowcount
            deleted += conn.execute(
                "DELETE FROM error_logs WHERE level IN ('INFO', 'DEBUG') AND created_at < %s", (info_cutoff,)
            ).rowcount

            if deleted:
                logging.getLogger("logger.cleanup").info(
                    "Cleaned %d expired log rows (error>%dd, warn>%dd, info>%dd)",
                    deleted, ERROR_RETENTION_DAYS, WARN_RETENTION_DAYS, INFO_RETENTION_DAYS,
                )
    except Exception:
        pass


def _cleanup_oversized_log_files() -> None:
    """当日志目录总大小超过上限时，按时间从旧到新删除文件。"""
    try:
        total_size = sum(
            f.stat().st_size for f in LOG_DIR.iterdir() if f.is_file() and f.suffix in (".log", ".json")
        )
        max_bytes = MAX_TOTAL_LOG_SIZE_MB * 1024 * 1024
        if total_size <= max_bytes:
            return

        files = sorted(
            [f for f in LOG_DIR.iterdir() if f.is_file() and f.suffix in (".log", ".json")],
            key=lambda f: f.stat().st_mtime,
        )
        for f in files:
            if total_size <= max_bytes * 0.8:  # 清理到 80% 上限
                break
            try:
                size = f.stat().st_size
                f.unlink()
                total_size -= size
            except OSError:
                pass
        logging.getLogger("logger.cleanup").info(
            "Log directory cleanup completed, current size: %.1f MB", total_size / (1024 * 1024)
        )
    except Exception:
        pass


def trigger_cleanup() -> dict[str, Any]:
    """手动触发一次日志清理（供管理后台调用）。"""
    before_db = _count_db_logs()
    _cleanup_expired_db_logs()
    _cleanup_oversized_log_files()
    after_db = _count_db_logs()
    return {"db_deleted": before_db - after_db, "db_remaining": after_db}


def _count_db_logs() -> int:
    if not _db_path:
        return 0
    try:
        from db import connect
        with connect(_db_path) as conn:
            return int(conn.execute("SELECT COUNT(*) AS cnt FROM error_logs").fetchone()["cnt"] or 0)
    except Exception:
        return -1


# ── 日志查询 API 工具函数 ───────────────────────────────

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
) -> dict[str, Any]:
    """分页查询 error_logs 表。

    :returns: {"rows": [...], "total": int, "page": int, "page_size": int}
    """
    from db import connect

    filters: list[str] = []
    params: list[Any] = []

    if level:
        filters.append("level = %s")
        params.append(level.upper())
    if module:
        filters.append("module ILIKE %s")
        params.append(f"%{module}%")
    if keyword:
        filters.append("(message ILIKE %s OR exc_message ILIKE %s OR stack_trace ILIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
    if date_from:
        filters.append("created_at >= %s")
        params.append(date_from)
    if date_to:
        filters.append("created_at <= %s")
        params.append(date_to)

    where = (" WHERE " + " AND ".join(filters)) if filters else ""
    offset = max(0, (page - 1)) * page_size

    with connect(db_path) as conn:
        total = int(
            conn.execute(f"SELECT COUNT(*) AS cnt FROM error_logs{where}", params).fetchone()["cnt"] or 0
        )
        rows = conn.execute(
            f"SELECT * FROM error_logs{where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset],
        ).fetchall()

    return {
        "rows": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


def get_error_log_detail(db_path: str, log_id: int) -> dict[str, Any] | None:
    """获取单条错误日志的完整详情。"""
    from db import connect
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM error_logs WHERE id = %s", (log_id,)).fetchone()
        return dict(row) if row else None


def export_error_logs(db_path: str, **filters: Any) -> list[dict[str, Any]]:
    """导出错误日志（不分页，最多 5000 条）。"""
    from db import connect

    clauses: list[str] = []
    params: list[Any] = []
    for key, val in filters.items():
        if not val:
            continue
        if key == "level":
            clauses.append("level = %s")
            params.append(str(val).upper())
        elif key == "module":
            clauses.append("module ILIKE %s")
            params.append(f"%{val}%")
        elif key == "keyword":
            clauses.append("(message ILIKE %s OR exc_message ILIKE %s)")
            params.extend([f"%{val}%", f"%{val}%"])
        elif key == "date_from":
            clauses.append("created_at >= %s")
            params.append(str(val))
        elif key == "date_to":
            clauses.append("created_at <= %s")
            params.append(str(val))

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM error_logs{where} ORDER BY created_at DESC LIMIT 5000", params
        ).fetchall()
    return [dict(r) for r in rows]


def get_log_stats(db_path: str) -> dict[str, Any]:
    """获取日志统计摘要。"""
    from db import connect
    with connect(db_path) as conn:
        total = int(conn.execute("SELECT COUNT(*) AS cnt FROM error_logs").fetchone()["cnt"] or 0)
        by_level_rows = conn.execute(
            "SELECT level, COUNT(*) AS cnt FROM error_logs GROUP BY level ORDER BY cnt DESC"
        ).fetchall()
        recent = conn.execute(
            "SELECT COUNT(*) AS cnt FROM error_logs WHERE created_at >= NOW() - INTERVAL '24 hours'"
        ).fetchone()

        # 日志文件大小
        file_size_mb = 0.0
        file_count = 0
        if LOG_DIR.exists():
            for f in LOG_DIR.iterdir():
                if f.is_file() and f.suffix in (".log", ".json"):
                    file_size_mb += f.stat().st_size / (1024 * 1024)
                    file_count += 1

    return {
        "db_total_rows": total,
        "db_recent_24h": int(recent["cnt"] or 0) if recent else 0,
        "by_level": {str(r["level"]): int(r["cnt"]) for r in by_level_rows},
        "file_count": file_count,
        "file_size_mb": round(file_size_mb, 2),
        "log_dir": str(LOG_DIR),
    }
