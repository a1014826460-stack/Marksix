import os
import re
import time

from playwright.sync_api import sync_playwright


def _prediction_payload(lottery_type: int):
    rows = []
    for index in range(7):
        rows.append({
            "issue": f"{lottery_type}{301 - index}",
            "prediction": {
                "tokens": ["鼠|01,13", "牛|02,14", "虎|03,15", "兔|04,16", "龙|05,17", "蛇|06,18", "红波", "蓝波"],
                "groups": [
                    {"key": "xiao_4", "label": "四肖", "tokens": ["鼠", "牛", "虎", "兔"]},
                    {"key": "code_24", "label": "24码", "tokens": [f"{number:02d}" for number in range(1, 25)]},
                ],
            },
            "raw": {"daxiao": "大", "wave": ["红波", "蓝波"], "tail": ["1尾", "2尾", "3尾", "4尾", "5尾"]},
            "result": {"isOpened": index > 0, "code": "01,02,03,04,05,06,07", "zodiac": "鼠,牛,虎,兔,龙,蛇,马", "isCorrect": index % 2 == 0},
        })
    keys = [
        "title_14", "selected_22_codes", "9xzt", "shuangbo", "juesha3xiao", "sixiao_sima", "daxiao", "title_66",
        "title_5", "ma24", "danshuang4xiao", "siduanzhongte", "yibo", "tiandi", "3tou",
        "title_279", "pt1xiao", "title_132", "qinqi",
    ]
    return {"ok": True, "data": {"canonical_modules": [{"key": key, "rows": rows} for key in keys]}}


def test_twsyw_all_lottery_tabs_render_isolated_slots():
    requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe")
        page = browser.new_page()
        page_errors = []
        console_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)

        def fulfill(route):
            match = re.search(r"lottery_type=(\d+)", route.request.url)
            lottery_type = int(match.group(1)) if match else 3
            requests.append((route.request.url, lottery_type))
            if "/draw" in route.request.url:
                route.fulfill(json={"ok": True, "data": {"issue": f"{lottery_type}500"}})
            else:
                route.fulfill(json=_prediction_payload(lottery_type))

        page.route("**/api/sites/twsyw/**", fulfill)
        base_url = os.environ.get("TWSYW_BASE_URL", "http://127.0.0.1:3000")
        page.goto(f"{base_url}/twsyw", wait_until="domcontentloaded")
        deadline = time.monotonic() + 5
        frame = None
        while time.monotonic() < deadline:
            frame = next((item for item in page.frames if item.url.endswith("/vendor/twsyw/index.html")), None)
            if frame:
                break
            page.wait_for_timeout(50)
        assert frame is not None
        draw_frame = None
        while time.monotonic() < deadline:
            draw_frame = next((item for item in page.frames if item.url.endswith("/vendor/twsyw/kai.html")), None)
            if draw_frame:
                break
            page.wait_for_timeout(50)
        assert draw_frame is not None

        for lottery_type in (3, 2, 1):
            draw_frame.locator(f"[data-lottery-type='{lottery_type}']").click()
            page.wait_for_timeout(150)
            assert any(item[1] == lottery_type for item in requests)
            assert draw_frame.locator("[data-current-issue]").inner_text() == f"{lottery_type}500"
            assert f"{lottery_type}301期" in frame.locator("#jx24m").inner_text()
            assert "开:07马" in frame.locator("#jx24m").inner_text()
            assert "????" not in frame.locator("#jx24m").inner_text()
            for section_id in ("msks", "wsxx", "wl4x", "dxzt"):
                section = frame.locator(f"#{section_id}")
                assert section.locator("[data-prediction-content]").first.inner_text(), f"{section_id} must render prediction content"
                assert section.locator("[data-prediction-result]").first.inner_text() == "开:待开奖", f"{section_id} must render the prediction result"
            for section_id in ("tdsx", "pt1xiao", "qqsh"):
                content = frame.locator(f"#{section_id} [data-prediction-content]").first
                assert content.evaluate("element => getComputedStyle(element).textAlign") == "center", f"{section_id} prediction text must be centered"
            assert "2025181" not in frame.locator("#yxym").first.inner_text()
            assert "|" not in frame.locator("#yxym").first.inner_text()

        draw_frame.locator("[data-lottery-type='3']").click()
        page.wait_for_timeout(150)
        assert draw_frame.locator("[data-current-issue]").inner_text() == "3500"
        assert frame.locator("#msks .tit").inner_text().startswith("台湾 ")
        draw_frame.locator("[data-lottery-type='2']").click()
        page.wait_for_timeout(150)
        assert frame.locator("#msks .tit").inner_text().startswith("澳门 ")

        footer = frame.locator("#legacy-attribute-anchor")
        assert footer.count() == 1
        assert footer.locator("#legacy-attribute-gallery img").evaluate_all("items => items.map(item => item.getAttribute('src'))") == [
            "/uploads/image/20250322/1742580086567063.png",
            "/uploads/image/20250322/1742580119746508.jpg",
            "/uploads/image/20250322/1742580130762983.jpg",
        ]
        assert not page_errors
        assert not console_errors
        browser.close()




