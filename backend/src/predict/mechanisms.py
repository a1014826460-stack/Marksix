import json
import random
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from db import ConnectionAdapter, connect as db_connect, utc_now
from domains.prediction import predict_repository

from predict.common import (
    DEFAULT_DB_TARGET,
    ELEMENT_ORDER,
    ZODIAC_ORDER,
    PredictionConfig,
    build_element_number_map,
    contains_hit,
    default_content_from_row,
    excludes_hit,
    fixed_label_for_value,
    load_fixed_labels,
    load_fixed_value_map,
    normalize_zodiac_label,
    parse_json_or_plain_content,
    parse_number_content,
    parse_pipe_label_content,
    parse_zodiac_content,
    quote_identifier,
    row_get,
    special_code_from_res_code,
    special_element_from_row,
    special_zodiac_from_number_map,
    table_exists,
    title_content_from_row,
    xiao_pair_content_from_row,
)
from predict._db_helpers import (
    COMMON_PAYLOAD_COLUMNS,
    _business_columns,
    _is_first_stage_supported_table,
    _sample_column_value,
    _sample_content,
    _table_column_list,
    _table_columns,
)
from predict.categories import content_columns, image, mixed, number, size_parity, structured_mapping, text_mapping, zodiac
from predict.categories.mixed import (
    mixed_dimension_contains_hit,
    mixed_dimension_excludes_hit,
    mixed_xiao_tail_outcome_from_row as _mixed_xiao_tail_outcome_from_row,
    parse_mixed_dimension_content,
)
from predict.categories.image import format_window_content
from predict.categories.content_columns import (
    black_white_content_from_row,
    jiexi_content_from_row,
    join_columns_content_loader,
    parse_literal_label_content,
    parse_tail_digit_content,
    parse_wave_chars,
    parse_zodiac_chars,
    parsed_columns_content_loader,
    tail_code_content_from_row,
    tail_columns_content_loader,
    xiao_code_content_from_row,
)
from predict.categories.number import (
    format_24_numbers,
    format_segment_groups,
    format_split_number_columns,
    special_number_from_row,
    special_segment_from_row,
)
from predict.categories.size_parity import (
    format_fixed_groups,
    format_half_wave_groups,
    format_head_groups,
    format_parity_groups,
    format_size_groups,
    format_tail_groups,
    label_for_special_number,
    special_combined_parity_from_row,
    special_combined_size_from_row,
    special_half_wave_from_row,
    special_head_from_row,
    special_parity_from_row,
    special_size_from_row,
    special_tail_from_row,
    special_wave_from_row,
)
from predict.categories.structured_mapping import (
    build_pipe_value_map,
    category_outcome_from_map,
    format_dynamic_pipe_groups,
    format_qinqi_content,
    format_zodiac_groups,
    make_pipe_category_outcome,
    qinqi_outcome_from_row,
)
from predict.categories.text_mapping import (
    format_humor_tail_groups,
    format_juzi_title,
    format_text_history_mapping,
    format_text_pool_jiexi,
    random_text_pool_row,
)
from predict.categories.zodiac import (
    format_9x12,
    format_split_zodiac_columns,
    format_xiao_code_columns,
    format_xiao_pair,
    format_zodiac_all_codes,
    format_zodiac_csv,
    format_zodiac_one_code,
    format_zodiac_two_codes,
    format_zodiac_word_codes,
    get_zodiac_numbers,
)


# 数字映射常量已迁移至 predict/number_maps.py，此处兼容导入
from predict.number_maps import (  # noqa: F401 - 兼容导出
    HALF_WAVE_NUMBER_MAP,
    HEAD_NUMBER_MAP,
    PARITY_NUMBER_MAP,
    SIZE_NUMBER_MAP,
    TAIL_NUMBER_MAP,
    WAVE_COLOR_NUMBER_MAP,
)


TABLE_FIXED_MAPPING_KEYS: dict[str, str] = {
    "mode_payload_12": "头",
    "mode_payload_20": "尾",
    "mode_payload_26": "四艺生肖",
    "mode_payload_28": "单双",
    "mode_payload_38": "波色",
    "mode_payload_53": "五行肖",
    "mode_payload_54": "尾",
    "mode_payload_57": "大小",
    "mode_payload_58": "波色单双",
    "mode_payload_61": "四季肖",
}
structured_mapping.table_fixed_mapping_keys = TABLE_FIXED_MAPPING_KEYS

DOMESTIC_WILD_LABELS = ("家禽", "野兽")
DOMESTIC_WILD_FALLBACK = {
    "家禽": ("牛", "狗", "猪", "羊", "马", "鸡"),
    "野兽": ("兔", "猴", "虎", "蛇", "鼠", "龙"),
}


def labels_from_fixed(mapping_key: str, fallback: tuple[str, ...]):
    def loader(conn: sqlite3.Connection) -> tuple[str, ...]:
        return load_fixed_labels(conn, mapping_key, fallback)

    return loader






def labels_from_history_pipe(table_name: str, fallback: tuple[str, ...] = ()):
    """从本地历史表的 `标签|值列表` content 中读取去重后的标签。

    fetched_mode_records 归一化后会进入 mode_payload_xxx 表。同一 title 在多个站点
    下可能有相同玩法结构，这里只从本地归一化后的表提取标签，避免为同类玩法重复
    编写固定 labels。
    """

    def loader(conn: sqlite3.Connection) -> tuple[str, ...]:
        if not table_exists(conn, table_name):
            return fallback

        labels: list[str] = []
        for content in predict_repository.load_non_empty_column_values(conn, table_name, "content"):
            for item in parse_json_or_plain_content(content):
                if "|" not in item:
                    continue
                label = item.split("|", 1)[0].strip()
                if label and label not in labels:
                    labels.append(label)
        return tuple(labels) or fallback

    return loader


