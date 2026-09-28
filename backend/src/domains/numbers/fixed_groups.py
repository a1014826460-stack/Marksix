"""Public fixed_data group reads.

`public.fixed_data` 是号码／生肖固定分组的唯一权威来源（如「合单双」「波色单双」
「生肖」）。前端渲染器需要把 `合单` / `合双` 这类**纯标签**展开成号码集合，才能
按集合语义判断「特码是否命中」，因此这里提供一个只读的公开读取入口，避免任何
前端层硬编码号码表。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from db import connect


def load_fixed_data_groups(
    db_path: str | Path,
    sign: str,
    *,
    include_disabled: bool = False,
) -> dict[str, Any]:
    """按 ``fixed_data.sign`` 读取固定分组。

    args:
        - db_path: 数据库连接串。
        - sign: `fixed_data.sign` 分类名，例如 `合单双`、`波色`、`生肖`。
        - include_disabled: 是否包含 `status != 1` 的行；公开接口一律只要启用行。
    returns:
        - ``{"sign": sign, "groups": [{"label": name, "codes": [...]}, ...]}``；
          `label` 按 `xu`、`id` 稳定排序，`codes` 原样保留库内两位号码串或生肖串。
    """
    resolved_sign = str(sign or "").strip()
    if not resolved_sign:
        raise ValueError("sign 不能为空")

    with connect(db_path) as conn:
        if not conn.table_exists("fixed_data"):
            return {"sign": resolved_sign, "groups": []}
        conditions = ["sign = ?"]
        params: list[Any] = [resolved_sign]
        if not include_disabled:
            conditions.append("status = 1")
        rows = conn.execute(
            f"""
            SELECT id, name, code, xu
            FROM fixed_data
            WHERE {' AND '.join(conditions)}
            ORDER BY xu ASC, id ASC
            """,
            tuple(params),
        ).fetchall()

    groups: list[dict[str, Any]] = []
    for row in rows:
        label = str(row["name"] or "").strip()
        if not label:
            continue
        codes = [item.strip() for item in str(row["code"] or "").split(",") if item.strip()]
        groups.append({"label": label, "codes": codes})
    return {"sign": resolved_sign, "groups": groups}
