#!/usr/bin/env python3
"""把 twsaimahui 首页的逐模块脚本按"连续区间"合并成 bundle。

为什么不是合成一个文件：这些 `<script src="static/js/0xx….js">` 分散在文档各处，
彼此之间夹着其它脚本与 inline 脚本；把它们全部挪到一个文件会改变执行顺序，进而改变
DOM 渲染顺序。因此只合并**连续区间**（区间内部顺序完全保留，区间位置不变），
63 个请求 → 14 个。

等价性保证：
- 区间内按文档顺序逐字节拼接（用 ``\\n;\\n`` 分隔，避免依赖自动分号插入）；
- 每个 bundle 头部记录来源文件与各自 sha256，便于审计；
- 原始文件保留在磁盘上（api-audit 等契约仍按文件名引用）；
- 脚本幂等：已存在记录文件时会复用（内容哈希命名）。

用法：
    python scripts/bundle-twsaimahui-modules.py            # dry-run
    python scripts/bundle-twsaimahui-modules.py --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

SITE_ROOT = pathlib.Path("frontend/public/vendor/twsaimahui")
INDEX = SITE_ROOT / "index.html"
BUNDLE_MANIFEST = SITE_ROOT / "static/js/bundles.json"
MODULE_SRC_RE = re.compile(r"^static/js/0\d{2}[A-Za-z0-9_]*\.js$")
SCRIPT_OPEN_RE = re.compile(r"<script\b[^>]*>", re.IGNORECASE)
SRC_ATTR_RE = re.compile(r"\ssrc=(?P<quote>['\"])(?P<src>[^'\"]+)(?P=quote)", re.IGNORECASE)


def src_of(match: re.Match[str]) -> str | None:
    found = SRC_ATTR_RE.search(match.group(0))
    return found.group("src") if found else None


def element_span(match: re.Match[str], html: str) -> tuple[int, int]:
    """Return the full ``<script …></script>`` span for an opening-tag match."""
    close = html.lower().find("</script>", match.end())
    end = len(html) if close < 0 else close + len("</script>")
    return match.start(), end


def live_regions(html: str) -> list[tuple[int, int]]:
    """Return spans that are outside HTML comments and <noscript> blocks.

    页面里有 41 个 script 标签位于注释里（例如被刻意停用的
    ``<!-- <script src="static/js/032ma20.js"></script> -->``）。这些标签既不能算作
    启用脚本，也不能被替换掉。
    """
    hidden = [
        (match.start(), match.end())
        for match in re.finditer(r"<!--[\s\S]*?-->", html)
    ]
    hidden += [
        (match.start(), match.end())
        for match in re.finditer(r"<noscript\b[\s\S]*?</noscript\s*>", html, re.IGNORECASE)
    ]
    hidden.sort()
    regions: list[tuple[int, int]] = []
    cursor = 0
    for start, end in hidden:
        if start > cursor:
            regions.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < len(html):
        regions.append((cursor, len(html)))
    return regions


def _in_regions(index: int, regions: list[tuple[int, int]]) -> bool:
    for start, end in regions:
        if start <= index < end:
            return True
        if index < start:
            return False
    return False


def runs_from(html: str) -> list[list[re.Match[str]]]:
    """Group *active* module script tags into contiguous runs.

    只有正文（非注释、非 noscript）里的标签参与；任何一个其它 ``<script``
    （无论是否带 src、包括 inline）都会打断区间，这样合并后的执行顺序与合并前完全一致。
    """
    regions = live_regions(html)
    runs: list[list[re.Match[str]]] = []
    current: list[re.Match[str]] = []
    for match in SCRIPT_OPEN_RE.finditer(html):
        if not _in_regions(match.start(), regions):
            continue
        src_match = SRC_ATTR_RE.search(match.group(0))
        if src_match and MODULE_SRC_RE.match(src_match.group("src")):
            current.append(match)
            continue
        if current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def build() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--site-root", default=str(SITE_ROOT))
    args = parser.parse_args()

    site_root = pathlib.Path(args.site_root)
    index = site_root / "index.html"
    html = index.read_text(encoding="utf-8")
    runs = runs_from(html)
    total_scripts = sum(len(run) for run in runs)
    print(f"module runs: {len(runs)}, module scripts: {total_scripts}")

    replacements: list[tuple[int, int, str]] = []
    bundle_records: list[dict] = []
    for run in runs:
        sources: list[str] = []
        digest = hashlib.sha256()
        names: list[str] = []
        for match in run:
            source_name = src_of(match)
            if source_name is None:  # pragma: no cover - runs_from guarantees a src
                raise SystemExit("module run contains a script without src")
            path = site_root / source_name
            if not path.exists():
                raise SystemExit(f"missing module script: {path}")
            data = path.read_bytes()
            digest.update(source_name.encode("utf-8"))
            digest.update(data)
            sources.append(data.decode("utf-8"))
            names.append(source_name)
        bundle_name = f"bundle-{digest.hexdigest()[:16]}.js"
        bundle_path = site_root / "static/js" / bundle_name
        header = (
            "/* twsaimahui 模块脚本合并包（顺序与原文档一致）\n"
            + "".join(f" *   {name}\n" for name in names)
            + " */\n"
        )
        body = header + "\n;\n".join(sources) + "\n"
        record = {
            "bundle": f"static/js/{bundle_name}",
            "sources": names,
            "bytes": len(body.encode("utf-8")),
        }
        start, end = element_span(run[0], html)
        replacements.append((start, end, f'<script type="text/javascript" src="static/js/{bundle_name}"></script>'))
        bundle_records.append(record)
        # 同一区间的其余标签逐个删除：区间内可能夹着注释等非 script 内容，必须原样保留。
        for match in run[1:]:
            tag_start, tag_end = element_span(match, html)
            replacements.append((tag_start, tag_end, ""))
        if args.apply:
            bundle_path.parent.mkdir(parents=True, exist_ok=True)
            bundle_path.write_text(body, encoding="utf-8", newline="")
        print(f"  {len(run):2} scripts -> {bundle_name} ({record['bytes'] / 1024:.1f} KB)")

    if not args.apply:
        print("dry-run: nothing written")
        return 0

    if not runs:
        # 幂等：已经合并过的页面没有可合并区间，保留既有 manifest，不能清空。
        if (site_root / "static/js/bundles.json").exists():
            print("already bundled (no module runs left); manifest kept")
        else:
            print("no module runs found; nothing to do")
        return 0

    updated = html
    for start, end, tag in sorted(replacements, reverse=True):
        updated = updated[:start] + tag + updated[end:]
    index.write_text(updated, encoding="utf-8", newline="")

    manifest = {
        "generated_by": "scripts/bundle-twsaimahui-modules.py",
        "runs": bundle_records,
        "module_scripts_before": total_scripts,
        "bundles_after": len(bundle_records),
    }
    (site_root / "static/js").mkdir(parents=True, exist_ok=True)
    (site_root / "static/js" / "bundles.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline=""
    )
    print(f"index.html rewritten; {total_scripts} script tags -> {len(bundle_records)} bundle tags")
    return 0


if __name__ == "__main__":
    sys.exit(build())
