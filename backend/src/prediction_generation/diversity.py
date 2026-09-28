from __future__ import annotations

import hashlib
import json
import random
import re
from typing import Any

# ---------- 多样性策略常量 ----------
# 默认策略：仅保证前两位组合不重复（“前二唯一”）
DEFAULT_DIVERSITY_POLICY = "unique_first_two"
# 窗口内允许共享策略（适用内容多样性豁免模式）
WINDOW_SHARED_DIVERSITY_POLICY = "window_shared"
# 完全自由策略，不做任何多样性限制
FREE_DIVERSITY_POLICY = "free"
# 无序号码集合策略：不做位置轮转，改为“按期号决定的一次性展示置换”
UNORDERED_SET_DIVERSITY_POLICY = "unordered_set_display_order"

# ---------- 豁免模式 ID ----------
# 某些 mode_id 不需要执行默认的多样性限制，这里直接使用窗口共享策略
CONTENT_DIVERSITY_EXEMPT_MODE_IDS = {197}

# ---------- 无序号码集合玩法 ----------
# 这些 mode 的 content 就是一组 01-49 号码（`01,17,40,...`），属于**集合语义**：
#   1. 前台只按“特码是否落在集合内”高亮（`038ma10.js` 用 `indexOf` + `join('.')`），
#      命中/不中与顺序完全无关；
#   2. 生成侧 `predict.common.score_labels(strategy="hot")` 会按“热度”排序，热度最高的
#      号码固定排在最前面；
#   3. 热度窗口读的是跨站共享的 `public.mode_payload_*` 表，而该表每个 (year, term)
#      有多行（每个站点一行，见下表），因此最近 5 条记录往往只覆盖 1~2 个真实期号，
#      同一个号码的 counts 被重复累加，排名前 1~5 位在整批生成里几乎恒定。
#
# 线上实测（created.mode_payload_* web_id=6 最近 40 期）：
#   mode 116（10码）位置 1 = `01` 出现 38/40，位置 2 = `17` 出现 25/40；
#   mode 88（杀7码）位置 1/2 只在 {01,17} 之间互换（19/18），位置 3 = `14` 出现 23/40；
#   mode 9（16码）位置 1~5 只在 {23,39,08,22,36} 之间轮转（前 5 位 distinct 仅 5~11 个）。
# 根因就是上面的“热度排序 + 展示顺序 = 排名顺序”。
#
# 因此对这些 mode：
#   1. 停用 `unique_first_two` 的位置轮转——集合语义下轮转没有意义，而且只会制造
#      另一组固定的“旋转位”（交换前两位 / 前四位左移一位的循环）；
#   2. 展示顺序改为“按 (mode, 年, 期, 站点) 决定的一次性置换”，保证每期位置都不同，
#      同时**完全不改变号码成员**，命中/不中判定保持等价。
#
# 说明（2026-09-29 复审修订）：**白名单不再靠人工维护**。
# 「是不是号码集合玩法」可以从配置形状直接判定（见 `is_number_set_config`），
# 因此原 `frozenset({9, 65, 88, 116})` 被替换为
# 「配置派生 + 契约例外」两层：
#
#   1. `unordered_number_set_mode_ids()` 由 `predict.mechanisms` 的配置清单派生：
#      `content_parser is parse_number_content` 且 `hit_checker` 是 contains/excludes
#      且 `labels` 恰好是 `01`..`49` 全域。落库形态确实是 01-49 号码集合时才允许置换。
#      这样 mode 34（24码）/ 77（14码中特）/ 481（稳杀10码）/ 485（内幕5不中）/
#      493（精选22码）/ 494（稳杀7码）自动获得修复，不需要再手工加白名单。
#   2. `UNORDERED_NUMBER_SET_DISPLAY_ORDER_EXCLUDED_MODE_IDS` 是**契约例外**：
#      配置形状像号码集合，但展示顺序本身承载语义，置换会改变页面判定或版面。
#      目前只有 mode 65（码段12/特码段）：前台 `016teduan.js` 用
#      `${content[0]}-${content[content.length-1]}` 渲染「段区间」，判定也按
#      `value >= parseInt(first) && value <= parseInt(last)` 计算（含区间内全部号码），
#      置换后区间语义与判定同时被破坏（`unordered_set: no positional rotation` 不成立）。
#      同族 mode 156（杀码段13连码）虽未在本部署启用，语义相同，一并排除。
#
# `UNORDERED_NUMBER_SET_MODE_IDS` 保留为**兼容别名**：取值来自派生函数，
# 静态配置缺失时退回 bootstrap 集合（下限，绝不比派生结果更宽）。
UNORDERED_NUMBER_SET_BOOTSTRAP_MODE_IDS: frozenset[int] = frozenset({9, 34, 77, 88, 116, 481, 485, 493, 494})

