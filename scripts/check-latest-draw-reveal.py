"""开奖分片揭示的现场核验脚本（只读 + 可选写入测试行）。

用途
----
在真实开奖窗口或人造测试行上，按秒采样 ``/api/public/latest-draw``，确认号码
严格按 ``reveal_start + 25s×N`` 逐球开放：

- 第 1 球在 ``reveal_start`` 当刻可见；
- 每秒的 ``revealed_count`` 只由服务器时间决定（与请求次数无关）；
- 特码只在 ``revealed_count == 7`` 时出现；
- ``is_complete`` 与 ``next_reveal_at`` 与进度自洽。

彩种口径（2026-10-05 用户口径）
------------------------------
只有**台湾彩（3）**走 25 秒/球的服务端节拍；港澳彩（1/2）源站本来就公开号码，
已入库几个就下发几个、``next_reveal_at`` 恒为空串、不叠加时间闸门。
因此 ``--lottery-type 1|2`` 时脚本只校验「一次给全 + 不倒退 + 特码不提前」。

用法
----
现场观察（线上/本地均可，默认台湾彩）::

    python scripts/check-latest-draw-reveal.py --base-url https://www.tw8800.com --lottery-type 3 --duration 260

人造测试行（仅本地开发库；结束自动删除）::

    python scripts/check-latest-draw-reveal.py --seed-local --database-url "$env:DATABASE_URL" --duration 200

``--seed-local`` 会写入一条临时期（默认借 ``lottery_type_id=3`` 且期号 ``901``，
因为 ``lottery_draws.lottery_type_id`` 有指向 ``lottery_types`` 的外键），
同时打印该期的 ``reveal_start``，并在结束后删除该行。仅用于本地开发库；
``--seed-lottery-type 1|2`` 时写入的港澳行属于「非节拍」口径，脚本按非节拍校验。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = REPO_ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from public.draw_reveal import is_paced_lottery_type  # noqa: E402

DEFAULT_INTERVAL_SECONDS = 5.0
SEED_TERM = 901


def _insert_seed_row(database_url: str, lottery_type_id: int) -> str:
    from core.time_utils import BEIJING_TZ
    from db import connect

    now = datetime.now(BEIJING_TZ)
    opened_at = (now - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
    draw_time = (now - timedelta(seconds=3)).strftime("%Y-%m-%d %H:%M:%S")
    with connect(database_url) as conn:
        conn.execute(
            "DELETE FROM lottery_draws WHERE lottery_type_id = ? AND term = ?",
            (lottery_type_id, SEED_TERM),
        )
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, status,
                is_opened, next_term, opened_at, created_at, updated_at
            ) VALUES (?, 2026, ?, '01,02,03,04,05,06,07', ?, 1, 1, ?, ?, ?, ?)
            """,
            (lottery_type_id, SEED_TERM, draw_time, SEED_TERM + 1, opened_at, opened_at, opened_at),
        )
    return opened_at


def _delete_seed_row(database_url: str, lottery_type_id: int) -> None:
    from db import connect

    with connect(database_url) as conn:
        conn.execute(
            "DELETE FROM lottery_draws WHERE lottery_type_id = ? AND term = ?",
            (lottery_type_id, SEED_TERM),
        )


def _fetch(base_url: str, lottery_type: int) -> dict:
    url = f"{base_url.rstrip('/')}/api/public/latest-draw?lottery_type={lottery_type}"
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - 固定内部/公开地址
        return json.loads(response.read().decode("utf-8"))


def _parse_seconds(text: str) -> float | None:
    try:
        return datetime.strptime(str(text).strip(), "%Y-%m-%d %H:%M:%S").timestamp()
    except (ValueError, TypeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="核验开奖号码的服务端分片揭示节奏")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--lottery-type", type=int, default=3)
    parser.add_argument("--duration", type=float, default=200.0, help="采样总时长（秒）")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_SECONDS, help="采样间隔（秒）")
    parser.add_argument("--seed-local", action="store_true", help="写入临时测试行（仅本地开发库）")
    parser.add_argument(
        "--seed-lottery-type",
        type=int,
        default=3,
        help="临时测试行借用的彩种 ID（必须是 lottery_types 里已存在的类型）",
    )
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    args = parser.parse_args()

    lottery_type = args.lottery_type
    seeded = False
    if args.seed_local:
        if not args.database_url:
            print("--seed-local 需要 --database-url 或 DATABASE_URL", file=sys.stderr)
            return 2
        lottery_type = args.seed_lottery_type
        opened_at = _insert_seed_row(args.database_url, lottery_type)
        seeded = True
        print(f"[seed] lottery_type={lottery_type} term={SEED_TERM} opened_at={opened_at}")

    failures: list[str] = []
    started = time.time()
    last_count = -1
    paced = is_paced_lottery_type(lottery_type)
    print(f"[mode] lottery_type={lottery_type} 揭示口径={'台湾彩 25 秒/球（服务端节拍）' if paced else '港澳彩 一次性全量（不节流）'}")
    try:
        while time.time() - started <= args.duration:
            payload = _fetch(args.base_url, lottery_type)
            count = payload.get("revealed_count")
            anchor = _parse_seconds(payload.get("reveal_start") or "")
            now = time.time()
            elapsed = None if anchor is None else now - anchor
            balls = payload.get("result_balls") or []
            special = payload.get("special_ball")
            print(
                f"t+{now - started:6.1f}s elapsed={('%.1f' % elapsed) if elapsed is not None else 'n/a':>6} "
                f"revealed={count} balls={len(balls)} special={'yes' if special else 'no'} "
                f"complete={payload.get('is_complete')} next={payload.get('next_reveal_at') or '-'}"
            )

            if count is None:
                failures.append("响应缺少 revealed_count（后端未部署分片揭示）")
            else:
                count = int(count)
                if count < last_count:
                    failures.append(f"进度回退：{last_count} → {count}")
                last_count = max(last_count, count)
                delivered = len(balls) + (1 if special else 0)
                if count < 7 and delivered != count:
                    failures.append(f"下发号码数与 revealed_count 不一致：count={count} delivered={delivered}")
                if special and count < 7:
                    failures.append(f"特码提前下发：revealed_count={count}")
                if bool(payload.get("is_complete")) != (count >= 7):
                    failures.append(f"is_complete 与进度不一致：count={count}")
                if paced:
                    if elapsed is not None and elapsed >= 0:
                        expected = min(7, int(elapsed // 25) + 1)
                        if abs(count - expected) > 1:
                            failures.append(f"节奏偏差：elapsed={elapsed:.1f}s 期望约 {expected}，实际 {count}")
                else:
                    # 港澳彩：不节流，拿到几个就是几个；不承诺下一次揭示时间。
                    if str(payload.get("next_reveal_at") or "").strip():
                        failures.append(
                            f"非节拍彩种不应下发 next_reveal_at：{payload.get('next_reveal_at')!r}"
                        )
                    if count >= 7 and delivered != 7:
                        failures.append(f"已完整但下发号码数不为 7：delivered={delivered}")

            if last_count >= 7:
                print("[done] 7 个号码已全部开放")
                break
            time.sleep(max(0.5, args.interval))
    finally:
        if seeded:
            _delete_seed_row(args.database_url, lottery_type)
            print("[seed] 临时测试行已删除")

    if failures:
        print("\n核验失败：")
        for item in dict.fromkeys(failures):
            print(" -", item)
        return 1
    print("\n核验通过：号码按服务器时间逐球开放")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