def make_dynamic_pipe_outcome(table_name: str, labels: tuple[str, ...]):
    """生成通用 `标签|值列表` 命中规则。

    该规则先用特码号码匹配标签值，再用特码生肖匹配标签值。这样同一个模块可以覆盖
    号码分类、生肖分类、尾数/波色等多种结构化玩法，避免为每个 title 重复构建模块。
    """

    def loader(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
        resolved_labels = labels_from_history_pipe(table_name, labels)(conn)
        mapping = build_pipe_value_map(conn, table_name, resolved_labels)
        special_code = special_code_from_res_code(row["res_code"] or "")
        special_zodiac = special_zodiac_from_number_map(row, conn)
        return (
            category_outcome_from_map(special_code, mapping, resolved_labels)
            or category_outcome_from_map(special_zodiac, mapping, resolved_labels)
        )

    return loader


def format_dynamic_pipe_groups(table_name: str):
    """按动态标签输出 `标签|值列表`。

    与固定玩法不同，自动机制的标签来自历史 content，不能在模块加载时写死。
    因此 formatter 以本次选中的 labels 为准重新读取映射，保证输出字段与预测标签一致。
    """

    def formatter(selected: tuple[str, ...], conn: sqlite3.Connection) -> list[str]:
        mapping = build_pipe_value_map(conn, table_name, selected)
        return [f"{label}|{','.join(mapping.get(label, ()))}" for label in selected]

    return formatter














def _special_digit_sum(row: sqlite3.Row) -> int:
    number = int(special_code_from_res_code(row["res_code"] or ""))
    return (number // 10) + (number % 10)






def load_domestic_wild_value_map(conn: sqlite3.Connection) -> dict[str, tuple[str, ...]]:
    for sign in ("家禽|野兽", "家野肖"):
        mapping = load_fixed_value_map(conn, sign, DOMESTIC_WILD_LABELS)
        if any(mapping.get(label) for label in DOMESTIC_WILD_LABELS):
            return mapping
    return {label: values for label, values in DOMESTIC_WILD_FALLBACK.items()}


def special_domestic_wild_from_row(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
    zodiac = special_zodiac_from_number_map(row, conn)
    if not zodiac:
        return ""
    mapping = load_domestic_wild_value_map(conn)
    for label in DOMESTIC_WILD_LABELS:
        if zodiac in mapping.get(label, ()):
            return label
    return ""


def special_fengmaibizhong_from_row(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
    number = int(special_code_from_res_code(row["res_code"] or ""))
    outcomes = (
        "单数" if number % 2 == 1 else "双数",
        "大数" if number >= 25 else "小数",
        special_domestic_wild_from_row(row, conn),
    )
    return "|".join(label for label in outcomes if label)


























def _find_fixed_data_sign_for_labels(
    conn: sqlite3.Connection, labels: tuple[str, ...]
) -> str | None:
    """在 fixed_data 中查找与给定标签集合匹配的 sign。

    匹配条件：某个 sign 下至少有 2 个 name 出现在 labels 中（或 labels 为空时返回 None）。
    """
    if not labels or not table_exists(conn, "fixed_data"):
        return None

    label_set = set(labels)
    rows = predict_repository.load_fixed_data_sign_names(conn)

    # 按 sign 分组统计匹配的 name 数量
    sign_hits: dict[str, int] = {}
    sign_all_names: dict[str, set[str]] = {}
    for row in rows:
        sign = str(row["sign"] or "")
        name = str(row["name"] or "").strip()
        if not sign or not name:
            continue
        sign_all_names.setdefault(sign, set()).add(name)
        if name in label_set:
            sign_hits[sign] = sign_hits.get(sign, 0) + 1

    # 优先返回匹配数最多的 sign；至少需要匹配 2 个标签
    best = max(sign_hits.items(), key=lambda item: (item[1], item[0])) if sign_hits else None
    if best and best[1] >= 2:
        return best[0]

    # 退而求其次：sign 下所有 name 都出现在 labels 中
    for sign, names in sign_all_names.items():
        if names and names.issubset(label_set) and len(names) >= 2:
            return sign

    return None


structured_mapping.find_fixed_data_sign_for_labels = _find_fixed_data_sign_for_labels
















def format_wave_csv(labels: tuple[str, ...], _: sqlite3.Connection) -> str:
    """双波中特历史格式为 `红波,蓝波`。"""
    return ",".join(labels)












def format_split_tail_columns(columns: tuple[str, ...], widths: tuple[int, ...]):
    """把内部统一使用的 `N尾` 标签还原为历史列中的纯数字尾数格式。"""

    def formatter(labels: tuple[str, ...], _: sqlite3.Connection) -> dict[str, str]:
        result: dict[str, str] = {}
        index = 0
        for column, width in zip(columns, widths):
            group_labels = labels[index:index + width]
            index += width
            result[column] = ",".join(label.removesuffix("尾") for label in group_labels)
        return result

    return formatter






def format_qianhou_texiao_columns(
    xiao_column: str = "xiao",
    content_column: str = "content",
):
    """Build the minimal `content+xiao` structure used by 前后特肖."""

    def formatter(labels: tuple[str, ...], _: sqlite3.Connection) -> dict[str, str]:
        selected = list(labels[:2])
        prefix = "前肖" if selected else "后肖"
        return {
            xiao_column: ",".join(selected),
            content_column: f"{prefix}|{','.join(selected)}",
        }

    return formatter


def xiao_column_content_loader(column: str = "xiao"):
    """读取最终生肖候选列。
    `content+xiao` 结构中，content 通常是分类及分类内生肖列表，xiao 才是最终候选生肖。
    历史回测只使用 xiao 列，避免把分类说明字段误当成另一个命中条件。
    """

    def loader(row: sqlite3.Row) -> str:
        return str(row_get(row, column, "") or "")

    return loader


def xiao_or_content_content_loader(
    xiao_column: str = "xiao",
    content_column: str = "content",
):
    """优先读取 `xiao`，为空时回退到 `content` 中已标记的生肖标签。"""

    def loader(row: sqlite3.Row) -> str:
        xiao_value = parse_zodiac_content(str(row_get(row, xiao_column, "") or ""))
        if xiao_value:
            return ",".join(xiao_value)
        content_value = str(row_get(row, content_column, "") or "")
        return ",".join(parse_pipe_label_content(content_value))

    return loader


def mixed_xiao_tail_content_loader(
    xiao_column: str = "xiao",
    tail_column: str = "wei",
):
    """把生肖列和尾数列合并成内部可解析的混合标签串。"""

    def loader(row: sqlite3.Row) -> str:
        zodiac_labels = [f"肖:{label}" for label in parse_zodiac_content(str(row_get(row, xiao_column, "") or ""))]
        tail_labels = [f"尾:{label}" for label in parse_tail_digit_content(str(row_get(row, tail_column, "") or ""))]
        return ",".join(zodiac_labels + tail_labels)

    return loader




def mixed_xiao_tail_outcome_from_row(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
    """把真实开奖结果表示为两个命中原子：特码生肖和特码尾数。"""
    return f"肖:{special_zodiac_from_number_map(row, conn)}|尾:{special_tail_from_row(row, conn)}"






def _content_category_pool(conn: sqlite3.Connection, table_name: str, content_column: str = "content") -> list[str]:
    if not table_exists(conn, table_name) or content_column not in _table_columns(conn, table_name):
        return []
    return predict_repository.load_distinct_non_empty_column_values_by_frequency(
        conn,
        table_name,
        content_column,
    )


def _pipe_right_zodiac_values(content: str) -> tuple[str, ...]:
    """提取 `标签|生肖列表` 右侧的生肖值，用于判断分类与候选生肖是否互斥。"""
    values: list[str] = []
    for item in parse_json_or_plain_content(content):
        if "|" not in item:
            continue
        _, raw_values = item.split("|", 1)
        for value in raw_values.split(","):
            value = value.strip()
            if value in ZODIAC_ORDER and value not in values:
                values.append(value)
    return tuple(values)


def format_content_xiao_columns(table_name: str, xiao_column: str = "xiao", content_column: str = "content"):
    """还原 `content+xiao` 输出结构。
    这类历史表的 content 是分类池，xiao 是最终生肖候选。根据历史样本，xiao 候选
    与 content 分类内生肖互斥，因此生成时优先选一个与预测生肖不重叠的历史分类。
    content_column 允许指定输出键名，兼容表的实际列名（如 title 替代 content）。
    """

    def formatter(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, str]:
        selected = set(labels)
        pool = _content_category_pool(conn, table_name, content_column)
        content = ""
        for candidate in pool:
            if not selected.intersection(_pipe_right_zodiac_values(candidate)):
                content = candidate
                break
        if not content and pool:
            content = pool[0]
        return {
            content_column: content,
            xiao_column: ",".join(labels),
        }

    return formatter


def format_mixed_xiao_tail_columns(
    xiao_width: int,
    tail_width: int,
    xiao_codes_per_label: int = 0,
    xiao_column: str = "xiao",
    tail_column: str = "wei",
):
    """还原 `xiao/wei` 混合输出结构。"""

    def formatter(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, str]:
        zodiac_labels = [label.removeprefix("肖:") for label in labels if label.startswith("肖:")][:xiao_width]
        tail_labels = [label.removeprefix("尾:") for label in labels if label.startswith("尾:")][:tail_width]
        if xiao_codes_per_label > 0:
            xiao_value = json.dumps(
                [
                    f"{label}|{','.join(get_zodiac_numbers(conn, label)[:xiao_codes_per_label])}"
                    for label in zodiac_labels
                ],
                ensure_ascii=False,
            )
        else:
            xiao_value = ",".join(zodiac_labels)
        return {
            xiao_column: xiao_value,
            tail_column: json.dumps(format_tail_groups(tuple(tail_labels), conn), ensure_ascii=False),
        }

    return formatter














def format_title_jiexi(title: str):
    """文案类玩法没有稳定生成文案模型，这里输出可审计的预测标题和候选生肖。"""

    def formatter(labels: tuple[str, ...], _: sqlite3.Connection) -> dict[str, Any]:
        return {
            "title": title,
            "jiexi": "".join(labels),
            "content": f"{title}：{','.join(labels)}",
        }

    return formatter


SEGMENT_ORDER = tuple(f"{index}段" for index in range(1, 8))
XIONGJI_LABELS = ("凶丑", "吉美")




def special_xiongjiliuxiao_from_row(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
    zodiac = special_zodiac_from_number_map(row, conn)
    if not zodiac:
        return ""
    mapping = load_fixed_value_map(conn, "凶丑吉美生肖", XIONGJI_LABELS)
    for label in XIONGJI_LABELS:
        if zodiac in mapping.get(label, ()):
            return label
    if zodiac in {"鼠", "牛", "虎", "猴", "狗", "猪"}:
        return "凶丑"
    if zodiac in {"兔", "龙", "蛇", "马", "羊", "鸡"}:
        return "吉美"
    return ""




def format_xiongjiliuxiao_groups(labels: tuple[str, ...], conn: sqlite3.Connection) -> list[str]:
    mapping = load_fixed_value_map(conn, "凶丑吉美生肖", labels)
    fallback = {
        "凶丑": ("鼠", "牛", "虎", "猴", "狗", "猪"),
        "吉美": ("兔", "龙", "蛇", "马", "羊", "鸡"),
    }
    result: list[str] = []
    for label in labels:
        values = tuple(item for item in mapping.get(label, ()) if str(item).strip())
        if not values:
            values = fallback.get(label, ())
        result.append(f"{label}|{','.join(values)}")
    return result


def format_domestic_wild_groups(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, str]:
    grouped = format_split_zodiac_columns(("jia", "ye"), (4, 4))(labels, conn)
    jia = str(grouped.get("jia") or "")
    ye = str(grouped.get("ye") or "")
    return {
        **grouped,
        "content": f"家:{jia};野:{ye}",
    }


def format_literal_label(labels: tuple[str, ...], _: sqlite3.Connection) -> str:
    return labels[0] if labels else ""


TEXT_POOL_SOURCES: dict[str, tuple[str, str]] = {
    "一句真言": ("mode_payload_50", "content"),
    "四字玄机": ("mode_payload_52", "title"),
    "独家幽默": ("mode_payload_59", "content"),
}
text_mapping.text_pool_sources = TEXT_POOL_SOURCES

TEXT_HISTORY_MAPPING_TABLE = "text_history_mappings"
TEXT_HISTORY_TITLE_MARKERS = (
    "真言",
    "玄机",
    "幽默",
    "谜语",
    "欲钱",
    "词语",
    "成语",
    "破天机",
    "老黄历",
)
TEXT_HISTORY_COLUMN_PREFERENCE = ("content", "title", "jiexi")
text_mapping.text_history_mapping_table = TEXT_HISTORY_MAPPING_TABLE
text_mapping.text_history_column_preference = TEXT_HISTORY_COLUMN_PREFERENCE


def _text_history_preferred_column(conn: sqlite3.Connection, modes_id: int) -> str | None:
    """从精简后的 text_history_mappings 里选一个优先展示字段。"""
    if not table_exists(conn, TEXT_HISTORY_MAPPING_TABLE):
        return None
    columns = set(_table_column_list(conn, TEXT_HISTORY_MAPPING_TABLE))
    mode_column = "mode_id" if "mode_id" in columns else ("modes_id" if "modes_id" in columns else "")
    filters = []
    params: list[Any] = []
    if modes_id >= 0:
        if not mode_column:
            return None
        filters.append(f"{quote_identifier(mode_column)} = ?")
        params.append(modes_id)
    for column in TEXT_HISTORY_COLUMN_PREFERENCE:
        if column not in columns:
            continue
        if predict_repository.has_text_history_column_value(
            conn,
            TEXT_HISTORY_MAPPING_TABLE,
            column,
            mode_column=mode_column,
            modes_id=modes_id if filters else None,
        ):
            return column
    return None


text_mapping.text_history_preferred_column = _text_history_preferred_column


def _random_text_history_mapping_row(
    conn: sqlite3.Connection,
    modes_id: int,
    selected_zodiacs: tuple[str, ...] = (),
    text_column: str | None = None,
) -> sqlite3.Row | None:
    """从精简后的 text_history_mappings 随机抽取一条文本记录。"""
    del selected_zodiacs
    if not table_exists(conn, TEXT_HISTORY_MAPPING_TABLE):
        return None

    columns = set(_table_column_list(conn, TEXT_HISTORY_MAPPING_TABLE))
    preferred_column = text_column or _text_history_preferred_column(conn, modes_id)
    mode_column = "mode_id" if "mode_id" in columns else ("modes_id" if "modes_id" in columns else "")
    filters: list[str] = []
    params: list[Any] = []
    if modes_id >= 0:
        if not mode_column:
            return None
        filters.append(f"{quote_identifier(mode_column)} = ?")
        params.append(modes_id)

    if "payload_json" in columns or "text_content" in columns:
        where_parts = list(filters)
        legacy_text_parts = []
        if "payload_json" in columns:
            legacy_text_parts.append("COALESCE(payload_json, '') != ''")
        if "text_content" in columns:
            legacy_text_parts.append("COALESCE(text_content, '') != ''")
        if legacy_text_parts:
            where_parts.append(f"({' OR '.join(legacy_text_parts)})")
            row = predict_repository.load_random_text_history_row(
                conn,
                TEXT_HISTORY_MAPPING_TABLE,
                mode_column=mode_column,
                modes_id=modes_id if filters else None,
                non_empty_columns=tuple(
                    column_name
                    for column_name in ("payload_json", "text_content")
                    if column_name in columns
                ),
            )
            if row:
                return row

    if preferred_column and preferred_column in columns:
        row = predict_repository.load_random_text_history_row(
            conn,
            TEXT_HISTORY_MAPPING_TABLE,
            mode_column=mode_column,
            modes_id=modes_id if filters else None,
            non_empty_columns=(preferred_column,),
        )
        if row:
            return row

    available_columns = [column for column in TEXT_HISTORY_COLUMN_PREFERENCE if column in columns]
    if not available_columns:
        return None
    row = predict_repository.load_random_text_history_row(
        conn,
        TEXT_HISTORY_MAPPING_TABLE,
        mode_column=mode_column,
        modes_id=modes_id if filters else None,
        non_empty_columns=tuple(available_columns),
    )
    if row:
        return row

    return None


text_mapping.random_text_history_mapping_row = _random_text_history_mapping_row


def _text_history_row_payload(row: Any) -> dict[str, Any]:
    """Normalize old/new text_history_mappings rows to title/content/jiexi."""
    result: dict[str, Any] = {}
    keys = row.keys() if hasattr(row, "keys") else ()
    if "payload_json" in keys and row["payload_json"]:
        try:
            parsed = json.loads(str(row["payload_json"]))
            if isinstance(parsed, dict):
                for key in ("title", "content", "jiexi"):
                    if parsed.get(key) not in (None, ""):
                        result[key] = str(parsed.get(key) or "")
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    for key in ("title", "content", "jiexi"):
        if key in keys and row[key] not in (None, ""):
            result.setdefault(key, str(row[key] or ""))

    if "text_content" in keys and row["text_content"] not in (None, ""):
        text_column = str(row["text_column"] or "").strip() if "text_column" in keys else ""
        target_column = text_column if text_column in {"title", "content", "jiexi"} else "content"
        result.setdefault(target_column, str(row["text_content"] or ""))

    return result


text_mapping.text_history_row_payload = _text_history_row_payload


def _table_output_columns(
    conn: sqlite3.Connection,
    table_name: str,
    allowed_columns: tuple[str, ...],
) -> tuple[str, ...]:
    """按表实际列过滤输出字段，避免生成不存在的业务列。"""
    if not table_exists(conn, table_name):
        return allowed_columns
    columns = set(_table_column_list(conn, table_name))
    return tuple(column for column in allowed_columns if column in columns)


text_mapping.table_output_columns = _table_output_columns




image.table_exists = table_exists
image.table_columns = _table_column_list
format_window_content = image.format_window_content

jiexi_content_from_row = content_columns.jiexi_content_from_row
tail_code_content_from_row = content_columns.tail_code_content_from_row
xiao_code_content_from_row = content_columns.xiao_code_content_from_row
black_white_content_from_row = content_columns.black_white_content_from_row
join_columns_content_loader = content_columns.join_columns_content_loader
parsed_columns_content_loader = content_columns.parsed_columns_content_loader
tail_columns_content_loader = content_columns.tail_columns_content_loader
parse_tail_digit_content = content_columns.parse_tail_digit_content
parse_zodiac_chars = content_columns.parse_zodiac_chars
parse_wave_chars = content_columns.parse_wave_chars
parse_literal_label_content = content_columns.parse_literal_label_content


def _is_text_history_title(title: str) -> bool:
    return any(marker in title for marker in TEXT_HISTORY_TITLE_MARKERS)


def _make_text_history_mapping_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    text_column: str | None = None,
) -> PredictionConfig:
    """构建历史文本映射玩法。

    命中口径仍按当期特码生肖评估；预测输出阶段不解析文本，而是从
    text_history_mappings 中随机抽取一条历史文本及其对应的特码号码/生肖。
    """
    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(ZODIAC_ORDER),
        label_count=1,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=text_mapping.format_text_history_mapping(title, modes_id, text_column),
        hit_checker=contains_hit,
        explanation=(
            f"{title} 属于文本历史映射玩法，不做固定语义推理。",
            "系统从 text_history_mappings 读取历史中已经出现过的文本与当期特码号码/生肖配对。",
            "预测时先按历史特码生肖选择候选生肖，再随机抽取一条匹配的历史文本配对；若没有匹配项则从该玩法历史池随机抽取。",
        ),
    )


def format_black_white(labels: tuple[str, ...], _: sqlite3.Connection) -> dict[str, str]:
    """黑白各3肖：前 3 个放黑肖，后 3 个放白肖。"""
    return {
        "hei": ",".join(labels[:3]),
        "bai": ",".join(labels[3:6]),
    }


def format_element_groups(labels: tuple[str, ...], conn: sqlite3.Connection) -> list[str]:
    """3行中特接口沿用历史格式：`行|号码列表` 的 JSON 数组。"""
    number_to_element = build_element_number_map(conn)
    result: list[str] = []
    for label in labels:
        numbers = [
            number
            for number, element in sorted(number_to_element.items(), key=lambda item: int(item[0]))
            if element == label
        ]
        result.append(f"{label}|{','.join(numbers)}")
    return result


# Static configurations capture these callables at import time. Rebind category
# implementations after legacy local definitions so configurations use one source.
label_for_special_number = size_parity.label_for_special_number
format_fixed_groups = size_parity.format_fixed_groups
special_head_from_row = size_parity.special_head_from_row
special_tail_from_row = size_parity.special_tail_from_row
special_parity_from_row = size_parity.special_parity_from_row
special_size_from_row = size_parity.special_size_from_row
special_half_wave_from_row = size_parity.special_half_wave_from_row
special_wave_from_row = size_parity.special_wave_from_row
special_combined_parity_from_row = size_parity.special_combined_parity_from_row
special_combined_size_from_row = size_parity.special_combined_size_from_row
format_head_groups = size_parity.format_head_groups
format_tail_groups = size_parity.format_tail_groups
format_size_groups = size_parity.format_size_groups
format_half_wave_groups = size_parity.format_half_wave_groups
format_parity_groups = size_parity.format_parity_groups

parse_mixed_dimension_content = mixed.parse_mixed_dimension_content
mixed_dimension_contains_hit = mixed.mixed_dimension_contains_hit
mixed_dimension_excludes_hit = mixed.mixed_dimension_excludes_hit

get_zodiac_numbers = zodiac.get_zodiac_numbers
format_zodiac_one_code = zodiac.format_zodiac_one_code
format_zodiac_two_codes = zodiac.format_zodiac_two_codes
format_zodiac_all_codes = zodiac.format_zodiac_all_codes
format_9x12 = zodiac.format_9x12
format_zodiac_csv = zodiac.format_zodiac_csv
format_xiao_pair = zodiac.format_xiao_pair
format_split_zodiac_columns = zodiac.format_split_zodiac_columns
format_xiao_code_columns = zodiac.format_xiao_code_columns

format_text_history_mapping = text_mapping.format_text_history_mapping
random_text_pool_row = text_mapping.random_text_pool_row
format_text_pool_jiexi = text_mapping.format_text_pool_jiexi
format_humor_tail_groups = text_mapping.format_humor_tail_groups
format_juzi_title = text_mapping.format_juzi_title

special_number_from_row = number.special_number_from_row
format_24_numbers = number.format_24_numbers
special_segment_from_row = number.special_segment_from_row
format_segment_groups = number.format_segment_groups
format_split_number_columns = number.format_split_number_columns

make_pipe_category_outcome = structured_mapping.make_pipe_category_outcome
qinqi_outcome_from_row = structured_mapping.qinqi_outcome_from_row
format_zodiac_groups = structured_mapping.format_zodiac_groups
format_qinqi_content = structured_mapping.format_qinqi_content
format_window_content = image.format_window_content


def three_head_four_tail_content_loader(row: Any) -> str:
    """Read the combined head/tail payload without flattening its dimensions."""
    return default_content_from_row(row)


def parse_three_head_four_tail_content(content: str) -> tuple[str, ...]:
    try:
        payload = json.loads(str(content or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return ()
    if not isinstance(payload, dict):
        return ()
    heads = payload.get("heads") if isinstance(payload.get("heads"), list) else []
    tails = payload.get("tails") if isinstance(payload.get("tails"), list) else []
    return tuple(
        [f"头:{str(value).strip()}" for value in heads if str(value).strip()]
        + [f"尾:{str(value).strip()}" for value in tails if str(value).strip()]
    )


def format_three_head_four_tail(labels: tuple[str, ...], _conn: Any) -> str:
    heads = [label.removeprefix("头:") for label in labels if label.startswith("头:")][:3]
    tails = [label.removeprefix("尾:") for label in labels if label.startswith("尾:")][:4]
    return json.dumps({"heads": heads, "tails": tails}, ensure_ascii=False, separators=(",", ":"))


def three_head_four_tail_outcome(row: Any, conn: Any) -> str:
    return f"头:{special_head_from_row(row, conn)}|尾:{special_tail_from_row(row, conn)}"


def three_head_four_tail_hit(outcome: str, labels: tuple[str, ...]) -> bool:
    required = tuple(part for part in str(outcome or "").split("|") if part)
    return bool(required) and all(part in labels for part in required)


def format_expert_publications(labels: tuple[str, ...], _conn: Any) -> str:
    return json.dumps({"publications": list(labels)}, ensure_ascii=False, separators=(",", ":"))

PREDICTION_CONFIGS: dict[str, PredictionConfig] = {
    "3tou": PredictionConfig(
        key="3tou",
        title="3头中特",
        default_table="mode_payload_12",
        default_modes_id=12,
        labels=tuple(HEAD_NUMBER_MAP.keys()),
        label_count=3,
        outcome_loader=special_head_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_head_groups,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("头", tuple(HEAD_NUMBER_MAP.keys())),
        explanation=(
            "3头中特将 01-49 按十位分为 0头、1头、2头、3头、4头。",
            "开奖结果 res_code 最后一个号码按特码处理，特码所在头数落入预测的 3 个头即为命中。",
            "脚本滚动浏览历史开奖记录，回测多个窗口和策略，选择历史命中率最接近 65% 的策略生成本次 content。",
        ),
    ),
    "3zxt": PredictionConfig(
        key="3zxt",
        title="3肖中特",
        default_table="mode_payload_69",
        default_modes_id=69,
        labels=tuple(ZODIAC_ORDER),
        label_count=3,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_csv,
        hit_checker=contains_hit,
        explanation=(
            "3肖中特从 12 个生肖中选出 3 个生肖作为 content。",
            "开奖结果 res_code 最后一个号码按特码处理，特码生肖优先从 res_sx 最后一项读取；缺失时从 fixed_data 的生肖映射推导。",
            "若特码生肖落入预测的 3 个生肖，则本期按命中计算。",
            "脚本滚动浏览历史开奖记录，回测多个窗口和策略，选择历史命中率最接近 65% 的策略生成本次 content。",
        ),
    ),
    "3hang": PredictionConfig(
        key="3hang",
        title="3行中特",
        default_table="mode_payload_53",
        default_modes_id=53,
        labels=tuple(ELEMENT_ORDER),
        label_count=3,
        outcome_loader=special_element_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_element_groups,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("五行肖", tuple(ELEMENT_ORDER)),
        explanation=(
            "3行中特从 金、木、水、火、土 五行中选出 3 行作为 content。",
            "开奖结果 res_code 最后一个号码按特码处理，脚本通过历史 3行中特 content 建立 01-49 号码到五行的映射。",
            "若特码号码所属五行落入预测的 3 行，则本期按命中计算。",
            "脚本滚动浏览历史开奖记录，回测多个窗口和策略，选择历史命中率最接近 65% 的策略生成本次 content。",
        ),
    ),
    "rcca": PredictionConfig(
        key="rcca",
        title="肉菜草肖",
        default_table="mode_payload_3",
        default_modes_id=3,
        labels=("肉肖", "菜肖", "草肖"),
        label_count=2,
        outcome_loader=make_pipe_category_outcome("mode_payload_3", ("肉肖", "菜肖", "草肖")),
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_zodiac_groups("mode_payload_3", ("肉肖", "菜肖", "草肖")),
        hit_checker=contains_hit,
        explanation=(
            "肉菜草肖把 12 个生肖分为肉肖、菜肖、草肖三类，每次选择其中两类。",
            "特码生肖所属分类落入预测分类则命中。",
        ),
    ),
    "hllx": PredictionConfig(
        key="hllx",
        title="红蓝绿肖（3选2）",
        default_table="mode_payload_8",
        default_modes_id=8,
        labels=("红肖", "蓝肖", "绿肖"),
        label_count=2,
        outcome_loader=make_pipe_category_outcome("mode_payload_8", ("红肖", "蓝肖", "绿肖")),
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_zodiac_groups("mode_payload_8", ("红肖", "蓝肖", "绿肖")),
        hit_checker=contains_hit,
        explanation=(
            "红蓝绿肖（3选2）把生肖分为红肖、蓝肖、绿肖三类，每次选择其中两类。",
            "特码生肖所属分类落入预测分类则命中。",
        ),
    ),
    "juesha1wei": PredictionConfig(
        key="juesha1wei",
        title="绝杀一尾",
        default_table="mode_payload_20",
        default_modes_id=20,
        labels=tuple(TAIL_NUMBER_MAP.keys()),
        label_count=1,
        outcome_loader=special_tail_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_tail_groups,
        hit_checker=excludes_hit,
        labels_loader=labels_from_fixed("尾", tuple(TAIL_NUMBER_MAP.keys())),
        explanation=(
            "绝杀一尾选择 1 个尾数作为排除尾。",
            "若特码尾数没有落入预测的绝杀尾，则本期按命中计算。",
        ),
    ),
    "qinqi": PredictionConfig(
        key="qinqi",
        title="琴棋书画",
        default_table="mode_payload_26",
        default_modes_id=26,
        labels=("琴", "棋", "书", "画"),
        label_count=3,
        outcome_loader=qinqi_outcome_from_row,
        content_loader=title_content_from_row,
        content_parser=parse_literal_label_content,
        content_formatter=format_qinqi_content,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("四艺生肖", ("琴", "棋", "书", "画")),
        explanation=(
            "琴棋书画把生肖分为琴、棋、书、画四类，每次选择三类。",
            "该表 title 存预测标签（如 画,琴,棋），content 存按标签展开的生肖。",
        ),
    ),
    "danshuangtema": PredictionConfig(
        key="danshuangtema",
        title="单双中特（单双码）",
        default_table="mode_payload_28",
        default_modes_id=28,
        labels=("单", "双"),
        label_count=1,
        outcome_loader=special_parity_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_parity_groups,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("单双", ("单", "双")),
        explanation=(
            "单双中特按特码号码奇偶分为单、双。",
            "特码奇偶与预测标签一致则命中。",
        ),
    ),
    "danshuang4xiao": PredictionConfig(
        key="danshuang4xiao",
        title="单双四肖",
        default_table="mode_payload_31",
        default_modes_id=31,
        labels=tuple(ZODIAC_ORDER),
        label_count=8,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=xiao_pair_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_xiao_pair,
        hit_checker=contains_hit,
        explanation=(
            "单双四肖原表使用 xiao_1/xiao_2 两列，每列 4 个生肖。",
            "脚本预测 8 个生肖并拆成两组；特码生肖落入任一组则命中。",
        ),
    ),
    "ma24": PredictionConfig(
        key="ma24",
        title="24码",
        default_table="mode_payload_34",
        default_modes_id=34,
        labels=tuple(f"{number:02d}" for number in range(1, 50)),
        label_count=24,
        outcome_loader=special_number_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_number_content,
        content_formatter=format_24_numbers,
        hit_checker=contains_hit,
        explanation=(
            "24码从 01-49 中选择 24 个号码。",
            "特码号码落入预测的 24 个号码则命中。",
        ),
    ),
    "three_head_four_tail": PredictionConfig(
        key="three_head_four_tail",
        title="三头四尾",
        default_table="mode_payload_492",
        default_modes_id=492,
        labels=(
            "头:0头", "头:1头", "头:2头", "头:3头", "头:4头",
            "尾:0尾", "尾:1尾", "尾:2尾", "尾:3尾", "尾:4尾",
            "尾:5尾", "尾:6尾", "尾:7尾", "尾:8尾", "尾:9尾",
        ),
        label_count=7,
        outcome_loader=three_head_four_tail_outcome,
        content_loader=three_head_four_tail_content_loader,
        content_parser=parse_three_head_four_tail_content,
        content_formatter=format_three_head_four_tail,
        hit_checker=three_head_four_tail_hit,
        explanation=(
            "三头四尾分别选择3个头数和4个尾数。",
            "特码头数与尾数同时落入各自候选集合才记为命中。",
        ),
        selection_groups=(
            ("头:0头", "头:1头", "头:2头", "头:3头", "头:4头"),
            ("尾:0尾", "尾:1尾", "尾:2尾", "尾:3尾", "尾:4尾", "尾:5尾", "尾:6尾", "尾:7尾", "尾:8尾", "尾:9尾"),
        ),
        selection_widths=(3, 4),
    ),
    "expert_publications": PredictionConfig(
        key="expert_publications",
        title="精准台湾高手资料",
        default_table="mode_payload_495",
        default_modes_id=495,
        labels=(
            "平特一肖", "大小中特", "双波中特", "平特三肖", "四肖八码", "七尾中特", "精选22码",
            "绝杀二肖", "绝杀一波", "绝杀一尾", "稳杀七码", "一句话中特码", "三头四尾", "家禽VS野兽",
        ),
        label_count=14,
        outcome_loader=lambda _row, _conn: "",
        content_loader=default_content_from_row,
        content_parser=lambda content: tuple(
            str(item).strip()
            for item in (json.loads(str(content or "{}")) or {}).get("publications", [])
            if str(item).strip()
        ) if str(content or "").lstrip().startswith("{") else (),
        content_formatter=format_expert_publications,
        hit_checker=contains_hit,
        explanation=(
            "精准台湾高手资料由本站已授权的14项后端预测机制组成。",
            "该索引只发布当前后端资料名称和期号，不沿用供应商专家快照。",
        ),
    ),
    "selected_22_codes": PredictionConfig(
        key="selected_22_codes",
        title="精选22码",
        default_table="mode_payload_493",
        default_modes_id=493,
        labels=tuple(f"{number:02d}" for number in range(1, 50)),
        label_count=22,
        outcome_loader=special_number_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_number_content,
        content_formatter=lambda labels, _conn: ",".join(labels),
        hit_checker=contains_hit,
        explanation=(
            "精选22码从01-49中选择22个号码。",
            "特码号码落入候选号码集合即记为命中。",
        ),
    ),
    "wuzhong5ma": PredictionConfig(
        key="wuzhong5ma",
        title="内幕5不中",
        default_table="mode_payload_485",
        default_modes_id=485,
        labels=tuple(f"{number:02d}" for number in range(1, 50)),
        label_count=5,
        outcome_loader=special_number_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_number_content,
        content_formatter=format_24_numbers,
        hit_checker=excludes_hit,
        explanation=(
            "内幕5不中从01-49中选择5个号码作为排除号码。",
            "特码号码不在这5个号码内时按命中计算。",
        ),
    ),
    "shuangbo": PredictionConfig(
        key="shuangbo",
        title="双波中特",
        default_table="mode_payload_38",
        default_modes_id=38,
        labels=("红波", "蓝波", "绿波"),
        label_count=2,
        outcome_loader=special_wave_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_wave_csv,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("波色", ("红波", "蓝波", "绿波")),
        explanation=(
            "双波中特从红波、蓝波、绿波中选择两波。",
            "特码波色落入预测波色则命中。",
        ),
    ),
    "juesha3xiao": PredictionConfig(
        key="juesha3xiao",
        title="绝杀3肖",
        default_table="mode_payload_42",
        default_modes_id=42,
        labels=tuple(ZODIAC_ORDER),
        label_count=3,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_csv,
        hit_checker=excludes_hit,
        explanation=(
            "绝杀3肖选择 3 个生肖作为排除生肖。",
            "若特码生肖没有落入预测的绝杀生肖，则本期按命中计算。",
        ),
    ),
    "pt2xiao": PredictionConfig(
        key="pt2xiao",
        title="平特2肖",
        default_table="mode_payload_43",
        default_modes_id=43,
        labels=tuple(ZODIAC_ORDER),
        label_count=2,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_csv,
        hit_checker=contains_hit,
        explanation=(
            "平特2肖选择 2 个生肖。",
            "按统一预测口径，特码生肖落入预测生肖则命中。",
        ),
    ),
    "siduanzhongte": PredictionConfig(
        key="siduanzhongte",
        title="四段中特",
        default_table="mode_payload_479",
        default_modes_id=479,
        labels=SEGMENT_ORDER,
        label_count=4,
        outcome_loader=special_segment_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_segment_groups,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("7段", SEGMENT_ORDER),
        explanation=(
            "四段中特把 01-49 按 7 段分组，按特码号码归属段位命中。",
            "输出沿用 `N段|号码列表` 结构，方便前端按段位展示。",
        ),
    ),
    "xiongjiliuxiao": PredictionConfig(
        key="xiongjiliuxiao",
        title="凶吉六肖",
        default_table="mode_payload_480",
        default_modes_id=480,
        labels=XIONGJI_LABELS,
        label_count=1,
        outcome_loader=special_xiongjiliuxiao_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_xiongjiliuxiao_groups,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("凶丑吉美生肖", XIONGJI_LABELS),
        explanation=(
            "凶吉六肖按生肖分为凶丑与吉美两类，按特码生肖归类命中。",
            "输出沿用分类+生肖列表结构，优先读取 fixed_data 中的凶丑吉美生肖映射。",
        ),
    ),
    "sanxiao15ma": PredictionConfig(
        key="sanxiao15ma",
        title="三肖15码中特",
        default_table="mode_payload_72",
        default_modes_id=72,
        labels=tuple(ZODIAC_ORDER),
        label_count=9,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=xiao_code_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_xiao_code_columns("xiao", "code", 15),
        hit_checker=contains_hit,
        explanation=(
            "三肖15码中特沿用 xiao/code 双列结构，生成 9 个生肖与 15 个号码。",
            "前端会按 7 肖、5 肖、3 肖和 15 码递进展示同一条预测。",
        ),
    ),
    "shisi_mazhong": PredictionConfig(
        key="shisi_mazhong",
        title="14码中特",
        default_table="mode_payload_77",
        default_modes_id=77,
        labels=tuple(f"{number:02d}" for number in range(1, 50)),
        label_count=14,
        outcome_loader=special_number_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_number_content,
        content_formatter=format_24_numbers,
        hit_checker=contains_hit,
        explanation=(
            "14码中特按号码类玩法处理，输出 14 个候选号码。",
            "特码号码落入候选号码集合即记为命中。",
        ),
    ),
    "sixiao_sima": PredictionConfig(
        key="sixiao_sima",
        title="四肖四码",
        default_table="mode_payload_78",
        default_modes_id=78,
        labels=tuple(ZODIAC_ORDER),
        label_count=4,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_one_code,
        hit_checker=contains_hit,
        explanation=(
            "四肖四码输出 4 组 `生肖|代表号码` 结构。",
            "特码生肖落入候选生肖集合即记为命中。",
        ),
    ),
    "shiwu_mazhong": PredictionConfig(
        key="shiwu_mazhong",
        title="15码中特",
        default_table="mode_payload_81",
        default_modes_id=81,
        labels=tuple(TAIL_NUMBER_MAP.keys()),
        label_count=5,
        outcome_loader=special_tail_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_tail_digit_content,
        content_formatter=format_tail_groups,
        hit_checker=contains_hit,
        labels_loader=lambda _conn: tuple(TAIL_NUMBER_MAP.keys()),
        explanation=(
            "15码中特沿用尾数分组结构，输出 5 组尾数及其固定号码。",
            "特码尾数落入候选尾数组合即记为命中。",
        ),
    ),
    "sanxiao_siwei_xiao": PredictionConfig(
        key="sanxiao_siwei_xiao",
        title="三肖四尾",
        default_table="mode_payload_117",
        default_modes_id=117,
        labels=tuple(ZODIAC_ORDER),
        label_count=3,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_one_code,
        hit_checker=contains_hit,
        explanation=(
            "三肖四尾中的生肖半区输出 3 组 `生肖|代表号码`。",
            "特码生肖落入候选生肖集合即记为命中。",
        ),
    ),
    "sanxiao_siwei_wei": PredictionConfig(
        key="sanxiao_siwei_wei",
        title="四尾八码",
        default_table="mode_payload_123",
        default_modes_id=123,
        labels=tuple(TAIL_NUMBER_MAP.keys()),
        label_count=4,
        outcome_loader=special_tail_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_tail_digit_content,
        content_formatter=format_tail_groups,
        hit_checker=contains_hit,
        labels_loader=lambda _conn: tuple(TAIL_NUMBER_MAP.keys()),
        explanation=(
            "三肖四尾中的尾数半区输出 4 组尾数与固定号码。",
            "特码尾数落入候选尾数组合即记为命中。",
        ),
    ),
    "wensha10ma": PredictionConfig(
        key="wensha10ma",
        title="稳杀10码",
        default_table="mode_payload_481",
        default_modes_id=481,
        labels=tuple(f"{number:02d}" for number in range(1, 50)),
        label_count=10,
        outcome_loader=special_number_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_number_content,
        content_formatter=format_24_numbers,
        hit_checker=excludes_hit,
        explanation=(
            "稳杀10码按号码类玩法处理，从 01-49 中选出 10 个号码。",
            "特码号码落入预测号码集合外时按命中计算。",
        ),
    ),
    "steady_kill_7_codes": PredictionConfig(
        key="steady_kill_7_codes",
        title="稳杀7码",
        default_table="mode_payload_494",
        default_modes_id=494,
        labels=tuple(f"{number:02d}" for number in range(1, 50)),
        label_count=7,
        outcome_loader=special_number_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_number_content,
        content_formatter=lambda labels, _conn: ",".join(labels),
        hit_checker=excludes_hit,
        explanation=(
            "稳杀7码从01-49中选择7个号码作为排除号码。",
            "特码不在7个排除号码内时按命中计算。",
        ),
    ),
    "sihangzhongte": PredictionConfig(
        key="sihangzhongte",
        title="四行中特",
        default_table="mode_payload_482",
        default_modes_id=482,
        labels=tuple(ELEMENT_ORDER),
        label_count=4,
        outcome_loader=special_element_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_element_groups,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("五行肖", tuple(ELEMENT_ORDER)),
        explanation=(
            "四行中特按五行分组，优先读取 public.fixed_data 中的五行肖映射。",
            "特码号码所属五行落入预测集合即命中。",
        ),
    ),
    "sitouzhongte": PredictionConfig(
        key="sitouzhongte",
        title="四头中特",
        default_table="mode_payload_483",
        default_modes_id=483,
        labels=tuple(HEAD_NUMBER_MAP.keys()),
        label_count=4,
        outcome_loader=special_head_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_head_groups,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("头", tuple(HEAD_NUMBER_MAP.keys())),
        explanation=(
            "四头中特按特码十位分为 0头~4头，输出沿用头数号码列表结构。",
            "特码头数落入预测集合即命中。",
        ),
    ),
    "liuxiao18ma": PredictionConfig(
        key="liuxiao18ma",
        title="六肖十八码",
        default_table="mode_payload_484",
        default_modes_id=484,
        labels=tuple(ZODIAC_ORDER),
        label_count=6,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_xiao_code_columns("xiao", "code", 18),
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("生肖", tuple(ZODIAC_ORDER)),
        explanation=(
            "六肖十八码按生肖类玩法处理，输出 xiao/code 双列结构。",
            "特码生肖落入预测生肖集合即命中，code 从 fixed_data 的生肖号码映射生成。",
        ),
    ),
    "daimingxiao": PredictionConfig(
        key="daimingxiao",
        title="代号生肖",
        default_table="mode_payload_486",
        default_modes_id=486,
        labels=tuple(ZODIAC_ORDER),
        label_count=5,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_word_codes,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("生肖", tuple(ZODIAC_ORDER)),
        explanation=("代号生肖输出五个含生肖字的固定词语。", "特码生肖出现于五个代号词对应生肖时命中。"),
    ),
    "liuweichute": PredictionConfig(
        key="liuweichute",
        title="六尾出特",
        default_table="mode_payload_487",
        default_modes_id=487,
        labels=tuple(TAIL_NUMBER_MAP.keys()),
        label_count=6,
        outcome_loader=special_tail_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_tail_digit_content,
        content_formatter=lambda labels, _conn: ",".join(labels),
        hit_checker=contains_hit,
        labels_loader=lambda _conn: tuple(TAIL_NUMBER_MAP.keys()),
        explanation=("六尾出特选择六个尾数。", "特码尾数在候选尾数内时命中。"),
    ),
    "toudanshuang": PredictionConfig(
        key="toudanshuang",
        title="头数单双",
        default_table="mode_payload_488",
        default_modes_id=488,
        labels=tuple(f"{head}头{parity}" for head in range(5) for parity in ("单", "双")),
        label_count=5,
        outcome_loader=lambda row, _conn: (
            ("0头" if int(special_code_from_res_code(row["res_code"] or "")) < 10 else f"{int(special_code_from_res_code(row['res_code'] or '')) // 10}头")
            + ("双" if int(special_code_from_res_code(row["res_code"] or "")) % 2 == 0 else "单")
        ),
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=lambda labels, _conn: list(labels),
        hit_checker=contains_hit,
        explanation=("头数单双选择五个十位头数与单双的组合。", "特码的头数及单双组合在候选内时命中。"),
    ),
    "liuxiaoliuma": PredictionConfig(
        key="liuxiaoliuma",
        title="六肖六码",
        default_table="mode_payload_489",
        default_modes_id=489,
        labels=tuple(ZODIAC_ORDER),
        label_count=6,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_xiao_code_columns("xiao", "code", 6),
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("生肖", tuple(ZODIAC_ORDER)),
        explanation=("六肖六码输出六肖及每肖一个代表号码。", "特码生肖在六个候选生肖内时命中。"),
    ),
    "shaliangbanbo": PredictionConfig(
        key="shaliangbanbo",
        title="杀两半波",
        default_table="mode_payload_490",
        default_modes_id=490,
        labels=tuple(HALF_WAVE_NUMBER_MAP.keys()),
        label_count=2,
        outcome_loader=special_half_wave_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=lambda labels, _conn: ",".join(labels),
        hit_checker=excludes_hit,
        labels_loader=labels_from_fixed("波色单双", tuple(HALF_WAVE_NUMBER_MAP.keys())),
        explanation=("杀两半波选择两个半波作为排除项。", "特码半波不在两个排除项内时命中。"),
    ),
    "gongshi_siw": PredictionConfig(
        key="gongshi_siw",
        title="公式四尾",
        default_table="mode_payload_491",
        default_modes_id=491,
        labels=tuple(TAIL_NUMBER_MAP.keys()),
        label_count=4,
        outcome_loader=special_tail_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_tail_digit_content,
        content_formatter=lambda labels, _conn: ",".join(labels),
        hit_checker=contains_hit,
        labels_loader=lambda _conn: tuple(TAIL_NUMBER_MAP.keys()),
        explanation=("公式四尾选择四个尾数。", "特码尾数在四个公式尾数内时命中。"),
    ),
    "pt3xiao": PredictionConfig(
        key="pt3xiao",
        title="平特3肖",
        default_table="mode_payload_470",
        default_modes_id=470,
        labels=tuple(ZODIAC_ORDER),
        label_count=3,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_csv,
        hit_checker=contains_hit,
        explanation=(
            "平特3肖选择 3 个生肖。",
            "按统一预测口径，特码生肖落入预测生肖则命中。",
        ),
    ),
    "liangtouzxt": PredictionConfig(
        key="liangtouzxt",
        title="两头中特",
        default_table="mode_payload_471",
        default_modes_id=471,
        labels=tuple(HEAD_NUMBER_MAP.keys()),
        label_count=2,
        outcome_loader=special_head_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_head_groups,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("头", tuple(HEAD_NUMBER_MAP.keys())),
        explanation=(
            "两头中特从 0头、1头、2头、3头、4头中选择 2 个头数。",
            "开奖结果 res_code 最后一个号码按特码处理，特码所在头数落入预测头数则命中。",
        ),
    ),
    "juesha1xiao": PredictionConfig(
        key="juesha1xiao",
        title="绝杀1肖",
        default_table="mode_payload_472",
        default_modes_id=472,
        labels=tuple(ZODIAC_ORDER),
        label_count=1,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_csv,
        hit_checker=excludes_hit,
        explanation=(
            "绝杀1肖选择 1 个生肖作为排除生肖。",
            "若特码生肖没有落入预测的绝杀生肖，则本期按命中计算。",
        ),
    ),
    "juesha2xiao": PredictionConfig(
        key="juesha2xiao",
        title="绝杀2肖",
        default_table="mode_payload_473",
        default_modes_id=473,
        labels=tuple(ZODIAC_ORDER),
        label_count=2,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_csv,
        hit_checker=excludes_hit,
        explanation=(
            "绝杀2肖选择 2 个生肖作为排除生肖。",
            "若特码生肖没有落入预测的绝杀生肖，则本期按命中计算。",
        ),
    ),
    "7xiao7ma": PredictionConfig(
        key="7xiao7ma",
        title="7肖7码",
        default_table="mode_payload_44",
        default_modes_id=44,
        labels=tuple(ZODIAC_ORDER),
        label_count=7,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_one_code,
        hit_checker=contains_hit,
        explanation=(
            "7肖7码选择 7 个生肖，并为每个生肖带 1 个代表号码。",
            "特码生肖落入预测生肖则命中；号码用于生成接口展示。",
        ),
    ),
    "heibai3xiao": PredictionConfig(
        key="heibai3xiao",
        title="黑白各3肖",
        default_table="mode_payload_45",
        default_modes_id=45,
        labels=tuple(ZODIAC_ORDER),
        label_count=6,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=black_white_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_black_white,
        hit_checker=contains_hit,
        explanation=(
            "黑白各3肖使用 hei/bai 两列，每列 3 个生肖。",
            "脚本预测 6 个生肖并拆成黑白两组；特码生肖落入任一组则命中。",
        ),
    ),
    "6xzt": PredictionConfig(
        key="6xzt",
        title="6肖中特",
        default_table="mode_payload_46",
        default_modes_id=46,
        labels=tuple(ZODIAC_ORDER),
        label_count=6,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_csv,
        hit_checker=contains_hit,
        explanation=(
            "6肖中特从 12 个生肖中选择 6 个。",
            "特码生肖落入预测生肖则命中。",
        ),
    ),
    "title_47": PredictionConfig(
        key="title_47",
        title="4肖中特",
        default_table="mode_payload_47",
        default_modes_id=47,
        labels=tuple(ZODIAC_ORDER),
        label_count=4,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_csv,
        hit_checker=contains_hit,
        explanation=(
            "4肖中特按生肖组选处理，从 12 个生肖中选出 4 个生肖。",
            "特码生肖落入预测生肖则命中。",
        ),
    ),
    "title_5": PredictionConfig(
        key="title_5",
        title="天地生肖（天地选1，生肖选2）",
        default_table="mode_payload_5",
        default_modes_id=5,
        labels=tuple(ZODIAC_ORDER),
        label_count=2,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=xiao_or_content_content_loader("xiao", "content"),
        content_parser=parse_zodiac_content,
        content_formatter=format_content_xiao_columns("mode_payload_5", "xiao", "content"),
        hit_checker=contains_hit,
        explanation=(
            "天地生肖按天肖/地肖分类，content 存储分类标签与生肖池，xiao 列存储最终候选生肖。",
            "特码生肖落入 xiao 列的候选生肖则命中。",
        ),
    ),
    "title_15": PredictionConfig(
        key="title_15",
        title="单双公式",
        default_table="mode_payload_15",
        default_modes_id=15,
        labels=tuple(ZODIAC_ORDER),
        label_count=2,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=xiao_column_content_loader("xiao"),
        content_parser=parse_zodiac_content,
        content_formatter=format_content_xiao_columns("mode_payload_15", "xiao", "content"),
        hit_checker=contains_hit,
        explanation=(
            "单双公式从 content 存储的分类（单生肖/双生肖）中选出一组，xiao 列存储最终候选生肖。",
            "特码生肖落入 xiao 列的候选生肖则命中。",
        ),
    ),
    "title_14": PredictionConfig(
        key="title_14",
        title="家禽野兽",
        default_table="mode_payload_14",
        default_modes_id=14,
        labels=tuple(ZODIAC_ORDER),
        label_count=8,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=parsed_columns_content_loader(("jia", "ye"), parse_zodiac_content),
        content_parser=parse_zodiac_content,
        content_formatter=format_domestic_wild_groups,
        hit_checker=contains_hit,
        selection_groups=(
            DOMESTIC_WILD_FALLBACK["家禽"],
            DOMESTIC_WILD_FALLBACK["野兽"],
        ),
        selection_widths=(4, 4),
        explanation=(
            "家禽野兽按家禽/野兽两列分组选出 8 个生肖，其中家列 4 个、野列 4 个。",
            "命中判断按特码生肖是否落入两列合并后的候选生肖集合处理，输出阶段保留 jia/ye 原始列结构。",
        ),
    ),
    "title_48": PredictionConfig(
        key="title_48",
        title="8肖中特",
        default_table="mode_payload_48",
        default_modes_id=48,
        labels=tuple(ZODIAC_ORDER),
        label_count=8,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_one_code,
        hit_checker=contains_hit,
        explanation=(
            "8肖中特按生肖组选处理，从 12 个生肖中选出 8 个生肖。",
            "输出为生肖加对应代表号码，便于前端复用“无错八肖”展示。",
        ),
    ),
    "9xzt": PredictionConfig(
        key="9xzt",
        title="9肖中特",
        default_table="mode_payload_49",
        default_modes_id=49,
        labels=tuple(ZODIAC_ORDER),
        label_count=9,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_csv,
        hit_checker=contains_hit,
        explanation=(
            "9肖中特从 12 个生肖中选择 9 个。",
            "特码生肖落入预测生肖则命中。",
        ),
    ),
    "yijuzhenyan": PredictionConfig(
        key="yijuzhenyan",
        title="一句真言",
        default_table="mode_payload_50",
        default_modes_id=50,
        labels=tuple(ZODIAC_ORDER),
        label_count=1,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=jiexi_content_from_row,
        content_parser=parse_zodiac_chars,
        content_formatter=format_text_pool_jiexi("预测一句真言", "一句真言"),
        hit_checker=contains_hit,
        explanation=(
            "一句真言属于文本历史映射玩法，不做固定语义推理。",
            "系统从 text_history_mappings 随机抽取历史真言文本及其当期对应的特码号码/生肖。",
        ),
    ),
    "4xiao8ma": PredictionConfig(
        key="4xiao8ma",
        title="4肖8码",
        default_table="mode_payload_51",
        default_modes_id=51,
        labels=tuple(ZODIAC_ORDER),
        label_count=4,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_two_codes,
        hit_checker=contains_hit,
        explanation=(
            "4肖8码选择 4 个生肖，并为每个生肖带 2 个代表号码。",
            "特码生肖落入预测生肖则命中；号码用于生成接口展示。",
        ),
    ),
    "title_197": PredictionConfig(
        key="title_197",
        title="三期4肖",
        default_table="mode_payload_197",
        default_modes_id=197,
        labels=tuple(ZODIAC_ORDER),
        label_count=4,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_all_codes,
        hit_checker=contains_hit,
        explanation=(
            "三期4肖按生肖组选处理，从 12 个生肖中选出 4 个生肖。",
            "开奖结果取特码生肖命中判断；输出保持为 `生肖|号码列表` 结构，和历史表内容一致。",
            "该模块直接对应 mode_payload_197 与前端 getSanqiXiao4new。",
        ),
    ),
    "sizixuanji": PredictionConfig(
        key="sizixuanji",
        title="四字玄机",
        default_table="mode_payload_52",
        default_modes_id=52,
        labels=tuple(ZODIAC_ORDER),
        label_count=1,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=jiexi_content_from_row,
        content_parser=parse_zodiac_chars,
        content_formatter=format_text_pool_jiexi("预测四字玄机", "四字玄机"),
        hit_checker=contains_hit,
        explanation=(
            "四字玄机属于文本历史映射玩法，不做固定语义推理。",
            "系统从 text_history_mappings 随机抽取历史四字文本及其当期对应的特码号码/生肖。",
        ),
    ),
    "pt1wei": PredictionConfig(
        key="pt1wei",
        title="平特1尾",
        default_table="mode_payload_54",
        default_modes_id=54,
        labels=tuple(TAIL_NUMBER_MAP.keys()),
        label_count=1,
        outcome_loader=special_tail_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_tail_groups,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("尾", tuple(TAIL_NUMBER_MAP.keys())),
        explanation=(
            "平特1尾选择 1 个尾数。",
            "特码尾数与预测尾数一致则命中。",
        ),
    ),
    "title_66": PredictionConfig(
        key="title_66",
        title="5尾中特",
        default_table="mode_payload_66",
        default_modes_id=66,
        labels=tuple(TAIL_NUMBER_MAP.keys()),
        label_count=5,
        outcome_loader=special_tail_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_tail_digit_content,
        content_formatter=format_tail_groups,
        hit_checker=contains_hit,
        labels_loader=lambda _conn: tuple(TAIL_NUMBER_MAP.keys()),
        explanation=(
            "5尾中特按尾数玩法处理，从 0-9 中选出 5 个尾数。",
            "特码尾数落入预测尾数组则命中。",
        ),
    ),
    "title_132": PredictionConfig(
        key="title_132",
        title="合数单双",
        default_table="mode_payload_132",
        default_modes_id=132,
        labels=("合单", "合双"),
        label_count=1,
        outcome_loader=special_combined_parity_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_literal_label_content,
        content_formatter=format_literal_label,
        hit_checker=contains_hit,
        explanation=(
            "合数单双按特码十位与个位之和的奇偶归类为合单/合双。",
            "例如 38 的合数为 11，因此归类为合单。",
        ),
    ),
    "title_143": PredictionConfig(
        key="title_143",
        title="一波中特",
        default_table="mode_payload_143",
        default_modes_id=143,
        labels=("红波", "蓝波", "绿波"),
        label_count=1,
        outcome_loader=special_wave_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_literal_label_content,
        content_formatter=format_literal_label,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("波色", ("红波", "蓝波", "绿波")),
        explanation=(
            "一波中特按特码波色单选处理，预测红波/蓝波/绿波中的 1 个标签。",
            "特码波色与预测标签一致则命中。",
        ),
    ),
    "title_198": PredictionConfig(
        key="title_198",
        title="逢买必中",
        default_table="mode_payload_198",
        default_modes_id=198,
        labels=("单数", "双数", "大数", "小数", "家禽", "野兽"),
        label_count=1,
        outcome_loader=special_fengmaibizhong_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_literal_label_content,
        content_formatter=format_literal_label,
        hit_checker=mixed_dimension_contains_hit,
        explanation=(
            "逢买必中属于混合分类单选玩法，候选标签覆盖单双、大小、家禽/野兽三类维度。",
            "开奖后以特码真实分类落点作为命中目标，预测阶段只输出 1 个候选标签。",
        ),
    ),
    "title_279": PredictionConfig(
        key="title_279",
        title="合数大小",
        default_table="mode_payload_279",
        default_modes_id=279,
        labels=("合数大", "合数小"),
        label_count=1,
        outcome_loader=special_combined_size_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_literal_label_content,
        content_formatter=format_literal_label,
        hit_checker=contains_hit,
        explanation=(
            "合数大小按特码十位与个位之和归类，7-13 为合数大，0-6 为合数小。",
            "例如 42 的合数为 6，因此归类为合数小。",
        ),
    ),
    "qianhou_texiao": PredictionConfig(
        key="qianhou_texiao",
        title="前后特肖",
        default_table="mode_payload_219",
        default_modes_id=219,
        labels=tuple(ZODIAC_ORDER),
        label_count=2,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=xiao_column_content_loader("xiao"),
        content_parser=parse_zodiac_content,
        content_formatter=format_content_xiao_columns("mode_payload_219", "xiao", "content"),
        hit_checker=contains_hit,
        explanation=(
            "前后特肖保留 `content+xiao` 结构，其中 xiao 为最终候选特肖。",
            "前端会直接读取 xiao 列展示两个特肖候选。",
        ),
    ),
    "title_74": PredictionConfig(
        key="title_74",
        title="必中7尾",
        default_table="mode_payload_74",
        default_modes_id=74,
        labels=tuple(TAIL_NUMBER_MAP.keys()),
        label_count=7,
        outcome_loader=special_tail_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_tail_digit_content,
        content_formatter=format_tail_groups,
        hit_checker=contains_hit,
        labels_loader=lambda _conn: tuple(TAIL_NUMBER_MAP.keys()),
        explanation=(
            "必中7尾按尾数玩法处理，从 0-9 中选出 7 个尾数。",
            "特码尾数落入预测尾数组则命中。",
        ),
    ),
    "pt1xiao": PredictionConfig(
        key="pt1xiao",
        title="平特1肖",
        default_table="mode_payload_56",
        default_modes_id=56,
        labels=tuple(ZODIAC_ORDER),
        label_count=1,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_csv,
        hit_checker=contains_hit,
        explanation=(
            "平特1肖选择 1 个生肖。",
            "按统一预测口径，特码生肖与预测生肖一致则命中。",
        ),
    ),
    "daxiao": PredictionConfig(
        key="daxiao",
        title="大小中特",
        default_table="mode_payload_57",
        default_modes_id=57,
        labels=("小", "大"),
        label_count=1,
        outcome_loader=special_size_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_size_groups,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("大小", ("小", "大")),
        explanation=(
            "大小中特按特码号码大小分为小、大，01-24 为小，25-49 为大。",
            "特码大小与预测标签一致则命中。",
        ),
    ),
    "dxztt1": PredictionConfig(
        key="dxztt1",
        title="大小中特带1头",
        default_table="mode_payload_108",
        default_modes_id=108,
        labels=("小", "大"),
        label_count=1,
        outcome_loader=special_size_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_size_groups,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("大小", ("小", "大")),
        explanation=(
            "大小中特带1头按特码号码大小分为小、大，01-24 为小，25-49 为大。",
            "同时根据特码十位数输出头数（0头~4头）。",
            "特码大小与预测标签一致则命中。",
        ),
    ),
    "jueshabanbo": PredictionConfig(
        key="jueshabanbo",
        title="绝杀半波（1个半波）",
        default_table="mode_payload_58",
        default_modes_id=58,
        labels=tuple(HALF_WAVE_NUMBER_MAP.keys()),
        label_count=1,
        outcome_loader=special_half_wave_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_half_wave_groups,
        hit_checker=excludes_hit,
        labels_loader=labels_from_fixed("波色单双", tuple(HALF_WAVE_NUMBER_MAP.keys())),
        explanation=(
            "绝杀半波选择 1 个半波作为排除项，例如 红单、蓝双。",
            "若特码半波没有落入预测半波，则本期按命中计算。",
        ),
    ),
    "dujiayoumo": PredictionConfig(
        key="dujiayoumo",
        title="独家幽默",
        default_table="mode_payload_59",
        default_modes_id=59,
        labels=tuple(ZODIAC_ORDER),
        label_count=1,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_humor_tail_groups,
        hit_checker=contains_hit,
        explanation=(
            "独家幽默属于文本历史映射玩法，不做固定语义推理。",
            "系统从 text_history_mappings 随机抽取历史幽默文本及其当期对应的特码号码/生肖。",
        ),
    ),
    "yqjs": PredictionConfig(
        key="yqjs",
        title="欲钱解特",
        default_table="mode_payload_62",
        default_modes_id=62,
        labels=tuple(ZODIAC_ORDER),
        label_count=1,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=title_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_juzi_title,
        hit_checker=contains_hit,
        explanation=(
            "欲钱解特属于文本历史映射玩法，不做固定语义推理。",
            "系统从 text_history_mappings 随机抽取历史 title 文本。",
        ),
    ),
    "brainteaser": PredictionConfig(
        key="brainteaser",
        title="脑筋急转弯",
        default_table="mode_payload_475",
        default_modes_id=475,
        labels=tuple(ZODIAC_ORDER),
        label_count=1,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_text_pool_jiexi("脑筋急转弯", "一句真言"),
        hit_checker=contains_hit,
        explanation=(
            "脑筋急转弯模块使用专用静态映射数据生成题面与答案，不走通用生肖文本池预测格式化。",
            "批量生成时由 prediction_generation.service 中的 mode_id=475 专用分支生成并落库。",
        ),
    ),
    "sxztu": PredictionConfig(
        key="sxztu",
        title="四不像中特图",
        default_table="mode_payload_474",
        default_modes_id=474,
        labels=tuple(ZODIAC_ORDER),
        label_count=1,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_text_pool_jiexi("四不像中特图", "一句真言"),
        hit_checker=contains_hit,
        explanation=(
            "四不像中特图模块沿用普通生肖预测内容，同时补充专用图片 image_url。",
            "批量生成时由 prediction_generation.service 中的 mode_id=474 专用分支负责图片合成和落库。",
        ),
    ),
    "pmtj_image": PredictionConfig(
        key="pmtj_image",
        title="跑马图解（带图）",
        default_table="mode_payload_476",
        default_modes_id=476,
        labels=tuple(ZODIAC_ORDER),
        label_count=7,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_zodiac_two_codes,
        hit_checker=contains_hit,
        explanation=(
            "跑马图解（带图）模块复用跑马图解的 7 肖 14 码预测结构，同时补充专用图片 image_url。",
            "批量生成时由 prediction_generation.service 中的 mode_id=476 专用分支负责图片合成和落库。",
        ),
    ),
    "tw_pmt_image": PredictionConfig(
        key="tw_pmt_image",
        title="台湾跑马图（带图）",
        default_table="mode_payload_478",
        default_modes_id=478,
        labels=tuple(ZODIAC_ORDER),
        label_count=7,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_zodiac_two_codes,
        hit_checker=contains_hit,
        explanation=(
            "台湾跑马图（带图）模块复用跑马图解的 7 肖 14 码预测结构，同时补充专用图片 image_url。",
            "批量生成时由 prediction_generation.service 中的 mode_id=478 专用分支负责图片合成和落库。",
        ),
    ),
    "9xiao12ma": PredictionConfig(
        key="9xiao12ma",
        title="9肖12码",
        default_table="mode_payload_60",
        default_modes_id=60,
        labels=tuple(ZODIAC_ORDER),
        label_count=9,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=xiao_code_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_9x12,
        hit_checker=contains_hit,
        explanation=(
            "9肖12码使用 xiao/code 两列。",
            "脚本预测 9 个生肖并从固定生肖号码映射中生成 12 个号码；特码生肖落入预测生肖则命中。",
        ),
    ),
    "siji3": PredictionConfig(
        key="siji3",
        title="四季生肖（4选3）",
        default_table="mode_payload_61",
        default_modes_id=61,
        labels=("春肖", "夏肖", "秋肖", "冬肖"),
        label_count=3,
        outcome_loader=make_pipe_category_outcome("mode_payload_61", ("春肖", "夏肖", "秋肖", "冬肖")),
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_zodiac_groups("mode_payload_61", ("春肖", "夏肖", "秋肖", "冬肖")),
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("四季肖", ("春肖", "夏肖", "秋肖", "冬肖")),
        explanation=(
            "四季生肖（4选3）把生肖分为春、夏、秋、冬四类，每次选择三类。",
            "特码生肖所属季节落入预测季节则命中。",
        ),
    ),
}

# ---------------------------------------------------------------------------
# 站点别名 — 前端页面和测试可能使用与 PREDICTION_CONFIGS 不同的 key 名。
# 这些别名不创建新机制，仅将已存在的 PredictionConfig 对象注册到其他 key。
# ---------------------------------------------------------------------------
_PREDICTION_CONFIG_ALIASES: dict[str, str] = {
    # twcf888 / twjinniu / twcaibawang 常用别名
    "qqsh":              "qinqi",           # 琴棋书画 (mode 26)
    "title_38":          "shuangbo",        # 双波中特 (mode 38)
    "title_45":          "heibai3xiao",     # 黑白中特 (mode 45)
    "sanxiaozhongte":    "3zxt",            # 三肖中特 (mode 69)
    "4tou":              "sitouzhongte",    # 四头中特 (mode 483)
}
for _alias_key, _target_key in _PREDICTION_CONFIG_ALIASES.items():
    if _target_key in PREDICTION_CONFIGS and _alias_key not in PREDICTION_CONFIGS:
        PREDICTION_CONFIGS[_alias_key] = PREDICTION_CONFIGS[_target_key]


def _extract_first_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text)
    return int(match.group(1)) if match else None


CHINESE_NUMBER_MAP = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def _extract_count(pattern: str, text: str) -> int | None:
    """提取阿拉伯数字或常见中文数字，兼容 `绝杀一肖`、`三期3肖` 等 title。"""
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group(1)
    if value.isdigit():
        return int(value)
    return CHINESE_NUMBER_MAP.get(value)


def _dynamic_key(modes_id: int) -> str:
    """动态机制使用 modes_id 生成稳定 key，避免中文 title 变化导致调用入口失效。"""
    return f"title_{modes_id}"


def _make_number_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建号码类玩法。

    适用 title 示例：10码、12码、36码、杀10码、平五不中。命中目标统一为
    res_code 最后一位特码号码；杀号/不中类使用排除命中规则。
    """
    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(f"{number:02d}" for number in range(1, 50)),
        label_count=label_count,
        outcome_loader=special_number_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_number_content,
        content_formatter=format_24_numbers,
        hit_checker=excludes_hit if exclude else contains_hit,
        explanation=(
            f"{title} 按号码类玩法处理，从 01-49 中选择 {label_count} 个号码。",
            "开奖结果 res_code 最后一位按特码号码处理；特码号码落入预测号码则为命中。",
            "若 title 带有“杀”或“不中”语义，则反向计算：特码号码没有落入预测号码才算命中。",
        ),
    )


def _make_zodiac_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建生肖类玩法。

    适用 title 示例：4肖中特、8肖中特、平特3肖、杀2肖。命中目标优先取
    res_sx 最后一项；缺失时通过 fixed_data 的“生肖”映射由特码号码推导。
    """
    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(ZODIAC_ORDER),
        label_count=label_count,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=default_content_from_row,
        content_parser=parse_zodiac_content,
        content_formatter=format_zodiac_csv,
        hit_checker=excludes_hit if exclude else contains_hit,
        explanation=(
            f"{title} 按生肖类玩法处理，从 12 个生肖中选择 {label_count} 个生肖。",
            "开奖结果 res_code 最后一位按特码处理，特码生肖优先取 res_sx 最后一项。",
            "若 title 带有“杀”或“绝杀”语义，则反向计算：特码生肖没有落入预测生肖才算命中。",
        ),
    )


def _make_tail_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建尾数类玩法。

    适用 title 示例：必中6尾、5尾中特、平特2尾、杀2尾。尾数标签和值列表统一
    从 fixed_data 的“尾”映射读取，输出沿用 `尾|号码列表` 结构。
    """
    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(TAIL_NUMBER_MAP.keys()),
        label_count=label_count,
        outcome_loader=special_tail_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_tail_groups,
        hit_checker=excludes_hit if exclude else contains_hit,
        labels_loader=labels_from_fixed("尾", tuple(TAIL_NUMBER_MAP.keys())),
        explanation=(
            f"{title} 按尾数类玩法处理，从 0尾-9尾中选择 {label_count} 个尾数。",
            "开奖结果 res_code 最后一位按特码处理，特码号码个位数即为命中目标。",
            "若 title 带有“杀”或“绝杀”语义，则反向计算：特码尾数没有落入预测尾数才算命中。",
        ),
    )


def _make_head_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建头数类玩法，头数和值列表统一从 fixed_data 的“头”映射读取。"""
    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(HEAD_NUMBER_MAP.keys()),
        label_count=label_count,
        outcome_loader=special_head_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_head_groups,
        hit_checker=excludes_hit if exclude else contains_hit,
        labels_loader=labels_from_fixed("头", tuple(HEAD_NUMBER_MAP.keys())),
        explanation=(
            f"{title} 按头数类玩法处理，从 0头-4头中选择 {label_count} 个头数。",
            "开奖结果 res_code 最后一位按特码处理，特码号码十位归属即为命中目标。",
            "若 title 带有“杀”或“绝杀”语义，则反向计算：特码头数没有落入预测头数才算命中。",
        ),
    )


def _make_wave_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建波色类玩法，命中目标为特码波色。"""
    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=("红波", "蓝波", "绿波"),
        label_count=label_count,
        outcome_loader=special_wave_from_row,
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_wave_csv,
        hit_checker=excludes_hit if exclude else contains_hit,
        labels_loader=labels_from_fixed("波色", ("红波", "蓝波", "绿波")),
        explanation=(
            f"{title} 按波色类玩法处理，从红波、蓝波、绿波中选择 {label_count} 个。",
            "开奖结果 res_code 最后一位按特码处理，特码波色落入预测波色则为命中。",
            "若 title 带有“杀”或“绝杀”语义，则反向计算：特码波色没有落入预测波色才算命中。",
        ),
    )


def _make_text_column_zodiac_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    column: str,
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建文本列直接提取生肖的玩法。
    适用于 `成语平特`、`谜语平特` 等字段本身含生肖字的表。文本只作为载体，
    回测和预测都按从文本中提取出的生肖集合计算。
    """

    def loader(row: sqlite3.Row) -> str:
        return str(row_get(row, column, "") or "")

    def formatter(labels: tuple[str, ...], _: sqlite3.Connection) -> dict[str, str]:
        return {column: "".join(labels)}

    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(ZODIAC_ORDER),
        label_count=label_count,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=loader,
        content_parser=parse_zodiac_chars,
        content_formatter=formatter,
        hit_checker=excludes_hit if exclude else contains_hit,
        explanation=(
            f"{title} 从 `{column}` 文本字段中提取生肖作为候选集合。",
            "回测时特码生肖落入文本提取出的生肖集合即为命中；生成时输出可审计的生肖占位文本。",
            "该机制只适用于文本中明确出现生肖字的历史表。",
        ),
    )


def _make_text_column_tail_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    column: str,
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建文本列直接提取尾数的玩法，例如 `成语平特尾`。"""

    def loader(row: sqlite3.Row) -> str:
        return str(row_get(row, column, "") or "")

    def formatter(labels: tuple[str, ...], _: sqlite3.Connection) -> dict[str, str]:
        return {column: "".join(label.removesuffix("尾") for label in labels)}

    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(TAIL_NUMBER_MAP.keys()),
        label_count=label_count,
        outcome_loader=special_tail_from_row,
        content_loader=loader,
        content_parser=parse_tail_digit_content,
        content_formatter=formatter,
        hit_checker=excludes_hit if exclude else contains_hit,
        labels_loader=labels_from_fixed("尾", tuple(TAIL_NUMBER_MAP.keys())),
        explanation=(
            f"{title} 从 `{column}` 文本字段中提取数字尾数作为候选集合。",
            "回测时特码尾数落入文本提取出的尾数集合即为命中；生成时输出可审计的尾数占位文本。",
        ),
    )


def _make_pipe_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建结构化 `标签|值列表` 玩法。

    这类玩法的标签来自历史 content 左侧，值可能是生肖、号码、波色或其他固定分类。
    预测时不新增业务模块，而是复用同一个映射还原逻辑：特码号码或特码生肖归属到
    某个标签，若该标签被选中则命中。
    """
    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=(),
        label_count=label_count,
        outcome_loader=make_dynamic_pipe_outcome(table_name, ()),
        content_loader=default_content_from_row,
        content_parser=parse_pipe_label_content,
        content_formatter=format_dynamic_pipe_groups(table_name),
        hit_checker=excludes_hit if exclude else contains_hit,
        labels_loader=labels_from_history_pipe(table_name),
        explanation=(
            f"{title} 按结构化标签映射玩法处理，标签和值列表从本地历史 content 自动提取。",
            "content 需符合 `标签|值列表` 结构；脚本将特码号码或特码生肖归属到对应标签。",
            "该配置由 title 自动生成，复用通用映射模块，避免为相同结构重复编写机制。",
        ),
    )


# _sample_content, COMMON_PAYLOAD_COLUMNS, _table_column_list, _table_columns,
# _business_columns, _sample_column_value 已迁移至 predict._db_helpers


def _infer_group_widths(
    conn: sqlite3.Connection,
    table_name: str,
    columns: tuple[str, ...],
    value_parser,
) -> tuple[int, ...] | None:
    """根据历史样本推导每个业务列应承载多少个标签。
    第二阶段生成机制时，输出需要还原成多列结构，所以不能只知道总标签数，
    还必须知道每列的分组宽度。这里从历史非空样本中取最常见宽度，避免个别异常
    记录把整个机制的输出形态带偏。
    """

    widths: list[int] = []
    for column in columns:
        counter: Counter[int] = Counter()
        for raw_value in predict_repository.load_limited_non_empty_column_values(conn, table_name, column, limit=50):
            parsed_values = tuple(value_parser(str(raw_value or "")))
            if parsed_values:
                counter[len(parsed_values)] += 1
        if not counter:
            return None
        widths.append(counter.most_common(1)[0][0])
    return tuple(widths)


def _infer_codes_per_label(
    conn: sqlite3.Connection,
    table_name: str,
    columns: tuple[str, ...],
) -> int:
    """推导单个生肖在原始列里携带几个号码。
    `3组3肖6码` 这类表的列值不是纯生肖列表，而是 `生肖|号码` 数组。预测时仍按
    生肖命中回测，但输出需要补回每个生肖的号码个数，这里根据历史样本自动推导。
    """

    counter: Counter[int] = Counter()
    for column in columns:
        for raw_value in predict_repository.load_limited_non_empty_column_values(conn, table_name, column, limit=50):
            raw_value = str(raw_value or "")
            if "|" not in raw_value:
                continue
            zodiac_values = parse_zodiac_content(raw_value)
            number_values = parse_number_content(raw_value)
            if zodiac_values and number_values and len(number_values) % len(zodiac_values) == 0:
                counter[len(number_values) // len(zodiac_values)] += 1
    return counter.most_common(1)[0][0] if counter else 0


def _ordered_labels(values: list[str], preferred_order: tuple[str, ...]) -> tuple[str, ...]:
    """按固定业务顺序优先排序，其余值按首次出现顺序追加。"""
    preferred = [label for label in preferred_order if label in values]
    extras = [label for label in values if label not in preferred]
    return tuple(preferred + extras)


def _infer_group_selection_groups(
    conn: sqlite3.Connection,
    table_name: str,
    columns: tuple[str, ...],
    value_parser,
    preferred_order: tuple[str, ...],
) -> tuple[tuple[str, ...], ...]:
    """推导每个业务列自己的候选域。
    家/野、男/女、单/双 这类玩法不是“总池任意切分”，而是每一列都有自己的业务域。
    这里从历史列值中提取每列出现过的标签集合，并保持业务顺序，用于后续按列限域选取。
    """

    groups: list[tuple[str, ...]] = []
    for column in columns:
        seen: list[str] = []
        for raw_value in predict_repository.load_limited_non_empty_column_values(conn, table_name, column, limit=200):
            for value in value_parser(str(raw_value or "")):
                if value not in seen:
                    seen.append(value)
        groups.append(_ordered_labels(seen, preferred_order) or preferred_order)
    return tuple(groups)


# _is_first_stage_supported_table 已迁移至 predict._db_helpers


def _make_grouped_zodiac_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    columns: tuple[str, ...],
    widths: tuple[int, ...],
    selection_groups: tuple[tuple[str, ...], ...],
    codes_per_label: int = 0,
    exclude: bool = False,
) -> PredictionConfig:
    """构建多列生肖玩法。
    适用于 `家野各3肖`、`男女各4肖`、`3组3肖`、`3组3肖6码`、`2+1肖` 这类玩法。
    历史表虽然拆成多列，但命中口径仍是“特码生肖是否落入所有预测生肖集合”，
    因此回测时统一按生肖集合处理，输出时再恢复成原始多列结构。
    """

    label_count = sum(widths)
    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(ZODIAC_ORDER),
        label_count=label_count,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=parsed_columns_content_loader(columns, parse_zodiac_content),
        content_parser=parse_zodiac_content,
        content_formatter=format_split_zodiac_columns(columns, widths, codes_per_label),
        hit_checker=excludes_hit if exclude else contains_hit,
        selection_groups=selection_groups,
        selection_widths=widths,
        explanation=(
            f"{title} 属于多列生肖分组玩法，历史数据拆在 {', '.join(columns)} 中。",
            "回测和预测都会保留每列自己的候选域与配额，使用特码生肖是否落入任一已选生肖判断命中。",
            "输出阶段再按历史列宽恢复为原始字段结构，若历史列自带 `生肖|号码`，则号码从 fixed_data 的生肖映射生成。",
        ),
    )


