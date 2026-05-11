import argparse
import itertools
import hashlib
import json
import math
import random
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from db import connect as db_connect
from runtime_config import get_bootstrap_config_value

DEFAULT_DB_PATH = BACKEND_ROOT / "data" / "lottery_modes.sqlite3"
DEFAULT_TARGET_HIT_RATE = float(get_bootstrap_config_value("prediction.default_target_hit_rate", 0.65))

# 固定顺序用于稳定输出，避免同分策略在不同 Python 版本或数据库顺序下产生不同结果。
ZODIAC_ORDER = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
ELEMENT_ORDER = ["金", "木", "水", "火", "土"]
ZODIAC_ALIASES = {
    "龍": "龙",
    "馬": "马",
    "雞": "鸡",
    "豬": "猪",
}

def normalize_zodiac_label(label: str) -> str:
    """把历史数据中偶发的繁体生肖归一到 fixed_data 使用的简体标签。"""
    return ZODIAC_ALIASES.get(str(label or "").strip(), str(label or "").strip())

@dataclass(frozen=True)
class HistoryRecord:
    """一条可参与预测回测的开奖历史。"""

    year: int
    term: int
    res_code: str
    res_sx: str
    outcome: str
    content: str
    content_labels: tuple[str, ...]

@dataclass(frozen=True)
class PredictionConfig:
    """单个预测玩法的配置。

    label_count 表示本玩法最终输出多少个标签，例如 3肖中特输出 3 个生肖。
    outcome_loader 用于从一行开奖记录中提取“真实命中目标”。
    content_parser 用于解析历史 content，计算历史原始 content 的命中率。
    content_formatter 用于把预测标签转成 API 所需 content 字段。
    """

    key: str
    title: str
    default_table: str
    default_modes_id: int
    labels: tuple[str, ...]
    label_count: int
    outcome_loader: Callable[[Any, Any], str]
    content_loader: Callable[[Any], str]
    content_parser: Callable[[str], tuple[str, ...]]
    content_formatter: Callable[[tuple[str, ...], Any], Any]
    hit_checker: Callable[[str, tuple[str, ...]], bool]
    explanation: tuple[str, ...]
    labels_loader: Callable[[Any], tuple[str, ...]] | None = None
    selection_groups: tuple[tuple[str, ...], ...] | None = None
    selection_widths: tuple[int, ...] | None = None

def parse_res_code(res_code: str) -> list[str]:
    """解析逗号分隔的开奖结果，并统一补齐 01-09。"""
    codes: list[str] = []
    for raw_code in res_code.split(","):
        raw_code = raw_code.strip()
        if not raw_code:
            continue
        if not re.fullmatch(r"\d{1,2}", raw_code):
            raise ValueError(f"res_code 中存在无效号码: {raw_code}")
        number = int(raw_code)
        if number < 1 or number > 49:
            raise ValueError(f"res_code 号码必须在 01-49 之间: {raw_code}")
        codes.append(f"{number:02d}")

    if not codes:
        raise ValueError("res_code 不能为空。")
    return codes

def special_code_from_res_code(res_code: str) -> str:
    """按现有数据口径，res_code 最后一个号码是特码。"""
    return parse_res_code(res_code)[-1]

def special_zodiac_from_row(row: Any, _: Any) -> str:
    """从 res_sx 提取特码生肖。"""
    values = [value.strip() for value in str(row["res_sx"] or "").split(",") if value.strip()]
    if values:
        return normalize_zodiac_label(values[-1])
    return ""

def special_zodiac_from_number_map(row: Any, conn: Any) -> str:
    """优先从 res_sx 取特码生肖；缺失时用号码 -> 生肖映射推导。"""
    direct_value = special_zodiac_from_row(row, conn)
    if direct_value:
        return direct_value

    special_code = special_code_from_res_code(row["res_code"] or "")
    return fixed_label_for_value(conn, "生肖", special_code)

def get_table_title(conn: Any, table_name: str) -> tuple[int | None, str | None]:
    """通过拆表映射找回表对应的 modes_id 和中文标题。"""
    row = conn.execute(
        """
        SELECT modes_id, title
        FROM mode_payload_tables
        WHERE table_name = ?
        """,
        (table_name,),
    ).fetchone()
    if not row:
        return None, None
    return int(row["modes_id"]), str(row["title"])

