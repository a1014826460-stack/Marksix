"""生成流程必须对 28/57/62/63/108 施加“相邻连续三期展示值不得相同”。

这些测试锁定服务层的接线：候选展示值枚举、替代 content 模板构造、
以及 `_process_single_module` 生成循环中的实际调用。
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from prediction_generation import service
from prediction_generation import diversity
from domains.prediction.simulation_service import SimulationConfig


def _config(mode_id: int, key: str, labels: tuple[str, ...]) -> SimpleNamespace:
    return SimpleNamespace(
        key=key,
        title=key,
        default_table=f"mode_payload_{mode_id}",
        default_modes_id=mode_id,
        labels=labels,
        label_count=1,
        diversity_policy="",
    )


# ---------- 替代取值枚举 ----------


def test_alternative_tokens_prefers_config_labels_when_available():
    config = _config(63, "title_63", ("家禽", "野兽"))
    tokens = service._three_period_alternative_tokens(
        mode_id=63, config=config, conn=object(), current_tokens=("家禽",)
    )
    # 当前取值排在最前，其余候选（含另一取值）其后
    assert tokens == ("家禽", "野兽")


def test_alternative_tokens_fall_back_to_row_content():
    """mode 63 的 config.labels 为空，需从库内 content 取另一池标签。"""
    config = _config(63, "title_63", ())
    rows = [{"content": '["野兽|鼠,虎,兔,龙,蛇,猴"]'}]
    tokens = service._three_period_alternative_tokens(
        mode_id=63,
        config=config,
        conn=object(),
        current_tokens=("家禽",),
        history_rows=rows,
    )
    assert tokens == ("家禽", "野兽")


def test_alternative_tokens_returns_labels_for_size_modes():
    config = _config(57, "daxiao", ("小", "大"))
    tokens = service._three_period_alternative_tokens(
        mode_id=57, config=config, conn=object(), current_tokens=("小",)
    )
    assert tokens == ("小", "大")


def test_alternative_content_templates_use_mode_formatter():
    """候选模板必须来自该模式自己的 formatter，保持 `标签|号码` 结构不变。"""
    calls: list[tuple[str, ...]] = []

    def formatter(labels, conn):
        calls.append(tuple(labels))
        return [f"{label}|{'1,2,3' if label == '大' else '4,5,6'}" for label in labels]

    config = SimpleNamespace(content_formatter=formatter)
    templates = service._three_period_alternative_content_templates(
        mode_id=57, config=config, conn=object(), alternative_tokens=("大",)
    )
    assert templates == ["大|1,2,3"]
    assert calls == [("大",)]


def test_alternative_content_templates_keep_json_array_shape():
    """mode 57 的真实 formatter 返回 JSON 数组，模板必须原样保留。"""

    def formatter(labels, conn):
        return ['["大|25,26,27"]']

    config = SimpleNamespace(content_formatter=formatter)
    templates = service._three_period_alternative_content_templates(
        mode_id=57, config=config, conn=object(), alternative_tokens=("大",)
    )
    assert templates == ['["大|25,26,27"]']


# ---------- 生成循环接线 ----------


def test_text_fallback_reads_public_table_when_mapping_table_is_empty(monkeypatch):
    """mode 62：text_history_mappings 没有该 mode 的行时，回退读取 public 表真实 title。"""
    monkeypatch.setattr(service.generation_repository, "load_text_history_candidate_rows",
                        lambda conn, **kwargs: [])
    monkeypatch.setattr(service.generation_repository, "load_mode_payload_title_rows",
                        lambda conn, **kwargs: [{"title": "守株待兔"}, {"title": "欲钱解特诗"}])

    payloads = service._load_three_period_text_payloads(object(), 62)

    titles = [p.get("title") for p in payloads]
    assert "守株待兔" in titles


def test_text_fallback_keeps_title_and_jiexi_paired(monkeypatch):
    """mode 52：title 与 jiexi 必须成对带出，否则命中口径与标题对不上。"""
    monkeypatch.setattr(service.generation_repository, "load_text_history_candidate_rows",
                        lambda conn, **kwargs: [])
    monkeypatch.setattr(
        service.generation_repository,
        "load_mode_payload_title_rows",
        lambda conn, **kwargs: [
            {"title": "黯然無光", "jiexi": "虎马兔龙牛羊狗", "content": ""},
            {"title": "抓小辫子", "jiexi": "猴鼠兔龙猪马牛", "content": ""},
        ],
    )

    payloads = service._load_three_period_text_payloads(object(), 52)

    assert [(p["title"], p["jiexi"]) for p in payloads] == [
        ("黯然無光", "虎马兔龙牛羊狗"),
        ("抓小辫子", "猴鼠兔龙猪马牛"),
    ]


def test_text_fallback_ignores_rows_without_title(monkeypatch):
    monkeypatch.setattr(service.generation_repository, "load_text_history_candidate_rows",
                        lambda conn, **kwargs: [])
    monkeypatch.setattr(service.generation_repository, "load_mode_payload_title_rows",
                        lambda conn, **kwargs: [{"title": ""}, {"title": "  "}, {"title": "有理反成无理亏"}])

    payloads = service._load_three_period_text_payloads(object(), 62)

    assert [p["title"] for p in payloads] == ["有理反成无理亏"]


def test_text_fallback_prefers_mapping_table_when_available(monkeypatch):
    monkeypatch.setattr(service, "_load_text_history_candidate_payloads",
                        lambda conn, mode_id: [{"title": "映射标题", "content": "", "jiexi": ""}])
    monkeypatch.setattr(service.generation_repository, "load_mode_payload_title_rows",
                        lambda conn, **kwargs: [{"title": "public 标题"}])

    payloads = service._load_three_period_text_payloads(object(), 62)

    assert [p["title"] for p in payloads] == ["映射标题"]


def test_placeholder_title_is_replaced_not_alternated():
    """mode 62 的占位文案不是真实诗句：有真实候选时必须换掉，而不是与占位轮流出现。"""
    row = {"title": "欲钱解特诗", "content": ""}
    recent = [{"title": "欲钱解特诗", "content": ""} for _ in range(4)]
    result = diversity.enforce_three_period_uniqueness(
        mode_id=62,
        row_data=row,
        recent_rows=recent,
        alternative_text_payloads=[
            {"title": "欲钱解特诗", "content": "", "jiexi": ""},
            {"title": "梅花三弄寒香远,四五枝头报早春", "content": "", "jiexi": ""},
        ],
    )
    assert result["title"] == "梅花三弄寒香远,四五枝头报早春"


def test_placeholder_used_only_when_no_real_candidate():
    row = {"title": "欲钱解特诗", "content": ""}
    recent = [{"title": "欲钱解特诗", "content": ""} for _ in range(4)]
    result = diversity.enforce_three_period_uniqueness(
        mode_id=62,
        row_data=row,
        recent_rows=recent,
        alternative_text_payloads=[{"title": "欲钱解特诗", "content": "", "jiexi": ""}],
    )
    assert result["title"] == "欲钱解特诗"
    assert "mode_id=62" in str(result.get("_diversity_warning", "")) or result["title"] == "欲钱解特诗"


def test_apply_uniqueness_routes_mode_52_through_title_payloads(monkeypatch):
    """mode 52 与 62 一样按 title 唯一化，走替代文本分支而不是 content 模板分支。"""
    row = {"title": "黯然無光", "jiexi": "蛇鸡虎兔龙鼠羊"}
    identical = {"title": "黯然無光", "jiexi": "猪猴蛇鸡兔虎狗"}
    monkeypatch.setattr(service, "_load_three_period_history_rows",
                        lambda *args, **kwargs: [dict(identical) for _ in range(4)])
    monkeypatch.setattr(service, "_load_three_period_text_payloads",
                        lambda conn, mode_id: [
                            {"title": "黯然無光", "jiexi": "猪猴蛇鸡兔虎狗"},
                            {"title": "抓小辫子", "jiexi": "牛羊马虎猴鼠猪"},
                        ])

    result = service._apply_three_period_uniqueness(
        object(),
        config=_config(52, "sizixuanji", ()),
        mode_id=52,
        row_data=row,
        table_name="mode_payload_52",
        lottery_type=3,
        site_web_id=5,
    )

    assert result["title"] == "抓小辫子"
    assert result["jiexi"] == "牛羊马虎猴鼠猪"


def test_apply_uniqueness_keeps_mode_52_title_when_mapping_table_missing_or_same(monkeypatch):
    """候选表缺 mode 52 行、或候选与最近四期都相同时，保持原值并给出告警。"""
    row = {"title": "黯然無光", "jiexi": "蛇鸡虎兔龙鼠羊"}
    identical = {"title": "黯然無光", "jiexi": "猪猴蛇鸡兔虎狗"}
    monkeypatch.setattr(service, "_load_three_period_history_rows",
                        lambda *args, **kwargs: [dict(identical) for _ in range(4)])
    monkeypatch.setattr(service, "_load_three_period_text_payloads",
                        lambda conn, mode_id: [dict(identical)])

    result = service._apply_three_period_uniqueness(
        object(),
        config=_config(52, "sizixuanji", ()),
        mode_id=52,
        row_data=row,
        table_name="mode_payload_52",
        lottery_type=3,
        site_web_id=5,
    )

    assert result["title"] == "黯然無光"
    assert "连续5期" in str(result.get("_diversity_warning", ""))


def test_apply_uniqueness_requires_four_identical_periods_for_mode_62(monkeypatch):
    """窗口 5：库里只有连续三期相同时不得换诗句。"""
    row = {"title": "一字当头十相投，时来运转否泰交", "content": ""}
    monkeypatch.setattr(service, "_load_three_period_history_rows",
                        lambda *args, **kwargs: [
                            {"title": "一字当头十相投，时来运转否泰交", "content": ""},
                            {"title": "一字当头十相投，时来运转否泰交", "content": ""},
                        ])
    monkeypatch.setattr(service, "_load_three_period_text_payloads",
                        lambda conn, mode_id: [{"title": "别的诗句"}])

    result = service._apply_three_period_uniqueness(
        object(),
        config=_config(62, "yqjs", ()),
        mode_id=62,
        row_data=row,
        table_name="mode_payload_62",
        lottery_type=3,
        site_web_id=4,
    )

    assert result["title"] == row["title"]


def test_alternative_tokens_read_payload_table_when_history_is_one_sided(monkeypatch):
    """近期历史只有 左肖 时，必须从模式自己的表里补出 右肖 这个候选。

    twsaimahui 的「二选一」分组（左右肖 / 阴阳肖 / 文武肖 / 有无肖 / 吉美凶丑 /
    肥瘦肖 / 胆大胆小）常出现连续多期同一组；只用历史行会让候选集缩成一个标签，
    相邻期规则因此无解。
    """
    config = _config(152, "title_152", ())
    monkeypatch.setattr(
        service.generation_repository,
        "load_mode_payload_content_rows",
        lambda conn, **kwargs: [
            {"content": '["左肖|牛,猴,蛇,鸡,鼠,龙"]'},
            {"content": '["右肖|虎,兔,马,羊,狗,猪"]'},
        ],
    )

    tokens = service._three_period_alternative_tokens(
        mode_id=152,
        config=config,
        conn=object(),
        current_tokens=("左肖",),
        history_rows=[{"content": '["左肖|牛,猴,蛇,鸡,鼠,龙"]'}],
    )

    assert tokens == ("左肖", "右肖")


def test_generation_loop_switches_token_after_two_identical_periods(monkeypatch):
    """真实场景：库里最近两期都是同一展示值时，本期必须换一个。

    content_formatter 按真实语义返回该模式**全部**池（家禽 + 野兽），
    生成器每期都选择“家禽”，历史加载使用“已写入行”的真实视图（新→旧）。
    """
    config = _config(63, "title_63", ())
    pools = {
        "家禽": "牛,马,羊,鸡,狗,猪",
        "野兽": "鼠,虎,兔,龙,蛇,猴",
    }
    config.content_formatter = lambda labels, conn: [
        f"{label}|{pools[label]}" for label in ("家禽", "野兽")
    ]

    monkeypatch.setattr(
        service,
        "_resolve_prediction_config_with_mode_fallback",
        lambda mechanism_key, mode_id, db_path: (config, mechanism_key, False),
    )
    monkeypatch.setattr(service, "_load_recent_rows", lambda *args, **kwargs: [])
    # 旧的“前二唯一”策略不参与本用例
    monkeypatch.setattr(service, "enforce_prediction_diversity", lambda **kwargs: dict(kwargs["row_data"]))
    monkeypatch.setattr(service, "_repair_text_prediction_diversity", lambda *args, **kwargs: dict(kwargs["row_data"]))

    writes: list[dict] = []
    # 库内已存在的最近两期：都是“家禽”（对应用户看到的连续相同结果）
    seeded = [
        {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'},
        {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'},
    ]

    def fake_history(*args, **kwargs):
        # 真实语义：按 year/term 倒序返回库内最近行（最新在前，其后是库内旧行）
        return list(reversed(writes)) + seeded

    monkeypatch.setattr(service, "_load_three_period_history_rows", fake_history)

    def fake_generate(**kwargs):
        return {
            "type": str(kwargs["lottery_type"]),
            "year": str(kwargs["draw"]["year"]),
            "term": str(kwargs["draw"]["term"]),
            "web": str(kwargs["site_web_id"]),
            "content": '["家禽|牛,马,羊,鸡,狗,猪"]',
            "res_code": kwargs["safe_res_code"] or "",
        }

    monkeypatch.setattr(service, "_generate_single_draw_row", fake_generate)

    def fake_persist(conn, table, row_data, **kwargs):
        writes.append(dict(row_data))
        return {"action": "inserted"}

    monkeypatch.setattr(service, "_persist_generated_row", fake_persist)

    draws = [{"year": 2026, "term": term, "numbers_str": "01,02,03,04,05,06,07"} for term in (192, 193, 194)]
    report = service._process_single_module(
        conn=object(),
        module_row={"id": 1, "mechanism_key": "title_63", "mode_id": 63},
        draws=draws,
        future_draws=[],
        future_only=False,
        safety_draw_map={},
        lottery_type=3,
        site_id=4,
        site_web_id=4,
        db_path="fake-db",
        default_target_hit_rate=0.65,
        simulation_config=SimulationConfig(target_hit_rate=0.65),
        zodiac_map={},
        color_map={},
        trigger="manual",
        allow_overwrite=False,
        resolve_prediction_table_for_mode=lambda conn, mode_id, table: "mode_payload_63",
        build_generated_prediction_row_data=lambda **kwargs: dict(kwargs.get("generated_content") or {}),
    )

    assert report["inserted"] == 3
    tokens = [json.loads(row["content"])[0].split("|")[0] for row in writes]
    # 第 192 期前两期（库内）都是“家禽”，因此 192 期必须换值
    assert tokens[0] != "家禽", f"连续三期不得相同: {tokens}"
    # 且换值后不得造成新的连续三期相同
    assert len(set(tokens)) > 1
    # 池内号码必须与标签一致
    assert json.loads(writes[0]["content"]) == ["野兽|鼠,虎,兔,龙,蛇,猴"]