def _make_grouped_tail_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    columns: tuple[str, ...],
    widths: tuple[int, ...],
    selection_groups: tuple[tuple[str, ...], ...],
    exclude: bool = False,
) -> PredictionConfig:
    """构建多列尾数玩法，例如 `单双各3尾`。"""

    label_count = sum(widths)
    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(TAIL_NUMBER_MAP.keys()),
        label_count=label_count,
        outcome_loader=special_tail_from_row,
        content_loader=parsed_columns_content_loader(columns, parse_tail_digit_content),
        content_parser=parse_tail_digit_content,
        content_formatter=format_split_tail_columns(columns, widths),
        hit_checker=excludes_hit if exclude else contains_hit,
        labels_loader=labels_from_fixed("尾", tuple(TAIL_NUMBER_MAP.keys())),
        selection_groups=selection_groups,
        selection_widths=widths,
        explanation=(
            f"{title} 属于多列尾数玩法，历史数据拆在 {', '.join(columns)} 中。",
            "回测和预测都会保留每列自己的候选域与配额，再用特码尾数判断命中。",
            "输出阶段按历史列宽回填为纯数字尾数，保持与原始表结构一致。",
        ),
    )


def _make_grouped_number_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    columns: tuple[str, ...],
    widths: tuple[int, ...],
    selection_groups: tuple[tuple[str, ...], ...],
    exclude: bool = False,
) -> PredictionConfig:
    """构建多列号码玩法，例如 `单双各16码`。"""

    label_count = sum(widths)
    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(f"{number:02d}" for number in range(1, 50)),
        label_count=label_count,
        outcome_loader=special_number_from_row,
        content_loader=parsed_columns_content_loader(columns, parse_number_content),
        content_parser=parse_number_content,
        content_formatter=format_split_number_columns(columns, widths),
        hit_checker=excludes_hit if exclude else contains_hit,
        selection_groups=selection_groups,
        selection_widths=widths,
        explanation=(
            f"{title} 属于多列号码玩法，历史数据拆在 {', '.join(columns)} 中。",
            "回测和预测都会保留每列自己的候选域与配额，使用特码号码是否落入任一已选号段判断命中。",
            "输出阶段按历史列宽拆回原始多列结构，避免重复构建专用模块。",
        ),
    )


