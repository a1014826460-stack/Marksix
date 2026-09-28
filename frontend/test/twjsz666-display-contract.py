"""twjsz666 展示契约：全模块文字居中 + 命中高亮只落在候选文字上。

背景（2026-09-29 需求）
----------------------
1. 全部预测模块文字居中；
2. 只有「预测命中的生肖 / 数字 / 波色 / 大小 / 头尾」文字可以标黄，其余文字
   （期号、`开:22羊对` 开奖段、判定字、模块标题）一律不允许标黄。

本契约不依赖线上站点与数据库：本地静态服务提供 `frontend/public`，
`/vendor/_shared/lottery-site-data-client.js` 由桩替换，用**合成数据**驱动
`site-data-adapter.js` 真渲染，然后对真实 DOM 断言。

历史缺陷（本契约防回归）
------------------------
* `highlightScope` 默认整行 → 预测格里没有该字时，黄底飘到同一行的开奖段
  （大小中特 / 双波中特 / 七尾中特 / 四字解平特肖 / 绝杀类 / 精选22码 / ④肖⑧码 …）；
* 命中 token 只有「生肖 / 特码 / 头尾」三类 → 波色、大小玩法无从点亮候选；
* 排除玩法（绝杀二肖 / 绝杀①半波 / 绝杀①尾 / 稳杀⑦码）判定「准」时也标黄开奖段；
* `四字解平特肖` 候选只写成语、丢掉解肖生肖 → 命中时无处可标黄；
* `一头一码` 24 码卡拉从不绑定预测行 → 命中永远零黄底；
* `.bizhong1-tit` 是黄字 → 被判成「高亮」，制造「错期有黄底」的假阳性。

运行：python frontend/test/twjsz666-display-contract.py
"""

from __future__ import annotations

import functools
import http.server
import json
import os
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
WEB_ROOT = REPO / "frontend" / "public"
CHROME = os.environ.get(
    "PLAYWRIGHT_CHROMIUM_EXECUTABLE", r"C:\Program Files\Google\Chrome\Application\chrome.exe"
)

STUB_CLIENT = r"""
window.LotterySiteDataClient = {
  create: function () {
    return {
      loadDraw: function () { return Promise.resolve({ state: "ready", data: { current_issue: "270", balls: [] } }); },
      loadPredictions: function () {
        return Promise.resolve({ state: "ready", data: { canonical_modules: window.__CONTRACT_MODULES__ || [] } });
      }
    };
  }
};
"""

