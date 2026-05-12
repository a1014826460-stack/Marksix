"""彩种领域数据结构定义。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LotteryType:
    """彩种领域模型。

    Attributes:
        id: 彩种 ID（1=香港彩, 2=澳门彩, 3=台湾彩）
        name: 彩种名称
        draw_time: 默认开奖时间（HH:MM 格式）
        collect_url: 数据采集 URL
        next_time: 下一期开奖时间（毫秒时间戳字符串）
        status: 是否启用
    """
    id: int
    name: str
    draw_time: str = ""
    collect_url: str = ""
    next_time: str = ""
    status: bool = True

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "LotteryType":
        return cls(
            id=int(row["id"]),
            name=str(row.get("name") or ""),
            draw_time=str(row.get("draw_time") or ""),
            collect_url=str(row.get("collect_url") or ""),
            next_time=str(row.get("next_time") or ""),
            status=bool(row.get("status")),
        )


@dataclass
class LotteryDraw:
    """开奖记录领域模型。

    Attributes:
        id: 记录 ID
        lottery_type_id: 彩种 ID
        year: 年份
        term: 期号
        numbers: 开奖号码（逗号分隔）
        draw_time: 开奖时间（北京时间 YYYY-MM-DD HH:MM:SS）
        is_opened: 是否已开奖
        next_term: 下一期期号
        next_time: 下一期开奖时间（毫秒时间戳）
    """
    id: int
    lottery_type_id: int
    year: int
    term: int
    numbers: str
    draw_time: str = ""
    is_opened: bool = False
    next_term: int | None = None
    next_time: str = ""

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "LotteryDraw":
        return cls(
            id=int(row["id"]),
            lottery_type_id=int(row["lottery_type_id"]),
            year=int(row["year"]),
            term=int(row["term"]),
            numbers=str(row.get("numbers") or ""),
            draw_time=str(row.get("draw_time") or ""),
            is_opened=bool(row.get("is_opened")),
            next_term=int(row["next_term"]) if row.get("next_term") else None,
            next_time=str(row.get("next_time") or ""),
        )
