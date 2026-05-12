from __future__ import annotations

from . import _load_stdlib_http_submodule


_stdlib_client = _load_stdlib_http_submodule("client")

for _name in dir(_stdlib_client):
    if _name.startswith("__") and _name not in {"__all__", "__doc__"}:
        continue
    globals()[_name] = getattr(_stdlib_client, _name)

__all__ = getattr(_stdlib_client, "__all__", [])

