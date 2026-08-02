import os
import time

from playwright.sync_api import sync_playwright


MODULE_ROWS = {
    "7xiao7ma": [["猴", "龙", "羊", "马", "猪", "狗", "鼠"]],
    "sixiao_sima": [["猴", "龙", "羊", "马"]],
    "wensha10ma": [["35", "47", "24", "38", "27", "39", "13", "33", "43", "15"]],
    "3zxt": [["猴", "龙", "羊"]],
    "4xiao8ma": [["35", "47", "24", "38", "27", "39", "13", "33"]],
    "pt2xiao": [["猴", "龙"]],
    "danshuangtema": [["单", "双", "单"]],
    # title_66 is the approved closest replacement for the supplied
    # 15码中特 cards. Its five tail groups can generate the card's 3/5-tail
    # and 15/9-code slots without inventing vendor data.
    "title_66": [["2尾|02,12,22", "4尾|04,14,24", "6尾|06,16,26", "8尾|08,18,28", "0尾|10,20,30"]],
    "sanxiao_siwei_xiao": [["羊", "蛇", "虎", "马"], ["虎", "马", "猴", "兔"]],
    "sanxiao_siwei_wei": [["3", "7", "6", "5"], ["4", "9", "8", "6"]],
    "ma24": [
        [f"{value:02d}" for value in range(1, 25)],
        [f"{value:02d}" for value in range(25, 49)],
    ],
    "title_48": [["猴", "龙", "羊", "马", "猪", "狗", "鼠", "35", "47", "24", "38"]],
    "shuangbo": [
        [
            "绿波|43,33,28,17,16,27,05,49,32,06",
            "蓝波|20,26,14,42,37,03,47,10,48,04",
        ],
    ],
    "sxztu": [["四不像"]],
}
MODULE_KEYS = [
    *MODULE_ROWS,
    "daxiao", "3tou", "pt1wei", "pt1xiao", "title_48", "wuzhong5ma",
    "juesha1wei", "juesha1xiao", "juesha2xiao", "jueshabanbo", "3hang",
    "pt3xiao", "shuangbo", "title_47", "title_5", "danshuangtema", "title_143",
]



