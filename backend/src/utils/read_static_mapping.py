"""CLI and reusable helpers for reading PostgreSQL static mapping tables."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.errors import AppError  # pyright: ignore[reportMissingImports]
from domains.static_mappings.service import (  # pyright: ignore[reportMissingImports]
    MappingReader,
    build_reader_argument_parser,
    load_import_config,
)


def _build_reader(config_path: str | Path | None = None, db_target: str | None = None) -> MappingReader:
    config = load_import_config(config_path=config_path, db_target=db_target, incremental=True)
    return MappingReader(
        db_target=config.db_target,
        schema_name=config.schema_name,
        dataset_table_map={dataset.name: dataset.table_name for dataset in config.datasets},
    )


def get_mapping(
    path: str,
    *,
    dataset_name: str | None = None,
    config_path: str | Path | None = None,
    db_target: str | None = None,
    db_host: str | None = None,
    db_port: str | None = None,
    db_name: str | None = None,
    db_user: str | None = None,
    db_password: str | None = None,
) -> dict[str, Any]:
    """Get one mapping row by logical path."""

    config = load_import_config(
        config_path=config_path,
        db_target=db_target,
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
        incremental=True,
    )
    with MappingReader(
        db_target=config.db_target,
        schema_name=config.schema_name,
        dataset_table_map={dataset.name: dataset.table_name for dataset in config.datasets},
    ) as reader:
        if dataset_name:
            return reader.get_mapping(dataset_name, path)
        return reader.get_mapping_by_path(path)


def get_mappings(
    paths: list[str],
    *,
    dataset_name: str | None = None,
    config_path: str | Path | None = None,
    db_target: str | None = None,
    db_host: str | None = None,
    db_port: str | None = None,
    db_name: str | None = None,
    db_user: str | None = None,
    db_password: str | None = None,
) -> list[dict[str, Any]]:
    """Get multiple mapping rows by logical path."""

    config = load_import_config(
        config_path=config_path,
        db_target=db_target,
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
        incremental=True,
    )
    with MappingReader(
        db_target=config.db_target,
        schema_name=config.schema_name,
        dataset_table_map={dataset.name: dataset.table_name for dataset in config.datasets},
    ) as reader:
        if dataset_name:
            return reader.batch_get_mappings(dataset_name, paths)
        return reader.batch_get_mappings_by_path(paths)


def main() -> int:
    """Run static mapping read from CLI."""

    parser = build_reader_argument_parser()
    args = parser.parse_args()

    try:
        if args.path:
            result: Any = get_mapping(
                args.path,
                dataset_name=args.dataset or None,
                config_path=args.config,
                db_target=args.db_target,
                db_host=args.db_host,
                db_port=args.db_port,
                db_name=args.db_name,
                db_user=args.db_user,
                db_password=args.db_password,
            )
        else:
            result = get_mappings(
                list(args.paths),
                dataset_name=args.dataset or None,
                config_path=args.config,
                db_target=args.db_target,
                db_host=args.db_host,
                db_port=args.db_port,
                db_name=args.db_name,
                db_user=args.db_user,
                db_password=args.db_password,
            )
    except AppError as exc:
        print(json.dumps(exc.to_dict(), ensure_ascii=False), file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive CLI fallback
        print(
            json.dumps(
                {
                    "error": True,
                    "code": "STATIC_MAPPING_READ_UNEXPECTED",
                    "message": str(exc),
                    "status": 500,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
