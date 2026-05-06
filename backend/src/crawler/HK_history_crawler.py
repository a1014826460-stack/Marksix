import requests
import json
from typing import Union, List, Dict, Any


def fetch_hongkong_history_data(date: int = 2026) -> tuple[str, int]:
    """
    获取历史数据的函数，发送GET请求到指定的API端点，并返回响应文本和状态码。

        Args:
            date (int): 需要查询的年份，默认为2026年。


        returns:
            tuple[str, int]: 包含响应文本和状态码的元组。
    """
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
    cookies = {
    
    }
    url = "https://www.lnlllt.com/api.php"
    params = {
        "action": "history_page",
        "lottery_id": "20",
        "date": str(date),
        "page": "1",
        "limit": "50"
    }
    response = requests.get(url, headers=headers, cookies=cookies, params=params)

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
                "result": str(result)
            })
    
    return output


if __name__ == "__main__":
    history_data, status_code = fetch_hongkong_history_data()
    transformed_data = transform_standard_list(history_data)
    print(transformed_data)
    # print(history_data)
    print(status_code)
    print(len(transformed_data))