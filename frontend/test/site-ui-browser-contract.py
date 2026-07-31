import os
import time

from playwright.sync_api import sync_playwright


SITES = (
    {
        "key": "shengshi8800",
        "path": "/",
        "frame": "/vendor/shengshi8800/embed.html",
        "draw": ".KJ-TabBox",
        "nav": "#nav2",
        "footer": ".foot-img",
        "self_domain": "www.tw8800.com",
    },
    {
        "key": "twsaimahui",
        "path": "/twsaimahui",
        "frame": "/vendor/twsaimahui/index.html",
        "draw": ".KJ-TabBox",
        "nav": "#nav2",
        "footer": "img[src='static/picture/log1.jpg']",
        "self_domain": "www.twsaimahui.com",
    },
    {
        "key": "twcaibawang",
        "path": "/twcaibawang",
        "draw": ".KJ-TabBox",
        "nav": "#nav2",
        "footer": ".foot-img",
        "self_domain": "www.twcaibawang.com",
    },
    {
        "key": "twjinniu",
        "path": "/twjinniu",
        "frame": "/vendor/twjinniu/index.html",
        "draw": "#twjinniu-kj-iframe",
        "nav": "#nav2",
        "footer": ".foot-img",
        "self_domain": "www.twtongtian.com",
    },
    {
        "key": "twcf888",
        "path": "/twcf888",
        "frame": "/vendor/twcf888.com/index.html",
        "draw": "#twcf888-kj-iframe",
        "nav": "#nav2",
        "footer": ".pop-xyz-footer",
        "self_domain": "www.twcf888.com",
    },
    {
        "key": "twssz",
        "path": "/twssz",
        "frame": "/vendor/twssz/index.html",
        "draw": "iframe[src='kai.html']",
        "nav": "#nav2",
        "footer": ".cgi-body",
        "self_domain": "www.twssz.com",
    },
    {
        "key": "twbst528",
        "path": "/twbst528",
        "frame": "/vendor/twbst528/index.html",
        "draw": ".KJ-TabBox",
        "nav": ".KJ-TabBox",
        "footer": ".footer",
        "self_domain": "www.twbst528.com",
    },
    {
        "key": "twjsz666",
        "path": "/twjsz666",
        "frame": "/vendor/twjsz666/index.html",
        "draw": "iframe[src='kai.html']",
        "nav": ".nav",
        "footer": ".foot-img",
        "self_domain": "www.twjsz666.com",
    },
)

FIXTURE_ROWS = (
    {
        "name": "Fixture Browser Alpha",
        "domain": "fixture-alpha.example.com",
        "blueprint_name": "fixture_browser_alpha",
    },
    {
        "name": "Fixture Browser Beta",
        "domain": "fixture-beta.example.com",
        "blueprint_name": "fixture_browser_beta",
    },
)


