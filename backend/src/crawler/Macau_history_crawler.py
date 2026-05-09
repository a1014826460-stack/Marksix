import requests
import json
from typing import Union, List, Dict, Any


# ──────────────────────────────────────────────────────────────
# 澳门彩历史数据采集器
# ──────────────────────────────────────────────────────────────
# 该模块负责从澳门彩官方API拉取历史开奖数据。
# 注意：采集地址（collect_url）和开奖时间（draw_time）不再硬编码在此脚本中，
# 而是统一存储在 PostgreSQL 数据库的 lottery_types 表中，
# 由 crawler_service.py 在调用时从数据库读取并传入。
# ──────────────────────────────────────────────────────────────


def fetch_macau_history_data(
    date: int = 2026,
    collect_url: str = "https://www.lnlllt.com/api.php",
) -> tuple[str, int]:
    """
    获取澳门彩历史数据的函数，发送GET请求到指定的API端点，并返回响应文本和状态码。

    Args:
        date (int): 需要查询的年份，默认为2026年。
        collect_url (str): 采集接口的基础URL地址，
            由调用方从数据库 lottery_types 表的 collect_url 字段获取并传入，
            避免将URL硬编码在脚本中。
            实际请求时会在该URL后拼接 /y/{date} 路径。

    Returns:
        tuple[str, int]: 包含响应文本（JSON字符串）和HTTP状态码的元组。
    """
    # ── 构造请求头，模拟浏览器访问 ──
    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://www.lnlllt.com/?id=20",
        "sec-ch-ua": "\"Microsoft Edge\";v=\"147\", \"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"147\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0"
    }
    params = {
        "action": "history_page",
        "lottery_id": "49",
        "date": str(date),
        "page": "1",
        "limit": "50"
    }
    cookies = {
        # 当前接口不需要cookie，保留空字典以便后续扩展
    }
    # ── 使用从数据库传入的 collect_url 拼接年份路径后发起请求 ──
    response = requests.get(collect_url, headers=headers, cookies=cookies, params=params)

    return response.text, response.status_code


def transform_standard_list(data: Union[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    处理已经符合 {issue, open_time, result} 格式的数据。
    输入可以是 JSON 字符串或直接列表，输出相同的格式（过滤掉无效记录）。
    
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
    
    if not isinstance(data, list):
        raise ValueError("期望输入为一个 JSON 数组")
    
    output = []
    for item in data:
        issue = item.get("issue")
        open_time = item.get("open_time")
        result = item.get("result")
        
        if issue is not None and open_time is not None and result is not None:
            output.append({
                "issue": str(issue),
                "open_time": str(open_time),
                "result": str(result),
                "next_time": str(item.get("next_time") or ""),
            })
    
    return output

if __name__ == "__main__":
    history_data, status_code = fetch_macau_history_data()
    history_data_transformed = transform_standard_list(history_data)
    print(history_data)
    print(status_code)
    print(history_data_transformed)
    print(len(history_data_transformed))