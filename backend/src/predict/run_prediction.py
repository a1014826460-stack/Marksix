import argparse

from common import build_common_parser, predict, print_json_result
from mechanisms import get_prediction_config, list_prediction_configs


def build_parser() -> argparse.ArgumentParser:
    """统一预测脚本入口，供前端 API 调用。"""
    parser = build_common_parser("统一预测入口：按 mechanism 生成对应玩法 content。")
    parser.add_argument(
        "--mechanism",
        help="预测机制 key。可用 --list-mechanisms 查看静态机制和按 title 自动生成的本地机制。",
    )
    parser.add_argument("--list-mechanisms", action="store_true", help="列出当前可用预测机制。")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    if args.list_mechanisms:
        print_json_result({"mechanisms": list_prediction_configs()})
        raise SystemExit(0)

    if not args.mechanism:
        raise SystemExit("--mechanism 不能为空；可用 --list-mechanisms 查看可用机制。")

    config = get_prediction_config(args.mechanism)
    result = predict(
        config=config,
        res_code=args.res_code,
        content=args.content,
        source_table=args.source_table,
        db_path=args.db_path,
        target_hit_rate=args.target_hit_rate,
    )
    print_json_result(result)
