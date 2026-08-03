import os
import re
import time

from playwright.sync_api import sync_playwright


def prediction_payload(lottery_type: str):
    marker = {"3": "台", "2": "澳", "1": "港"}[lottery_type]
    rows = []
    for index in range(6):
        rows.append({
            "term": str(510 - index),
            "prediction": {"tokens": [f"{marker}肖{index}", f"{marker}码{index}"], "text": f"{marker}文本{index}"},
            "result": {
                "isOpened": index != 0,
                "isCorrect": index % 2 == 0,
                "code": "20,37,24,28,19,48,36",
                "zodiac": "猪,马,羊,兔,鼠,羊,马",
                "text": f"{marker}开奖{index}",
            },
        })
    daiming_rows = [
        {
            **row,
            "prediction": {"tokens": [f"牛|犏牛{marker}", "鼠|鼠疫", "马|马帮", "蛇|蛇精", "羊|羊脂"]},
        }
        for row in rows
    ]
    tail_rows = [{**row, "prediction": {"tokens": ["1尾", "2尾", "3尾", "4尾", "5尾", "6尾"]}} for row in rows]
    head_parity_rows = [{**row, "prediction": {"tokens": ["0头双", "1头单", "2头双", "3头单", "4头双"]}} for row in rows]
    xiao_code_rows = [
        {
            **row,
            "raw": {"xiao": '["鼠","牛","虎","兔","龙","蛇"]', "code": '["01","02","03","04","05","06"]'},
        }
        for row in rows
    ]
    half_wave_rows = [{**row, "prediction": {"tokens": ["红单", "蓝双"]}} for row in rows]
    formula_rows = [
        {
            **row,
            "raw": {"res_code": "20,37,24,28,19,48,36", "formula": {"parity": {"labels": ["单"], "is_correct": True}, "size": {"labels": ["大"], "is_correct": False}, "tails": {"labels": ["1", "2", "3", "4"], "is_correct": True}}},
        }
        for row in rows
    ]
    yixiao_rows = [
        {
            **row,
            "raw": {"code": "台码0,台码1,台码2,台码3,台码4,台码5,台码6,台码7,台码8,台码9", "xiao": "台肖0,台肖1,台肖2,台肖3,台肖4,台肖5,台肖6,台肖7,台肖8"},
        }
        for row in rows
    ]
    return {
        "ok": True,
        "data": {
            "canonical_modules": [
                {"moduleKey": "yijuzhenyan", "rows": rows + [rows[0]]},
                {"moduleKey": "shuangbo", "rows": rows},
                {"moduleKey": "shuangbo_12ma", "rows": rows},
                {"moduleKey": "7xiao7ma", "rows": rows},
                {"moduleKey": "pt2xiao", "rows": rows},
                {"moduleKey": "jueshabanbo", "rows": rows},
                {"moduleKey": "pt1wei", "rows": rows},
                {"moduleKey": "daxiao", "rows": rows},
                {"moduleKey": "4xiao8ma", "rows": [
                    {**row, "prediction": {"tokens": ["羊|12,24", "马|01,13", "狗|09,21", "鼠|07,19"]}}
                    for row in rows
                ]},
                {"moduleKey": "pt1xiao", "rows": rows},
                {"moduleKey": "title_5", "rows": [
                    {**row, "prediction": {"tokens": ["地肖|蛇,羊,鸡,狗,鼠,虎"]}, "raw": {"xiao": "猴,猪"}}
                    for row in rows
                ]},
                {"moduleKey": "title_47", "rows": rows},
                {"moduleKey": "pt3xiao", "rows": rows},
                {"moduleKey": "juesha1xiao", "rows": rows},
                {"moduleKey": "danshuangtema", "rows": rows},
                {"moduleKey": "juesha1wei", "rows": rows},
                {"moduleKey": "shuangbo_12ma", "rows": rows},
                {"moduleKey": "shujinguang", "rows": rows},
                {"moduleKey": "daimingxiao", "rows": daiming_rows},
                {"moduleKey": "liuweichute", "rows": tail_rows},
                {"moduleKey": "toudanshuang", "rows": head_parity_rows},
                {"moduleKey": "liuxiaoliuma", "rows": xiao_code_rows},
                {"moduleKey": "shaliangbanbo", "rows": half_wave_rows},
                {"moduleKey": "dujia_gongshi", "rows": formula_rows},
                {"moduleKey": "9xzt", "rows": rows},
                {"moduleKey": "title_15", "rows": rows},
                {"moduleKey": "title_74", "rows": rows},
                {"moduleKey": "6xzt", "rows": rows},
                {"moduleKey": "liuxiao18ma", "rows": rows},
                {"moduleKey": "hllx", "rows": rows},
                {"moduleKey": "wensha10ma", "rows": rows},
                {"moduleKey": "9xiao12ma", "rows": yixiao_rows},
                {"moduleKey": "title_45", "rows": rows},
                {"moduleKey": "title_48", "rows": rows},
                {"moduleKey": "sanxiaozhongte", "rows": rows},
                {"moduleKey": "title_197", "rows": rows},
                {"moduleKey": "juesha2xiao", "rows": rows},
                {"moduleKey": "dxztt1", "rows": rows},
                {"moduleKey": "qianhou_texiao", "rows": rows},
                {"moduleKey": "sihangzhongte", "rows": rows},
                {"moduleKey": "siji3", "rows": rows},
                {"moduleKey": "siduanzhongte", "rows": rows},
                {"moduleKey": "wuzhong5ma", "rows": rows},
                {"moduleKey": "juesha3xiao", "rows": rows},
                {"moduleKey": "3tou", "rows": rows},
                {"moduleKey": "3hang", "rows": rows},
                {"moduleKey": "qinqi", "rows": rows},
                {"moduleKey": "shujinguang", "rows": rows},
                {"moduleKey": "sitouzhongte", "rows": rows},
                {"moduleKey": "qianhou_texiao", "rows": rows},
                {"moduleKey": "siji3", "rows": rows},
                {"moduleKey": "4xiao8ma", "rows": rows},
                {"moduleKey": "tw_pmt_image", "rows": [
                    {**row, "prediction": {"imageUrl": f"/uploads/predictions/{lottery_type}-{index}.png", "tokens": []}}
                    for index, row in enumerate(rows)
                ]},
                *[
                    {"moduleKey": module_key, "rows": [
                        {**row, "prediction": {"imageUrl": f"/uploads/predictions/{module_key}-{lottery_type}-{index}.png", "tokens": []}}
                        for index, row in enumerate(rows)
                    ]}
                    for module_key in ("sxztu", "pmtj_image")
                ],
            ]
        },
    }


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
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            prediction_requests = []
            page_errors = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))

            def fulfill_prediction(route):
                query = route.request.url.split("?", 1)[1]
                lottery_type = next(item.split("=", 1)[1] for item in query.split("&") if item.startswith("lottery_type="))
                history_limit = next(item.split("=", 1)[1] for item in query.split("&") if item.startswith("history_limit="))
                prediction_requests.append(f"{lottery_type}:{history_limit}")
                route.fulfill(json=prediction_payload(lottery_type))

            page.route("**/api/sites/twbst528/prediction-modules?**", fulfill_prediction)
            page.route("**/api/sites/twbst528/draw?**", lambda route: route.fulfill(json={"ok": True, "data": {"issue": "510"}}))
            page.goto(os.environ.get("SITE_TEST_BASE_URL", "http://127.0.0.1:3000") + "/twbst528", wait_until="domcontentloaded")

            deadline = time.monotonic() + 10
            frame = None
            while time.monotonic() < deadline:
                frame = next((item for item in page.frames if item.url.split("?", 1)[0].endswith("/vendor/twbst528/index.html")), None)
                if frame:
                    break
                page.wait_for_timeout(100)
            assert frame is not None, "twbst528 vendor frame did not load"

            # The supplier tab panels must embed the shared, same-origin draw
            # component rather than leave their original blank iframe URL.
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and not frame.locator(".KJ-IFRAME").count():
                page.wait_for_timeout(100)
            draw_frame = frame.locator(".KJ-IFRAME").first
            draw_src = draw_frame.get_attribute("src") or ""
            assert "/vendor/shengshi8800/kj/local.html?lottery_type=" in draw_src
            assert "about:blank" not in draw_src

            # The supplier's mobile media query must leave room for both the
            # 36px tab strip and the complete 200px same-origin draw frame.
            # Regressions here previously clipped the issue and refresh area.
            page.set_viewport_size({"width": 390, "height": 844})
            for lottery_type in ("3", "2", "1"):
                frame.locator(f".KJ-TabBox a[data-lottery-type='{lottery_type}']").click()
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    iframe_height = frame.locator(".KJ-IFRAME").first.evaluate("node => node.getBoundingClientRect().height")
                    if iframe_height >= 200:
                        break
                    page.wait_for_timeout(100)
                geometry = frame.locator(".KJ-TabBox").first.evaluate("""box => {
                    const iframe = box.querySelector('.KJ-IFRAME').getBoundingClientRect();
                    const parent = box.getBoundingClientRect();
                    return { parentHeight: parent.height, iframeTop: iframe.top, iframeBottom: iframe.bottom, parentTop: parent.top, parentBottom: parent.bottom };
                }""")
                assert geometry["parentHeight"] >= 236, geometry
                assert geometry["iframeTop"] >= geometry["parentTop"], geometry
                assert geometry["iframeBottom"] <= geometry["parentBottom"], geometry

            page.set_viewport_size({"width": 1280, "height": 720})
            frame.locator(".KJ-TabBox a[data-lottery-type='3']").click()

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and "3:6" not in prediction_requests:
                page.wait_for_timeout(100)
            assert "3:6" in prediction_requests, prediction_requests

            first_table = frame.locator("#zhenyan_ping_xiao")
            assert first_table.locator("tr").count() == 6
            first_row = first_table.locator("tr").first.inner_text()
            assert "第510期" in first_row and "台文本0" in first_row and "开:待开奖" in first_row, first_row
            assert "第233期" not in first_table.inner_text() and "晴川历历汉阳树" not in first_table.inner_text()
            second_row = first_table.locator("tr").nth(1).inner_text()
            assert "开:36马错" in second_row, second_row

            tiandi = frame.locator(".lxlm").filter(has=frame.locator(".pb-tit", has_text="天地+②肖")).first
            assert "第510期" in tiandi.inner_text() and "地肖" in tiandi.inner_text(), tiandi.inner_text()[:300]

            # The dedicated, pre-existing image slot must receive only this
            # site's Taiwan 跑马图 URL; it must never reuse another site's image.
            pmt_image = frame.locator("[data-prediction-image='tw_pmt_image']")
            assert pmt_image.count() == 1
            assert pmt_image.get_attribute("src") == "/uploads/predictions/3-0.png"
            assert pmt_image.get_attribute("hidden") is None

            for module_key in ("sxztu", "pmtj_image"):
                image = frame.locator(f"img[data-prediction-image='{module_key}']")
                assert image.count() == 1
                assert image.get_attribute("src") == f"/uploads/predictions/{module_key}-3-0.png"
                assert image.get_attribute("hidden") is None
                assert image.get_attribute("loading") == "lazy"
                assert image.get_attribute("decoding") == "async"

            # All reviewed three-column modules must replace supplier terms,
            # values and result placeholders from their own API module.
            for title in (
                "两波突围", "八肖来袭", "家野中特", "杀两半波", "平特一尾", "大小中特",
                "暴富⑦肖", "平特①肖", "四肖中特", "三肖六码",
                "绝杀①肖", "绝杀①波", "单双二肖", "绝杀一肖一尾",
            ):
                if title == "杀两半波":
                    continue
                section = frame.locator(".lxlm").filter(has=frame.locator(".pb-tit", has_text=title)).first
                history_rows = section.locator("table.mtbl tbody > tr")
                rendered_rows = [history_rows.nth(index).inner_text() for index in range(history_rows.count())]
                assert any("第509期" in value and "开:36马错" in value for value in rendered_rows), (title, rendered_rows)
                assert not any("第323期" in value or "????" in value for value in rendered_rows), (title, rendered_rows)

            # Remaining reviewed three-column supplier sections also require a
            # dedicated backend mapping rather than their static snapshots.
            for title in ("杀肖杀码", "琴棋书画", "本期输尽光"):
                section = frame.locator(".lxlm").filter(has=frame.locator(".pb-tit", has_text=title)).first
                rows_text = section.locator("table tbody > tr").all_inner_texts()
                assert any("第509期" in value and "开:36马错" in value for value in rows_text), (title, rows_text)
                assert not any("第323期" in value or "????" in value for value in rows_text), (title, rows_text)

            forum = frame.locator(".lxlm, .tzlb").filter(has=frame.locator(".pb-tit", has_text="高手论坛")).first
            assert "510期:台湾百事通" in forum.locator("li").first.inner_text()

            newly_dynamic_titles = (
                "代号生肖", "独家公式", "六尾出特", "六肖六码", "一肖一码", "码友来料参考",
                "梭哈⑦尾", "六肖十八码", "红蓝绿肖", "五行来料", "绝杀⑩码", "⑥肖12码",
                "黑白三肖", "阴阳⑧码中特", "18码中特", "③肖防③码", "8肖16码", "三期计划",
                "⑤肖⑩码", "稳中单双", "综合绝杀", "大小+①头", "四肖八码", "日夜特肖",
                "左右中特", "前后中特", "七尾四行", "四季九肖",
                "四段中特",
            )
            for title in newly_dynamic_titles:
                section = frame.locator(".lxlm").filter(has=frame.locator(".pb-tit", has_text=title)).first
                section_text = section.inner_text()
                assert re.search(r"(?:第)?510\s*期", section_text), (title, section_text[:300])
                assert "233期" not in section_text and "323期" not in section_text, (title, section_text[:300])
                assert "????" not in section_text, (title, section_text[:300])
                assert "暂无后端资料" not in section_text, (title, section_text[:300])

            # Reused mature backend modules must preserve the vendor's visual
            # grouping: no raw implementation delimiters or dense unbroken
            # payloads may replace a card/table data slot.
            for title in ("⑥肖12码", "③肖防③码", "8肖16码", "⑤肖⑩码", "三期计划", "综合绝杀"):
                section = frame.locator(".lxlm").filter(has=frame.locator(".pb-tit", has_text=title)).first
                assert section.locator("br").count() > 0, (title, section.inner_text()[:300])
                assert "|" not in section.inner_text(), (title, section.inner_text()[:300])

            # The exact source modes now drive these slots, so no static issue
            # or supplier placeholder may survive after the adapter renders.
            for title in ("代号生肖", "六尾出特", "六肖六码", "杀两半波"):
                section = frame.locator(".lxlm").filter(has=frame.locator(".pb-tit", has_text=title)).first
                assert re.search(r"(?:第)?510\s*期", section.inner_text()), (title, section.inner_text()[:300])
                assert "暂无后端资料" not in section.inner_text(), (title, section.inner_text()[:300])
                assert "323期" not in section.inner_text() and "????" not in section.inner_text(), (title, section.inner_text()[:300])

            # Empty preferred modules must fall back to a populated mature
            # module instead of masking the usable source object.
            for title in ("一肖一码", "黑白三肖", "⑤肖⑩码"):
                section = frame.locator(".lxlm").filter(has=frame.locator(".pb-tit", has_text=title)).first
                section_text = section.inner_text()
                assert re.search(r"(?:第)?510\s*期", section_text), (title, section_text[:300])
                assert "暂无后端资料" not in section_text, (title, section_text[:300])
            five_xiao = frame.locator(".lxlm").filter(has=frame.locator(".pb-tit", has_text="⑤肖⑩码")).first
            assert "台肖0台码0" in five_xiao.inner_text(), five_xiao.inner_text()[:300]
            assert "|" not in five_xiao.inner_text(), five_xiao.inner_text()[:300]

            formula = frame.locator(".lxlm").filter(has=frame.locator(".pb-tit", has_text="独家公式")).first
            formula_text = formula.inner_text()
            assert "510期 --------------------- T-- 【单数】?" in formula_text, formula_text[:500]
            assert "509期 20-37-24-28-19-48 T36 【单数】x" in formula_text, formula_text[:500]
            assert "510期 --------------------- T-- 【大数】?" in formula_text, formula_text[:500]
            assert "510期 --------------------- T-- 【1234尾】?" in formula_text, formula_text[:500]

            yixiao = frame.locator(".lxlm").filter(has=frame.locator(".pb-tit", has_text="一肖一码")).first
            yixiao_rows = yixiao.locator("table.mtbl").first.locator("tbody > tr")
            assert yixiao_rows.count() == 12
            assert "台码0" in yixiao_rows.nth(0).inner_text()
            assert "台码0.台码1.台码2" in yixiao_rows.nth(1).inner_text()

            # The supplier double-wave card is one row per issue, with a
            # preserved three-font header and the supplied coloured wave lines.
            double_wave = frame.locator("[data-prediction-section='shuangbo_12ma']").filter(has_text="双波⑩码")
            assert double_wave.count() == 1
            wave_rows = double_wave.locator("table tbody > tr")
            assert wave_rows.count() == 6
            first_wave = wave_rows.first.inner_text()
            assert "第510期" in first_wave and "【双波⑩码】" in first_wave and "开:待开奖" in first_wave, first_wave
            assert "233期" not in double_wave.inner_text() and "?????" not in double_wave.inner_text()
            assert wave_rows.first.locator("td p b > font").count() == 3

            footer = frame.locator("#legacy-attribute-anchor")
            assert footer.count() == 1
            assert footer.locator("#legacy-attribute-gallery img").count() == 3
            assert footer.locator("#legacy-attribute-gallery img").nth(0).get_attribute("src") == "/uploads/image/20250322/1742580086567063.png"
            footer.scroll_into_view_if_needed()
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and not all(footer.locator("#legacy-attribute-gallery img").evaluate_all("images => images.map(image => image.complete && image.naturalWidth > 0)")):
                page.wait_for_timeout(100)
            assert footer.locator("#legacy-attribute-gallery img").evaluate_all("images => images.map(image => image.complete && image.naturalWidth > 0)") == [True, True, True]

            for lottery_type, label, marker, title_prefix in (("2", "澳门彩", "澳", "澳门"), ("1", "香港彩", "港", "香港")):
                frame.locator(f".KJ-TabBox a[data-lottery-type='{lottery_type}']").click()
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and f"{lottery_type}:6" not in prediction_requests:
                    page.wait_for_timeout(100)
                assert f"{lottery_type}:6" in prediction_requests, prediction_requests
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and f"{marker}文本0" not in first_table.locator("tr").first.inner_text():
                    page.wait_for_timeout(100)
                assert f"{marker}文本0" in first_table.locator("tr").first.inner_text()
                assert f"{title_prefix}百事通【一句中平特】" in frame.locator(".pb-tit").first.inner_text(), frame.locator(".pb-tit").first.inner_text()
                assert f"510期:{title_prefix}百事通" in forum.locator("li").first.inner_text()

            # Selecting an already cached lottery must use its resolved data,
            # rather than treating the cached result object as a Promise.
            frame.locator(".KJ-TabBox a[data-lottery-type='3']").click()
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and "台文本0" not in first_table.locator("tr").first.inner_text():
                page.wait_for_timeout(100)
            assert "台文本0" in first_table.locator("tr").first.inner_text()
            assert "510期:台湾百事通" in forum.locator("li").first.inner_text()

            assert page_errors == [], page_errors
        finally:
            browser.close()


if __name__ == "__main__":
    main()
