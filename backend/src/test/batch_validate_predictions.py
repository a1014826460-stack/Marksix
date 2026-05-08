"""
批量验证所有预测模块生成数据格式与数据库中 type=3 content 列格式是否一致。

使用多进程并行调用 predict() 加速，tqdm 显示实时进度。

用法：
    # 命令行方式
    python backend/src/test/batch_validate_predictions.py --term 2025001 --numbers "01,05,12,23,34,45,49" --type 3 --opened

    # 函数调用方式
    from test.batch_validate_predictions import batch_validate_predictions
    report = batch_validate_predictions(
        term="2025001",
        winning_numbers="01,05,12,23,34,45,49",
        lottery_type=3,
        is_opened=True,
    )
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import re
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# tqdm 可选导入（未安装时回退到无进度条模式）
# ---------------------------------------------------------------------------
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

for p in (PREDICT_ROOT, SRC_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from db import connect as db_connect  # noqa: E402  # pyright: ignore[reportMissingImports]
from mechanisms import list_prediction_configs  # noqa: E402  # pyright: ignore[reportMissingImports]

DEFAULT_DB_PATH = "postgresql://postgres:2225427@localhost:5432/liuhecai"
DEFAULT_WORKERS = min(multiprocessing.cpu_count(), 8)

# JSON 报告输出路径
REPORT_OUTPUT_PATH = TEST_DIR / "validation_report.json"


# ---------------------------------------------------------------------------
# 格式指纹提取
# ---------------------------------------------------------------------------

def extract_format_fingerprint(value: Any) -> str:
    """从 content 值提取格式指纹，用于比较两个 content 是否同构。"""
    if value is None or value == "":
        return "empty"

    if isinstance(value, (list, tuple)):
        return _fingerprint_list(value)

    if isinstance(value, dict):
        return _fingerprint_dict(value)

    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                parsed = json.loads(stripped)
                return extract_format_fingerprint(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
        return _fingerprint_plain_str(stripped)

    return f"unknown:{type(value).__name__}"


def _fingerprint_list(items: list | tuple) -> str:
    if not items:
        return "list:empty"

    item_patterns: list[str] = []
    for item in items:
        if isinstance(item, str):
            if "|" in item:
                item_patterns.append("pipe_item")
            elif re.match(r"^\d{2}$", item):
                item_patterns.append("number_2d")
            elif re.match(r"^[一-鿿]+$", item):
                item_patterns.append("chinese_label")
            else:
                item_patterns.append("string")
        elif isinstance(item, (int, float)):
            item_patterns.append("numeric")
        elif isinstance(item, dict):
            item_patterns.append(f"dict[{_fingerprint_dict(item)}]")
        elif isinstance(item, list):
            item_patterns.append("nested_list")
        else:
            item_patterns.append(type(item).__name__)
        item_patterns.append(item_patterns[-1])

    unique_patterns = sorted(set(item_patterns))
    return f"list:[{','.join(unique_patterns)}]"


def _fingerprint_dict(obj: dict) -> str:
    if not obj:
        return "dict:empty"
    keys = sorted(obj.keys())
    return f"dict:keys[{','.join(keys)}]"


def _fingerprint_plain_str(text: str) -> str:
    """对非 JSON 纯文本做格式指纹。"""
    if "," not in text:
        return "str:plain"

    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        return "str:csv_empty"

    if all(re.match(r"^\d{2}$", p) for p in parts):
        return "str:csv_numbers_2d"
    if all(re.match(r"^\d+$", p) for p in parts):
        return "str:csv_numbers"
    if all(re.match(r"^[一-鿿]+$", p) for p in parts):
        return "str:csv_chinese"
    return "str:csv_mixed"


# ---------------------------------------------------------------------------
# Phase 1：收集 type=3 格式指纹（主进程，顺序执行 — 纯 DB 读取，很快）
# ---------------------------------------------------------------------------

def _collect_type3_fingerprints(
    db_path: str,
    mechanisms: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """为所有 mechanism 提前查询 type=3 格式指纹。

    Returns:
        {mechanism_key: {"type3_format": str|None, "type3_sample": Any, "error": str|None}}
    """
    info: dict[str, dict[str, Any]] = {}

    with db_connect(db_path) as conn:
        for entry in mechanisms:
            key = entry["key"]
            table_name = entry.get("default_table", f"mode_payload_{entry['default_modes_id']}")

            result: dict[str, Any] = {
                "type3_format": None,
                "type3_sample": None,
                "error": None,
            }

            try:
                if not conn.table_exists(table_name):
                    result["type3_format"] = None  # 表不存在 → 之后标记为 skip
                else:
                    rows = conn.execute(
                        f"""
                        SELECT content
                        FROM "{table_name}"
                        WHERE CAST(type AS TEXT) = '3'
                          AND content IS NOT NULL
                          AND content != ''
                        ORDER BY CAST(year AS INTEGER) DESC, CAST(term AS INTEGER) DESC
                        LIMIT 5
                        """
                    ).fetchall()

                    if rows:
                        samples = [dict(r) for r in rows]
                        fp_counts: dict[str, int] = {}
                        for s in samples:
                            fp = extract_format_fingerprint(s.get("content", ""))
                            fp_counts[fp] = fp_counts.get(fp, 0) + 1
                        result["type3_format"] = max(fp_counts, key=lambda k: fp_counts[k])
                        result["type3_sample"] = samples[0].get("content")
            except Exception as exc:
                try:
                    conn.rollback()
                except Exception:
                    pass
                result["error"] = str(exc)

            info[key] = result

    return info


# ---------------------------------------------------------------------------
# Phase 2：多进程并行调用 predict()
# ---------------------------------------------------------------------------

def _predict_one(payload: dict[str, Any]) -> dict[str, Any]:
    """Worker 函数（模块级别，供 multiprocessing pickle 使用）。

    每个 worker 创建自己的数据库连接，调用一次 predict()。
    """
    key = payload["key"]
    db_path = payload["db_path"]
    res_code = payload["res_code"]
    table_name = payload["table_name"]

    result: dict[str, Any] = {
        "mechanism_key": key,
        "generated_content": None,
        "generated_format": None,
        "error": None,
    }

    try:
        # 子进程中需要重建 sys.path（Windows spawn 模式下不继承）
        predict_root = PREDICT_ROOT
        src_root = SRC_ROOT
        for p_dir in (predict_root, src_root):
            if str(p_dir) not in sys.path:
                sys.path.insert(0, str(p_dir))

        from common import predict as worker_predict  # pyright: ignore[reportMissingImports]
        from mechanisms import (  # pyright: ignore[reportMissingImports]
            get_prediction_config as worker_get_config,
        )

        config = worker_get_config(key)
        prediction = worker_predict(
            config=config,
            res_code=res_code,
            source_table=table_name,
            db_path=db_path,
        )
        generated = prediction["prediction"]["content"]
        result["generated_content"] = generated
        result["generated_format"] = extract_format_fingerprint(generated)
    except Exception:
        result["error"] = traceback.format_exc()

    return result


# ---------------------------------------------------------------------------
# 主验证函数
# ---------------------------------------------------------------------------

def batch_validate_predictions(
    term: str = "",
    winning_numbers: str = "",
    lottery_type: int = 3,
    is_opened: bool = False,
    db_path: str = DEFAULT_DB_PATH,
    workers: int = DEFAULT_WORKERS,
    output_json: str | Path | None = REPORT_OUTPUT_PATH,
) -> dict[str, Any]:
    """批量调用所有预测模块 API，验证生成数据格式与 type=3 content 格式一致性。

    Args:
        term: 期数，如 "2025001"。
        winning_numbers: 开奖号码，逗号分隔，如 "01,05,12,23,34,45,49"。
        lottery_type: 彩种类型，1=香港彩, 2=澳门彩, 3=台湾彩。
        is_opened: 是否已经开奖。True 时传入 res_code；False 时留空生成下一期预测。
        db_path: 数据库目标路径或 DSN。
        workers: 并行 worker 数量，默认 min(cpu_count, 8)。
        output_json: JSON 报告输出路径，None 表示不保存文件。

    Returns:
        验证报告 dict。
    """
    res_code = winning_numbers.strip() if is_opened and winning_numbers.strip() else None

    mechanisms = list_prediction_configs()

    # ── Phase 1: 收集 type=3 格式指纹 ──
    print(f"Phase 1/2: 收集 {len(mechanisms)} 个模块的 type=3 格式指纹 ...")
    type3_info = _collect_type3_fingerprints(db_path, mechanisms)
    print(f"  完成，{len([v for v in type3_info.values() if v['type3_format']])} 个模块有 type=3 数据\n")

    # ── Phase 2: 多进程并行 predict() ──
    tasks: list[dict[str, Any]] = []
    skip_keys: set[str] = set()
    for entry in mechanisms:
        key = entry["key"]
        table_name = entry.get("default_table", f"mode_payload_{entry['default_modes_id']}")
        info = type3_info.get(key, {})

        if info.get("error"):
            skip_keys.add(key)
            continue
        if info.get("type3_format") is None:
            skip_keys.add(key)
            continue

        tasks.append({
            "key": key,
            "db_path": db_path,
            "res_code": res_code,
            "table_name": table_name,
        })

    print(f"Phase 2/2: 并行调用 predict() [{len(tasks)} 个模块, {workers} workers] ...")

    predict_results: dict[str, dict[str, Any]] = {}
    if tasks:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_map = {executor.submit(_predict_one, t): t["key"] for t in tasks}
            pbar = _tqdm(
                as_completed(future_map),
                total=len(tasks),
                desc="  predict",
                unit="module",
                ncols=100,
            )
            for future in pbar:
                key = future_map[future]
                try:
                    predict_results[key] = future.result()
                except Exception:
                    predict_results[key] = {
                        "mechanism_key": key,
                        "generated_content": None,
                        "generated_format": None,
                        "error": traceback.format_exc(),
                    }
            if hasattr(pbar, "close"):
                pbar.close()  # type: ignore[union-attr]

    # ── 汇总结果 ──
    results: list[dict[str, Any]] = []
    summary = {"total": len(mechanisms), "ok": 0, "warn": 0, "error": 0, "skip": 0}

    for entry in mechanisms:
        key = entry["key"]
        title = entry["title"]
        table_name = entry.get("default_table", f"mode_payload_{entry['default_modes_id']}")
        info = type3_info.get(key, {})
        pred = predict_results.get(key, {})

        result: dict[str, Any] = {
            "mechanism_key": key,
            "mechanism_title": title,
            "mode_payload_table": table_name,
            "status": "skip",
            "type3_format": info.get("type3_format"),
            "generated_format": pred.get("generated_format"),
            "type3_sample": info.get("type3_sample"),
            "generated_content": pred.get("generated_content"),
            "message": "",
        }

        # 判断状态
        if info.get("error"):
            result["status"] = "error"
            result["message"] = f"查询 type=3 格式失败: {info['error']}"
            summary["error"] += 1
        elif info.get("type3_format") is None:
            result["status"] = "skip"
            result["message"] = f"表 {table_name} 无 type=3 数据，跳过比较"
            summary["skip"] += 1
        elif pred.get("error"):
            result["status"] = "error"
            msg = pred["error"]
            # 只保留最后一行有意义的消息
            lines = [l for l in msg.strip().split("\n") if l.strip()]
            result["message"] = f"predict() 执行失败: {lines[-1] if lines else msg}"
            summary["error"] += 1
        elif result["generated_format"] == result["type3_format"]:
            result["status"] = "ok"
            result["message"] = "格式一致"
            summary["ok"] += 1
        else:
            result["status"] = "warn"
            result["message"] = (
                f"格式不一致：type=3 格式为 [{result['type3_format']}]，"
                f"生成格式为 [{result['generated_format']}]"
            )
            summary["warn"] += 1

        results.append(result)

    report: dict[str, Any] = {
        "summary": summary,
        "parameters": {
            "term": term,
            "winning_numbers": winning_numbers,
            "lottery_type": lottery_type,
            "is_opened": is_opened,
            "res_code_passed": res_code,
            "db_path": db_path,
            "workers": workers,
        },
        "results": results,
    }

    # 保存 JSON 报告
    if output_json is not None:
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nJSON 报告已保存至: {output_path}")

    return report


# ---------------------------------------------------------------------------
# 控制台报告
# ---------------------------------------------------------------------------

def print_report(report: dict[str, Any]) -> None:
    """格式化打印验证报告到控制台。"""
    summary = report["summary"]
    params = report["parameters"]

    print("\n" + "=" * 72)
    print("预测模块格式验证报告")
    print("=" * 72)
    print(f"  彩种: {params['lottery_type']} ({'香港彩' if params['lottery_type'] == 1 else '澳门彩' if params['lottery_type'] == 2 else '台湾彩'})")
    print(f"  期数: {params['term'] or '(未指定)'}")
    print(f"  开奖号码: {params['winning_numbers'] or '(未指定)'}")
    print(f"  已开奖: {'是' if params['is_opened'] else '否'} (res_code={'传入' if params['res_code_passed'] else '留空'})")
    print(f"  数据库: {params['db_path']}")
    print(f"  Workers: {params.get('workers', 'N/A')}")
    print("-" * 72)
    print(f"  总计 {summary['total']} 个模块:")
    print(f"    通过 (格式一致): {summary['ok']}")
    print(f"    警告 (格式不一致): {summary['warn']}")
    print(f"    错误 (执行失败): {summary['error']}")
    print(f"    跳过 (无 type=3 数据): {summary['skip']}")
    print("-" * 72)

    for status, label, prefix in [
        ("warn", "格式不一致的模块", "?"),
        ("error", "执行失败的模块", "!"),
        ("skip", "跳过的模块", "-"),
    ]:
        items = [r for r in report["results"] if r["status"] == status]
        if not items:
            continue
        print(f"\n{prefix} {label} ({len(items)} 个):")
        for item in items:
            print(f"  [{item['mechanism_key']}] {item['mechanism_title']}")
            print(f"    表: {item['mode_payload_table']}")
            print(f"    type=3 格式: {item['type3_format']}")
            if item["status"] == "warn":
                print(f"    生成格式:   {item['generated_format']}")
            print(f"    信息: {item['message']}")

    ok_items = [r for r in report["results"] if r["status"] == "ok"]
    if ok_items:
        print(f"\n  通过验证的模块 ({len(ok_items)} 个):")
        for item in ok_items:
            print(f"    [{item['mechanism_key']}] {item['mechanism_title']} — 格式 [{item['type3_format']}]")

    print("\n" + "=" * 72)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="批量验证所有预测模块生成数据与 type=3 content 格式一致性"
    )
    parser.add_argument("--term", default="", help="期数，如 2025001")
    parser.add_argument(
        "--numbers", default="",
        help="开奖号码，逗号分隔，如 01,05,12,23,34,45,49",
    )
    parser.add_argument(
        "--type", type=int, default=3, dest="lottery_type",
        help="彩种类型: 1=香港彩, 2=澳门彩, 3=台湾彩 (默认 3)",
    )
    parser.add_argument(
        "--opened", action="store_true", default=False,
        help="已开奖 (传入 res_code 生成命中标注)",
    )
    parser.add_argument(
        "--db-path", default=DEFAULT_DB_PATH,
        help="数据库路径 (默认 PostgreSQL DSN)",
    )
    parser.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS,
        help=f"并行 worker 数 (默认 {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--no-progress", action="store_true", default=False,
        help="禁用进度条 (当 tqdm 未安装时自动回退)",
    )
    parser.add_argument(
        "--no-save", action="store_true", default=False,
        help="不保存 JSON 报告文件",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    # 进度条由 tqdm 自动控制；--no-progress 仅当 tqdm 已安装时有用
    global _tqdm, _HAS_TQDM
    if args.no_progress and _HAS_TQDM:
        _HAS_TQDM = False
        _tqdm = lambda iterable, **_kw: iterable  # type: ignore[assignment]

    output_json = None if args.no_save else REPORT_OUTPUT_PATH

    print("=" * 72)
    print("批量预测格式验证")
    print("=" * 72)
    print(f"  彩种: {args.lottery_type}")
    print(f"  Workers: {args.workers}")
    print(f"  数据库: {args.db_path}")
    print(f"  进度条: {'禁用' if args.no_progress or not _HAS_TQDM else '启用'}")
    print()

    report = batch_validate_predictions(
        term=args.term,
        winning_numbers=args.numbers,
        lottery_type=args.lottery_type,
        is_opened=args.opened,
        db_path=args.db_path,
        workers=args.workers,
        output_json=output_json,
    )

    print_report(report)

    summary = report["summary"]
    if summary["warn"] > 0 or summary["error"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