#: 契约例外：内容形态是号码集合，但展示顺序承载语义（段区间/位置切片），不得置换。
UNORDERED_NUMBER_SET_DISPLAY_ORDER_EXCLUDED_MODE_IDS: frozenset[int] = frozenset({65, 156})

#: `predict.mechanisms` 里号码类玩法使用的 content_parser 名称（延迟绑定，避免循环导入）。
_NUMBER_CONTENT_PARSER_NAME = "parse_number_content"

#: 号码类玩法的候选全域（`labels` 必须恰好等于该集合才算号码集合玩法）。
_NUMBER_LABEL_SPACE: tuple[str, ...] = tuple(f"{number:02d}" for number in range(1, 50))

#: `is_number_set_config` 的缓存：决定该 mode 是否为号码集合玩法（避免重复判定）。
_NUMBER_SET_CONFIG_STATUS: dict[int, bool | None] = {}

#: `unordered_number_set_mode_ids()` 的结果缓存（按配置清单规模失效）。
_NUMBER_SET_MODE_IDS_CACHE: tuple[int, frozenset[int]] | None = None

#: `01`-`49` 的两位号码
_NUMBER_SET_ITEM_RE = re.compile(r"^\d{2}$")

# ---------- 相邻连续 N 期不得相同的模式 ----------
# 这些模块前台只渲染一个“池标签”或一段文本，取值空间很小
# （如 28 单/双、57 与 108 大/小、63 家禽/野兽、62 欲钱解特诗）。
# 默认的“前二唯一”策略对单元素 content 完全失效，因此这里单独强制：
# 相邻连续 N 期的展示值不得全部相同（N 由 display_unique_window 决定）。
#
# 141/144/147/152/155/157/158 是 twsaimahui 的「二选一」生肖分组
# （阴阳肖 / 文武肖 / 有无肖 / 左右肖 / 吉美凶丑 / 肥瘦肖 / 胆大胆小）：
# content 只有 `["左肖|…"]` 这类单个标签，生成器此前会连续多期都抽到同一组。
THREE_PERIOD_UNIQUE_MODE_IDS = frozenset(
    {28, 52, 57, 62, 63, 108, 141, 144, 147, 152, 155, 157, 158}
)

#: 展示值取自 `title`（而不是 content 首项标签）的模式。
#: 前台直接渲染 title，因此唯一性也必须按 title 判定。
TITLE_UNIQUE_MODE_IDS = frozenset({52, 62})

#: 连续不重复窗口：默认 3 期；52 四字玄机与 62 欲钱解特候选池最大，要求相邻 5 期不得相同。
DISPLAY_UNIQUE_WINDOW_BY_MODE: dict[int, int] = {52: 5, 62: 5}

#: 默认窗口（未在 DISPLAY_UNIQUE_WINDOW_BY_MODE 中单独指定的托管模式）。
DEFAULT_DISPLAY_UNIQUE_WINDOW = 3

# 这些模式改由三期规则统一处理，跳过旧的“前二唯一”旋转策略，
# 避免两套规则互相抵消（旧策略对两项 content 会来回交换同一个值）。
_THREE_PERIOD_MANAGED_MODE_IDS = frozenset({28})


def display_unique_window(mode_id: int) -> int:
    """返回该模式要求「相邻连续多少期展示值不得完全相同」。"""
    resolved_mode_id = int(mode_id or 0)
    window = DISPLAY_UNIQUE_WINDOW_BY_MODE.get(resolved_mode_id, DEFAULT_DISPLAY_UNIQUE_WINDOW)
    return max(2, int(window))


# ---------- 号码集合玩法：按配置形状派生，不再人工维护白名单 ----------