def payload(lottery_type: str = "3"):
    marker = {"3": "台", "2": "澳", "1": "港"}[lottery_type]
    rows = []
    for module_index, key in enumerate(MODULE_KEYS):
        rows.append({
            "moduleKey": key,
            "rows": [
                {
                    "term": str(207 - row_index),
                    "prediction": {
                        "tokens": (
                        MODULE_ROWS[key][row_index % len(MODULE_ROWS[key])]
                        if key in {"sanxiao_siwei_xiao", "sanxiao_siwei_wei"}
                        else MODULE_ROWS.get(key, [[f"{marker}{key}-{row_index}"]])[row_index % len(MODULE_ROWS.get(key, [[f"{marker}{key}-{row_index}"]]))]
                    ),
                        "text": f"{marker}{key}-{row_index}",
                        "imageUrl": (
                            f"/uploads/predictions/{marker}-sxztu-{row_index}.jpg"
                            if key == "sxztu"
                            else ""
                        ),
                    },
                    "result": {
                        "isOpened": row_index != 0,
                        "isCorrect": row_index % 2 == 0,
                        # The leading issue proves hit formatting must use the
                        # canonical code instead of the first text number.
                        "code": "02",
                        "text": f"{marker}第999期，开奖02" if row_index else "待开奖",
                    },
                }
                # The supplied 连肖连尾 section has sixteen existing issue
                # groups, so its complete request must provide every slot.
                for row_index in range(16)
            ],
        })
    return {"ok": True, "data": {"canonical_modules": rows}}


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
            page = browser.new_page(viewport={"width": 1280, "height": 300})
            prediction_requests = []

            def fulfill_prediction(route):
                history_limit = route.request.url.split("history_limit=", 1)[1].split("&", 1)[0]
                lottery_type = route.request.url.split("lottery_type=", 1)[1].split("&", 1)[0]
                prediction_requests.append(f"{lottery_type}:{history_limit}")
                route.fulfill(json=payload(lottery_type))

            page.route(
                "**/api/sites/twssz/prediction-modules?**",
                fulfill_prediction,
            )
            page.goto("http://127.0.0.1:3000/twssz", wait_until="domcontentloaded")
            assert page.title() == "台湾神算子，算无遗漏", page.title()
            icon_href = page.locator("head link[rel='icon']").first.get_attribute("href")
            assert icon_href == "/vendor/twssz/static/file/favicon.ico", icon_href
            deadline = time.monotonic() + 10
            frame = None
            while time.monotonic() < deadline:
                frame = next(
                    (
                        item
                        for item in page.frames
                        if item.url.split("?", 1)[0].endswith("/vendor/twssz/index.html")
                    ),
                    None,
                )
                if frame:
                    break
                page.wait_for_timeout(100)
            assert frame is not None, "twssz vendor frame did not load"
            first_table = frame.locator(".dz_content08ab2d table").first
            first_table.locator("td").first.wait_for(state="attached", timeout=10000)
            assert "暂无期号" not in frame.locator("body").inner_text()
            frame.evaluate("window.TwsszSiteData.preloadPredictions()")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and not prediction_requests:
                page.wait_for_timeout(100)

            assert "3:1" in prediction_requests, (
                "initial rendering must request the selected lottery's newest rows: "
                f"{prediction_requests}"
            )

            text = first_table.inner_text()
            assert "台湾 A级猛料大公开" in text
            assert "七肖" in text and "猴龙羊马猪狗鼠" in text
            assert "⑩码" in text and "35.47.24.38.27.39.13.33.43.15" in text
            assert "【" not in text, "A级表必须保留供应商字段布局，而非通用原始 token 行"


            draw_frame = next(
                (item for item in page.frames if item.url.split("?", 1)[0].endswith("/vendor/twssz/kai.html")),
                None,
            )
            assert draw_frame is not None, "twssz draw frame did not load"
            for lottery_type, label, marker, title in (
                ("2", "澳门彩", "澳", "澳门 A级猛料大公开"),
                ("1", "香港彩", "港", "香港 A级猛料大公开"),
            ):
                draw_frame.get_by_text(label, exact=True).click()
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if f"{lottery_type}:1" in prediction_requests:
                        break
                    page.wait_for_timeout(100)
                while time.monotonic() < deadline:
                    if f"{lottery_type}:16" in prediction_requests:
                        break
                    page.wait_for_timeout(100)
                page.wait_for_timeout(1000)
                text = first_table.inner_text()
                assert title in text
                assert "七肖" in text and "⑩码" in text, text
                assert f"{lottery_type}:16" in prediction_requests, prediction_requests

            sxztu_image = frame.locator("img[data-prediction-image='sxztu']")
            assert sxztu_image.get_attribute("src") == "/uploads/predictions/港-sxztu-0.jpg"
            assert sxztu_image.get_attribute("hidden") is None

            # The full eight-row history is fetched only after the visitor
            # reaches prediction content inside the supplied vendor document.
            # The Taiwan history request may already be active when the user
            # switches draw tabs. Trigger history after Hong Kong is active.
            frame.evaluate("window.dispatchEvent(new Event('scroll'))")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and "1:16" not in prediction_requests:
                page.wait_for_timeout(100)
            assert "1:16" in prediction_requests, (
                "the selected lottery must request all sixteen supplied history groups"
            )

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and "207期" not in first_table.inner_text():
                page.wait_for_timeout(100)

            # A future prediction has no draw result. It must render exactly as
            # 待开奖, never as a made-up missed result such as 待开奖错.
            assert "待开奖错" not in frame.locator("body").inner_text()

            grade_text = first_table.inner_text()
            assert "207期" in grade_text and "七肖" in grade_text and "猴龙羊马猪狗鼠" in grade_text, grade_text
            assert "⑩码" in grade_text and "35.47.24.38.27.39.13.33.43.15" in grade_text
            assert "开：待开奖" in grade_text
            assert "暂无期号" not in frame.locator("body").inner_text()

            grade_tables = frame.locator("[data-prediction-section='grade-a'] table")
            assert grade_tables.count() == 8
            assert "200期" in grade_tables.nth(7).inner_text(), grade_tables.nth(7).inner_text()

            lianxiao_rows = frame.locator("#top_14 + table + div tr")
            assert lianxiao_rows.count() == 32
            assert "192期" in lianxiao_rows.nth(30).inner_text(), "16 existing linked groups need 16 API rows"

            lianxiao = frame.locator("#top_14 + table + div").first
            lianxiao_text = lianxiao.inner_text()
            assert "207期" in lianxiao_text and "开 待开奖" in lianxiao_text, lianxiao_text
            assert "【3.7尾】【6.5尾】" in lianxiao_text and "【羊蛇】【虎马】" in lianxiao_text
            assert "港sanxiao_siwei_xiao" not in lianxiao_text

            m24_rows = frame.locator("[data-prediction-section='ma24'] tr.zt24mtr")
            assert m24_rows.count() >= 4
            assert m24_rows.nth(0).locator("td").first.inner_text() == "01"
            assert m24_rows.nth(1).locator("td").last.inner_text() == "24"
            assert m24_rows.nth(2).locator("td").first.inner_text() == "25"
            assert m24_rows.nth(3).locator("td").last.inner_text() == "48"
            ma24_headings = frame.locator("[data-site-slot='ma24-heading']")
            assert ma24_headings.count() == 8
            for index in range(8):
                heading_row = ma24_headings.nth(index)
                heading = heading_row.inner_text()
                assert f"{207 - index}期 精选24码;准确率绝对100%;大胆下注!" in heading, heading
                # Each supplied issue card has a heading, an untouched image
                # row, then two fixed 12-cell number rows.  The heading must
                # remain attached to its own number grid.
                first_number, last_number = (1, 24) if index % 2 == 0 else (25, 48)
                assert heading_row.locator("xpath=following-sibling::tr[2]").locator("td").first.inner_text() == f"{first_number:02d}"
                assert heading_row.locator("xpath=following-sibling::tr[3]").locator("td").last.inner_text() == f"{last_number:02d}"
            assert "待加载期" not in ma24_headings.first.inner_text()

            # 精准四肖标题后的 15 码中特是独立的复杂卡片。所有既有槽位必须
            # 替换为后端数据，不能仅让相邻区域含有 API 文本就通过。
            cards = frame.locator(".bbzhong122")
            assert cards.count() == 8
            first_card_text = cards.first.inner_text()
            assert "香港 15码中特" in first_card_text
            assert "207期必中三尾：2-4-6" in first_card_text
            assert "207期必中五尾：2-4-6-8-0" in first_card_text
            assert "必中15码：02.12.22.04.14.24.06.16.26.08.18.28.10.20.30" in first_card_text
            assert "必中九码：02.12.22.04.14.24.06.16.26" in first_card_text
            assert "207期一尾一码：（02）" in first_card_text
            assert "200期" in cards.nth(7).inner_text(), cards.nth(7).inner_text()
            for forbidden in ("执笔先生", "gat566.cc", "205期必中三尾", "单车变宝马", "14.24.04.18.48"):
                assert forbidden not in first_card_text, (forbidden, first_card_text)

            # A hit must use the vendor's existing yellow background marker,
            # rather than yellow foreground text that is not visually clear.
            hit_number = cards.nth(1).locator("font[bgcolor='#FFFF00']")
            assert hit_number.count() == 2 and all(
                hit_number.nth(index).inner_text().strip(".") == "02"
                for index in range(hit_number.count())
            ), (
                "命中号码必须使用供应商既有的黄色高亮节点"
            )

            # AI心水 uses its supplied multi-line card layout. It must not be
            # routed through the generic sibling-offset summary renderer.
            ai_root = frame.locator("[data-prediction-section='title_48-ai']")
            assert ai_root.count() == 1
            ai_text = ai_root.inner_text()
            assert "207期" in ai_text and "＜嫩＞" in ai_text
            assert "生肖:猴龙羊马猪狗" in ai_text and "35.47.24.38" in ai_text
            for label in ("波色:", "大小:", "尾数:"):
                assert label in ai_text, ai_text
            assert "07.19" not in ai_text, "AI module must not invent zodiac-derived numbers"
            assert "AI心水玄机论坛：" not in ai_text
            assert "待加载期" not in ai_text

            aaa_cards = frame.locator("[data-site-slot='aaa-grade-card']")
            assert aaa_cards.count() == 8
            assert frame.locator("[data-prediction-section='grade-a'] [data-site-slot='aaa-grade-card']").count() == 0
            for index in range(8):
                card = aaa_cards.nth(index)
                assert card.locator("tr").count() == 5
                assert card.locator("tr").nth(0).locator("td").count() == 1
                assert f"{207 - index}期 AAA级大公开" in card.inner_text()
                for row_index, (label, count) in enumerate((("⑨", 9), ("⑧", 8), ("⑦", 7), ("⑥", 6)), start=1):
                    detail = card.locator("tr").nth(row_index)
                    outer = detail.locator("td > span > strong > font[color='#fa035a']")
                    assert outer.count() == 1
                    assert f"{207 - index}期{label}肖中特:" in outer.inner_text()
                    # Individual zodiac slots must retain the vendor's font /
                    # highlight nodes instead of being collapsed into a line.
                    values = outer.locator(":scope > font, :scope > span")
                    assert values.count() == count
                    assert "".join(values.all_inner_texts()) == "猴龙羊马猪狗鼠牛虎"[:count]

            jia_ye = frame.get_by_text("家野二肖", exact=True).locator("xpath=ancestor::table[1]/following-sibling::div[1]")
            jia_ye_text = jia_ye.inner_text()
            assert "207期 【野兽+猴龙】 开 待开奖" in jia_ye_text, jia_ye_text
            assert "206期 【野兽+猴龙】 开 港第999期，开奖02错" in jia_ye_text, jia_ye_text
            assert "家禽：牛、马、羊、鸡、狗、猪" in jia_ye_text
            assert "野兽：鼠、虎、兔、龙、蛇、猴" in jia_ye_text

            # The paired cards retain their supplied header/detail formatting:
            # issue before the blue module label, the vendor "开" literal and
            # two visual detail lines rather than a generic text-row summary.
            for section_key, title in (
                ("title_48", "╔8肖16码╗"),
                ("wuzhong5ma", "『内幕⑤不中』"),
                ("pt3xiao", "╔三肖六码╗"),
                ("shuangbo", "『双波10码』"),
            ):
                section = frame.locator(f"[data-prediction-section='{section_key}']")
                header = section.locator("tr").nth(0)
                detail = section.locator("tr").nth(1)
                assert "207期" in header.inner_text() and title in header.inner_text(), header.inner_text()
                assert "开" in header.inner_text() and "待开奖" in header.inner_text(), header.inner_text()
                assert header.locator("td > p > b > font").count() == 1
                assert header.locator("td > p > b > font[color='#0000FF']").count() == 1
                assert header.locator("td > p > b > font[color='#FF0000']").count() == 1
                assert detail.locator("br").count() == 1, detail.inner_text()

            double_wave = frame.locator("[data-prediction-section='shuangbo']")
            double_wave_header = double_wave.locator("tr").nth(0).inner_text()
            double_wave_detail = double_wave.locator("tr").nth(1).inner_text()
            assert "207期" in double_wave_header and "『双波10码』开 待开奖" in double_wave_header
            assert "绿波:43.33.28.17.16.27.05.49.32.06" in double_wave_detail
            assert "蓝波:20.26.14.42.37.03.47.10.48.04" in double_wave_detail

            four_zodiac = frame.locator("[data-prediction-section='title_47-四肖中特']")
            assert four_zodiac.count() == 1
            assert "207期 四肖中特：猴·龙·羊·马" in four_zodiac.inner_text()

            composite = frame.get_by_text("综合绝杀", exact=True).locator("xpath=ancestor::table[1]/following-sibling::table[1]")
            composite_text = composite.inner_text()
            for heading, line in (
                ("（绝杀二肖）", "207期稳杀(2)肖【"),
                ("（绝杀二尾）", "207期稳杀(2)尾【"),
                ("（绝杀一头）", "207期稳杀(1)头【"),
                ("（绝杀一行）", "207期稳杀(1)头【"),
            ):
                assert heading in composite_text and line in composite_text, composite_text[:2000]
            assert composite_text.count("待开奖") == 4, composite_text[:2000]

            dan_shuang = frame.locator("#con_jihuadanshuang50000ww_1")
            dan_shuang_text = dan_shuang.inner_text()
            for term in range(207, 199, -1):
                assert f"{term}期" in dan_shuang_text, dan_shuang_text
            # The frontend must not repeat a response row when the backend
            # contains duplicate issue records. Empty vendor rows remain empty.
            pingte_wei = frame.locator("#top_3").locator("xpath=following-sibling::div[contains(@class, 'dz_content08ab2d')][1]")
            pingte_wei_text = pingte_wei.inner_text()
            assert pingte_wei_text.count("207期") == 1
            assert pingte_wei_text.count("206期") == 1
            assert "暂无期号" not in pingte_wei_text

            tiandi = frame.get_by_text("精准天地+两肖", exact=True).locator("xpath=ancestor::table[1]/following-sibling::table[1]")
            tiandi_text = tiandi.inner_text()
            assert tiandi_text.count("207期") == 1
            assert tiandi_text.count("206期") == 1
            assert "暂无期号" not in tiandi_text

            # Every mapped section must contain the selected Hong Kong response
            # only: no vendor term, result, placeholder or static hit data.
            sections = frame.locator("[data-prediction-section]")
            assert sections.count() >= 18, "every reviewed prediction area must be API-backed"
            assert frame.locator("[data-prediction-row]").count() >= 128, (
                "each reviewed prediction section must retain eight API-backed history rows"
            )
            section_keys = [
                sections.nth(index).get_attribute("data-prediction-section")
                for index in range(sections.count())
            ]
            for required_key in (
                "sanxiao_siwei_xiao",
                "wuzhong5ma",
                "title_47",
                "title_5",
                "juesha2xiao",  # Composite section renders all four approved kill modules.
            ):
                assert any(key == required_key or key.startswith(required_key + "-") for key in section_keys), (
                    f"{required_key} has no mapped vendor section"
                )
            for index in range(sections.count()):
                section_text = sections.nth(index).inner_text()
                section_key = sections.nth(index).get_attribute("data-prediction-section")
                # Presentation-only cards such as 一头一码 legitimately render
                # the selected canonical values without a regional marker.
                if not (str(section_key).startswith("3tou-head") or section_key in {"aaa-grade", "pt2xiao", "danshuangtema"}):
                    assert "港" in section_text, (index, section_key, section_text[:300])
            for forbidden in ("46鸡对", "13马对", "?????"):
                    assert forbidden not in section_text, (
                        index,
                        sections.nth(index).get_attribute("data-prediction-section"),
                        forbidden,
                        section_text[:500],
                    )

            body_text = frame.locator("body").inner_text()
            for forbidden in ("暂无期号", "暂无后端资料", "待加载期"):
                assert forbidden not in body_text, forbidden

            # These previously escaped the generic table scan. They must now
            # be explicit API-backed sections with no vendor historical data.
            for title in ("AI心水玄机论坛", "综合绝杀", "精准天地+两肖"):
                heading = frame.locator(f"text={title}").first
                heading.wait_for(state="attached", timeout=10000)
                container = heading.locator("xpath=following::table[1]")
                assert "港" in container.inner_text(), (title, container.inner_text()[:500])
                for forbidden in ("46鸡对", "13马对", "?????"):
                    assert forbidden not in container.inner_text(), (title, forbidden, container.inner_text()[:500])

        finally:
            browser.close()


if __name__ == "__main__":
    main()
