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
                {"moduleKey": "4xiao8ma", "rows": rows},
                {"moduleKey": "pt1xiao", "rows": rows},
                {"moduleKey": "title_5", "rows": rows},
                {"moduleKey": "title_47", "rows": rows},
                {"moduleKey": "pt3xiao", "rows": rows},
                {"moduleKey": "juesha1xiao", "rows": rows},
                {"moduleKey": "danshuangtema", "rows": rows},
                {"moduleKey": "juesha1wei", "rows": rows},
                {"moduleKey": "shuangbo_12ma", "rows": rows},
                {"moduleKey": "shujinguang", "rows": rows},
                {"moduleKey": "9xzt", "rows": rows},
                {"moduleKey": "title_15", "rows": rows},
                {"moduleKey": "title_74", "rows": rows},
                {"moduleKey": "6xzt", "rows": rows},
                {"moduleKey": "liuxiao18ma", "rows": rows},
                {"moduleKey": "hllx", "rows": rows},
                {"moduleKey": "wensha10ma", "rows": rows},
                {"moduleKey": "9xiao12ma", "rows": rows},
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
            page.goto("http://127.0.0.1:3000/twbst528", wait_until="domcontentloaded")

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

            # All reviewed three-column modules must replace supplier terms,
            # values and result placeholders from their own API module.
            for title in (
                "两波突围", "八肖来袭", "家野中特", "杀两半波", "平特一尾", "大小中特",
                "暴富⑦肖", "火爆④头", "平特①肖", "天地+②肖", "四肖中特", "三肖六码",
                "绝杀①肖", "绝杀①波", "单双二肖", "绝杀一肖一尾",
            ):
                section = frame.locator(".lxlm").filter(has=frame.locator(".pb-tit", has_text=title)).first
                history_rows = section.locator("table.mtbl tbody > tr")
                rendered_rows = [history_rows.nth(index).inner_text() for index in range(history_rows.count())]
                assert any("第509期" in value and "开:36马错" in value for value in rendered_rows), (title, rendered_rows)
                assert not any("第323期" in value or "????" in value for value in rendered_rows), (title, rendered_rows)

            # Remaining reviewed three-column supplier sections also require a
            # dedicated backend mapping rather than their static snapshots.
            for title in ("杀肖杀码", "头数单双", "琴棋书画", "本期输尽光"):
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

            assert page_errors == [], page_errors
        finally:
            browser.close()


if __name__ == "__main__":
    main()
