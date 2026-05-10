import requests
import json
from typing import Union, List, Dict, Any


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
    ) -> tuple[str, int]:
    """
    获取香港彩历史数据的函数，发送GET请求到指定的API端点，并返回响应文本和状态码。

    Args:
        type (int): 需要查询的彩票格式，1为香港；2为澳门。

    Returns:
        tuple[str, int]: 包含响应文本（JSON字符串）和HTTP状态码的元组。
    """
    # ── 构造请求头，模拟浏览器访问 ──
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
    cookies = {
        # 当前接口不需要cookie，保留空字典以便后续扩展
    }
    url = "https://www.lnlllt.com/api.php"  
    
    # ── 构造查询参数，请求指定年份的历史开奖数据 ──
    # lottery_id=20 表示香港六合彩，page=1取第一页，limit=50每页最多50条
    params = {
        "lottery_id": "49" if type == 2 else "20",
        "action": "current"
    }

    # ── 使用从数据库传入的 url 发起请求 ──
    response = requests.get(url, headers=headers, cookies=cookies, params=params)
    # response.json()["issus"] = response.text.get("issus", [])[4:]
    # print(response.text)      # 解析JSON响应，确保数据格式正确
    return response.text, response.status_code



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

    if not isinstance(data, list) and isinstance(data, dict):
        data = [data]

    output = []
    for item in data:
        issue = item.get("issue")
        open_time = item.get("open_time")
        result = item.get("result")

        if issue is not None and open_time is not None and result is not None:
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