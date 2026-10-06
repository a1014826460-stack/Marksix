"""twwanli 一肖一码（#yxym）契约：版式（7 码不溢出/不折错位）+ 逐行判定与高亮。

一、版式（2026-09-29 报障）
--------------------------
`#yxym table.yxym` 中列是号码展示区，7 码渲染成 `01.02.03.04.05.06.07`。共享样式块把
`[data-prediction-content]` 放大到 26px 粗体后，这一串实测宽 269px；而表格继承
`style2.css` 的 `table{table-layout:fixed}`，首行又是 `<th colspan="3">` 标题行 ——
fixed 布局把三列均分成 1/3（视口 360 时中列只有 116px，7 码溢出 153px 并被
`.box{overflow:hidden}` 裁掉）。修法：`#yxym` 作用域 `table-layout:auto` + td1/td3 25%
+ td2 50%，号码每行最多 4 码均衡折行。本契约在三个移动视口下真渲染断言：

1. 号码单元格不溢出：`td.scrollWidth <= td.clientWidth + 1`；
2. 号码完整：1/3/5/7 码行的号码一个不少、顺序正确；
3. 号码不折错位：每个**可见行**内的号码都是完整的两位号；
4. 表格与 `#yxym` 容器不溢出；
5. 号码字号没有被改小（仍 >= 共享样式块的 26px）。

二、逐行判定与高亮（2026-10-02 报障）
------------------------------------
线上 2026278 期【一肖一码发布区】八行生肖全部显示「开:03龙对」并整格黄底，但其中
`七肖 牛虎马鼠羊鸡猪`、`九肖 牛虎马鼠羊鸡猪猴` 都不含「龙」。两个根因：

1. **派生行共用了数据源模块的判定**。这 13 行都是「9 肖中特 前 N 肖 / 精选22码 前 N 码 /
   双波」派生出来的，旧实现统一取 `source.result.isCorrect`（9 肖中特的整份 9 肖判定），
   于是 `一肖 牛` 也显示「对」。
2. **行宽按 `rowIndex - 3` 推**，把 `九肖` 行算成 8 个生肖 —— 9 肖里的第 9 个（本期「龙」）
   被裁掉，那一行却仍按 9 肖判定上黄底。

修法：行宽**由行名决定**（`一肖`→1 … `九肖`→9），判定**逐行按本行展示的候选项复算**
（号码行比特码、生肖行比特肖、波色行比波色），命中只点亮那一个候选项（S2），
判定「错」的整行零黄底（S3），未开奖不给判定也不高亮（S1）。

本契约用**故意写反的接口 `isCorrect`**（命中行的 `isCorrect=False`、未命中行的
`isCorrect=True`）证明判定确实来自本地复算，而不是透传接口值。

不连线上、不连数据库、不起常驻服务：临时 http.server + 桩 `lottery-site-data-client`。

运行：python -X utf8 frontend/test/twwanli-yxym-layout-contract.py
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

VIEWPORTS = (360, 414, 480)

ZODIACS = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
CODES = ["01", "02", "03", "04", "05", "06", "07"]

#: 行名（与适配器 ONE_CODE_ONE_XIAO_LABELS 一一对应，DOM 顺序固定）。
ROW_LABELS = [
    "一码", "三码", "五码", "七码",
    "一肖", "二肖", "三肖", "四肖", "五肖", "六肖", "七肖", "九肖",
    "波色",
]
CN_NUMERALS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
#: DOM 行号 → 适配器行号（DOM 第 0 行是 colspan=3 的标题行，没有数据槽）。
DOM_ROW_OFFSET = 1

#: 命中表（第 1 张表）的开奖值：03 龙 / 蓝波。
HIT = {"code": "03", "zodiac": "龙", "color": "blue", "wave": "蓝波"}
#: 未命中表（第 2-6 张表）的开奖值：37 狗 / 绿波（都不在桩候选里）。
MISS = {"code": "37", "zodiac": "狗", "color": "green", "wave": "绿波"}

MIN_CONTENT_FONT_PX = 26.0

STUB_CLIENT = r"""
window.LotterySiteDataClient = {
  create: function () {
    return {
      clear: function () {},
      loadDraw: function () { return Promise.resolve({ state: "ready", data: { issue: "2026270" } }); },
      loadPredictions: function () {
        // 适配器读 envelope.data.data.canonical_modules（客户端再包一层 data）。
        return Promise.resolve({ state: "ready", data: { data: { canonical_modules: window.__CONTRACT_MODULES__ || [] } } });
      }
    };
  }
};
"""

PROBE_JS = r"""
() => {
  const MONO = (s) => String(s || '').replace(/[ \t\r]+/g, ' ').trim();
  // 把一个内容槽读成「可见行」：<br> 与字面换行都算换行。
  const readLines = (slot) => {
    const lines = [''];
    const push = (text) => { lines[lines.length - 1] += text; };
    const walk = (node) => {
      node.childNodes.forEach((child) => {
        if (child.nodeType === 3) {
          String(child.nodeValue || '').split('\n').forEach((part, index) => {
            if (index) lines.push('');
            push(part);
          });
        } else if (child.nodeType === 1) {
          if (child.tagName === 'BR') lines.push('');
          else walk(child);
        }
      });
    };
    walk(slot);
    return lines.map((line) => MONO(line));
  };

  const tables = Array.from(document.querySelectorAll('#yxym table.yxym'));
  const wrap = document.getElementById('yxym');
  const view = {
    viewport: window.innerWidth,
    docScrollWidth: document.documentElement.scrollWidth,
    docClientWidth: document.documentElement.clientWidth,
    wrap: wrap ? { clientWidth: wrap.clientWidth, scrollWidth: wrap.scrollWidth } : null,
    tables: [],
  };
  tables.forEach((table, tableIndex) => {
    const entry = {
      tableIndex: tableIndex,
      clientWidth: table.clientWidth,
      scrollWidth: table.scrollWidth,
      tableLayout: getComputedStyle(table).tableLayout,
      rows: [],
    };
    Array.from(table.querySelectorAll('tr')).forEach((tr, rowIndex) => {
      const cell = Array.from(tr.querySelectorAll('td'))
        .find((td) => td.querySelector('[data-prediction-content]'));
      if (!cell) return;
      const slot = cell.querySelector('[data-prediction-content]');
      const issue = tr.querySelector('[data-prediction-issue]');
      const result = tr.querySelector('[data-prediction-result]');
      const lines = readLines(slot);
      const codes = lines.join('.').split('.').filter((part) => part !== '');
      const cs = getComputedStyle(slot);
      entry.rows.push({
        rowIndex: rowIndex,
        label: MONO(issue ? issue.textContent : ''),
        lines: lines,
        codes: codes,
        text: lines.join(''),
        verdict: MONO(result ? result.textContent : ''),
        hits: Array.from(slot.querySelectorAll('[data-prediction-hit="true"]')).map((el) => MONO(el.textContent)),
        slotHit: slot.getAttribute('data-prediction-hit'),
        cellWidths: Array.from(tr.querySelectorAll('td'))
          .map((td) => Math.round(td.getBoundingClientRect().width * 100) / 100),
        td: {
          clientWidth: cell.clientWidth,
          scrollWidth: cell.scrollWidth,
          offsetWidth: cell.offsetWidth,
          width: Math.round(cell.getBoundingClientRect().width * 100) / 100,
        },
        span: {
          clientWidth: slot.clientWidth,
          scrollWidth: slot.scrollWidth,
          width: Math.round(slot.getBoundingClientRect().width * 100) / 100,
          fontSize: cs.fontSize,
          fontWeight: cs.fontWeight,
          backgroundColor: cs.backgroundColor,
        },
      });
    });
    view.tables.push(entry);
  });
  return view;
}
"""


def payload_row(issue, tokens, result, raw=None):
    return {
        "issue": issue,
        "prediction": {"tokens": list(tokens), "text": " ".join(tokens)},
        "raw": raw or {},
        "result": result,
    }


def build_modules():
    """6 张表：第 1 张命中（03 龙 / 蓝波），其余未命中（37 狗 / 绿波）。

    接口 `isCorrect` **故意写反**：命中行给 False、未命中行给 True —— 判定必须由适配器
    按「本行展示的候选项」复算，照抄接口值就会整组反过来。
    """
    codes = list(CODES)
    zodiacs = ZODIACS[:9]  # 9 肖：鼠牛虎兔龙蛇马羊猴（第 5 个是「龙」）
    waves = ["蓝波", "红波"]

    rows = [(HIT, False)] + [(MISS, True)] * 5
    modules = []
    for key in ("selected_22_codes", "ma24"):
        modules.append({
            "moduleKey": key,
            "rows": [
                payload_row("202627%d" % i, codes, {
                    "isOpened": True, "code": draw["code"], "zodiac": draw["zodiac"],
                    "isCorrect": wrong,
                })
                for i, (draw, wrong) in enumerate(rows)
            ],
        })
    modules.append({
        "moduleKey": "9xzt",
        "rows": [
            payload_row("202627%d" % i, zodiacs, {
                "isOpened": True, "code": draw["code"], "zodiac": draw["zodiac"],
                "isCorrect": wrong,
            })
            for i, (draw, wrong) in enumerate(rows)
        ],
    })
    modules.append({
        "moduleKey": "shuangbo",
        "rows": [
            payload_row("202627%d" % i, waves, {
                "isOpened": True, "code": draw["code"], "zodiac": draw["zodiac"],
                "color": draw["color"], "isCorrect": wrong,
            }, raw={"wave": list(waves)})
            for i, (draw, wrong) in enumerate(rows)
        ],
    })
    # needsPredictionRefresh 要求这三个模块非空，否则适配器会走重试分支。
    for key in ("6xzt", "pt1wei", "sitouzhongte"):
        modules.append({
            "moduleKey": key,
            "rows": [payload_row("2026270", ["鼠"], {
                "isOpened": True, "code": "03", "zodiac": "龙", "isCorrect": True,
            })],
        })
    return modules


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
    views = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME, headless=True)
            for width in VIEWPORTS:
                page = browser.new_page(viewport={"width": width, "height": 1600})
                page.route(
                    "**/lottery-site-data-client.js",
                    lambda route: route.fulfill(
                        status=200, content_type="application/javascript", body=STUB_CLIENT),
                )
                page.route("**/forced-announcement.js", lambda route: route.fulfill(
                    status=200, content_type="application/javascript", body=""))
                page.add_init_script(f"window.__CONTRACT_MODULES__ = {json.dumps(build_modules())};")
                page.goto(f"http://127.0.0.1:{port}/vendor/twwanli/index.html", wait_until="load")
                page.wait_for_timeout(1200)
                views[width] = page.evaluate(PROBE_JS)
                page.close()
            browser.close()
    finally:
        httpd.shutdown()
    return views


def expected_row(adapter_index: int, hit_table: bool):
    """一行应显示的（内容文本、判定后缀、命中项）。

    命中表：03 落在 3/5/7 码行、龙落在 5/6/7/9 肖行、蓝波落在波色行；
    未命中表：候选里既没有 37 也没有狗、绿波，全部「错」且零高亮。
    """
    label = ROW_LABELS[adapter_index]
    if label == "波色":
        return "蓝波+红波", ("对" if hit_table else "错"), ([HIT["wave"]] if hit_table else [])
    count = CN_NUMERALS[label[0]]
    if label.endswith("码"):
        text = ".".join(CODES[:count])
        if not hit_table:
            return text, "错", []
        hit = HIT["code"] in CODES[:count]
        return text, ("对" if hit else "错"), ([HIT["code"]] if hit else [])
    text = "".join(ZODIACS[:count])
    if not hit_table:
        return text, "错", []
    hit = HIT["zodiac"] in ZODIACS[:count]
    return text, ("对" if hit else "错"), ([HIT["zodiac"]] if hit else [])


def check_layout(width: int, view: dict, problems: list[str]) -> list[dict]:
    measured: list[dict] = []
    if not view["tables"]:
        problems.append(f"{width}px: 页面上没有 #yxym table.yxym")
        return measured
    wrap = view["wrap"] or {}
    if wrap.get("scrollWidth", 0) > wrap.get("clientWidth", 0) + 1:
        problems.append(
            f"{width}px: #yxym 容器溢出 {wrap['scrollWidth'] - wrap['clientWidth']}px"
            f"（scrollWidth {wrap['scrollWidth']} > clientWidth {wrap['clientWidth']}）"
            "—— 溢出部分会被 .box{overflow:hidden} 裁掉，相邻列串位")
    for table in view["tables"]:
        if table["scrollWidth"] > table["clientWidth"] + 1:
            problems.append(
                f"{width}px: 第 {table['tableIndex'] + 1} 张表溢出 "
                f"{table['scrollWidth'] - table['clientWidth']}px"
                f"（scrollWidth {table['scrollWidth']} > clientWidth {table['clientWidth']}，"
                f"table-layout={table['tableLayout']}）")
        for row in table["rows"]:
            adapter_index = row["rowIndex"] - DOM_ROW_OFFSET
            if adapter_index not in range(len(ROW_LABELS)):
                continue
            label = ROW_LABELS[adapter_index]
            if not label.endswith("码"):
                continue
            expected = CN_NUMERALS[label[0]]
            want = CODES[:expected]
            measured.append({
                "viewport": width,
                "table": table["tableIndex"] + 1,
                "row": row["rowIndex"],
                "label": row["label"],
                "expected": expected,
                "td_client": row["td"]["clientWidth"],
                "td_scroll": row["td"]["scrollWidth"],
                "span_client": row["span"]["clientWidth"],
                "span_scroll": row["span"]["scrollWidth"],
                "fontSize": row["span"]["fontSize"],
                "lines": row["lines"],
                "codes": row["codes"],
                "cellWidths": row["cellWidths"],
            })
            where = f"{width}px 表{table['tableIndex'] + 1} {row['label'] or ('行' + str(row['rowIndex']))}"
            for cell_name, cell in (("号码单元格", row["td"]), ("内容槽", row["span"])):
                overflow = cell["scrollWidth"] - cell["clientWidth"]
                if overflow > 1:
                    problems.append(
                        f"{where}: {cell_name}溢出 {overflow}px"
                        f"（scrollWidth {cell['scrollWidth']} > clientWidth {cell['clientWidth']}）"
                        f":: {' / '.join(row['lines'])}")
            if row["codes"] != want:
                problems.append(f"{where}: 号码应为 {want}，实际 {row['codes']}（可见行 {' / '.join(row['lines'])}）")
            for line in row["lines"]:
                parts = [part for part in line.split(".") if part != ""]
                if any(not (len(part) == 2 and part.isdigit()) for part in parts):
                    problems.append(f"{where}: 号码被折错位，可见行含残号 '{line}'")
            font = float(str(row["span"]["fontSize"]).replace("px", "") or 0)
            if font < MIN_CONTENT_FONT_PX:
                problems.append(
                    f"{where}: 号码字号被改小到 {row['span']['fontSize']}（应 >= {MIN_CONTENT_FONT_PX:g}px）")
    return measured


def check_verdicts(width: int, view: dict, problems: list[str]) -> None:
    """逐行断言：期号/行名、行宽按行名、判定按本行候选复算、只点亮命中项。"""
    for table in view["tables"]:
        hit_table = table["tableIndex"] == 0
        for row in table["rows"]:
            adapter_index = row["rowIndex"] - DOM_ROW_OFFSET
            if adapter_index not in range(len(ROW_LABELS)):
                continue
            label = ROW_LABELS[adapter_index]
            where = f"{width}px 表{table['tableIndex'] + 1} {row['label']}"
            expect_label = f"202627{table['tableIndex']}期:{label}"
            if row["label"] != expect_label:
                problems.append(f"{where}: 期号/行名应为 {expect_label}，实际 {row['label']!r}")
            text, suffix, hits = expected_row(adapter_index, hit_table)
            # 号码行的可见行之间没有分隔符（`01.02.03` / `04.05` 两行），比较时忽略分隔符。
            if row["text"].replace(".", "") != text.replace(".", ""):
                problems.append(f"{where}: 候选应为 {text!r}，实际 {row['text']!r}")
            if not row["verdict"].endswith(suffix):
                problems.append(f"{where}: 判定应以「{suffix}」结尾，实际 {row['verdict']!r}")
            if sorted(row["hits"]) != sorted(hits):
                problems.append(f"{where}: 命中项应为 {hits}，实际 {row['hits']}（{row['text']}）")
            # 2026-10-02：整格黄底改为逐项黄底（S2）—— 槽本身不得再带命中标记。
            if row["slotHit"] == "true":
                problems.append(f"{where}: 内容槽不得整格上命中标记（应只点亮命中项，S2）")
            if suffix == "错" and row["hits"]:
                problems.append(f"{where}: 判定「错」的整行必须零黄底，实际 {row['hits']}（S3）")
            if suffix == "错" and row["span"]["backgroundColor"] == "rgb(255, 255, 0)":
                problems.append(f"{where}: 判定「错」的整行不得有黄底（S3）")

    # 九肖行必须显示 9 个生肖（旧实现按 rowIndex-3 只给 8 个，把第 9 个「龙」裁掉）。
    nine = [row for row in view["tables"][0]["rows"] if row["rowIndex"] - DOM_ROW_OFFSET == 11]
    if not nine:
        problems.append(f"{width}px: 第 1 张表找不到「九肖」行")
    else:
        if nine[0]["text"] != "".join(ZODIACS[:9]):
            problems.append(f"{width}px: 九肖行应显示 9 个生肖 {''.join(ZODIACS[:9])}，实际 {nine[0]['text']}")
        if nine[0]["hits"] != ["龙"]:
            problems.append(f"{width}px: 九肖行应只点亮「龙」（第 9 个生肖），实际 {nine[0]['hits']}")


def main() -> None:
    views = render_probe()
    problems: list[str] = []
    measured: list[dict] = []
    for width in VIEWPORTS:
        measured.extend(check_layout(width, views[width], problems))
        check_verdicts(width, views[width], problems)

    print(f"视口 {list(VIEWPORTS)}；表数 {len(views[VIEWPORTS[0]]['tables'])} × 13 行")
    header = (f"{'视口':>5} {'行':>12} {'应':>3} {'左列':>6} {'中列宽':>7} {'右列':>6} "
              f"{'内容宽':>7} {'溢出':>6} {'字号':>6}  可见行")
    print(header)
    for item in measured:
        widths = item["cellWidths"]
        left = widths[0] if len(widths) > 1 else 0
        right = widths[-1] if len(widths) > 2 else 0
        overflow = max(item["td_scroll"] - item["td_client"], item["span_scroll"] - item["span_client"])
        print(f"{item['viewport']:>5} {item['label'][:12]:>12} {item['expected']:>3} {left:>6.0f} "
              f"{item['td_client']:>7} {right:>6.0f} {item['span_scroll']:>7} {overflow:>6} "
              f"{item['fontSize']:>6}  {' / '.join(item['lines'])}")

    if problems:
        print(f"\nFAIL ({len(problems)} 项)：")
        for line in problems:
            print(f"  - {line}")
        raise SystemExit(1)

    print("\ntwwanli-yxym-layout-contract: OK"
          "（360/414/480 版式正常；判定/高亮按本行候选复算，九肖显示 9 肖）")


if __name__ == "__main__":
    main()
