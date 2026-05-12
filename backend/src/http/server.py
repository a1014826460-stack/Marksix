from __future__ import annotations

from . import _load_stdlib_http_submodule


_stdlib_server = _load_stdlib_http_submodule("server")

for _name in dir(_stdlib_server):
    if _name.startswith("__") and _name not in {"__all__", "__doc__"}:
        continue
    globals()[_name] = getattr(_stdlib_server, _name)

__all__ = getattr(_stdlib_server, "__all__", [])
