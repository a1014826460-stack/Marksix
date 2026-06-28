"""预测领域数据结构定义。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


@dataclass
class PredictionModule:
    """站点预测模块领域模型。

    Attributes:
        id: 模块 ID
        site_id: 所属站点 ID
        mechanism_key: 预测机制标识
        mode_id: 关联的 mode_id
        status: 模块状态（1=启用, 0=停用）
        sort_order: 排序权重
    """
    id: int
    site_id: int
    mechanism_key: str
    mode_id: int = 0
    status: bool = True
    sort_order: int = 0

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "PredictionModule":
        return cls(
            id=int(row["id"]),
            site_id=int(row["site_id"]),
            mechanism_key=str(row.get("mechanism_key") or ""),
            mode_id=int(row.get("mode_id") or 0),
            status=bool(row.get("status")),
            sort_order=int(row.get("sort_order") or 0),
        )


@dataclass
class GenerationContext:
    """预测资料生成上下文。

    封装一次批量生成所需的所有参数。
    """
    site_id: int
    web_id: int
    lottery_type_id: int
    start_year: int
    start_term: int
    end_year: int
    end_term: int
    mechanism_keys: list[str]
    created_by: str = ""


class PredictionCategory(str, Enum):
    ZODIAC = "zodiac"
    IMAGE = "image"
    SIZE_PARITY = "size_parity"
    TEXT_MAPPING = "text_mapping"
    NUMBER = "number"
    STRUCTURED_MAPPING = "structured_mapping"
    MIXED = "mixed"


@dataclass(frozen=True)
class DrawContext:
    lottery_type_id: int
    year: int
    term: int
    is_future: bool
    site_id: int
    web_id: int
    mode_id: int
    mechanism_key: str


@dataclass(frozen=True)
class DrawTruth:
    numbers: tuple[str, ...]
    special_code: str
    special_zodiac: str = ""
    special_color: str = ""

    def to_safe_dict(self) -> dict[str, bool]:
        return {"has_truth": bool(self.numbers)}


@dataclass(frozen=True)
class PredictionRequest:
    category: PredictionCategory
    context: DrawContext
    config_key: str
    candidate_labels: tuple[str, ...]
    truth: DrawTruth | None = None
    hit_checker: Callable[[str, tuple[str, ...]], bool] | None = None


@dataclass(frozen=True)
class PredictionOutput:
    category: PredictionCategory
    row_data: dict[str, Any]
    hit_target: bool | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "row_data": dict(self.row_data),
            "hit_target": self.hit_target,
        }