def _db_connect():
    """Connect to the local dev database via the user-scoped DATABASE_URL env var.

    Returns None (fixture scenario is skipped) when the variable is absent so
    the contract never embeds credentials.
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return None
    try:
        import psycopg2

        return psycopg2.connect(url)
    except Exception:
        return None


def _wait_for_links(links_el, timeout_ms=8000):
    """Wait until the managed-site-links component has rendered its anchors.

    The component fetches /api/site-links asynchronously after connect, so a
    render may lag the element attachment by a few hundred milliseconds.
    """
    deadline = time.monotonic() + timeout_ms / 1000.0
    while links_el.locator("a").count() == 0:
        if time.monotonic() >= deadline:
            break
        links_el.page.wait_for_timeout(200)
    return links_el.locator("a").count()


def _verify_db_fixture(browser):
    """Plan acceptance item 5: DB fixture add/remove changes link count/order,
    and the current site never appears.

    Requires the user-scoped DATABASE_URL; skipped (with a note) otherwise.
    """
    conn = _db_connect()
    if conn is None:
        print("SKIP site-links DB fixture: DATABASE_URL not set / psycopg2 unavailable")
        return

    page = browser.new_page()
    page.add_init_script(
        """
        window.__siteDataEvents = [];
        window.addEventListener('site-data:ready', (event) => {
          window.__siteDataEvents.push(event.detail);
        });
        """
    )
    snapshot = None
    try:
        page.goto("http://127.0.0.1:3000/twjsz666", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        frame = next(
            (item for item in page.frames if item.url.split("?", 1)[0].endswith("/vendor/twjsz666/index.html")),
            None,
        )
        assert frame is not None, "twjsz666 must retain its original content frame"
        links_el = frame.locator("managed-site-links").first
        links_el.wait_for(state="attached", timeout=5000)
        _wait_for_links(links_el)
        anchors = links_el.locator("a")
        snapshot = [anchors.nth(i).text_content() for i in range(anchors.count())]
        print(f"DB fixture baseline ({len(snapshot)} links): {snapshot}")

        # 1. Insert fixture rows -> links must grow by 2, appended in id ASC order.
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(id), 0) FROM managed_sites")
        next_id = cur.fetchone()[0] + 1
        for offset, row in enumerate(FIXTURE_ROWS):
            cur.execute(
                """
                INSERT INTO managed_sites (id, name, enabled, domain, blueprint_name,
                                           created_at, updated_at, lottery_type_id)
                VALUES (%s, %s, 1, %s, %s, %s, %s, 3)
                """,
                (next_id + offset, row["name"], row["domain"], row["blueprint_name"], now, now),
            )
        conn.commit()

        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        frame = next(
            (item for item in page.frames if item.url.split("?", 1)[0].endswith("/vendor/twjsz666/index.html")),
            None,
        )
        links_el = frame.locator("managed-site-links").first
        links_el.wait_for(state="attached", timeout=5000)
        _wait_for_links(links_el)
        anchors = links_el.locator("a")
        grown = [anchors.nth(i).text_content() for i in range(anchors.count())]
        assert len(grown) == len(snapshot) + len(FIXTURE_ROWS), (
            f"fixture insert must add {len(FIXTURE_ROWS)} links, "
            f"got {len(snapshot)} -> {len(grown)}"
        )
        assert grown[-2:] == [row["name"] for row in FIXTURE_ROWS], (
            f"fixture links must be appended in id ASC order, tail is {grown[-2:]}"
        )
        hrefs = [anchors.nth(i).get_attribute("href") or "" for i in range(anchors.count())]
        assert not any("twjsz666" in href for href in hrefs), (
            "current site (twjsz666) must not appear in its own link list"
        )
        print(f"DB fixture grown ({len(grown)} links): {grown}")

        # 2. Delete fixture rows -> links must return to the original set.
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM managed_sites WHERE blueprint_name = ANY(%s)",
            ([row["blueprint_name"] for row in FIXTURE_ROWS],),
        )
        conn.commit()

        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        frame = next(
            (item for item in page.frames if item.url.split("?", 1)[0].endswith("/vendor/twjsz666/index.html")),
            None,
        )
        links_el = frame.locator("managed-site-links").first
        links_el.wait_for(state="attached", timeout=5000)
        _wait_for_links(links_el)
        anchors = links_el.locator("a")
        restored = [anchors.nth(i).text_content() for i in range(anchors.count())]
        assert restored == snapshot, (
            f"after fixture delete, links must match the baseline, got {restored}"
        )
        print(f"DB fixture restored ({len(restored)} links): {restored}")
    finally:
        try:
            conn.rollback()
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM managed_sites WHERE blueprint_name = ANY(%s)",
                ([row["blueprint_name"] for row in FIXTURE_ROWS],),
            )
            conn.commit()
        finally:
            conn.close()
        page.close()


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
                            "twssz": "TwsszSiteData",
                            "twbst528": "Twbst528SiteData",
                            "twjsz666": "Twjsz666SiteData",
                        }[site["key"]],
                    ), f"{site['key']} must expose its existing-DOM data adapter"
                # Managed site links contract (all 8 manifest sites)
                links_el = frame.locator("managed-site-links").first
                links_el.wait_for(state="attached", timeout=5000)
                title_el = links_el.locator('[data-title]')
                title_el.wait_for(state="attached", timeout=3000)
                title_text = title_el.text_content()
                assert title_text == "友情链接", (
                    f"{site['key']} managed-site-links must show title '友情链接', got '{title_text}'"
                )
                link_count = _wait_for_links(links_el)
                assert link_count > 0, (
                    f"{site['key']} managed-site-links must render links from the database"
                )
                link_anchors = links_el.locator("a")
                for i in range(link_count):
                    anchor = link_anchors.nth(i)
                    assert anchor.get_attribute("target") == "_blank", (
                        f"{site['key']} link {i} must have target=_blank"
                    )
                    assert anchor.get_attribute("rel") == "noopener noreferrer", (
                        f"{site['key']} link {i} must have rel=noopener noreferrer"
                    )
                    href = anchor.get_attribute("href") or ""
                    assert href.startswith("https://"), (
                        f"{site['key']} link {i} must use HTTPS, got '{href}'"
                    )
                    assert site["self_domain"] not in href, (
                        f"{site['key']} must not link to itself, got '{href}'"
                    )

                # Three-line prediction display contract (twjsz666 only)
                if site["key"] == "twjsz666":
                    for data_attr, label in [
                        ("data-prediction-issue", "issue"),
                        ("data-prediction-content", "content"),
                        ("data-prediction-result", "result"),
                    ]:
                        el = frame.locator(f"[{data_attr}]").first
                        el.wait_for(state="attached", timeout=5000)
                        display = el.evaluate("el => window.getComputedStyle(el).display")
                        assert display == "block", (
                            f"twjsz666 {label} node [{data_attr}] must be display:block, got '{display}'"
                        )

                if site["key"] == "twssz":
                    external_requests = []
                    page.on(
                        "request",
                        lambda request: external_requests.append(request.url)
                        if request.url.startswith(("http://", "https://"))
                        and "127.0.0.1:3000" not in request.url
                        else None,
                    )
                    page.reload(wait_until="domcontentloaded")
                    page.wait_for_timeout(500)
                    assert not external_requests, "twssz must not request external origins"
                page.close()

            _verify_db_fixture(browser)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