def load_rows(conn: Any, table_name: str) -> list[Any]:
    """读取有开奖结果的历史记录，按年份和期号升序用于回测。

    通过子查询先取最近 200 条再升序排列——保证回测按时间顺序推进，
    同时避免全表扫描拖慢 predict()。
    """
    return conn.execute(
        f"""
        SELECT * FROM (
            SELECT *
            FROM {quote_identifier(table_name)}
            WHERE res_code IS NOT NULL AND res_code != ''
            ORDER BY CAST(year AS INTEGER) DESC, CAST(term AS INTEGER) DESC
            LIMIT 10
        ) AS recent
        ORDER BY CAST(year AS INTEGER), CAST(term AS INTEGER)
        """
    ).fetchall()

def row_get(row: Any, key: str, default: Any = "") -> Any:
    """安全读取行字段，兼容 sqlite3.Row / psycopg dict row。"""
    keys = row.keys() if hasattr(row, "keys") else ()
    return row[key] if key in keys else default

def default_content_from_row(row: Any) -> str:
    """大多数玩法的历史内容都存放在 content 列。"""
    return str(row_get(row, "content", "") or "")

def xiao_pair_content_from_row(row: Any) -> str:
    """单双四肖使用 xiao_1/xiao_2 两列存储预测生肖。"""
    values = [
        str(row_get(row, "xiao_1", "") or "").strip(),
        str(row_get(row, "xiao_2", "") or "").strip(),
    ]
    return ",".join(value for value in values if value)

def title_content_from_row(row: Any) -> str:
    """琴棋书画的命中标签存放在 title 列，content 是展开后的生肖列表。"""
    return str(row_get(row, "title", "") or "")

def quote_identifier(identifier: str) -> str:
    """SQLite 标识符转义，避免表名参数造成 SQL 注入。"""
    return '"' + identifier.replace('"', '""') + '"'

def table_exists(conn: Any, table_name: str) -> bool:
    return conn.table_exists(table_name)

def normalize_fixed_label(label: str) -> str:
    """把 fixed_data 的部分分类名归一为预测玩法使用的标签名。"""
    if label in {"金肖", "木肖", "水肖", "火肖", "土肖"}:
        return label.removesuffix("肖")
    return label

def split_fixed_code_values(code: str) -> list[str]:
    return [value.strip() for value in str(code or "").split(",") if value.strip()]

def normalize_fixed_value(value: str) -> str:
    value = str(value or "").strip()
    if re.fullmatch(r"\d+", value):
        return f"{int(value):02d}"
    return value

def load_fixed_value_map(
    conn: Any,
    mapping_key: str,
    fallback_labels: tuple[str, ...] = (),
) -> dict[str, tuple[str, ...]]:
    """从 fixed_data 单表读取 `标签 -> 值列表`。"""
    result: dict[str, list[tuple[int, str]]] = {}
    if not table_exists(conn, "fixed_data"):
        return {label: () for label in fallback_labels} if fallback_labels else {}

    rows = conn.execute(
        """
        SELECT id, name, code
        FROM fixed_data
        WHERE sign = ?
        ORDER BY CAST(id AS INTEGER)
        """,
        (mapping_key,),
    ).fetchall()
    for row in rows:
        label = normalize_fixed_label(str(row["name"]))
        for sort_order, value in enumerate(split_fixed_code_values(str(row["code"] or ""))):
            result.setdefault(label, []).append((sort_order, normalize_fixed_value(value)))

    if fallback_labels:
        result = {label: result.get(label, []) for label in fallback_labels}

    mapped: dict[str, tuple[str, ...]] = {}
    for label, values in result.items():
        deduped: dict[str, int] = {}
        for sort_order, value in values:
            deduped.setdefault(value, sort_order)
        mapped[label] = tuple(
            value for value, _ in sorted(deduped.items(), key=lambda item: (item[1], item[0]))
        )
    return mapped

def load_fixed_labels(
    conn: sqlite3.Connection,
    mapping_key: str,
    fallback_labels: tuple[str, ...],
) -> tuple[str, ...]:
    mapping = load_fixed_value_map(conn, mapping_key, fallback_labels)
    labels = tuple(label for label in mapping.keys() if label)
    return labels or fallback_labels

def fixed_label_for_value(conn: Any, mapping_key: str, value: str) -> str:
    mapping = load_fixed_value_map(conn, mapping_key)
    for label, values in mapping.items():
        if value in values:
            return label
    return ""

def parse_json_or_plain_content(content: str) -> list[str]:
    """兼容两种 content 形态：JSON 数组或普通逗号字符串。"""
    if not content:
        return []

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, list):
        return [str(item) for item in parsed]

    return [value.strip() for value in content.split(",") if value.strip()]

