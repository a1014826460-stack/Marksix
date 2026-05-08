"""Compatibility wrapper for rebuilding text_history_mappings.

This project previously had two builders for `text_history_mappings`.
Keep this module as the app-facing entrypoint, but delegate to the
minimal-column rebuild required by the current PostgreSQL workflow.
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

from rebuild_text_mappings import (  # pyright: ignore[reportMissingImports]
    DEFAULT_DB_PATH,
    rebuild_text_history_mappings as _rebuild_text_history_mappings,
)


def build_text_history_mappings(
    db_path: str | Path = DEFAULT_DB_PATH,
    rebuild: bool = True,
) -> dict[str, Any]:
    del rebuild
    return _rebuild_text_history_mappings(str(db_path))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild text_history_mappings using the minimal text-only schema."
    )
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="PostgreSQL DSN")
    parser.add_argument(
        "--append",
        action="store_true",
        default=False,
        help="Ignored. The builder always recreates the mapping table.",
    )
    args = parser.parse_args()

    result = build_text_history_mappings(args.db_path, rebuild=not args.append)
    print(result)


if __name__ == "__main__":
    main()
