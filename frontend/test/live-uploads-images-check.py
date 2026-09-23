"""跨站点复核共享上传图（/uploads/image/20250322/*）——确定性校验。

做法：在真实浏览器页面上下文里直接 `fetch` 这三个文件并用 `createImageBitmap` 解码，
从而验证"浏览器能取到并且能解码"，不受 `loading="lazy"` 与是否在首屏影响。
另外顺带记录 DOM 中这三个 img 的 natural 尺寸（若已加载）。

用法：
    python frontend/test/live-uploads-images-check.py
    python frontend/test/live-uploads-images-check.py www.tw8800.com
"""

from __future__ import annotations

import json
import sys

from playwright.sync_api import sync_playwright

EXPECTED = {
    "1742580086567063.png": (966, 671, 249805),
    "1742580130762983.jpg": (783, 1280, 233233),
    "1742580119746508.jpg": (960, 1280, 84187),
}

PROBE = """
async (files) => {
  const out = [];
  for (const name of files) {
    const url = `/uploads/image/20250322/${name}`;
    try {
      const response = await fetch(url, { cache: 'no-store' });
      const blob = await response.blob();
      const bitmap = await createImageBitmap(blob);
      out.push({ name, status: response.status, bytes: blob.size, width: bitmap.width, height: bitmap.height, type: blob.type });
      bitmap.close && bitmap.close();
    } catch (error) {
      out.push({ name, error: String(error).slice(0, 120) });
    }
  }
  return out;
}
"""

DOM_SCAN = """
() => {
  const found = {};
  const walk = (doc) => {
    let images = [];
    try { images = Array.from(doc.querySelectorAll('img')); } catch (error) { images = []; }
    for (const image of images) {
      const src = image.currentSrc || image.src || '';
      if (!/uploads\\/image\\/20250322/.test(src)) continue;
      found[src.split('/').pop()] = { naturalWidth: image.naturalWidth, naturalHeight: image.naturalHeight, complete: image.complete };
    }
    let frames = [];
    try { frames = Array.from(doc.querySelectorAll('iframe')); } catch (error) { frames = []; }
    for (const frame of frames) {
      try { if (frame.contentDocument) walk(frame.contentDocument); } catch (error) { /* cross-origin */ }
    }
  };
  walk(document);
  return found;
}
"""

DOMAINS = ["www.tw8800.com", "www.twsaimahui.com", "www.twssz.com"]


def main() -> int:
    domains = sys.argv[1:] or DOMAINS
    failures: list[str] = []
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(channel="chrome")
        except Exception:
            browser = playwright.chromium.launch(channel="msedge")
        context = browser.new_context(ignore_https_errors=True)
        for domain in domains:
            page = context.new_page()
            opened = False
            for attempt in range(1, 4):
                try:
                    page.goto(f"https://{domain}/", wait_until="domcontentloaded", timeout=45000)
                    opened = True
                    break
                except Exception as error:  # noqa: BLE001 - 公网抖动重试
                    print(f"   {domain} 第 {attempt} 次打开失败：{type(error).__name__}")
                    page.wait_for_timeout(2000)
            if not opened:
                failures.append(f"{domain} goto failed")
                page.close()
                continue
            page.wait_for_timeout(2000)
            rows = page.evaluate(PROBE, list(EXPECTED))
            dom = page.evaluate(DOM_SCAN)
            print(f"== {domain}")
            for row in rows:
                width, height, size = EXPECTED[row["name"]]
                verdict = "OK"
                if "error" in row:
                    verdict = f"FETCH-FAIL {row['error']}"
                elif (row["bytes"], row["width"], row["height"]) != (size, width, height):
                    verdict = f"MISMATCH expected bytes/width/height={(size, width, height)}"
                if verdict != "OK":
                    failures.append(f"{domain} {row['name']} -> {verdict}")
                print(
                    f"   {row['name']:<28} {verdict}  "
                    + json.dumps({k: v for k, v in row.items() if k != "name"}, ensure_ascii=False)
                )
            for name, info in dom.items():
                if not info["complete"] or info["naturalWidth"] == 0:
                    print(f"   （DOM 中 {name} 未加载：complete={info['complete']}，属于 lazy 首屏外，属正常）")
                else:
                    print(f"   （DOM 中 {name} natural={info['naturalWidth']}x{info['naturalHeight']}）")
            page.close()
        browser.close()
    print(json.dumps({"failures": failures}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