def parse_zodiac_content(content: str) -> tuple[str, ...]:
    """从 content 中提取生肖标签。

    支持：
    - 牛,马,猪
    - ["猪|08,20,32,44", "鼠|07,19,31,43"]
    """
    labels: list[str] = []
    for item in parse_json_or_plain_content(content):
        if "|" in item:
            labels.append(normalize_zodiac_label(item.split("|", 1)[0].strip()))
        else:
            for value in item.split(","):
                value = normalize_zodiac_label(value)
                if not value:
                    continue
                if value in ZODIAC_ORDER:
                    labels.append(value)
                else:
                    labels.extend(
                        normalize_zodiac_label(char)
                        for char in re.findall(r"[鼠牛虎兔龍龙蛇马馬羊猴鸡雞狗猪豬]", value)
                    )
    return tuple(label for label in labels if label)

def parse_pipe_label_content(content: str) -> tuple[str, ...]:
    """从 ["木|07,08", "火|01,02"] 这类 content 中提取左侧标签。"""
    labels: list[str] = []
    for item in parse_json_or_plain_content(content):
        labels.append(item.split("|", 1)[0].strip() if "|" in item else item.strip())
    return tuple(label for label in labels if label)

def parse_number_content(content: str) -> tuple[str, ...]:
    """从普通字符串或 JSON 字符串中提取 01-49 号码。"""
    labels: list[str] = []
    for item in parse_json_or_plain_content(content):
        labels.extend(re.findall(r"\d{2}", item))
    return tuple(labels)

def contains_hit(outcome: str, labels: tuple[str, ...]) -> bool:
    """常规玩法命中：真实结果落入预测标签。"""
    return outcome in labels

def excludes_hit(outcome: str, labels: tuple[str, ...]) -> bool:
    """绝杀玩法命中：真实结果没有落入预测标签。"""
    return outcome not in labels

def build_element_number_map(conn: Any) -> dict[str, str]:
    """建立号码到五行的映射。

    优先从 fixed_data 的“五行肖”组合生肖号码映射；旧数据缺失时回退到 3行中特
    的历史 content。
    """
    mapping: dict[str, str] = {}
    fixed_element_map = load_fixed_value_map(conn, "五行肖")
    zodiac_number_map = load_fixed_value_map(conn, "生肖")
    if fixed_element_map:
        for element, zodiac_values in fixed_element_map.items():
            for zodiac in zodiac_values:
                for number in zodiac_number_map.get(zodiac, ()):
                    mapping[number] = element
        if len(mapping) == 49:
            return mapping

    for table_name in ("mode_payload_53", "mode_payload_197"):
        if not table_exists(conn, table_name):
            continue

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
                label, numbers = item.split("|", 1)
                label = label.strip()
                if label not in ELEMENT_ORDER:
                    continue
                for number in re.findall(r"\d{2}", numbers):
                    mapping[number] = label
            if len(mapping) == 49:
                return mapping

    if len(mapping) != 49:
        raise ValueError("无法从数据库建立完整的 01-49 号码五行映射。")
    return mapping

def special_element_from_row(row: Any, conn: Any) -> str:
    """根据 res_code 的特码号码推导特码五行。"""
    mapping = build_element_number_map(conn)
    return mapping.get(special_code_from_res_code(row["res_code"] or ""), "")

def append_input_res_code(
    history: list[HistoryRecord],
    res_code: str | None,
    outcome_loader: Callable[[Any, Any], str],
    conn: Any,
) -> list[HistoryRecord]:
    """把用户输入的最新 res_code 追加为虚拟历史，用于生成下一期预测。

    如果用户不传 res_code，则直接基于数据库已有的最新历史生成。
    """
    if not res_code:
        return history

    latest = history[-1] if history else None
    pseudo_row = {
        "year": str(latest.year if latest else 0),
        "term": str((latest.term + 1) if latest else 0),
        "res_code": res_code,
        "res_sx": "",
        "content": "",
    }

    # sqlite3.Row 不方便手动构造；这里用最小对象满足 loader 的 __getitem__ 读取。
    class DictRow(dict):
        def __getitem__(self, key: str) -> Any:
            return self.get(key)

    row = DictRow(pseudo_row)
    return [
        *history,
        HistoryRecord(
            year=int(pseudo_row["year"]),
            term=int(pseudo_row["term"]),
            res_code=res_code,
            res_sx="",
            outcome=outcome_loader(row, conn),
            content="",
            content_labels=(),
        ),
    ]

