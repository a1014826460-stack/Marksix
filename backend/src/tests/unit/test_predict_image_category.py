from __future__ import annotations

from predict import mechanisms


def test_image_category_reexports_window_formatter():
    from predict.categories import image

    assert mechanisms.format_window_content is image.format_window_content


def test_window_formatter_preserves_existing_payload_shape(monkeypatch):
    from predict.categories import image

    monkeypatch.setattr(
        image,
        "latest_window_metadata",
        lambda _conn, _table_name: {
            "start": "2026001",
            "end": "2026007",
            "image_url": "/images/window.png",
        },
    )

    formatter = image.format_window_content(lambda labels, _conn: ",".join(labels), "mode_payload_99")

    assert formatter(("鼠", "牛"), object()) == {
        "start": "2026001",
        "end": "2026007",
        "content": "鼠,牛",
        "image_url": "/images/window.png",
    }
