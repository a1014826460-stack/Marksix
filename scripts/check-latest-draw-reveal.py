"""开奖分片揭示的现场核验脚本（只读 + 可选写入测试行）。

用途
----
在真实开奖窗口或人造测试行上，按秒采样 ``/api/public/latest-draw``，确认号码
严格按 ``reveal_start + 25s×N`` 逐球开放：

- 第 1 球在 ``reveal_start`` 当刻可见；
- ``revealed_count`` 不得超过服务器时间允许的上限（源站未齐时可以更少）；
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

    python scripts/check-latest-draw-reveal.py --base-url https://www.tw8800.com --lottery-type 3 --expected-issue 2026281 --duration 260 --jsonl taiwan-2026281.jsonl

建议指定当晚完整期号并保存脱敏 JSONL；旧期响应仍记录，但不参与当期核验，
也不会让采样提前结束。记录仅含期号、数量、布尔状态和时间，不包含开奖号码。
没有观测到目标期完整响应时返回 ``incomplete``（退出码 3），不能认定核验通过。

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
import math
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

from public.draw_reveal import is_paced_lottery_type, reveal_anchor  # noqa: E402
from core.time_utils import BEIJING_TZ  # noqa: E402

DEFAULT_INTERVAL_SECONDS = 5.0
REQUEST_TIMEOUT_SECONDS = 5.0
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


def _fetch(
    base_url: str,
    lottery_type: int,
    *,
    request_ts: int | None = None,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
) -> dict:
    request_ts = int(time.time() * 1000) if request_ts is None else request_ts
    url = f"{base_url.rstrip('/')}/api/public/latest-draw?lottery_type={lottery_type}&_ts={request_ts}"
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - 用户指定地址
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("latest-draw response is not an object")
    return payload


def _parse_seconds(text: str) -> float | None:
    try:
        return datetime.strptime(str(text).strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=BEIJING_TZ).timestamp()
    except (ValueError, TypeError):
        return None


def _is_delivered_ball(ball: object) -> bool:
    return isinstance(ball, dict) and bool(str(ball.get("value") or "").strip())


def validate_sample(
    payload: dict,
    *,
    lottery_type: int,
    clienttime: float,
    expected_issue: str | None = None,
    last_count: int = -1,
    request_ts: int | None = None,
) -> dict:
    """Pure validation; return only safe metadata, never retain number values."""
    issue = str(payload.get("current_issue", payload.get("issue")) or "").strip()
    raw_count = payload.get("revealed_count")
    try:
        if isinstance(raw_count, bool) or str(raw_count).strip() != str(int(raw_count)):
            raise ValueError
        count = int(raw_count)
    except (ValueError, TypeError, OverflowError):
        count = None
    balls = payload.get("result_balls") or []
    special = _is_delivered_ball(payload.get("special_ball"))
    normal_count = sum(_is_delivered_ball(ball) for ball in balls) if isinstance(balls, list) else 0
    delivered = normal_count + int(special)
    paced = is_paced_lottery_type(lottery_type)
    anchor_datetime = reveal_anchor(payload, paced=paced)
    anchor_text = anchor_datetime.strftime("%Y-%m-%d %H:%M:%S") if anchor_datetime is not None else None
    anchor = anchor_datetime.timestamp() if anchor_datetime is not None else None
    raw_server_now = payload.get("server_now")
    try:
        server_now = float(raw_server_now)
        if isinstance(raw_server_now, bool) or not math.isfinite(server_now):
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        server_now = None
    now = clienttime if server_now is None else server_now
    allowed = None
    if not paced:
        allowed = 7
    elif anchor is not None:
        elapsed = now - anchor
        allowed = 0 if elapsed < 0 else min(7, int(elapsed // 25) + 1)
    record = {
        "issue": issue or None,
        "balls": count,
        "delivered": delivered,
        "specialbool": special,
        "server_now": server_now,
        "anchor": anchor_text,
        "clienttime": clienttime,
        "request_ts": request_ts,
        "error": [],
        "allowed_count": allowed,
    }
    matches = expected_issue is None or issue == str(expected_issue).strip()
    errors: list[str] = []
    if not matches:
        record["error"] = ["期号不匹配：仅记录，不参与目标期核验"]
    elif payload:
        if count is None:
            errors.append("响应缺少有效 revealed_count")
        elif not 0 <= count <= 7:
            errors.append("revealed_count 超出 0..7")
        else:
            if count < last_count:
                errors.append(f"进度回退：{last_count} → {count}")
            if delivered != count:
                errors.append(f"下发号码数与 revealed_count 不一致：count={count} delivered={delivered}")
            if special and count < 7:
                errors.append(f"特码提前下发：revealed_count={count}")
            if bool(payload.get("is_complete")) != (count == 7):
                errors.append(f"is_complete 与进度不一致：count={count}")
        if not isinstance(balls, list):
            errors.append("result_balls 不是列表")
        elif normal_count != len(balls):
            errors.append("result_balls 包含未交付的空值或畸形球位置")
        elif len(balls) > 6:
            errors.append("result_balls 超过 6 个常规球")
        if payload.get("special_ball") is not None and not special:
            errors.append("special_ball 缺少有效号码值")
        if paced:
            if raw_server_now is not None and server_now is None:
                errors.append("server_now 无效")
            if anchor is None and (delivered or (count or 0) > 0):
                errors.append("已下发号码但缺少有效揭示锚点")
            if allowed is not None:
                if (count is not None and count > allowed) or delivered > allowed:
                    errors.append(f"超过服务器时间上限：allowed={allowed} count={count} delivered={delivered}")
                if special and allowed < 7:
                    errors.append(f"特码早于服务器允许时间：allowed={allowed}")
        elif str(payload.get("next_reveal_at") or "").strip():
            errors.append("非节拍彩种不应下发 next_reveal_at")
        record["error"] = errors
    complete = matches and not errors and count == 7 and normal_count == 6 and special and bool(payload.get("is_complete"))
    return {"record": record, "errors": errors, "matches": matches, "count": count, "complete": complete}


def main() -> int:
    parser = argparse.ArgumentParser(description="核验开奖号码的服务端分片揭示节奏")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--lottery-type", type=int, default=3)
    parser.add_argument("--duration", type=float, default=200.0, help="采样总时长（秒）")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_SECONDS, help="采样间隔（秒）")
    parser.add_argument("--expected-issue", help="当晚目标完整期号；旧期只记录，不参与核验或结束条件")
    parser.add_argument("--jsonl", help="追加脱敏采样记录（仅数量、时间、期号，无开奖号码）")
    parser.add_argument("--seed-local", action="store_true", help="写入临时测试行（仅本地开发库）")
    parser.add_argument(
        "--seed-lottery-type",
        type=int,
        default=3,
        help="临时测试行借用的彩种 ID（必须是 lottery_types 里已存在的类型）",
    )
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    args = parser.parse_args()
    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error("--duration 必须是有限正数")
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("--interval 必须是有限正数")

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
    started = time.monotonic()
    deadline = started + args.duration
    last_count = -1
    last_issue = None
    completed = False
    paced = is_paced_lottery_type(lottery_type)
    print(f"[mode] lottery_type={lottery_type} 揭示口径={'台湾彩 25 秒/球（服务端节拍）' if paced else '港澳彩 一次性全量（不节流）'}")
    log = None
    try:
        if args.jsonl:
            log = open(args.jsonl, "a", encoding="utf-8")
        while time.monotonic() < deadline:
            clienttime = time.time()
            request_ts = int(clienttime * 1000)
            try:
                payload = _fetch(
                    args.base_url, lottery_type, request_ts=request_ts,
                    timeout=min(REQUEST_TIMEOUT_SECONDS, deadline - time.monotonic()),
                )
            except (OSError, ValueError) as exc:
                # 不写异常正文，避免服务端响应或 URL 意外夹带号码。
                record = validate_sample({}, lottery_type=lottery_type, clienttime=time.time(), request_ts=request_ts)["record"]
                record["error"] = [f"请求失败：{type(exc).__name__}"]
                print(f"[retry] {record['error'][0]}")
            else:
                issue = str(payload.get("current_issue", payload.get("issue")) or "").strip()
                previous_count = last_count if issue == last_issue else -1
                checked = validate_sample(
                    payload, lottery_type=lottery_type, clienttime=time.time(),
                    expected_issue=args.expected_issue, last_count=previous_count, request_ts=request_ts,
                )
                record = checked["record"]
                if checked["matches"]:
                    failures.extend(checked["errors"])
                    if checked["count"] is not None:
                        last_count = max(previous_count, checked["count"])
                        last_issue = issue
                    completed = checked["complete"]
                print(
                    f"t+{time.monotonic() - started:6.1f}s issue={record['issue'] or '-'} "
                    f"revealed={record['balls']} delivered={record['delivered']} "
                    f"special={record['specialbool']} allowed={record['allowed_count']} "
                    f"target={checked['matches']} complete={checked['complete']}"
                )
            if log is not None:
                log.write(json.dumps(record, ensure_ascii=False) + "\n")
                log.flush()
            if completed:
                print("[done] 目标期 7 个号码已全部开放")
                break
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(max(0.05, args.interval), remaining))
    finally:
        if log is not None:
            log.close()
        if seeded:
            _delete_seed_row(args.database_url, lottery_type)
            print("[seed] 临时测试行已删除")

    if failures:
        print("\n核验失败：")
        for item in dict.fromkeys(failures):
            print(" -", item)
        return 1
    if not completed:
        print("\n[incomplete] 采样结束，尚未观测到目标期完整响应；核验未完成")
        return 3
    print("\n核验通过：号码按服务器时间逐球开放")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
