#!/usr/bin/env python3
"""为 liuhecai nginx 站点配置注入两层加速：

1) http 层：开奖/聚合接口的 micro-cache 区域、gzip、带 $request_time 的日志格式；
2) 每个对外的 server 块：开奖关键路径 3s / 开奖与公告 5s / 预测聚合 20s 的
   代理缓存 location，以及 /vendor/ 静态直出（命中不到文件时回落到 Next.js）。

幂等：检测到标记注释即直接退出。默认 dry-run，--apply 才写回文件。
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

MARKER = "# >>> liuhecai edge cache (perf)"
HTTP_MARKER = "# >>> liuhecai edge cache http-level (perf)"
CACHE_LOG_MARKER = "# >>> liuhecai edge cache access log (perf)"
CACHE_LOG_LINE = "        access_log /var/log/nginx/kj_cache.log kj_timing;\n"

SECURITY_HEADERS = """        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-XSS-Protection "1; mode=block" always;
"""

PROXY_HEADERS = """        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
"""

HTTP_LEVEL_BLOCK = f"""{HTTP_MARKER}
# 开奖与预测聚合接口的边缘缓存区域：把同一 TTL 窗口内的重复请求合并为一次回源，
# 避免单进程 Next.js 被重复聚合拖慢（开奖面板轮询也在其中）。
proxy_cache_path /var/cache/nginx/kj levels=1:2 keys_zone=kj_api:16m max_size=512m inactive=10m use_temp_path=off;
proxy_cache_key "$scheme$request_method$host$request_uri";

# 与 Next.js 一致的压缩行为；缓存中保存未压缩响应体，由 nginx 按客户端压缩。
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_comp_level 4;
gzip_proxied any;
gzip_types text/plain text/css text/xml application/json application/javascript application/xml image/svg+xml;

# 便于用访问日志核对缓存命中与后端耗时（rt=总耗时 urt=上游耗时 ucs=缓存状态）。
log_format kj_timing '$remote_addr "$request" $status $body_bytes_sent rt=$request_time urt=$upstream_response_time ucs=$upstream_cache_status';

"""


def cache_location(regex: str, ttl: str, comment: str, use_stale: str | None = None) -> str:
    listed = use_stale or "updating error timeout http_500 http_502 http_503 http_504"
    return f"""    # {comment}
    location ~ {regex} {{
        proxy_cache kj_api;
        proxy_cache_valid 200 {ttl};
        proxy_cache_lock on;
        proxy_cache_lock_timeout 5s;
        proxy_cache_use_stale {listed};
        proxy_cache_background_update on;
        proxy_ignore_headers Cache-Control Expires Set-Cookie;
        proxy_hide_header Set-Cookie;
        proxy_set_header Accept-Encoding "";
        add_header X-Cache-Status $upstream_cache_status always;
{SECURITY_HEADERS}        proxy_pass http://$be_frontend;
{PROXY_HEADERS}    }}

"""


SERVER_BLOCK = f"""    {MARKER}
{cache_location(r"^/api/(latest-draw|next-draw-deadline|site-links)$", "1s", "开奖关键路径：1 秒微缓存 + 并发合并（只允许 updating 时用旧值，避免后端故障时长期陈旧）", use_stale="updating")}{cache_location(r"^/api/sites/[A-Za-z0-9_-]+/draw$", "5s", "站点开奖接口：5 秒微缓存")}{cache_location(r"^/api/(kaijiang/|public/forced-announcement$|index/notice$)", "20s", "旧站预测资料与公告：20 秒微缓存")}{cache_location(r"^/api/sites/[A-Za-z0-9_-]+/(prediction-modules|site-page)$", "20s", "站点预测资料聚合：20 秒微缓存")}{cache_location(r"^/api/(vendor|twjinniu|twcf888|twcaibawang|twsaimahui|shengshi8800|twssz|twbst528|twjsz666|twsyw|twwanli)/(homepage-modules|site-page|article-detail)$", "20s", "首页/文章聚合：20 秒微缓存")}    # /vendor 静态直出：不再占用单进程 Node；未命中时回落到 Next.js
    location ~ ^/vendor/[^/]+/(history|wylhc)\\.html$ {{
        # Next.js 会把这两个旧路径改写为 /history 页面，必须继续走应用。
        proxy_pass http://$be_frontend;
{PROXY_HEADERS}    }}

    location ~ ^/vendor/[^/]+/static/ {{
        root /srv/public;
        access_log off;
        # 与 Next.js 的 /vendor/:siteKey/static/:path* 规则保持一致（不再使用
        # expires，避免与 add_header 重复下发 Cache-Control）。
        add_header Cache-Control "public, max-age=31536000, immutable" always;
{SECURITY_HEADERS}        try_files $uri @vendor_frontend;
    }}

    location /vendor/ {{
        root /srv/public;
        access_log off;
        # 与 Next.js 现有行为一致：HTML/根级 JS 每次协商，部署后立即生效。
        add_header Cache-Control "public, max-age=0, must-revalidate" always;
{SECURITY_HEADERS}        try_files $uri @vendor_frontend;
    }}

    location @vendor_frontend {{
        proxy_pass http://$be_frontend;
{PROXY_HEADERS}    }}

