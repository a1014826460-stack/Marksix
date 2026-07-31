import json
import os
import re

from playwright.sync_api import sync_playwright


def prediction_payload(lottery_type: int) -> dict:
    rows = []
    for index in range(1, 10):
        rows.append(
            {
                "issue": f"{lottery_type}{index:02d}",
                "prediction": {"tokens": [f"{lottery_type}肖", f"{index:02d}"], "text": f"{lottery_type}肖|{index:02d}"},
                "result": {"isOpened": index < 9, "code": f"{index:02d}", "zodiac": "鼠", "isCorrect": index == 1, "text": f"{index:02d}鼠"},
            }
        )
    module_keys = (
        "9xzt", "pt1xiao", "shuangbo", "pt3xiao", "4xiao8ma", "daxiao",
        "pt1wei", "juesha2xiao", "jueshabanbo", "juesha1wei", "yijuzhenyan",
    )
    modules = {key: {"moduleKey": key, "rows": rows} for key in module_keys}
    return {"ok": True, "data": {"canonical_modules": list(modules.values())}}


def test_twjsz666_all_lottery_tabs_are_isolated():
    requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe")
        page = browser.new_page()

        def fulfill(route):
            request = route.request
            match = re.search(r"lottery_type=(\d+)", request.url)
            lottery_type = int(match.group(1)) if match else 3
            requests.append((request.url, lottery_type))
            if "/draw" in request.url:
                route.fulfill(json={"ok": True, "data": {"issue": f"{lottery_type}99"}})
            else:
                route.fulfill(json=prediction_payload(lottery_type))

        page.route("**/api/sites/twjsz666/**", fulfill)
        base_url = os.environ.get("TWJSZ666_BASE_URL", "http://127.0.0.1:3000")
        page.goto(f"{base_url}/twjsz666", wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        vendor = next(frame for frame in page.frames if frame.url.endswith("/vendor/twjsz666/index.html"))
        draw = next(frame for frame in page.frames if frame.url.endswith("/vendor/twjsz666/kai.html"))
        tabs = draw.locator(".KJ-TabBox li")
        assert tabs.count() == 3
        for index, expected in enumerate((3, 2, 1)):
            tabs.nth(index).click()
            page.wait_for_timeout(250)
            assert any(lottery_type == expected for _, lottery_type in requests), (expected, requests)
            heading = vendor.locator(".list-title").first.inner_text()
            assert "台湾金手指" not in heading or expected == 3
            body_text = vendor.locator("body").inner_text()
            assert "????" not in body_text
            for title in ("发财⑨肖", "平特一肖", "双波中特", "平特③肖", "④肖⑧码", "大小中特", "平特一尾", "绝杀二肖", "绝杀①波", "绝杀①尾", "一句话中特码"):
                section = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text=title)).first
                assert section.count() == 1, title
                assert f"第{expected}01期" in section.inner_text(), title
        page.goto(f"{base_url}/vendor/twjsz666/155.html", wait_until="domcontentloaded")
        page.wait_for_timeout(250)
        article = page.locator('[data-prediction-article="true"]')
        assert "第301期" in article.inner_text()
        assert "2025060期" not in article.inner_text()
        assert {lottery_type for _, lottery_type in requests} >= {1, 2, 3}
        browser.close()
