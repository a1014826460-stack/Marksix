import requests
import json
from datetime import datetime
import os

def fetch_and_save_lottery_data(page=1, page_size=500, sign="2", output_dir="lottery_data"):
    """
    获取彩票开奖数据并保存为 JSON 文件。
    
    Args:
        page: 页码（默认1）
        page_size: 每页条数（默认500）
        sign: 请求签名参数（根据实际需要）
        output_dir: 保存文件的目录（默认为 lottery_data）
    """
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://admin.shengshi8800.com/ds67BvM/kaijiang/index.html",
        "sec-ch-ua": "\"Microsoft Edge\";v=\"147\", \"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"147\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0",
        "x-requested-with": "XMLHttpRequest"
    }
    cookies = {
        "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiIiLCJhdWQiOiIiLCJpYXQiOjE3NzgxNTQyMzEsIm5iZiI6MTc3ODE1NDIzNCwiZXhwIjoxNzc4MjQwNjMxLCJkYXRhIjp7ImlkIjoxLCJuYW1lIjoiYWRtaW4iLCJzaWduIjoiXHU4ZDg1XHU3ZWE3XHU3YmExXHU3NDA2XHU1NDU4IiwianVyIjpudWxsfX0.1IaOuliRxxiil00NGadmiRii1XTb9u-HsdXKJLH-I04"
    }
    url = "https://admin.shengshi8800.com/ds67BvM/code/index"
    params = {
        "page": str(page),
        "pageNum": str(page_size),
        "sign": sign,
        "type": "2"
    }

    try:
        response = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=10)
        response.raise_for_status()  # 如果状态码不是 200，抛出 HTTPError

        # 检查返回内容是否为 JSON
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            print(f"警告：响应不是 JSON 格式，Content-Type: {content_type}")
            print("原始响应前500字符：", response.text[:500])
            return

        data = response.json()
        print(f"请求成功，状态码: {response.status_code}")
        print(f"数据条数: {len(data) if isinstance(data, list) else '非列表结构'}")

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 生成文件名：页码 + 时间戳，避免覆盖
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"lottery_page_{page}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)

        # 保存 JSON 文件（美化格式，支持中文）
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"数据已保存至: {filepath}")

    except requests.exceptions.Timeout:
        print("错误：请求超时，请检查网络或增加 timeout 参数。")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP 错误: {e} - 状态码: {response.status_code}")
        print("响应内容:", response.text[:500])
    except requests.exceptions.RequestException as e:
        print(f"网络请求异常: {e}")
    except json.JSONDecodeError:
        print("错误：无法解析返回的 JSON 数据，可能服务端返回了非 JSON 内容。")
        print("原始响应前500字符：", response.text[:500])
    except Exception as e:
        print(f"未知错误: {e}")


if __name__ == "__main__":
    # 示例：抓取第2页，每页500条
    fetch_and_save_lottery_data(page=1, page_size=500, sign="")