from __future__ import annotations

from http import HTTPStatus

from app_http.request_context import RequestContext
from app_http.router import Router


def register(router: Router, *, admin_html: str, legacy_images_dir) -> None:
    router.add("GET", "/", root)
    router.add("GET", "/admin", lambda ctx: admin(ctx, admin_html))
    router.add("GET", "/health", health)
    router.add("GET", "/health/live", liveness)
    router.add("GET", "/health/ready", readiness)
    router.add("GET", "/health/dependencies", dependencies)
    router.add("GET", "/api/health", api_health)
    router.add_prefix("GET", "/uploads/", lambda ctx: uploads(ctx, legacy_images_dir))


def root(ctx: RequestContext) -> None:
    ctx.redirect("/admin")


def admin(ctx: RequestContext, admin_html: str) -> None:
    ctx.send_html(admin_html)


def health(ctx: RequestContext) -> None:
    detect_database_engine = ctx.state["detect_database_engine"]
    ctx.send_json({"status": "ok", "engine": detect_database_engine(ctx.db_path)})


def liveness(ctx: RequestContext) -> None:
    """Report only HTTP process availability for container restarts."""
    ctx.send_json({"ok": True, "status": "alive"})


def _dependency_payload(ctx: RequestContext) -> dict:
    dependency_health = ctx.state["dependency_health"]
    return dependency_health(ctx.write_db_path, ctx.read_db_path)


def readiness(ctx: RequestContext) -> None:
    payload = _dependency_payload(ctx)
    write_available = bool(payload.get("database", {}).get("write", {}).get("ok"))
    ctx.send_json(payload, HTTPStatus.OK if write_available else HTTPStatus.SERVICE_UNAVAILABLE)


def dependencies(ctx: RequestContext) -> None:
    payload = _dependency_payload(ctx)
    ctx.send_json(payload, HTTPStatus.OK if payload["ok"] else HTTPStatus.SERVICE_UNAVAILABLE)


def api_health(ctx: RequestContext) -> None:
    database_summary = ctx.state["database_summary"]
    scheduler_worker_health = ctx.state["scheduler_worker_health"]
    lottery_draw_health = ctx.state["lottery_draw_health"]
    ctx.send_json(
        {
            "ok": True,
            "summary": database_summary(ctx.db_path),
            "scheduler_worker": scheduler_worker_health(ctx.db_path),
            "draws": lottery_draw_health(ctx.db_path),
        }
    )


def uploads(ctx: RequestContext, legacy_images_dir) -> None:
    ctx.serve_upload(ctx.path, legacy_images_dir)