def is_number_set_config(config: Any) -> bool:
    """配置形状是否为「01-49 号码集合」玩法（与具体 mode 无关）。

    判据（全部满足才算）：
    1. `content_parser` 是 `parse_number_content`（按 `\\d{2}` 抽取号码，
       因此 `["家禽|牛,马"]` 这类有序标签序列不会被误判）；
    2. `hit_checker` 是 `contains_hit` 或 `excludes_hit`（号码类玩法只有包含/排除两向，
       复合口径 `head_tail` / 平特口径等一律排除）；
    3. `labels` 恰好是 `01`..`49` 全域（候选维度就是号码本身，不是生肖/尾数/波色）；
    4. `label_count` 是正数且不超过号码全域（候选宽度必须落在可枚举范围内）。

    满足以上四条时，落库 `content` 就是「一组 01-49 号码」，位置没有语义。
    """
    parser = getattr(config, "content_parser", None)
    if getattr(parser, "__name__", "") != _NUMBER_CONTENT_PARSER_NAME:
        return False
    checker = getattr(config, "hit_checker", None)
    if getattr(checker, "__name__", "") not in {"contains_hit", "excludes_hit"}:
        return False
    labels = tuple(str(label) for label in (getattr(config, "labels", ()) or ()))
    if labels != _NUMBER_LABEL_SPACE:
        return False
    label_count = int(getattr(config, "label_count", 0) or 0)
    return 0 < label_count < len(_NUMBER_LABEL_SPACE)


def _prediction_configs() -> tuple[tuple[int, Any], ...]:
    """返回本地配置清单的 (mode_id, config) 对；配置不可用时返回空元组。

    `predict.mechanisms.PREDICTION_CONFIGS` 在服务启动时由
    `ensure_prediction_configs_loaded()` 合并静态与动态（`title_*`）配置，
    因此这里读到的是**运行时真实生效**的清单。导入失败（循环导入/精简环境/未初始化）
    时静默退回空清单：调用方一律有 bootstrap 下限兜底，不会因此放宽任何约束。
    """
    try:
        from predict.mechanisms import PREDICTION_CONFIGS
    except Exception:  # noqa: BLE001 - 配置层不可用时退回 bootstrap 下限
        return ()
    pairs: list[tuple[int, Any]] = []
    for config in PREDICTION_CONFIGS.values():
        try:
            mode_id = int(getattr(config, "default_modes_id", 0) or 0)
        except (TypeError, ValueError):
            continue
        if mode_id:
            pairs.append((mode_id, config))
    return tuple(pairs)


def reload_number_set_mode_ids() -> None:
    """清空派生缓存（配置清单重新加载后调用；测试也用它验证派生逻辑）。"""
    global _NUMBER_SET_MODE_IDS_CACHE
    _NUMBER_SET_MODE_IDS_CACHE = None
    _NUMBER_SET_CONFIG_STATUS.clear()


def unordered_number_set_mode_ids() -> frozenset[int]:
    """派生「号码集合玩法」的 mode 集合：配置派生的号码集合玩法。

    结果 = 配置派生的号码集合 mode ∪ `UNORDERED_NUMBER_SET_BOOTSTRAP_MODE_IDS`，
    再减去 `UNORDERED_NUMBER_SET_DISPLAY_ORDER_EXCLUDED_MODE_IDS`。

    bootstrap 的角色是**下限兜底**（动态配置尚未加载、精简环境里没有
    `predict.mechanisms` 时，行为与历史白名单一致），绝不引入派生判据之外的 mode；
    例外集合的角色是**收紧**（内容形态是号码集合，但展示顺序本身是契约，不能置换）。
    """
    global _NUMBER_SET_MODE_IDS_CACHE
    pairs = _prediction_configs()
    cache_key = len(pairs)
    if _NUMBER_SET_MODE_IDS_CACHE is not None and _NUMBER_SET_MODE_IDS_CACHE[0] == cache_key:
        return _NUMBER_SET_MODE_IDS_CACHE[1]

    derived: set[int] = set()
    for mode_id, config in pairs:
        known = _NUMBER_SET_CONFIG_STATUS.get(mode_id)
        if known is None:
            known = is_number_set_config(config)
            _NUMBER_SET_CONFIG_STATUS[mode_id] = known
        if known:
            derived.add(mode_id)

    resolved = frozenset(
        (derived | set(UNORDERED_NUMBER_SET_BOOTSTRAP_MODE_IDS))
        - set(UNORDERED_NUMBER_SET_DISPLAY_ORDER_EXCLUDED_MODE_IDS)
    )
    _NUMBER_SET_MODE_IDS_CACHE = (cache_key, resolved)
    return resolved


