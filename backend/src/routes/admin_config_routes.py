from __future__ import annotations

import re

from runtime_config import (
    batch_update_configs,
    get_config_effective,
    get_config_groups,
    get_config_history,
    list_configs_effective,
    list_system_configs,
    reset_config,
    upsert_system_config,
    validate_config_value,
)

from http.request_context import RequestContext
from http.router import Router


def register(router: Router) -> None:
    router.add("GET", "/api/admin/system-config", system_config_list)
    router.add("GET", "/api/admin/configs/groups", config_groups)
    router.add("POST", "/api/admin/configs/batch-update", batch_update)
    router.add("GET", "/api/admin/configs/effective", configs_effective)
    router.add_prefix("GET", "/api/admin/configs/effective/", config_effective_detail)
    router.add("GET", "/api/admin/configs/history", config_history)
    router.add_regex("POST", r"^/api/admin/configs/.+/reset$", config_reset)
    router.add_prefix(None, "/api/admin/system-config/", system_config_detail)


def system_config_list(ctx: RequestContext) -> None:
    prefix = ctx.query_value("prefix", "") or ""
    include_secrets = (ctx.query_value("include_secrets", "0") or "0") in {"1", "true", "True"}
    ctx.send_json(
        {
            "configs": list_system_configs(
                ctx.db_path,
                prefix=prefix,
                include_secrets=include_secrets,
            )
        }
    )


def config_groups(ctx: RequestContext) -> None:
    ctx.send_json({"groups": get_config_groups()})


def batch_update(ctx: RequestContext) -> None:
    body = ctx.read_json()
    updates = body.get("updates", [])
    if not isinstance(updates, list):
        raise ValueError("updates 必须是数组")
    user = ctx.state.get("current_user")
    for item in updates:
        key = str(item.get("key", ""))
        value = item.get("value")
        value_type = str(item.get("value_type", ""))
        if value_type:
            is_valid, err_msg = validate_config_value(key, value, value_type)
            if not is_valid:
                raise ValueError(f"配置 '{key}': {err_msg}")
    changed_by = user.get("username", "unknown") if user else "unknown"
    ctx.send_json(batch_update_configs(ctx.db_path, updates, changed_by=changed_by))


def configs_effective(ctx: RequestContext) -> None:
    ctx.send_json(
        {
            "configs": list_configs_effective(
                ctx.db_path,
                group=ctx.query_value("group", "") or "",
                keyword=ctx.query_value("keyword", "") or "",
                source=ctx.query_value("source", "") or "",
            )
        }
    )


def config_effective_detail(ctx: RequestContext) -> None:
    config_key = ctx.path.split("/api/admin/configs/effective/", 1)[1].strip()
    ctx.send_json(get_config_effective(ctx.db_path, config_key))


def config_history(ctx: RequestContext) -> None:
    config_key = ctx.query_value("key", "") or ""
    page = int(ctx.query_value("page", "1") or 1)
    page_size = min(int(ctx.query_value("page_size", "30") or 30), 200)
    ctx.send_json(get_config_history(ctx.db_path, key=config_key, page=page, page_size=page_size))


def config_reset(ctx: RequestContext) -> None:
    config_key = ctx.path.rsplit("/", 2)[-2]
    user = ctx.state.get("current_user")
    changed_by = user.get("username", "unknown") if user else "unknown"
    ctx.send_json({"config": reset_config(ctx.db_path, config_key, changed_by=changed_by)})


def system_config_detail(ctx: RequestContext) -> None:
    if ctx.method not in {"PUT", "PATCH"}:
        raise KeyError("接口不存在")
    config_key = ctx.path.split("/api/admin/system-config/", 1)[1].strip()
    body = ctx.read_json()
    value = body.get("value")
    value_type = str(body.get("value_type") or "")
    if value_type:
        is_valid, err_msg = validate_config_value(config_key, value, value_type)
        if not is_valid:
            raise ValueError(err_msg)
    user = ctx.state.get("current_user")
    changed_by = user.get("username", "unknown") if user else "unknown"
    ctx.send_json(
        {
            "config": upsert_system_config(
                ctx.db_path,
                key=config_key,
                value=value,
                value_type=value_type or None,
                description=str(body.get("description") or "") or None,
                is_secret=body.get("is_secret"),
                changed_by=changed_by,
                change_reason=str(body.get("change_reason") or ""),
            )
        }
    )