def _make_xiao_code_columns_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    xiao_column: str,
    code_column: str,
    zodiac_count: int,
    code_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建 `xiao/code` 联动玩法。
    此类玩法的实质命中目标是生肖，`code` 只是该组生肖对应的号码展开结果，因此
    回测只按 `xiao` 列中的生肖集合统计命中率，输出时再同步生成号码列。
    """

    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(ZODIAC_ORDER),
        label_count=zodiac_count,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=parsed_columns_content_loader((xiao_column,), parse_zodiac_content),
        content_parser=parse_zodiac_content,
        content_formatter=format_xiao_code_columns(xiao_column, code_column, code_count),
        hit_checker=excludes_hit if exclude else contains_hit,
        explanation=(
            f"{title} 使用 `{xiao_column}/{code_column}` 双字段结构。",
            "回测时只按生肖集合统计命中，因为历史 `code` 列本质上是生肖集合展开后的号码表现形式。",
            "预测输出时先选生肖，再从 fixed_data 的生肖号码映射生成对应数量的号码，保持与历史表一致。",
        ),
    )


def _make_text_column_wave_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    column: str,
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建文本列直接提取波色的玩法，例如 `七字波色`。"""

    def loader(row: sqlite3.Row) -> str:
        return str(row_get(row, column, "") or "")

    def formatter(labels: tuple[str, ...], _: sqlite3.Connection) -> dict[str, str]:
        return {column: "".join(labels)}

    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=("红波", "蓝波", "绿波"),
        label_count=label_count,
        outcome_loader=special_wave_from_row,
        content_loader=loader,
        content_parser=parse_wave_chars,
        content_formatter=formatter,
        hit_checker=excludes_hit if exclude else contains_hit,
        labels_loader=labels_from_fixed("波色", ("红波", "蓝波", "绿波")),
        explanation=(
            f"{title} 从 `{column}` 文本字段中提取红/蓝/绿波色作为候选集合。",
            "回测时特码波色落入文本提取出的波色集合即为命中；生成时输出可审计的波色占位文本。",
        ),
    )




