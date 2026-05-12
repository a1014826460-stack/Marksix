from __future__ import annotations

from typing import Any

from logger import get_logger
from predict.common import predict as run_prediction
from predict.mechanisms import get_prediction_config, list_prediction_configs, set_mechanism_status
from runtime_config import get_config

from admin.prediction import (
    build_prediction_api_response,
    resolve_prediction_request_safety,
)
from db import connect
from http import HTTPStatus
from http.auth import require_generation_access
from http.request_context import RequestContext
from http.router import Router
from http.site_context import (
    extract_site_web_value,
    resolve_site_context,
    validate_web_matches_site,
)


def register(router: Router) -> None:
    router.add("GET", "/api/predict/mechanisms", list_public_mechanisms)
    router.add_regex(None, r"^/api/predict/[^/]+$", run_mechanism_prediction)
    router.add("GET", "/api/admin/predict/mechanisms", list_admin_mechanisms)
    router.add_regex(None, r"^/api/admin/predict/mechanisms/[^/]+$", mechanism_status)


def list_public_mechanisms(ctx: RequestContext) -> None:
    ctx.send_json({"mechanisms": list_prediction_configs(ctx.db_path)})


def run_mechanism_prediction(ctx: RequestContext) -> None:
    if ctx.method not in {"GET", "POST"}:
        raise KeyError("接口不存在")
    require_generation_access(ctx)
    mechanism = ctx.path.split("/")[-1]
    body = ctx.read_json() if ctx.method == "POST" else {}

    def pick(name: str, default: Any = None) -> Any:
        if name in body:
            return body[name]
        snake = name.replace("-", "_")
        if snake in body:
            return body[snake]
        return ctx.query.get(snake, [default])[0]

    config = get_prediction_config(mechanism)
    default_target_hit_rate = float(get_config(ctx.db_path, "prediction.default_target_hit_rate", 0.65))
    site_ctx = None
    if pick("site_id") not in (None, ""):
        site_ctx = resolve_site_context(
            ctx.db_path,
            path_site_id=None,
            query=ctx.query,
            body=body,
        )
        validate_web_matches_site(site_ctx, extract_site_web_value(ctx.query, body))
    request_payload = {
        "res_code": pick("res_code"),
        "content": pick("content"),
        "source_table": pick("source_table"),
        "target_hit_rate": float(pick("target_hit_rate", default_target_hit_rate)),
        "lottery_type": pick("lottery_type"),
        "year": pick("year"),
        "term": pick("term"),
        "site_id": pick("site_id"),
        "web": str(site_ctx.web_id) if site_ctx else pick("web"),
    }
    if site_ctx and request_payload["lottery_type"] in (None, ""):
        request_payload["lottery_type"] = str(site_ctx.lottery_type_id)
    safety: dict[str, Any] | None = None
    effective_res_code = request_payload["res_code"]
    if (
        request_payload["lottery_type"] not in (None, "")
        and request_payload["year"] not in (None, "")
        and request_payload["term"] not in (None, "")
    ):
        with connect(ctx.db_path) as conn:
            effective_res_code, safety = resolve_prediction_request_safety(
                conn,
                lottery_type=request_payload["lottery_type"],
                year=request_payload["year"],
                term=request_payload["term"],
                res_code=request_payload["res_code"],
            )
    request_payload["res_code"] = effective_res_code
    result = run_prediction(
        config=config,
        res_code=effective_res_code,
        content=request_payload["content"],
        source_table=request_payload["source_table"],
        db_path=ctx.db_path,
        target_hit_rate=float(request_payload["target_hit_rate"]),
    )
    ctx.send_json(
        build_prediction_api_response(
            mechanism_key=mechanism,
            request_payload=request_payload,
            raw_result=result,
            safety=safety,
        )
    )


def list_admin_mechanisms(ctx: RequestContext) -> None:
    ctx.send_json({"mechanisms": list_prediction_configs(ctx.db_path)})


def mechanism_status(ctx: RequestContext) -> None:
    mechanism_key = ctx.path.split("/api/admin/predict/mechanisms/", 1)[1].rstrip("/")
    if not mechanism_key or mechanism_key == "status" or mechanism_key.endswith("/status"):
        raise KeyError("接口不存在")
    if ctx.method != "PATCH":
        ctx.send_error_json(HTTPStatus.METHOD_NOT_ALLOWED, "不支持的操作")
        return
    body = ctx.read_json()
    status_value = int(body.get("status", 1))
    set_mechanism_status(ctx.db_path, mechanism_key, status_value)
    user = ctx.state.get("current_user")
    username = user.get("username", "unknown") if user else "unknown"
    get_logger("admin").info(
        "mechanism '%s' status changed to %d by user=%s",
        mechanism_key,
        status_value,
        username,
    )
    ctx.send_json({"key": mechanism_key, "status": status_value})
