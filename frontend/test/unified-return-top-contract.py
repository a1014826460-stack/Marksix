import time

from playwright.sync_api import sync_playwright


SITES = ("twssz", "twbst528", "twjsz666")


def test_unified_footer_return_top_controls_scroll_the_vendor_document():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
        )
        page = browser.new_page(viewport={"width": 390, "height": 844})
        for site_key in SITES:
            page.goto(f"http://127.0.0.1:3000/{site_key}", wait_until="domcontentloaded")
            deadline = time.monotonic() + 10
            frame = None
            while time.monotonic() < deadline:
                frame = next(
                    (
                        item
                        for item in page.frames
                        if item.url.split("?", 1)[0].endswith(f"/vendor/{site_key}/index.html")
                    ),
                    None,
                )
                if frame:
                    break
                page.wait_for_timeout(50)

            assert frame is not None, f"{site_key} vendor frame did not load"
            control = frame.get_by_text("返回顶部").first
            assert control.count() == 1, f"{site_key} must retain its return-top control"
            frame.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            page.wait_for_timeout(100)
            assert frame.evaluate("window.scrollY") > 500, f"{site_key} must have a scrollable vendor document"

            control.click()
            page.wait_for_timeout(200)
            assert frame.evaluate("window.scrollY") < 10, f"{site_key} return-top control must scroll to the document top"
        browser.close()