def _make_window_config(
    base_config: PredictionConfig,
) -> PredictionConfig:
    """把普通 content 玩法包装为连期表输出结构。"""
    return PredictionConfig(
        key=base_config.key,
        title=base_config.title,
        default_table=base_config.default_table,
        default_modes_id=base_config.default_modes_id,
        labels=base_config.labels,
        label_count=base_config.label_count,
        outcome_loader=base_config.outcome_loader,
        content_loader=base_config.content_loader,
        content_parser=base_config.content_parser,
        content_formatter=format_window_content(base_config.content_formatter, base_config.default_table),
        hit_checker=base_config.hit_checker,
        explanation=(
            *base_config.explanation,
            "该表包含 start/end 连期窗口；历史数据已按窗口内期开奖行展开，回测按逐期开奖样本计算。",
        ),
        labels_loader=base_config.labels_loader,
        selection_groups=base_config.selection_groups,
        selection_widths=base_config.selection_widths,
    )


def _make_source_column_zodiac_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    source_column: str,
    output_columns: tuple[str, ...],
    label_count: int,
    code_column: str | None = None,
    code_count: int = 0,
    exclude: bool = False,
) -> PredictionConfig:
    """构建以某个生肖列为命中来源的复合表。
    很多文案表同时有 title/content/jiexi/xiao/code 多个字段，但稳定命中字段通常是
    `xiao`、`texiao`、`shengxiao` 等生肖列。此工厂只把明确的生肖列纳入回测，
    其余文本列输出审计占位，避免重复构建各类文案模块。
    """

    def loader(row: sqlite3.Row) -> str:
        return str(row_get(row, source_column, "") or "")

    def formatter(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, str]:
        result: dict[str, str] = {}
        for column in output_columns:
            if column in {"title", "content", "jiexi", "remark", "jiexi1", "jiexi2"}:
                result[column] = f"{title}:{','.join(labels)}"
            elif column == source_column:
                result[column] = ",".join(labels)
            elif column == code_column:
                continue
            else:
                result[column] = None
        if code_column:
            result[code_column] = format_xiao_code_columns(source_column, code_column, code_count)(labels, conn)[code_column]
        return result

    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(ZODIAC_ORDER),
        label_count=label_count,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=loader,
        content_parser=parse_zodiac_content,
        content_formatter=formatter,
        hit_checker=excludes_hit if exclude else contains_hit,
        explanation=(
            f"{title} 使用 `{source_column}` 作为稳定生肖候选字段。",
            "同表的文案字段只作为展示载体，回测命中只按该生肖列计算，避免把文案解析误当作独立命中条件。",
            "若表中存在号码字段，预测时从 fixed_data 的生肖号码映射同步生成对应号码。",
        ),
    )


