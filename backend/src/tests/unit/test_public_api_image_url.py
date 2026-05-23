from __future__ import annotations

from io import BytesIO
from http import HTTPStatus

from app_http.response import ResponseWriter
from public.api import serialize_public_history_row


def test_serialize_public_history_row_exposes_image_url():
    row = {
        "year": "2026",
        "term": "123",
        "title": "image-title",
        "content": "01 02 03",
        "image_url": "/data/Images/mode_478/prediction/mode_478_type3_2026123_web4.jpg",
        "web_id": 4,
        "res_code": "",
        "res_sx": "",
        "draw_is_opened": False,
    }

    result = serialize_public_history_row(row)

    assert result["image_url"] == "/uploads/mode_478/prediction/mode_478_type3_2026123_web4.jpg"
    assert result["raw"]["image_url"] == row["image_url"]


class _DummyHandler:
    def __init__(self) -> None:
        self.status = None
        self.headers: list[tuple[str, str]] = []
        self.wfile = BytesIO()

    def send_response(self, status) -> None:
        self.status = status

    def send_header(self, key: str, value: str) -> None:
        self.headers.append((key, value))

    def end_headers(self) -> None:
        return


def test_serve_upload_supports_nested_relative_paths(tmp_path):
    base_dir = tmp_path / "Images"
    target = base_dir / "mode_474" / "prediction" / "mode_474_type3_2026144_web5.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"fake-image-data")

    handler = _DummyHandler()
    writer = ResponseWriter(handler)

    writer.serve_upload("/uploads/mode_474/prediction/mode_474_type3_2026144_web5.jpg", base_dir)

    assert handler.status == HTTPStatus.OK
    assert handler.wfile.getvalue() == b"fake-image-data"


def test_serve_upload_rejects_path_traversal(tmp_path):
    base_dir = tmp_path / "Images"
    base_dir.mkdir(parents=True, exist_ok=True)
    escaped = tmp_path / "escaped.jpg"
    escaped.write_bytes(b"nope")

    handler = _DummyHandler()
    writer = ResponseWriter(handler)

    writer.serve_upload("/uploads/../escaped.jpg", base_dir)

    assert handler.status == HTTPStatus.NOT_FOUND
