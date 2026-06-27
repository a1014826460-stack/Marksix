from __future__ import annotations

from tests.helpers.api_contract import make_ctx, response_json


def test_make_ctx_parses_query_and_body():
    ctx = make_ctx(
        "/api/example?page=2",
        method="POST",
        payload={"name": "demo"},
    )

    assert ctx.path == "/api/example"
    assert ctx.query_value("page") == "2"
    assert ctx.body == {"name": "demo"}


def test_response_json_reads_written_payload():
    ctx = make_ctx("/api/example")

    ctx.send_json({"ok": True})

    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {"ok": True}
