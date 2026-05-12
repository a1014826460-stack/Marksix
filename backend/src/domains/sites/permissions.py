"""站点权限判断——基于角色的访问控制。

角色体系（从高到低）：
  super_admin — 超级管理员，拥有全部权限
  admin       — 管理员，拥有全部管理权限
  site_admin  — 站点管理员，可管理指定站点
  operator    — 操作员，可查看和生成预测，但不可管理站点
  viewer      — 只读用户，仅可查看公开数据

当前实现：
  - super_admin / admin 拥有全部站点权限（向后兼容现有系统）
  - site_admin 可访问所有站点（站点粒度的权限控制预留接口）
  - operator 可查看数据、生成预测，但不可创建/更新/删除站点
  - viewer 仅可读取公开数据，不可执行任何管理操作

后续扩展方向：
  - 新增 site_permissions 表，将 site_admin 映射到具体站点
  - 在 managed_sites 上增加 created_by 字段，限制 operator 只能操作自己创建的站点
"""

from __future__ import annotations

from typing import Any

# ── 角色常量 ──────────────────────────────────────────

ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"
ROLE_SITE_ADMIN = "site_admin"
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"

# 拥有完整管理权限的角色
_ADMIN_ROLES = {ROLE_SUPER_ADMIN, ROLE_ADMIN}

# 可执行预测生成的角色（管理员 + 操作员）
_GENERATION_ROLES = {ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_SITE_ADMIN, ROLE_OPERATOR}

# 可查看后台数据的角色（所有已认证角色）
_VIEW_BACKEND_ROLES = {ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_SITE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER}


def _resolve_role(user: dict[str, Any] | None) -> str:
    """从用户字典中提取角色，未认证返回空字符串。"""
    if user is None:
        return ""
    return str(user.get("role") or "").strip().lower()


def is_admin(user: dict[str, Any] | None) -> bool:
    """判断是否为管理员（super_admin 或 admin）。"""
    return _resolve_role(user) in _ADMIN_ROLES


def can_access_site(user: dict[str, Any] | None, site_id: int) -> bool:
    """判断用户是否有权限访问指定站点。

    super_admin / admin: 全部站点
    site_admin / operator / viewer: 全部站点（站点粒度控制预留）
    未认证用户: 拒绝
    """
    role = _resolve_role(user)
    if not role:
        return False
    if role in _ADMIN_ROLES:
        return True
    # site_admin / operator / viewer 当前可访问所有站点
    # 后续通过 site_permissions 表进行站点粒度控制
    return role in _VIEW_BACKEND_ROLES


def can_manage_site(user: dict[str, Any] | None, site_id: int) -> bool:
    """判断用户是否有权限管理站点（创建/更新/删除）。

    只有 super_admin / admin / site_admin 可以管理站点。
    operator 和 viewer 不可管理。
    """
    role = _resolve_role(user)
    if not role:
        return False
    return role in {ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_SITE_ADMIN}


def can_generate_predictions(user: dict[str, Any] | None, site_id: int) -> bool:
    """判断用户是否有权限为指定站点生成预测资料。

    super_admin / admin / site_admin / operator 可生成预测。
    viewer 不可生成。
    """
    role = _resolve_role(user)
    if not role:
        return False
    return role in _GENERATION_ROLES


def can_view_backend(user: dict[str, Any] | None) -> bool:
    """判断用户是否有权限访问后台管理页面。"""
    return _resolve_role(user) in _VIEW_BACKEND_ROLES


def can_manage_users(user: dict[str, Any] | None) -> bool:
    """判断用户是否有权限管理其他用户。

    只有 super_admin / admin 可以管理用户。
    """
    return is_admin(user)


def can_manage_system_config(user: dict[str, Any] | None) -> bool:
    """判断用户是否有权限修改系统配置。

    只有 super_admin / admin 可以修改配置。
    """
    return is_admin(user)


def can_view_logs(user: dict[str, Any] | None) -> bool:
    """判断用户是否有权限查看系统日志。

    super_admin / admin / site_admin 可查看日志。
    """
    role = _resolve_role(user)
    return role in {ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_SITE_ADMIN}


def require_admin(user: dict[str, Any] | None) -> None:
    """要求管理员权限，否则抛出 ForbiddenError。"""
    from core.errors import ForbiddenError
    if not is_admin(user):
        raise ForbiddenError("需要管理员权限")


def require_site_management(user: dict[str, Any] | None, site_id: int) -> None:
    """要求站点管理权限，否则抛出 ForbiddenError。"""
    from core.errors import ForbiddenError
    if not can_manage_site(user, site_id):
        raise ForbiddenError("当前账号没有管理该站点的权限")


def require_generation_permission(user: dict[str, Any] | None, site_id: int) -> None:
    """要求预测生成权限，否则抛出 ForbiddenError。"""
    from core.errors import ForbiddenError
    if not can_generate_predictions(user, site_id):
        raise ForbiddenError("当前账号没有生成预测数据的权限")
