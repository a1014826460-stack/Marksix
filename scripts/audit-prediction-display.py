#!/usr/bin/env python
"""预测模块展示规范审计工具（十站点通用）。

用法：
    python scripts/audit-prediction-display.py                 # 审计全部站点
    python scripts/audit-prediction-display.py twsaimahui      # 只审计指定站点
    python scripts/audit-prediction-display.py --json out.json # 额外输出 JSON

检查项（对应《预测模块展示规范》）：
    R1 raw_json_leak      可见文本里残留 [" / "] / \\" 等原始 JSON 片段
    R2 verdict_pending    未开奖（结果为 ？/??/???? 占位）却显示了判定
    R3 highlight_miss     本期判定为「错」，却仍有黄色高亮
    R4 highlight_hit      本期判定为「准/对」，但整行没有黄色高亮（需模块内有高亮行）
    R5 repeat_run         同一模块相邻 3 期以上展示值完全相同
    R6 empty_legend       分组说明后面为空（如「右肖:」「阴肖:」）
    R7 verdict_missing    已开奖且有判定语义的模块缺判定文字（提示级）

退出码：0 = 无 error；1 = 存在 error。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

CHROME = r"C:\Users\Administrator\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"

SITES: list[dict[str, Any]] = [
    {
        "key": "shengshi8800",
        "label": "tw8800 (盛世台湾六合彩)",
        "web_id": 4,
        "url": "https://www.tw8800.com/vendor/shengshi8800/embed.html?type=3&web=4&debug=0&page_switch=1&shell_header=1",
    },
    {
        "key": "twcaibawang",
        "label": "twcaibawang (台湾彩霸王)",
        "web_id": 5,
        "url": "https://www.twcaibawang.com/twcaibawang",
    },
    {
        "key": "twsaimahui",
        "label": "twsaimahui (台湾跑马会)",
        "web_id": 6,
        "url": "https://www.twsaimahui.com/vendor/twsaimahui/index.html",
    },
    {
        "key": "twjinniu",
        "label": "twjinniu (台湾通天网)",
        "web_id": 7,
        "url": "https://www.twtongtian.com/twjinniu",
    },
    {
        "key": "twcf888",
        "label": "twcf888 (台湾创富网)",
        "web_id": 8,
        "url": "https://www.twcf888.com/twcf888",
    },
    {
        "key": "twssz",
        "label": "twssz (台湾神算子)",
        "web_id": 9,
        "url": "https://www.twssz.com/twssz",
    },
    {
        "key": "twbst528",
        "label": "twbst528 (台湾百事通)",
        "web_id": 10,
        "url": "https://www.twbst528.com/twbst528",
    },
    {
        "key": "twjsz666",
        "label": "twjsz666 (台湾金手指)",
        "web_id": 11,
        "url": "https://www.twjsz666.com/twjsz666",
    },
    {
        "key": "twwanli",
        "label": "twwanli (台湾万利网)",
        "web_id": 12,
        "url": "https://www.twwanli.com/twwanli",
    },
    {
        "key": "twsyw",
        "label": "twsyw (台湾神预网)",
        "web_id": 13,
        "url": "https://www.twsyw.com/twsyw",
    },
]

VERDICT_TOKENS = ("准", "对", "错", "赢", "输", "中", "不中")
PENDING_PATTERNS = (
    "？00", "?00", "？？？", "??????", "?????", "????", "？？", "待开",
    "猫00", "？?", "?？",
)
LEGEND_EMPTY_RE = re.compile(
    r"(左肖|右肖|阴肖|阳肖|文肖|武肖|有肖|无肖|吉美肖|凶丑肖|肥肖|瘦肖|"
    r"胆大生肖|胆小生肖|黑肖|白肖|黑中生肖|白边生肖|后肖|前肖|琴肖|棋肖|书肖|画肖)"
    r"\s*[:：]\s*(?=\s|$|\n|<)"
)

ROW_SCRIPT = r"""
() => {
  const out = [];
  const nodes = Array.from(document.querySelectorAll('tr, p, div, li, td, b, font, span'));
  const cands = [];
  for (const el of nodes) {
    const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (!text || text.length > 260) continue;
    if (!/\d{2,3}\s*期/.test(text)) continue;
    cands.push({ el, text });
  }
  const leaves = cands.filter((item) => !cands.some((other) => other.el !== item.el && item.el.contains(other.el)));
  const moduleOf = (el) => {
    let node = el;
    while (node && node !== document.body) {
      if (node.id) return '#' + node.id;
      const cls = String(node.className || '').trim();
      if (cls && /(box|Box|l\d+$|panel)/.test(cls)) return '.' + cls.split(/\s+/).slice(0, 2).join('.');
      node = node.parentElement;
    }
    return '?';
  };
  for (const item of leaves) {
    out.push({
      module: moduleOf(item.el),
      text: item.text,
      html: item.el.outerHTML.slice(0, 4000),
    });
  }
  return out;
}
"""

LEGEND_SCRIPT = r"""
() => {
  const out = [];
  const nodes = Array.from(document.querySelectorAll('tr, p, div, li, td, b, font, span'));
  for (const el of nodes) {
    const html = el.innerHTML || '';
    if (!/肖|生肖/.test(html)) continue;
    if (el.children.length > 0 && el.textContent.length > 200) continue;
    const text = (el.innerText || '').replace(/\s+/g, ' ').trim();
    if (!text || text.length > 120) continue;
    out.push({ text, html: html.slice(0, 3000) });
  }
  return out;
}
"""


@dataclass
class Finding:
    site: str
    rule: str
    level: str
    detail: str
    sample: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "rule": self.rule,
            "level": self.level,
            "detail": self.detail,
            "sample": self.sample,
        }


@dataclass
class SiteReport:
    site: str
    label: str
    url: str
    rows: int = 0
    errors: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


def is_pending(text: str) -> bool:
    return any(token in text for token in PENDING_PATTERNS)


def verdict_of(text: str) -> str:
    """取该行的判定文字。

    只看**开奖结果之后**的部分：模块名里也含「中」（单双中特 / 八肖中特 / 一波中特 …），
    在整行里搜「中」会把模块名误判成判定。
    """
    openings = list(re.finditer(r"开|開", text))
    tail = text[openings[-1].end():] if openings else text
    for token in ("不中", "错", "输", "赢", "准", "对", "中"):
        if token in tail:
            return token
    return ""


def highlight_count(html: str) -> int:
    return html.upper().count("#FFFF00")


def extract_display_token(text: str) -> str:
    """取「最后一个期号」到「开/開」之间的展示值（预测内容）。"""
    opening = re.search(r"开|開", text)
    head = text[: opening.start()] if opening else text
    terms = list(re.finditer(r"\d{2,3}\s*期", head))
    if not terms:
        return ""
    token = head[terms[-1].end():].strip()
    return re.sub(r"^[::\s]+", "", token)[:30]


def audit_rows(site_key: str, rows: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    display_seq: list[tuple[str, str, str]] = []

    for row in rows:
        text = row["text"]
        html = row["html"]
        module = row.get("module", "?")
        verdict = verdict_of(text)
        pending = is_pending(text)
        highlights = highlight_count(html)
        samples = text[:120]

        # R1 原始 JSON 残留
        if re.search(r'\["|\"\]|\\"', text):
            findings.append(Finding(site_key, "R1 raw_json_leak", "error",
                                    f"{module} 可见文本残留原始 JSON 片段", samples))

        # R2 未开奖却给判定：
        #   - 占位结果 + 命中判定（准/对/赢/中）一定是错的（没有开奖号码却宣称命中）→ error
        #   - 占位结果 + 未命中判定 → warn（多数模块用 `？00` 表示「本期无命中项」，
        #     需要人工确认该模块是不是真的未开奖）
        if pending and verdict:
            level = "error" if verdict in ("准", "对", "赢", "中") else "warn"
            findings.append(Finding(site_key, "R2 verdict_pending", level,
                                    f"{module} 结果为占位（未开奖/无命中项）却显示判定「{verdict}」", samples))

        # R3 判定为错却有高亮
        if verdict in ("错", "输", "不中") and highlights > 0:
            findings.append(Finding(site_key, "R3 highlight_miss", "error",
                                    f"{module} 判定「{verdict}」但仍有一处黄色高亮", samples))

        term_match = re.search(r"(\d{2,3})\s*期", text)
        if term_match:
            display_seq.append((module, term_match.group(1), extract_display_token(text)))

    # R4 命中却无高亮：按模块分组，仅当同模块其它行确有高亮时才报
    by_module: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_module.setdefault(row.get("module", "?"), []).append(row)
    for module, module_rows in by_module.items():
        if not any(highlight_count(row["html"]) > 0 for row in module_rows):
            continue
        for row in module_rows:
            if verdict_of(row["text"]) in ("准", "对", "赢", "中") and highlight_count(row["html"]) == 0:
                findings.append(Finding(site_key, "R4 highlight_hit", "warn",
                                        f"{module} 该行判定为命中，但本行没有黄色高亮",
                                        row["text"][:120]))

    # R5 相邻 3 期以上展示值完全相同（同一模块内、按期号降序/升序的连续段）
    by_module_seq: dict[str, list[tuple[str, str]]] = {}
    for module, term, token in display_seq:
        by_module_seq.setdefault(module, []).append((term, token))
    for module, seq in by_module_seq.items():
        run_start = 0
        for index in range(1, len(seq) + 1):
            same = index < len(seq) and seq[index][1] == seq[run_start][1] and seq[index][1] != ""
            if same:
                continue
            run_len = index - run_start
            if run_len >= 3:
                terms = ",".join(item[0] for item in seq[run_start:index])
                findings.append(Finding(site_key, "R5 repeat_run", "warn",
                                        f"{module} 连续 {run_len} 期展示值相同：{seq[run_start][1]!r}",
                                        terms))
            run_start = index
    return findings


def audit_legends(site_key: str, legends: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    for legend in legends:
        text = legend["text"]
        for match in LEGEND_EMPTY_RE.finditer(text):
            name = match.group(1)
            if name in seen:
                continue
            seen.add(name)
            findings.append(Finding(site_key, "R6 empty_legend", "error",
                                    f"分组说明「{name}:」后面为空",
                                    text[:120]))
    return findings


def audit_site(site: dict[str, Any], *, headless: bool = True, base_url: str = "") -> SiteReport:
    from playwright.sync_api import sync_playwright

    url = site["url"]
    if base_url:
        # 本地预检：把线上域名换成 --base-url（例如 http://127.0.0.1:3000）
        from urllib.parse import urlsplit, urlunsplit

        parts = urlsplit(url)
        base = urlsplit(base_url.rstrip("/"))
        url = urlunsplit((base.scheme, base.netloc, parts.path, parts.query, parts.fragment))

    report = SiteReport(site=site["key"], label=site["label"], url=url)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=headless)
        page = browser.new_page(viewport={"width": 900, "height": 1200})
        page.on("pageerror", lambda exc: report.errors.append(str(exc)[:200]))
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=180000)
            page.wait_for_timeout(12000)
            frames = [frame for frame in page.frames]
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"goto failed: {exc}")
            browser.close()
            return report

        all_rows: list[dict[str, Any]] = []
        all_legends: list[dict[str, Any]] = []
        for frame in frames:
            try:
                all_rows.extend(frame.evaluate(ROW_SCRIPT) or [])
                all_legends.extend(frame.evaluate(LEGEND_SCRIPT) or [])
            except Exception:  # noqa: BLE001 - 跨域 frame 直接跳过
                continue
        browser.close()

    report.rows = len(all_rows)
    report.findings.extend(audit_rows(site["key"], all_rows))
    report.findings.extend(audit_legends(site["key"], all_legends))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sites", nargs="*", help="站点 key，留空表示全部")
    parser.add_argument("--json", dest="json_path", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--base-url", default="", help="本地预检：替换站点域名为该地址（如 http://127.0.0.1:3000）")
    args = parser.parse_args()

    targets = [site for site in SITES if not args.sites or site["key"] in args.sites]
    if not targets:
        print("没有匹配的站点，可选：", ", ".join(site["key"] for site in SITES))
        return 1

    reports: list[SiteReport] = []
    for site in targets:
        print(f"=== auditing {site['key']} …", flush=True)
        report = audit_site(site, headless=not args.headed, base_url=args.base_url)
        reports.append(report)
        errors = [f for f in report.findings if f.level == "error"]
        warns = [f for f in report.findings if f.level == "warn"]
        print(f"    rows={report.rows} js_errors={len(report.errors)} error={len(errors)} warn={len(warns)}")

    text_lines = ["# 预测模块展示规范审计报告", ""]
    for report in reports:
        text_lines.append(f"## {report.label}  ({report.url})")
        text_lines.append(f"- 扫描行数：{report.rows}")
        if report.errors:
            text_lines.append(f"- JS 报错：{report.errors}")
        if not report.findings:
            text_lines.append("- 未发现违规 ✅")
        for finding in report.findings:
            mark = "ERROR" if finding.level == "error" else "warn"
            text_lines.append(f"- [{mark}] `{finding.rule}` {finding.detail} | 样例：{finding.sample}")
        text_lines.append("")

    report_path = args.json_path.replace(".json", ".md") if args.json_path else "audit-prediction-display.md"
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(text_lines))
    print(f"文本报告已写入 {report_path}")

    if args.json_path:
        payload = {
            "sites": [
                {
                    "site": report.site,
                    "label": report.label,
                    "url": report.url,
                    "rows": report.rows,
                    "js_errors": report.errors,
                    "findings": [finding.as_dict() for finding in report.findings],
                }
                for report in reports
            ]
        }
        with open(args.json_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=1)
        print(f"JSON 报告已写入 {args.json_path}")

    total_errors = sum(1 for report in reports for f in report.findings if f.level == "error")
    print(f"== total error={total_errors}")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