"""


def server_block_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in re.finditer(r"(?m)^\s*server\s*\{", text):
        start = match.start()
        depth = 0
        index = match.end() - 1
        while index < len(text):
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    spans.append((start, index + 1))
                    break
            index += 1
    return spans


def patch(text: str) -> tuple[str, int]:
    if HTTP_MARKER in text:
        return text, 0

    first_server = re.search(r"(?m)^\s*server\s*\{", text)
    if not first_server:
        raise SystemExit("no server block found")

    text = text[: first_server.start()] + HTTP_LEVEL_BLOCK + text[first_server.start() :]

    inserted = 0
    for start, end in reversed(server_block_spans(text)):
        block = text[start:end]
        if "proxy_pass http://$be_frontend;" not in block:
            continue
        anchor = None
        for candidate in (r"(?m)^\s*location\s+/api/\s*\{", r"(?m)^\s*location\s+/\s*\{"):
            found = re.search(candidate, block)
            if found:
                anchor = start + found.start()
                break
        if anchor is None:
            continue
        text = text[:anchor] + SERVER_BLOCK + text[anchor:]
        inserted += 1
    return text, inserted


def add_cache_access_log(text: str) -> tuple[str, int]:
    """给缓存 location 加独立访问日志（kj_timing：rt/urt/ucs），便于核对命中率。"""
    if CACHE_LOG_MARKER in text:
        return text, 0
    updated = text.replace(
        "        proxy_cache kj_api;\n",
        "        proxy_cache kj_api;\n" + CACHE_LOG_LINE,
    )
    added = updated.count(CACHE_LOG_LINE)
    if added == 0:
        return text, 0
    first_server = re.search(r"(?m)^\s*server\s*\{", updated)
    marker_line = f"{CACHE_LOG_MARKER} 缓存的访问日志由下方各 location 内的 access_log 写入。\n"
    updated = updated[: first_server.start()] + marker_line + updated[first_server.start() :]
    return updated, added


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("conf")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir")
    parser.add_argument(
        "--add-access-log",
        action="store_true",
        help="只补缓存 location 的 kj_timing 访问日志（第二步）",
    )
    args = parser.parse_args()

    path = Path(args.conf)
    original = path.read_text(encoding="utf-8")

    if args.add_access_log:
        updated, added = add_cache_access_log(original)
        print(f"cache access_log added to {added} location(s)")
        if added == 0:
            print("nothing to do")
            return 0
        if not args.apply:
            print("dry-run: nothing written")
            return 0
        if args.backup_dir:
            backup_root = Path(args.backup_dir)
            backup_root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            target = backup_root / f"{path.name}.pre-cache-log-{stamp}"
            shutil.copy2(path, target)
            print(f"backup: {target}")
        path.write_text(updated, encoding="utf-8", newline="")
        print(f"written: {path}")
        return 0

    if HTTP_MARKER in original:
        print(f"already patched: {path}")
        return 0

    updated, inserted = patch(original)
    print(f"server blocks patched: {inserted}")
    if inserted == 0:
        raise SystemExit("no serving server block matched; refusing to write")

    if not args.apply:
        print("dry-run: nothing written")
        return 0

    if args.backup_dir:
        backup_root = Path(args.backup_dir)
        backup_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = backup_root / f"{path.name}.pre-edge-cache-{stamp}"
        shutil.copy2(path, target)
        print(f"backup: {target}")

    path.write_text(updated, encoding="utf-8", newline="")
    print(f"written: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