PROBE_JS = r"""
() => {
  const MONO = (s) => String(s || '').replace(/\s+/g, ' ').trim();
  const norm = (v) => String(v || '').replace(/\s+/g, '').toLowerCase();
  const isYellowBg = (v) => ['rgb(255,255,0)', 'rgba(255,255,0,1)', '#ffff00', '#ff0', 'yellow'].includes(norm(v));
  const boxTitle = (el) => {
    const box = el.closest('.box.pad, .qxtable, .bizhong1, #yxym');
    if (!box) return '(outside)';
    const t = box.querySelector('.list-title');
    return MONO(t ? t.textContent : (box.className || box.tagName)).slice(0, 30);
  };

  // ── A. 居中 ──────────────────────────────────────────────────────────
  const alignOffenders = [];
  const seen = {};
  document.querySelectorAll('.box.pad, #yxym, .qxtable, .bizhong1, .post-list').forEach((box) => {
    Array.from(box.querySelectorAll('*')).forEach((el) => {
      const own = Array.from(el.childNodes).filter((n) => n.nodeType === 3).map((n) => n.nodeValue).join('');
      if (!MONO(own)) return;
      const cs = getComputedStyle(el);
      if (cs.textAlign === 'center') return;
      const key = [boxTitle(el), el.tagName, String(el.className || ''), cs.textAlign].join('|');
      if (seen[key]) return;
      seen[key] = 1;
      alignOffenders.push({ module: boxTitle(el), tag: el.tagName.toLowerCase(), cls: String(el.className || ''), align: cs.textAlign, text: MONO(own).slice(0, 30) });
    });
  });

  // ── B. 黄底（相对父节点新增）落点 ───────────────────────────────────
  const rowResultText = (row) => {
    const slot = row.querySelector('[data-prediction-result]');
    if (slot) return MONO(slot.textContent);
    for (const cell of Array.from(row.querySelectorAll('td, li, font, span'))) {
      const t = MONO(cell.textContent);
      if (/^开[:：]/.test(t)) return t;
    }
    const all = MONO(row.textContent);
    const at = all.lastIndexOf('开:');
    return at === -1 ? '' : all.slice(at);
  };
  const hits = [];
  document.querySelectorAll('[data-prediction-hit]').forEach((el) => {
    const row = el.closest('[data-prediction-row]');
    const cell = el.closest('td, th, li');
    hits.push({
      module: boxTitle(el),
      text: MONO(el.textContent),
      rowText: MONO(row ? row.textContent : '').slice(0, 90),
      rowResult: row ? rowResultText(row) : '',
      inIssueSlot: Boolean(el.closest('[data-prediction-issue]')),
      inResultSlot: Boolean(el.closest('[data-prediction-result]')),
      inResultCell: Boolean(cell && /^开[:：]/.test(MONO(cell.textContent))),
      inCandidate: Boolean(el.closest('[data-prediction-content], .zl, .bizhong1-l, .bizhong1-r, .xz2, .xz')),
    });
  });

  // 非命中标记的黄底/黄字（供应商残留、标题黄字等）。已存在的槽位高亮用
  // data-prediction-hit-slot 标记（不能包 span），同样算作命中高亮。
  const strayYellow = [];
  document.querySelectorAll('.box.pad, #yxym, .qxtable, .bizhong1, .post-list').forEach((box) => {
    Array.from(box.querySelectorAll('*')).forEach((el) => {
      if (el.closest('[data-prediction-hit]') || el.closest('[data-prediction-hit-slot]')) return;
      if (el.hasAttribute('data-prediction-hit-slot')) return;
      const cs = getComputedStyle(el);
      const ps = el.parentElement ? getComputedStyle(el.parentElement) : null;
      const bgNew = isYellowBg(cs.backgroundColor) && !(ps && isYellowBg(ps.backgroundColor));
      const hasText = Boolean(MONO(el.textContent));
      const fgNew = hasText && isYellowBg(cs.color) && !(ps && isYellowBg(ps.color));
      if (!bgNew && !fgNew) return;
      strayYellow.push({
        module: boxTitle(el),
        kind: bgNew ? 'bg' : 'fg',
        text: MONO(el.textContent).slice(0, 30),
        rowText: MONO((el.closest('tr, li, .bizhong1') || el).textContent).slice(0, 80),
      });
    });
  });

  // ── C. 逐行：判定 vs 黄底数（两种高亮标记都算）────────────────────
  const rows = [];
  document.querySelectorAll('[data-prediction-row]').forEach((row) => {
    rows.push({
      module: boxTitle(row),
      result: rowResultText(row),
      yellow: row.querySelectorAll('[data-prediction-hit], [data-prediction-hit-slot]').length,
      text: MONO(row.textContent).slice(0, 100),
    });
  });

  return { alignOffenders, hits, strayYellow, rows };
}
"""


def row(issue, *, tokens=None, raw=None, extra=None, text=None, groups=None,
        opened=True, code="", zodiac="", is_correct=None):
    prediction = {"tokens": tokens or [], "text": text or "", "extra": extra or {}}
    if groups is not None:
        prediction["groups"] = groups
    return {
        "issue": issue,
        "prediction": prediction,
        "raw": raw or {},
        "result": {"isOpened": opened, "code": code, "zodiac": zodiac, "isCorrect": is_correct},
    }


