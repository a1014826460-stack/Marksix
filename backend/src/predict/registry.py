from __future__ import annotations

from typing import Any

from predict.common import PredictionConfig


class PredictionRegistry:
    def __init__(self, configs: dict[str, PredictionConfig] | None = None):
        self._configs: dict[str, PredictionConfig] = dict(configs or {})

    def update(self, configs: dict[str, PredictionConfig]) -> None:
        self._configs.update(configs)

    def supported_keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._configs))

    def list_configs(self, status_map: dict[str, int] | None = None) -> list[dict[str, Any]]:
        statuses = dict(status_map or {})
        return [
            {
                "key": key,
                "title": config.title,
                "default_modes_id": config.default_modes_id,
                "default_table": config.default_table,
                "status": statuses.get(key, 1),
            }
            for key, config in sorted(self._configs.items())
        ]

    def get(self, key: str) -> PredictionConfig:
        try:
            return self._configs[key]
        except KeyError as exc:
            supported = ", ".join(sorted(self._configs))
            raise ValueError(f"Unsupported prediction mechanism: {key}. Supported: {supported}") from exc
