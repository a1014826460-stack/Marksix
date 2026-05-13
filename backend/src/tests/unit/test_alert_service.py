"""邮件报警服务单元测试。"""

import pytest

# ── 收件人解析测试 ────────────────────────────────────


def test_get_recipients_from_json_list(monkeypatch):
    """验证 get_recipients 正确解析 JSON 数组。"""
    from alerts.email_service import get_recipients

    def _fake_cfg(db_path, key, fallback):
        return ["a@qq.com", "b@qq.com"]
    monkeypatch.setattr("alerts.email_service._cfg", _fake_cfg)

    recipients = get_recipients("fake_path")
    assert recipients == ["a@qq.com", "b@qq.com"]


def test_get_recipients_default_is_qq_email(monkeypatch):
    """验证默认收件人为 1014826460@qq.com。"""
    from alerts.email_service import get_recipients

    def _fake_cfg(db_path, key, fallback):
        return fallback
    monkeypatch.setattr("alerts.email_service._cfg", _fake_cfg)

    recipients = get_recipients("fake_path")
    assert "1014826460@qq.com" in recipients


def test_get_recipients_filters_empty_strings(monkeypatch):
    """验证过滤空字符串。"""
    from alerts.email_service import get_recipients

    def _fake_cfg(db_path, key, fallback):
        return ["a@qq.com", "", "  ", "b@qq.com"]
    monkeypatch.setattr("alerts.email_service._cfg", _fake_cfg)

    recipients = get_recipients("fake_path")
    assert recipients == ["a@qq.com", "b@qq.com"]


# ── 失败计数测试 ──────────────────────────────────────


def test_crawler_fail_count_key():
    """验证失败计数 key 格式。"""
    from alerts.alert_service import _crawler_fail_count_key
    key = _crawler_fail_count_key(1)
    assert key == "alert._crawler_fail_count_1"


# ── 期号推算测试 ──────────────────────────────────────


def test_compute_next_issue_normal():
    """正常期号推算。"""
    from alerts.alert_service import _compute_next_issue
    assert _compute_next_issue(2026, 130) == (2026, 131)


def test_compute_next_issue_year_boundary():
    """跨年期号推算。"""
    from alerts.alert_service import _compute_next_issue
    assert _compute_next_issue(2026, 365) == (2027, 1)


# ── 爬虫失败报警阈值测试 ──────────────────────────────


def test_alert_crawler_below_threshold_no_alert(monkeypatch):
    """低于阈值不发报警。"""
    from alerts.alert_service import alert_crawler_failure

    def fake_cfg(db_path, key, fallback):
        if key == "alert.crawler_retry_threshold":
            return 3
        if "fail_count" in key:
            return 0
        return fallback

    def fake_increment(db_path, lt):
        return 1

    monkeypatch.setattr("alerts.alert_service._cfg", fake_cfg)
    monkeypatch.setattr("alerts.alert_service.increment_crawler_fail_count", fake_increment)

    result = alert_crawler_failure("fake", 1, "test error")
    assert result is False


def test_alert_crawler_reaches_threshold_sends_email(monkeypatch):
    """达到阈值发报警。"""
    from alerts.alert_service import alert_crawler_failure

    def fake_cfg(db_path, key, fallback):
        if key == "alert.crawler_retry_threshold":
            return 3
        if "fail_count" in key:
            return 2
        return fallback

    def fake_increment(db_path, lt):
        return 3

    monkeypatch.setattr("alerts.alert_service._cfg", fake_cfg)
    monkeypatch.setattr("alerts.alert_service.increment_crawler_fail_count", fake_increment)

    result = alert_crawler_failure("fake", 1, "Connection refused")
    assert result is True


# ── SMTP 配置加载测试 ─────────────────────────────────


def test_load_smtp_config_defaults(monkeypatch):
    """验证 SMTP 配置默认值。"""
    from alerts.email_service import _load_smtp_config

    def fake_cfg(db_path, key, fallback):
        return fallback

    monkeypatch.setattr("alerts.email_service._cfg", fake_cfg)
    config = _load_smtp_config("fake")
    assert config["host"] == "smtp.qq.com"
    assert config["port"] == 587
    assert config["from_name"] == "Liuhecai 报警系统"
