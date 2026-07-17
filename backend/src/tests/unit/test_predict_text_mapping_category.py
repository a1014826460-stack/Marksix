from __future__ import annotations

from predict import mechanisms


def test_text_mapping_category_reexports_text_helpers():
    from predict.categories import text_mapping

    assert mechanisms.format_text_history_mapping is text_mapping.format_text_history_mapping
    assert mechanisms.random_text_pool_row is text_mapping.random_text_pool_row
    assert mechanisms.format_text_pool_jiexi is text_mapping.format_text_pool_jiexi
    assert mechanisms.format_humor_tail_groups is text_mapping.format_humor_tail_groups
    assert mechanisms.format_juzi_title is text_mapping.format_juzi_title


def test_text_history_formatter_falls_back_when_mapping_row_missing(monkeypatch):
    from predict.categories import text_mapping

    monkeypatch.setattr(text_mapping, "random_text_history_mapping_row", lambda *_args, **_kwargs: None)

    formatter = text_mapping.format_text_history_mapping("test-title", 244)

    assert formatter(("rat",), object()) == {
        "title": "test-title",
        "content": "test-title",
        "code": "",
        "sx": "",
        "_labels": ["rat"],
    }


def test_text_pool_jiexi_prefers_history_mapping_payload(monkeypatch):
    from predict.categories import text_mapping

    monkeypatch.setattr(
        text_mapping,
        "random_text_history_mapping_row",
        lambda *_args, **_kwargs: {"title": "history-title", "content": "history-content", "jiexi": "history-jiexi"},
    )
    monkeypatch.setattr(text_mapping, "text_history_row_payload", lambda row: dict(row))
    monkeypatch.setattr(text_mapping, "table_output_columns", lambda *_args, **_kwargs: ("title", "content", "jiexi"))

    formatter = text_mapping.format_text_pool_jiexi("fallback-title", "一句真言")

    assert formatter(("rat",), object()) == {
        "title": "history-title",
        "content": "history-content",
        "jiexi": "history-jiexi",
        "_labels": ["rat"],
    }


def test_humor_tail_groups_fall_back_to_text_pool(monkeypatch):
    from predict.categories import text_mapping

    monkeypatch.setattr(text_mapping, "random_text_history_mapping_row", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        text_mapping,
        "random_text_pool_row",
        lambda *_args, **_kwargs: {"title": "pool-title", "content": "pool-content"},
    )
    monkeypatch.setattr(text_mapping.random, "sample", lambda values, count: list(values)[:count])

    result = text_mapping.format_humor_tail_groups(("1尾",), object())

    assert result["title"] == "pool-title"
    assert result["content"] == "pool-content"
    assert len(result["code"]) == 6


def test_juzi_title_uses_history_title_when_available(monkeypatch):
    from predict.categories import text_mapping

    monkeypatch.setattr(
        text_mapping,
        "random_text_history_mapping_row",
        lambda *_args, **_kwargs: {"title": "history-title"},
    )

    assert text_mapping.format_juzi_title(("rat",), object()) == {
        "title": "history-title",
        "_labels": ["rat"],
    }
