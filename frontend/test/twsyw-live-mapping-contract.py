import os
import re
import time
from playwright.sync_api import sync_playwright


def prediction_payload(lottery_type: int):
    rows = []
    for index in range(20):
        rows.append({
            "issue": f"{lottery_type}{320 - index}",
            "prediction": {"tokens": ["鼠|01", "牛|02", "虎|03", "兔|04", "龙|05", "蛇|06", "马|07", "羊|08", "猴|09", "鸡|10", "狗|11", "猪|12", "红波", "蓝波"]},
            "result": {"isOpened": index > 0, "code": "01,02,03,04,05,06,07", "zodiac": "鼠,牛,虎,兔,龙,蛇,马", "isCorrect": index % 2 == 0},
        })
    modules = [{"key": key, "rows": rows} for key in (
        "title_14", "juesha3xiao", "9xzt", "selected_22_codes", "shuangbo", "sixiao_sima",
        "daxiao", "title_66", "ma24", "danshuang4xiao", "siduanzhongte", "title_143",
        "title_5", "3tou", "title_279", "pt1xiao", "title_132", "qinqi",
    )]
    for module_key, image_name in (("pmtj_image", "pmtj"), ("brainteaser", "brainteaser")):
        image_rows = [dict(row, prediction={**row["prediction"], "imageUrl": f"/uploads/test/{image_name}-{lottery_type}.jpg"}) for row in rows]
        modules.append({"key": module_key, "rows": image_rows})
    return {"ok": True, "data": {"canonical_modules": modules}}


def test_twsyw_correct_template_renders_draw_and_predictions_for_all_lotteries():
    requests, page_errors, console_errors = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe")
        page = browser.new_page()
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)

        def fulfill(route):
            match = re.search(r"lottery_type=(\d+)", route.request.url)
            lottery_type = int(match.group(1)) if match else 3
            requests.append((route.request.url, lottery_type))
            route.fulfill(json={"ok": True, "data": {"issue": f"{lottery_type}500"}} if "/draw" in route.request.url else prediction_payload(lottery_type))

        page.route("**/api/sites/twsyw/**", fulfill)
        page.route("**/uploads/test/**", lambda route: route.fulfill(
            status=200,
            content_type="image/png",
            body=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0dIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82",
        ))
        base_url = os.environ.get("TWSYW_BASE_URL", "http://127.0.0.1:3000")
        page.goto(f"{base_url}/twsyw", wait_until="domcontentloaded")
        deadline = time.monotonic() + 5
        frame = draw_frame = None
        while time.monotonic() < deadline and (frame is None or draw_frame is None):
            frame = frame or next((item for item in page.frames if item.url.endswith("/vendor/twsyw/index.html")), None)
            draw_frame = draw_frame or next((item for item in page.frames if item.url.endswith("/vendor/twsyw/kai.html")), None)
            page.wait_for_timeout(50)
        assert frame is not None and draw_frame is not None
        outer_draw = frame.locator("iframe[src='kai.html']").first
        assert outer_draw.evaluate("element => element.getBoundingClientRect().height") >= draw_frame.locator("body").evaluate("element => element.scrollHeight")

        for lottery_type, title in ((3, "台湾彩"), (2, "澳门彩"), (1, "香港彩"), (3, "台湾彩")):
            draw_frame.locator(f"[data-lottery-type='{lottery_type}']").click()
            page.wait_for_timeout(150)
            assert draw_frame.locator(".KJ-TabBox > div.cur .KJ-IFRAME").evaluate("element => element.getBoundingClientRect().height") >= 190
            assert any(item[1] == lottery_type for item in requests)
            assert draw_frame.locator("[data-current-issue]").inner_text() == f"{lottery_type}500"
            for section_id in (
                "top_xiao_code", "fslx", "m24", "daxiao", "jiaye", "qixiao", "jiaye4xiao", "gold6xiao",
                "pt1wei", "winner12", "jiuxiao", "lianma", "nannv", "danshuang", "dssx", "hblvxiao",
                "santou", "qiw", "kill4xiao", "kill3wei", "chengyu", "shuangbo", "kill1tou", "five_no_hit", "composite_kill",
            ):
                section = frame.locator(f"#{section_id}")
                assert section.locator("[data-prediction-issue]").first.inner_text().startswith(f"{lottery_type}320期")
                assert section.locator("[data-prediction-content]").first.inner_text() != "暂无后端资料"
                assert section.locator("[data-prediction-result]").first.inner_text() == "开:待开奖"
            assert frame.locator("#top_xiao_code [data-prediction-draw-issue]").first.inner_text() == f"{lottery_type}320期"
            assert frame.locator("[data-site-domain]").first.inner_text() == "www.twsyw.com"
            assert "家禽野兽资料" in frame.locator("#fslx [data-prediction-content]").first.inner_text()
            assert "绝杀三肖" in frame.locator("#composite_kill [data-prediction-content]").first.inner_text()
            assert "平特一肖资料" in frame.locator("#gold6xiao [data-prediction-content]").first.inner_text()
            assert "四段资料" in frame.locator("#lianma [data-prediction-content]").first.inner_text()
            assert "合数大小资料" in frame.locator("#danshuang [data-prediction-content]").first.inner_text()
            assert "一波资料" in frame.locator("#hblvxiao [data-prediction-content]").first.inner_text()
            assert frame.locator("img[data-prediction-image='pmtj_image']").get_attribute("src") == f"/uploads/test/pmtj-{lottery_type}.jpg"
            assert frame.locator("img[data-prediction-image='brainteaser']").get_attribute("src") == f"/uploads/test/brainteaser-{lottery_type}.jpg"
            for module_key in ("pmtj_image", "brainteaser"):
                image = frame.locator(f"img[data-prediction-image='{module_key}']")
                assert image.get_attribute("loading") == "lazy"
                assert image.get_attribute("decoding") == "async"
            assert frame.locator("[data-lottery-title]").first.inner_text() == title

        assert frame.locator("[data-prediction-section]").count() == 25
        footer = frame.locator("#legacy-attribute-anchor")
        assert footer.count() == 1
        assert footer.locator("#legacy-attribute-gallery img").evaluate_all("images => images.map(image => image.getAttribute('src'))") == [
            "/uploads/image/20250322/1742580086567063.png",
            "/uploads/image/20250322/1742580119746508.jpg",
            "/uploads/image/20250322/1742580130762983.jpg",
        ]
        footer.scroll_into_view_if_needed()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not all(footer.locator("#legacy-attribute-gallery img").evaluate_all("images => images.map(image => image.complete && image.naturalWidth > 0)")):
            page.wait_for_timeout(100)
        assert footer.locator("#legacy-attribute-gallery img").evaluate_all("images => images.map(image => image.complete && image.naturalWidth > 0)") == [True, True, True]
        assert footer.evaluate("node => getComputedStyle(node).maxWidth") == "800px"
        assert footer.bounding_box()["width"] <= 800
        links_wrapper = frame.locator("managed-site-links[site-key='twsyw']").locator("xpath=..")
        assert links_wrapper.evaluate("node => getComputedStyle(node).maxWidth") == "800px"
        assert links_wrapper.bounding_box()["width"] <= 800
        assert frame.locator("managed-site-links[site-key='twsyw']").count() == 1
        assert not page_errors
        assert not console_errors
        browser.close()