def is_unordered_number_set_mode(mode_id: int) -> bool:
    """该 mode 是否按「无序号码集合」处理（派生白名单成员，且不在契约例外内）。"""
    resolved_mode_id = int(mode_id or 0)
    if resolved_mode_id in UNORDERED_NUMBER_SET_DISPLAY_ORDER_EXCLUDED_MODE_IDS:
        return False
    return resolved_mode_id in unordered_number_set_mode_ids()


#: 兼容别名（取值来自派生函数；导入时机不影响正确性，因为 `frozenset` 已展开）。
#: 需要审阅/断言时请优先使用 `unordered_number_set_mode_ids()`。
UNORDERED_NUMBER_SET_MODE_IDS: frozenset[int] = unordered_number_set_mode_ids()


def resolve_diversity_policy(mode_id: int, config: Any | None = None) -> str:
    """
    根据 mode_id 与外部配置，解析出最终使用的多样性策略名称。

    优先级：
    1. 配置对象中的 ``diversity_policy`` 属性（非空字符串）
    2. 无序号码集合模式（``is_unordered_number_set_mode``）→
       ``UNORDERED_SET_DIVERSITY_POLICY``（不做位置轮转）
    3. 如果 mode_id 在豁免列表中，返回 ``WINDOW_SHARED_DIVERSITY_POLICY``
    4. 兜底返回 ``DEFAULT_DIVERSITY_POLICY``
    """
    # 尝试从 config 对象读取策略字段，转为字符串并去除首尾空格
    policy = str(getattr(config, "diversity_policy", "") or "").strip()
    if policy:
        return policy
    resolved_mode_id = int(mode_id or 0)
    # 集合语义的号码类玩法不做位置轮转，改用一次性展示置换
    if is_unordered_number_set_mode(resolved_mode_id):
        return UNORDERED_SET_DIVERSITY_POLICY
    # 三期规则托管模式不使用旧的“前二唯一”旋转策略
    if resolved_mode_id in _THREE_PERIOD_MANAGED_MODE_IDS:
        return WINDOW_SHARED_DIVERSITY_POLICY
    # 检查 mode_id 是否属于内容多样性豁免模式
    if resolved_mode_id in CONTENT_DIVERSITY_EXEMPT_MODE_IDS:
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


# ── 无序号码集合：成员解析 + 一次性展示置换 ─────────────────


def number_set_members(content_value: Any) -> list[str] | None:
    """把 content 解析成“纯 01-49 号码集合”，不是号码集合时返回 None。

    支持三种落库形态：
    - list：``["01", "17", ...]``
    - JSON 数组字符串：``'["01","17"]'``
    - 普通逗号串：``"01,17,40"``（号码类玩法 `format_24_numbers` 的输出形态）

    只要有任何一项不是 01-49 的两位号码，就返回 None：调用方据此确认“位置无意义”，
    不会把 `1头|01,11` 这类有序标签序列误当成号码集合。
    """
    if isinstance(content_value, dict):
        return None

    if isinstance(content_value, list):
        items = [str(item).strip() for item in content_value]
    else:
        text = str(content_value or "").strip()
        if not text:
            return None
        if text.startswith("[") and text.endswith("]"):
            parsed = parse_array_content(text)
            if parsed is None:
                return None
            items = [str(item).strip() for item in parsed]
        else:
            items = [part.strip() for part in text.split(",")]

    items = [item for item in items if item]
    if len(items) < 2:
        return None
    for item in items:
        if not _NUMBER_SET_ITEM_RE.match(item) or not 1 <= int(item) <= 49:
            return None
    return items


def is_unordered_number_set_content(content_value: Any) -> bool:
    """content 是否为“纯 01-49 号码集合”（集合语义，顺序无意义）。"""
    return number_set_members(content_value) is not None


def _dump_number_set(items: list[str], original_value: Any) -> Any:
    """按原落库形态回写号码集合（list / JSON 数组串 / 逗号串）。"""
    if isinstance(original_value, list):
        return list(items)
    text = str(original_value or "").strip()
    if text.startswith("[") and text.endswith("]"):
        return json.dumps(items, ensure_ascii=False)
    return ",".join(items)


