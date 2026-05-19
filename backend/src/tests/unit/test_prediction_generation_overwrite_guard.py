from __future__ import annotations

import json
import re

from prediction_generation import service


def test_persist_generated_row_skips_existing_when_overwrite_disabled(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        service,
        "find_existing_created_row",
        lambda conn, table_name, row_data: {"id": "c7", "created_at": "2026-05-14T00:00:00Z"},
    )
    monkeypatch.setattr(
        service,
        "upsert_created_prediction_row",
        lambda conn, table_name, row_data: calls.append("upsert") or {"action": "updated"},
    )

    result = service._persist_generated_row(
        object(),
        "mode_payload_44",
        {"type": "3", "year": "2026", "term": "133", "web": "4", "content": "old"},
        allow_overwrite=False,
    )

    assert result["action"] == "skipped_existing"
    assert result["id"] == "c7"
    assert calls == []


def test_persist_generated_row_allows_admin_overwrite(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        service,
        "find_existing_created_row",
        lambda conn, table_name, row_data: {"id": "c7", "created_at": "2026-05-14T00:00:00Z"},
    )
    monkeypatch.setattr(
        service,
        "upsert_created_prediction_row",
        lambda conn, table_name, row_data: calls.append("upsert") or {"action": "updated"},
    )

    result = service._persist_generated_row(
        object(),
        "mode_payload_44",
        {"type": "3", "year": "2026", "term": "133", "web": "4", "content": "new"},
        allow_overwrite=True,
    )

    assert result["action"] == "updated"
    assert calls == ["upsert"]


def test_generate_mode_331_row_persists_x7m14(monkeypatch):
    monkeypatch.setattr(
        service,
        "predict",
        lambda **kwargs: {
            "prediction": {
                "labels": ["06", "18", "21", "09", "44", "20", "12", "24", "01", "49", "43", "19", "39", "03"],
                "content": {"title": "示例标题", "content": "示例内容"},
            }
        },
    )

    row_data = service._generate_mode_331_row(
        draw={"year": 2026, "term": 131},
        is_future=False,
        safe_res_code="01,02,03,04,05,06,07",
        lottery_type=3,
        site_web_id=4,
        config=object(),
        table_name="mode_payload_331",
        db_path="fake-db",
        default_target_hit_rate=0.65,
        zodiac_map={
            "01": "马", "03": "龙", "06": "牛", "09": "狗", "12": "羊", "18": "牛", "19": "鼠",
            "20": "猪", "21": "狗", "24": "羊", "39": "龙", "43": "鼠", "44": "猪", "49": "马",
            "02": "蛇", "04": "兔", "05": "虎", "07": "鼠", "08": "猪", "10": "鸡", "11": "猴",
            "13": "马", "14": "蛇", "15": "龙", "16": "兔", "17": "虎", "22": "鸡", "23": "猴",
            "25": "马", "26": "蛇", "27": "龙", "28": "兔", "29": "虎", "30": "牛", "31": "鼠",
            "32": "猪", "33": "狗", "34": "鸡", "35": "猴", "36": "羊", "37": "马", "38": "蛇",
            "40": "兔", "41": "虎", "42": "牛", "45": "狗", "46": "鸡", "47": "猴", "48": "羊",
        },
        build_row=lambda **kwargs: {
            "type": kwargs["lottery_type"],
            "year": kwargs["year"],
            "term": kwargs["term"],
            "web": kwargs["web_value"],
            **dict(kwargs["generated_content"]),
        },
    )

    parsed = json.loads(row_data["x7m14"])
    assert len(parsed) == 7
    assert all(
        re.fullmatch(r"(鼠|牛|虎|兔|龙|蛇|马|羊|猴|鸡|狗|猪)\|\d{2},\d{2}", item)
        for item in parsed
    )
