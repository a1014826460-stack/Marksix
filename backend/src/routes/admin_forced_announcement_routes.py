from __future__ import annotations

from http import HTTPStatus

from app_http.auth import require_super_admin
from app_http.request_context import RequestContext
from app_http.router import Router
from domains.announcements.service import (
    create_forced_announcement,
    delete_forced_announcement,
    get_forced_announcement,
    list_forced_announcements,
    update_forced_announcement,
)


def register(router: Router) -> None:
    router.add(
        "GET",
        "/api/admin/forced-announcements",
        list_announcements,
        guard=require_super_admin,
    )
    router.add(
        "POST",
        "/api/admin/forced-announcements",
        create_announcement,
        guard=require_super_admin,
    )
    router.add_regex(
        None,
        r"^/api/admin/forced-announcements/\d+$",
        announcement_detail,
        guard=require_super_admin,
    )


def list_announcements(ctx: RequestContext) -> None:
    ctx.send_json({"announcements": list_forced_announcements(ctx.db_path)})


def create_announcement(ctx: RequestContext) -> None:
    announcement = create_forced_announcement(ctx.db_path, ctx.read_json())
    ctx.send_json({"announcement": announcement}, HTTPStatus.CREATED)


def announcement_detail(ctx: RequestContext) -> None:
    announcement_id = int(ctx.path.rsplit("/", 1)[-1])
    if ctx.method == "GET":
        ctx.send_json(
            {"announcement": get_forced_announcement(ctx.db_path, announcement_id)}
        )
        return
    if ctx.method in {"PUT", "PATCH"}:
        ctx.send_json(
            {
                "announcement": update_forced_announcement(
                    ctx.db_path,
                    announcement_id,
                    ctx.read_json(),
                )
            }
        )
        return
    if ctx.method == "DELETE":
        delete_forced_announcement(ctx.db_path, announcement_id)
        ctx.send_json({"ok": True})
        return
    raise KeyError("强制公告接口不存在")

