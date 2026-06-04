"""Managed site data model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ManagedSite:
    id: int
    web_id: int
    name: str
    domain: str | None = None
    lottery_type_id: int | None = None
    enabled: bool = True
    blueprint_name: str = "default"
    announcement: str = ""
    notes: str = ""

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ManagedSite":
        return cls(
            id=int(row["id"]),
            web_id=int(row.get("web_id") or row["id"]),
            name=str(row.get("name") or ""),
            domain=str(row.get("domain") or "") if row.get("domain") else None,
            lottery_type_id=int(row["lottery_type_id"]) if row.get("lottery_type_id") else None,
            enabled=bool(row.get("enabled")),
            blueprint_name=str(row.get("blueprint_name") or "default"),
            announcement=str(row.get("announcement") or ""),
            notes=str(row.get("notes") or ""),
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "web_id": self.web_id,
            "name": self.name,
            "domain": self.domain or "",
            "lottery_type_id": self.lottery_type_id,
            "enabled": self.enabled,
            "blueprint_name": self.blueprint_name,
            "announcement": self.announcement,
            "notes": self.notes,
        }
