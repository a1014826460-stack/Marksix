"""Exercise the vendored jQuery in a browser without allowing external traffic.

Regression: loading the supplier's library used to inject a hidden external
script and write a daily `tool` cookie. A non-localhost origin and fresh cookies
are essential: the appended loader deliberately skips localhost/repeat visits.
Run from any directory: python frontend/test/twsyw-jquery-security-contract.py
"""

from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "frontend/public/vendor/twsyw/static/js/jquery.js"
CHROME = Path(
    r"C:\Users\Administrator\AppData\Local\ms-playwright"
    r"\chromium-1228\chrome-win64\chrome.exe"
)
ORIGIN = "https://twsyw-security.test"
HTML = """<!doctype html><html><head><meta charset="utf-8">
<script src="/vendor/twsyw/static/js/jquery.js"></script>
</head><body><p>Library isolation check</p></body></html>"""


def main():
    failures = []
    with sync_playwright() as playwright:
        launch = {"headless": True}
        if CHROME.exists():
            launch["executable_path"] = str(CHROME)
        browser = playwright.chromium.launch(**launch)
        try:
            for label, options in (
                ("desktop", {}),
                ("android", {
                    "viewport": {"width": 390, "height": 844},
                    "is_mobile": True,
                    "has_touch": True,
                    "user_agent": (
                        "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/140.0.0.0 Mobile Safari/537.36"
                    ),
                }),
            ):
                # Exercise both eligible daily visits and an exhausted counter.
                for initial_cookie in (None, "1", "2"):
                    context = browser.new_context(**options)
                    try:
                        if initial_cookie is not None:
                            context.add_cookies([{
                                "name": "tool", "value": initial_cookie,
                                "url": ORIGIN,
                            }])
                        unexpected = []

                        def intercept(route):
                            request = route.request
                            if request.url == ORIGIN + "/":
                                route.fulfill(content_type="text/html", body=HTML)
                            elif request.url == ORIGIN + "/vendor/twsyw/static/js/jquery.js":
                                route.fulfill(
                                    content_type="application/javascript",
                                    body=SCRIPT.read_bytes(),
                                )
                            else:
                                unexpected.append(request.url)
                                # An accidentally restored loader cannot contact
                                # its upstream endpoint even on a failing run.
                                route.fulfill(
                                    content_type="application/javascript", body=""
                                )

                        context.route("**/*", intercept)
                        page = context.new_page()
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.goto(ORIGIN + "/", wait_until="load")
                        page.wait_for_timeout(100)
                        state = page.evaluate("""() => ({
                            version: window.jQuery?.fn.jquery,
                            scripts: Array.from(document.scripts).map(s => s.src),
                            images: document.querySelectorAll('img').length,
                            frames: document.querySelectorAll('iframe').length,
                        })""")
                        cookie = next(
                            (c["value"] for c in context.cookies() if c["name"] == "tool"),
                            None,
                        )
                        case = f"{label}, initial tool={initial_cookie!r}"
                        if state["version"] != "1.10.2":
                            failures.append(f"{case}: jQuery failed to initialize: {state}")
                        external_scripts = [
                            url for url in state["scripts"]
                            if urlsplit(url).netloc != urlsplit(ORIGIN).netloc
                        ]
                        if unexpected or external_scripts or state["images"] or state["frames"]:
                            failures.append(
                                f"{case}: library injected resources: "
                                f"requests={unexpected}, DOM={state}"
                            )
                        if cookie != initial_cookie:
                            failures.append(
                                f"{case}: library changed tool cookie to {cookie!r}"
                            )
                        if errors:
                            failures.append(f"{case}: page errors: {errors}")
                    finally:
                        context.close()
        finally:
            browser.close()
    assert not failures, "\n".join(failures)
    print("twsyw jQuery security contract passed (6 isolated browser cases)")


if __name__ == "__main__":
    main()