def _number_set_shuffle_seed(mode_id: int, row_data: dict[str, Any], items: list[str]) -> int:
    """展示置换种子：同一期稳定、不同期不同、不同站点不同。

    种子主体是 ``(mode, year, term, web)``；同时混入成员集合，保证调用方漏传
    ``year``/``term``/``web``（例如单元测试或未来的新调用点）时，不同号码集合也不会
    退化成同一个固定置换——否则“位置固定”的缺陷会以另一种形式复现。
    成员本身在同一期是确定的，因此不会破坏“同期稳定”。
    """
    raw = (
        f"unordered-number-set:{int(mode_id or 0)}:"
        f"{row_data.get('year')}:{row_data.get('term')}:{row_data.get('web')}:"
        f"{','.join(items)}"
    )
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest(), 16) % (2**32)


def unordered_number_set_display_order(
    mode_id: int,
    row_data: dict[str, Any],
    recent_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """给无序号码集合生成“本期展示顺序”，成员一个都不改。

    行为：
    - mode 不是派生白名单成员（或属于契约例外，如 mode 65 码段区间），
      或 content 不是纯号码集合 → 原样返回（绝不误改有序标签序列 / 段区间）；
    - 否则用 ``(mode, year, term, web)`` 派生的种子对成员做一次性置换；
    - 若置换结果与最近一期**成员完全相同**的展示顺序仍然一致，则再错开一位，
      保证相邻期展示顺序不同（“相邻期唯一性”在这里落到展示顺序上）。

    只影响展示顺序，不影响集合本身，因此命中/不中判定保持等价。
    """
    row = dict(row_data)
    if not is_unordered_number_set_mode(mode_id):
        return row

    items = number_set_members(row.get("content"))
    if not items:
        return row

    ordered = list(items)
    random.Random(_number_set_shuffle_seed(mode_id, row, items)).shuffle(ordered)

    previous = _previous_number_set_order(items, recent_rows)
    if previous is not None and ordered == previous and len(ordered) > 1:
        # 成员完全相同且顺序撞上上一期时，整体错开一位
        ordered = ordered[1:] + ordered[:1]

    row["content"] = _dump_number_set(ordered, row.get("content"))
    return row


def _previous_number_set_order(
    items: list[str],
    recent_rows: list[dict[str, Any]] | None,
) -> list[str] | None:
    """返回最近一期“成员与本期完全相同”的展示顺序（新→旧查找）。"""
    target = sorted(items)
    for recent_row in recent_rows or []:
        previous = number_set_members((recent_row or {}).get("content"))
        if previous and sorted(previous) == target:
            return previous
    return None


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
        无序号码集合玩法（``unordered_number_set_mode_ids()`` 派生集合）不参与位置轮转，
        只把展示顺序换成按期号决定的一次性置换（成员不变）。
        若 5 次尝试后仍无法解决冲突，会在结果中附加 ``_diversity_warning`` 键。
    """
    # 1. 解析多样性策略，若为窗口共享或自由策略则不做任何限制
    policy = resolve_diversity_policy(mode_id, config)
    if policy in {WINDOW_SHARED_DIVERSITY_POLICY, FREE_DIVERSITY_POLICY}:
        return dict(row_data)
    if policy == UNORDERED_SET_DIVERSITY_POLICY:
        # 无序号码集合：位置没有意义，不做“前二唯一”轮转，
        # 只给本期生成一个稳定的展示顺序（成员完全不变）。
        return unordered_number_set_display_order(mode_id, row_data, recent_rows=recent_rows)

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


# ── 相邻连续三期不得相同 ─────────────────────────────────


def display_token_for_row(mode_id: int, row: Any) -> str | None:
    """返回该模式下前台实际渲染的展示值（池标签 / 文本），非托管模式返回 None。

    展示值定义与前台渲染器一致：
      - 28 / 57 / 63 / 108：content 数组首项 `标签|号码` 的标签部分
      - 52 / 62：title（四字玄机 / 欲钱解特诗，前台直接渲染 title）
    取值与顺序无关，因此 `["小|..","大|.."]` 与 `["大|..","小|.."]` 视为同一展示值。
    """
    resolved_mode_id = int(mode_id or 0)
    if resolved_mode_id not in THREE_PERIOD_UNIQUE_MODE_IDS:
        return None

    if resolved_mode_id in TITLE_UNIQUE_MODE_IDS:
        title = str(row.get("title") or "").strip()
        return title or None

    content_value = row.get("content")
    items = parse_array_content(content_value)
    if not items:
        # 兜底：content 缺失的单字段模式回落到整串内容
        fallback = str(content_value or "").strip()
        if not fallback:
            return None
        return fallback.split("|", 1)[0].strip() or None
    return items[0].split("|", 1)[0].strip() or None


def distinct_tokens_for_content(content_value: Any) -> tuple[str, ...]:
    """按出现顺序返回 content 中所有不同的展示值。"""
    tokens: list[str] = []
    for item in parse_array_content(content_value) or []:
        token = str(item).split("|", 1)[0].strip()
        if token and token not in tokens:
            tokens.append(token)
    return tuple(tokens)


def _pick_alternative_token(
    candidates: tuple[str, ...],
    recent_tokens: list[str],
    preferred_token: str,
) -> str | None:
    """选出与本期不同的展示值，优先保持固定轮转顺序。

    调用方已确认最近两期与本期相同，因此这里只需避开本期取值；
    最近两期本来就等于本期取值（二值模式必然如此），不能把它们当作候选黑名单，
    否则永远挑不出替代值。
    """
    rotated = [token for token in candidates if token and token != preferred_token]
    return rotated[0] if rotated else None


def _pipe_items_from_content(content_value: Any) -> list[str]:
    """把 content 的各种形态统一成若干 `标签[|号码]` 项。

    支持：list、JSON 数组字符串（`["家禽|牛,马"]`）、`标签|号码` 普通字符串。
    注意：含 `|` 的普通字符串整体视为一项，不能按逗号拆开，
    否则 `野兽|鼠,虎,兔` 会被拆成 `野兽|鼠` 之类的残项。
    """
    if isinstance(content_value, dict):
        return []

    if isinstance(content_value, list):
        return [str(item) for item in content_value if str(item).strip()]

    parsed = parse_array_content(content_value)
    if parsed:
        return [str(item) for item in parsed]

    raw = str(content_value or "").strip()
    if not raw:
        return []
    try:
        decoded = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        decoded = None
    if isinstance(decoded, list):
        return [str(item) for item in decoded if str(item).strip()]
    if "|" in raw:
        return [raw]
    return [item.strip() for item in raw.split(",") if item.strip()]


def _content_with_token(
    *,
    items: list[str],
    current_content: Any,
    target_token: str,
    template_content: Any = None,
) -> Any:
    """把 content 的首项换成 target_token 对应的 `标签|号码` 结构。

    优先使用本期 content 里已有的同标签项（只调整顺序）；
    否则使用本模式该标签的模板项（保留真实号码池），并按本期 content 的原有形态回写。
    """
    for index, item in enumerate(items):
        if str(item).split("|", 1)[0].strip() != target_token:
            continue
        reordered = [item] + [value for position, value in enumerate(items) if position != index]
        return dump_array_content([str(value) for value in reordered], current_content)

    for template_item in _pipe_items_from_content(template_content):
        if str(template_item).split("|", 1)[0].strip() != target_token:
            continue
        # 用模板项替换首项；本期首项已不再使用，不再向后拼接，避免同一标签重复出现。
        replaced = [str(template_item)] + [str(value) for value in items[1:]]
        return _dump_like_current(replaced, current_content)

    return None


def _dump_like_current(items: list[str], current_content: Any) -> Any:
    """按本期 content 的原有形态回写（JSON 数组保持数组，普通字符串保持字符串）。"""
    if isinstance(current_content, list):
        return list(items)

    text = str(current_content or "").strip()
    looks_like_json_array = text.startswith("[") and text.endswith("]")
    if looks_like_json_array:
        return json.dumps(items, ensure_ascii=False)

    if len(items) == 1:
        return items[0]
    return json.dumps(items, ensure_ascii=False)


#: 文本类模式的占位文案：不是真实预测内容，有真实候选时应被替换掉。
TEXT_PLACEHOLDER_TITLES = frozenset({"欲钱解特诗"})


def replace_text_placeholder(
    mode_id: int,
    row_data: dict[str, Any],
    alternative_text_payloads: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """把文本类模式的占位文案换成真实候选（不改动历史行）。

    生成器在历史文本源为空时会写入 `欲钱解特诗` 这类占位串；既然库里已有真实
    诗句候选，就不应把占位串当成一期预测展示出去（否则会出现“占位↔真实”轮流出现）。
    """
    row = dict(row_data)
    if int(mode_id or 0) not in THREE_PERIOD_UNIQUE_MODE_IDS:
        return row
    if str(row.get("title") or "").strip() not in TEXT_PLACEHOLDER_TITLES:
        return row
    for payload in alternative_text_payloads or []:
        title = str(payload.get("title") or "").strip()
        if not title or title in TEXT_PLACEHOLDER_TITLES:
            continue
        row["title"] = title
        return row
    return row


def enforce_three_period_uniqueness(
    *,
    mode_id: int,
    row_data: dict[str, Any],
    recent_rows: list[dict[str, Any]] | None = None,
    alternative_content_templates: list[Any] | None = None,
    alternative_text_payloads: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """禁止相邻连续 N 期的展示值完全相同（N = display_unique_window(mode_id)）。

    参数：
        mode_id                      : 预测模式 ID，非托管模式直接返回原值
        row_data                     : 本期待写入的行数据
        recent_rows                  : 已存在/已生成的最近行（按新→旧排序）
        alternative_content_templates: 本模式其他展示值的完整 content
                                       （如 63 的 `["野兽|鼠,虎,兔,龙,蛇,猴"]`）
        alternative_text_payloads    : 文本类模式（52 / 62）可选的替代 title/content/jiexi

    行为：
        当前展示值与最近 N-1 期都相同时，改用另一展示值（沿用其完整号码池）；
        无法找到合法取值时保留原值并附加 ``_diversity_warning``；
        只影响尚未写入的行，绝不改写历史行。
    """
    resolved_mode_id = int(mode_id or 0)
    row = dict(row_data)
    if resolved_mode_id not in THREE_PERIOD_UNIQUE_MODE_IDS:
        return row

    current_token = display_token_for_row(resolved_mode_id, row)
    if not current_token:
        return row

    window = display_unique_window(resolved_mode_id)
    required_recent = window - 1

    recent_tokens: list[str] = []
    for recent_row in recent_rows or []:
        token = display_token_for_row(resolved_mode_id, recent_row)
        if token:
            recent_tokens.append(token)
        if len(recent_tokens) >= required_recent:
            break
    if len(recent_tokens) < required_recent:
        return row
    # 只要最近 N-1 期中有一期与本期不同，就不构成“连续 N 期相同”
    if any(token != current_token for token in recent_tokens):
        return row

    if resolved_mode_id in TITLE_UNIQUE_MODE_IDS:
        for payload in alternative_text_payloads or []:
            candidate = dict(row)
            for key in ("title", "content", "jiexi"):
                if payload.get(key) not in (None, ""):
                    candidate[key] = payload[key]
            candidate_token = display_token_for_row(resolved_mode_id, candidate)
            if candidate_token and candidate_token not in recent_tokens:
                return candidate
        row["_diversity_warning"] = (
            f"mode_id={resolved_mode_id}: 连续{window}期展示值相同且无可用替代文本，保留本期取值"
        )
        return row

    items = [str(item) for item in (parse_array_content(row.get("content")) or [])]
    token_pool: list[str] = []
    templates: dict[str, Any] = {}
    for template in alternative_content_templates or []:
        token = display_token_for_row(resolved_mode_id, {"content": template})
        if not token or token in templates:
            continue
        token_pool.append(token)
        templates[token] = template
    for token in distinct_tokens_for_content(row.get("content")):
        if token not in token_pool:
            token_pool.append(token)
            templates[token] = row.get("content")
    for recent_row in recent_rows or []:
        for token in distinct_tokens_for_content(recent_row.get("content")):
            if token not in token_pool:
                token_pool.append(token)
                templates[token] = recent_row.get("content")

    target_token = _pick_alternative_token(tuple(token_pool), recent_tokens, current_token)
    if target_token:
        swapped = _content_with_token(
            items=items,
            current_content=row.get("content"),
            target_token=target_token,
            template_content=templates.get(target_token),
        )
        if swapped is not None:
            row["content"] = swapped
            if display_token_for_row(resolved_mode_id, row) != current_token:
                return row

    row["_diversity_warning"] = (
        f"mode_id={resolved_mode_id}: 连续{window}期展示值 {current_token!r} 相同且无可用替代取值，保留本期取值"
    )
    return row