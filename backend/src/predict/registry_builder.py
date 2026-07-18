from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from db import connect as db_connect
from domains.prediction import predict_repository
from predict._db_helpers import _business_columns, _is_first_stage_supported_table, _sample_content, _table_columns
from predict.common import DEFAULT_DB_TARGET, PredictionConfig, table_exists


def build_dynamic_prediction_configs(
    db_path: str | Path = DEFAULT_DB_TARGET,
    *,
    static_configs: dict[str, PredictionConfig],
    classify_first_stage: Callable[[str, str, int, str], PredictionConfig | None],
    classify_second_stage: Callable[[Any, str, str, int, tuple[str, ...]], PredictionConfig | None],
) -> dict[str, PredictionConfig]:
    """Build dynamic configs while keeping rule classification injected and testable."""
    try:
        conn = db_connect(db_path)
    except Exception:
        return {}

    with conn:
        if not table_exists(conn, "mode_payload_tables"):
            return {}

        static_mode_ids = {config.default_modes_id for config in static_configs.values()}
        static_titles = {config.title for config in static_configs.values()}
        generated: dict[str, PredictionConfig] = {}

        for row in predict_repository.load_mode_payload_table_rows(conn):
            modes_id = int(row["modes_id"])
            title = str(row["title"] or "").strip()
            table_name = str(row["table_name"] or "").strip()
            if (
                not title
                or modes_id in static_mode_ids
                or title in static_titles
                or not table_exists(conn, table_name)
                or int(row["record_count"] or 0) <= 0
            ):
                continue

            columns = _table_columns(conn, table_name)
            if _is_first_stage_supported_table(columns):
                config = classify_first_stage(title, table_name, modes_id, _sample_content(conn, table_name))
            else:
                config = classify_second_stage(
                    conn,
                    title,
                    table_name,
                    modes_id,
                    _business_columns(conn, table_name),
                )
            if config is not None:
                generated[config.key] = config

        return generated
