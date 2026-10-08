from __future__ import annotations

import hashlib

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.security import MAX_PUBLIC_HISTORY_LIMIT, parse_bounded_int
from cache.prediction_snapshots import KIND_HOMEPAGE, read_through
from vendor.homepage_modules import build_vendor_homepage_modules, SUPPORTED_MODULE_KEYS
from db import connect
from helpers import apply_public_result_gate


def register(router: Router) -> None:
    router.add("GET", "/api/vendor/homepage-modules", homepage_modules)


def homepage_modules(ctx: RequestContext) -> None:
    ctx.response.set_header("Cache-Control", "no-store")
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
    def build() -> dict:
        return build_vendor_homepage_modules(
            ctx.db_path,
            site_id=site_id,
            lottery_type=lottery_type,
            module_keys=requested_modules or None,
            history_limit=history_limit,
        )

    if lottery_type is None:
        # 彩种未显式给出时需要先解析站点彩种，键无法稳定，直接按原路径构建。
        _send_modules(ctx, build(), lottery_type)
        return

    selector = f"{lottery_type}-{history_limit}-{_modules_fingerprint(requested_modules)}"
    _send_modules(ctx,
        read_through(
            ctx.state.get("prediction_snapshots"),
            kind=KIND_HOMEPAGE,
            site_ref=f"site{site_id}",
            lottery_type_id=lottery_type,
            selector=selector,
            builder=build,
            db_path=ctx.db_path,
        ),
        lottery_type,
    )


def _send_modules(ctx: RequestContext, payload: dict, lottery_type: int | None) -> None:
    # Cached presentation data cannot authorize a result. Recheck every response.
    if lottery_type is None:
        site = payload.get("site") or {}
        resolved = site.get("lottery_type") if isinstance(site, dict) else None
        try:
            lottery_type = int(resolved) if int(resolved) in (1, 2, 3) else None
        except (TypeError, ValueError):
            lottery_type = None
    with connect(getattr(ctx, "write_db_path", ctx.db_path)) as conn:
        safe = apply_public_result_gate(conn, payload, default_lottery_type_id=lottery_type)
    ctx.send_json(safe)


def _modules_fingerprint(modules: list[str]) -> str:
    if not modules:
        return "all"
    joined = ",".join(sorted(modules))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]
