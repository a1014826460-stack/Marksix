import os
import re
import time
from copy import deepcopy

from playwright.sync_api import sync_playwright


def _prediction_payload(lottery_type: int):
    rows = []
    for index in range(8):
        rows.append({
            "issue": f"{lottery_type}{301 - index}",
            "prediction": {
                "tokens": ["鼠|01,13", "牛|02,14", "虎|03,15", "兔|04,16", "龙|05,17", "蛇|06,18", "红波", "蓝波"],
                "groups": [
                    {"key": "xiao_4", "label": "四肖", "tokens": ["鼠", "牛", "虎", "兔"]},
                    {"key": "code_24", "label": "24码", "tokens": [f"{number:02d}" for number in range(1, 25)]},
                ],
            },
            "raw": {"daxiao": "大", "wave": ["红波", "蓝波"], "tail": ["1尾", "2尾", "3尾", "4尾", "5尾"], "xiao_1": "单肖:鼠牛虎兔", "xiao_2": "双肖:龙蛇马羊"},
            "result": {"isOpened": index > 0, "code": "01,02,03,04,05,06,07", "zodiac": "鼠,牛,虎,兔,龙,蛇,马", "isCorrect": None if index == 0 else index % 2 == 0},
        })
    keys = [
        "title_14", "selected_22_codes", "9xzt", "shuangbo", "juesha3xiao", "sixiao_sima", "daxiao", "title_66",
        "title_5", "ma24", "danshuang4xiao", "siduanzhongte", "yibo", "tiandi", "3tou",
        "title_279", "pt1xiao", "pt1wei", "sitouzhongte", "title_132", "qinqi", "3hang", "6xzt",
    ]
    modules = []
    for key in keys:
        module_rows = deepcopy(rows)
        if key == "pt1wei":
            for row in module_rows:
                row["prediction"]["tokens"] = ["1尾|01,11,21,31,41"]
                row["raw"]["tail"] = ["1尾"]
        elif key == "sitouzhongte":
            for row in module_rows:
                row["prediction"]["tokens"] = ["0头|01,02,03", "1头|10,11,12", "2头|20,21,22", "3头|30,31,32"]
        elif key == "title_14":
            for row in module_rows:
                row["raw"]["jia"] = ["牛", "马", "羊", "鸡"]
                row["raw"]["ye"] = ["鼠", "虎", "兔", "龙"]
        modules.append({"key": key, "rows": module_rows})
    return {"ok": True, "data": {"canonical_modules": modules}}


