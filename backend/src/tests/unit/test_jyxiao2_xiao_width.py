"""mode 251「家野两肖」的候选宽度契约。

厂商原始 `mode_payload_251`（web 1/5）的列结构是：
    title = `家禽|牛,马,羊,鸡,狗,猪`（组名|组成员，**这张表没有 content 列**）
    xiao  = `蛇,龙`（两肖，宽度恒为 2）

历史生成的 bug：宽度推断用 `parse_pipe_label_content(title)`，而 title 的逗号右侧是
**分类成员**不是候选标签，于是被按逗号拆成 6 个标签，每期生成 6 肖写进 xiao，
前台渲染成「家禽+6肖」。这里锁定「候选宽度必须取 xiao 列」的契约。
"""
from __future__ import annotations

from db import connect
from predict.mechanisms import build_title_prediction_configs


def _build_config(tmp_path, title_value: str, xiao_values: list[str]):
    db_path = str(tmp_path / "jyxiao2_width.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY,
                table_name TEXT NOT NULL,
                title TEXT,
                record_count INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE mode_payload_251 (
                year TEXT,
                term TEXT,
                web INTEGER,
                type INTEGER,
                title TEXT,
                xiao TEXT,
                res_code TEXT,
                res_sx TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO mode_payload_tables (modes_id, table_name, title, record_count) VALUES (?, ?, ?, ?)",
            (251, "mode_payload_251", "家野两肖", len(xiao_values)),
        )
        for index, xiao_value in enumerate(xiao_values):
            conn.execute(
                """
                INSERT INTO mode_payload_251 (year, term, web, type, title, xiao, res_code, res_sx)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026",
                    str(300 - index),
                    6,
                    3,
                    title_value,
                    xiao_value,
                    "01,02,03,04,05,06,07",
                    "龙,鸡,马,羊,狗,鼠,鼠",
                ),
            )
        conn.commit()
    return build_title_prediction_configs(db_path)["title_251"]


def test_jyxiao2_width_comes_from_xiao_column(tmp_path):
    """title 的成员列表（6 项）不能当成候选宽度；宽度取 xiao 列（两肖 = 2）。"""
    config = _build_config(
        tmp_path,
        "家禽|牛,马,羊,鸡,狗,猪",
        ["蛇,龙", "猪,牛", "猴,兔"],
    )
    assert config.label_count == 2
    # content_loader 只按 xiao 列计算命中候选。
    assert config.content_loader({"title": "家禽|牛,马,羊,鸡,狗,猪", "xiao": "蛇,龙"}) == "蛇,龙"


def test_jyxiao2_width_follows_wild_group_rows(tmp_path):
    """两种分组行（家禽 / 野兽）共用同一宽度。"""
    config = _build_config(
        tmp_path,
        "野兽|鼠,虎,兔,龙,蛇,猴",
        ["猪,马", "鸡,牛"],
    )
    assert config.label_count == 2
    assert config.content_loader({"title": "野兽|鼠,虎,兔,龙,蛇,猴", "xiao": "猪,马"}) == "猪,马"
