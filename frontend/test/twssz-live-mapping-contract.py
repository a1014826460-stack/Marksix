import os
import time

from playwright.sync_api import sync_playwright


MODULE_KEYS = [
    "7xiao7ma", "sixiao_sima", "wensha10ma", "3zxt", "4xiao8ma", "pt2xiao", "title_66",
    "sanxiao_siwei_xiao", "sanxiao_siwei_wei", "ma24", "daxiao", "3tou", "pt1wei", "pt1xiao",
    "title_48", "wuzhong5ma", "juesha1wei", "juesha1xiao", "juesha2xiao", "jueshabanbo",
    "3hang", "pt3xiao", "shuangbo", "title_47", "title_5", "danshuangtema", "title_143",
]


def payload(lottery_type: str = "3"):
    marker = {"3": "台", "2": "澳", "1": "港"}[lottery_type]
    rows = []
    for module_index, key in enumerate(MODULE_KEYS):
        rows.append({
            "moduleKey": key,
            "rows": [
                {
                    "term": f"{marker}{module_index + 1:03d}{row_index}",
                    "prediction": {"tokens": [f"{marker}{key}-{row_index}"], "text": f"{marker}{key}-{row_index}"},
                    "result": {
                        "isOpened": True,
                        "isCorrect": row_index % 2 == 0,
                        "text": f"{marker}开奖{row_index}",
                    },
                }
                for row_index in range(8)
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
            frame.evaluate("window.TwsszSiteData.preloadPredictions()")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and not prediction_requests:
                page.wait_for_timeout(100)

            assert prediction_requests and all(item == "3:1" for item in prediction_requests), (
                "initial rendering must request only the selected lottery's newest rows: "
                f"{prediction_requests}"
            )

            text = first_table.inner_text()
            assert "台7xiao7ma-0" in text
            assert "台湾 A级猛料大公开" in text


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
                page.wait_for_timeout(1000)
                text = first_table.inner_text()
                assert f"{marker}7xiao7ma-0" in text, (lottery_type, prediction_requests, text)
                assert title in text

            # The full eight-row history is fetched only after the visitor
            # reaches prediction content inside the supplied vendor document.
            # The Taiwan history request may already be active when the user
            # switches draw tabs. Trigger history after Hong Kong is active.
            frame.evaluate("window.dispatchEvent(new Event('scroll'))")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and "1:8" not in prediction_requests:
                page.wait_for_timeout(100)
            assert "1:8" in prediction_requests, (
                "the selected lottery must fetch its own deferred history"
            )

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
                assert "港" in section_text, (index, sections.nth(index).get_attribute("data-prediction-section"), section_text[:300])
                for forbidden in ("204期", "46鸡对", "13马对", "?????"):
                    assert forbidden not in section_text, (
                        index,
                        sections.nth(index).get_attribute("data-prediction-section"),
                        forbidden,
                        section_text[:500],
                    )

            # These previously escaped the generic table scan. They must now
            # be explicit API-backed sections with no vendor historical data.
            for title in ("AI心水玄机论坛", "综合绝杀", "精准天地+两肖"):
                heading = frame.locator(f"text={title}").first
                heading.wait_for(state="attached", timeout=10000)
                container = heading.locator("xpath=following::table[1]")
                assert "港" in container.inner_text(), (title, container.inner_text()[:500])
                for forbidden in ("204期", "46鸡对", "13马对", "?????"):
                    assert forbidden not in container.inner_text(), (title, forbidden, container.inner_text()[:500])

        finally:
            browser.close()


if __name__ == "__main__":
    main()