def _make_source_column_number_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    source_column: str,
    output_columns: tuple[str, ...],
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建以某个号码列为命中来源的复合表。"""

    def loader(row: sqlite3.Row) -> str:
        return str(row_get(row, source_column, "") or "")

    def formatter(labels: tuple[str, ...], _: sqlite3.Connection) -> dict[str, str]:
        result: dict[str, str] = {}
        for column in output_columns:
            if column in {"title", "content", "jiexi", "remark"}:
                result[column] = f"{title}:{','.join(labels)}"
            elif column == source_column:
                result[column] = ",".join(labels)
            else:
                result[column] = None
        return result

    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(f"{number:02d}" for number in range(1, 50)),
        label_count=label_count,
        outcome_loader=special_number_from_row,
        content_loader=loader,
        content_parser=parse_number_content,
        content_formatter=formatter,
        hit_checker=excludes_hit if exclude else contains_hit,
        explanation=(
            f"{title} 使用 `{source_column}` 作为稳定号码候选字段。",
            "回测命中只按该号码列计算；同表其他文案或辅助字段仅作为输出占位。",
        ),
    )


def _make_source_column_tail_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    source_column: str,
    output_columns: tuple[str, ...],
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建以某个尾数列为命中来源的复合表。"""

    def loader(row: sqlite3.Row) -> str:
        return str(row_get(row, source_column, "") or "")

    def formatter(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, str]:
        result: dict[str, str] = {}
        for column in output_columns:
            if column in {"title", "content", "jiexi", "remark"}:
                result[column] = f"{title}:{','.join(labels)}"
            elif column == source_column:
                result[column] = json.dumps(format_tail_groups(labels, conn), ensure_ascii=False)
            else:
                result[column] = None
        return result

    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(TAIL_NUMBER_MAP.keys()),
        label_count=label_count,
        outcome_loader=special_tail_from_row,
        content_loader=loader,
        content_parser=parse_tail_digit_content,
        content_formatter=formatter,
        hit_checker=excludes_hit if exclude else contains_hit,
        labels_loader=labels_from_fixed("尾", tuple(TAIL_NUMBER_MAP.keys())),
        explanation=(
            f"{title} 使用 `{source_column}` 作为稳定尾数候选字段。",
            "回测命中只按该尾数字段计算；同表其他文案或辅助字段仅作为输出占位。",
        ),
    )


