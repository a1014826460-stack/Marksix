from __future__ import annotations

import json
import random
from typing import Any, Callable

from domains.prediction import predict_repository
from predict._db_helpers import _table_column_list
from predict.common import quote_identifier, table_exists
from predict.number_maps import TAIL_NUMBER_MAP


text_pool_sources: dict[str, tuple[str, str]] = {}
text_history_mapping_table = "text_history_mappings"
text_history_column_preference: tuple[str, ...] = ("content", "title", "jiexi")

table_output_columns: Callable[[Any, str, tuple[str, ...]], tuple[str, ...]] = lambda _conn, _table_name, columns: columns
text_history_preferred_column: Callable[[Any, int], str | None] = lambda _conn, _modes_id: None
random_text_history_mapping_row: Callable[[Any, int, tuple[str, ...], str | None], Any | None] = (
    lambda _conn, _modes_id, _selected_zodiacs=(), _text_column=None: None
)
text_history_row_payload: Callable[[Any], dict[str, Any]] = lambda row: dict(row) if row else {}


def format_text_history_mapping(title: str, modes_id: int, text_column: str | None = None):
    def formatter(labels: tuple[str, ...], conn: Any) -> dict[str, Any]:
        row = random_text_history_mapping_row(conn, modes_id, labels, text_column)
        if not row:
            return {
                "title": title,
                "content": title,
                "code": "",
                "sx": "",
                "_labels": list(labels),
            }

        result = text_history_row_payload(row)
        if not result:
            source_text_column = text_column or "content"
            result[source_text_column] = title
        result["_labels"] = list(labels)
        return result

    return formatter


def random_text_pool_row(conn: Any, mapping_key: str) -> dict[str, str] | None:
    source = text_pool_sources.get(mapping_key)
    if not source:
        return None
    table_name, text_column = source
    if not table_exists(conn, table_name):
        return None
    columns = list(_table_column_list(conn, table_name))
    if text_column not in columns:
        return None

    selected_columns = [column for column in ("title", "content", "jiexi", "code") if column in columns]
    if not selected_columns:
        return None

    return predict_repository.load_random_distinct_text_pool_row(
        conn,
        table_name,
        text_column=text_column,
        selected_columns=tuple(selected_columns),
    )


def format_text_pool_jiexi(title: str, mapping_key: str):
    def formatter(labels: tuple[str, ...], conn: Any) -> dict[str, Any]:
        source = text_pool_sources.get(mapping_key)
        if source:
            table_name, text_column = source
            modes_id = int(table_name.rsplit("_", 1)[-1])
            output_columns = table_output_columns(conn, table_name, ("title", "content", "jiexi"))
            row = random_text_history_mapping_row(conn, modes_id, labels, text_column)
            if row:
                mapped_payload = text_history_row_payload(row)
                result: dict[str, Any] = {}
                if "title" in output_columns:
                    result["title"] = str(mapped_payload.get("title") or title)
                if "content" in output_columns:
                    content_value = str(mapped_payload.get("content") or "")
                    result["content"] = content_value or f"{title}|{','.join(labels)}"
                if "jiexi" in output_columns:
                    jiexi_value = str(mapped_payload.get("jiexi") or "")
                    result["jiexi"] = jiexi_value or "".join(labels)
                if not result:
                    result[text_column] = title
                result["_labels"] = list(labels)
                return result

        row = random_text_pool_row(conn, mapping_key)
        table_name, text_column = source if source else ("", "content")
        output_columns = table_output_columns(conn, table_name, ("title", "content", "jiexi"))
        result: dict[str, Any] = {}
        if "title" in output_columns:
            result["title"] = (row or {}).get("title") or title
        if "content" in output_columns:
            result["content"] = (row or {}).get("content") or f"{title}|{','.join(labels)}"
        if "jiexi" in output_columns:
            result["jiexi"] = (row or {}).get("jiexi") or "".join(labels)
        if not result:
            result[text_column] = title
        return result

    return formatter


def format_humor_tail_groups(labels: tuple[str, ...], conn: Any) -> dict[str, Any]:
    mapped = random_text_history_mapping_row(conn, 59, (), "content")

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

    row = random_text_pool_row(conn, "独家幽默")
    return {
        "title": (row or {}).get("title") or "预测独家幽默",
        "content": (row or {}).get("content") or f"独家幽默：本期参考 {','.join(labels)}。",
        "code": humor_code,
    }


def format_juzi_title(labels: tuple[str, ...], conn: Any) -> dict[str, Any]:
    mapped = random_text_history_mapping_row(conn, 62, (), "title")
    if mapped and "title" in mapped.keys():
        return {"title": str(mapped["title"] or ""), "_labels": list(labels)}
    return {"title": "欲钱解特诗", "_labels": list(labels)}
