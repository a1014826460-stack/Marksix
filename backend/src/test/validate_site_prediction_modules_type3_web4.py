"""校验 public.site_prediction_modules 中启用模块的生成机制。

校验口径：
1. 读取 PostgreSQL `public.site_prediction_modules` 中启用的模块。
2. 为每个 `mechanism_key` 找到对应预测配置与 `mode_id/default_modes_id`。
3. 优先从 `public.mode_payload_{mode_id}` 读取 `type=3 + web_id=4` 的最新样本。
4. 若没有 `web_id=4` 样本，则回退到同表其他 `web_id` 的 `type=3` 最新样本。
5. 调用真实 `predict()` 生成数据。
6. 对比生成结果与数据库样本的业务字段结构，重点保留 `content` 字段的数据库样本和生成样本。

注意：
1. 这里判断的“是否正确”是指生成结果是否与历史数据结构兼容，不要求预测文本与历史文本逐字相等。
2. 报告中会明确记录实际用于校验的 `web_id`，以及是否发生了回退。
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"
PREDICT_ROOT = SRC_ROOT / "predict"
TEST_DIR = SRC_ROOT / "test"

for path_item in (TEST_DIR, PREDICT_ROOT, SRC_ROOT):
    if str(path_item) not in sys.path:
        sys.path.insert(0, str(path_item))

from common import predict  # noqa: E402
from db import connect as db_connect  # noqa: E402
from mechanisms import (  # noqa: E402
    PREDICTION_CONFIGS,
    build_title_prediction_configs,
    get_prediction_config,
)
from validate_prediction_vs_fetched_mode_record import (  # noqa: E402
    BASE_KEYS,
    IGNORED_KEYS,
    build_shape_fingerprint,
    normalize_generated_content,
    strip_ignored_keys,
)


DEFAULT_DB_PATH = "postgresql://postgres:2225427@localhost:5432/liuhecai"
FORCED_LOTTERY_TYPE = 3
PREFERRED_WEB_ID = 4
REPORT_OUTPUT_PATH = TEST_DIR / "site_prediction_modules_type3_web4_report.json"


def quote_identifier(name: str) -> str:
    """安全引用表名或列名。"""
    return '"' + str(name).replace('"', '""') + '"'


def refresh_prediction_configs(db_path: str | Path) -> None:
    """刷新动态预测配置。"""
    PREDICTION_CONFIGS.update(build_title_prediction_configs(db_path))


def load_enabled_site_modules(db_path: str | Path) -> list[dict[str, Any]]:
    """读取启用中的站点预测模块，并按 mechanism_key 去重。"""
    with db_connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT mechanism_key, mode_id, site_id, sort_order, status
            FROM site_prediction_modules
            WHERE COALESCE(status, 0) = 1
            ORDER BY sort_order, id
            """
        ).fetchall()

    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row["mechanism_key"] or "").strip()
        if not key:
            continue
        entry = grouped.setdefault(
            key,
            {
                "mechanism_key": key,
                "mode_id": int(row["mode_id"] or 0) if row.get("mode_id") is not None else None,
                "site_ids": [],
                "sort_order": int(row["sort_order"] or 0),
            },
        )
        if entry.get("mode_id") in (None, 0) and row.get("mode_id") is not None:
            entry["mode_id"] = int(row["mode_id"] or 0)
        site_id = int(row["site_id"] or 0)
        if site_id not in entry["site_ids"]:
            entry["site_ids"].append(site_id)

    return sorted(grouped.values(), key=lambda item: (item["sort_order"], item["mechanism_key"]))


def build_order_clause(columns: set[str]) -> str:
    """构建按最新样本优先的排序语句。"""
    order_parts: list[str] = []
    if "year" in columns:
        order_parts.append("CAST(year AS INTEGER) DESC")
    if "term" in columns:
        order_parts.append("CAST(term AS INTEGER) DESC")
    if "source_record_id" in columns:
        order_parts.append(
            "CAST(COALESCE(NULLIF(CAST(source_record_id AS TEXT), ''), '0') AS INTEGER) DESC"
        )
    elif "id" in columns:
        order_parts.append(
            "CAST(COALESCE(NULLIF(CAST(id AS TEXT), ''), '0') AS INTEGER) DESC"
        )
    return f" ORDER BY {', '.join(order_parts)}" if order_parts else ""