def _make_source_column_head_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    source_column: str,
    output_columns: tuple[str, ...],
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建以某个头数字段为命中来源的复合表。"""

    def loader(row: sqlite3.Row) -> str:
        return str(row_get(row, source_column, "") or "")

    def formatter(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, str]:
        result = {column: None for column in output_columns}
        result[source_column] = json.dumps(format_head_groups(labels, conn), ensure_ascii=False)
        return result

    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(HEAD_NUMBER_MAP.keys()),
        label_count=label_count,
        outcome_loader=special_head_from_row,
        content_loader=loader,
        content_parser=parse_tail_digit_content,
        content_formatter=formatter,
        hit_checker=excludes_hit if exclude else contains_hit,
        labels_loader=labels_from_fixed("头", tuple(HEAD_NUMBER_MAP.keys())),
        explanation=(
            f"{title} 使用 `{source_column}` 作为稳定头数候选字段。",
            "回测命中只按该头数字段计算；同表其他文案或辅助字段仅作为输出占位。",
        ),
    )


def _make_source_column_element_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    source_column: str,
    output_columns: tuple[str, ...],
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建以某个五行字段为命中来源的复合表。"""

    def loader(row: sqlite3.Row) -> str:
        return str(row_get(row, source_column, "") or "")

    def formatter(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, str]:
        result = {column: None for column in output_columns}
        result[source_column] = json.dumps(format_element_groups(labels, conn), ensure_ascii=False)
        return result

    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(ELEMENT_ORDER),
        label_count=label_count,
        outcome_loader=special_element_from_row,
        content_loader=loader,
        content_parser=parse_pipe_label_content,
        content_formatter=formatter,
        hit_checker=excludes_hit if exclude else contains_hit,
        labels_loader=labels_from_fixed("五行肖", tuple(ELEMENT_ORDER)),
        explanation=(
            f"{title} 使用 `{source_column}` 作为稳定五行候选字段。",
            "回测命中只按该五行字段计算；同表其他文案或辅助字段仅作为输出占位。",
        ),
    )


def _labels_from_column(table_name: str, label_column: str):
    def loader(conn: sqlite3.Connection) -> tuple[str, ...]:
        if not table_exists(conn, table_name):
            return ()
        labels: list[str] = []
        for raw_value in predict_repository.load_non_empty_column_values(conn, table_name, label_column):
            for label in parse_pipe_label_content(str(raw_value or "")):
                if label and label not in labels:
                    labels.append(label)
        return tuple(labels)

    return loader


def _build_label_value_map(
    conn: sqlite3.Connection,
    table_name: str,
    label_column: str,
    value_column: str | None,
    labels: tuple[str, ...],
) -> dict[str, tuple[str, ...]]:
    result: dict[str, set[str]] = {label: set() for label in labels}
    if not table_exists(conn, table_name):
        return {label: () for label in labels}

    selected_columns = [label_column] if value_column is None else [label_column, value_column]
    rows = predict_repository.load_rows_with_non_empty_label_column(
        conn,
        table_name,
        label_column=label_column,
        selected_columns=tuple(selected_columns),
    )
    for row in rows:
        if value_column is None:
            for item in parse_json_or_plain_content(str(row[label_column] or "")):
                if "|" not in item:
                    continue
                label, raw_values = item.split("|", 1)
                label = label.strip()
                if label not in result:
                    continue
                result[label].update(value.strip() for value in raw_values.split(",") if value.strip())
        else:
            label = str(row[label_column] or "").strip()
            if label not in result:
                continue
            raw_value = str(row[value_column] or "")
            values = parse_number_content(raw_value) or parse_zodiac_content(raw_value) or parse_tail_digit_content(raw_value)
            result[label].update(values)
    return {label: tuple(sorted(values)) for label, values in result.items()}


def _make_label_value_column_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    label_column: str,
    value_column: str | None,
    label_count: int,
    exclude: bool = False,
) -> PredictionConfig:
    """构建 `标签 -> 值列表` 还原玩法。
    适用于 `title/content`、`jiexi/content`、以及单列 `标签|值列表` 的历史表。
    命中时先把特码号码或生肖归属到历史标签，再判断该标签是否被选中。
    """

    def outcome_loader(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
        labels = _labels_from_column(table_name, label_column)(conn)
        mapping = _build_label_value_map(conn, table_name, label_column, value_column, labels)
        special_code = special_code_from_res_code(row["res_code"] or "")
        special_zodiac = special_zodiac_from_number_map(row, conn)
        return (
            category_outcome_from_map(special_code, mapping, labels)
            or category_outcome_from_map(special_zodiac, mapping, labels)
        )

    def content_loader(row: sqlite3.Row) -> str:
        return str(row_get(row, label_column, "") or "")

    def formatter(selected: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, Any]:
        labels = _labels_from_column(table_name, label_column)(conn)
        mapping = _build_label_value_map(conn, table_name, label_column, value_column, labels)
        if value_column is None:
            return {
                label_column: json.dumps(
                    [f"{label}|{','.join(mapping.get(label, ())) }" for label in selected],
                    ensure_ascii=False,
                )
            }
        return {
            label_column: ",".join(selected),
            value_column: ",".join(value for label in selected for value in mapping.get(label, ())),
        }

    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=(),
        label_count=label_count,
        outcome_loader=outcome_loader,
        content_loader=content_loader,
        content_parser=parse_pipe_label_content,
        content_formatter=formatter,
        hit_checker=excludes_hit if exclude else contains_hit,
        labels_loader=_labels_from_column(table_name, label_column),
        explanation=(
            f"{title} 使用 `{label_column}` 和 `{value_column or label_column}` 还原标签映射。",
            "回测时先用历史值列表判断特码号码或生肖归属标签，再判断预测标签是否命中。",
        ),
    )


def _make_content_xiao_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    xiao_width: int,
    exclude: bool = False,
    content_column: str = "content",
) -> PredictionConfig:
    """构建 `content+xiao` 玩法。
    历史 content 保存分类说明，例如 `地肖|蛇,羊,...`；xiao 保存最终候选生肖。
    从样本看二者互斥，因此命中回测只按 xiao 候选生肖统计，content 由历史分类池回填。
    content_column 允许指定实际列名（如 title），兼容表结构差异。
    """

    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(ZODIAC_ORDER),
        label_count=xiao_width,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=xiao_or_content_content_loader("xiao", content_column),
        content_parser=parse_zodiac_content,
        content_formatter=format_content_xiao_columns(table_name, "xiao", content_column),
        hit_checker=excludes_hit if exclude else contains_hit,
        explanation=(
            f"{title} 使用 `content+xiao` 双字段结构。",
            "content 保存分类与分类内生肖列表，xiao 保存最终候选生肖；回测命中只按 xiao 列计算。",
            "生成输出时从历史 content 分类池选择一个与预测生肖不重叠的分类，再回填 xiao 字段。",
        ),
    )


def _is_jyxiao2_title(title: str, modes_id: int) -> bool:
    return int(modes_id or 0) == 251 or "家野两肖" in str(title or "")


def _make_mixed_xiao_tail_config(
    key: str,
    title: str,
    table_name: str,
    modes_id: int,
    xiao_width: int,
    tail_width: int,
    xiao_codes_per_label: int = 0,
    exclude: bool = False,
) -> PredictionConfig:
    """构建 `xiao+wei` 混合玩法。
    命中目标拆成两个原子：特码生肖、特码尾数。常规玩法任一原子落入预测集合即命中；
    杀类玩法则要求两个原子都未落入预测集合。
    """

    zodiac_labels = tuple(f"肖:{label}" for label in ZODIAC_ORDER)
    tail_labels = tuple(f"尾:{label}" for label in TAIL_NUMBER_MAP)
    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=zodiac_labels + tail_labels,
        label_count=xiao_width + tail_width,
        outcome_loader=mixed_xiao_tail_outcome_from_row,
        content_loader=mixed_xiao_tail_content_loader("xiao", "wei"),
        content_parser=parse_mixed_dimension_content,
        content_formatter=format_mixed_xiao_tail_columns(
            xiao_width,
            tail_width,
            xiao_codes_per_label,
            "xiao",
            "wei",
        ),
        hit_checker=mixed_dimension_excludes_hit if exclude else mixed_dimension_contains_hit,
        selection_groups=(zodiac_labels, tail_labels),
        selection_widths=(xiao_width, tail_width),
        explanation=(
            f"{title} 使用 `xiao+wei` 混合字段结构。",
            "回测时把真实开奖结果拆为特码生肖和特码尾数两个命中原子，预测也分别按生肖、尾数配额选取。",
            "输出阶段恢复为历史表的 xiao 与 wei 字段；若历史 xiao 自带号码，则从 fixed_data 生成生肖号码。",
        ),
    )


def _classify_second_stage_config(
    conn: ConnectionAdapter,
    title: str,
    table_name: str,
    modes_id: int,
    columns: tuple[str, ...],
) -> PredictionConfig | None:
    """第二阶段自动化：处理命中规则清晰的多字段玩法。
    只覆盖以下几类：
    - 多列生肖分组：`jia/ye`、`nan/nv`、`zu1/zu2/zu3`、`xiao1/xiao2`
    - `xiao/code` 联动输出
    - 多列尾数或号码分组：`dan/shuang`
    其余混合维度玩法仍暂缓，避免在业务口径未确认时自我推测。
    """

    key = _dynamic_key(modes_id)
    exclude = any(word in title for word in ("杀", "绝杀", "不中"))
    all_columns = _table_columns(conn, table_name)
    preferred_text_column = _text_history_preferred_column(conn, modes_id)

    # 兼容 title 作为 content 的替代表（如 mode_payload_251）
    _content_col = None
    if "content" in all_columns:
        _content_col = "content"
    elif "title" in all_columns:
        _content_col = "title"

    if _is_jyxiao2_title(title, modes_id) and _content_col:
        # 优先检测 xiao+code 双列模式：从 xiao 列推断生肖数量，从 code 列推断号码数量
        if "xiao" in columns and "code" in columns:
            xiao_sample = _sample_column_value(conn, table_name, "xiao")
            code_sample = _sample_column_value(conn, table_name, "code")
            zodiac_values = parse_zodiac_content(xiao_sample)
            code_values = parse_number_content(code_sample)
            if (
                zodiac_values
                and code_values
                and all(label in ZODIAC_ORDER for label in zodiac_values)
            ):
                return _make_xiao_code_columns_config(
                    key,
                    title,
                    table_name,
                    modes_id,
                    "xiao",
                    "code",
                    len(zodiac_values),
                    len(code_values),
                    exclude,
                )
        # 回退：content/title 管道标签模式（家|… / 野|… 等）
        content_sample = _sample_column_value(conn, table_name, _content_col)
        inferred_labels = parse_pipe_label_content(content_sample)
        if inferred_labels:
            return _make_content_xiao_config(
                key,
                title,
                table_name,
                modes_id,
                len(tuple(dict.fromkeys(inferred_labels))),
                exclude,
                content_column=_content_col,
            )

    if preferred_text_column and _is_text_history_title(title):
        return _make_text_history_mapping_config(
            key,
            title,
            table_name,
            modes_id,
            preferred_text_column,
        )

    if "start" in columns and "end" in columns and "content" in _table_columns(conn, table_name):
        sample_content = _sample_content(conn, table_name)
        base_config = _classify_title_config(title, table_name, modes_id, sample_content)
        if base_config is not None:
            return _make_window_config(base_config)

    if "content" in all_columns and "jiexi" in columns:
        sample_value = _sample_column_value(conn, table_name, "content")
        if parse_number_content(sample_value) or parse_zodiac_content(sample_value):
            return _make_label_value_column_config(
                key,
                title,
                table_name,
                modes_id,
                "jiexi",
                "content",
                1,
                exclude,
            )

    if "content" in all_columns and "title" in columns:
        sample_value = _sample_column_value(conn, table_name, "content")
        if parse_number_content(sample_value) or parse_zodiac_content(sample_value):
            return _make_label_value_column_config(
                key,
                title,
                table_name,
                modes_id,
                "title",
                "content",
                1,
                exclude,
            )

    for pipe_column in ("xiao", "ds", "dx", "bo", "banbo"):
        if pipe_column not in columns:
            continue
        sample_value = _sample_column_value(conn, table_name, pipe_column)
        if "|" in sample_value:
            return _make_label_value_column_config(
                key,
                title,
                table_name,
                modes_id,
                pipe_column,
                None,
                max(1, len(parse_pipe_label_content(sample_value))),
                exclude,
            )

    if columns in {
        ("jia", "ye"),
        ("nan", "nv"),
        ("xiao1", "xiao2"),
        ("xiao_1", "xiao_2"),
        ("zu1", "zu2", "zu3"),
    }:
        widths = _infer_group_widths(conn, table_name, columns, parse_zodiac_content)
        if widths:
            selection_groups = _infer_group_selection_groups(
                conn,
                table_name,
                columns,
                parse_zodiac_content,
                tuple(ZODIAC_ORDER),
            )
            return _make_grouped_zodiac_config(
                key,
                title,
                table_name,
                modes_id,
                columns,
                widths,
                selection_groups,
                codes_per_label=_infer_codes_per_label(conn, table_name, columns),
                exclude=exclude,
            )

    if columns == ("dan", "shuang"):
        sample_value = _sample_column_value(conn, table_name, "dan")
        if re.search(r"\d{2}", sample_value):
            widths = _infer_group_widths(conn, table_name, columns, parse_number_content)
            if widths:
                selection_groups = _infer_group_selection_groups(
                    conn,
                    table_name,
                    columns,
                    parse_number_content,
                    tuple(f"{number:02d}" for number in range(1, 50)),
                )
                return _make_grouped_number_config(
                    key,
                    title,
                    table_name,
                    modes_id,
                    columns,
                    widths,
                    selection_groups,
                    exclude,
                )
        else:
            widths = _infer_group_widths(conn, table_name, columns, parse_tail_digit_content)
            if widths:
                selection_groups = _infer_group_selection_groups(
                    conn,
                    table_name,
                    columns,
                    parse_tail_digit_content,
                    tuple(TAIL_NUMBER_MAP.keys()),
                )
                return _make_grouped_tail_config(
                    key,
                    title,
                    table_name,
                    modes_id,
                    columns,
                    widths,
                    selection_groups,
                    exclude,
                )

    if columns == ("hongbo", "lvbo", "lanbo"):
        widths = _infer_group_widths(conn, table_name, columns, parse_number_content)
        if widths:
            selection_groups = _infer_group_selection_groups(
                conn,
                table_name,
                columns,
                parse_number_content,
                tuple(f"{number:02d}" for number in range(1, 50)),
            )
            return _make_grouped_number_config(
                key,
                title,
                table_name,
                modes_id,
                columns,
                widths,
                selection_groups,
                exclude,
            )

    if columns == ("xiao", "code"):
        xiao_sample = _sample_column_value(conn, table_name, "xiao")
        code_sample = _sample_column_value(conn, table_name, "code")
        zodiac_values = parse_zodiac_content(xiao_sample)
        code_values = parse_number_content(code_sample)
        if (
            zodiac_values
            and code_values
            and all(label in ZODIAC_ORDER for label in zodiac_values)
        ):
            return _make_xiao_code_columns_config(
                key,
                title,
                table_name,
                modes_id,
                "xiao",
                "code",
                len(zodiac_values),
                len(code_values),
                exclude,
            )

    if "content" in all_columns and "xiao" in columns:
        content_sample = _sample_column_value(conn, table_name, "content")
        xiao_sample = _sample_column_value(conn, table_name, "xiao")
        content_items = parse_json_or_plain_content(content_sample)
        xiao_values = parse_zodiac_content(xiao_sample)
        if content_items and (xiao_values or _pipe_right_zodiac_values(content_sample)):
            return _make_content_xiao_config(
                key,
                title,
                table_name,
                modes_id,
                len(xiao_values) or len(_pipe_right_zodiac_values(content_sample)),
                exclude,
            )

    if columns == ("xiao",) and "content" in _table_columns(conn, table_name):
        xiao_sample = _sample_column_value(conn, table_name, "xiao")
        zodiac_values = parse_zodiac_content(xiao_sample)
        if zodiac_values and all(label in ZODIAC_ORDER for label in zodiac_values):
            return _make_content_xiao_config(
                key,
                title,
                table_name,
                modes_id,
                len(zodiac_values),
                exclude,
            )

    if columns == ("xiao", "wei"):
        xiao_widths = _infer_group_widths(conn, table_name, ("xiao",), parse_zodiac_content)
        tail_widths = _infer_group_widths(conn, table_name, ("wei",), parse_tail_digit_content)
        if xiao_widths and tail_widths:
            return _make_mixed_xiao_tail_config(
                key,
                title,
                table_name,
                modes_id,
                xiao_widths[0],
                tail_widths[0],
                xiao_codes_per_label=_infer_codes_per_label(conn, table_name, ("xiao",)),
                exclude=exclude,
            )

    if columns == ("title",):
        sample_title = _sample_column_value(conn, table_name, "title")
        wave_labels = parse_wave_chars(sample_title)
        if wave_labels:
            return _make_text_column_wave_config(
                key,
                title,
                table_name,
                modes_id,
                "title",
                min(len(wave_labels), 3),
                exclude,
            )

        tail_labels = parse_tail_digit_content(sample_title)
        if "尾" in title and tail_labels:
            return _make_text_column_tail_config(
                key,
                title,
                table_name,
                modes_id,
                "title",
                min(len(tail_labels), len(TAIL_NUMBER_MAP)),
                exclude,
            )

        zodiac_labels = parse_zodiac_chars(sample_title)
        if zodiac_labels:
            return _make_text_column_zodiac_config(
                key,
                title,
                table_name,
                modes_id,
                "title",
                min(len(zodiac_labels), len(ZODIAC_ORDER)),
                exclude,
            )

    all_columns = _table_columns(conn, table_name)

    for text_column in ("jiexi", "title", "content"):
        if text_column not in all_columns:
            continue
        sample_text = _sample_column_value(conn, table_name, text_column)
        zodiac_labels = parse_zodiac_chars(sample_text)
        if zodiac_labels and any(marker in title for marker in ("解", "玄机", "真言", "平特", "中特", "诗", "语", "梦", "藏宝", "肖", "码")):
            return _make_text_column_zodiac_config(
                key,
                title,
                table_name,
                modes_id,
                text_column,
                min(len(zodiac_labels), len(ZODIAC_ORDER)),
                exclude,
            )

        tail_labels = parse_tail_digit_content(sample_text)
        if "尾" in title and tail_labels:
            return _make_text_column_tail_config(
                key,
                title,
                table_name,
                modes_id,
                text_column,
                min(len(tail_labels), len(TAIL_NUMBER_MAP)),
                exclude,
            )

    zodiac_source_candidates = (
        "texiao",
        "shengxiao",
        "xiao",
        "xiao1",
        "xiao7",
        "xiao6",
        "xiao8",
        "xiao3",
        "xiao2",
        "pingxiao",
        "xiao_9",
        "xiao_6",
        "shaxiao3",
        "sm_sx",
    )
    for source_column in zodiac_source_candidates:
        if source_column not in columns:
            continue
        sample = _sample_column_value(conn, table_name, source_column)
        zodiac_values = parse_zodiac_content(sample)
        if not zodiac_values or not all(label in ZODIAC_ORDER for label in zodiac_values):
            continue
        code_column = next((column for column in ("code", "tema_code", "x_code", "x7m14", "x6m12", "x4m8") if column in columns), None)
        code_count = len(parse_number_content(_sample_column_value(conn, table_name, code_column))) if code_column else 0
        return _make_source_column_zodiac_config(
            key,
            title,
            table_name,
            modes_id,
            source_column,
            columns,
            len(zodiac_values),
            code_column=code_column,
            code_count=code_count,
            exclude=exclude,
        )

    number_source_candidates = (
        "code",
        "x_code",
        "tema_code",
        "x7m14",
        "x6m12",
        "x4m8",
        "ma_22",
        "ma_13",
        "result",
    )
    for source_column in number_source_candidates:
        if source_column not in columns:
            continue
        sample = _sample_column_value(conn, table_name, source_column)
        number_values = parse_number_content(sample)
        if not number_values:
            continue
        return _make_source_column_number_config(
            key,
            title,
            table_name,
            modes_id,
            source_column,
            columns,
            min(len(tuple(dict.fromkeys(number_values))), 49),
            exclude,
        )

    if "content" in all_columns:
        sample = _sample_column_value(conn, table_name, "content")
        number_values = parse_number_content(sample)
        if number_values and any(marker in title for marker in ("码", "数", "大小")):
            return _make_source_column_number_config(
                key,
                title,
                table_name,
                modes_id,
                "content",
                tuple(column for column in _table_column_list(conn, table_name) if column not in COMMON_PAYLOAD_COLUMNS or column == "content"),
                min(len(tuple(dict.fromkeys(number_values))), 49),
                exclude,
            )

    for source_column in ("tou", "sm_tou"):
        if source_column not in columns:
            continue
        sample = _sample_column_value(conn, table_name, source_column)
        head_values = parse_tail_digit_content(sample)
        if not head_values:
            continue
        return _make_source_column_head_config(
            key,
            title,
            table_name,
            modes_id,
            source_column,
            columns,
            min(len(tuple(dict.fromkeys(head_values))), len(HEAD_NUMBER_MAP)),
            exclude,
        )

    for source_column in ("xing", "wx"):
        if source_column not in columns:
            continue
        sample = _sample_column_value(conn, table_name, source_column)
        labels = tuple(label for label in parse_pipe_label_content(sample) if label in ELEMENT_ORDER)
        if not labels:
            continue
        return _make_source_column_element_config(
            key,
            title,
            table_name,
            modes_id,
            source_column,
            columns,
            min(len(tuple(dict.fromkeys(labels))), len(ELEMENT_ORDER)),
            exclude,
        )

    tail_source_candidates = ("wei", "tou", "wei1", "wei2", "er_wei1", "er_wei2", "san_wei1", "san_wei2")
    for source_column in tail_source_candidates:
        if source_column not in columns:
            continue
        sample = _sample_column_value(conn, table_name, source_column)
        tail_values = parse_tail_digit_content(sample)
        if not tail_values:
            continue
        if source_column.startswith("tou") or source_column == "tou":
            # 头数字段由专门的头数机制处理，不能误归入尾数。
            continue
        return _make_source_column_tail_config(
            key,
            title,
            table_name,
            modes_id,
            source_column,
            columns,
            min(len(tuple(dict.fromkeys(tail_values))), len(TAIL_NUMBER_MAP)),
            exclude,
        )

    return None


