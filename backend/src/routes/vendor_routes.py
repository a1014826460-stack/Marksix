from __future__ import annotations

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.security import MAX_PUBLIC_HISTORY_LIMIT, parse_bounded_int
from vendor.homepage_modules import build_vendor_homepage_modules, SUPPORTED_MODULE_KEYS


def register(router: Router) -> None:
    router.add("GET", "/api/vendor/homepage-modules", homepage_modules)


def homepage_modules(ctx: RequestContext) -> None:
    raw_site_id = ctx.query_value("site_id")
    if raw_site_id in (None, ""):
        raise ValueError("site_id is required")
    site_id = int(raw_site_id)
    history_limit = parse_bounded_int(
        ctx.query_value("history_limit", "8"),
        default=8,
        maximum=MAX_PUBLIC_HISTORY_LIMIT,
        field_name="history_limit",
    )
    lottery_type_raw = ctx.query_value("lottery_type")
    lottery_type = int(lottery_type_raw) if lottery_type_raw not in (None, "") else None
    requested_modules = [
        item.strip()
        for item in str(ctx.query_value("modules", "") or "").split(",")
        if item.strip()
    ]
    if requested_modules:
        invalid = [item for item in requested_modules if item not in SUPPORTED_MODULE_KEYS]
        if invalid:
            raise ValueError(f"unsupported modules: {', '.join(invalid)}")
    ctx.send_json(
        build_vendor_homepage_modules(
            ctx.db_path,
            site_id=site_id,
            lottery_type=lottery_type,
            module_keys=requested_modules or None,
            history_limit=history_limit,
        )
    )
