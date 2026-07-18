from __future__ import annotations

from typing import Any


def write_prediction_task_log(
    conn: Any,
    *,
    level: str,
    message: str,
    site_id: int,
    web_id: int,
    lottery_type_id: int,
    created_at: str,
    file_path: str = "",
) -> None:
    """Persist safe task metadata; prediction truth never enters this boundary."""
    conn.execute(
        """
        INSERT INTO error_logs (
            created_at, level, logger_name, module, func_name,
            file_path, line_number, message,
            site_id, web_id, lottery_type_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(created_at),
            str(level),
            "prediction.task",
            "prediction_generation",
            "_log_module_result",
            str(file_path),
            0,
            str(message),
            int(site_id),
            int(web_id),
            int(lottery_type_id),
        ),
    )
