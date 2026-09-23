"""诊断：面板两个接口在真实页面上下文里是否可取到数据。"""

from __future__ import annotations

import json
import sys

from playwright.sync_api import sync_playwright

PROBE = """
async () => {
  const out = {};
  for (const path of ['/api/next-draw-deadline?lottery_type=3', '/api/latest-draw?lottery_type=3']) {
    try {
      const response = await fetch(path, { cache: 'no-store' });
      const text = await response.text();
      out[path] = { status: response.status, bytes: text.length, body: text.slice(0, 160), cache: response.headers.get('x-cache-status') };
    } catch (error) {
      out[path] = { error: String(error).slice(0, 160) };
    }
  }
  return out;
}
"""


def main() -> int:
    domain = sys.argv[1] if len(sys.argv) > 1 else "www.twssz.com"
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(channel="chrome")
        except Exception:
            browser = playwright.chromium.launch(channel="msedge")
        page = browser.new_context(ignore_https_errors=True).new_page()
        logs: list[str] = []
        page.on("console", lambda message: logs.append(f"{message.type}: {message.text[:160]}"))
        page.goto(f"https://{domain}/", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(1500)
        result = page.evaluate(PROBE)
        print(json.dumps({"domain": domain, "api": result}, ensure_ascii=False, indent=2))
        print("---- panel console log tail ----")
        for line in logs[-14:]:
            print(line)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
