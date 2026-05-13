from __future__ import annotations

from http import HTTPStatus

from app_http.request_context import RequestContext
from app_http.router import Router

from .common import get_background_job


def register(router: Router) -> None:
    router.add_prefix("GET", "/api/admin/jobs/", get_job)


def get_job(ctx: RequestContext) -> None:
    job_id = ctx.path.split("/")[-1]
    job = get_background_job(job_id)
    if job is None:
        ctx.send_error_json(HTTPStatus.NOT_FOUND, f"job_id={job_id} 不存在或已过期")
        return
    ctx.send_json(job)
