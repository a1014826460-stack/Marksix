"""开奖窗口泄漏审计：验证「除开奖模块外，其他接口不得提前透露当期号码」。

背景
----
开奖号码在**开奖模块**（`/api/latest-draw` 及其派生：`/api/sites/<key>/draw`、`/wy.json`、
`site-page` 的 `draw` 段）里按 `reveal_start + 25s×N` 逐球开放；其余出口必须等到
闸门（`system_config.history_backfill_delay_after_draw`，生产 8 分钟）之后才允许出现结果。

本脚本在开奖窗口内轮询所有已知公开出口，对每个响应做两类判定：

1. **结构化**：任何 `issue/term == 当期` 的记录只要带上结果字段
   （`res_code` / `res_sx` / `res_color` / `numbers` / `balls` / `special_ball` /
   `openCode` / `result.code` / `is_opened=True`）即判为泄漏；`*.draw.*` 子树属于开奖模块，
   只记录进度、不计泄漏。
2. **原始序列**：响应文本里出现当期完整号码序列（`,` `.` `-` 空格 / 连写）即判为泄漏
   （用于识别非 JSON 的旧站 JSONP / 静态片段）。

用法
----
本地（默认）::

    python scripts/audit-draw-leak-window.py --issue 2026279 --numbers "03,10,16,24,31,38,46" \
        --until "2026-10-05 05:49:00" --interval 8

生产（开奖窗口内，公网只读 GET）::

    python scripts/audit-draw-leak-window.py --base-url https://www.tw8800.com \
        --backend-url https://www.tw8800.com/central-api \
        --issue 2026278 --numbers "01,09,17,26,32,39,45" \
        --until "2026-10-05 22:35:00" --interval 8

退出码：0 = 窗口内无提前透露；1 = 发现泄漏或探测失败。
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Iterable

BEIJING = timezone(timedelta(hours=8))
ALLOWED = "allowed"
FORBIDDEN = "forbidden"

RESULT_KEYS = (
    "res_code", "res_sx", "res_color", "numbers", "openCode", "balls",
    "special_ball", "is_opened", "draw_is_opened", "result",
)


def build_probes(base_url: str, backend_url: str, site_key: str, lottery_type: int) -> list[tuple[str, str, str]]:
    base = base_url.rstrip("/")
    backend = backend_url.rstrip("/")
    query = f"lottery_type={lottery_type}"
    return [
        # 开奖模块家族
        ("latest-draw(后端)", ALLOWED, f"{backend}/api/public/latest-draw?{query}"),
        ("latest-draw(前端)", ALLOWED, f"{base}/api/latest-draw?{query}"),
        (f"sites/{site_key}/draw", ALLOWED, f"{base}/api/sites/{site_key}/draw?{query}"),
        ("wy.json", ALLOWED, f"{base}/wy.json?t=1"),
        # 其余出口（必须等闸门）
        ("draw-history(后端)", FORBIDDEN, f"{backend}/api/public/draw-history?{query}&page_size=10"),
        ("draw-history(前端)", FORBIDDEN, f"{base}/api/draw-history?{query}&page_size=10"),
        ("ttklsjl(JSONP)", FORBIDDEN, f"{base}/index/ajax/ttklsjl?year={datetime.now(BEIJING).year}"),
        ("site-page(后端)", FORBIDDEN, f"{backend}/api/public/site-page?site_id=10&{query}&history_limit=6"),
        (f"sites/{site_key}/site-page", FORBIDDEN, f"{base}/api/sites/{site_key}/site-page?{query}&history_limit=6"),
        (f"sites/{site_key}/prediction-modules", FORBIDDEN, f"{base}/api/sites/{site_key}/prediction-modules?{query}&history_limit=6&include_vendor=1"),
        (f"sites/{site_key}/homepage-modules", FORBIDDEN, f"{base}/api/sites/{site_key}/homepage-modules?{query}&history_limit=8"),
        ("homepage-modules(后端)", FORBIDDEN, f"{backend}/api/vendor/homepage-modules?site_id=10&{query}&history_limit=8"),
        ("legacy/module-rows(后端)", FORBIDDEN, f"{backend}/api/legacy/module-rows?modes_id=57&limit=3&web=10&type={lottery_type}"),
        ("legacy/current-term(后端)", FORBIDDEN, f"{backend}/api/legacy/current-term?type={lottery_type}"),
        ("kaijiang(后端)", FORBIDDEN, f"{backend}/api/kaijiang/getShaXiao?web=10&type={lottery_type}&limit=3"),
        ("kaijiang(前端)", FORBIDDEN, f"{base}/api/kaijiang/getShaXiao?web=10&type={lottery_type}&limit=3"),
        ("lottery-data(前端)", FORBIDDEN, f"{base}/api/lottery-data?site_id=10&{query}&history_limit=6"),
        ("current-period(后端)", FORBIDDEN, f"{backend}/api/public/current-period?{query}"),
        ("next-deadline(后端)", FORBIDDEN, f"{backend}/api/public/next-draw-deadline?{query}"),
    ]


def walk(node, path="$") -> Iterable[tuple[str, object]]:
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk(value, f"{path}[{index}]")


def issue_tokens(issue: str) -> set[str]:
    term = issue[4:] if len(issue) > 4 else issue
    return {issue, term, term.lstrip("0") or term}


def scan(body: str, issue: str, numbers: list[str]) -> tuple[list[str], int | None]:
    tokens = issue_tokens(issue)
    leaks: list[str] = []
    revealed: int | None = None
    try:
        data = json.loads(body)
    except Exception:
        data = None
    if data is not None:
        for path, node in walk(data):
            if not isinstance(node, dict):
                continue
            if "draw" in path.split("."):
                if str(node.get("current_issue") or "") == issue and isinstance(node.get("revealed_count"), int):
                    revealed = node["revealed_count"]
                continue
            ident = {
                str(value)
                for key, value in node.items()
                if key in ("issue", "term", "current_issue", "currentIssue", "period", "draw_issue")
            }
            if not (ident & tokens):
                continue
            for key in RESULT_KEYS:
                value = node.get(key)
                if key not in node or value in (None, "", [], {}, False, 0, "0"):
                    continue
                if key == "result" and isinstance(value, dict):
                    if not any(value.get(inner) for inner in ("code", "value", "res_code", "zodiac", "text")):
                        continue
                leaks.append(f"{path}.{key}={str(value)[:70]}")
    for variant in (",".join(numbers), ".".join(numbers), "-".join(numbers), " ".join(numbers), "".join(numbers)):
        if variant and variant in body:
            leaks.append(f"raw-sequence:{variant}")
    return leaks, revealed


def revealed_from_latest(body: str, issue: str) -> int | None:
    """latest-draw 家族：直接读响应里的 revealed_count（仅当期）。"""
    try:
        data = json.loads(body)
    except Exception:
        return None
    if not isinstance(data, dict) or str(data.get("current_issue") or "") != issue:
        return None
    count = data.get("revealed_count")
    return int(count) if isinstance(count, int) else None


def fetch(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> str:
    merged = {"Cache-Control": "no-cache", "User-Agent": "liuhecai-draw-leak-audit/1.0"}
    if headers:
        merged.update(headers)
    request = urllib.request.Request(url, headers=merged)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - 审计目标由调用方指定
        return response.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="开奖窗口泄漏审计")
    parser.add_argument("--base-url", default="http://127.0.0.1:3000", help="前端站点入口")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000", help="后端 API 入口")
    parser.add_argument("--site-key", default="twbst528", help="站点私有路由使用的 siteKey")
    parser.add_argument("--lottery-type", type=int, default=3)
    parser.add_argument("--issue", required=True, help="当期期号，例如 2026279")
    parser.add_argument("--numbers", required=True, help="当期号码 CSV（必须与库内一致，用于原始序列判定）")
    parser.add_argument("--until", required=True, help="结束时刻（北京时间 YYYY-MM-DD HH:MM:SS）")
    parser.add_argument("--interval", type=float, default=8.0)
    parser.add_argument("--host-header", default="", help="旧站私有路径需要的 Host 头（例：www.twcaibawang.com）")
    args = parser.parse_args()

    numbers = [item.strip() for item in args.numbers.split(",") if item.strip()]
    probes = build_probes(args.base_url, args.backend_url, args.site_key, args.lottery_type)
    headers = {"Host": args.host_header} if args.host_header else None
    until = datetime.strptime(args.until, "%Y-%m-%d %H:%M:%S").replace(tzinfo=BEIJING)

    leaks: dict[str, set[str]] = {name: set() for name, _, _ in probes}
    progress: dict[str, list[int]] = {}
    failures: dict[str, int] = {name: 0 for name, _, _ in probes}
    print(f"[audit] issue={args.issue} numbers={numbers} until={until.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)

    while datetime.now(BEIJING) <= until:
        stamp = datetime.now(BEIJING).strftime("%H:%M:%S")
        parts = [stamp]
        for name, kind, url in probes:
            try:
                body = fetch(url, headers)
            except urllib.error.HTTPError as exc:
                failures[name] += 1
                parts.append(f"{name}=HTTP{exc.code}")
                continue
            except Exception:
                failures[name] += 1
                parts.append(f"{name}=ERR")
                continue
            found, revealed = scan(body, args.issue, numbers)
            if kind == FORBIDDEN and found:
                leaks[name].update(found)
            if kind == FORBIDDEN:
                parts.append(f"{name}={'!!泄漏' if found else 'ok'}")
            else:
                if revealed is None:
                    revealed = revealed_from_latest(body, args.issue)
                if revealed is not None:
                    progress.setdefault(name, []).append(revealed)
                    parts.append(f"{name}={revealed}")
                else:
                    parts.append(f"{name}=-")
        print(" | ".join(parts), flush=True)
        time.sleep(max(1.0, args.interval))

    print("\n==== 汇总 ====")
    total = 0
    for name, kind, _ in probes:
        if kind == ALLOWED:
            print(f"[开奖模块] {name}: revealed_count 序列 = {progress.get(name, [])}")
        else:
            found = leaks[name]
            total += len(found)
            note = "" if not failures[name] else f"（{failures[name]} 次探测失败）"
            print(f"[其他接口] {name}: {'无泄漏' if not found else '!! 泄漏 ' + str(sorted(found)[:3])}{note}")
    if total:
        print(f"\nFAIL: 开奖窗口内其他接口共 {total} 处提前透露")
        return 1
    print("\nOK: 窗口内除开奖模块外没有任何接口提前透露当期号码")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
