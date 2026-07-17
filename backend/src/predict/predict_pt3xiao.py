from predict.script_cli import build_single_mechanism_parser, run_single_mechanism_cli


MECHANISM_KEY = "pt3xiao"
DESCRIPTION = "predict pt3xiao"


def build_parser():
    return build_single_mechanism_parser(DESCRIPTION)


if __name__ == "__main__":
    run_single_mechanism_cli(MECHANISM_KEY, DESCRIPTION)
