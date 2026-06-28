from __future__ import annotations

from db import connect
from runtime_config import ensure_system_config_table, seed_system_config_defaults


def test_prediction_simulation_defaults_are_seeded(tmp_path):
    db_path = tmp_path / "prediction_simulation_config.sqlite3"
    with connect(db_path) as conn:
        ensure_system_config_table(conn)
        seed_system_config_defaults(conn, now="2026-01-01T00:00:00+00:00")
        rows = conn.execute(
            """
            SELECT key, value_text, value_type
            FROM system_config
            WHERE key IN (
                'prediction.simulation.target_hit_rate',
                'prediction.simulation.max_consecutive_hits',
                'prediction.simulation.max_consecutive_misses'
            )
            ORDER BY key
            """
        ).fetchall()

    assert [dict(row) for row in rows] == [
        {
            "key": "prediction.simulation.max_consecutive_hits",
            "value_text": "3",
            "value_type": "int",
        },
        {
            "key": "prediction.simulation.max_consecutive_misses",
            "value_text": "3",
            "value_type": "int",
        },
        {
            "key": "prediction.simulation.target_hit_rate",
            "value_text": "0.5",
            "value_type": "float",
        },
    ]
