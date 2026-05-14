from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from alerts.alert_service import alert_prediction_gap
from crawler.scheduler import _run_auto_prediction


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run daily prediction generation in a separate process.")
    parser.add_argument("--db-path", "--db_path", dest="db_path", required=True, help="Database target.")
    parser.add_argument("--lottery-type-id", dest="lottery_type_id", type=int, required=True, help="Lottery type id.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    db_path = str(Path(args.db_path)) if "://" not in str(args.db_path) else str(args.db_path)
    _run_auto_prediction._worker_mode = True

    _run_auto_prediction(db_path, int(args.lottery_type_id))

    try:
        alert_prediction_gap(db_path)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
