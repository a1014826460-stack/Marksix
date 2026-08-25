import time as _time
import os
import threading
from collections.abc import Callable
from urllib.parse import urlsplit

import requests
import json
from typing import Union, List, Dict, Any


_REQUEST_LIMIT_LOCK = threading.Lock()
_LAST_REQUEST_AT: dict[str, float] = {}


def _request_proxy(crawler_type: int) -> dict[str, str] | None:
    """Return the dedicated proxy only for Hong Kong and Macau crawls."""
    if crawler_type not in (1, 2):
        return None
    proxy = os.environ.get("DRAW_PROXY_URL", "").strip()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def _throttle_source(url: str, crawler_type: int) -> None:
    if crawler_type not in (1, 2):
        return
    try:
        minimum = max(0.0, float(os.environ.get("DRAW_HK_MACAU_MIN_REQUEST_INTERVAL_SECONDS", "10")))
    except ValueError:
        minimum = 10.0
    if minimum <= 0:
        return
    with _REQUEST_LIMIT_LOCK:
        now = _time.monotonic()
        previous = _LAST_REQUEST_AT.get(url)
        wait_for = minimum - (now - previous) if previous is not None else 0.0
        if wait_for > 0:
            _time.sleep(wait_for)
        _LAST_REQUEST_AT[url] = _time.monotonic()


# ──────────────────────────────────────────────────────────────
# 香港彩（六合彩）历史数据采集器
# ──────────────────────────────────────────────────────────────
# 该模块负责从香港彩官方API拉取历史开奖数据。
# 注意：采集地址（collect_url）和开奖时间（draw_time）不再硬编码在此脚本中，
# 而是统一存储在 PostgreSQL 数据库的 lottery_types 表中，
# 由 crawler_service.py 在调用时从数据库读取并传入。
# ──────────────────────────────────────────────────────────────


def fetch_current_term_data(
    type: int = 1,
    collect_url: str = "",
    backup_url: str = "",
    retry_count: int = 1,
    retry_delay: float = 1.0,
    timeout: int = 30,
    expected_period: str | None = None,
    on_attempt: Callable[[dict[str, Any]], None] | None = None,
    ) -> tuple[str, int]:
    """获取香港/澳门彩当前期开奖数据，支持主/备 URL 和重试。

    先尝试主 URL，每次失败后等待 retry_delay 秒重试。
    主 URL 全部重试耗尽后自动切换备用 URL（若有配置）。

    Args:
        type (int): 1=香港, 2=澳门
        collect_url (str): 主采集 URL，为空时使用默认地址
        backup_url (str): 备用采集 URL，为空时不使用备用
        retry_count (int): 每个 URL 的额外重试次数（总尝试 = 1 + retry_count）
        retry_delay (float): 重试间隔秒数
        timeout (int): 单次 HTTP 请求超时秒数
        expected_period (str): 预期完整期号。仅港澳彩使用：HTTP 200 但
            返回其他期号时继续检查下一来源。

    Returns:
        tuple[str, int]: (响应文本, HTTP 状态码)。全部 URL 和重试失败时返回 ("", 0)
    """
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "priority": "u=0, i",
        "referer": "https://www.lnlllt.com/",
        "sec-ch-ua": "\"Microsoft Edge\";v=\"147\", \"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"147\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "cross-site",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0"
    }
    def split_urls(url: str) -> list[str]:
        return [u.strip() for u in (url or "").split(",") if u.strip()]

    # 支持逗号分隔的多个采集 URL（主源 + 多个备用源），按顺序逐个尝试。
    urls: list[str] = split_urls(collect_url) or ["https://www.lnlllt.com/api.php"]
    for u in split_urls(backup_url):
        if u and u not in urls:
            urls.append(u)

    expected_period = str(expected_period or "").strip()
    def _source_name(url: str) -> str:
        return urlsplit(url).netloc or "unknown"

    def _report(
        url: str,
        attempt: int,
        *,
        status_code: int,
        returned_period: str = "",
        outcome: str,
        elapsed_ms: int,
        error: str = "",
    ) -> None:
        if on_attempt is None:
            return
        on_attempt({
            "source": _source_name(url),
            "attempt": attempt,
            "status_code": status_code,
            "returned_period": returned_period,
            "outcome": outcome,
            "elapsed_ms": elapsed_ms,
            "error": error,
        })

    last_status = 0
    first_old_response: str | None = None
    for url in urls:
        # lnlllt 主源需要 lottery_id/action 参数；csjid 与 macaumarksix 完整 API 不需要。
        params = {} if ("csjid.com" in url or "macaumarksix.com" in url) else {
            "lottery_id": "49" if type == 2 else "20",
            "action": "current"
        }
        for attempt in range(1 + retry_count):
            started_at = _time.monotonic()
            try:
                _throttle_source(url, type)
                request_kwargs = {"headers": headers, "params": params, "timeout": timeout}
                proxy = _request_proxy(type)
                if proxy:
                    request_kwargs["proxies"] = proxy
                response = requests.get(url, **request_kwargs)
                last_status = response.status_code
                elapsed_ms = round((_time.monotonic() - started_at) * 1000)
                if response.status_code == 200:
                    if expected_period and type in (1, 2):
                        try:
                            records = transform_standard_list(response.text, crawler_type=type)
                        except (TypeError, ValueError, json.JSONDecodeError):
                            records = []
                        returned_period = next(
                            (_standard_record_period(record) for record in records if _standard_record_period(record)),
                            "",
                        )
                        if any(_standard_record_period(record) == expected_period for record in records):
                            _report(url, attempt + 1, status_code=200, returned_period=returned_period,
                                    outcome="expected_period", elapsed_ms=elapsed_ms)
                            return response.text, response.status_code
                        if records and first_old_response is None:
                            first_old_response = response.text
                        _report(url, attempt + 1, status_code=200, returned_period=returned_period,
                                outcome="old_period" if records else "no_records", elapsed_ms=elapsed_ms)
                        # HTTP 成功但返回旧期或无有效记录，继续检查后续来源。
                        break
                    _report(url, attempt + 1, status_code=200, outcome="success", elapsed_ms=elapsed_ms)
                    return response.text, response.status_code
                _report(url, attempt + 1, status_code=response.status_code, outcome="http_error", elapsed_ms=elapsed_ms)
                if attempt < retry_count:
                    _time.sleep(retry_delay * (2 ** attempt))
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                last_status = 0
                _report(url, attempt + 1, status_code=0, outcome="network_error",
                        elapsed_ms=round((_time.monotonic() - started_at) * 1000), error=exc.__class__.__name__)
                if attempt < retry_count:
                    _time.sleep(retry_delay * (2 ** attempt))
            except Exception as exc:
                last_status = 0
                _report(url, attempt + 1, status_code=0, outcome="request_error",
                        elapsed_ms=round((_time.monotonic() - started_at) * 1000), error=exc.__class__.__name__)
                if attempt < retry_count:
                    _time.sleep(retry_delay * (2 ** attempt))

    return first_old_response or "", last_status



