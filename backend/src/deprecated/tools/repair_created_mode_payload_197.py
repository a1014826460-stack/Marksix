from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from db import connect  # noqa: E402
from utils.created_prediction_store import repair_three_period_special_created_rows  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="修复 created.mode_payload_197 中同一三期窗口 content 不一致的问题。"
    )
    parser.add_argument(
        "--db-path",
        default="postgresql://postgres:2225427@localhost:5432/liuhecai",
        help="数据库目标，可传 PostgreSQL DSN。",
    )
    parser.add_argument("--type", dest="lottery_type", default="3", help="按 type 过滤，默认 3。")
    parser.add_argument("--web", dest="web_value", default="4", help="按 web/web_id 过滤，默认 4。")
    parser.add_argument("--year", default="", help="可选：仅修复指定 year。")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    with connect(args.db_path) as conn:
        result = repair_three_period_special_created_rows(
            conn,
            "mode_payload_197",
            lottery_type=args.lottery_type or None,
            web_value=args.web_value or None,
            year=args.year or None,
        )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
