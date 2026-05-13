from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.errors import NotFoundError, ValidationError, ForbiddenError
from db import connect

from .request_context import RequestContext


@dataclass(frozen=True)
class SiteContext:
    """站点上下文——多站点隔离的核心数据结构。

    Attributes:
        site_id: managed_sites 表内部主键
        web_id: 站点业务 ID，对应旧资料表中的 web 字段
        name: 站点名称
        domain: 站点域名
        lottery_type_id: 关联的彩种 ID
        enabled: 站点是否启用
    """
    site_id: int
    web_id: int
    name: str
    domain: str | None
    lottery_type_id: int | None
    enabled: bool


@dataclass(frozen=True)
class SiteRouteContext:
    site_id: int
    parts: list[str]


def parse_site_route_context(ctx: RequestContext) -> SiteRouteContext:
    parts = ctx.path.split("/")
    if len(parts) < 5:
        raise KeyError("站点接口不存在")
    return SiteRouteContext(site_id=int(parts[4]), parts=parts)


def _coalesce_site_id(path_site_id: int | None, query: dict[str, list[str]] | None, body: dict[str, Any] | None) -> int | None:
    if path_site_id is not None:
        return int(path_site_id)
    for candidate in (
        (query or {}).get("site_id", [None])[0],
        body.get("site_id") if body else None,
    ):
        if candidate in (None, ""):
            continue
        return int(candidate)
    return None


def resolve_site_context(
    db_path: str | Path,
    path_site_id: int | None = None,
    query: dict[str, list[str]] | None = None,
    body: dict[str, Any] | None = None,
    host: str | None = None,
) -> SiteContext:
    """解析站点上下文。

    解析优先级：path_site_id > query/body 中的 site_id > domain/host 匹配。

    不会静默回退到"第一个站点"。如果没有明确的 site_id 且无法通过
    domain/host 匹配，将抛出 ValidationError。

    Raises:
        ValidationError: 无法确定站点上下文（无 site_id 且无匹配 domain）
        NotFoundError: 指定的 site_id 对应的站点不存在
    """
    resolved_site_id = _coalesce_site_id(path_site_id, query, body)
    normalized_host = str(host or "").strip().lower()

    with connect(db_path) as conn:
        row = None
        if resolved_site_id is not None:
            row = conn.execute(
                """
                SELECT id, web_id, name, domain, lottery_type_id, enabled
                FROM managed_sites
                WHERE id = ?
                LIMIT 1
                """,
                (resolved_site_id,),
            ).fetchone()
        elif normalized_host:
            row = conn.execute(
                """
                SELECT id, web_id, name, domain, lottery_type_id, enabled
                FROM managed_sites
                WHERE LOWER(COALESCE(domain, '')) = ?
                ORDER BY id
                LIMIT 1
                """,
                (normalized_host,),
            ).fetchone()
        else:
            raise ValidationError(
                "无法确定站点上下文：缺少 site_id 且无法通过 domain/host 匹配站点。"
                "请显式传入 site_id 参数。"
            )

        if not row:
            raise NotFoundError("未找到站点配置")
        if row["web_id"] in (None, ""):
            raise ValidationError(f"site_id={row['id']} 缺少 web_id 配置")
        return SiteContext(
            site_id=int(row["id"]),
            web_id=int(row["web_id"]),
            name=str(row["name"] or ""),
            domain=str(row["domain"] or None) if row["domain"] else None,
            lottery_type_id=int(row["lottery_type_id"]) if row["lottery_type_id"] else None,
            enabled=bool(row["enabled"]),
        )


def resolve_first_site_context(db_path: str | Path) -> SiteContext:
    """显式回退到第一个启用站点（仅限少数明确允许的兼容场景）。

    高风险接口（管理接口、站点相关接口）必须使用 resolve_site_context
    并显式传入 site_id，不得依赖此函数。
    """
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, web_id, name, domain, lottery_type_id, enabled
            FROM managed_sites
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()
        if not row:
            raise NotFoundError("未找到任何站点配置")
        if row["web_id"] in (None, ""):
            raise ValidationError(f"site_id={row['id']} 缺少 web_id 配置")
        return SiteContext(
            site_id=int(row["id"]),
            web_id=int(row["web_id"]),
            name=str(row["name"] or ""),
            domain=str(row["domain"] or None) if row["domain"] else None,
            lottery_type_id=int(row["lottery_type_id"]) if row["lottery_type_id"] else None,
            enabled=bool(row["enabled"]),
        )


def resolve_site_context_from_request(
    ctx: RequestContext,
    path_site_id: int | None = None,
) -> SiteContext:
    """从 RequestContext 解析站点上下文的便捷函数。

    自动提取 Host、query、body 参数，
    是路由处理器中最常用的站点解析入口。
    """
    host = ctx.headers.get("Host", "")
    return resolve_site_context(
        db_path=ctx.db_path,
        path_site_id=path_site_id,
        query=ctx.query,
        body=ctx.body if ctx._body is not None else None,
        host=host,
    )


def require_site_access(ctx: RequestContext, site_id: int) -> SiteContext:
    """校验并返回指定站点的上下文。

    先解析 SiteContext，再校验当前用户是否有权限访问该站点。
    第一阶段允许 super_admin/admin 访问所有站点，
    但接口结构预留 site_admin/operator/viewer 角色。
    """
    site_ctx = resolve_site_context(db_path=ctx.db_path, path_site_id=site_id)
    if not site_ctx.enabled:
        raise ForbiddenError(f"站点 site_id={site_id} 已被停用")
    # 后续可在此处加入角色级别的站点权限判断
    return site_ctx


def validate_web_matches_site(site_ctx: SiteContext, web_value: Any) -> None:
    """校验 query/body 中的 web/web_id 必须等于当前站点的 web_id。

    规则：如果请求中显式传了 web/web_id，则必须与站点 web_id 一致；
    不传则放行（后续使用站点 web_id 作为默认值）。
    """
    if web_value in (None, ""):
        return
    try:
        normalized_web = int(str(web_value).strip())
    except (TypeError, ValueError) as exc:
        raise ValidationError("web/web_id 必须为整数") from exc
    if normalized_web != int(site_ctx.web_id):
        raise ForbiddenError(
            f"当前站点 site_id={site_ctx.site_id} 只允许访问 web_id={site_ctx.web_id} 的数据"
        )


def extract_site_web_value(query: dict[str, list[str]] | None = None, body: dict[str, Any] | None = None) -> Any:
    query = query or {}
    body = body or {}
    for key in ("web", "web_id"):
        if key in body and body[key] not in (None, ""):
            return body[key]
        value = query.get(key, [None])[0]
        if value not in (None, ""):
            return value
    return None
