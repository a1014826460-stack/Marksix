"""Exercise the read-only reveal probe without HTTP or a database."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest


SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "check-latest-draw-reveal.py"
spec = importlib.util.spec_from_file_location("draw_reveal_probe", SCRIPT)
probe = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(probe)

ANCHOR = "2026-10-07 22:32:01"
ANCHOR_SECONDS = 1791383521.0


def sample(count=1, *, issue="2026280", elapsed=0, anchor=ANCHOR):
    return {
        "current_issue": issue,
        "draw_time": ANCHOR,
        "result_balls": [{"value": f"SECRET_BALL_{i}"} for i in range(min(count, 6))],
        "special_ball": {"value": "SECRET_SPECIAL"} if count == 7 else None,
        "revealed_count": count,
        "total_balls": 7,
        "reveal_interval_seconds": 25,
        "reveal_start": anchor,
        "server_now": ANCHOR_SECONDS + elapsed,
        "is_complete": count == 7,
        "next_reveal_at": "" if count == 7 else "2026-10-07 22:32:26",
    }


class Clock:
    def __init__(self, now=ANCHOR_SECONDS):
        self.now = now
        self.elapsed = 0.0

    def time(self):
        return self.now + self.elapsed

    def monotonic(self):
        return self.elapsed

    def sleep(self, duration):
        self.elapsed += duration


def run_probe(monkeypatch, payloads, **overrides):
    args = argparse.Namespace(
        base_url="http://local.invalid",
        lottery_type=3,
        duration=0.6,
        interval=0.5,
        seed_local=False,
        seed_lottery_type=3,
        database_url="",
        expected_issue=None,
        jsonl=None,
    )
    for key, value in overrides.items():
        setattr(args, key, value)
    clock = Clock(overrides.get("clienttime", ANCHOR_SECONDS))
    monkeypatch.setattr(probe.time, "time", clock.time)
    monkeypatch.setattr(probe.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(probe.time, "sleep", clock.sleep)
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda *_: args)
    fetched = []

    def fetch(*_args, **_kwargs):
        payload = payloads[min(len(fetched), len(payloads) - 1)]
        fetched.append(payload)
        if isinstance(payload, Exception):
            raise payload
        return payload

    monkeypatch.setattr(probe, "_fetch", fetch)
    return probe.main(), fetched


def test_previous_complete_issue_does_not_end_target_sampling(monkeypatch):
    old = sample(7, issue="2026279", elapsed=150)
    target = sample(7, elapsed=150)
    result, fetched = run_probe(monkeypatch, [old, target], expected_issue="2026280")
    assert len(fetched) == 2
    assert result == 0


def test_unobserved_target_completion_is_incomplete(monkeypatch, capsys):
    result, _ = run_probe(monkeypatch, [sample(1)], expected_issue="2026280")
    assert result != 0
    assert "incomplete" in capsys.readouterr().out.lower()


def test_seven_balls_at_125_seconds_is_rejected(monkeypatch):
    result, _ = run_probe(monkeypatch, [sample(7, elapsed=125)], clienttime=ANCHOR_SECONDS + 125)
    assert result == 1


def test_server_clock_prevents_fast_client_from_allowing_early_special(monkeypatch):
    result, _ = run_probe(monkeypatch, [sample(7, elapsed=0)], clienttime=ANCHOR_SECONDS + 3600)
    assert result == 1


def test_numbers_without_valid_anchor_cannot_pass(monkeypatch):
    payload = sample(7, anchor="invalid", elapsed=150)
    payload["draw_time"] = ""
    result, _ = run_probe(monkeypatch, [payload])
    assert result == 1


def test_probe_rejects_early_opened_at_before_planned_draw():
    payload = sample(1)
    payload["reveal_start"] = "2026-10-07 22:30:01"
    payload["server_now"] = ANCHOR_SECONDS - 1
    checked = probe.validate_sample(payload, lottery_type=3, clienttime=ANCHOR_SECONDS + 600)
    assert checked["record"]["allowed_count"] == 0
    assert checked["record"]["anchor"] == ANCHOR
    assert checked["errors"]


@pytest.mark.parametrize("preferred", ["invalid", "2026-02-30 22:32:01", "2026-10-07 24:00:00"])
def test_probe_invalid_preferred_anchor_cannot_borrow_valid_planned_time(preferred):
    payload = sample(7, anchor=preferred, elapsed=150)
    checked = probe.validate_sample(payload, lottery_type=3, clienttime=ANCHOR_SECONDS + 600)
    assert checked["record"]["anchor"] is None
    assert checked["errors"]
    assert not checked["complete"]


def test_probe_accepts_canonical_t_separator_from_a_paced_payload():
    payload = sample(7, anchor="2026-10-07T22:32:01", elapsed=150)
    payload["draw_time"] = "2026-10-07T22:32:00"
    checked = probe.validate_sample(payload, lottery_type=3, clienttime=ANCHOR_SECONDS)
    assert checked["record"]["anchor"] == ANCHOR
    assert checked["complete"]


@pytest.mark.parametrize("planned", [None, "", "invalid", "2026-02-30 22:32:00"])
def test_probe_valid_preferred_anchor_cannot_borrow_invalid_planned_time(planned):
    payload = sample(7, elapsed=150)
    payload["draw_time"] = planned
    checked = probe.validate_sample(payload, lottery_type=3, clienttime=ANCHOR_SECONDS + 600)
    assert checked["record"]["anchor"] is None
    assert checked["record"]["allowed_count"] is None
    assert checked["errors"]
    assert not checked["complete"]


def test_parse_seconds_treats_naive_timestamp_as_beijing_on_utc_host(monkeypatch):
    class UtcHostDateTime(datetime):
        def timestamp(self):
            if self.tzinfo is None:
                return self.replace(tzinfo=timezone.utc).timestamp()
            return super().timestamp()

    monkeypatch.setattr(probe, "datetime", UtcHostDateTime)
    assert probe._parse_seconds(ANCHOR) == ANCHOR_SECONDS


def test_fetch_adds_cache_busting_timestamp(monkeypatch):
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return b"{}"

    def open_url(request, **kwargs):
        requests.append(request.full_url)
        return Response()

    monkeypatch.setattr(probe.urllib.request, "urlopen", open_url)
    probe._fetch("http://local.invalid", 3)
    query = parse_qs(urlparse(requests[0]).query)
    assert "_ts" in query
    assert int(query["_ts"][0]) > 0


def test_jsonl_records_counts_for_old_and_target_without_ball_values(monkeypatch, tmp_path):
    path = tmp_path / "samples.jsonl"
    result, _ = run_probe(
        monkeypatch,
        [sample(7, issue="2026279", elapsed=150), sample(7, elapsed=150)],
        expected_issue="2026280",
        jsonl=str(path),
    )
    assert result == 0
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    records = [json.loads(line) for line in content.splitlines()]
    assert [record["issue"] for record in records] == ["2026279", "2026280"]
    assert records[1]["allowed_count"] == 7
    assert "SECRET" not in content
    assert set(records[1]) == {
        "issue", "balls", "delivered", "specialbool", "server_now", "anchor",
        "clienttime", "request_ts", "error", "allowed_count",
    }


def test_transient_network_error_is_recorded_and_retried(monkeypatch, tmp_path):
    path = tmp_path / "errors.jsonl"
    result, fetched = run_probe(
        monkeypatch, [TimeoutError("SECRET_RESPONSE"), sample(7, elapsed=150)], jsonl=str(path)
    )
    assert result == 0
    assert len(fetched) == 2
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert records[0]["error"]
    assert "SECRET" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("count,elapsed", [(1, 0), (2, 125), (6, 125), (7, 150)])
def test_valid_source_partial_below_time_limit_is_allowed(count, elapsed):
    assert hasattr(probe, "validate_sample")
    result = probe.validate_sample(sample(count, elapsed=elapsed), lottery_type=3, clienttime=ANCHOR_SECONDS)
    assert result["errors"] == []


def test_empty_payload_has_no_completion_or_invented_anchor():
    assert hasattr(probe, "validate_sample")
    result = probe.validate_sample({}, lottery_type=3, clienttime=ANCHOR_SECONDS)
    assert not result["complete"]
    assert result["record"]["anchor"] is None


def test_delivered_count_cannot_exceed_time_limit_even_when_count_does_not():
    assert hasattr(probe, "validate_sample")
    payload = sample(1)
    payload["result_balls"] = [{"value": "SECRET"}] * 6
    result = probe.validate_sample(payload, lottery_type=3, clienttime=ANCHOR_SECONDS)
    assert result["errors"]
    assert result["record"]["allowed_count"] == 1


def test_only_previous_issue_observed_is_incomplete(monkeypatch):
    result, fetched = run_probe(
        monkeypatch, [sample(7, issue="2026279", elapsed=150)], expected_issue="2026280"
    )
    assert len(fetched) == 2
    assert result == 3


def test_mismatched_issue_does_not_add_target_timing_failures(monkeypatch):
    result, _ = run_probe(
        monkeypatch,
        [sample(7, issue="2026279", elapsed=0), sample(7, elapsed=150)],
        expected_issue="2026280",
    )
    assert result == 0


def test_repeated_network_failures_end_at_sampling_deadline(monkeypatch, tmp_path):
    path = tmp_path / "timeouts.jsonl"
    result, fetched = run_probe(monkeypatch, [TimeoutError()], jsonl=str(path))
    assert result == 3
    assert len(fetched) == 2
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_legacy_response_without_server_clock_uses_local_beijing_timestamp():
    payload = sample(7, elapsed=150)
    del payload["server_now"]
    result = probe.validate_sample(payload, lottery_type=3, clienttime=ANCHOR_SECONDS + 125)
    assert result["record"]["allowed_count"] == 6
    assert result["errors"]
    assert not result["complete"]


@pytest.mark.parametrize("server_now", [None, "invalid", True, float("nan"), float("inf")])
def test_invalid_server_clock_cannot_validate_complete_sample(server_now):
    payload = sample(7, elapsed=150)
    payload["server_now"] = server_now
    result = probe.validate_sample(payload, lottery_type=3, clienttime=ANCHOR_SECONDS)
    assert result["errors"]
    assert not result["complete"]


def test_future_anchor_allows_no_numbers():
    result = probe.validate_sample(sample(1, elapsed=-1), lottery_type=3, clienttime=ANCHOR_SECONDS + 150)
    assert result["record"]["allowed_count"] == 0
    assert result["errors"]


def test_matched_issue_progress_cannot_regress():
    result = probe.validate_sample(
        sample(1, elapsed=150), lottery_type=3, clienttime=ANCHOR_SECONDS, last_count=2
    )
    assert result["errors"]


@pytest.mark.parametrize("lottery_type", [1, 2])
def test_non_paced_source_can_complete_without_timing_gate(lottery_type):
    result = probe.validate_sample(sample(7, elapsed=0), lottery_type=lottery_type, clienttime=ANCHOR_SECONDS)
    assert result["errors"] == []
    assert result["complete"]


def test_empty_current_latest_does_not_pass_without_expected_issue(monkeypatch):
    result, _ = run_probe(monkeypatch, [{}])
    assert result == 3


def test_cli_accepts_target_and_jsonl_flags(monkeypatch, tmp_path):
    path = tmp_path / "cli.jsonl"
    monkeypatch.setattr(
        probe.sys, "argv",
        [str(SCRIPT), "--expected-issue", "2026280", "--jsonl", str(path), "--duration", "1"],
    )
    monkeypatch.setattr(probe, "_fetch", lambda *_args, **_kwargs: sample(7, elapsed=150))
    assert probe.main() == 0
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["issue"] == "2026280"
    assert record["request_ts"] > 0


def test_authoritative_current_issue_is_matched_and_logged():
    result = probe.validate_sample(
        sample(7, elapsed=150), lottery_type=3, clienttime=ANCHOR_SECONDS,
        expected_issue="2026280",
    )
    assert result["matches"]
    assert result["complete"]
    assert result["record"]["issue"] == "2026280"


def test_current_issue_takes_precedence_over_legacy_issue():
    payload = sample(7, elapsed=150)
    payload["issue"] = "2026279"
    result = probe.validate_sample(
        payload, lottery_type=3, clienttime=ANCHOR_SECONDS, expected_issue="2026280"
    )
    assert result["complete"]
    assert result["record"]["issue"] == "2026280"


def test_legacy_issue_is_compatible_when_canonical_issue_is_absent():
    payload = sample(7, elapsed=150)
    payload["issue"] = payload.pop("current_issue")
    result = probe.validate_sample(
        payload, lottery_type=3, clienttime=ANCHOR_SECONDS, expected_issue="2026280"
    )
    assert result["complete"]
    assert result["record"]["issue"] == "2026280"


def test_cross_issue_count_reset_without_expected_issue_does_not_report_regression(monkeypatch):
    result, _ = run_probe(
        monkeypatch,
        [sample(6, issue="2026279", elapsed=150), sample(1), sample(7, elapsed=150)],
        duration=1.1,
    )
    assert result == 0


def test_blank_ball_values_do_not_count_as_delivered_or_complete():
    payload = sample(7, elapsed=150)
    payload["result_balls"] = [{"value": ""}] * 6
    payload["special_ball"] = {"value": ""}
    result = probe.validate_sample(payload, lottery_type=3, clienttime=ANCHOR_SECONDS)
    assert result["record"]["delivered"] == 0
    assert not result["record"]["specialbool"]
    assert result["errors"]
    assert not result["complete"]


@pytest.mark.parametrize("invalid_ball", [None, "01", {}, {"value": None}, {"value": " "}])
def test_invalid_regular_ball_position_cannot_validate_completion(invalid_ball):
    payload = sample(7, elapsed=150)
    payload["result_balls"][0] = invalid_ball
    result = probe.validate_sample(payload, lottery_type=3, clienttime=ANCHOR_SECONDS)
    assert result["record"]["delivered"] == 6
    assert result["errors"]
    assert not result["complete"]


@pytest.mark.parametrize("invalid_ball", [None, "07", {}, {"value": None}, {"value": " "}])
def test_invalid_special_ball_cannot_validate_completion(invalid_ball):
    payload = sample(7, elapsed=150)
    payload["special_ball"] = invalid_ball
    result = probe.validate_sample(payload, lottery_type=3, clienttime=ANCHOR_SECONDS)
    assert result["record"]["delivered"] == 6
    assert not result["record"]["specialbool"]
    assert not result["complete"]


def test_seven_regular_balls_plus_special_is_not_six_regular_balls_complete():
    payload = sample(7, elapsed=150)
    payload["result_balls"].append({"value": "SECRET_EXTRA"})
    result = probe.validate_sample(payload, lottery_type=3, clienttime=ANCHOR_SECONDS)
    assert result["errors"]
    assert not result["complete"]


def test_missing_special_cannot_be_replaced_by_a_seventh_regular_ball():
    payload = sample(7, elapsed=150)
    payload["result_balls"].append({"value": "SECRET_EXTRA"})
    payload["special_ball"] = None
    result = probe.validate_sample(payload, lottery_type=3, clienttime=ANCHOR_SECONDS)
    assert result["errors"]
    assert not result["complete"]