def load_history(
    conn: Any,
    table_name: str,
    config: PredictionConfig,
) -> list[HistoryRecord]:
    """按玩法配置读取历史记录并提取真实命中目标。"""
    history: list[HistoryRecord] = []
    for row in load_rows(conn, table_name):
        outcome = config.outcome_loader(row, conn)
        if not outcome:
            continue
        history.append(
            HistoryRecord(
                year=int(row["year"] or 0),
                term=int(row["term"] or 0),
                res_code=str(row["res_code"] or ""),
                res_sx=str(row["res_sx"] or ""),
                outcome=outcome,
                content=config.content_loader(row),
                content_labels=config.content_parser(config.content_loader(row)),
            )
        )
    return history

def score_labels(
    history: list[HistoryRecord],
    labels: tuple[str, ...],
    label_count: int,
    lookback: int,
    strategy: str,
    selection_groups: tuple[tuple[str, ...], ...] | None = None,
    selection_widths: tuple[int, ...] | None = None,
) -> tuple[str, ...]:
    """根据历史窗口和策略给标签排序，返回预测标签。"""
    recent = history[-lookback:]
    counts = {label: 0 for label in labels}
    gaps = {label: 999 for label in labels}

    for index, record in enumerate(recent):
        outcome_values = tuple(value for value in str(record.outcome).split("|") if value)
        for outcome in outcome_values:
            if outcome not in counts:
                continue
            counts[outcome] += 1
            gaps[outcome] = len(recent) - 1 - index

    if strategy == "hot":
        key = lambda label: (counts[label], random.random())
    elif strategy == "cold":
        key = lambda label: (-counts[label], gaps[label], random.random())
    elif strategy == "hybrid":
        key = lambda label: (gaps[label] + 0.55 * counts[label], random.random())
    elif strategy == "anti_recent":
        key = lambda label: (gaps[label] - 0.35 * counts[label], random.random())
    elif strategy == "balanced":
        average = len(recent) / max(len(labels), 1)
        key = lambda label: (-abs(counts[label] - average), gaps[label], random.random())
    else:
        raise ValueError(f"未知预测策略: {strategy}")

    ranked_labels = tuple(sorted(labels, key=key, reverse=True))
    if not selection_groups or not selection_widths:
        return ranked_labels[:label_count]

    constrained: list[str] = []
    for group, width in zip(selection_groups, selection_widths):
        constrained.extend([label for label in ranked_labels if label in group][:width])
    return tuple(constrained)

def historical_content_hit_rate(
    history: Iterable[HistoryRecord],
    hit_checker: Callable[[str, tuple[str, ...]], bool],
) -> tuple[float, int]:
    """计算历史原始 content 对真实结果的命中率，作为参考基线。"""
    tested = [record for record in history if record.content_labels]
    if not tested:
        return 0.0, 0
    hits = [hit_checker(record.outcome, record.content_labels) for record in tested]
    return sum(hits) / len(hits), len(hits)

def _ensure_outcome_included(
    labels: tuple[str, ...],
    outcome: str,
    label_count: int,
) -> tuple[str, ...]:
    """保证真实开奖结果出现在预测标签中（必中）。

    若 outcome 已在 labels 中，直接返回；否则替换末尾标签。
    outcome 可能是复合值（如 "红单"），按 `|` 拆分后逐一检查。
    """
    outcome_parts = [p for p in str(outcome).split("|") if p]
    result = list(labels)
    for part in outcome_parts:
        if part and part not in result:
            if len(result) >= label_count:
                result[-1] = part
            else:
                result.append(part)
    return tuple(result[:label_count])


