import json
import random
import re
import sqlite3
from collections import Counter
from typing import Any

from db import connect as db_connect

from common import (
    DEFAULT_DB_PATH,
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


HEAD_NUMBER_MAP: dict[str, list[str]] = {
    "0头": [f"{number:02d}" for number in range(1, 10)],
    "1头": [str(number) for number in range(10, 20)],
    "2头": [str(number) for number in range(20, 30)],
    "3头": [str(number) for number in range(30, 40)],
    "4头": [str(number) for number in range(40, 50)],
}

TAIL_NUMBER_MAP: dict[str, list[str]] = {
    f"{tail}尾": [
        f"{number:02d}"
        for number in range(1, 50)
        if number % 10 == tail
    ]
    for tail in range(10)
}

PARITY_NUMBER_MAP: dict[str, list[str]] = {
    "单": [f"{number:02d}" for number in range(1, 50) if number % 2 == 1],
    "双": [f"{number:02d}" for number in range(1, 50) if number % 2 == 0],
}

WAVE_COLOR_NUMBER_MAP: dict[str, list[str]] = {
    "红波": ["01", "02", "07", "08", "12", "13", "18", "19", "23", "24", "29", "30", "34", "35", "40", "45", "46"],
    "蓝波": ["03", "04", "09", "10", "14", "15", "20", "25", "26", "31", "36", "37", "41", "42", "47", "48"],
    "绿波": ["05", "06", "11", "16", "17", "21", "22", "27", "28", "32", "33", "38", "39", "43", "44", "49"],
}

HALF_WAVE_NUMBER_MAP: dict[str, list[str]] = {
    "红单": ["01", "07", "13", "19", "23", "29", "35", "45"],
    "红双": ["02", "08", "12", "18", "24", "30", "34", "40", "46"],
    "蓝单": ["03", "09", "15", "25", "31", "37", "41", "47"],
    "蓝双": ["04", "10", "14", "20", "26", "36", "42", "48"],
    "绿单": ["05", "11", "17", "21", "27", "33", "39", "43", "49"],
    "绿双": ["06", "16", "22", "28", "32", "38", "44"],
}

SIZE_NUMBER_MAP: dict[str, list[str]] = {
    "小": [f"{number:02d}" for number in range(1, 25)],
    "大": [str(number) for number in range(25, 50)],
}


TABLE_FIXED_MAPPING_KEYS: dict[str, str] = {
    "mode_payload_12": "头",
    "mode_payload_20": "尾",
    "mode_payload_26": "琴棋书画",
    "mode_payload_28": "单双",
    "mode_payload_38": "波色",
    "mode_payload_53": "五行肖",
    "mode_payload_54": "尾",
    "mode_payload_57": "大小",
    "mode_payload_58": "波色单双",
    "mode_payload_61": "四季肖",
}


def labels_from_fixed(mapping_key: str, fallback: tuple[str, ...]):
    def loader(conn: sqlite3.Connection) -> tuple[str, ...]:
        return load_fixed_labels(conn, mapping_key, fallback)

    return loader


def label_for_special_number(
    row: sqlite3.Row,
    conn: sqlite3.Connection,
    mapping_key: str,
    fallback: str,
) -> str:
    special_code = special_code_from_res_code(row["res_code"] or "")
    return fixed_label_for_value(conn, mapping_key, special_code) or fallback


def format_fixed_groups(mapping_key: str, fallback_map: dict[str, list[str]] | None = None):
    def formatter(labels: tuple[str, ...], conn: sqlite3.Connection) -> list[str]:
        mapping = load_fixed_value_map(conn, mapping_key, labels)
        return [
            f"{label}|{','.join(mapping.get(label, tuple(fallback_map.get(label, ()) if fallback_map else ())))}"
            for label in labels
        ]

    return formatter


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
        rows = conn.execute(
            f"""
            SELECT content
            FROM {quote_identifier(table_name)}
            WHERE content IS NOT NULL AND content != ''
            """
        ).fetchall()
        for row in rows:
            for item in parse_json_or_plain_content(row["content"] or ""):
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


def special_head_from_row(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
    """根据 res_code 的特码号码推导特码头数。"""
    special_code = special_code_from_res_code(row["res_code"] or "")
    number = int(special_code)
    fallback = "0头" if number < 10 else f"{number // 10}头"
    return label_for_special_number(row, conn, "头", fallback)


def special_tail_from_row(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
    """根据 res_code 的特码号码推导特码尾数。"""
    special_code = special_code_from_res_code(row["res_code"] or "")
    fallback = f"{int(special_code) % 10}尾"
    return label_for_special_number(row, conn, "尾", fallback)


def special_parity_from_row(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
    """根据 res_code 的特码号码推导单双。"""
    fallback = "双" if int(special_code_from_res_code(row["res_code"] or "")) % 2 == 0 else "单"
    return label_for_special_number(row, conn, "单双", fallback)


def special_size_from_row(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
    """根据特码号码推导大小，01-24 为小，25-49 为大。"""
    fallback = "大" if int(special_code_from_res_code(row["res_code"] or "")) >= 25 else "小"
    return label_for_special_number(row, conn, "大小", fallback)


def special_half_wave_from_row(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
    """根据特码波色和单双推导半波，例如 红单、蓝双。"""
    special_code = special_code_from_res_code(row["res_code"] or "")
    mapped = fixed_label_for_value(conn, "波色单双", special_code)
    if mapped:
        return mapped

    wave = special_wave_from_row(row, conn).removesuffix("波")
    parity = special_parity_from_row(row, conn)
    return f"{wave}{parity}" if wave and parity else ""


def special_wave_from_row(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
    """优先从 res_color 取特码波色；缺失时用固定号码波色映射推导。"""
    values = [value.strip() for value in str(row_get(row, "res_color", "") or "").split(",") if value.strip()]
    if values:
        return {"red": "红波", "blue": "蓝波", "green": "绿波"}.get(values[-1], "")

    special_code = special_code_from_res_code(row["res_code"] or "")
    mapped_label = fixed_label_for_value(conn, "波色", special_code)
    if mapped_label:
        return mapped_label
    return ""


def special_number_from_row(row: sqlite3.Row, _: sqlite3.Connection) -> str:
    """24码直接以特码号码作为命中目标。"""
    return special_code_from_res_code(row["res_code"] or "")


def jiexi_content_from_row(row: sqlite3.Row) -> str:
    """一句真言/四字玄机用 jiexi 字段存储候选生肖。"""
    return str(row_get(row, "jiexi", "") or "")


def tail_code_content_from_row(row: sqlite3.Row) -> str:
    """独家幽默用 code 字段存储尾数候选。"""
    return str(row_get(row, "code", "") or "")


def xiao_code_content_from_row(row: sqlite3.Row) -> str:
    """9肖12码使用 xiao/code 两列，这里把 xiao 作为历史命中标签来源。"""
    return str(row_get(row, "xiao", "") or "")


def black_white_content_from_row(row: sqlite3.Row) -> str:
    """黑白各3肖使用 hei/bai 两列存储预测生肖。"""
    values = [
        str(row_get(row, "hei", "") or "").strip(),
        str(row_get(row, "bai", "") or "").strip(),
    ]
    return ",".join(value for value in values if value)


def join_columns_content_loader(columns: tuple[str, ...]):
    """把多个字段中的预测标签合并为一个字符串参与历史命中率计算。

    多字段玩法常见于 jia/ye、nan/nv、zu1/zu2/zu3、xiao/code 等结构。命中判断
    本质仍是“特码生肖或尾数是否落入这些字段给出的标签集合”，因此只需要把各列
    的标签合并后交给既有 parser 即可。
    """

    def loader(row: sqlite3.Row) -> str:
        values = [
            str(row_get(row, column, "") or "").strip()
            for column in columns
            if str(row_get(row, column, "") or "").strip()
        ]
        return ",".join(values)

    return loader


def parsed_columns_content_loader(columns: tuple[str, ...], value_parser):
    """逐列解析并合并标签，避免把 JSON 字符串直接拼接后破坏原始结构。
    第二阶段支持的多字段玩法里，单列内容可能本身就是 JSON 数组字符串，例如
    `["猴|34,46","龙|14,38"]`。如果直接把多列原值用逗号拼接，再交给统一 parser，
    会把 JSON 内部的逗号也拆开，导致历史命中标签解析失真。这里先按列解析，再合并
    成规范化标签串，供历史回测与策略选择复用。
    """

    def loader(row: sqlite3.Row) -> str:
        labels: list[str] = []
        for column in columns:
            raw_value = str(row_get(row, column, "") or "")
            labels.extend(value_parser(raw_value))
        return ",".join(labels)

    return loader


def tail_columns_content_loader(columns: tuple[str, ...]):
    """读取尾数字段，并统一转成 `N尾` 标签。

    部分表的 dan/shuang 字段只保存 `1,3,5` 这类尾数数字，而预测模块统一用
    `1尾` 标签计算命中，所以这里在读取阶段做一次规范化。
    """

    def loader(row: sqlite3.Row) -> str:
        labels: list[str] = []
        for column in columns:
            raw_value = str(row_get(row, column, "") or "")
            for value in re.findall(r"\d", raw_value):
                label = f"{int(value)}尾"
                if label not in labels:
                    labels.append(label)
        return ",".join(labels)

    return loader


def parse_tail_digit_content(content: str) -> tuple[str, ...]:
    """解析尾数内容，兼容 `1尾`、`1,3,5` 和 JSON `1尾|01,11` 结构。"""
    labels: list[str] = []
    chinese_tail_digits = {
        "零": 0,
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
    }
    for item in parse_json_or_plain_content(content):
        if "|" in item:
            item = item.split("|", 1)[0]
        for value in re.findall(r"\d", item):
            label = f"{int(value)}尾"
            if label not in labels:
                labels.append(label)
        for value in re.findall(r"[零一二两三四五六七八九]", item):
            label = f"{chinese_tail_digits[value]}尾"
            if label not in labels:
                labels.append(label)
    return tuple(labels)


def parse_zodiac_chars(content: str) -> tuple[str, ...]:
    """从无分隔中文文本中提取生肖字符，兼容 jiexi=鼠虎兔龙 这类格式。"""
    values = [normalize_zodiac_label(value) for value in re.findall(r"[鼠牛虎兔龍蛇马馬羊猴鸡雞狗猪豬]", content or "")]
    return tuple(dict.fromkeys(values))


def parse_wave_chars(content: str) -> tuple[str, ...]:
    """从文本中提取红/蓝/绿波色标签。"""
    labels: list[str] = []
    for value in re.findall(r"[红蓝绿]", content or ""):
        label = f"{value}波"
        if label not in labels:
            labels.append(label)
    return tuple(labels)


def build_pipe_value_map(
    conn: sqlite3.Connection,
    table_name: str,
    labels: tuple[str, ...],
) -> dict[str, tuple[str, ...]]:
    """从 `标签|值列表` 的历史 content 中建立标签映射。

    适用于肉菜草肖、红蓝绿肖、头、尾、单双、波色等结构化 content。
    """
    fixed_mapping_key = TABLE_FIXED_MAPPING_KEYS.get(table_name, table_name)
    fixed_mapping = load_fixed_value_map(conn, fixed_mapping_key, labels)
    if fixed_mapping and any(fixed_mapping.values()):
        return fixed_mapping

    result: dict[str, set[str]] = {label: set() for label in labels}
    rows = conn.execute(
        f"""
        SELECT content
        FROM {quote_identifier(table_name)}
        WHERE content IS NOT NULL AND content != ''
        """
    ).fetchall()
    for row in rows:
        for item in parse_json_or_plain_content(row["content"] or ""):
            if "|" not in item:
                continue
            label, raw_values = item.split("|", 1)
            label = label.strip()
            if label not in result:
                continue
            values = [value.strip() for value in raw_values.split(",") if value.strip()]
            result[label].update(values)
    return {label: tuple(sorted(values)) for label, values in result.items()}


def build_qinqi_value_map(conn: sqlite3.Connection) -> dict[str, tuple[str, ...]]:
    """琴棋书画的映射来自 title 与 content 的组合。

    该表的 title 保存标签顺序，例如 `书,棋,琴`；content 保存按标签顺序展开的
    生肖，例如 9 个生肖即 3 个标签各 3 个生肖。因此这里按 title 顺序切片还原映射。
    """
    labels = ("琴", "棋", "书", "画")
    fixed_mapping = load_fixed_value_map(conn, "琴棋书画", labels)
    if fixed_mapping and all(fixed_mapping.get(label) for label in labels):
        return fixed_mapping

    result: dict[str, set[str]] = {label: set() for label in labels}
    rows = conn.execute(
        """
        SELECT title, content
        FROM mode_payload_26
        WHERE title IS NOT NULL AND title != ''
          AND content IS NOT NULL AND content != ''
        """
    ).fetchall()
    for row in rows:
        title_labels = [value.strip() for value in row["title"].split(",") if value.strip()]
        zodiac_values = [value.strip() for value in row["content"].split(",") if value.strip()]
        if not title_labels or len(zodiac_values) % len(title_labels) != 0:
            continue
        chunk_size = len(zodiac_values) // len(title_labels)
        for index, label in enumerate(title_labels):
            if label not in result:
                continue
            start = index * chunk_size
            result[label].update(zodiac_values[start:start + chunk_size])
        if all(result[label] for label in labels):
            break
    return {label: tuple(sorted(values)) for label, values in result.items()}


def category_outcome_from_map(
    value: str,
    mapping: dict[str, tuple[str, ...]],
    labels: tuple[str, ...],
) -> str:
    """把特码生肖或号码归属到某个预测标签。"""
    for label in labels:
        if value in mapping.get(label, ()):
            return label
    return ""


def make_pipe_category_outcome(
    table_name: str,
    labels: tuple[str, ...],
):
    """生成从特码生肖反推结构化 content 标签的 outcome_loader。"""

    def loader(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
        zodiac = special_zodiac_from_number_map(row, conn)
        mapping = build_pipe_value_map(conn, table_name, labels)
        return category_outcome_from_map(zodiac, mapping, labels)

    return loader


def qinqi_outcome_from_row(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
    """根据特码生肖推导琴棋书画标签。"""
    zodiac = special_zodiac_from_number_map(row, conn)
    return category_outcome_from_map(zodiac, build_qinqi_value_map(conn), ("琴", "棋", "书", "画"))


def format_head_groups(labels: tuple[str, ...], _: sqlite3.Connection) -> list[str]:
    """3头中特接口格式：`头|号码列表` 的 JSON 数组。"""
    return format_fixed_groups("头", HEAD_NUMBER_MAP)(labels, _)


def format_tail_groups(labels: tuple[str, ...], _: sqlite3.Connection) -> list[str]:
    """绝杀一尾接口格式：`尾|号码列表` 的 JSON 数组。"""
    return format_fixed_groups("尾", TAIL_NUMBER_MAP)(labels, _)


def format_size_groups(labels: tuple[str, ...], _: sqlite3.Connection) -> list[str]:
    """大小中特接口格式：`大/小|号码列表` 的 JSON 数组。"""
    return format_fixed_groups("大小", SIZE_NUMBER_MAP)(labels, _)


def format_half_wave_groups(labels: tuple[str, ...], _: sqlite3.Connection) -> list[str]:
    """绝杀半波接口格式：`半波|号码列表` 的 JSON 数组。"""
    return format_fixed_groups("波色单双", HALF_WAVE_NUMBER_MAP)(labels, _)


def format_parity_groups(labels: tuple[str, ...], _: sqlite3.Connection) -> list[str]:
    """单双码接口格式：`单/双|号码列表` 的 JSON 数组。"""
    return format_fixed_groups("单双", PARITY_NUMBER_MAP)(labels, _)


def format_wave_csv(labels: tuple[str, ...], _: sqlite3.Connection) -> str:
    """双波中特历史格式为 `红波,蓝波`。"""
    return ",".join(labels)


def format_zodiac_csv(labels: tuple[str, ...], _: sqlite3.Connection) -> str:
    """生肖列表历史格式为英文逗号拼接。"""
    return ",".join(labels)


def format_zodiac_groups(table_name: str, labels: tuple[str, ...]):
    """返回 `标签|生肖列表` 结构化 content formatter。"""

    def formatter(selected: tuple[str, ...], conn: sqlite3.Connection) -> list[str]:
        mapping = build_pipe_value_map(conn, table_name, labels)
        return [f"{label}|{','.join(mapping.get(label, ()))}" for label in selected]

    return formatter


def format_qinqi_content(labels: tuple[str, ...], conn: sqlite3.Connection) -> str:
    """琴棋书画原始 content 是按标签展开后的生肖字符串。"""
    mapping = build_qinqi_value_map(conn)
    values: list[str] = []
    for label in labels:
        values.extend(mapping.get(label, ()))
    return ",".join(values)


def format_xiao_pair(labels: tuple[str, ...], _: sqlite3.Connection) -> dict[str, str]:
    """单双四肖原表使用 xiao_1/xiao_2，两组各 4 个生肖。"""
    return {
        "xiao_1": ",".join(labels[:4]),
        "xiao_2": ",".join(labels[4:8]),
    }


def format_split_zodiac_columns(
    columns: tuple[str, ...],
    widths: tuple[int, ...],
    codes_per_label: int = 0,
):
    """按历史列结构回填生肖分组，必要时补出每个生肖对应的固定号码。
    例如：
    - `家野4肖` 需要输出 `{"jia": "猪,鸡,羊,牛", "ye": "鼠,龙,虎,蛇"}`
    - `3组3肖6码` 需要输出 `{"zu1": "[\"猴|34,46\", ...]" , ...}`
    """

    def formatter(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, str]:
        result: dict[str, str] = {}
        index = 0
        for column, width in zip(columns, widths):
            group_labels = labels[index:index + width]
            index += width
            if codes_per_label > 0:
                result[column] = json.dumps(
                    [
                        f"{label}|{','.join(get_zodiac_numbers(conn, label)[:codes_per_label])}"
                        for label in group_labels
                    ],
                    ensure_ascii=False,
                )
            else:
                result[column] = ",".join(group_labels)
        return result

    return formatter


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


def format_split_number_columns(columns: tuple[str, ...], widths: tuple[int, ...]):
    """按列宽把号码集合拆回历史表结构，例如 `dan/shuang` 两列各 16 码。"""

    def formatter(labels: tuple[str, ...], _: sqlite3.Connection) -> dict[str, str]:
        result: dict[str, str] = {}
        index = 0
        for column, width in zip(columns, widths):
            result[column] = ",".join(labels[index:index + width])
            index += width
        return result

    return formatter


def format_xiao_code_columns(
    xiao_column: str,
    code_column: str,
    code_count: int,
):
    """根据选中的生肖生成对应号码列，保持 `xiao/code` 历史表结构。"""

    def formatter(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, str]:
        per_zodiac_numbers = {label: get_zodiac_numbers(conn, label) for label in labels}
        selected_codes: list[str] = []
        index = 0
        while len(selected_codes) < code_count and index < 5:
            for label in labels:
                numbers = per_zodiac_numbers.get(label, [])
                if index < len(numbers):
                    code = numbers[index]
                    if code not in selected_codes:
                        selected_codes.append(code)
                        if len(selected_codes) == code_count:
                            break
            index += 1

        return {
            xiao_column: ",".join(labels),
            code_column: ",".join(selected_codes),
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


def parse_mixed_dimension_content(content: str) -> tuple[str, ...]:
    """解析内部混合标签，当前用于 `生肖 + 尾数` 组合玩法。"""
    return tuple(value.strip() for value in content.split(",") if value.strip())


def mixed_xiao_tail_outcome_from_row(row: sqlite3.Row, conn: sqlite3.Connection) -> str:
    """把真实开奖结果表示为两个命中原子：特码生肖和特码尾数。"""
    return f"肖:{special_zodiac_from_number_map(row, conn)}|尾:{special_tail_from_row(row, conn)}"


def mixed_dimension_contains_hit(outcome: str, labels: tuple[str, ...]) -> bool:
    """组合玩法命中：任一真实命中原子落入预测标签集合。"""
    return any(value in labels for value in str(outcome or "").split("|") if value)


def mixed_dimension_excludes_hit(outcome: str, labels: tuple[str, ...]) -> bool:
    """组合绝杀玩法命中：所有真实命中原子都没有落入预测标签集合。"""
    return not mixed_dimension_contains_hit(outcome, labels)


def _content_category_pool(conn: sqlite3.Connection, table_name: str) -> list[str]:
    if not table_exists(conn, table_name) or "content" not in _table_columns(conn, table_name):
        return []
    rows = conn.execute(
        f"""
        SELECT content
        FROM {quote_identifier(table_name)}
        WHERE content IS NOT NULL AND content != ''
        GROUP BY content
        ORDER BY COUNT(*) DESC, content
        """
    ).fetchall()
    return [str(row["content"] or "") for row in rows]


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


def format_content_xiao_columns(table_name: str, xiao_column: str = "xiao"):
    """还原 `content+xiao` 输出结构。
    这类历史表的 content 是分类池，xiao 是最终生肖候选。根据历史样本，xiao 候选
    与 content 分类内生肖互斥，因此生成时优先选一个与预测生肖不重叠的历史分类。
    """

    def formatter(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, str]:
        selected = set(labels)
        pool = _content_category_pool(conn, table_name)
        content = ""
        for candidate in pool:
            if not selected.intersection(_pipe_right_zodiac_values(candidate)):
                content = candidate
                break
        if not content and pool:
            content = pool[0]
        return {
            "content": content,
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


def get_zodiac_numbers(conn: sqlite3.Connection, zodiac: str) -> list[str]:
    """从固定映射表读取生肖对应号码。"""
    mapping = load_fixed_value_map(conn, "生肖", (zodiac,))
    return list(mapping.get(zodiac, ()))


def format_zodiac_one_code(labels: tuple[str, ...], conn: sqlite3.Connection) -> list[str]:
    """7肖7码：每个生肖带 1 个代表号码。"""
    result: list[str] = []
    for label in labels:
        numbers = get_zodiac_numbers(conn, label)
        result.append(f"{label}|{numbers[0] if numbers else ''}")
    return result


def format_zodiac_two_codes(labels: tuple[str, ...], conn: sqlite3.Connection) -> list[str]:
    """4肖8码：每个生肖带 2 个代表号码。"""
    result: list[str] = []
    for label in labels:
        numbers = get_zodiac_numbers(conn, label)[:2]
        result.append(f"{label}|{','.join(numbers)}")
    return result


def format_9x12(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, str]:
    """9肖12码：输出 9 个生肖和 12 个号码。"""
    selected_codes: list[str] = []
    per_zodiac_numbers = {label: get_zodiac_numbers(conn, label) for label in labels}
    index = 0
    while len(selected_codes) < 12 and index < 5:
        for label in labels:
            numbers = per_zodiac_numbers.get(label, [])
            if index < len(numbers):
                selected_codes.append(numbers[index])
                if len(selected_codes) == 12:
                    break
        index += 1
    return {
        "xiao": ",".join(labels),
        "code": ",".join(selected_codes),
    }


def format_24_numbers(labels: tuple[str, ...], _: sqlite3.Connection) -> str:
    """24码历史格式为 24 个号码逗号拼接。"""
    return ",".join(labels)


def format_title_jiexi(title: str):
    """文案类玩法没有稳定生成文案模型，这里输出可审计的预测标题和候选生肖。"""

    def formatter(labels: tuple[str, ...], _: sqlite3.Connection) -> dict[str, Any]:
        return {
            "title": title,
            "jiexi": "".join(labels),
            "content": f"{title}：{','.join(labels)}",
        }

    return formatter


TEXT_POOL_SOURCES: dict[str, tuple[str, str]] = {
    "一句真言": ("mode_payload_50", "content"),
    "四字玄机": ("mode_payload_52", "title"),
    "独家幽默": ("mode_payload_59", "content"),
}

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


def _text_history_preferred_column(conn: sqlite3.Connection, modes_id: int) -> str | None:
    """从精简后的 text_history_mappings 里选一个优先展示字段。"""
    if not table_exists(conn, TEXT_HISTORY_MAPPING_TABLE):
        return None
    columns = set(_table_column_list(conn, TEXT_HISTORY_MAPPING_TABLE))
    filters = []
    params: list[Any] = []
    if "mode_id" in columns and modes_id >= 0:
        filters.append("mode_id = ?")
        params.append(modes_id)
    for column in TEXT_HISTORY_COLUMN_PREFERENCE:
        if column not in columns:
            continue
        where_prefix = ""
        if filters:
            where_prefix = "WHERE " + " AND ".join(filters) + f" AND COALESCE({quote_identifier(column)}, '') != ''"
        else:
            where_prefix = f"WHERE COALESCE({quote_identifier(column)}, '') != ''"
        row = conn.execute(
            f"""
            SELECT 1
            FROM {quote_identifier(TEXT_HISTORY_MAPPING_TABLE)}
            {where_prefix}
            LIMIT 1
            """,
            params,
        ).fetchone()
        if row:
            return column
    if filters:
        return _text_history_preferred_column(conn, -1)
    return None


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
    filters: list[str] = []
    params: list[Any] = []
    if "mode_id" in columns and modes_id >= 0:
        filters.append("mode_id = ?")
        params.append(modes_id)

    if preferred_column and preferred_column in columns:
        where_parts = list(filters)
        where_parts.append(f"COALESCE({quote_identifier(preferred_column)}, '') != ''")
        row = conn.execute(
            f"""
            SELECT *
            FROM {quote_identifier(TEXT_HISTORY_MAPPING_TABLE)}
            WHERE {" AND ".join(where_parts)}
            ORDER BY RANDOM()
            LIMIT 1
            """,
            params,
        ).fetchone()
        if row:
            return row

    available_columns = [column for column in TEXT_HISTORY_COLUMN_PREFERENCE if column in columns]
    if not available_columns:
        return None
    text_where_clause = " OR ".join(
        f"COALESCE({quote_identifier(column)}, '') != ''" for column in available_columns
    )
    where_parts = list(filters)
    where_parts.append(f"({text_where_clause})")
    row = conn.execute(
        f"""
        SELECT *
        FROM {quote_identifier(TEXT_HISTORY_MAPPING_TABLE)}
        WHERE {" AND ".join(where_parts)}
        ORDER BY RANDOM()
        LIMIT 1
        """,
        params,
    ).fetchone()
    if row:
        return row

    if filters:
        return _random_text_history_mapping_row(conn, -1, (), text_column)
    return None


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


def _latest_window_metadata(
    conn: sqlite3.Connection,
    table_name: str,
) -> dict[str, Any]:
    """读取连期表最新一组窗口元信息，用于保持输出结构稳定。"""
    if not table_exists(conn, table_name):
        return {}

    columns = set(_table_column_list(conn, table_name))
    selected_columns = [
        column for column in ("start", "end", "image_url")
        if column in columns
    ]
    if not selected_columns:
        return {}

    order_parts: list[str] = []
    if "year" in columns:
        order_parts.append("CAST(year AS INTEGER) DESC")
    if "term" in columns:
        order_parts.append("CAST(term AS INTEGER) DESC")
    if "source_record_id" in columns:
        order_parts.append(
            "CAST(COALESCE(NULLIF(CAST(source_record_id AS TEXT), ''), '0') AS INTEGER) DESC"
        )
    elif "id" in columns:
        order_parts.append(
            "CAST(COALESCE(NULLIF(CAST(id AS TEXT), ''), '0') AS INTEGER) DESC"
        )
    order_clause = f" ORDER BY {', '.join(order_parts)}" if order_parts else ""

    row = conn.execute(
        f"""
        SELECT {", ".join(quote_identifier(column) for column in selected_columns)}
        FROM {quote_identifier(table_name)}
        {order_clause}
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return {}
    return {
        column: row[column]
        for column in selected_columns
    }


def format_text_history_mapping(title: str, modes_id: int, text_column: str | None = None):
    """输出历史文本映射配对，不做文本语义猜测。

    该类玩法的本质是历史推荐池：随机抽取一条历史文本，并携带它当期对应的
    特码号码和特码生肖。这样“四字词语/谜语/玄机”等玩法不需要硬编码解释规则。
    """

    def formatter(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, Any]:
        row = _random_text_history_mapping_row(conn, modes_id, labels, text_column)
        if not row:
            return {
                "title": title,
                "content": title,
                "code": "",
                "sx": "",
                "_labels": list(labels),
            }

        result: dict[str, Any] = {
            key: str(row[key] or "")
            for key in ("title", "content", "jiexi")
            if key in row.keys() and row[key] not in (None, "")
        }
        if not result:
            source_text_column = text_column or "content"
            result[source_text_column] = title
        result["_labels"] = list(labels)
        return result

    return formatter


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
        content_formatter=format_text_history_mapping(title, modes_id, text_column),
        hit_checker=contains_hit,
        explanation=(
            f"{title} 属于文本历史映射玩法，不做固定语义推理。",
            "系统从 text_history_mappings 读取历史中已经出现过的文本与当期特码号码/生肖配对。",
            "预测时先按历史特码生肖选择候选生肖，再随机抽取一条匹配的历史文本配对；若没有匹配项则从该玩法历史池随机抽取。",
        ),
    )


def random_text_pool_row(conn: sqlite3.Connection, mapping_key: str) -> dict[str, str] | None:
    """从 SQLite 文案池随机取一条文案；旧库没有文案池时回退到源玩法表。"""
    source = TEXT_POOL_SOURCES.get(mapping_key)
    if not source:
        return None
    table_name, text_column = source
    if not table_exists(conn, table_name):
        return None
    columns = list(_table_column_list(conn, table_name))
    if text_column not in columns:
        return None

    selected_columns = [
        column for column in ("title", "content", "jiexi", "code") if column in columns
    ]
    row = conn.execute(
        f"""
        SELECT {", ".join(quote_identifier(column) for column in selected_columns)}
        FROM {quote_identifier(table_name)}
        WHERE {quote_identifier(text_column)} IS NOT NULL
          AND {quote_identifier(text_column)} != ''
        GROUP BY {quote_identifier(text_column)}
        ORDER BY RANDOM()
        LIMIT 1
        """
    ).fetchone()
    return {key: str(row[key] or "") for key in row.keys()} if row else None


def format_text_pool_jiexi(title: str, mapping_key: str):
    def formatter(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, Any]:
        source = TEXT_POOL_SOURCES.get(mapping_key)
        if source:
            table_name, text_column = source
            modes_id = int(table_name.rsplit("_", 1)[-1])
            output_columns = _table_output_columns(conn, table_name, ("title", "content", "jiexi"))
            row = _random_text_history_mapping_row(conn, modes_id, labels, text_column)
            if row:
                result: dict[str, Any] = {}
                if "title" in output_columns:
                    result["title"] = str(row["title"] or title) if "title" in row.keys() else title
                if "content" in output_columns:
                    content_value = ""
                    if "content" in row.keys():
                        content_value = str(row["content"] or "")
                    if not content_value and text_column in row.keys():
                        content_value = str(row[text_column] or "")
                    result["content"] = content_value or f"{title}：{','.join(labels)}"
                if "jiexi" in output_columns:
                    jiexi_value = str(row["jiexi"] or "") if "jiexi" in row.keys() else ""
                    result["jiexi"] = jiexi_value or "".join(labels)
                if not result:
                    result[text_column] = title
                result["_labels"] = list(labels)
                return result

        row = random_text_pool_row(conn, mapping_key)
        table_name, text_column = source if source else ("", "content")
        output_columns = _table_output_columns(conn, table_name, ("title", "content", "jiexi"))
        result: dict[str, Any] = {}
        if "title" in output_columns:
            result["title"] = (row or {}).get("title") or title
        if "content" in output_columns:
            result["content"] = (row or {}).get("content") or f"{title}：{','.join(labels)}"
        if "jiexi" in output_columns:
            result["jiexi"] = (row or {}).get("jiexi") or "".join(labels)
        if not result:
            result[text_column] = title
        return result

    return formatter


def format_humor_tail_groups(labels: tuple[str, ...], _: sqlite3.Connection) -> dict[str, Any]:
    """独家幽默保留 title/content/code 三字段结构。

    title/content 从 text_history_mappings (mode_id=59) 随机抽取；
    code 为随机 6 个尾数分组。
    """
    mapped = _random_text_history_mapping_row(_, 59, (), "content")

    # 随机选取 6 个尾数生成 code
    all_tails = list(TAIL_NUMBER_MAP.keys())
    selected_tails = random.sample(all_tails, 6)
    humor_code = [f"{tail}|{','.join(TAIL_NUMBER_MAP[tail])}" for tail in selected_tails]

    if mapped:
        return {
            "title": str(mapped["title"] or "预测独家幽默") if "title" in mapped.keys() else "预测独家幽默",
            "content": str(mapped["content"] or "") if "content" in mapped.keys() else "",
            "code": humor_code,
            "_labels": list(labels),
        }

    row = random_text_pool_row(_, "独家幽默")
    return {
        "title": (row or {}).get("title") or "预测独家幽默",
        "content": (row or {}).get("content") or f"独家幽默：本期参考 {','.join(labels)}。",
        "code": humor_code,
    }


def format_juzi_title(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, Any]:
    """欲钱解特：从 text_history_mappings (mode_id=62) 随机抽取 title。"""
    mapped = _random_text_history_mapping_row(conn, 62, (), "title")
    if mapped and "title" in mapped.keys():
        return {"title": str(mapped["title"] or ""), "_labels": list(labels)}
    return {"title": "欲钱解特诗", "_labels": list(labels)}


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
        content_parser=parse_zodiac_content,
        content_formatter=format_qinqi_content,
        hit_checker=contains_hit,
        labels_loader=labels_from_fixed("琴棋书画", ("琴", "棋", "书", "画")),
        explanation=(
            "琴棋书画把生肖分为琴、棋、书、画四类，每次选择三类。",
            "该表 title 存预测标签，content 存按标签展开的生肖；脚本用 title/content 还原映射。",
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


def _sample_content(conn: sqlite3.Connection, table_name: str) -> str:
    if not table_exists(conn, table_name):
        return ""
    columns = _table_columns(conn, table_name)
    if "content" not in columns:
        return ""
    row = conn.execute(
        f"""
        SELECT content
        FROM {quote_identifier(table_name)}
        WHERE content IS NOT NULL AND content != ''
        LIMIT 1
        """
    ).fetchone()
    return str(row["content"] or "") if row else ""


COMMON_PAYLOAD_COLUMNS = {
    "id",
    "web",
    "type",
    "year",
    "term",
    "res_code",
    "res_sx",
    "res_color",
    "status",
    "content",
    "image_url",
    "video_url",
    "web_id",
    "modes_id",
    "source_record_id",
    "fetched_at",
    "month",
    "m_tema",
}


def _table_column_list(conn: sqlite3.Connection, table_name: str) -> tuple[str, ...]:
    return tuple(conn.table_columns(table_name))


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return set(_table_column_list(conn, table_name))


def _business_columns(conn: sqlite3.Connection, table_name: str) -> tuple[str, ...]:
    """返回去掉公共开奖字段后的业务列，并保持 SQLite 原始列顺序。"""
    return tuple(column for column in _table_column_list(conn, table_name) if column not in COMMON_PAYLOAD_COLUMNS)


def _sample_column_value(conn: sqlite3.Connection, table_name: str, column: str) -> str:
    if column not in _table_columns(conn, table_name):
        return ""
    row = conn.execute(
        f"""
        SELECT {quote_identifier(column)}
        FROM {quote_identifier(table_name)}
        WHERE {quote_identifier(column)} IS NOT NULL
          AND {quote_identifier(column)} != ''
        LIMIT 1
        """
    ).fetchone()
    return str(row[column] or "") if row else ""


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
        rows = conn.execute(
            f"""
            SELECT {quote_identifier(column)}
            FROM {quote_identifier(table_name)}
            WHERE {quote_identifier(column)} IS NOT NULL
              AND {quote_identifier(column)} != ''
            LIMIT 50
            """
        ).fetchall()
        for row in rows:
            parsed_values = tuple(value_parser(str(row[column] or "")))
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
        rows = conn.execute(
            f"""
            SELECT {quote_identifier(column)}
            FROM {quote_identifier(table_name)}
            WHERE {quote_identifier(column)} IS NOT NULL
              AND {quote_identifier(column)} != ''
            LIMIT 50
            """
        ).fetchall()
        for row in rows:
            raw_value = str(row[column] or "")
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
        rows = conn.execute(
            f"""
            SELECT {quote_identifier(column)}
            FROM {quote_identifier(table_name)}
            WHERE {quote_identifier(column)} IS NOT NULL
              AND {quote_identifier(column)} != ''
            LIMIT 200
            """
        ).fetchall()
        for row in rows:
            for value in value_parser(str(row[column] or "")):
                if value not in seen:
                    seen.append(value)
        groups.append(_ordered_labels(seen, preferred_order) or preferred_order)
    return tuple(groups)


def _is_first_stage_supported_table(columns: set[str]) -> bool:
    """第一阶段只自动处理 content 单字段玩法。

    很多 title 在 fetched_mode_records 中带有 xiao/code/jiexi/nan/nv/zu1 等复合字段，
    这些字段通常代表多个命中维度或前端输出结构。为了避免“按 title 猜规则”造成
    错误命中口径，本阶段只让 content 单字段表进入自动机制。
    """
    return "content" in columns and not (columns - COMMON_PAYLOAD_COLUMNS)


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


def format_window_content(base_formatter, table_name: str):
    """给连期表恢复 `start/end/content` 输出结构。
    预测脚本无法预知真实下一段窗口的 end，这里只生成 content，start/end 留空给调用方
    或上游排期逻辑填充；历史回测仍按表内已有 start/end 展开的逐期开奖行计算。
    """

    def formatter(labels: tuple[str, ...], conn: sqlite3.Connection) -> dict[str, Any]:
        metadata = _latest_window_metadata(conn, table_name)
        return {
            "start": str(metadata.get("start") or ""),
            "end": str(metadata.get("end") or ""),
            "content": base_formatter(labels, conn),
            "image_url": metadata.get("image_url"),
        }

    return formatter


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
                result[column] = ""
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
                result[column] = ""
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
                result[column] = ""
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
        result = {column: "" for column in output_columns}
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
        result = {column: "" for column in output_columns}
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
        rows = conn.execute(
            f"""
            SELECT {quote_identifier(label_column)}
            FROM {quote_identifier(table_name)}
            WHERE {quote_identifier(label_column)} IS NOT NULL
              AND {quote_identifier(label_column)} != ''
            """
        ).fetchall()
        labels: list[str] = []
        for row in rows:
            for label in parse_pipe_label_content(str(row[label_column] or "")):
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
    rows = conn.execute(
        f"""
        SELECT {", ".join(quote_identifier(column) for column in selected_columns)}
        FROM {quote_identifier(table_name)}
        WHERE {quote_identifier(label_column)} IS NOT NULL
          AND {quote_identifier(label_column)} != ''
        """
    ).fetchall()
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
) -> PredictionConfig:
    """构建 `content+xiao` 玩法。
    历史 content 保存分类说明，例如 `地肖|蛇,羊,...`；xiao 保存最终候选生肖。
    从样本看二者互斥，因此命中回测只按 xiao 候选生肖统计，content 由历史分类池回填。
    """

    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=modes_id,
        labels=tuple(ZODIAC_ORDER),
        label_count=xiao_width,
        outcome_loader=special_zodiac_from_number_map,
        content_loader=xiao_column_content_loader("xiao"),
        content_parser=parse_zodiac_content,
        content_formatter=format_content_xiao_columns(table_name, "xiao"),
        hit_checker=excludes_hit if exclude else contains_hit,
        explanation=(
            f"{title} 使用 `content+xiao` 双字段结构。",
            "content 保存分类与分类内生肖列表，xiao 保存最终候选生肖；回测命中只按 xiao 列计算。",
            "生成输出时从历史 content 分类池选择一个与预测生肖不重叠的分类，再回填 xiao 字段。",
        ),
    )


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
    conn: sqlite3.Connection,
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


def build_title_prediction_configs(db_path=DEFAULT_DB_PATH) -> dict[str, PredictionConfig]:
    """从本地 SQLite 的 mode_payload_tables.title 自动建立预测机制。

    - 已经在 PREDICTION_CONFIGS 中手写维护的 modes_id/title 会跳过，避免重复机制。
    - 只生成本地已归一化为 mode_payload_xxx 的表，确保回测和预测都使用本地数据。
    - 当前是第一阶段自动化覆盖，复杂文案和多字段复合玩法留给后续分段处理。
    """
    try:
        conn = db_connect(db_path)
    except Exception:
        return {}

    with conn:
        if not table_exists(conn, "mode_payload_tables"):
            return {}

        existing_modes_ids = {config.default_modes_id for config in PREDICTION_CONFIGS.values()}
        existing_titles = {config.title for config in PREDICTION_CONFIGS.values()}
        generated: dict[str, PredictionConfig] = {}

        rows = conn.execute(
            """
            SELECT modes_id, title, table_name, record_count
            FROM mode_payload_tables
            ORDER BY modes_id
            """
        ).fetchall()
        for row in rows:
            modes_id = int(row["modes_id"])
            title = str(row["title"] or "").strip()
            table_name = str(row["table_name"] or "").strip()
            if (
                not title
                or modes_id in existing_modes_ids
                or title in existing_titles
                or not table_exists(conn, table_name)
                or int(row["record_count"] or 0) <= 0
            ):
                continue

            columns = _table_columns(conn, table_name)
            business_columns = _business_columns(conn, table_name)

            if _is_first_stage_supported_table(columns):
                config = _classify_title_config(title, table_name, modes_id, _sample_content(conn, table_name))
            else:
                config = _classify_second_stage_config(
                    conn,
                    title,
                    table_name,
                    modes_id,
                    business_columns,
                )
            if config is not None:
                generated[config.key] = config

        return generated


PREDICTION_CONFIGS.update(build_title_prediction_configs())


def supported_prediction_keys() -> tuple[str, ...]:
    """返回当前可用预测机制 key，包含手写机制和按 title 自动生成的本地机制。"""
    return tuple(sorted(PREDICTION_CONFIGS))


def list_prediction_configs() -> list[dict[str, Any]]:
    """输出机制清单，便于前端或命令行查看 title 到 key 的映射。"""
    return [
        {
            "key": key,
            "title": config.title,
            "default_modes_id": config.default_modes_id,
            "default_table": config.default_table,
        }
        for key, config in sorted(PREDICTION_CONFIGS.items())
    ]


def get_prediction_config(key: str) -> PredictionConfig:
    """根据统一 key 获取预测配置。"""
    try:
        return PREDICTION_CONFIGS[key]
    except KeyError as exc:
        supported = ", ".join(sorted(PREDICTION_CONFIGS))
        raise ValueError(f"不支持的预测机制: {key}。当前支持: {supported}") from exc
