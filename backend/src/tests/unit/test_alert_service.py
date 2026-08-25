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


def test_prediction_gap_uses_columns_present_in_payload_table(monkeypatch):
    from alerts.alert_service import alert_prediction_gap

    class Result:
        def __init__(self, rows=None, row=None):
            self.rows = rows or []
            self.row = row

        def fetchall(self):
            return self.rows

        def fetchone(self):
            return self.row

    class Conn:
        engine = "postgres"

        def __init__(self):
            self.sql = []

        def execute(self, sql, params=()):
            self.sql.append(sql)
            if "FROM lottery_draws" in sql:
                return Result(rows=[{"lottery_type_id": 3, "year": 2026, "term": 100}])
            if "FROM managed_sites" in sql:
                return Result(rows=[{"id": 4, "name": "site", "lottery_type_id": 3, "web_id": 4}])
            if "FROM site_prediction_modules" in sql:
                return Result(row={"mode_id": 123})
            return Result()

        def table_exists(self, name, *, schema=None):
            return name == "mode_payload_123" and schema == "created"

        def table_columns(self, name, *, schema=None):
            assert schema == "created"
            return ("type", "year", "term", "res_code")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    conn = Conn()
    monkeypatch.setattr("alerts.alert_service.connect", lambda _db: conn)
    issues = alert_prediction_gap("fake")

    payload_sql = next(sql for sql in conn.sql if "mode_payload_123" in sql)
    assert "res_code IS NOT NULL" in payload_sql
    assert "content IS NOT NULL" not in payload_sql
    assert issues


def test_prediction_gap_uses_created_schema_jia_ye_payload_columns(monkeypatch):
    """created 表的 jia/ye 有值时不得报预测断层。"""
    from alerts.alert_service import alert_prediction_gap

    class Result:
        def __init__(self, rows=None, row=None):
            self.rows = rows or []
            self.row = row

        def fetchall(self):
            return self.rows

        def fetchone(self):
            return self.row

    class Conn:
        engine = "postgres"

        def __init__(self):
            self.sql = []

        def execute(self, sql, params=()):
            self.sql.append(sql)
            if "FROM lottery_draws" in sql:
                return Result(rows=[{"lottery_type_id": 3, "year": 2026, "term": 100}])
            if "FROM managed_sites" in sql:
                return Result(rows=[{"id": 13, "name": "台湾神预网", "lottery_type_id": 3, "web_id": 13}])
            if "FROM site_prediction_modules" in sql:
                return Result(row={"mode_id": 14})
            if "FROM created.mode_payload_14" in sql:
                return Result(row={"present": 1})
            return Result()

        def table_exists(self, name, *, schema=None):
            return name == "mode_payload_14" and schema == "created"

        def table_columns(self, name, *, schema=None):
            assert name == "mode_payload_14"
            assert schema == "created"
            return ("type", "year", "term", "jia", "ye")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    conn = Conn()
    monkeypatch.setattr("alerts.alert_service.connect", lambda _db: conn)

    assert alert_prediction_gap("fake") == []
    payload_sql = next(sql for sql in conn.sql if "created.mode_payload_14" in sql)
    assert "jia IS NOT NULL" in payload_sql
    assert "ye IS NOT NULL" in payload_sql


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


def test_alert_crawler_above_threshold_suppressed(monkeypatch):
    """超过阈值后不再重复发送报警（防止邮件轰炸）。"""
    from alerts.alert_service import alert_crawler_failure, _alert_last_sent

    # 清除冷却期缓存，避免受其他测试影响
    _alert_last_sent.pop("crawler_failure_1", None)

    def fake_cfg(db_path, key, fallback):
        if key == "alert.crawler_retry_threshold":
            return 3
        if key == "alert.cooldown_seconds":
            return 0  # 关闭冷却期，仅验证阈值去重逻辑
        if "fail_count" in key:
            return 0
        return fallback

    def fake_increment(db_path, lt):
        return 1101  # 远超阈值

    monkeypatch.setattr("alerts.alert_service._cfg", fake_cfg)
    monkeypatch.setattr("alerts.alert_service.increment_crawler_fail_count", fake_increment)

    result = alert_crawler_failure("fake", 1, "超时错误")
    assert result is False  # 超过阈值后不再发送


def test_alert_crawler_cooldown_suppression(monkeypatch):
    """冷却期内不重复发送报警。"""
    import time
    from alerts.alert_service import alert_crawler_failure, _alert_last_sent

    # 预设上次发送时间为"现在"，冷却期 3600 秒
    _alert_last_sent["crawler_failure_2"] = time.time()

    def fake_cfg(db_path, key, fallback):
        if key == "alert.crawler_retry_threshold":
            return 3
        if key == "alert.cooldown_seconds":
            return 3600
        if "fail_count" in key:
            return 0
        return fallback

    def fake_increment(db_path, lt):
        return 3  # 刚好等于阈值

    monkeypatch.setattr("alerts.alert_service._cfg", fake_cfg)
    monkeypatch.setattr("alerts.alert_service.increment_crawler_fail_count", fake_increment)

    result = alert_crawler_failure("fake", 2, "冷却期测试")
    assert result is False  # 冷却期内，抑制发送


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