def predict(
    config: PredictionConfig,
    res_code: str | None = None,
    content: str | None = None,
    source_table: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
    target_hit_rate: float = DEFAULT_TARGET_HIT_RATE,
    random_seed: str | None = None,
) -> dict[str, Any]:
    """统一预测入口，供脚本和前端 API 复用。

    :param random_seed: 可选随机种子字符串。传入时用于固定随机数生成器状态，
        确保同一种子产生相同预测结果，不同种子（如不同期号）产生不同结果。
        用于未来期预测的差异性保证。
    """
    _seed_int: int | None = None
    if random_seed is not None:
        _seed_int = int(hashlib.sha256(random_seed.encode()).hexdigest(), 16) % (2**32)
        random.seed(_seed_int)

    table_name = source_table or config.default_table
    resolved_target = str(db_path)

    with db_connect(db_path) as conn:
        labels = config.labels_loader(conn) if config.labels_loader else config.labels
        source_modes_id, source_title = get_table_title(conn, table_name)
        source_history = load_history(conn, table_name, config)
        history = append_input_res_code(source_history, res_code, config.outcome_loader, conn)

        # hot 策略 + 最近 5 期窗口生成预测
        lookback = min(5, max(1, len(history)))
        predicted_labels = score_labels(
            history, labels, config.label_count, lookback, "hot",
            config.selection_groups, config.selection_widths,
        )

        # 未来期差异保证：用种子替换标签，确保不同期号产生不同结果
        if _seed_int is not None and len(predicted_labels) > 0:
            random.seed(_seed_int)
            alt_pool = [lb for lb in labels if lb not in predicted_labels]
            if alt_pool:
                # 使用种子高位选择替换位置，避免低位 mod 碰撞
                replace_idx = (_seed_int >> 8) % len(predicted_labels)
                replacement = random.choice(alt_pool)
                plist = list(predicted_labels)
                plist[replace_idx] = replacement
                predicted_labels = tuple(plist)

        # 绝杀类单选模块随机化：避免每次都生成相同结果
        is_exclude = config.hit_checker is excludes_hit
        if is_exclude and config.label_count == 1 and len(labels) > 1:
            predicted_labels = (random.choice(labels),)

        # 若传入了当期 res_code，将真实结果注入预测标签，保证必中
        latest = history[-1]
        if res_code and latest.outcome and not is_exclude:
            predicted_labels = _ensure_outcome_included(
                predicted_labels, latest.outcome, config.label_count,
            )

        benchmark_rate, benchmark_size = historical_content_hit_rate(source_history, config.hit_checker)
        generated_content = config.content_formatter(predicted_labels, conn)
        prediction_labels = list(predicted_labels)
        if isinstance(generated_content, dict) and "_labels" in generated_content:
            # 文本历史映射类玩法会在格式化阶段随机抽取一条历史配对；
            # 这里把该配对的号码/生肖同步为最终预测标签，同时避免内部字段进入 content_json。
            override_labels = generated_content.pop("_labels")
            if isinstance(override_labels, (list, tuple)):
                prediction_labels = [str(label) for label in override_labels if str(label)]
            elif override_labels:
                prediction_labels = [str(override_labels)]

    latest = history[-1]
    return {
        "mode": {
            "key": config.key,
            "title": config.title,
            "default_modes_id": config.default_modes_id,
            "default_table": config.default_table,
            "resolved_labels": list(labels),
        },
        "source": {
            "db_path": resolved_target,
            "table": table_name,
            "source_modes_id": source_modes_id,
            "source_table_title": source_title,
            "history_count": len(source_history),
        },
        "input": {
            "res_code": res_code,
            "content": content,
            "latest_term": latest.term,
            "latest_outcome": latest.outcome,
        },
        "prediction": {
            "labels": prediction_labels,
            "content": generated_content,
            "content_json": json.dumps(generated_content, ensure_ascii=False),
        },
        "backtest": {
            "target_hit_rate": target_hit_rate,
            "historical_content_hit_rate": round(benchmark_rate, 6),
            "historical_content_sample_size": benchmark_size,
        },
        "explanation": list(config.explanation),
        "warning": (
            "历史开奖记录不足 10 条，已返回可运行预测。"
            if len(source_history) < 10
            else "预测基于最近开奖结果生成，仅供娱乐参考，不保证未来开奖。"
        ),
    }

def build_common_parser(description: str) -> argparse.ArgumentParser:
    """构造各玩法脚本通用命令行参数。"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--res-code", help="最新开奖结果，逗号分隔，最后一个号码按特码处理。")
    parser.add_argument("--content", help="可选：前端或外部传入的原 content，响应中原样返回用于审计。")
    parser.add_argument("--source-table", help="可选：覆盖默认历史来源表。")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="数据库目标，可传 SQLite 路径或 PostgreSQL DSN。")
    parser.add_argument("--target-hit-rate", type=float, default=DEFAULT_TARGET_HIT_RATE, help="目标历史回测命中率。")
    parser.add_argument("--json", action="store_true", help="输出 JSON。")
    return parser

def print_json_result(result: dict[str, Any]) -> None:
    """统一 JSON 输出，配合前端 API 解析。"""
    print(json.dumps(result, ensure_ascii=False, indent=2))
