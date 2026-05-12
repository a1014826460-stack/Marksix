from __future__ import annotations

import json
from typing import Any

# ---------- 多样性策略常量 ----------
# 默认策略：仅保证前两位组合不重复（“前二唯一”）
DEFAULT_DIVERSITY_POLICY = "unique_first_two"
# 窗口内允许共享策略（适用内容多样性豁免模式）
WINDOW_SHARED_DIVERSITY_POLICY = "window_shared"
# 完全自由策略，不做任何多样性限制
FREE_DIVERSITY_POLICY = "free"

# ---------- 豁免模式 ID ----------
# 某些 mode_id 不需要执行默认的多样性限制，这里直接使用窗口共享策略
CONTENT_DIVERSITY_EXEMPT_MODE_IDS = {197}


def resolve_diversity_policy(mode_id: int, config: Any | None = None) -> str:
    """
    根据 mode_id 与外部配置，解析出最终使用的多样性策略名称。

    优先级：
    1. 配置对象中的 ``diversity_policy`` 属性（非空字符串）
    2. 如果 mode_id 在豁免列表中，返回 ``WINDOW_SHARED_DIVERSITY_POLICY``
    3. 兜底返回 ``DEFAULT_DIVERSITY_POLICY``
    """
    # 尝试从 config 对象读取策略字段，转为字符串并去除首尾空格
    policy = str(getattr(config, "diversity_policy", "") or "").strip()
    if policy:
        return policy
    # 检查 mode_id 是否属于内容多样性豁免模式
    if int(mode_id or 0) in CONTENT_DIVERSITY_EXEMPT_MODE_IDS:
        return WINDOW_SHARED_DIVERSITY_POLICY
    # 默认策略
    return DEFAULT_DIVERSITY_POLICY


def parse_array_content(content_value: Any) -> list[str] | None:
    """
    将 content 字段统一解析为字符串列表。

    支持两种输入形式：
    - 已经是 list → 直接对每个元素做 str() 转换
    - 是 JSON 字符串 → 尝试 json.loads，若结果为列表则转换

    解析失败或结果为空时返回 None。
    """
    # 若已经是列表，直接转换元素
    if isinstance(content_value, list):
        return [str(item) for item in content_value]

    # 否则当作字符串处理
    text = str(content_value or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None

    # 解析后必须是列表，否则视为无效
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return None


def dump_array_content(items: list[str], original_value: Any) -> Any:
    """
    将多样性调整后的列表 items 序列化回原始格式。

    如果原始值是 list 类型 → 直接返回列表
    否则（原始值是 JSON 字符串或其他） → 用 json.dumps 生成字符串
    """
    if isinstance(original_value, list):
        return items
    # 非列表原始值：序列化为 JSON 字符串，保持中文可读
    return json.dumps(items, ensure_ascii=False)


def content_prefix_signature(content_value: Any, width: int = 2) -> tuple[str, ...] | None:
    """
    提取内容的前几个元素，形成“前缀签名”。

    用于快速比较两组内容是否可能冲突。
    返回元组，若内容不可解析或为空则返回 None。
    """
    items = parse_array_content(content_value)
    if not items:
        return None
    # 取前 width 个元素，至少取 1 个
    limited = items[: max(1, width)]
    return tuple(str(item) for item in limited)


def enforce_prediction_diversity(
    *,
    mode_id: int,
    row_data: dict[str, Any],
    recent_rows: list[dict[str, Any]] | None = None,
    config: Any | None = None,
) -> dict[str, Any]:
    """
    对列表形式的内容执行多样性强制策略（默认策略为“前二不能重复”）。

    参数说明：
        mode_id     : 当前预测模式 ID，用于策略选择
        row_data    : 当前待检查的行数据（必须包含 'content' 字段）
        recent_rows : 最近已生成的行列表，用于检测重复
        config      : 可选的配置对象，可能携带 diversity_policy

    返回：
        处理后的 row_data 字典。如果启用了多样性限制且当前内容与
        近期记录的前缀重复，则会尝试通过旋转元素顺序来修复。
        若 5 次尝试后仍无法解决冲突，会在结果中附加 ``_diversity_warning`` 键。
    """
    # 1. 解析多样性策略，若为窗口共享或自由策略则不做任何限制
    policy = resolve_diversity_policy(mode_id, config)
    if policy in {WINDOW_SHARED_DIVERSITY_POLICY, FREE_DIVERSITY_POLICY}:
        return dict(row_data)

    # 2. 提取当前行内容列表，若长度不足 2 则无需多样性检查
    content_value = row_data.get("content")
    items = parse_array_content(content_value)
    if not items or len(items) < 2:
        return dict(row_data)

    # 确保 recent_rows 不为 None
    recent = recent_rows or []

    # 3. 构建近期记录的“签名”集合
    #    分为两类：① 首项集合；② 前两项对儿集合
    recent_first: set[str] = set()
    recent_pairs: set[tuple[str, str]] = set()
    for row in recent:
        row_items = parse_array_content(row.get("content"))
        if not row_items:
            continue
        # 记录首项
        recent_first.add(row_items[0])
        # 若长度足够，记录前两项的组合
        if len(row_items) >= 2:
            recent_pairs.add((row_items[0], row_items[1]))

    # 4. 检查当前内容的首项和前两项是否已出现在近期记录中
    current_first = items[0]
    current_pair = (items[0], items[1])

    needs_repair = (current_first in recent_first) or (current_pair in recent_pairs)
    if not needs_repair:
        return dict(row_data)

    # 5. 需要修复：复制一份候选列表，尝试 5 次旋转/交换
    best = list(items)
    resolved = False
    for attempt in range(5):
        if attempt == 0:
            # 第一次尝试：简单互换前两个元素
            best[0], best[1] = best[1], best[0]
        else:
            # 后续尝试：将前四个元素循环左移一位（若长度足够）
            # 例如 [a,b,c,d,...] → [b,c,d,a,...]
            if len(best) >= 4:
                best[:4] = best[1:4] + [best[0]]
            else:
                # 长度不足 4 则继续重复互换前两位
                best[0], best[1] = best[1], best[0]

        # 检查调整后的方案是否满足多样性要求
        if best[0] not in recent_first and (best[0], best[1]) not in recent_pairs:
            resolved = True
            break

    # 6. 生成最终结果，将修复后的列表回写到 content 字段
    result = dict(row_data)
    result["content"] = dump_array_content(best, content_value)

    # 若 5 次尝试后仍未解决，附加警告信息
    if not resolved:
        result["_diversity_warning"] = (
            f"mode_id={mode_id}: 多样性修复在5次尝试后仍未解决，"
            f"首项={best[0]!r}，保留最后候选值"
        )

    return result