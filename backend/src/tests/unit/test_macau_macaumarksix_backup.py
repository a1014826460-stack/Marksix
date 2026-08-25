from __future__ import annotations


# ── transform_standard_list：macaumarksix 数组格式 ─────────────────────────

def test_macaumarksix_array_payload_is_normalized():
    from crawler.result_crawler import transform_standard_list

    payload = [{
        "suit": None,
        "expect": "2026233",
        "openTime": "2026-08-21 21:32:32",
        "type": "8",
        "openCode": "18,41,05,49,04,34,07",
        "wave": "red,blue,green,green,blue,red,red",
        "zodiac": "牛,虎,虎,馬,兔,雞,鼠",
        "info": "macaujc.com",
    }]

    assert transform_standard_list(payload, crawler_type=2) == [{
        "issue": "233",
        "open_time": "2026-08-21 21:32:32",
        "result": "18,41,05,49,04,34,07",
        "next_time": "",
    }]


def test_macaumarksix_payload_with_no_open_code_is_rejected():
    from crawler.result_crawler import transform_standard_list

    payload = [{"expect": "2026233", "openTime": "2026-08-21 21:32:32", "openCode": ""}]

    assert transform_standard_list(payload, crawler_type=2) == []


# ── fetch_current_term_data：URL 参数与多源顺序 ────────────────────────────

def test_macaumarksix_request_does_not_append_lnlllt_query_parameters(monkeypatch):
    from crawler.result_crawler import fetch_current_term_data

    observed: dict[str, object] = {}

    class Response:
        status_code = 200
        text = "[]"

    def fake_get(url, **kwargs):
        observed["url"] = url
        observed["params"] = kwargs["params"]
        return Response()

    monkeypatch.setattr("crawler.result_crawler.requests.get", fake_get)
    fetch_current_term_data(
        type=2,
        collect_url="https://macaumarksix.com/api/macaujc2.com",
    )

    assert observed == {
        "url": "https://macaumarksix.com/api/macaujc2.com",
        "params": {},
    }


