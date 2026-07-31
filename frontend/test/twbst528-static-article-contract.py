import os
import time

from playwright.sync_api import sync_playwright


def payload(module_key: str):
    rows = []
    for index in range(8):
        rows.append({
            "issue": str(510 - index),
            "term": str(510 - index),
            "prediction": {"text": f"动态值{index}", "tokens": [f"动态值{index}"]},
            "result": {
                "isOpened": index != 0,
                "isCorrect": index in (1, 4),
                "code": "02",
                "zodiac": "龙",
                "text": "龙02",
            },
        })
    return {"ok": True, "data": {"canonical_modules": [{"moduleKey": module_key, "rows": rows}]}}


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get(
                "PLAYWRIGHT_CHROMIUM_EXECUTABLE",
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            ),
            headless=True,
        )
        try:
            page = browser.new_page()
            def fulfill(route):
                response = payload("title_198")
                response["data"]["canonical_modules"].append(payload("yijuzhenyan")["data"]["canonical_modules"][0])
                route.fulfill(json=response)

            page.route("**/api/sites/twbst528/prediction-modules?**", fulfill)
            for page_id, label, capacity in (("141", "逢买必中", 8), ("15", "逢买必中", 1), ("44", "一句中特", 2)):
                page.goto(f"http://127.0.0.1:3000/vendor/twbst528/{page_id}.html", wait_until="domcontentloaded")
                deadline = time.monotonic() + 10
                article = page.locator(".article-content")
                while time.monotonic() < deadline and "第510期" not in article.inner_text():
                    page.wait_for_timeout(100)

                rows = article.locator(":scope > p")
                assert rows.count() == capacity
                assert f"第510期 {label} 【动态值0】开 待开奖" in rows.nth(0).inner_text()
                if capacity > 1:
                    assert f"第509期 {label} 【动态值1】开 02龙对" in rows.nth(1).inner_text()
                assert "2025233期" not in article.inner_text()
                assert "?????" not in article.inner_text()

            page.goto("http://127.0.0.1:3000/vendor/twbst528/141.html", wait_until="domcontentloaded")
            article = page.locator(".article-content")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and "第510期" not in article.inner_text():
                page.wait_for_timeout(100)
            marker = article.locator(":scope > p").nth(4).locator("span[style*='background-color']")
            assert marker.count() == 1
            assert "rgb(255, 255, 0)" in (marker.get_attribute("style") or "")

            # The visible draw-history page must replace every supplier issue
            # and ball with the same-origin draw-history payload.
            page.route("**/api/draw-history?**", lambda route: route.fulfill(json={
                "items": [{
                    "issue": "510", "date": "2026-07-31", "balls": [
                        {"value": "01", "zodiac": "鼠", "color": "red"},
                        {"value": "12", "zodiac": "牛", "color": "blue"},
                        {"value": "23", "zodiac": "虎", "color": "green"},
                        {"value": "34", "zodiac": "兔", "color": "red"},
                        {"value": "45", "zodiac": "龙", "color": "blue"},
                        {"value": "46", "zodiac": "蛇", "color": "green"},
                    ],
                    "specialBall": {"value": "49", "zodiac": "猪", "color": "red"},
                }]
            }))
            base_url = os.environ.get("SITE_TEST_BASE_URL", "http://127.0.0.1:3000")
            page.goto(base_url + "/vendor/twbst528/history.html", wait_until="domcontentloaded")
            history = page.locator("#lishi")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and "第510期开奖结果" not in history.inner_text():
                page.wait_for_timeout(100)
            assert "第510期开奖结果" in history.inner_text()
            assert "第323期开奖结果" not in history.inner_text()
            assert "49" in history.locator(".open-item").first.inner_text()
            assert history.locator(".open-item").nth(1).inner_text().strip() == ""
        finally:
            browser.close()


if __name__ == "__main__":
    main()
