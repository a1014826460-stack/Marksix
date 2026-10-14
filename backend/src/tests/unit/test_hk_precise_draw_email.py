"""Hong Kong publication delays must not become period-mismatch emails."""

import pytest

from alerts import alert_service


@pytest.fixture
def mail_probe(monkeypatch):
    sent = []
    cooldowns = []
    monkeypatch.setattr(
        "alerts.email_service.send_alert_async",
        lambda db_path, **kwargs: sent.append(kwargs),
    )
    monkeypatch.setattr(
        alert_service, "_is_alert_suppressed",
        lambda key, db_path: cooldowns.append(key) or False,
    )
    return sent, cooldowns


@pytest.mark.parametrize("actual", [
    "error: Expecting value: line 1 column 1 (char 0)",
    "error: HTTP 503", "error: no records returned", "", "N/A",
    "2026108", "2026109", "2025150",
])
def test_hk_unavailable_or_not_yet_advanced_does_not_email(actual, mail_probe):
    alert_service.alert_precise_draw_mismatch("unused", 1, "2026109", actual, 4)
    sent, cooldowns = mail_probe
    assert sent == []
    assert cooldowns == []  # Waiting must not consume the real alert cooldown.


def test_hk_unexpected_later_period_still_emails(mail_probe):
    alert_service.alert_precise_draw_mismatch("unused", 1, "2026109", "2026110", 4)
    sent, cooldowns = mail_probe
    assert len(sent) == 1
    assert "香港彩开奖期号不匹配" in sent[0]["subject"]
    assert "2026110" in sent[0]["body_html"]
    assert cooldowns == ["precise_mismatch_1"]


@pytest.mark.parametrize("lottery_type", [2, 3])
@pytest.mark.parametrize("actual", ["error: Expecting value: line 1 column 1 (char 0)", "2026108"])
def test_other_lottery_email_behavior_is_unchanged(lottery_type, actual, mail_probe):
    alert_service.alert_precise_draw_mismatch("unused", lottery_type, "2026109", actual, 4)
    sent, cooldowns = mail_probe
    assert len(sent) == 1
    assert actual in sent[0]["body_html"]
    assert cooldowns == [f"precise_mismatch_{lottery_type}"]