def load_mode_payload_sample(
    db_path: str | Path,
    table_name: str,
) -> dict[str, Any] | None:
    """优先读取 type=3 + web_id=4 的最新样本；缺失时回退到其他 web_id。"""
    with db_connect(db_path) as conn:
        if not conn.table_exists(table_name):
            return None

        columns = set(conn.table_columns(table_name))
        if "type" not in columns:
            return None

        web_columns = [column_name for column_name in ("web_id", "web") if column_name in columns]
        order_clause = build_order_clause(columns)

        available_web_ids: list[int] = []
        if web_columns:
            web_expr = "COALESCE(" + ", ".join(
                f"CAST({quote_identifier(column_name)} AS INTEGER)"
                for column_name in web_columns
            ) + ")"
            rows = conn.execute(
                f"""
                SELECT DISTINCT {web_expr} AS sample_web_id
                FROM {quote_identifier(table_name)}
                WHERE CAST(type AS INTEGER) = ?
                  AND {web_expr} IS NOT NULL
                ORDER BY sample_web_id
                """,
                (FORCED_LOTTERY_TYPE,),
            ).fetchall()
            available_web_ids = [
                int(row["sample_web_id"])
                for row in rows
                if row["sample_web_id"] is not None
            ]

        candidate_web_ids: list[int | None] = [PREFERRED_WEB_ID]
        candidate_web_ids.extend(web_id for web_id in available_web_ids if web_id != PREFERRED_WEB_ID)
        if not web_columns:
            candidate_web_ids = [None]

        for candidate_web_id in candidate_web_ids:
            filters = ["CAST(type AS INTEGER) = ?"]
            params: list[Any] = [FORCED_LOTTERY_TYPE]
            if candidate_web_id is not None and web_columns:
                filters.append(
                    "(" + " OR ".join(
                        f"CAST({quote_identifier(column_name)} AS INTEGER) = ?"
                        for column_name in web_columns
                    ) + ")"
                )
                params.extend([candidate_web_id] * len(web_columns))

            row = conn.execute(
                f"""
                SELECT *
                FROM {quote_identifier(table_name)}
                WHERE {' AND '.join(filters)}
                {order_clause}
                LIMIT 1
                """,
                params,
            ).fetchone()
            if row:
                return {
                    "row": dict(row),
                    "selected_web_id": candidate_web_id,
                    "preferred_web_id": PREFERRED_WEB_ID,
                    "used_fallback_web_id": candidate_web_id not in (None, PREFERRED_WEB_ID),
                    "available_web_ids": available_web_ids,
                    "table_name": table_name,
                    "lottery_type": FORCED_LOTTERY_TYPE,
                }

    return None


def build_sample_for_comparison(sample_row: dict[str, Any]) -> dict[str, Any]:
    """将数据库样本裁剪为可比较结构。"""
    sample: dict[str, Any] = {}
    for key in BASE_KEYS:
        if key in sample_row:
            sample[key] = sample_row[key]
    for key, value in sample_row.items():
        if key in sample or key in IGNORED_KEYS:
            continue
        sample[key] = value
    return sample


def build_generated_sample(
    prediction_result: dict[str, Any],
    sample_row: dict[str, Any],
) -> dict[str, Any]:
    """按历史样本结构归一化生成结果。"""
    comparable_sample = build_sample_for_comparison(sample_row)
    generated: dict[str, Any] = {}

    for key in BASE_KEYS:
        if key in comparable_sample:
            generated[key] = comparable_sample[key]

    generated.update(
        normalize_generated_content(
            prediction_result["prediction"]["content"],
            comparable_sample,
        )
    )
    return generated


def build_content_preview(value: Any) -> dict[str, Any]:
    """构建 content 字段预览，方便看数据形态。"""
    parsed_value = value
    parsed_type = type(value).__name__
    if isinstance(value, str):
        text = value.strip()
        if text[:1] in {"[", "{"}:
            try:
                parsed_value = json.loads(text)
                parsed_type = type(parsed_value).__name__
            except json.JSONDecodeError:
                parsed_value = value
                parsed_type = "str"
    return {
        "raw": value,
        "raw_type": type(value).__name__,
        "parsed_type": parsed_type,
        "parsed": parsed_value,
    }


