import os

from playwright.sync_api import sync_playwright


SITES = (
    {
        "key": "shengshi8800",
        "path": "/",
        "frame": "/vendor/shengshi8800/embed.html",
        "draw": ".KJ-TabBox",
        "nav": "#nav2",
        "footer": ".foot-img",
    },
    {
        "key": "twsaimahui",
        "path": "/twsaimahui",
        "frame": "/vendor/twsaimahui/index.html",
        "draw": ".KJ-TabBox",
        "nav": "#nav2",
        "footer": "img[src='static/picture/log1.jpg']",
    },
    {
        "key": "twcaibawang",
        "path": "/twcaibawang",
        "draw": ".KJ-TabBox",
        "nav": "#nav2",
        "footer": ".foot-img",
    },
    {
        "key": "twjinniu",
        "path": "/twjinniu",
        "frame": "/vendor/twjinniu/index.html",
        "draw": "#twjinniu-kj-iframe",
        "nav": "#nav2",
        "footer": ".foot-img",
    },
    {
        "key": "twcf888",
        "path": "/twcf888",
        "frame": "/vendor/twcf888.com/index.html",
        "draw": "#twcf888-kj-iframe",
        "nav": "#nav2",
        "footer": ".pop-xyz-footer",
    },
)


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
            for site in SITES:
                page = browser.new_page()
                page.add_init_script(
                    """
                    window.__siteDataEvents = [];
                    window.addEventListener('site-data:ready', (event) => {
                      window.__siteDataEvents.push(event.detail);
                    });
                    """
                )
                page.goto(f"http://127.0.0.1:3000{site['path']}", wait_until="domcontentloaded")
                page.wait_for_timeout(1000)
                frame = page.main_frame
                if "frame" in site:
                    frame = next(
                        (item for item in page.frames if item.url.split("?", 1)[0].endswith(site["frame"])),
                        None,
                    )
                    assert frame is not None, f"{site['key']} must retain its original content frame"

                frame.locator(site["draw"]).wait_for(state="attached", timeout=10000)
                frame.locator(site["nav"]).wait_for(state="attached", timeout=10000)
                frame.locator(site["footer"]).wait_for(state="attached", timeout=10000)
                page.wait_for_timeout(1500)

                if site["key"] == "twcaibawang":
                    events = page.evaluate("window.__siteDataEvents || []")
                    assert any(
                        event and event.get("siteKey") == site["key"] and event.get("resource") == "page-data"
                        for event in events
                    ), f"{site['key']} must emit its page-data readiness signal"
                else:
                    assert frame.evaluate("typeof window.LotterySiteDataClient === 'object'")
                    assert frame.evaluate(
                        "name => typeof window[name] === 'object'",
                        {
                            "shengshi8800": "Shengshi8800SiteData",
                            "twsaimahui": "TwsaimahuiSiteData",
                            "twjinniu": "TwjinniuSiteData",
                            "twcf888": "Twcf888SiteData",
                        }[site["key"]],
                    ), f"{site['key']} must expose its existing-DOM data adapter"
                page.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
