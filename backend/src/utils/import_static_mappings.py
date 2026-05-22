"""CLI script for importing static JSON mapping tables into PostgreSQL."""

from __future__ import annotations

import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.errors import AppError  # pyright: ignore[reportMissingImports]
from domains.static_mappings.service import (  # pyright: ignore[reportMissingImports]
    build_import_argument_parser,
    import_static_mappings,
    load_import_config,
)


def main() -> int:
    """Run static mapping import from CLI."""

    parser = build_import_argument_parser()
    args = parser.parse_args()

    try:
        config = load_import_config(
            config_path=args.config,
            db_target=args.db_target,
            db_host=args.db_host,
            db_port=args.db_port,
            db_name=args.db_name,
            db_user=args.db_user,
            db_password=args.db_password,
            incremental=bool(args.incremental),
        )
        reports = import_static_mappings(config)
    except AppError as exc:
        print(json.dumps(exc.to_dict(), ensure_ascii=False), file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive CLI fallback
        print(
            json.dumps(
                {
                    "error": True,
                    "code": "STATIC_MAPPING_IMPORT_UNEXPECTED",
                    "message": str(exc),
                    "status": 500,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            [
                {
                    "dataset": report.dataset,
                    "table_name": report.table_name,
                    "total_rows": report.total_rows,
                    "inserted_rows": report.inserted_rows,
                    "updated_rows": report.updated_rows,
                    "failed_rows": report.failed_rows,
                    "replaced": report.replaced,
                }
                for report in reports
            ],
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
