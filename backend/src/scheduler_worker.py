"""Dedicated durable scheduler worker entrypoint.

Run this process separately from the HTTP API so timers and long-running work
cannot be duplicated by API replicas or interrupted by an HTTP restart.
"""

from __future__ import annotations

import argparse
import os
import signal
import socket
import threading
import time
import uuid
from pathlib import Path

from crawler.crawler_service import CrawlerScheduler
from db import DEFAULT_POSTGRES_DSN, detect_database_engine
from logger import init_logging
from runtime_environment import validate_runtime_database_target
from predict.mechanisms import ensure_prediction_configs_loaded
from tables import ensure_admin_tables
from app_http.startup_warnings import log_startup_risk_warnings
from domains.scheduler.service import (
    _task_poll_interval_seconds,
    _worker_lease_seconds,
    release_scheduler_worker_lease,
    renew_scheduler_worker_lease,
    try_acquire_scheduler_worker_lease,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Liuhecai durable scheduler worker.")
    parser.add_argument(
        "--db-path",
        "--db_path",
        dest="db_path",
        default=(
            os.environ.get("DATABASE_WRITE_URL", "").strip()
            or os.environ.get("DATABASE_URL", "").strip()
            or DEFAULT_POSTGRES_DSN
            or None
        ),
    )
    return parser


def start_lease_heartbeat(
    db_path: str | Path,
    *,
    holder_id: str,
    lease_seconds: int,
    interval_seconds: float | None = None,
) -> tuple[threading.Event, threading.Event, threading.Thread]:
    """Renew the leadership lease even while a scheduler task blocks the main thread."""
    stop_event = threading.Event()
    lease_lost = threading.Event()
    interval = interval_seconds if interval_seconds is not None else max(1.0, lease_seconds / 3)

    def run() -> None:
        while not stop_event.wait(interval):
            try:
                renewed = renew_scheduler_worker_lease(
                    db_path,
                    holder_id=holder_id,
                    lease_seconds=lease_seconds,
                )
            except Exception:
                renewed = False
            if not renewed:
                lease_lost.set()
                return

    thread = threading.Thread(target=run, name="scheduler-lease-heartbeat", daemon=True)
    thread.start()
    return stop_event, lease_lost, thread


def main() -> int:
    args = build_parser().parse_args()
    db_path = args.db_path
    if detect_database_engine(db_path) != "postgres":
        raise RuntimeError("调度 worker 正式运行仅支持 PostgreSQL。")
    validate_runtime_database_target(str(db_path))

    ensure_admin_tables(db_path)
    ensure_prediction_configs_loaded(db_path)
    init_logging(str(db_path))
    log_startup_risk_warnings()

    scheduler = CrawlerScheduler(db_path)
    stopping = False
    holder_id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:12]}"
    lease_seconds = _worker_lease_seconds(db_path)

    def stop(_signum, _frame) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    poll_seconds = _task_poll_interval_seconds(db_path)
    while not stopping:
        if try_acquire_scheduler_worker_lease(
            db_path,
            holder_id=holder_id,
            lease_seconds=lease_seconds,
        ):
            break
        time.sleep(poll_seconds)
    if stopping:
        return 0
    heartbeat_stop, lease_lost, heartbeat_thread = start_lease_heartbeat(
        db_path,
        holder_id=holder_id,
        lease_seconds=lease_seconds,
    )
    try:
        scheduler.start()
        while not stopping and not lease_lost.is_set():
            time.sleep(poll_seconds)
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=max(1.0, lease_seconds / 3 + 1))
        scheduler.stop()
        release_scheduler_worker_lease(db_path, holder_id=holder_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
