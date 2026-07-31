from db import auto_increment_primary_key, connect
from domains.prediction.generation_rules import get_generation_rule
from predict.mechanisms import get_prediction_config


def test_twjsz666_exact_homepage_modes_preserve_vendor_cardinality():
    expected = {
        "three_head_four_tail": (492, 7),
        "selected_22_codes": (493, 22),
        "steady_kill_7_codes": (494, 7),
        "expert_publications": (495, 14),
    }

    for key, (mode_id, label_count) in expected.items():
        config = get_prediction_config(key)
        assert config.default_modes_id == mode_id
        assert config.default_table == f"mode_payload_{mode_id}"
        assert config.label_count == label_count


def test_twjsz666_number_modes_keep_inclusion_and_exclusion_rules_separate():
    selected = get_prediction_config("selected_22_codes")
    kill = get_prediction_config("steady_kill_7_codes")

    assert selected.content_formatter(tuple(f"{value:02d}" for value in range(1, 23)), None) == ",".join(
        f"{value:02d}" for value in range(1, 23)
    )
    assert selected.hit_checker("22", tuple(f"{value:02d}" for value in range(1, 23))) is True
    assert kill.hit_checker("08", ("01", "02", "03", "04", "05", "06", "07")) is True
    assert kill.hit_checker("07", ("01", "02", "03", "04", "05", "06", "07")) is False


def test_twjsz666_three_head_four_tail_keeps_two_structured_dimensions():
    config = get_prediction_config("three_head_four_tail")
    labels = ("头:0头", "头:1头", "头:2头", "尾:0尾", "尾:1尾", "尾:2尾", "尾:3尾")

    content = config.content_formatter(labels, None)

    assert content == '{"heads":["0头","1头","2头"],"tails":["0尾","1尾","2尾","3尾"]}'
    assert config.hit_checker("头:2头|尾:3尾", labels) is True
    assert config.hit_checker("头:2头|尾:8尾", labels) is False


def test_twjsz666_exact_mode_tables_are_bootstrapped(tmp_path):
    from database.schema.legacy import ensure_twjsz666_prediction_tables

    db_path = str(tmp_path / "twjsz666_exact_modes.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY, filename TEXT, title TEXT,
                table_name TEXT, record_count INTEGER, is_image INTEGER,
                is_text INTEGER, created_at TEXT, updated_at TEXT
            )
            """
        )
        ensure_twjsz666_prediction_tables(conn, auto_increment_primary_key("id", conn.engine))

        for mode_id in (492, 493, 494, 495):
            assert "content" in set(conn.table_columns(f"mode_payload_{mode_id}"))


def test_twjsz666_exact_modes_have_verified_generation_rules():
    assert get_generation_rule(get_prediction_config("three_head_four_tail")).rule_id == "head_tail"
    assert get_generation_rule(get_prediction_config("selected_22_codes")).rule_id == "number"
    assert get_generation_rule(get_prediction_config("steady_kill_7_codes")).rule_id == "number_exclusion"
