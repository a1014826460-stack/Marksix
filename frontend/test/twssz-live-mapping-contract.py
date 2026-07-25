import os
import time

from playwright.sync_api import sync_playwright


MODULES = [
    ("7xiao7ma", "2026173", ["鼠|01", "牛|02", "虎|03", "兔|04", "龙|05", "蛇|06", "马|07"]),
    ("sixiao_sima", "2026173", ["鼠|01", "牛|02", "虎|03", "兔|04"]),
    ("wensha10ma", "2026173", ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]),
    ("3zxt", "2026173", ["鼠", "牛", "虎"]),
    ("4xiao8ma", "2026173", ["鼠|01,13", "牛|02,14", "虎|03,15", "兔|04,16"]),
    ("pt2xiao", "2026173", ["鼠", "牛"]),
    ("title_66", "2026173", ["1尾|01,11,21,31,41", "2尾|02,12,22,32,42", "3尾|03,13,23,33,43", "4尾|04,14,24,34,44", "5尾|05,15,25,35,45"]),
]


def payload(lottery_type: str = "3"):
    marker = {"3": "台", "2": "澳", "1": "港"}[lottery_type]
    return {
        "ok": True,
        "data": {
            "canonical_modules": [
                {
                    "moduleKey": key,
                    "rows": [{"term": term, "prediction": {"tokens": [f"{marker}{token}" for token in tokens], "text": ",".join(tokens)}}],
                }
                for key, term, tokens in MODULES
            ]
        },
    }


def live_page_payload():
    return {
        "ok": True,
        "data": {
            "canonical_modules": [
                {
                    "moduleKey": key,
                    "rows": [{"term": term, "prediction": {"tokens": tokens, "text": ",".join(tokens)}}],
                }
                for key, term, tokens in [
                    *MODULES,
                    ("ma24", "2026173", ["01", "02", "03", "04"]),
                    ("daxiao", "2026173", ["大"]),
                    ("title_14", "2026173", ["家禽|牛,马", "野兽|鼠,虎"]),
                    ("3tou", "2026173", ["1头|10,11,12"]),
                    ("shuangbo", "2026173", ["红波", "蓝波"]),
                    ("pt1wei", "2026173", ["3尾|03,13,23,33,43"]),
                    ("9xiao12ma", "2026173", ["01", "02", "03", "04"]),
                ]
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
            page.wait_for_timeout(1000)

            assert prediction_requests == ["3:1"], (
                "initial rendering must request only each module's newest row"
            )

            text = first_table.inner_text()
            assert "2026173期" in text
            assert ":台鼠台牛台虎台兔台龙台蛇台马" in text
            assert "台01.台02.台03.台04.台05.台06.台07.台08.台09.台10" in text
            assert "台01.台02.台03.台04.台05.台06.台07.台08" in text
            assert "台01.台02.台03.台04.台05" in text
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
                page.wait_for_timeout(300)
                text = first_table.inner_text()
                assert title in text
                assert f":{marker}鼠{marker}牛{marker}虎{marker}兔{marker}龙{marker}蛇{marker}马" in text

            # The full eight-row history is fetched only after the visitor
            # reaches prediction content inside the supplied vendor document.
            frame.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and "1:8" not in prediction_requests:
                page.wait_for_timeout(100)
            assert prediction_requests == ["3:1", "2:1", "1:1", "1:8"], (
                "scrolling near a prediction table must defer and then fetch historical rows"
            )

            # The real site endpoint uses the same canonical envelope. It must
            # render all reviewed replacement sections without a route error.
            page.unroute("**/api/sites/twssz/prediction-modules?**")
            page.route(
                "**/api/sites/twssz/prediction-modules?**",
                lambda route: route.fulfill(json=live_page_payload()),
            )
            page.reload(wait_until="domcontentloaded")
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
            assert frame is not None, "twssz vendor frame did not reload"
            frame.locator("#top_9").wait_for(state="attached", timeout=10000)
            page.wait_for_timeout(1000)
            for anchor in ("top_9", "top_1", "top_2", "top_6", "top_7"):
                heading = frame.locator(f"#{anchor}").first.locator("xpath=following-sibling::*[1]")
                assert "台湾精选" in heading.inner_text()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
