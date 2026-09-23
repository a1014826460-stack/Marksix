"""列出各站点首屏实际加载的大图（跨 frame），找出 MB 级图片的来源。"""

from __future__ import annotations

import json
import re
import sys

from playwright.sync_api import sync_playwright

COLLECT = """
() => {
  const rows = [];
  const walk = (win) => {
    let entries = [];
    try { entries = win.performance.getEntriesByType('resource') || []; } catch (error) { entries = []; }
    for (const entry of entries) {
      if (entry.initiatorType === 'img' && (entry.transferSize || entry.decodedBodySize || 0) > 50000) {
        rows.push({ url: entry.name, kb: Math.round((entry.transferSize || entry.decodedBodySize || 0) / 1024), type: 'img' });
      }
    }
    let frames = [];
    try { frames = Array.from(win.frames || []); } catch (error) { frames = []; }
    for (const frame of frames) walk(frame);
  };
  walk(window);
  return rows;
}
"""

SITES = {
    "twsaimahui": "www.twsaimahui.com",
    "twssz": "www.twssz.com",
    "tw8800": "www.tw8800.com",
    "twcaibawang": "www.twcaibawang.com",
}


def main() -> int:
    wanted = sys.argv[1:] or list(SITES)
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(channel="chrome")
        except Exception:
            browser = playwright.chromium.launch(channel="msedge")
        context = browser.new_context(ignore_https_errors=True)
        for key in wanted:
            page = context.new_page()
            page.goto(f"https://{SITES[key]}/", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(6000)
            rows = page.evaluate(COLLECT)
            rows.sort(key=lambda row: -row["kb"])
            total = sum(row["kb"] for row in rows)
            print(f"== {key}: {len(rows)} images >= 50 KB, total {total} KB")
            for row in rows[:8]:
                print(f"   {row['kb']:>6} KB  {row['url'][:150]}")
            page.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
