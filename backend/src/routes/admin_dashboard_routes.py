from __future__ import annotations

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.auth import require_admin
from domains.dashboard import get_dashboard_overview


def register(router: Router) -> None:
    router.add("GET", "/api/admin/dashboard", overview, guard=require_admin)


def overview(ctx: RequestContext) -> None:
    ctx.send_json(get_dashboard_overview(ctx.db_path))