def _classify_title_config(
    title: str,
    table_name: str,
    modes_id: int,
    sample_content: str,
) -> PredictionConfig | None:
    """按 title 和样本 content 归类生成预测配置。

    第一阶段只覆盖命中规则明确、可复用性高的玩法：号码、生肖、尾数、头数和
    `标签|值列表` 结构化玩法。文案解读、复合字段、多阶段玩法暂不自动生成，
    需要后续分段单独确认命中口径。
    """
    key = _dynamic_key(modes_id)
    exclude = any(word in title for word in ("杀", "绝杀", "不中"))
    sample_zodiacs = parse_zodiac_content(sample_content)
    sample_text_zodiacs = parse_zodiac_chars(sample_content)
    sample_numbers = parse_number_content(sample_content)
    sample_tail_labels = parse_tail_digit_content(sample_content)

    if _is_text_history_title(title):
        return _make_text_history_mapping_config(
            key,
            title,
            table_name,
            modes_id,
            "content",
        )

    if "|" in sample_content and not any(marker in title for marker in ("尾中特", "必中", "平特", "杀")):
        labels = parse_pipe_label_content(sample_content)
        if labels:
            return _make_pipe_config(
                key,
                title,
                table_name,
                modes_id,
                max(1, len(labels)),
                exclude,
            )

    if tail_count := (
        _extract_count(r"必中([一二两三四五六七八九十\d]+)尾", title)
        or _extract_count(r"([一二两三四五六七八九十\d]+)尾中特", title)
        or _extract_count(r"平特([一二两三四五六七八九十\d]+)尾", title)
        or _extract_count(r"杀([一二两三四五六七八九十\d]+)尾", title)
        or _extract_count(r"([一二两三四五六七八九十\d]+)尾$", title)
    ):
        return _make_tail_config(key, title, table_name, modes_id, tail_count, exclude)

    if head_count := (
        _extract_count(r"([一二两三四五六七八九十\d]+)头中特", title)
        or _extract_count(r"杀([一二两三四五六七八九十\d]+)头", title)
        or _extract_count(r"([一二两三四五六七八九十\d]+)头$", title)
    ):
        return _make_head_config(key, title, table_name, modes_id, head_count, exclude)

    if zodiac_count := (
        _extract_count(r"([一二两三四五六七八九十\d]+)肖中特", title)
        or _extract_count(r"平特([一二两三四五六七八九十\d]+)肖", title)
        or _extract_count(r"杀([一二两三四五六七八九十\d]+)肖", title)
        or _extract_count(r"绝杀([一二两三四五六七八九十\d]+)肖", title)
        or _extract_count(r"([一二两三四五六七八九十\d]+)肖$", title)
    ):
        return _make_zodiac_config(key, title, table_name, modes_id, zodiac_count, exclude)

    if number_count := (
        _extract_count(r"杀([一二两三四五六七八九十\d]+)码", title)
        or _extract_count(r"杀平([一二两三四五六七八九十\d]+)码", title)
        or _extract_count(r"平[一二三四五六七八九十]([一二两三四五六七八九十\d]+)码", title)
        or _extract_count(r"平特([一二两三四五六七八九十\d]+)码", title)
        or _extract_count(r"码段([一二两三四五六七八九十\d]+)", title)
        or _extract_count(r"([一二两三四五六七八九十\d]+)码$", title)
        or _extract_count(r"([一二两三四五六七八九十\d]+)码中特", title)
    ):
        return _make_number_config(key, title, table_name, modes_id, number_count, exclude)

    sample_waves = parse_wave_chars(sample_content)
    if "波" in title and sample_waves:
        return _make_wave_config(key, title, table_name, modes_id, len(sample_waves), exclude)

    if "|" in sample_content:
        labels = parse_pipe_label_content(sample_content)
        if labels:
            return _make_pipe_config(
                key,
                title,
                table_name,
                modes_id,
                max(1, len(labels)),
                exclude,
            )

    if sample_zodiacs and all(label in ZODIAC_ORDER for label in sample_zodiacs):
        return _make_zodiac_config(
            key,
            title,
            table_name,
            modes_id,
            min(len(tuple(dict.fromkeys(sample_zodiacs))), len(ZODIAC_ORDER)),
            exclude,
        )

    if sample_numbers and re.search(r"码|段", title):
        return _make_number_config(
            key,
            title,
            table_name,
            modes_id,
            min(len(tuple(dict.fromkeys(sample_numbers))), 49),
            exclude,
        )

    if "尾" in title and sample_tail_labels:
        return _make_tail_config(
            key,
            title,
            table_name,
            modes_id,
            min(len(tuple(dict.fromkeys(sample_tail_labels))), len(TAIL_NUMBER_MAP)),
            exclude,
        )

    if sample_text_zodiacs and any(marker in title for marker in ("平特", "中特", "玄机", "谜语", "欲钱", "成语", "词语")):
        return _make_text_column_zodiac_config(
            key,
            title,
            table_name,
            modes_id,
            "content",
            min(len(sample_text_zodiacs), len(ZODIAC_ORDER)),
            exclude,
        )

    return None


def build_title_prediction_configs(db_path: str | Path = DEFAULT_DB_TARGET) -> dict[str, PredictionConfig]:
    """从当前数据库的 mode_payload_tables.title 自动建立预测机制。

    - 已经在 PREDICTION_CONFIGS 中手写维护的 modes_id/title 会跳过，避免重复机制。
    - 只生成本地已归一化为 mode_payload_xxx 的表，确保回测和预测都使用本地数据。
    - 当前是第一阶段自动化覆盖，复杂文案和多字段复合玩法留给后续分段处理。
    """
    from predict.registry_builder import build_dynamic_prediction_configs

    return build_dynamic_prediction_configs(
        db_path,
        static_configs=PREDICTION_CONFIGS,
        classify_first_stage=_classify_title_config,
        classify_second_stage=_classify_second_stage_config,
    )


_title_configs_loaded = False


def ensure_prediction_configs_loaded(db_path: str | Path = DEFAULT_DB_TARGET) -> None:
    """在服务启动时加载动态预测配置。

    传入实际数据库路径（如 PostgreSQL DSN），避免依赖本地 SQLite。
    """
    global _title_configs_loaded
    dynamic = build_title_prediction_configs(db_path)
    PREDICTION_CONFIGS.update(dynamic)
    _title_configs_loaded = True
    import logging
    logging.getLogger("predict.init").info(
        "Loaded %d dynamic prediction configs from %s, total: %d",
        len(dynamic), db_path, len(PREDICTION_CONFIGS),
    )


def supported_prediction_keys() -> tuple[str, ...]:
    """返回当前可用预测机制 key，包含手写机制和按 title 自动生成的本地机制。"""
    from predict.registry import PredictionRegistry

    return PredictionRegistry(PREDICTION_CONFIGS).supported_keys()


def list_prediction_configs(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """输出机制清单，便于前端或命令行查看 title 到 key 的映射。"""
    status_map: dict[str, int] = {}
    if db_path is not None:
        status_map = get_mechanism_statuses(db_path)
    from predict.registry import PredictionRegistry

    return PredictionRegistry(PREDICTION_CONFIGS).list_configs(status_map)


# get_mechanism_statuses, set_mechanism_status 已迁移至 predict.mechanism_status
from predict.mechanism_status import (  # noqa: F401 - 兼容导出
    get_mechanism_statuses,
    set_mechanism_status,
)


def get_prediction_config(key: str) -> PredictionConfig:
    """根据统一 key 获取预测配置。"""
    from predict.registry import PredictionRegistry

    return PredictionRegistry(PREDICTION_CONFIGS).get(key)


format_dynamic_pipe_groups = structured_mapping.format_dynamic_pipe_groups

special_parity_from_row = size_parity.special_parity_from_row
special_size_from_row = size_parity.special_size_from_row
special_wave_from_row = size_parity.special_wave_from_row
special_half_wave_from_row = size_parity.special_half_wave_from_row
format_size_groups = size_parity.format_size_groups
format_parity_groups = size_parity.format_parity_groups

parse_mixed_dimension_content = mixed.parse_mixed_dimension_content
mixed_dimension_contains_hit = mixed.mixed_dimension_contains_hit
mixed_dimension_excludes_hit = mixed.mixed_dimension_excludes_hit

format_zodiac_csv = zodiac.format_zodiac_csv
format_xiao_pair = zodiac.format_xiao_pair
format_split_zodiac_columns = zodiac.format_split_zodiac_columns
get_zodiac_numbers = zodiac.get_zodiac_numbers
format_zodiac_one_code = zodiac.format_zodiac_one_code
format_zodiac_two_codes = zodiac.format_zodiac_two_codes
format_zodiac_all_codes = zodiac.format_zodiac_all_codes
format_9x12 = zodiac.format_9x12

format_text_history_mapping = text_mapping.format_text_history_mapping
random_text_pool_row = text_mapping.random_text_pool_row
format_text_pool_jiexi = text_mapping.format_text_pool_jiexi
format_humor_tail_groups = text_mapping.format_humor_tail_groups
format_juzi_title = text_mapping.format_juzi_title