def test_alert_draw_staleness_includes_lottery_name_and_repair_hint(monkeypatch):
    from alerts.alert_service import alert_draw_staleness
    from datetime import datetime as real_datetime, timezone

    class FakeRow(dict):
        pass

    class FakeConn:
        def execute(self, sql, params=None):
            self.sql = sql
            self.params = params
            return self

        def fetchone(self):
            if "FROM lottery_draws" in getattr(self, "sql", ""):
                return FakeRow({"year": 2026, "term": 142, "next_time": "1000"})
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    captured = {}

    def fake_connect(db_path):
        return FakeConn()

    def fake_send_alert_async(db_path, subject, body_html):
        captured["subject"] = subject
        captured["body_html"] = body_html

    class FakeDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 5, 23, 9, 41, 23, tzinfo=timezone.utc)

    monkeypatch.setattr("alerts.alert_service.connect", fake_connect)
    monkeypatch.setattr("alerts.email_service.send_alert_async", fake_send_alert_async)
    monkeypatch.setattr("alerts.alert_service._load_draw_staleness_state", lambda conn: {})
    monkeypatch.setattr("alerts.alert_service._save_draw_staleness_state", lambda db_path, state: None)
    monkeypatch.setattr("alerts.alert_service.datetime", FakeDatetime)

    result = alert_draw_staleness("fake", lottery_type_id=2)
    assert result is True
    assert "澳门彩" in captured["subject"]
    assert "2026142" in captured["body_html"]
    assert "POST /api/admin/crawler/run-macau" in captured["body_html"]


def test_alert_draw_staleness_taiwan_subject_uses_taiwan_name(monkeypatch):
    from alerts.alert_service import alert_draw_staleness
    from datetime import datetime as real_datetime, timezone

    class FakeRow(dict):
        pass

    class FakeConn:
        def execute(self, sql, params=None):
            self.sql = sql
            return self

        def fetchone(self):
            if "FROM lottery_draws" in getattr(self, "sql", ""):
                return FakeRow({"year": 2026, "term": 162, "next_time": "1748529120000"})
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    captured = {}

    class FakeDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 6, 4, 11, 8, 56, tzinfo=timezone.utc)

    monkeypatch.setattr("alerts.alert_service.connect", lambda db_path: FakeConn())
    monkeypatch.setattr(
        "alerts.email_service.send_alert_async",
        lambda db_path, subject, body_html: captured.update({"subject": subject, "body_html": body_html}),
    )
    monkeypatch.setattr("alerts.alert_service._load_draw_staleness_state", lambda conn: {})
    monkeypatch.setattr("alerts.alert_service._save_draw_staleness_state", lambda db_path, state: None)
    monkeypatch.setattr("alerts.alert_service.datetime", FakeDatetime)

    result = alert_draw_staleness("fake", lottery_type_id=3)
    assert result is True
    assert captured["subject"] == "[台湾彩] 开奖数据滞后报警"
    assert "六合彩" not in captured["subject"]
    assert "台湾彩" in captured["body_html"]


def test_alert_draw_staleness_same_issue_only_sends_once(monkeypatch):
    from alerts.alert_service import alert_draw_staleness
    from datetime import datetime as real_datetime, timezone

    class FakeRow(dict):
        pass

    class FakeConn:
        def execute(self, sql, params=None):
            self.sql = sql
            return self

        def fetchone(self):
            if "FROM lottery_draws" in getattr(self, "sql", ""):
                return FakeRow({"year": 2026, "term": 162, "next_time": "1748529120000"})
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    stored_state = {}
    sent_subjects = []

    class FakeDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 6, 4, 11, 8, 56, tzinfo=timezone.utc)

    def fake_load_state(conn):
        return dict(stored_state)

    def fake_save_state(db_path, state):
        stored_state.clear()
        stored_state.update(state)

    monkeypatch.setattr("alerts.alert_service.connect", lambda db_path: FakeConn())
    monkeypatch.setattr(
        "alerts.email_service.send_alert_async",
        lambda db_path, subject, body_html: sent_subjects.append(subject),
    )
    monkeypatch.setattr("alerts.alert_service._load_draw_staleness_state", fake_load_state)
    monkeypatch.setattr("alerts.alert_service._save_draw_staleness_state", fake_save_state)
    monkeypatch.setattr("alerts.alert_service.datetime", FakeDatetime)

    assert alert_draw_staleness("fake", lottery_type_id=3) is True
    assert sent_subjects == ["[台湾彩] 开奖数据滞后报警"]

    assert alert_draw_staleness("fake", lottery_type_id=3) is True
    assert sent_subjects == ["[台湾彩] 开奖数据滞后报警"]