def test_twwanli_all_lottery_tabs_render_isolated_slots():
    requests = []
    page_errors = []
    console_errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe")
        page = browser.new_page()
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" and not message.text.startswith("Failed to load resource") else None)

        def fulfill(route):
            match = re.search(r"lottery_type=(\d+)", route.request.url)
            lottery_type = int(match.group(1)) if match else 3
            requests.append((route.request.url, lottery_type))
            if "/draw" in route.request.url:
                route.fulfill(json={"ok": True, "data": {"issue": f"{lottery_type}500"}})
            else:
                route.fulfill(json=_prediction_payload(lottery_type))

        def fulfill_latest_draw(route):
            match = re.search(r"lottery_type=(\d+)", route.request.url)
            lottery_type = int(match.group(1)) if match else 3
            balls = [{"value": f"{number:02d}", "zodiac": "鼠", "color": "red"} for number in range(1, 7)]
            route.fulfill(json={"current_issue": f"{lottery_type}500", "result_balls": balls, "special_ball": {"value": "07", "zodiac": "马", "color": "blue"}})

        page.route("**/api/sites/twwanli/**", fulfill)
        page.route("**/api/latest-draw?**", fulfill_latest_draw)
        base_url = os.environ.get("TWWANLI_BASE_URL", "http://127.0.0.1:3000")
        page.goto(f"{base_url}/twwanli", wait_until="domcontentloaded")
        deadline = time.monotonic() + 5
        frame = None
        while time.monotonic() < deadline:
            frame = next((item for item in page.frames if item.url.endswith("/vendor/twwanli/index.html")), None)
            if frame:
                break
            page.wait_for_timeout(50)
        assert frame is not None
        draw_frame = None
        while time.monotonic() < deadline:
            draw_frame = next((item for item in page.frames if item.url.endswith("/vendor/twwanli/kai.html")), None)
            if draw_frame:
                break
            page.wait_for_timeout(50)
        assert draw_frame is not None
        outer_draw = frame.locator("iframe[src='kai.html']").first
        assert outer_draw.evaluate("element => element.getBoundingClientRect().height") >= draw_frame.locator("body").evaluate("element => element.scrollHeight")

        for lottery_type in (3, 2, 1):
            draw_frame.locator(f"[data-lottery-type='{lottery_type}']").click()
            page.wait_for_timeout(150)
            assert draw_frame.locator(".KJ-TabBox > div.cur .KJ-IFRAME").evaluate("element => element.getBoundingClientRect().height") >= 190
            assert any(item[1] == lottery_type for item in requests)
            local_draw_frame = next((item for item in page.frames if f"local.html?lottery_type={lottery_type}&" in item.url), None)
            assert local_draw_frame is not None
            assert local_draw_frame.locator("#currentIssue").inner_text() == f"{lottery_type}500"
            assert f"{lottery_type}301期" in frame.locator("#jx24m").inner_text()
            assert "开:07马" in frame.locator("#jx24m").inner_text()
            assert "????" not in frame.locator("#jx24m").inner_text()
            for section_id in ("msks", "wsxx", "wl4x", "dxzt"):
                section = frame.locator(f"#{section_id}")
                assert section.locator("[data-prediction-content]").first.inner_text(), f"{section_id} must render prediction content"
                assert section.locator("[data-prediction-result]").first.inner_text() == "开:待开奖", f"{section_id} must render the prediction result"
            assert "暂无后端资料" not in frame.locator("#jz5x").inner_text()
            assert frame.locator("#jz5x [data-prediction-content]").first.inner_text()
            assert "暂无后端资料" not in frame.locator("#jxzt").inner_text()
            assert frame.locator("#jxzt [data-prediction-content]").first.inner_text()
            assert frame.locator("#dssx [data-prediction-content]").first.inner_text() == "单肖:鼠牛虎兔"
            assert frame.locator("#dssx [data-prediction-content-secondary]").first.inner_text() == "双肖:龙蛇马羊"
            assert "暂无后端资料" not in frame.locator("#qqsh").inner_text()
            for section_id in ("sdzt",):
                content = frame.locator(f"#{section_id} [data-prediction-content]").first
                assert content.evaluate("element => getComputedStyle(element).textAlign") == "center", f"{section_id} prediction text must be centered"
            featured_posts = frame.locator(".tie-con").filter(has_text="181期:【平特一尾】期期免费公開").first
            assert featured_posts.count() == 0
            featured_posts = frame.locator("#jhtz")
            assert featured_posts.locator("a[data-prediction-module]").count() == 6
            assert featured_posts.locator('[data-prediction-module="pt1wei"] [data-prediction-issue]').all_inner_texts() == [f"{lottery_type}301期", f"{lottery_type}300期"]
            assert featured_posts.locator('[data-prediction-module="pt1xiao"] [data-prediction-issue]').all_inner_texts() == [f"{lottery_type}301期", f"{lottery_type}300期"]
            assert featured_posts.locator('[data-prediction-module="pt1wei"] [data-prediction-content]').first.inner_text() == "1尾"
            assert "家禽:牛马羊鸡 野兽:鼠虎兔龙" in featured_posts.locator('[data-prediction-module="title_14"]').inner_text()
            assert featured_posts.locator('[data-prediction-module="sitouzhongte"] [data-prediction-content]').inner_text() == "0头-1头-2头-3头"
            assert featured_posts.locator("[data-prediction-result]").first.inner_text() == "开:待开奖"
            assert featured_posts.locator("[data-prediction-content]").first.evaluate("element => getComputedStyle(element).color") != "rgba(0, 0, 0, 0)"
            assert all(f"lottery_type={lottery_type}" in href for href in featured_posts.locator("a[data-prediction-module]").evaluate_all("items => items.map(item => item.getAttribute('href'))"))
            assert "暂无后端资料" not in featured_posts.inner_text()
            for section_id in ("tdsx", "pt1xiao", "qqsh"):
                content = frame.locator(f"#{section_id} [data-prediction-content]").first
                assert content.evaluate("element => getComputedStyle(element).textAlign") == "center", f"{section_id} prediction text must be centered"
            assert "2025181" not in frame.locator("#yxym").first.inner_text()
            assert "|" not in frame.locator("#yxym").first.inner_text()

        footer = frame.locator("#legacy-attribute-anchor")
        assert footer.count() == 1
        assert footer.locator("#legacy-attribute-gallery img").evaluate_all("items => items.map(item => item.getAttribute('src'))") == [
            "/uploads/image/20250322/1742580086567063.png",
            "/uploads/image/20250322/1742580119746508.jpg",
            "/uploads/image/20250322/1742580130762983.jpg",
        ]

        featured_pages = {
            "21.html": (6, "1尾"),
            "22.html": (6, "鼠"),
            "25.html": (7, "1尾"),
            "26.html": (7, "鼠"),
            "27.html": (7, "家禽:牛马羊鸡 野兽:鼠虎兔龙"),
            "28.html": (7, "0-1-2-3"),
        }
        for filename, (row_count, expected_content) in featured_pages.items():
            page.goto(f"{base_url}/vendor/twwanli/{filename}?lottery_type=2", wait_until="domcontentloaded")
            article = page.locator('[data-prediction-article="true"]')
            article.locator("[data-prediction-content]").first.wait_for(state="visible")
            page.wait_for_function("element => element.textContent.length > 0", arg=article.locator("[data-prediction-content]").first.element_handle())
            assert article.locator("p[data-prediction-row]").count() == row_count
            assert article.locator("[data-prediction-issue]").first.inner_text() == "2301期"
            assert article.locator("[data-prediction-content]").first.inner_text() == expected_content
            assert article.locator("[data-prediction-result]").first.inner_text() == "开:待开奖"
            assert article.locator("[data-prediction-result]").nth(1).inner_text() == "开:07马错"
            assert article.locator("[data-prediction-content]").first.evaluate("element => getComputedStyle(element).display") == "block"
            assert article.locator("[data-prediction-content]").nth(2).get_attribute("data-prediction-hit") == "true"
            assert "2025181" not in article.inner_text()
            assert "????" not in article.inner_text()
        assert not page_errors
        assert not console_errors
        browser.close()


