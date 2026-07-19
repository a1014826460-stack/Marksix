"""PostgreSQL logical backup runner for scheduler tasks."""

from __future__ import annotations

import hashlib
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
PG_DUMP_HINT = (
    "pg_dump not found. Install postgresql-client in the container "
    "(apt-get install -y postgresql-client) or set system_config "
    "database.pg_dump_path to an absolute path."
)


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
        raise RuntimeError(PG_DUMP_HINT)

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


def _timeout_seconds(db_path: str | Path, key: str, fallback: int) -> int:
    try:
        return max(1, int(_cfg(db_path, key, fallback)))
    except (TypeError, ValueError):
        return fallback


def _ensure_backup_space(db_path: str | Path, backup_dir: Path) -> None:
    try:
        minimum_mb = max(0, int(_cfg(db_path, "database.backup_min_free_space_mb", 1024)))
    except (TypeError, ValueError):
        minimum_mb = 1024
    required_bytes = minimum_mb * 1024 * 1024
    available_bytes = shutil.disk_usage(backup_dir).free
    if available_bytes < required_bytes:
        raise RuntimeError(
            "PostgreSQL backup aborted: insufficient free space "
            f"({available_bytes} bytes available, {required_bytes} bytes required)"
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_backup_archive(db_path: str | Path, output_path: Path, env: dict[str, str]) -> None:
    configured = str(_cfg(db_path, "database.pg_restore_path", "pg_restore")).strip() or "pg_restore"
    pg_restore = shutil.which(configured)
    if pg_restore is None:
        raise RuntimeError(
            "pg_restore not found. Install postgresql-client or set system_config "
            "database.pg_restore_path to an absolute path."
        )
    timeout_seconds = _timeout_seconds(db_path, "database.backup_verify_timeout_seconds", 60)
    try:
        completed = subprocess.run(
            [pg_restore, "--list", str(output_path)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"pg_restore verification timed out after {timeout_seconds}s") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or f"exit code {completed.returncode}").strip()
        raise RuntimeError(f"pg_restore verification failed: {detail}")


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
    _ensure_backup_space(db_path, backup_dir)

    timestamp = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    probe_output = backup_dir / "probe.dump"
    command, env, db_name = _build_pg_dump_command(db_path, probe_output)
    output_path = backup_dir / f"{_safe_database_name(db_name)}_{timestamp}.dump"
    command[-1] = str(output_path)

    _logger.info("PostgreSQL backup starting: database=%s output=%s", db_name, output_path)
    timeout_seconds = _timeout_seconds(db_path, "database.backup_timeout_seconds", 900)
    try:
        completed = subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        try:
            output_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise RuntimeError(f"pg_dump timed out after {timeout_seconds}s") from exc
    if completed.returncode != 0:
        try:
            output_path.unlink(missing_ok=True)
        except Exception:
            pass
        detail = (completed.stderr or completed.stdout or f"exit code {completed.returncode}").strip()
        raise RuntimeError(f"pg_dump failed: {detail}")

    try:
        _verify_backup_archive(db_path, output_path, env)
    except Exception:
        try:
            output_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise

    removed = cleanup_old_backups(db_path, backup_dir, db_name)
    size_bytes = output_path.stat().st_size
    checksum = _sha256_file(output_path)
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
        "sha256": checksum,
        "archive_verified": True,
        "cleanup_removed": removed,
        "payload": payload or {},
    }
