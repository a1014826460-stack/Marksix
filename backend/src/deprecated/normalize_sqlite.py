"""Deprecated compatibility wrapper for payload-table normalization.

正式运行的 mode_payload 拆表逻辑已经迁移到
`utils.normalize_payload_tables`，这里仅保留给历史脚本或旧导入路径使用。
文件名中的 `sqlite` 只是遗留名称，不再代表正式运行数据库依赖 SQLite。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from normalize_payload_tables import (  # noqa: E402
    DEFAULT_DB_TARGET,
    normalize_payload_tables,
    rebuild_mode_payload_metadata,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Deprecated wrapper. Use backend/src/utils/normalize_payload_tables.py "
            "for PostgreSQL runtime normalization."
        )
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_TARGET),
        help="数据库目标。正式运行默认使用 PostgreSQL；SQLite 仅限显式 legacy/test 用途。",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        default=False,
        help="Only rebuild mode_payload_tables metadata, keep existing mode_payload_* tables.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.metadata_only:
        rebuilt = rebuild_mode_payload_metadata(args.db_path)
        for modes_id, meta in rebuilt.items():
            print(
                f"rebuilt metadata for {modes_id}: {meta['title']} "
                f"(table={meta['table_name']}, rows={meta['record_count']}, "
                f"is_text={meta['is_text']}, is_image={meta['is_image']})"
            )
    else:
        normalize_payload_tables(args.db_path)


if __name__ == "__main__":
    main()
