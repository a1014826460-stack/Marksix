from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from crawler import postgres_backup


def _backup_config(values: dict[str, object]):
    return lambda _db_path, key, fallback: values.get(key, fallback)


def test_backup_rejects_insufficient_disk_space_before_running_pg_dump(tmp_path, monkeypatch):
    monkeypatch.setattr(postgres_backup, "backup_enabled", lambda _db_path: True)
    monkeypatch.setattr(postgres_backup, "_backup_dir", lambda _db_path: tmp_path)
    monkeypatch.setattr(
        postgres_backup,
        "_build_pg_dump_command",
        lambda *_args: (["pg_dump"], {}, "liuhecai"),
    )
    monkeypatch.setattr(
        postgres_backup,
        "_cfg",
        _backup_config({"database.backup_min_free_space_mb": 2}),
    )
    monkeypatch.setattr(
        postgres_backup.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(free=1024 * 1024),
    )
    run = monkeypatch.setattr(postgres_backup.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("pg_dump must not run"))

    with pytest.raises(RuntimeError, match="insufficient free space"):
        postgres_backup.run_postgres_backup("postgresql://postgres@localhost/liuhecai")


def test_backup_times_out_and_removes_partial_dump(tmp_path, monkeypatch):
    output_paths: list[Path] = []
    monkeypatch.setattr(postgres_backup, "backup_enabled", lambda _db_path: True)
    monkeypatch.setattr(postgres_backup, "_backup_dir", lambda _db_path: tmp_path)
    monkeypatch.setattr(
        postgres_backup,
        "_build_pg_dump_command",
        lambda _db_path, output_path: (["pg_dump", "-f", str(output_path)], {}, "liuhecai"),
    )
    monkeypatch.setattr(
        postgres_backup,
        "_cfg",
        _backup_config({"database.backup_timeout_seconds": 42, "database.backup_min_free_space_mb": 0}),
    )
    monkeypatch.setattr(postgres_backup.shutil, "disk_usage", lambda _path: SimpleNamespace(free=10**12))

    def timeout(command, **kwargs):
        output_path = Path(command[-1])
        output_paths.append(output_path)
        output_path.write_bytes(b"partial")
        assert kwargs["timeout"] == 42
        raise subprocess.TimeoutExpired(command, 42)

    monkeypatch.setattr(postgres_backup.subprocess, "run", timeout)

    with pytest.raises(RuntimeError, match="timed out after 42s"):
        postgres_backup.run_postgres_backup("postgresql://postgres@localhost/liuhecai")

    assert output_paths and not output_paths[0].exists()


def test_backup_verifies_archive_and_returns_sha256_checksum(tmp_path, monkeypatch):
    calls: list[tuple[list[str], dict[str, object]]] = []
    payload = b"verified-backup"
    monkeypatch.setattr(postgres_backup, "backup_enabled", lambda _db_path: True)
    monkeypatch.setattr(postgres_backup, "_backup_dir", lambda _db_path: tmp_path)
    monkeypatch.setattr(
        postgres_backup,
        "_build_pg_dump_command",
        lambda _db_path, output_path: (["pg_dump", "-f", str(output_path)], {}, "liuhecai"),
    )
    monkeypatch.setattr(
        postgres_backup,
        "_cfg",
        _backup_config(
            {
                "database.backup_timeout_seconds": 60,
                "database.backup_verify_timeout_seconds": 30,
                "database.backup_min_free_space_mb": 0,
                "database.pg_restore_path": "pg_restore",
            }
        ),
    )
    monkeypatch.setattr(postgres_backup.shutil, "disk_usage", lambda _path: SimpleNamespace(free=10**12))
    monkeypatch.setattr(postgres_backup.shutil, "which", lambda executable: executable)
    monkeypatch.setattr(postgres_backup, "cleanup_old_backups", lambda *_args: 0)

    def run(command, **kwargs):
        calls.append((list(command), kwargs))
        if command[0] == "pg_dump":
            Path(command[-1]).write_bytes(payload)
        return SimpleNamespace(returncode=0, stdout="archive entries", stderr="")

    monkeypatch.setattr(postgres_backup.subprocess, "run", run)

    result = postgres_backup.run_postgres_backup("postgresql://postgres@localhost/liuhecai")

    assert result["sha256"] == hashlib.sha256(payload).hexdigest()
    assert result["archive_verified"] is True
    assert calls[1][0][:2] == ["pg_restore", "--list"]
    assert calls[1][1]["timeout"] == 30


def test_scheduler_worker_receives_the_durable_backup_mount():
    from pathlib import Path

    compose = (Path(__file__).resolve().parents[4] / "docker-compose.yml").read_text(encoding="utf-8")
    api_block = compose.split("  python-api:", 1)[1].split("\n  scheduler-worker:", 1)[0]
    worker_block = compose.split("  scheduler-worker:", 1)[1].split("\n  db-migrate:", 1)[0]

    assert "${BACKUP_DIR:-./backend/data/backups}:/app/data/backups" in worker_block
    assert "${BACKUP_DIR:-./backend/data/backups}:/app/data/backups" not in api_block
