import copy
import json
import os
import re

from playwright.sync_api import sync_playwright


def prediction_payload(lottery_type: int) -> dict:
    rows = []
    for index in range(1, 10):
        rows.append(
            {
                "issue": f"2026{lottery_type}{index:02d}",
                "prediction": {"tokens": [f"{lottery_type}肖", f"{index:02d}"], "text": f"{lottery_type}肖|{index:02d}"},
                "result": {"isOpened": index < 9, "code": f"{index:02d}", "zodiac": "鼠", "isCorrect": index == 1, "text": f"{index:02d}鼠"},
            }
        )
    module_keys = (
        "9xzt", "pt1xiao", "shuangbo", "pt3xiao", "4xiao8ma", "daxiao",
        "pt1wei", "juesha2xiao", "jueshabanbo", "juesha1wei", "yijuzhenyan",
        "danshuang4xiao", "three_head_four_tail", "gongshi_siw", "title_14", "title_74",
        "sizixuanji", "selected_22_codes", "steady_kill_7_codes", "expert_publications",
    )
    # Each module needs independent rows: specialized payload fields must not
    # overwrite the fixture data consumed by another module renderer.
    modules = {key: {"moduleKey": key, "rows": copy.deepcopy(rows)} for key in module_keys}
    for row in modules["three_head_four_tail"]["rows"]:
        row["raw"] = {"content": json.dumps({"heads": ["0头", "1头", "2头"], "tails": ["0尾", "1尾", "2尾"]})}
    for row in modules["gongshi_siw"]["rows"]:
        row["prediction"]["tokens"] = ["0尾", "1尾", "2尾", "3尾"]
    for row in modules["expert_publications"]["rows"]:
        row["raw"] = {"content": json.dumps({"publications": [f"后端资料{index}" for index in range(1, 15)]})}
    for row in modules["danshuang4xiao"]["rows"]:
        row["raw"] = {"single_xiao": ["鼠", "牛", "虎", "兔"], "double_xiao": ["龙", "蛇", "马", "羊"]}
    for row in modules["title_14"]["rows"]:
        row["raw"] = {"jia": "鸡,牛,羊", "ye": "龙,鼠,蛇"}
    for row in modules["4xiao8ma"]["rows"]:
        row["raw"] = {"xiao": ["鼠", "牛", "虎", "兔"], "code": ["01", "02", "03", "04", "05", "06", "07", "08"]}
    for row in modules["selected_22_codes"]["rows"]:
        row["prediction"]["tokens"] = [f"{value:02d}" for value in range(1, 23)]
    for row in modules["steady_kill_7_codes"]["rows"]:
        row["prediction"]["tokens"] = [f"{value:02d}" for value in range(1, 8)]
    for row in modules["pt1xiao"]["rows"]:
        row["raw"] = {"xiao": "虎"}
    for row in modules["shuangbo"]["rows"]:
        row["raw"] = {"wave": ["红波", "绿波"]}
    for row in modules["daxiao"]["rows"]:
        row["raw"] = {"daxiao": "大"}
    for row in modules["jueshabanbo"]["rows"]:
        row["prediction"]["tokens"] = ["红单"]
    for row in modules["title_74"]["rows"]:
        row["prediction"]["tokens"] = ["1尾", "2尾", "3尾", "4尾", "5尾", "6尾", "7尾"]
    for row in modules["yijuzhenyan"]["rows"]:
        row["raw"] = {"sentence": "鼠来牛来虎兔发财"}
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
                route.fulfill(json={"ok": True, "data": {
                    "current_issue": f"{lottery_type}99",
                    "balls": [
                        {"value": "01", "zodiac": "鼠", "is_special": False},
                        {"value": "49", "zodiac": "猪", "is_special": True},
                    ],
                }})
            else:
                route.fulfill(json=prediction_payload(lottery_type))

        page.route("**/api/sites/twjsz666/**", fulfill)
        base_url = os.environ.get("TWJSZ666_BASE_URL", "http://127.0.0.1:3000")
        page.goto(f"{base_url}/twjsz666", wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        vendor = next(frame for frame in page.frames if frame.url.endswith("/vendor/twjsz666/index.html"))
        draw = next(frame for frame in page.frames if frame.url.endswith("/vendor/twjsz666/kai.html"))
        one_head_cards = vendor.locator("#yxym .bizhong1")
        assert one_head_cards.count() == 9
        assert "060期" not in one_head_cards.first.inner_text()
        assert "资料同步中" not in vendor.locator("body").inner_text()
        four_xiao = vendor.locator("#pttj + table tr").first
        assert "301期:单肖" in four_xiao.locator("font").nth(0).inner_text()
        assert "【鼠牛虎兔】" == four_xiao.locator(".zl").nth(0).inner_text()
        assert "双肖" == four_xiao.locator("font").nth(1).inner_text()
        assert "【龙蛇马羊】" == four_xiao.locator(".zl").nth(1).inner_text()
        poultry = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="家禽VS野兽")).first.locator("tr").first
        assert poultry.locator(".zl").nth(0).inner_text() == "鸡牛羊"
        assert poultry.locator(".zl").nth(1).inner_text() == "龙鼠蛇"
        four_xiao_eight_code = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="④肖⑧码")).first.locator("tr").nth(1)
        assert "合肖（鼠牛虎兔）" in four_xiao_eight_code.inner_text()
        assert "01.02.03.04.05.06.07.08" in four_xiao_eight_code.inner_text()
        assert four_xiao_eight_code.locator("td > font").nth(2).inner_text().strip() == "开:01鼠对"
        # The template has one row break and one detail-line break; both are
        # structural and must survive data binding.
        assert four_xiao_eight_code.locator("br").count() == 2
        selected = vendor.locator("#jx22ma + table tr").first
        assert selected.locator("th").nth(1).locator("br").count() == 1
        assert selected.locator("th").nth(1).inner_text().splitlines() == [
            "01-02-03-04-05-06-07-08-09-10-11",
            "12-13-14-15-16-17-18-19-20-21-22",
        ]
        kill_seven = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="稳杀⑦码")).first.locator("tr").first
        assert kill_seven.locator("br").count() == 1
        assert "【01.02.03.04.05.06.07】" in kill_seven.inner_text()
        assert kill_seven.locator("td > font").nth(2).inner_text().strip() == "开:01鼠对"
        fortune = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="发财⑨肖")).first.locator("tr").first
        assert "301期" in fortune.locator("font").nth(0).inner_text()
        assert "【3肖01】" == fortune.locator(".zl").first.inner_text()
        assert "开:01鼠对" in fortune.locator("font").last.inner_text()
        assert fortune.locator("xpath=following-sibling::tr[1]").locator("td > font").last.inner_text() == "开:02鼠错"
        flat_three = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="平特③肖")).first.locator("tr").first
        assert "301期" in flat_three.locator("font").nth(0).inner_text()
        assert "【3肖01】" == flat_three.locator(".zl").first.inner_text()
        assert flat_three.locator("font").last.inner_text() == "大奉送！"
        flat_tail = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="平特一尾")).first.locator("tr").first
        assert "301期" in flat_tail.locator("font").nth(0).inner_text()
        assert "3肖、01" in flat_tail.locator("font").nth(0).inner_text()
        assert "开:01鼠对" in flat_tail.locator("font").nth(0).inner_text()
        kill_two = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="绝杀二肖")).first.locator("tr").first
        assert "301期" in kill_two.locator("font").nth(0).inner_text()
        assert "【3肖.01】" == kill_two.locator(".zl").first.inner_text()
        assert "开:01鼠对" in kill_two.locator("font").last.inner_text()
        kill_tail = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="绝杀①尾")).first.locator("tr").first
        assert "301期" in kill_tail.locator("font").nth(0).inner_text()
        assert "3肖" == kill_tail.locator(".zl").first.inner_text()
        assert "开:01鼠对" in kill_tail.locator("font").last.inner_text()
        flat_one = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="平特一肖")).first.locator("tr").first
        assert "301期:平特一肖" == flat_one.locator("font").nth(0).inner_text()
        assert "【虎】" == flat_one.locator(".zl").first.inner_text()
        assert "开:01鼠对" in flat_one.locator("font").last.inner_text()
        double_wave = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="双波")).first.locator("tr").first
        assert "301期:双波" == double_wave.locator("font").nth(0).inner_text()
        assert "【红波+绿波】" == double_wave.locator(".zl").first.inner_text()
        assert "开:01鼠对" in double_wave.locator("font").last.inner_text()
        big_small = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="大小中特")).first.locator("tr").first
        assert "301期: " == big_small.locator("font").nth(0).inner_text()
        assert "大数" == big_small.locator(".zl").first.inner_text()
        assert "开:01鼠对" in big_small.locator("font").last.inner_text()
        four_char = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="四字解")).first.locator("tr").first
        assert four_char.locator("th").nth(0).inner_text() == "301期"
        assert four_char.locator(".zl").first.inner_text() == "【3肖01】"
        assert four_char.locator("th").nth(2).inner_text() == "开:01鼠对"
        seven_tail = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="七尾中特")).first.locator("tr").first
        assert seven_tail.locator("font").nth(0).inner_text() == "301期:七尾中特"
        assert seven_tail.locator(".zl").first.inner_text() == "【1-2-3-4-5-6-7尾】"
        assert "开:01鼠对" in seven_tail.locator("font").last.inner_text()
        one_sentence = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="一句话")).first.locator("tr").first
        assert one_sentence.locator("font").nth(0).inner_text() == "301期 一句话"
        assert one_sentence.locator(".zl").first.inner_text() == "「鼠来牛来虎兔发财」"
        assert "开:01鼠对" in one_sentence.locator("font").last.inner_text()
        head_tail = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="三头")).first.locator("tr").first
        assert head_tail.locator("th").nth(0).inner_text() == "301期"
        assert head_tail.locator(".zl").first.inner_text() == "三头【0头.1头.2头】四尾【0尾.1尾.2尾.3尾】"
        assert head_tail.locator("th").nth(2).inner_text() == "开:01鼠对"
        kill_wave = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="绝杀①半波")).first.locator("tr").first
        assert kill_wave.locator("font").nth(0).inner_text() == "301期:绝杀①半波"
        assert kill_wave.locator(".zl").first.inner_text() == "【红单】"
        assert "开:01鼠对" in kill_wave.locator("font").last.inner_text()
        expert = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text="精准台湾高手")).first
        assert expert.locator("li a").count() == 14
        assert expert.locator("li").first.inner_text().startswith("301期 后端资料1")
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
            assert "暂无后端资料" not in body_text
            assert not re.search(r"\b(?:0(?:5[2-9]|60)|136|323)期\b", body_text)
            for title in ("发财⑨肖", "平特一肖", "双波中特", "平特③肖", "④肖⑧码", "大小中特", "平特一尾", "绝杀二肖", "绝杀①半波", "绝杀①尾", "一句话中特码"):
                section = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text=title)).first
                assert section.count() == 1, title
                assert f"{expected}01期" in section.inner_text(), title
            for title in ("单双各四肖", "三头", "家禽VS野兽", "七尾中特"):
                section = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text=title)).first
                assert section.count() == 1, title
                assert f"{expected}01期" in section.inner_text(), title
            for title in ("四字解", "精选22码", "稳杀⑦码"):
                section = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text=title)).first
                assert section.count() == 1, title
                assert f"{expected}01期" in section.inner_text(), title
            for title in ():
                section = vendor.locator(".box.pad", has=vendor.locator(".list-title", has_text=title)).first
                assert section.count() == 1, title
                text = section.inner_text()
                assert "暂无后端资料" in text, title
                for supplier_sentinel in ("060期", "059期", "28虎", "26龙", "19猪", "对", "错"):
                    assert supplier_sentinel not in text, (title, supplier_sentinel, text)
        page.goto(f"{base_url}/vendor/twjsz666/155.html", wait_until="domcontentloaded")
        page.wait_for_timeout(250)
        article = page.locator('[data-prediction-article="true"]')
        assert "301期" in article.inner_text()
        assert "2026301期" not in article.inner_text()
        assert "2025060期" not in article.inner_text()
        page.goto(f"{base_url}/vendor/twjsz666/kai.html", wait_until="domcontentloaded")
        assert page.locator(".KJ-TabBox > div.cur .KJ-IFRAME").count() == 1
        assert {lottery_type for _, lottery_type in requests} >= {1, 2, 3}
        browser.close()
