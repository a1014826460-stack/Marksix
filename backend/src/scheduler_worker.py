"""Dedicated durable scheduler worker entrypoint.

Run this process separately from the HTTP API so timers and long-running work
cannot be duplicated by API replicas or interrupted by an HTTP restart.
"""

from __future__ import annotations

import argparse
import os
import signal
import socket
import time
import uuid
from pathlib import Path

from crawler.crawler_service import CrawlerScheduler
from db import DEFAULT_POSTGRES_DSN, detect_database_engine
from logger import init_logging
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
    parser.add_argument("--db-path", "--db_path", dest="db_path", default=DEFAULT_POSTGRES_DSN or None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    db_path = args.db_path
    if detect_database_engine(db_path) != "postgres":
        raise RuntimeError("调度 worker 正式运行仅支持 PostgreSQL。")

    ensure_prediction_configs_loaded(db_path)
    ensure_admin_tables(db_path)
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
    try:
        scheduler.start()
        while not stopping:
            time.sleep(poll_seconds)
            if not renew_scheduler_worker_lease(
                db_path,
                holder_id=holder_id,
                lease_seconds=lease_seconds,
            ):
                stopping = True
    finally:
        scheduler.stop()
        release_scheduler_worker_lease(db_path, holder_id=holder_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
