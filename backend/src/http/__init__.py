from __future__ import annotations

import importlib.util
import sys
import sysconfig
from pathlib import Path
from types import ModuleType


def _load_stdlib_http_submodule(name: str) -> ModuleType:
    stdlib_root = Path(sysconfig.get_path("stdlib"))
    relative = Path("http") / "__init__.py" if name == "__init__" else Path("http") / f"{name}.py"
    file_path = stdlib_root / relative
    spec = importlib.util.spec_from_file_location(f"_stdlib_http_{name}", file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load stdlib http.{name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_stdlib_http = _load_stdlib_http_submodule("__init__")
HTTPStatus = _stdlib_http.HTTPStatus
HTTPMethod = getattr(_stdlib_http, "HTTPMethod", None)
__path__ = [str(Path(sysconfig.get_path("stdlib")) / "http"), str(Path(__file__).resolve().parent)]


def __getattr__(name: str) -> ModuleType | object:
    if hasattr(_stdlib_http, name):
        return getattr(_stdlib_http, name)
    try:
        module = _load_stdlib_http_submodule(name)
    except ImportError as exc:
        raise AttributeError(name) from exc
    sys.modules[f"{__name__}.{name}"] = module
    return module

__all__ = ["HTTPMethod", "HTTPStatus"]