#: 每个 moduleKey 给 3 行：270 = 命中(特码 22 羊)、269 = 未命中(特码 37 龙)、268 = 未开奖。
#: `exclude=True` 的玩法「准」表示开奖目标不在候选里，命中行也必须是零黄底。
def build_modules():
    def trio(build):
        return [build("270", True), build("269", False), build("268", None)]

    def result(hit):
        if hit is None:
            return dict(opened=False, code="", zodiac="", is_correct=None)
        if hit:
            return dict(code="22", zodiac="羊", is_correct=True)
        return dict(code="37", zodiac="龙", is_correct=False)

    modules = []

    def add(key, rows):
        modules.append({"moduleKey": key, "title": key, "displayKind": "tokens", "rows": rows})

    add("danshuang4xiao", trio(lambda i, h: row(
        i, tokens=["羊", "牛", "虎", "兔", "蛇", "马", "鸡", "狗"],
        raw={"single_xiao": ["羊", "牛", "虎", "兔"], "double_xiao": ["蛇", "马", "鸡", "狗"]},
        **result(h))))
    add("sitouzhongte", trio(lambda i, h: row(
        i, tokens=["1头|01,13", "2头|02,14", "3头|03,15", "4头|04,16"], **result(h))))
    add("ma24", trio(lambda i, h: row(i, tokens=[f"{n:02d}" for n in range(1, 25)], **result(h))))
    add("9xzt", trio(lambda i, h: row(
        i, tokens=["羊", "牛", "虎", "兔", "龙", "蛇", "马", "鸡", "狗"], **result(h))))
    add("three_head_four_tail", trio(lambda i, h: row(
        i, raw={"content": json.dumps({"heads": ["1头", "3头", "4头"], "tails": ["2尾", "7尾", "9尾", "4尾"]})},
        **result(h))))
    add("pt1xiao", trio(lambda i, h: row(i, raw={"xiao": ["羊"]}, tokens=["羊"], **result(h))))
    # 供应商口径：正文是 `成语|解肖生肖`，令牌里只有成语。
    add("sizixuanji", trio(lambda i, h: row(
        i, tokens=["黯然無光"], raw={"jiexi": "牛羊马虎猴鼠猪"}, **result(h))))
    add("expert_publications", [row(
        "270", raw={"content": json.dumps({"publications": ["第一条资料"]})},
        opened=True, code="22", zodiac="羊", is_correct=True)])
    add("shuangbo", trio(lambda i, h: row(
        i, raw={"wave": ["红波", "绿波"]}, tokens=["红波", "绿波"], **result(h))))
    add("title_14", trio(lambda i, h: row(
        i, raw={"jia": ["牛", "马", "羊", "鸡", "狗", "猪"], "ye": ["鼠", "虎", "兔", "龙", "蛇", "猴"]},
        **result(h))))
    add("pt3xiao", trio(lambda i, h: row(i, tokens=["羊", "牛", "虎"], **result(h))))
    add("4xiao8ma", trio(lambda i, h: row(
        i, raw={"xiao": ["羊", "牛", "虎", "兔"], "code": ["11", "22", "33", "44", "05", "16", "27", "38"]},
        **result(h))))
    add("daxiao", trio(lambda i, h: row(
        i, raw={"daxiao": "小" if h is not False else "大"}, tokens=["小" if h is not False else "大"],
        **result(h))))
    add("title_74", trio(lambda i, h: row(
        i, tokens=["2尾", "3尾", "4尾", "5尾", "6尾", "7尾", "8尾"], **result(h))))
    add("pt1wei", trio(lambda i, h: row(i, raw={"tail": "2"}, tokens=["2"], **result(h))))
    add("selected_22_codes", trio(lambda i, h: row(
        i, tokens=[f"{n:02d}" for n in range(1, 23)], **result(h))))
    add("juesha2xiao", trio(lambda i, h: row(i, raw={"xiao": ["龙", "狗"]}, tokens=["龙", "狗"], **result(h))))
    add("jueshabanbo", trio(lambda i, h: row(i, raw={"wave": "红单"}, tokens=["红单"], **result(h))))
    add("juesha1wei", trio(lambda i, h: row(i, raw={"tail": "7"}, tokens=["7"], **result(h))))
    add("steady_kill_7_codes", trio(lambda i, h: row(
        i, tokens=["01", "02", "03", "04", "05", "06", "07"], **result(h))))
    add("yijuzhenyan", trio(lambda i, h: row(
        i, text="荷香十里先收虎鸡龙，尾声补上羊猪蛇狗", **result(h))))
    add("6xzt", trio(lambda i, h: row(i, tokens=["羊", "牛", "虎", "兔", "龙", "蛇"], **result(h))))
    add("pt2xiao", trio(lambda i, h: row(i, tokens=["羊", "牛"], **result(h))))
    add("wuxiao_wuma", trio(lambda i, h: row(
        i, groups=[
            {"key": "xiao_5", "tokens": ["羊", "牛", "虎", "兔", "龙"]},
            {"key": "code_5", "tokens": ["22", "11", "33", "44", "55"]},
        ], **result(h))))
    return modules


