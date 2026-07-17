from __future__ import annotations

from predict.common import build_common_parser, predict, print_json_result
from predict.mechanisms import get_prediction_config


def build_single_mechanism_parser(description: str):
    return build_common_parser(description)


def run_single_mechanism_cli(mechanism_key: str, description: str) -> None:
    args = build_single_mechanism_parser(description).parse_args()
    result = predict(
        config=get_prediction_config(mechanism_key),
        res_code=args.res_code,
        content=args.content,
        source_table=args.source_table,
        db_path=args.db_path,
        target_hit_rate=args.target_hit_rate,
    )
    print_json_result(result)
