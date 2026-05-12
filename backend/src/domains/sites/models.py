"""站点领域数据结构定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ManagedSite:
    """托管站点领域模型。

    Attributes:
        id: 站点内部主键（managed_sites.id）
        web_id: 站点业务 ID（对应旧资料表中的 web 字段）
        name: 站点名称
        domain: 站点域名
        lottery_type_id: 关联的彩种 ID
        enabled: 站点是否启用
        start_web_id: 旧站抓取范围起始值（兼容字段）
        end_web_id: 旧站抓取范围结束值（兼容字段）
        manage_url_template: 管理页面 URL 模板
        modes_data_url: 资料数据 URL
        token: 站点 API token
        request_limit: 请求频率限制
        request_delay: 请求间隔（秒）
        announcement: 站点公告
        notes: 备注
    """
    id: int
    web_id: int
    name: str
    domain: str | None = None
    lottery_type_id: int | None = None
    enabled: bool = True
    start_web_id: int = 1
    end_web_id: int = 10
    manage_url_template: str = ""
    modes_data_url: str = ""
    token: str = ""
    request_limit: int = 250
    request_delay: float = 0.5
    announcement: str = ""
    notes: str = ""

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ManagedSite":
        """从数据库行字典构建领域模型。"""
        return cls(
            id=int(row["id"]),
            web_id=int(row.get("web_id") or row.get("start_web_id") or 1),
            name=str(row.get("name") or ""),
            domain=str(row.get("domain") or "") if row.get("domain") else None,
            lottery_type_id=int(row["lottery_type_id"]) if row.get("lottery_type_id") else None,
            enabled=bool(row.get("enabled")),
            start_web_id=int(row.get("start_web_id") or 1),
            end_web_id=int(row.get("end_web_id") or 10),
            manage_url_template=str(row.get("manage_url_template") or ""),
            modes_data_url=str(row.get("modes_data_url") or ""),
            token=str(row.get("token") or ""),
            request_limit=int(row.get("request_limit") or 250),
            request_delay=float(row.get("request_delay") or 0.5),
            announcement=str(row.get("announcement") or ""),
            notes=str(row.get("notes") or ""),
        )

    def to_public_dict(self) -> dict[str, Any]:
        """转换为对外安全的字典（隐藏完整 token）。"""
        return {
            "id": self.id,
            "web_id": self.web_id,
            "name": self.name,
            "domain": self.domain or "",
            "lottery_type_id": self.lottery_type_id,
            "enabled": self.enabled,
            "start_web_id": self.start_web_id,
            "end_web_id": self.end_web_id,
            "manage_url_template": self.manage_url_template,
            "modes_data_url": self.modes_data_url,
            "token_present": bool(self.token),
            "token_preview": f"{self.token[:8]}..." if self.token else "",
            "request_limit": self.request_limit,
            "request_delay": self.request_delay,
            "announcement": self.announcement,
            "notes": self.notes,
        }
