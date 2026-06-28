from __future__ import annotations

from unittest.mock import patch

from routes import admin_payload_routes
from tests.helpers.api_contract import make_ctx, response_json


def test_site_payload_update_checks_row_ownership_before_preserving_response_shape():
    ctx = make_ctx(
        "/api/admin/sites/7/mode-payload/mode_payload_43/12?source=public",
        method="PATCH",
        payload={"content": "updated"},
    )
    site = type("Site", (), {"site_id": 7, "web_id": 6})()

    with patch("routes.admin_payload_routes.resolve_site_context", return_value=site), \
         patch("routes.admin_payload_routes.validate_web_matches_site") as validate_web, \
         patch("routes.admin_payload_routes.ensure_mode_payload_row_belongs_to_site") as ensure_row, \
         patch("routes.admin_payload_routes.update_mode_payload_row", return_value={"row": {"id": 12}}) as update_row:
        admin_payload_routes.site_payload_detail(ctx)

    validate_web.assert_called_once()
    ensure_row.assert_called_once_with(
        ctx.db_path,
        "mode_payload_43",
        "12",
        source="public",
        site_web_id=6,
    )
    update_row.assert_called_once_with(
        ctx.db_path,
        "mode_payload_43",
        "12",
        {"content": "updated", "web": 6, "web_id": 6},
        source="public",
    )
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {"row": {"id": 12}}


def test_site_payload_delete_checks_row_ownership_before_preserving_response_shape():
    ctx = make_ctx(
        "/api/admin/sites/7/mode-payload/mode_payload_43/12?source=created",
        method="DELETE",
    )
    site = type("Site", (), {"site_id": 7, "web_id": 6})()

    with patch("routes.admin_payload_routes.resolve_site_context", return_value=site), \
         patch("routes.admin_payload_routes.validate_web_matches_site"), \
         patch("routes.admin_payload_routes.ensure_mode_payload_row_belongs_to_site") as ensure_row, \
         patch("routes.admin_payload_routes.delete_mode_payload_row") as delete_row:
        admin_payload_routes.site_payload_detail(ctx)

    ensure_row.assert_called_once_with(
        ctx.db_path,
        "mode_payload_43",
        "12",
        source="created",
        site_web_id=6,
    )
    delete_row.assert_called_once_with(
        ctx.db_path,
        "mode_payload_43",
        "12",
        source="created",
    )
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {"ok": True}
