from __future__ import annotations

from contextlib import contextmanager

from public import api


class _Connection:
    engine = "postgres"

    def table_exists(self, _table_name: str) -> bool:
        return True


def _payload(term: int) -> dict[str, object]:
    return {
        "id": term,
        "type": 3,
        "year": 2026,
        "term": term,
        "web_id": 9,
        "content": f"row-{term}",
    }


def test_public_history_reads_fallback_when_preferred_window_has_duplicate_issues(monkeypatch):
    """A full raw created window is not sufficient when it has only one issue."""

    @contextmanager
    def fake_connect(_db_path):
        yield _Connection()

    calls: list[dict[str, object]] = []

    def fake_load(_conn, *, schema_name=None, **kwargs):
        calls.append({"schema_name": schema_name, **kwargs})
        if schema_name == "created":
            return [_payload(175) for _ in range(100)]
        return [_payload(term) for term in range(174, 166, -1)]

    monkeypatch.setattr(api, "connect", fake_connect)
    monkeypatch.setattr(api, "created_table_exists", lambda *_args: True)
    monkeypatch.setattr(api, "resolve_prediction_table_for_mode", lambda *_args: "mode_payload_54")
    monkeypatch.setattr(api, "load_mode_payload_rows_from_source", fake_load)
    monkeypatch.setattr(api, "apply_lottery_draw_overlay", lambda _conn, rows, **_kwargs: rows)

    result = api.load_public_module_history(
        "postgresql://example.invalid/test",
        "pt1wei",
        8,
        lottery_type_id=3,
    )

    assert [row["term"] for row in result["history"]] == [str(term) for term in range(175, 167, -1)]
    assert any(call["schema_name"] is None for call in calls)
