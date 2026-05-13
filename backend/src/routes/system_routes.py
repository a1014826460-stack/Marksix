from __future__ import annotations

from app_http.request_context import RequestContext
from app_http.router import Router


def register(router: Router, *, admin_html: str, legacy_images_dir) -> None:
    router.add("GET", "/", root)
    router.add("GET", "/admin", lambda ctx: admin(ctx, admin_html))
    router.add("GET", "/health", health)
    router.add("GET", "/api/health", api_health)
    router.add_prefix("GET", "/uploads/", lambda ctx: uploads(ctx, legacy_images_dir))


def root(ctx: RequestContext) -> None:
    ctx.redirect("/admin")


def admin(ctx: RequestContext, admin_html: str) -> None:
    ctx.send_html(admin_html)


def health(ctx: RequestContext) -> None:
    detect_database_engine = ctx.state["detect_database_engine"]
    ctx.send_json({"status": "ok", "engine": detect_database_engine(ctx.db_path)})


def api_health(ctx: RequestContext) -> None:
    database_summary = ctx.state["database_summary"]
    ctx.send_json({"ok": True, "summary": database_summary(ctx.db_path)})


def uploads(ctx: RequestContext, legacy_images_dir) -> None:
    ctx.serve_upload(ctx.path, legacy_images_dir)