def _normalize_issue(raw_issue: str, crawler_type: int = 0) -> str:
    """归一化期号字符串，处理不同彩种的特殊格式。

    转换规则：
    - type == 2（澳门彩）：API 返回的 issue 可能是 "YYYY期数" 格式
      （如 "2023第12期"），需要去除前 4 位年份，仅保留期数部分（如 "第12期"）。
      如果期数部分保留完整标识符（如 "第"、"期" 等中文描述），不做额外拆分。
    - type != 2 或 issue 长度 ≤ 4：原样返回，不做处理。

    :param raw_issue: 原始期号字符串
    :param crawler_type: 爬虫类型（1=香港, 2=澳门），默认 0 不做特殊处理
    :return: 归一化后的期号字符串
    """
    issue = str(raw_issue or "").strip()
    # 仅澳门彩(type==2) 且 issue 长度超过 4 位时，去除前 4 位年份前缀
    if crawler_type == 2 and len(issue) > 4:
        # 前 4 位为年份数字时执行切片，否则保持原样
        if issue[:4].isdigit():
            issue = issue[4:]
    return issue


def _standard_record_period(record: Dict[str, Any]) -> str:
    """将标准化记录的期号补全为 YYYYNNN，供多来源新期选择使用。"""
    issue = str(record.get("issue") or "").strip()
    open_time = str(record.get("open_time") or "").strip()
    if not issue:
        return ""
    try:
        term = int(issue)
    except ValueError:
        return issue
    if term < 1000 and len(open_time) >= 4 and open_time[:4].isdigit():
        return f"{open_time[:4]}{term:03d}"
    return str(term)


def transform_standard_list(
    data: Union[str, List[Dict[str, Any]]],
    crawler_type: int = 0,
) -> List[Dict[str, Any]]:
    """
    处理已经符合 {issue, open_time, result} 格式的数据。
    输入可以是 JSON 字符串或直接列表，输出相同的格式（过滤掉无效记录）。

    :param data: JSON 字符串或字典/列表
    :param crawler_type: 爬虫类型（1=香港, 2=澳门），用于 issue 字段归一化，
                         默认 0 不做特殊处理

    输入示例:
    [
        {"issue": "134", "open_time": "2025-12-28 21:34:59", "result": "07,30,19,11,25,10,45"},
        ...
    ]

    输出（不变，仅做校验）:
    相同列表，但可能过滤掉缺少必要字段的记录。
    """
    if isinstance(data, str):
        data = json.loads(data)

    if isinstance(data, dict):
        # csjid smallSix API: {errorCode, result: {businessCode, data: {...}}}.
        # preDraw* is the last opened draw; every timestamp is Beijing time.
        csjid_data = data.get("result", {}).get("data") if isinstance(data.get("result"), dict) else None
        if isinstance(csjid_data, dict):
            data = [{
                "issue": csjid_data.get("preDrawIssue"),
                "open_time": csjid_data.get("preDrawTime"),
                "result": csjid_data.get("preDrawCode"),
            }]
        else:
            data = [data]

    # macaumarksix API: 数组元素为 {expect, openTime, openCode, ...}，
    # 时间戳是北京时间。映射到标准 {issue, open_time, result}。
    if isinstance(data, list) and data and isinstance(data[0], dict) and "expect" in data[0]:
        output = []
        for item in data:
            issue = item.get("expect")
            open_time = item.get("openTime")
            result = item.get("openCode")
            if issue is not None and open_time is not None and str(result or "").strip():
                output.append({
                    "issue": _normalize_issue(str(issue), crawler_type),
                    "open_time": str(open_time),
                    "result": str(result),
                    "next_time": str(item.get("next_time") or ""),
                })
        return output

    output = []
    for item in data:
        issue = item.get("issue")
        open_time = item.get("open_time")
        result = item.get("result")

        if issue is not None and open_time is not None and str(result or "").strip():
            output.append({
                "issue": _normalize_issue(str(issue), crawler_type),
                "open_time": str(open_time),
                "result": str(result),
                "next_time": str(item.get("next_time") or ""),
            })

    return output


if __name__ == "__main__":
    history_data, status_code = fetch_current_term_data(type=1)
    transformed_data = transform_standard_list(history_data, crawler_type=2)
    print(transformed_data)
    # print(history_data)
    print(status_code)
    # print(len(transformed_data))