def compare_content_fields(
    database_sample: dict[str, Any],
    generated_sample: dict[str, Any],
) -> dict[str, Any]:
    """对比数据库样本与生成结果中的业务字段，重点关注 content 相关字段。"""
    database_keys = {
        key for key in database_sample.keys()
        if key not in BASE_KEYS and key not in IGNORED_KEYS
    }
    generated_keys = {
        key for key in generated_sample.keys()
        if key not in BASE_KEYS and key not in IGNORED_KEYS
    }
    field_names = sorted(database_keys | generated_keys)

    return {
        "database_keys": sorted(database_keys),
        "generated_keys": sorted(generated_keys),
        "matched_keys": sorted(database_keys & generated_keys),
        "missing_in_generated": sorted(database_keys - generated_keys),
        "extra_in_generated": sorted(generated_keys - database_keys),
        "field_previews": {
            key: {
                "database": build_content_preview(database_sample.get(key)),
                "generated": build_content_preview(generated_sample.get(key)),
            }
            for key in field_names
        },
    }


def validate_one_site_module(
    db_path: str | Path,
    module_entry: dict[str, Any],
) -> dict[str, Any]:
    """校验单个站点模块的生成机制。"""
    mechanism_key = str(module_entry["mechanism_key"])
    report: dict[str, Any] = {
        "mechanism_key": mechanism_key,
        "site_ids": list(module_entry.get("site_ids") or []),
        "status": "error",
        "message": "",
        "config": {},
        "comparison": {},
    }

    try:
        config = get_prediction_config(mechanism_key)
        table_name = str(config.default_table or f"mode_payload_{config.default_modes_id}")
        sample_info = load_mode_payload_sample(db_path, table_name)
        if sample_info is None:
            report["status"] = "skip"
            report["message"] = (
                f"未找到 {table_name} 中可用于校验的 type={FORCED_LOTTERY_TYPE} 样本数据"
            )
            report["config"] = {
                "title": config.title,
                "mode_id": int(module_entry.get("mode_id") or config.default_modes_id),
                "default_modes_id": int(config.default_modes_id),
                "default_table": table_name,
            }
            return report

        sample_row = dict(sample_info["row"])
        res_code = str(sample_row.get("res_code") or "").strip()
        prediction_result = predict(
            config=config,
            res_code=res_code or "01,02,03,04,05,06,07",
            db_path=db_path,
        )

        payload_sample = build_sample_for_comparison(sample_row)
        generated_sample = build_generated_sample(prediction_result, sample_row)

        payload_comparable = strip_ignored_keys(payload_sample)
        generated_comparable = strip_ignored_keys(generated_sample)
        payload_fingerprint = build_shape_fingerprint(payload_comparable)
        generated_fingerprint = build_shape_fingerprint(generated_comparable)
        matched = payload_fingerprint == generated_fingerprint

        selected_web_id = sample_info.get("selected_web_id")
        used_fallback = bool(sample_info.get("used_fallback_web_id"))

        report["status"] = "ok" if matched else "warn"
        if matched:
            if used_fallback:
                report["message"] = "生成机制与数据库样本结构一致，但当前使用了非 web_id=4 的回退样本"
            else:
                report["message"] = "生成机制与数据库样本结构一致"
        else:
            report["message"] = "生成机制与数据库样本结构不一致"

        report["config"] = {
            "title": config.title,
            "mode_id": int(module_entry.get("mode_id") or config.default_modes_id),
            "default_modes_id": int(config.default_modes_id),
            "default_table": table_name,
        }
        report["comparison"] = {
            "matched": matched,
            "lottery_type": FORCED_LOTTERY_TYPE,
            "preferred_web_id": PREFERRED_WEB_ID,
            "selected_web_id": selected_web_id,
            "used_fallback_web_id": used_fallback,
            "available_web_ids": sample_info.get("available_web_ids") or [],
            "payload_fingerprint": payload_fingerprint,
            "generated_fingerprint": generated_fingerprint,
            "sample_record": {
                "year": str(sample_row.get("year") or ""),
                "term": str(sample_row.get("term") or ""),
                "res_code": str(sample_row.get("res_code") or ""),
            },
            "content_comparison": compare_content_fields(payload_sample, generated_sample),
            "database_sample": payload_sample,
            "generated_sample": generated_sample,
        }
        return report
    except Exception:
        report["status"] = "error"
        report["message"] = traceback.format_exc()
        return report


