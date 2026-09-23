#!/usr/bin/env python3
"""把已部署的开奖微缓存 tier 收紧为 1 秒 + 仅 updating 时使用旧值。

背景（2026-09-24 时效审计）：开奖链路每一层都必须尽快反映真实开奖。
- `/api/latest-draw`、`/api/next-draw-deadline`、`/api/site-links` 原本 3 秒 TTL；
- 原 `proxy_cache_use_stale` 含 `error timeout http_5xx`，后端故障时会一直返回旧开奖。

本脚本幂等：已是 1 秒与 `updating` 时直接报告无需修改。默认 dry-run，`--apply` 才写回。
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shutil
from datetime import datetime, timezone

DRAW_TIER = re.compile(
    r"(location ~ \^/api/\(latest-draw\|next-draw-deadline\|site-links\)\$ \{\n)(.*?)(\n    \})",
    re.S,
)


def tighten(text: str) -> tuple[str, int]:
    changed = 0

    def fix(match: re.Match[str]) -> str:
        nonlocal changed
        body = match.group(2)
        updated = body.replace("proxy_cache_valid 200 3s;", "proxy_cache_valid 200 1s;")
        updated = updated.replace(
            "proxy_cache_use_stale updating error timeout http_500 http_502 http_503 http_504;",
            "proxy_cache_use_stale updating;",
        )
        if updated != body:
            changed += 1
        return match.group(1) + updated + match.group(3)

    return DRAW_TIER.sub(fix, text), changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("conf")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir")
    args = parser.parse_args()

    path = pathlib.Path(args.conf)
    original = path.read_text(encoding="utf-8")
    updated, changed = tighten(original)
    total = len(DRAW_TIER.findall(original))
    print(f"draw-tier blocks: {total}, tightened: {changed}")
    if not changed:
        print("already tightened")
        return 0
    if not args.apply:
        print("dry-run: nothing written")
        return 0
    if args.backup_dir:
        backup = pathlib.Path(args.backup_dir)
        backup.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(path, backup / f"{path.name}.pre-tighten-{stamp}")
        print(f"backup: {backup / f'{path.name}.pre-tighten-{stamp}'}")
    path.write_text(updated, encoding="utf-8", newline="")
    print(f"written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
