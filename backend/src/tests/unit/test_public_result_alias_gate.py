from copy import deepcopy

import pytest

from db import connect
from helpers import apply_public_result_gate


@pytest.mark.parametrize("actual, expected", [
    ({"special_ball": {"value": "14", "zodiac": "马"}, "result_balls": [{"value": "08"}]}, {"special_ball": None, "result_balls": []}),
    ({"resultText": "马14准", "hit_text": "马14", "is_hit": True}, {"resultText": "待开奖", "hit_text": "待开奖", "is_hit": None}),
    ({"result": {"value": "14", "zodiac": "马"}}, {"result": {"value": "", "zodiac": ""}}),
])
def test_unknown_alias_outcomes_fail_closed(tmp_path, actual, expected):
    payload = {"rows": [{**actual, "content": "候选12,19", "codes": ["12", "19"]}]}
    original = deepcopy(payload)
    with connect(str(tmp_path / "aliases.db")) as conn:
        result = apply_public_result_gate(conn, payload, default_lottery_type_id=3)
    row = result["rows"][0]
    for key, value in expected.items():
        assert row[key] == value
    assert row["content"] == "候选12,19"
    assert row["codes"] == ["12", "19"]
    assert payload == original