def test_fetch_current_term_data_tries_primary_then_backups_in_order(monkeypatch):
    from crawler.result_crawler import fetch_current_term_data

    calls: list[str] = []

    class Response:
        status_code = 200
        text = "[]"

    class ConnRefused(Exception):
        pass

    def fake_get(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            raise ConnRefused("connection refused")
        return Response()

    monkeypatch.setattr("crawler.result_crawler.requests.get", fake_get)
    raw, status = fetch_current_term_data(
        type=2,
        collect_url=(
            "https://macaumarksix.com/api/macaujc2.com,"
            "https://api.csjid.com/smallSix/findSmallSixInfo.do?lotCode=MACAO_2033"
        ),
        retry_count=0,
    )

    assert status == 200
    assert calls == [
        "https://macaumarksix.com/api/macaujc2.com",
        "https://api.csjid.com/smallSix/findSmallSixInfo.do?lotCode=MACAO_2033",
    ]


def test_fetch_current_term_data_uses_later_source_when_first_source_is_old(monkeypatch):
    """HTTP 200 的旧期不能遮蔽后续已更新的数据源。"""
    import json

    from crawler.result_crawler import fetch_current_term_data, transform_standard_list

    primary = "https://macaumarksix.com/api/macaujc2.com"
    backup = "https://api.csjid.com/smallSix/findSmallSixInfo.do?lotCode=MACAO_2033"
    calls: list[str] = []
    payloads = {
        primary: [{
            "expect": "2026233",
            "openTime": "2026-08-21 21:32:32",
            "openCode": "18,41,05,49,04,34,07",
        }],
        backup: {
            "result": {"data": {
                "preDrawIssue": "2026234",
                "preDrawTime": "2026-08-22 21:32:32",
                "preDrawCode": "01,02,03,04,05,06,07",
            }},
        },
    }

    class Response:
        status_code = 200

        def __init__(self, payload):
            self.text = json.dumps(payload)

    def fake_get(url, **_kwargs):
        calls.append(url)
        return Response(payloads[url])

    monkeypatch.setenv("DRAW_HK_MACAU_MIN_REQUEST_INTERVAL_SECONDS", "0")
    monkeypatch.setattr("crawler.result_crawler.requests.get", fake_get)

    raw, status = fetch_current_term_data(
        type=2,
        collect_url=f"{primary},{backup}",
        retry_count=0,
        expected_period="2026234",
    )

    assert status == 200
    assert calls == [primary, backup]
    assert transform_standard_list(raw, crawler_type=2)[0]["issue"] == "234"


def test_fetch_current_term_data_audits_old_then_matching_sources(monkeypatch):
    """每个来源都记录响应期号，旧期后立即继续尝试下一来源。"""
    import json

    from crawler.result_crawler import fetch_current_term_data

    primary = "https://first.example/api"
    backup = "https://second.example/api"
    events: list[dict[str, object]] = []
    payloads = {
        primary: [{
            "expect": "2026234",
            "openTime": "2026-08-22 21:32:32",
            "openCode": "01,02,03,04,05,06,07",
        }],
        backup: [{
            "expect": "2026235",
            "openTime": "2026-08-23 21:32:32",
            "openCode": "08,09,10,11,12,13,14",
        }],
    }

    class Response:
        status_code = 200

        def __init__(self, payload):
            self.text = json.dumps(payload)

    monkeypatch.setenv("DRAW_HK_MACAU_MIN_REQUEST_INTERVAL_SECONDS", "0")
    monkeypatch.setattr("crawler.result_crawler.requests.get", lambda url, **_kwargs: Response(payloads[url]))

    raw, status = fetch_current_term_data(
        type=2,
        collect_url=f"{primary},{backup}",
        retry_count=0,
        expected_period="2026235",
        on_attempt=events.append,
    )

    assert status == 200
    assert json.loads(raw)[0]["expect"] == "2026235"
    assert [(event["source"], event["returned_period"], event["outcome"]) for event in events] == [
        ("first.example", "2026234", "old_period"),
        ("second.example", "2026235", "expected_period"),
    ]
    assert all("url" not in event for event in events)


def test_fetch_current_term_data_returns_old_response_only_after_all_sources_are_old(monkeypatch):
    import json

    from crawler.result_crawler import fetch_current_term_data, transform_standard_list

    primary = "https://macaumarksix.com/api/macaujc2.com"
    backup = "https://api.csjid.com/smallSix/findSmallSixInfo.do?lotCode=MACAO_2033"
    calls: list[str] = []

    class Response:
        status_code = 200

        def __init__(self, payload):
            self.text = json.dumps(payload)

    def fake_get(url, **_kwargs):
        calls.append(url)
        if url == primary:
            return Response([{
                "expect": "2026233",
                "openTime": "2026-08-21 21:32:32",
                "openCode": "18,41,05,49,04,34,07",
            }])
        return Response({"result": {"data": {
            "preDrawIssue": "2026233",
            "preDrawTime": "2026-08-21 21:32:32",
            "preDrawCode": "18,41,05,49,04,34,07",
        }}})

    monkeypatch.setenv("DRAW_HK_MACAU_MIN_REQUEST_INTERVAL_SECONDS", "0")
    monkeypatch.setattr("crawler.result_crawler.requests.get", fake_get)

    raw, status = fetch_current_term_data(
        type=2,
        collect_url=f"{primary},{backup}",
        retry_count=0,
        expected_period="2026234",
    )

    assert status == 200
    assert calls == [primary, backup]
    assert transform_standard_list(raw, crawler_type=2)[0]["issue"] == "233"


def test_fetch_current_term_data_skips_lnlllt_params_on_each_backup(monkeypatch):
    """备用列表里每个 URL 独立决定是否附加 lnlllt 参数。"""
    from crawler.result_crawler import fetch_current_term_data

    observed: list[dict[str, object]] = []

    class Response:
        status_code = 500
        text = "[]"

    def fake_get(url, **kwargs):
        observed.append({"url": url, "params": kwargs["params"]})
        return Response()

    monkeypatch.setattr("crawler.result_crawler.requests.get", fake_get)
    fetch_current_term_data(
        type=2,
        collect_url=(
            "https://www.lnlllt.com/api.php,"
            "https://macaumarksix.com/api/macaujc2.com,"
            "https://api.csjid.com/smallSix/findSmallSixInfo.do?lotCode=MACAO_2033"
        ),
        retry_count=0,
    )

    assert observed == [
        {
            "url": "https://www.lnlllt.com/api.php",
            "params": {"lottery_id": "49", "action": "current"},
        },
        {"url": "https://macaumarksix.com/api/macaujc2.com", "params": {}},
        {
            "url": "https://api.csjid.com/smallSix/findSmallSixInfo.do?lotCode=MACAO_2033",
            "params": {},
        },
    ]


# ── scheduler：两个备用源合并与切换 ─────────────────────────────────────────

_MACAU_BACKUP1 = "https://macaumarksix.com/api/macaujc2.com"
_MACAU_BACKUP2 = "https://api.csjid.com/smallSix/findSmallSixInfo.do?lotCode=MACAO_2033&apiKey=secret"


def test_get_effective_collect_url_merges_both_backups(monkeypatch):
    from crawler.scheduler import _get_effective_collect_url

    cfg = {
        "draw.macau_backup_collect_url": _MACAU_BACKUP1,
        "draw.macau_backup2_collect_url": _MACAU_BACKUP2,
        "crawler.backup_fail_count_threshold": 2,
    }
    monkeypatch.setattr("crawler.scheduler._cfg", lambda _db, k, d: cfg.get(k, d))
    monkeypatch.setattr("crawler.scheduler._get_lottery_meta", lambda _db: {})
    monkeypatch.setattr("crawler.scheduler.os.environ", {})

    primary, backup = _get_effective_collect_url(":memory:", 2)

    assert primary == "https://www.lnlllt.com/api.php"
    assert backup == f"{_MACAU_BACKUP1},{_MACAU_BACKUP2}"


def test_get_effective_collect_url_switches_to_backup_after_threshold(monkeypatch):
    from crawler.scheduler import _get_effective_collect_url
    from alerts.alert_service import _crawler_fail_count_key

    cfg = {
        "draw.macau_backup_collect_url": _MACAU_BACKUP1,
        "draw.macau_backup2_collect_url": _MACAU_BACKUP2,
        "crawler.backup_fail_count_threshold": 2,
        _crawler_fail_count_key(2): 3,
    }
    monkeypatch.setattr("crawler.scheduler._cfg", lambda _db, k, d: cfg.get(k, d))
    monkeypatch.setattr("crawler.scheduler._get_lottery_meta", lambda _db: {})
    monkeypatch.setattr("crawler.scheduler.os.environ", {})

    primary, backup = _get_effective_collect_url(":memory:", 2)

    assert primary == f"{_MACAU_BACKUP1},{_MACAU_BACKUP2}"
    assert backup == ""


def test_has_backup_collect_url_sees_second_backup(monkeypatch):
    from crawler.scheduler import _has_backup_collect_url

    cfg = {"draw.macau_backup2_collect_url": _MACAU_BACKUP2}
    monkeypatch.setattr("crawler.scheduler._cfg", lambda _db, k, d: cfg.get(k, d))
    monkeypatch.setattr("crawler.scheduler.os.environ", {})

    assert _has_backup_collect_url(":memory:", 2) is True


def test_has_backup_collect_url_returns_false_when_neither_backup_set(monkeypatch):
    from crawler.scheduler import _has_backup_collect_url

    monkeypatch.setattr("crawler.scheduler._cfg", lambda _db, k, d: None)
    monkeypatch.setattr("crawler.scheduler.os.environ", {})

    assert _has_backup_collect_url(":memory:", 2) is False


def test_hk_macau_requests_use_dedicated_proxy(monkeypatch):
    from crawler.result_crawler import fetch_current_term_data

    observed = {}

    class Response:
        status_code = 200
        text = "[]"

    def fake_get(url, **kwargs):
        observed.update(kwargs)
        return Response()

    monkeypatch.setenv("DRAW_PROXY_URL", "http://mihomo:7890")
    monkeypatch.setenv("DRAW_HK_MACAU_MIN_REQUEST_INTERVAL_SECONDS", "0")
    monkeypatch.setattr("crawler.result_crawler.requests.get", fake_get)

    fetch_current_term_data(type=2, collect_url=_MACAU_BACKUP1)

    assert observed["proxies"] == {
        "http": "http://mihomo:7890",
        "https": "http://mihomo:7890",
    }


def test_non_hk_macau_requests_do_not_use_proxy(monkeypatch):
    from crawler.result_crawler import fetch_current_term_data

    observed = {}

    class Response:
        status_code = 200
        text = "[]"

    def fake_get(url, **kwargs):
        observed.update(kwargs)
        return Response()

    monkeypatch.setenv("DRAW_PROXY_URL", "http://mihomo:7890")
    monkeypatch.setattr("crawler.result_crawler.requests.get", fake_get)

    fetch_current_term_data(type=3, collect_url="https://example.test/api")

    assert "proxies" not in observed


def test_same_source_requests_wait_for_minimum_interval(monkeypatch):
    from crawler.result_crawler import fetch_current_term_data

    sleeps = []

    class Response:
        status_code = 200
        text = "[]"

    monkeypatch.setenv("DRAW_HK_MACAU_MIN_REQUEST_INTERVAL_SECONDS", "7")
    monkeypatch.setattr("crawler.result_crawler.requests.get", lambda *_a, **_k: Response())
    monkeypatch.setattr("crawler.result_crawler._LAST_REQUEST_AT", {})
    monkeypatch.setattr("crawler.result_crawler._time.monotonic", lambda: 100.0)
    monkeypatch.setattr("crawler.result_crawler._time.sleep", sleeps.append)

    fetch_current_term_data(type=2, collect_url=_MACAU_BACKUP1)
    fetch_current_term_data(type=2, collect_url=_MACAU_BACKUP1)

    assert sleeps == [7.0]
