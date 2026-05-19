from predict.common import build_common_parser, predict, print_json_result
from predict.mechanisms import get_prediction_config


def build_parser():
    return build_common_parser("预测 绝杀1肖")


if __name__ == "__main__":
    args = build_parser().parse_args()
    result = predict(
        config=get_prediction_config("juesha1xiao"),
        res_code=args.res_code,
        content=args.content,
        source_table=args.source_table,
        db_path=args.db_path,
        target_hit_rate=args.target_hit_rate,
    )
    print_json_result(result)