#: 排除玩法：判定「准」也没有命中候选，命中行必须是零黄底。
EXCLUSION_MARKERS = ("绝杀", "稳杀")

#: 关键字幕断言：命中行的黄底文字必须落在这批期望值里（模块 → 允许的命中文字）。
EXPECTED_HIT_TEXT = {
    "单双各四肖": {"羊"},
    "发财⑨肖": {"羊"},
    "三头": {"2头", "2尾", "2"},
    "平特一肖": {"羊"},
    "四字解平特肖": {"羊"},
    "双波": {"绿波", "绿"},
    "家禽VS野兽": {"羊"},
    "平特③肖": {"羊"},
    "④肖⑧码": {"羊", "22"},
    "大小中特": {"小数", "小"},
    "七尾中特": {"2", "2尾"},
    "平特一尾": {"2"},
    "精选22码": {"22"},
    "一句话中特码": {"羊", "22"},
}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):  # noqa: D102
        pass


def serve(directory: Path):
    handler = functools.partial(QuietHandler, directory=str(directory))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def render_probe():
    httpd, port = serve(WEB_ROOT)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME, headless=True)
            page = browser.new_page(viewport={"width": 480, "height": 1200})
            page.route(
                "**/lottery-site-data-client.js",
                lambda route: route.fulfill(status=200, content_type="application/javascript", body=STUB_CLIENT),
            )
            page.route("**/forced-announcement.js", lambda route: route.fulfill(
                status=200, content_type="application/javascript", body=""))
            page.add_init_script(f"window.__CONTRACT_MODULES__ = {json.dumps(build_modules())};")
            page.goto(f"http://127.0.0.1:{port}/vendor/twjsz666/index.html", wait_until="load")
            page.wait_for_timeout(1200)
            data = page.evaluate(PROBE_JS)

            # 文章子页（154-167.html）也是预测模块载体，正文容器必须居中。
            subpages = {}
            for path in sorted(WEB_ROOT.glob("vendor/twjsz666/1[5-6]*.html")):
                page.goto(f"http://127.0.0.1:{port}/vendor/twjsz666/{path.name}", wait_until="domcontentloaded")
                page.wait_for_timeout(60)
                subpages[path.name] = page.evaluate(
                    "() => { const el = document.querySelector('.post-list');"
                    " return el ? getComputedStyle(el).textAlign : 'missing'; }"
                )
            data["subpages"] = subpages
            browser.close()
    finally:
        httpd.shutdown()
    return data


def is_exclusion(module: str) -> bool:
    return any(marker in module for marker in EXCLUSION_MARKERS)


