from __future__ import annotations

import importlib
import inspect


def test_legacy_predict_scripts_delegate_to_shared_cli_runner():
    modules = [
        "predict.predict_pt3xiao",
        "predict.predict_liangtouzxt",
        "predict.predict_juesha1xiao",
        "predict.predict_juesha2xiao",
    ]

    for module_name in modules:
        module = importlib.import_module(module_name)
        source = inspect.getsource(module)

        assert hasattr(module, "build_parser")
        assert "run_single_mechanism_cli" in source
        assert "predict(" not in source
        assert "get_prediction_config" not in source
