from __future__ import annotations

from http import HTTPStatus

from admin.crud import delete_draw, list_draws, save_draw
from db import connect

from app_http.request_context import RequestContext
from app_http.router import Router


def register(router: Router) -> None:
    router.add("GET", "/api/admin/draws", list_draw_routes)
    router.add("POST", "/api/admin/draws", create_draw)
    router.add_prefix(None, "/api/admin/draws/", draw_detail)
    router.add("GET", "/api/admin/lottery-draws/latest-term", latest_term)


def list_draw_routes(ctx: RequestContext) -> None:
    limit = int(ctx.query_value("limit", ctx.query_value("page_size", "20")) or 20)
    page = int(ctx.query_value("page", "1") or 1)
    offset = (max(page, 1) - 1) * limit
    lottery_type_id_raw = ctx.query_value("lottery_type_id", None)
    lottery_type_id = int(lottery_type_id_raw) if lottery_type_id_raw else None
    ctx.send_json(list_draws(ctx.db_path, limit=limit, offset=offset, lottery_type_id=lottery_type_id))


def create_draw(ctx: RequestContext) -> None:
    ctx.send_json({"draw": save_draw(ctx.db_path, ctx.read_json())}, HTTPStatus.CREATED)


def draw_detail(ctx: RequestContext) -> None:
    draw_id = int(ctx.path.split("/")[-1])
    if ctx.method in {"PUT", "PATCH"}:
        ctx.send_json({"draw": save_draw(ctx.db_path, ctx.read_json(), draw_id)})
        return
    if ctx.method == "DELETE":
        delete_draw(ctx.db_path, draw_id)
        ctx.send_json({"ok": True})
        return
    raise KeyError("接口不存在")


def latest_term(ctx: RequestContext) -> None:
    lt_id = int(ctx.query_value("lottery_type_id", "1") or 1)
    with connect(ctx.db_path) as conn:
        row = conn.execute(
            """
            SELECT year, term, draw_time
            FROM lottery_draws
            WHERE lottery_type_id = ?
              AND is_opened = 1
            ORDER BY year DESC, term DESC, id DESC
            LIMIT 1
            """,
            (lt_id,),
        ).fetchone()
        if row:
            ctx.send_json(
                {
                    "year": int(row["year"]),
                    "term": int(row["term"]),
                    "draw_time": str(row["draw_time"] or ""),
                }
            )
            return
        ctx.send_json({"year": 0, "term": 0, "draw_time": ""})
