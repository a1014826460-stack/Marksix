import requests
import json
from typing import Union, List, Dict, Any


def fetch_macau_history_data(date: int = 2026) -> tuple[str, int]:
    """
    获取历史数据的函数，发送GET请求到指定的API端点，并返回响应文本和状态码。
    Args:
        date (int): 需要查询的年份，默认为2026年。
    returns:
        tuple[str, int]: 包含响应文本和状态码的元组。
    """
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "no-cache",
        "origin": "https://macaujc.com",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://macaujc.com/",
        "sec-ch-ua": "\"Microsoft Edge\";v=\"147\", \"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"147\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "sec-fetch-storage-access": "active",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0"
    }
    url = f"https://history.macaumarksix.com/history/macaujc2/y/{date}"
    response = requests.get(url, headers=headers)

    return response.text, response.status_code


def transform_macau_api(data: Union[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    将 macaujc.com API 返回的 JSON 数据转换为统一格式。
    
    输入示例:
    {
        "result": true,
        "data": [
            {"expect": "2026125", "openTime": "2026-05-05 21:32:32", "openCode": "16,19,07,30,38,39,31"},
            ...
        ]
    }
    
    输出示例:
    [
        {"issue": "2026125", "open_time": "2026-05-05 21:32:32", "result": "16,19,07,30,38,39,31"},
        ...
    ]
    """
    # 如果输入是 JSON 字符串，先解析
    if isinstance(data, str):
        data = json.loads(data)
    
    # 提取 data 字段（兼容可能没有外层的 result 字段，直接传入 data 数组的情况）
    if "data" in data:
        records = data["data"]
    elif isinstance(data, list):
        records = data
    else:
        raise ValueError("输入数据格式不正确：缺少 'data' 字段或不是数组")
    
    # 转换每条记录
    output = []
    for item in records:
        # 只提取需要的字段，其他忽略
        issue = item.get("expect")
        open_time = item.get("openTime")
        result = item.get("openCode")
        
        # 跳过缺少关键字段的记录
        if issue is None or open_time is None or result is None:
            continue
        
        output.append({
            "issue": str(issue),
            "open_time": str(open_time),
            "result": str(result)
        })
    
    return output

if __name__ == "__main__":
    history_data, status_code = fetch_macau_history_data()
    history_data_transformed = transform_macau_api(history_data)
    # print(history_data)
    print(status_code)
    print(history_data_transformed)
    print(len(history_data_transformed))