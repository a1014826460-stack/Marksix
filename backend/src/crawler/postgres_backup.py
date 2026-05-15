"""PostgreSQL logical backup runner for scheduler tasks."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from db import is_postgres_target
from runtime_config import get_config

_logger = logging.getLogger("database.backup")

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _cfg(db_path: str | Path, key: str, fallback: Any) -> Any:
    try:
        return get_config(db_path, key, fallback)
    except Exception:
        return fallback


def _parse_times(raw: Any) -> list[str]:
    if isinstance(raw, list):
        values = raw
    else:
        values = str(raw or "").split(",")
    result: list[str] = []
    for item in values:
        text = str(item).strip()
        if re.fullmatch(r"\d{1,2}:\d{2}", text):
            hour, minute = text.split(":", 1)
            h = int(hour)
            m = int(minute)
            if 0 <= h <= 23 and 0 <= m <= 59:
                result.append(f"{h:02d}:{m:02d}")
    return result or ["00:00", "11:00"]


def configured_backup_times(db_path: str | Path) -> list[str]:
    return _parse_times(_cfg(db_path, "database.backup_times", ["00:00", "11:00"]))


def backup_enabled(db_path: str | Path) -> bool:
    value = _cfg(db_path, "database.backup_enabled", True)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _backup_dir(db_path: str | Path) -> Path:
    raw = str(_cfg(db_path, "database.backup_dir", "data/backups")).strip()
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path


def _safe_database_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())
    return cleaned or "database"


def _dsn_parts(dsn: str) -> dict[str, str]:
    parsed = urlparse(dsn)
    db_name = unquote(parsed.path.lstrip("/"))
    return {
        "host": unquote(parsed.hostname or "localhost"),
        "port": str(parsed.port or 5432),
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": db_name,
    }


def _build_pg_dump_command(db_path: str | Path, output_path: Path) -> tuple[list[str], dict[str, str], str]:
    dsn = str(db_path)
    if not is_postgres_target(dsn):
        raise RuntimeError("PostgreSQL backup requires a PostgreSQL DSN")

    parts = _dsn_parts(dsn)
    db_name = parts["database"]
    if not db_name:
        raise RuntimeError("PostgreSQL DSN does not include a database name")

    pg_dump_cfg = str(_cfg(db_path, "database.pg_dump_path", "pg_dump")).strip() or "pg_dump"
    pg_dump = shutil.which(pg_dump_cfg)
    if pg_dump is None:
        # 在 Docker / 常见 Linux 环境中搜索 pg_dump
        for candidate in (
            "/usr/bin/pg_dump",
            "/usr/local/bin/pg_dump",
            "/usr/lib/postgresql/16/bin/pg_dump",
            "/usr/lib/postgresql/15/bin/pg_dump",
            "/usr/lib/postgresql/14/bin/pg_dump",
        ):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                pg_dump = candidate
                break
    if pg_dump is None:
        raise RuntimeError(
            "pg_dump 未找到。请在容器中安装 postgresql-client "
            "(apt-get install -y postgresql-client) "
            "或在 system_config 中设置 database.pg_dump_path 为绝对路径。"
        )
    command = [
        pg_dump,
        "-h",
        parts["host"],
        "-p",
        parts["port"],
        "-U",
        parts["user"] or "postgres",
        "-d",
        db_name,
        "-Fc",
        "-f",
        str(output_path),
    ]
    env = os.environ.copy()
    if parts["password"]:
        env["PGPASSWORD"] = parts["password"]
    return command, env, db_name


def cleanup_old_backups(db_path: str | Path, backup_dir: Path, db_name: str) -> int:
    retention_days = max(1, int(_cfg(db_path, "database.backup_retention_days", 30)))
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    prefix = f"{_safe_database_name(db_name)}_"
    removed = 0
    for path in backup_dir.glob(f"{prefix}*.dump"):
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                path.unlink()
                removed += 1
        except Exception as exc:
            _logger.warning("Failed to cleanup old backup %s: %s", path, exc)
    return removed


def send_backup_failure_alert(
    db_path: str | Path,
    *,
    error_message: str,
    attempt_no: int,
    final: bool,
) -> None:
    from alerts.email_service import send_alert_async

    status = "最终失败" if final else "失败，将重试"
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    _logger.error("PostgreSQL backup %s on attempt %s: %s", status, attempt_no, error_message)
    send_alert_async(
        db_path,
        subject=f"[Liuhecai Backup] PostgreSQL backup {status}",
        body_html=f"""
        <h2>PostgreSQL 数据库备份{status}</h2>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse">
            <tr><td><b>Attempt</b></td><td>{attempt_no}</td></tr>
            <tr><td><b>Final</b></td><td>{'yes' if final else 'no'}</td></tr>
            <tr><td><b>Error</b></td><td><pre>{error_message}</pre></td></tr>
            <tr><td><b>Time</b></td><td>{now_str}</td></tr>
        </table>
        """,
    )


def run_postgres_backup(db_path: str | Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not backup_enabled(db_path):
        _logger.info("PostgreSQL backup disabled by database.backup_enabled")
        return {"status": "disabled"}

    backup_dir = _backup_dir(db_path)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    probe_output = backup_dir / "probe.dump"
    command, env, db_name = _build_pg_dump_command(db_path, probe_output)
    output_path = backup_dir / f"{_safe_database_name(db_name)}_{timestamp}.dump"
    command[-1] = str(output_path)

    _logger.info("PostgreSQL backup starting: database=%s output=%s", db_name, output_path)
    completed = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        try:
            output_path.unlink(missing_ok=True)
        except Exception:
            pass
        detail = (completed.stderr or completed.stdout or f"exit code {completed.returncode}").strip()
        raise RuntimeError(f"pg_dump failed: {detail}")

    removed = cleanup_old_backups(db_path, backup_dir, db_name)
    size_bytes = output_path.stat().st_size
    _logger.info(
        "PostgreSQL backup completed: file=%s size=%d cleanup_removed=%d",
        output_path,
        size_bytes,
        removed,
    )
    return {
        "status": "ok",
        "database": db_name,
        "path": str(output_path),
        "size_bytes": size_bytes,
        "cleanup_removed": removed,
        "payload": payload or {},
    }