def summarize_results(results: list[dict[str, Any]]) -> dict[str, int]:
    """汇总校验结果计数。"""
    summary = {"total": len(results), "ok": 0, "warn": 0, "error": 0, "skip": 0}
    for item in results:
        status = str(item.get("status") or "error")
        if status not in summary:
            status = "error"
        summary[status] += 1
    return summary


def validate_site_prediction_modules(
    db_path: str | Path = DEFAULT_DB_PATH,
    output_json: str | Path | None = REPORT_OUTPUT_PATH,
) -> dict[str, Any]:
    """批量校验 site_prediction_modules 中启用模块的生成机制。"""
    refresh_prediction_configs(db_path)
    modules = load_enabled_site_modules(db_path)
    results = [validate_one_site_module(db_path, module_entry) for module_entry in modules]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "db_path": str(db_path),
            "lottery_type": FORCED_LOTTERY_TYPE,
            "preferred_web_id": PREFERRED_WEB_ID,
            "fallback_to_other_web_ids": True,
            "modules_count": len(modules),
        },
        "summary": summarize_results(results),
        "results": results,
    }

    if output_json is not None:
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file_obj:
            json.dump(report, file_obj, ensure_ascii=False, indent=2)

    return report


def print_report(report: dict[str, Any], output_json: str | Path | None) -> None:
    """打印批量校验摘要。"""
    summary = report["summary"]
    params = report["parameters"]
    print("=" * 72)
    print("Site Prediction Modules Validation Report")
    print("=" * 72)
    print(f"modules_count: {params['modules_count']}")
    print(f"lottery_type: {params['lottery_type']}")
    print(f"preferred_web_id: {params['preferred_web_id']}")
    print(f"fallback_to_other_web_ids: {params['fallback_to_other_web_ids']}")
    print(f"db_path: {params['db_path']}")
    print("-" * 72)
    print(f"total: {summary['total']}")
    print(f"ok: {summary['ok']}")
    print(f"warn: {summary['warn']}")
    print(f"error: {summary['error']}")
    print(f"skip: {summary['skip']}")

    warn_items = [item for item in report["results"] if item.get("status") == "warn"]
    error_items = [item for item in report["results"] if item.get("status") == "error"]
    skip_items = [item for item in report["results"] if item.get("status") == "skip"]

    if warn_items:
        print("\nWarn modules:")
        for item in warn_items:
            config = item.get("config") or {}
            selected_web_id = ((item.get("comparison") or {}).get("selected_web_id"))
            print(
                f"  key={item.get('mechanism_key')} "
                f"mode_id={config.get('mode_id')} "
                f"web_id={selected_web_id} "
                f"message={item.get('message')}"
            )

    if error_items:
        print("\nError modules:")
        for item in error_items:
            print(
                f"  key={item.get('mechanism_key')} "
                f"message={str(item.get('message') or '').splitlines()[-1]}"
            )

    if skip_items:
        print("\nSkipped modules:")
        for item in skip_items:
            config = item.get("config") or {}
            print(
                f"  key={item.get('mechanism_key')} "
                f"mode_id={config.get('mode_id')} "
                f"message={item.get('message')}"
            )

    if output_json is not None:
        print(f"\nReport saved: {output_json}")
    print("=" * 72)


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="校验 site_prediction_modules 与 type=3、优先 web_id=4 数据的结构兼容性。"
    )
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_PATH,
        help="数据库目标 DSN，默认使用本地 PostgreSQL。",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="报告输出路径，默认保存到 backend/src/test。",
    )
    return parser


def main() -> None:
    """命令行入口。"""
    args = build_parser().parse_args()
    output_json = Path(args.output_json) if args.output_json else REPORT_OUTPUT_PATH
    report = validate_site_prediction_modules(
        db_path=args.db_path,
        output_json=output_json,
    )
    print_report(report, output_json)
    if report["summary"]["warn"] > 0 or report["summary"]["error"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
