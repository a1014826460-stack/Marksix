from __future__ import annotations

from db import connect
from domains.prediction import generation_log_repository


def test_generation_log_repository_writes_allowlisted_task_log_fields(tmp_path):
    db_path = tmp_path / "prediction_log.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE error_logs (
                id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                level TEXT NOT NULL,
                logger_name TEXT,
                module TEXT,
                func_name TEXT,
                file_path TEXT,
                line_number INTEGER,
                message TEXT,
                site_id INTEGER,
                web_id INTEGER,
                lottery_type_id INTEGER
            )
            """
        )

        generation_log_repository.write_prediction_task_log(
            conn,
            level="INFO",
            message="Generated mode 43",
            site_id=7,
            web_id=4,
            lottery_type_id=3,
            created_at="2026-07-17T00:00:00Z",
        )
        row = conn.execute(
            "SELECT level, logger_name, module, func_name, message, site_id, web_id, lottery_type_id FROM error_logs"
        ).fetchone()

    assert dict(row) == {
        "level": "INFO",
        "logger_name": "prediction.task",
        "module": "prediction_generation",
        "func_name": "_log_module_result",
        "message": "Generated mode 43",
        "site_id": 7,
        "web_id": 4,
        "lottery_type_id": 3,
    }
