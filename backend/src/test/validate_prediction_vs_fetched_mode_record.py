"""
校验指定预测模块的输出 JSON 结构，是否与 public.fetched_mode_records 中
对应 modes_id 的 payload_json 结构一致。

用法示例:
    python backend/src/test/validate_prediction_vs_fetched_mode_record.py --modes-id 53
    python backend/src/test/validate_prediction_vs_fetched_mode_record.py --modes-id 246 --type 3 --web-id 2
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

for path_item in (PREDICT_ROOT, SRC_ROOT):
    if str(path_item) not in sys.path:
        sys.path.insert(0, str(path_item))

from db import connect as db_connect  # noqa: E402
from common import predict  # noqa: E402
from mechanisms import (  # noqa: E402
    PREDICTION_CONFIGS,
    build_title_prediction_configs,
    get_prediction_config,
)


DEFAULT_RECORDS_DB_PATH = "postgresql://postgres:2225427@localhost:5432/liuhecai"
DEFAULT_PREDICT_DB_PATH = DEFAULT_RECORDS_DB_PATH
DEFAULT_RES_CODE = "01,02,03,04,05,06,07"
TABLE_PREFIX = "mode_payload_"
TABLE_MAP_NAME = "mode_payload_tables"
TEXT_HISTORY_TITLES = {
    "澳门传真",
    "白小姐幽默（9肖10码 + 特码）",
    "财神爷一句中特",
    "藏宝图解析",
    "成语平特",
    "成语平特尾",
    "东南漫画解特",
    "大小肖--选四连肖--每肖选2码",
    "独家玄机",
    "独家幽默",
    "独解传真",
    "独解蓝月亮点特图",
    "赌王玄机",
    "挂牌解析",
    "管家婆解梦",
    "红字解六肖",
    "火车头",
    "解传真四字",
    "解红字肖（词7肖14码）",
    "解话中有意",
    "解今日闲情",
    "解今日闲情2",
    "解蓝月亮玄机报",
    "解六合皇",
    "解苹果报",
    "解苹果报2",
    "解蛇蛋图",
    "解释奇缘玄机",
    "解西游玄机",
    "解相入非非",
    "解寻宝图",
    "解正卦成语",
    "今日闲情",
    "金牌谜语",
    "精解跑马测字",
    "老黄历玄机",
    "另版挂牌",
    "另版管家婆解梦",
    "另版诗象",
    "梅花诗",
    "买定离手",
    "每日闲情",
    "谜语平特",
    "密码玄机",
    "民间大神解跑马",
    "跑马玄机测字(7肖14码)",
    "跑马玄机测字7肖10码",
    "平特藏宝",
    "平特二肖",
    "平特玄机",
    "破成语",
    "七字波色",
    "奇缘解析",
}
IGNORED_KEYS = {"id", "table_modes_id", "modes_id", "web_id", "source_record_id", "fetched_at"}
FLEXIBLE_SCALAR_KEYS = {"web", "type", "year", "term", "status"}
BASE_KEYS = ("web", "type", "year", "term", "res_code", "res_sx", "res_color", "status")


def quote_identifier(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def ensure_mode_payload_metadata(db_path: str | Path) -> int:
    """为 predict() 补齐 mode_payload_tables 元数据。

    这张表不是原始业务数据，而是 normalize_sqlite.py 拆表后生成的映射表：
    modes_id -> title / table_name / record_count。
    某些预测逻辑会读取它来获取来源标题和动态机制配置。
    """
    created_at = datetime.now(timezone.utc).isoformat()
    upserted = 0

    with db_connect(db_path) as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {quote_identifier(TABLE_MAP_NAME)} (
                modes_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                filename TEXT NOT NULL DEFAULT '',
                table_name TEXT NOT NULL UNIQUE,
                record_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                is_image INTEGER NOT NULL DEFAULT 0,
                is_text INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        payload_tables = [
            table_name
            for table_name in conn.list_tables(TABLE_PREFIX)
            if table_name != TABLE_MAP_NAME
        ]
        for table_name in payload_tables:
            suffix = table_name.removeprefix(TABLE_PREFIX)
            if not suffix.isdigit():
                continue

            modes_id = int(suffix)
            title_row = None
            if conn.table_exists("fetched_modes"):
                title_row = conn.execute(
                    """
                    SELECT COALESCE(NULLIF(MIN(title), ''), ?) AS title
                    FROM fetched_modes
                    WHERE modes_id = ?
                    """,
                    (table_name, modes_id),
                ).fetchone()

            count_row = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM {quote_identifier(table_name)}"
            ).fetchone()
            title = str((title_row["title"] if title_row else table_name) or table_name)
            record_count = int(count_row["cnt"] or 0) if count_row else 0
            is_text = 1 if title in TEXT_HISTORY_TITLES else 0

            conn.execute(
                f"""
                INSERT INTO {quote_identifier(TABLE_MAP_NAME)}
                    (modes_id, title, filename, table_name, record_count, created_at, is_image, is_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(modes_id) DO UPDATE SET
                    title = excluded.title,
                    filename = excluded.filename,
                    table_name = excluded.table_name,
                    record_count = excluded.record_count,
                    created_at = excluded.created_at,
                    is_image = excluded.is_image,
                    is_text = excluded.is_text
                """,
                (
                    modes_id,
                    title,
                    "",
                    table_name,
                    record_count,
                    created_at,
                    0,
                    is_text,
                ),
            )
            upserted += 1

    return upserted


def refresh_prediction_configs(predict_db_path: str | Path) -> None:
    ensure_mode_payload_metadata(predict_db_path)
    PREDICTION_CONFIGS.update(build_title_prediction_configs(predict_db_path))


def parse_json_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    text = value.strip()
    if not text or text[0] not in "[{":
        return value

    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return value


def normalize_generated_content(raw_content: Any, payload_sample: dict[str, Any]) -> dict[str, Any]:
    business_sample_keys = [
        key
        for key in payload_sample.keys()
        if key not in IGNORED_KEYS and key not in BASE_KEYS
    ]

    if isinstance(raw_content, dict):
        data: dict[str, Any] = {}
        for key, value in raw_content.items():
            if isinstance(value, (dict, list)):
                data[key] = json.dumps(value, ensure_ascii=False)
            elif value is None:
                data[key] = None
            else:
                data[key] = str(value)
        if "content" in payload_sample and "content" not in data:
            data["content"] = ""
        return data

    if isinstance(raw_content, list):
        target_key = "content"
        if len(business_sample_keys) == 1 and business_sample_keys[0] != "content":
            target_key = business_sample_keys[0]
        return {target_key: json.dumps(raw_content, ensure_ascii=False)}

    target_key = "content"
    if len(business_sample_keys) == 1 and business_sample_keys[0] != "content":
        target_key = business_sample_keys[0]
    return {target_key: "" if raw_content is None else str(raw_content)}


def build_generated_payload_sample(
    prediction_result: dict[str, Any],
    payload_sample: dict[str, Any],
    res_code: str,
) -> dict[str, Any]:
    generated: dict[str, Any] = {}

    for key in BASE_KEYS:
        if key in payload_sample:
            generated[key] = payload_sample[key]

    if "res_code" not in generated or not str(generated["res_code"] or "").strip():
        generated["res_code"] = res_code

    generated.update(
        normalize_generated_content(
            prediction_result["prediction"]["content"],
            payload_sample,
        )
    )
    return generated


def strip_ignored_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: strip_ignored_keys(sub_value)
            for key, sub_value in value.items()
            if key not in IGNORED_KEYS
        }
    if isinstance(value, list):
        return [strip_ignored_keys(item) for item in value]
    return value


def describe_shape(value: Any, parent_key: str = "") -> Any:
    parsed_value = parse_json_value(value)

    if isinstance(parsed_value, dict):
        return {
            "type": "dict",
            "keys": {
                key: describe_shape(sub_value, key)
                for key, sub_value in sorted(parsed_value.items(), key=lambda item: item[0])
            },
        }

    if isinstance(parsed_value, list):
        item_shapes = {
            json.dumps(describe_shape(item), ensure_ascii=False, sort_keys=True)
            for item in parsed_value
        }
        return {
            "type": "list",
            "item_shapes": sorted(item_shapes),
        }

    if parsed_value is None:
        return "null"

    if isinstance(parsed_value, bool):
        return "bool"

    if isinstance(parsed_value, (int, float)):
        if parent_key in FLEXIBLE_SCALAR_KEYS:
            return "scalar:flex"
        return "number"

    if isinstance(parsed_value, str):
        if parent_key in FLEXIBLE_SCALAR_KEYS:
            return "scalar:flex"
        return "string"

    return f"unknown:{type(parsed_value).__name__}"


def build_shape_fingerprint(value: Any) -> str:
    return json.dumps(describe_shape(value), ensure_ascii=False, sort_keys=True)


def find_prediction_config(modes_id: int, predict_db_path: str | Path) -> dict[str, Any]:
    refresh_prediction_configs(predict_db_path)

    for key, config in sorted(PREDICTION_CONFIGS.items(), key=lambda item: item[0]):
        if int(config.default_modes_id) == modes_id:
            return config
    raise ValueError(f"未找到 modes_id={modes_id} 对应的预测模块配置")


def load_payload_sample(
    records_db_path: str | Path,
    modes_id: int,
    lottery_type: int | None = None,
    web_id: int | None = None,
) -> dict[str, Any]:
    with db_connect(records_db_path) as conn:
        if not conn.table_exists("fetched_mode_records"):
            raise ValueError("数据库中不存在 fetched_mode_records 表")

        rows = conn.execute(
            """
            SELECT web_id, modes_id, source_record_id, year, term, payload_json, fetched_at
            FROM fetched_mode_records
            WHERE modes_id = ?
            ORDER BY CAST(year AS INTEGER) DESC, CAST(term AS INTEGER) DESC, source_record_id DESC
            LIMIT 200
            """,
            (modes_id,),
        ).fetchall()

    matched_rows: list[dict[str, Any]] = []
    for row in rows:
        payload = json.loads(str(row["payload_json"] or "{}"))
        if lottery_type is not None and str(payload.get("type", "")) != str(lottery_type):
            continue
        matched_rows.append(
            {
                "web_id": int(row["web_id"]),
                "modes_id": int(row["modes_id"]),
                "source_record_id": str(row["source_record_id"]),
                "year": str(row["year"] or ""),
                "term": str(row["term"] or ""),
                "fetched_at": str(row["fetched_at"] or ""),
                "payload": payload,
            }
        )

    if web_id is not None:
        for item in matched_rows:
            if int(item["web_id"]) == int(web_id):
                item["requested_web_id"] = web_id
                item["used_fallback_web_id"] = False
                return item

    if matched_rows:
        item = dict(matched_rows[0])
        item["requested_web_id"] = web_id
        item["used_fallback_web_id"] = web_id is not None and int(item["web_id"]) != int(web_id)
        return item

    filters = []
    if lottery_type is not None:
        filters.append(f"type={lottery_type}")
    if web_id is not None:
        filters.append(f"web_id={web_id}")
    suffix = f"（筛选: {', '.join(filters)}）" if filters else ""
    raise ValueError(f"未找到 modes_id={modes_id} 的 payload_json 样本{suffix}")


def choose_res_code(payload_sample: dict[str, Any], override_res_code: str) -> str:
    if override_res_code.strip():
        return override_res_code.strip()

    payload_res_code = str(payload_sample.get("res_code", "") or "").strip()
    if payload_res_code:
        return payload_res_code

    return DEFAULT_RES_CODE


def default_output_path(modes_id: int) -> Path:
    return TEST_DIR / f"prediction_vs_fetched_mode_record_{modes_id}.json"


def validate_prediction_vs_fetched_mode_record(
    modes_id: int,
    lottery_type: int | None = None,
    web_id: int | None = None,
    predict_db_path: str | Path = DEFAULT_PREDICT_DB_PATH,
    records_db_path: str | Path = DEFAULT_RECORDS_DB_PATH,
    res_code: str = "",
    output_json: str | Path | None = None,
) -> dict[str, Any]:
    config_meta = find_prediction_config(modes_id, predict_db_path)
    payload_info = load_payload_sample(records_db_path, modes_id, lottery_type, web_id)
    payload_sample = payload_info["payload"]
    chosen_res_code = choose_res_code(payload_sample, res_code)

    report: dict[str, Any] = {
        "status": "error",
        "message": "",
        "parameters": {
            "modes_id": modes_id,
            "mechanism_key": config_meta.key,
            "mechanism_title": config_meta.title,
            "lottery_type": lottery_type,
            "web_id": web_id,
            "predict_db_path": str(predict_db_path),
            "records_db_path": str(records_db_path),
            "res_code_used": chosen_res_code,
        },
        "sample_record": {
            "web_id": payload_info["web_id"],
            "requested_web_id": payload_info.get("requested_web_id"),
            "used_fallback_web_id": bool(payload_info.get("used_fallback_web_id")),
            "source_record_id": payload_info["source_record_id"],
            "year": payload_info["year"],
            "term": payload_info["term"],
            "fetched_at": payload_info["fetched_at"],
        },
        "comparison": {},
    }

    try:
        prediction_result = predict(
            config=get_prediction_config(config_meta.key),
            res_code=chosen_res_code,
            db_path=predict_db_path,
        )
        generated_sample = build_generated_payload_sample(
            prediction_result=prediction_result,
            payload_sample=payload_sample,
            res_code=chosen_res_code,
        )

        payload_comparable = strip_ignored_keys(payload_sample)
        generated_comparable = strip_ignored_keys(generated_sample)

        payload_fingerprint = build_shape_fingerprint(payload_comparable)
        generated_fingerprint = build_shape_fingerprint(generated_comparable)
        matched = payload_fingerprint == generated_fingerprint

        report["status"] = "ok" if matched else "warn"
        report["message"] = "格式一致" if matched else "格式不同，请检查样本"
        report["comparison"] = {
            "matched": matched,
            "payload_fingerprint": payload_fingerprint,
            "generated_fingerprint": generated_fingerprint,
            "payload_sample": payload_sample,
            "generated_sample": generated_sample,
            "payload_comparable": payload_comparable,
            "generated_comparable": generated_comparable,
        }
        report["prediction_result_excerpt"] = {
            "mode": prediction_result.get("mode"),
            "prediction": prediction_result.get("prediction"),
            "warning": prediction_result.get("warning"),
        }
    except Exception:
        report["status"] = "error"
        report["message"] = traceback.format_exc()

    if output_json is not None:
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file_obj:
            json.dump(report, file_obj, ensure_ascii=False, indent=2)

    return report


def safe_validate_prediction_vs_fetched_mode_record(
    modes_id: int,
    lottery_type: int | None = None,
    web_id: int | None = None,
    predict_db_path: str | Path = DEFAULT_PREDICT_DB_PATH,
    records_db_path: str | Path = DEFAULT_RECORDS_DB_PATH,
    res_code: str = "",
    output_json: str | Path | None = None,
) -> dict[str, Any]:
    try:
        return validate_prediction_vs_fetched_mode_record(
            modes_id=modes_id,
            lottery_type=lottery_type,
            web_id=web_id,
            predict_db_path=predict_db_path,
            records_db_path=records_db_path,
            res_code=res_code,
            output_json=output_json,
        )
    except Exception:
        return {
            "status": "error",
            "message": traceback.format_exc(),
            "parameters": {
                "modes_id": modes_id,
                "lottery_type": lottery_type,
                "web_id": web_id,
                "predict_db_path": str(predict_db_path),
                "records_db_path": str(records_db_path),
                "res_code_used": res_code or DEFAULT_RES_CODE,
            },
            "sample_record": {},
            "comparison": {},
        }


def print_report(report: dict[str, Any]) -> None:
    params = report["parameters"]
    print("=" * 72)
    print("预测 JSON 与 fetched_mode_records.payload_json 格式校验")
    print("=" * 72)
    print(f"modes_id: {params['modes_id']}")
    print(f"模块: {params['mechanism_key']} / {params['mechanism_title']}")
    print(f"records_db_path: {params['records_db_path']}")
    print(f"predict_db_path: {params['predict_db_path']}")
    print(f"res_code_used: {params['res_code_used']}")
    print("-" * 72)
    print(f"状态: {report['status']}")
    print(f"说明: {report['message']}")

    sample_record = report.get("sample_record", {})
    if sample_record:
        print(
            "样本来源: "
            f"web_id={sample_record.get('web_id')} "
            f"source_record_id={sample_record.get('source_record_id')} "
            f"year={sample_record.get('year')} "
            f"term={sample_record.get('term')}"
        )

    comparison = report.get("comparison") or {}
    if comparison:
        print(f"payload_fingerprint:   {comparison.get('payload_fingerprint')}")
        print(f"generated_fingerprint: {comparison.get('generated_fingerprint')}")

        if report["status"] == "warn":
            print("\n[警告] 预测模块生成的数据样本:")
            print(json.dumps(comparison.get("generated_sample"), ensure_ascii=False, indent=2))
            print("\n[警告] public.fetched_mode_records.payload_json 样本:")
            print(json.dumps(comparison.get("payload_sample"), ensure_ascii=False, indent=2))

    print("=" * 72)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="校验预测模块输出 JSON 与 fetched_mode_records.payload_json 的格式是否一致"
    )
    parser.add_argument("--modes-id", type=int, required=True, help="要校验的 modes_id")
    parser.add_argument("--type", type=int, default=None, dest="lottery_type", help="可选，筛选 type")
    parser.add_argument("--web-id", type=int, default=None, help="可选，筛选 web_id")
    parser.add_argument(
        "--res-code",
        default="",
        help=f"可选，传给 predict() 的开奖号码；未传时优先取 payload_json.res_code，否则使用默认值 {DEFAULT_RES_CODE}",
    )
    parser.add_argument(
        "--predict-db-path",
        default=str(DEFAULT_PREDICT_DB_PATH),
        help="predict() 使用的数据源，默认 PostgreSQL",
    )
    parser.add_argument(
        "--records-db-path",
        default=DEFAULT_RECORDS_DB_PATH,
        help="fetched_mode_records 所在数据源，默认 PostgreSQL",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="报告输出路径，默认保存到 backend/src/test 目录",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_json = Path(args.output_json) if args.output_json else default_output_path(args.modes_id)

    report = validate_prediction_vs_fetched_mode_record(
        modes_id=args.modes_id,
        lottery_type=args.lottery_type,
        web_id=args.web_id,
        predict_db_path=args.predict_db_path,
        records_db_path=args.records_db_path,
        res_code=args.res_code,
        output_json=output_json,
    )
    print_report(report)
    print(f"报告已保存: {output_json}")

    if report["status"] in {"warn", "error"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
