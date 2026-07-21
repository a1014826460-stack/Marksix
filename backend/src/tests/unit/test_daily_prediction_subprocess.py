from __future__ import annotations

import subprocess

import pytest


def test_daily_prediction_subprocess_uses_configured_timeout(monkeypatch):
    from crawler import scheduler

    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        scheduler,
        "_cfg",
        lambda _db_path, key, default=None: 123 if key == "crawler.daily_prediction_timeout_seconds" else default,
    )
    monkeypatch.setattr(
        scheduler.subprocess,
        "run",
        lambda *_args, **kwargs: calls.append(kwargs) or type("Done", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
    )

    scheduler._run_daily_prediction_subprocess("sqlite:///scheduler-test", 3)

    assert calls[0]["timeout"] == 123


def test_daily_prediction_subprocess_turns_timeout_into_a_retryable_error(monkeypatch):
    from crawler import scheduler

    monkeypatch.setattr(scheduler, "_cfg", lambda *_args, **_kwargs: 77)
    monkeypatch.setattr(
        scheduler.subprocess,
        "run",
        lambda command, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired(command, 77)),
    )

    with pytest.raises(RuntimeError, match="timed out after 77s"):
        scheduler._run_daily_prediction_subprocess("sqlite:///scheduler-test", 3)


def test_daily_prediction_subprocess_enforces_a_safe_minimum_timeout(monkeypatch):
    from crawler import scheduler

    calls: list[dict[str, object]] = []
    monkeypatch.setattr(scheduler, "_cfg", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(
        scheduler.subprocess,
        "run",
        lambda *_args, **kwargs: calls.append(kwargs) or type("Done", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
    )

    scheduler._run_daily_prediction_subprocess("sqlite:///scheduler-test", 3)

    assert calls[0]["timeout"] == 30