def test_twwanli_reloads_a_cached_empty_prediction_module_once():
    prediction_requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
        )
        page = browser.new_page()

        def fulfill_site_data(route):
            if "/prediction-modules?" not in route.request.url:
                route.fulfill(json={"ok": True, "data": {"issue": "3500"}})
                return

            prediction_requests.append(route.request.url)
            if len(prediction_requests) == 1:
                route.fulfill(json={
                    "ok": True,
                    "data": {
                        "canonical_modules": [
                            {"moduleKey": key, "rows": []}
                            for key in ("6xzt", "pt1wei", "sitouzhongte")
                        ],
                    },
                })
                return
            route.fulfill(json=_prediction_payload(3))

        page.route("**/api/sites/twwanli/**", fulfill_site_data)
        page.route(
            "**/api/latest-draw?**",
            lambda route: route.fulfill(json={
                "current_issue": "3500",
                "result_balls": [],
                "special_ball": {},
            }),
        )
        base_url = os.environ.get("TWWANLI_BASE_URL", "http://127.0.0.1:3000")
        page.goto(f"{base_url}/twwanli", wait_until="domcontentloaded")
        deadline = time.monotonic() + 5
        frame = None
        while time.monotonic() < deadline:
            frame = next(
                (item for item in page.frames if item.url.endswith("/vendor/twwanli/index.html")),
                None,
            )
            if frame:
                break
            page.wait_for_timeout(50)
        assert frame is not None
        frame.locator("#jxzt [data-prediction-content]").first.wait_for(state="visible")
        page.wait_for_timeout(500)

        assert len(prediction_requests) == 2
        assert "暂无后端资料" not in frame.locator("#jxzt").inner_text()
        assert "暂无后端资料" not in frame.locator("#jhtz").inner_text()
        browser.close()


