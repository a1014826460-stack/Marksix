from __future__ import annotations

from crawler.crawler_service import run_hk_crawler, run_macau_crawler

from app_http.request_context import RequestContext
from app_http.router import Router


def register(router: Router) -> None:
    router.add("POST", "/api/admin/crawler/run-hk", run_hk)
    router.add("POST", "/api/admin/crawler/run-macau", run_macau)
    router.add("POST", "/api/admin/crawler/run-all", run_all)


def run_hk(ctx: RequestContext) -> None:
    ctx.send_json(run_hk_crawler(ctx.db_path))


def run_macau(ctx: RequestContext) -> None:
    ctx.send_json(run_macau_crawler(ctx.db_path))


def run_all(ctx: RequestContext) -> None:
    errors: list[str] = []
    results: dict[str, object] = {}
    for label, fn in [("hk", run_hk_crawler), ("macau", run_macau_crawler)]:
        try:
            results[label] = fn(ctx.db_path)
        except Exception as exc:
            errors.append(f"{label}: {exc}")
    results["taiwan"] = {"message": "台湾彩数据需在管理后台手工录入"}
    ctx.send_json({"results": results, "errors": errors if errors else None})
