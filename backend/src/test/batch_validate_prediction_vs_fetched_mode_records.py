"""
Batch-validate all modes_id entries in fetched_mode_records against
prediction module output structure, and write a summary report under
backend/src/test.

Examples:
    python backend/src/test/batch_validate_prediction_vs_fetched_mode_records.py
    python backend/src/test/batch_validate_prediction_vs_fetched_mode_records.py --type 3 --workers 4
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from tqdm import tqdm as _tqdm  # pyright: ignore[reportMissingImports]

    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False

    def _tqdm(iterable: Any, **_kwargs: Any) -> Any:
        return iterable


BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"
PREDICT_ROOT = SRC_ROOT / "predict"
TEST_DIR = SRC_ROOT / "test"

for path_item in (TEST_DIR, PREDICT_ROOT, SRC_ROOT):
    if str(path_item) not in sys.path:
        sys.path.insert(0, str(path_item))

from db import connect as db_connect  # noqa: E402
from validate_prediction_vs_fetched_mode_record import (  # noqa: E402
    DEFAULT_PREDICT_DB_PATH,
    DEFAULT_RECORDS_DB_PATH,
    safe_validate_prediction_vs_fetched_mode_record,
)


DEFAULT_WORKERS = min(multiprocessing.cpu_count(), 8)
REPORT_OUTPUT_PATH = TEST_DIR / "batch_prediction_vs_fetched_mode_records_report.json"
FORCED_LOTTERY_TYPE = 3
FORCED_WEB_ID = 4


def default_output_path() -> Path:
    return REPORT_OUTPUT_PATH


def load_modes_ids(
    records_db_path: str | Path,
    lottery_type: int | None = None,
    web_id: int | None = None,
    limit: int | None = None,
) -> list[int]:
    with db_connect(records_db_path) as conn:
        if not conn.table_exists("fetched_mode_records"):
            raise ValueError("Database does not contain fetched_mode_records table")

        sql_text = """
            SELECT DISTINCT modes_id
            FROM fetched_mode_records
        """
        params: list[Any] = []
        if web_id is not None:
            sql_text += " WHERE web_id = ?"
            params.append(web_id)
        sql_text += " ORDER BY CAST(modes_id AS INTEGER)"

        rows = conn.execute(sql_text, params).fetchall()
        modes_ids = [int(row["modes_id"]) for row in rows]

        if lottery_type is not None:
            filtered: list[int] = []
            for modes_id in modes_ids:
                sample_rows = conn.execute(
                    """
                    SELECT payload_json
                    FROM fetched_mode_records
                    WHERE modes_id = ?
                    ORDER BY CAST(year AS INTEGER) DESC, CAST(term AS INTEGER) DESC
                    LIMIT 50
                    """,
                    (modes_id,),
                ).fetchall()
                has_type = False
                for row in sample_rows:
                    payload = json.loads(str(row["payload_json"] or "{}"))
                    if str(payload.get("type", "")) == str(lottery_type):
                        has_type = True
                        break
                if has_type:
                    filtered.append(modes_id)
            modes_ids = filtered

        if limit is not None and limit > 0:
            modes_ids = modes_ids[:limit]

        return modes_ids


def _validate_one(payload: dict[str, Any]) -> dict[str, Any]:
    return safe_validate_prediction_vs_fetched_mode_record(
        modes_id=payload["modes_id"],
        lottery_type=payload["lottery_type"],
        web_id=payload["web_id"],
        predict_db_path=payload["predict_db_path"],
        records_db_path=payload["records_db_path"],
        res_code=payload["res_code"],
        output_json=None,
    )


def summarize_results(results: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"total": len(results), "ok": 0, "warn": 0, "error": 0}
    for item in results:
        status = str(item.get("status") or "error")
        if status not in summary:
            status = "error"
        summary[status] += 1
    return summary


def build_report(
    *,
    modes_ids: list[int],
    results: list[dict[str, Any]],
    lottery_type: int | None,
    web_id: int | None,
    predict_db_path: str | Path,
    records_db_path: str | Path,
    res_code: str,
    workers: int,
    limit: int | None,
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summarize_results(results),
        "parameters": {
            "modes_ids_count": len(modes_ids),
            "lottery_type": lottery_type,
            "web_id": web_id,
            "predict_db_path": str(predict_db_path),
            "records_db_path": str(records_db_path),
            "res_code": res_code,
            "workers": workers,
            "limit": limit,
        },
        "results": results,
    }


def save_report(report: dict[str, Any], output_json: str | Path) -> None:
    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file_obj:
        json.dump(report, file_obj, ensure_ascii=False, indent=2)


def print_report(report: dict[str, Any], output_json: str | Path) -> None:
    summary = report["summary"]
    params = report["parameters"]

    print("=" * 72)
    print("Batch Validation Report: prediction vs fetched_mode_records.payload_json")
    print("=" * 72)
    print(f"modes_ids_count: {params['modes_ids_count']}")
    print(f"lottery_type: {params['lottery_type']}")
    print(f"web_id: {params['web_id']}")
    print(f"predict_db_path: {params['predict_db_path']}")
    print(f"records_db_path: {params['records_db_path']}")
    print(f"workers: {params['workers']}")
    print("-" * 72)
    print(f"total: {summary['total']}")
    print(f"ok: {summary['ok']}")
    print(f"warn: {summary['warn']}")
    print(f"error: {summary['error']}")

    warn_items = [item for item in report["results"] if item.get("status") == "warn"]
    error_items = [item for item in report["results"] if item.get("status") == "error"]

    if warn_items:
        print("\nWarn modes:")
        for item in warn_items:
            params_item = item.get("parameters", {})
            print(
                f"  modes_id={params_item.get('modes_id')} "
                f"module={params_item.get('mechanism_key')} "
                f"message={item.get('message')}"
            )

    if error_items:
        print("\nError modes:")
        for item in error_items:
            params_item = item.get("parameters", {})
            print(
                f"  modes_id={params_item.get('modes_id')} "
                f"module={params_item.get('mechanism_key')} "
                f"message={next(iter(str(item.get('message') or '').splitlines()[-1:]), '')}"
            )

    print(f"\nReport saved: {output_json}")
    print("=" * 72)


def batch_validate_prediction_vs_fetched_mode_records(
    *,
    lottery_type: int | None = FORCED_LOTTERY_TYPE,
    web_id: int | None = FORCED_WEB_ID,
    predict_db_path: str | Path = DEFAULT_PREDICT_DB_PATH,
    records_db_path: str | Path = DEFAULT_RECORDS_DB_PATH,
    res_code: str = "",
    workers: int = DEFAULT_WORKERS,
    limit: int | None = None,
    output_json: str | Path | None = REPORT_OUTPUT_PATH,
) -> dict[str, Any]:
    lottery_type = FORCED_LOTTERY_TYPE
    web_id = FORCED_WEB_ID

    modes_ids = load_modes_ids(
        records_db_path,
        lottery_type=lottery_type,
        web_id=web_id,
        limit=limit,
    )
    tasks = [
        {
            "modes_id": modes_id,
            "lottery_type": lottery_type,
            "web_id": web_id,
            "predict_db_path": str(predict_db_path),
            "records_db_path": str(records_db_path),
            "res_code": res_code,
        }
        for modes_id in modes_ids
    ]

    results: list[dict[str, Any]] = []
    if tasks:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_map = {executor.submit(_validate_one, task): task["modes_id"] for task in tasks}
            pbar = _tqdm(
                as_completed(future_map),
                total=len(tasks),
                desc="validate",
                unit="mode",
                ncols=100,
            )
            for future in pbar:
                results.append(future.result())
            if hasattr(pbar, "close"):
                pbar.close()  # type: ignore[union-attr]

    results.sort(key=lambda item: int(item.get("parameters", {}).get("modes_id", 0)))
    report = build_report(
        modes_ids=modes_ids,
        results=results,
        lottery_type=lottery_type,
        web_id=web_id,
        predict_db_path=predict_db_path,
        records_db_path=records_db_path,
        res_code=res_code,
        workers=workers,
        limit=limit,
    )

    if output_json is not None:
        save_report(report, output_json)

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch-validate all modes_id entries against fetched_mode_records.payload_json using fixed filters type=3 and web_id=4"
    )
    parser.add_argument(
        "--type",
        type=int,
        default=FORCED_LOTTERY_TYPE,
        dest="lottery_type",
        help=f"Fixed filter type, must be {FORCED_LOTTERY_TYPE}",
    )
    parser.add_argument(
        "--web-id",
        type=int,
        default=FORCED_WEB_ID,
        help=f"Fixed filter web_id, must be {FORCED_WEB_ID}",
    )
    parser.add_argument(
        "--res-code",
        default="",
        help="Optional res_code override passed to predict() for every modes_id",
    )
    parser.add_argument(
        "--predict-db-path",
        default=str(DEFAULT_PREDICT_DB_PATH),
        help="Prediction source database path, defaults to PostgreSQL",
    )
    parser.add_argument(
        "--records-db-path",
        default=DEFAULT_RECORDS_DB_PATH,
        help="fetched_mode_records source database path",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Parallel worker count, default {DEFAULT_WORKERS}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for modes_id count, useful for smoke tests",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Batch report output path, defaults to backend/src/test",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        default=False,
        help="Disable progress bar",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.lottery_type != FORCED_LOTTERY_TYPE:
        raise SystemExit(f"该脚本当前强制要求 --type={FORCED_LOTTERY_TYPE}")
    if args.web_id != FORCED_WEB_ID:
        raise SystemExit(f"该脚本当前强制要求 --web-id={FORCED_WEB_ID}")

    global _tqdm, _HAS_TQDM
    if args.no_progress and _HAS_TQDM:
        _HAS_TQDM = False
        _tqdm = lambda iterable, **_kw: iterable  # type: ignore[assignment]

    output_json = Path(args.output_json) if args.output_json else default_output_path()
    report = batch_validate_prediction_vs_fetched_mode_records(
        lottery_type=args.lottery_type,
        web_id=args.web_id,
        predict_db_path=args.predict_db_path,
        records_db_path=args.records_db_path,
        res_code=args.res_code,
        workers=args.workers,
        limit=args.limit,
        output_json=output_json,
    )
    print_report(report, output_json)

    if report["summary"]["warn"] > 0 or report["summary"]["error"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
