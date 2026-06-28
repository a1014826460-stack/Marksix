from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from admin import payload


def test_list_mode_payload_rows_delegates_to_prediction_domain_service():
    db_path = Path("delegation-only.sqlite3")
    expected = {
        "rows": [{"id": 1}],
        "total": 1,
        "page": 2,
        "page_size": 10,
        "columns": ["id"],
    }

    with patch("domains.prediction.mode_payload_service.list_mode_payload_rows", return_value=expected) as list_rows:
        result = payload.list_mode_payload_rows(
            db_path,
            "mode_payload_43",
            type_filter="3",
            web_filter="6",
            page=2,
            page_size=10,
            search="alpha",
            source="public",
        )

    assert result == expected
    list_rows.assert_called_once_with(
        db_path,
        "mode_payload_43",
        type_filter="3",
        web_filter="6",
        page=2,
        page_size=10,
        search="alpha",
        source="public",
    )
