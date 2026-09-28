"""twwanli 一肖一码（#yxym）号码展示区版式契约：7 码不溢出、不折错。

背景（2026-09-29 报障）：`#yxym table.yxym` 中列是号码展示区，7 码渲染成
`01.02.03.04.05.06.07`。共享样式块把 `[data-prediction-content]` 放大到 26px 粗体后，
这一串实测宽 269px；而表格继承 `style2.css` 的 `table{table-layout:fixed}`，首行又是
`<th colspan="3">` 标题行 —— fixed 布局把三列均分成 1/3：

  视口  中列 clientWidth   7 码宽度   溢出      表格自身
  360          116px        269px    +153px    #yxym 389 > 356（被 .box{overflow:hidden} 裁掉）
  414          134px        269px    +135px    406 == 406
  480          156px        269px    +113px    472 == 472

本契约在三个移动视口下真渲染（本地静态服务 + 桩 client + Playwright），断言：

1. 号码单元格不溢出：`td.scrollWidth <= td.clientWidth + 1`
   且内容槽 `span.scrollWidth <= span.clientWidth + 1`；
2. 号码完整：1/3/5/7 码行的号码一个不少、顺序正确；
3. 号码不折错位：每个**可见行**内的号码都是完整的两位号（不允许把 `04` 拆成 `0` + `4`）；
4. 表格与 `#yxym` 容器不溢出（否则溢出部分会被 `.box{overflow:hidden}` 裁掉，
   相邻的「期号 / 开奖结果」列会被串位或截断）；
5. 号码字号没有被改小（仍 >= 共享样式块的 26px）——不许用缩小字号换版式。

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

# DOM 行号 → 该行号码个数（rowIndex 0 是 colspan=3 的标题行）。
CODE_ROWS = {1: 1, 2: 3, 3: 5, 4: 7}
EXPECTED_CODES = ["01", "02", "03", "04", "05", "06", "07"]
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
  // 这样无论实现用 <br> 还是 "\n" + white-space:pre-line，契约量到的都是用户看到的行。
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
      const lines = readLines(slot);
      const codes = lines.join('.').split('.').filter((part) => part !== '');
      const cs = getComputedStyle(slot);
      entry.rows.push({
        rowIndex: rowIndex,
        label: MONO(issue ? issue.textContent : ''),
        lines: lines,
        codes: codes,
        text: lines.join('|'),
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
        hit: slot.getAttribute('data-prediction-hit'),
      });
    });
    view.tables.push(entry);
  });
  return view;
}
"""


def code_row(issue, codes, is_correct=False):
    return {
        "issue": issue,
        "prediction": {"tokens": list(codes), "text": " ".join(codes)},
        "raw": {},
        "result": {"isOpened": True, "code": "37", "zodiac": "马", "isCorrect": is_correct},
    }


def xiao_row(issue, zodiacs):
    return {
        "issue": issue,
        "prediction": {"tokens": list(zodiacs), "text": " ".join(zodiacs)},
        "raw": {},
        "result": {"isOpened": True, "code": "37", "zodiac": "马", "isCorrect": False},
    }


def build_modules():
    """6 张表各取一行，号码组一律给足 7 码（一码/三码/五码/七码行分别截取 1/3/5/7）。

    第 1 张表的号码行标 `isCorrect=True`（其余为 False）：既用来验证折行后版式，
    也用来守住「命中行整格黄底」这条既有展示行为（不得被折行改法吞掉）。
    """
    codes = list(EXPECTED_CODES)
    zodiacs = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马"]
    modules = [
        {"moduleKey": key,
         "rows": [code_row("202627%d" % i, codes, is_correct=(i == 0)) for i in range(6)]}
        for key in ("selected_22_codes", "ma24")
    ]
    modules.append({"moduleKey": "9xzt", "rows": [xiao_row("202627%d" % i, zodiacs) for i in range(6)]})
    modules.append({"moduleKey": "shuangbo",
                    "rows": [code_row("202627%d" % i, codes) for i in range(6)]})
    # needsPredictionRefresh 要求这三个模块非空，否则适配器会走重试分支。
    for key in ("6xzt", "pt1wei", "sitouzhongte"):
        modules.append({"moduleKey": key, "rows": [xiao_row("2026270", ["鼠"])]})
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


def check_view(width: int, view: dict, problems: list[str]) -> list[dict]:
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
            expected = CODE_ROWS.get(row["rowIndex"])
            if expected is None:
                continue
            want = EXPECTED_CODES[:expected]
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
            # 命中行整格黄底是既有展示行为（`writeRow` 的整格通道），折行改法不得吞掉它。
            expect_hit = table["tableIndex"] == 0
            has_hit = row["hit"] == "true"
            if has_hit != expect_hit:
                problems.append(
                    f"{where}: 命中标记应为 {'有' if expect_hit else '无'}，实际 {'有' if has_hit else '无'}")
            if expect_hit and row["span"]["backgroundColor"] != "rgb(255, 255, 0)":
                problems.append(
                    f"{where}: 命中行未上黄底（background-color {row['span']['backgroundColor']}）")
    return measured


def main() -> None:
    views = render_probe()
    problems: list[str] = []
    measured: list[dict] = []
    for width in VIEWPORTS:
        measured.extend(check_view(width, views[width], problems))

    print(f"视口 {list(VIEWPORTS)}；表数 {len(views[VIEWPORTS[0]]['tables'])} × 6 行号码")
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

    print("\ntwwanli-yxym-layout-contract: OK（360/414/480 下 7 码完整、不溢出、不折错位）")


if __name__ == "__main__":
    main()