def test_twwanli_formats_sum_qinqi_and_buy_what_opens_from_structured_rows():
    payload = _prediction_payload(2)
    modules = {item["key"]: item for item in payload["data"]["canonical_modules"]}
    outcomes = [
        ("00", "？", False),
        ("03", "龙", True),
        ("07", "鼠", True),
        ("28", "兔", True),
        ("01", "马", True),
    ]
    qinqi_titles = ["画,琴,棋", "画,棋,书", "棋,琴,书", "书,琴,棋", "书,琴,棋"]
    domestic_rows = [
        (["牛", "马", "羊", "鸡"], ["鼠", "虎", "兔", "龙"]),
        (["牛", "马", "羊", "鸡"], ["鼠", "虎", "兔", "龙"]),
        (["牛", "马", "羊", "鸡"], ["鼠", "虎", "兔", "龙"]),
        (["牛", "马", "羊", "鸡"], ["鼠", "虎", "兔", "龙"]),
        (["牛", "马", "羊", "鸡"], ["鼠", "虎", "兔", "龙"]),
    ]
    for index, (code, zodiac, opened) in enumerate(outcomes):
        result = {
            "isOpened": opened,
            "code": code,
            "zodiac": zodiac,
            "isCorrect": True if opened else None,
        }
        modules["title_132"]["rows"][index]["prediction"] = {"text": "合单" if index % 2 == 0 else "合双", "tokens": ["合", "单" if index % 2 == 0 else "双"]}
        modules["title_132"]["rows"][index]["raw"]["content"] = "合单" if index % 2 == 0 else "合双"
        modules["title_132"]["rows"][index]["result"] = result
        modules["title_279"]["rows"][index]["prediction"] = {"text": "合数大" if index % 2 == 0 else "合数小", "tokens": ["合", "数", "大" if index % 2 == 0 else "小"]}
        modules["title_279"]["rows"][index]["raw"]["content"] = "合数大" if index % 2 == 0 else "合数小"
        modules["title_279"]["rows"][index]["result"] = result
        modules["qinqi"]["rows"][index]["raw"]["title"] = qinqi_titles[index]
        modules["qinqi"]["rows"][index]["raw"]["qinqi_reference"] = "琴:兔蛇鸡　棋:鼠牛狗\n书:虎龙马　画:羊猴猪"
        modules["qinqi"]["rows"][index]["result"] = result
        jia, ye = domestic_rows[index]
        modules["title_14"]["rows"][index]["raw"]["jia"] = jia
        modules["title_14"]["rows"][index]["raw"]["ye"] = ye
        modules["title_14"]["rows"][index]["raw"]["domestic_wild_category"] = "家禽" if zodiac == "马" else "野兽" if opened else ""
        modules["title_14"]["rows"][index]["result"] = result

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
        )
        page = browser.new_page()
        page.route(
            "**/api/sites/twwanli/**",
            lambda route: route.fulfill(json=payload),
        )
        page.route(
            "**/api/latest-draw?**",
            lambda route: route.fulfill(json={"current_issue": "2200", "result_balls": [], "special_ball": {}}),
        )
        base_url = os.environ.get("TWWANLI_BASE_URL", "http://127.0.0.1:3000")
        page.goto(f"{base_url}/twwanli", wait_until="domcontentloaded")
        deadline = time.monotonic() + 5
        frame = None
        while time.monotonic() < deadline:
            frame = next((item for item in page.frames if item.url.endswith("/vendor/twwanli/index.html")), None)
            if frame:
                break
            page.wait_for_timeout(50)
        assert frame is not None
        frame.locator("#hsds [data-prediction-content]").first.wait_for(state="visible")
        frame.evaluate("window.TwwanliSiteDataAdapter.selectLottery(2)")
        page.wait_for_timeout(500)

        assert frame.locator("#hsds [data-prediction-content]").all_inner_texts()[:3] == ["合数单", "合数双", "合数单"]
        assert frame.locator("#hsdx [data-prediction-content]").all_inner_texts()[:4] == ["合数大", "合数小", "合数大", "合数小"]
        assert "琴:兔蛇鸡　棋:鼠牛狗" in frame.locator("#qqsh").inner_text()
        assert "书:虎龙马　画:羊猴猪" in frame.locator("#qqsh").inner_text()
        assert frame.locator("#qqsh [data-prediction-issue]").all_inner_texts()[:2] == [
            "琴:兔蛇鸡　棋:鼠牛狗 书:虎龙马　画:羊猴猪 2301期:",
            "2300期:",
        ]
        assert frame.locator("#qqsh [data-prediction-content]").all_inner_texts()[:2] == ["琴棋书画→画琴棋", "琴棋书画→画棋书"]
        assert frame.locator("#qqsh [data-prediction-result]").all_inner_texts()[:2] == ["开:？00", "开:龙03"]
        assert frame.locator("#msks [data-prediction-issue]").all_inner_texts()[:2] == [
            "2301期:火爆家野〈〈待开奖〉〉",
            "2300期:火爆家野〈〈野兽〉〉",
        ]
        assert frame.locator("#msks [data-prediction-content]").all_inner_texts()[:2] == ["待开奖", "准"]
        assert frame.locator("#msks [data-prediction-result]").all_inner_texts()[:2] == ["？00", "龙03准"]
        browser.close()