def main() -> None:
    data = render_probe()
    problems: list[str] = []

    # ── A. 全模块文字居中 ────────────────────────────────────────────────
    for item in data["alignOffenders"]:
        problems.append(
            f"非居中文字: [{item['module']}] <{item['tag']} class='{item['cls']}'> align={item['align']} :: {item['text']}"
        )
    for name, align in data["subpages"].items():
        if align != "center":
            problems.append(f"文章子页未居中: {name} .post-list text-align={align}")
    if not data["subpages"]:
        problems.append("没有找到任何文章子页（154-167.html），契约覆盖不完整")

    # ── B. 黄底必须落在候选文字上 ────────────────────────────────────────
    if not data["hits"]:
        problems.append("命中行没有任何高亮：期望命中项被标黄")
    unmarked = 0
    for item in data["hits"]:
        where = ("期号槽" if item["inIssueSlot"] else "开奖槽" if item["inResultSlot"]
                 else "开奖单元格" if item["inResultCell"] else "")
        if where:
            problems.append(f"黄底落在{where}（不允许）: [{item['module']}] '{item['text']}' <- {item['rowText']}")
        if not item["text"]:
            problems.append(f"出现空黄底: [{item['module']}] <- {item['rowText']}")
        # 部分模块（买码之前先上 / 小康早到来 / 精选22码）的候选格没有语义 class，
        # 只能靠「不在期号槽、不在开奖段」判定；这里只统计，不作为失败条件。
        if not item["inCandidate"]:
            unmarked += 1

    # ── C. 逐行判定 vs 黄底 ─────────────────────────────────────────────
    hit_rows = miss_rows = 0
    for item in data["rows"]:
        module, result, yellow = item["module"], item["result"], item["yellow"]
        if "错" in result or "待开奖" in result:
            miss_rows += 1
            if yellow:
                problems.append(f"未命中/未开奖却有 {yellow} 处黄底: [{module}] {result} <- {item['text']}")
            continue
        if "对" not in result:
            continue  # 没有判定段的玩法不参与此断言
        hit_rows += 1
        if is_exclusion(module):
            if yellow:
                problems.append(f"排除玩法（无命中候选）出现黄底: [{module}] {result} <- {item['text']}")
        elif not yellow:
            problems.append(f"命中却没有高亮: [{module}] {result} <- {item['text']}")

    # ── D. 命中文字必须是该玩法的命中项 ─────────────────────────────────
    checked = 0
    for item in data["hits"]:
        for marker, allowed in EXPECTED_HIT_TEXT.items():
            if marker in item["module"]:
                checked += 1
                if item["text"] not in allowed:
                    problems.append(
                        f"命中高亮文字不符: [{item['module']}] 期望 {sorted(allowed)} 实际 '{item['text']}'"
                    )
                break
    for marker in EXPECTED_HIT_TEXT:
        if not any(marker in item["module"] for item in data["hits"]):
            problems.append(f"模块「{marker}」在合成命中数据下没有任何高亮")

    # ── E. 模块标题不得是黄字/黄底（会被误判成命中高亮）──────────────────
    for item in data["strayYellow"]:
        problems.append(f"非命中标记的黄底/黄字: [{item['module']}] {item['kind']} '{item['text']}' <- {item['rowText']}")

    print(f"对齐检查: {len(data['alignOffenders'])} 处非居中")
    print(f"高亮检查: {len(data['hits'])} 处黄底（其中 {unmarked} 处在无语义 class 的候选格里），"
          f"命中行 {hit_rows} / 未命中行 {miss_rows}，逐模块字幕断言 {checked} 条")
    print(f"杂散黄底/黄字: {len(data['strayYellow'])} 处")

    if problems:
        print(f"\nFAIL ({len(problems)} 项)：")
        for line in problems:
            print(f"  - {line}")
        raise SystemExit(1)

    print("\ntwjsz666-display-contract: OK（全模块居中 + 命中高亮只在候选文字上）")


if __name__ == "__main__":
    main()
