from __future__ import annotations

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.auth import require_admin
from domains.traffic.service import (
    get_traffic_overview,
    get_traffic_sites,
    get_traffic_timeseries,
)


def register(router: Router) -> None:
    router.add("GET", "/api/admin/traffic/overview", overview, guard=require_admin)
    router.add("GET", "/api/admin/traffic/sites", sites, guard=require_admin)
    router.add("GET", "/api/admin/traffic/timeseries", timeseries, guard=require_admin)


def _date_from(ctx: RequestContext) -> str | None:
    return ctx.query_value("date_from")


def _date_to(ctx: RequestContext) -> str | None:
    return ctx.query_value("date_to")


def overview(ctx: RequestContext) -> None:
    ctx.send_json(
        get_traffic_overview(
            ctx.db_path,
            date_from=_date_from(ctx),
            date_to=_date_to(ctx),
        )
    )


def sites(ctx: RequestContext) -> None:
    ctx.send_json(
        get_traffic_sites(
            ctx.db_path,
            date_from=_date_from(ctx),
            date_to=_date_to(ctx),
        )
    )


def timeseries(ctx: RequestContext) -> None:
    ctx.send_json(
        get_traffic_timeseries(
            ctx.db_path,
            date_from=_date_from(ctx),
            date_to=_date_to(ctx),
        )
    )
