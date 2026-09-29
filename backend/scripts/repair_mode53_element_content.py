#!/usr/bin/env python
"""统一「五行」口径：把 ``created.mode_payload_53`` / ``created.mode_payload_482`` 正文里
每个五行标签后的**号码清单**重写为号码五行清单。

背景
----
`public.fixed_data` 有两套互不相同的五行分组：

* ``sign='五行'``（**号码五行**，权威口径，2026-09-29 二次改判后的新表）：
  金 04,05,12,13,26,27,34,35,42,43 / 木 08,09,16,17,24,25,38,39,46,47 /
  水 01,14,15,22,23,30,31,44,45 / 火 02,03,10,11,18,19,32,33,40,41,48,49 /
  土 06,07,20,21,28,29,36,37。与 ``predict.common.ELEMENT_NUMBER_GROUPS`` 完全一致，
  并由 versioned migration 32 同步落库。
* ``sign='五行肖'``（**生肖五行**，旧口径）：金肖 鸡,猴 / 木肖 兔,虎 / 水肖 鼠,猪 / 火肖 蛇,马 /
  土肖 牛,龙,羊,狗。

后端判定链用**号码五行**（``predict.common.build_element_number_map`` →
``ELEMENT_NUMBER_GROUPS``；``public.api._compute_outcome_from_row`` 的 ``element`` 原子，
见 ``_ELEMENT_MAP``）。但历史上落库的 mode 53（三行中特）/ mode 482（四行中特）正文，
号码清单是按**生肖五行**（生肖号段）拼出来的，于是同一个特码可能在判定上「中」、
在展示的候选清单里却找不到（例：45 的号码五行是木，生肖是狗 → 旧正文把 45 写进【土】）。

本脚本只改**展示用的号码清单**：标签名、条目顺序与数量、期号、其它列一律不动，
也不触碰 ``public.*``。

安全约束
--------
* 默认 ``--dry-run``：只统计与打印前后对照，绝不写库；``--apply`` 才写。
* 只更新 ``created.mode_payload_53`` / ``created.mode_payload_482`` 的 ``content`` 一列
  （SQL 在 ``utils/created_prediction_store.py``，带「id + 原正文」比较条件，
  并发写入会让语句影响 0 行而不是静默覆盖）。
* 幂等：清单已经是权威口径的行直接跳过，重复执行第二次的结果一定是「0 行待改」。
* 权威清单在执行前会与 ``predict.common.ELEMENT_NUMBER_GROUPS`` 交叉校验，不一致即终止。
* ``--manifest`` 导出「id / 原正文 / 新正文」，既是干跑证据，也是回滚依据；
  ``--rollback`` 可据此把正文逐行还原。

用法
----
    cd backend/src

    # 干跑（默认，不写库）并导出回滚清单
    python ../scripts/repair_mode53_element_content.py --db-path "$env:DATABASE_URL" `
        --manifest ../.codex-temp/mode53-element-manifest.json

    # 真正写库（生产必须先备份、先干跑审阅）
    python ../scripts/repair_mode53_element_content.py --db-path "$env:DATABASE_URL" `
        --apply --manifest ../.codex-temp/mode53-element-manifest-applied.json

    # 幂等复核：应显示「将修改 0 行」
    python ../scripts/repair_mode53_element_content.py --db-path "$env:DATABASE_URL"

    # 回滚（按 manifest 逐行还原，仍然只写 content 一列）
    python ../scripts/repair_mode53_element_content.py --db-path "$env:DATABASE_URL" `
        --rollback ../.codex-temp/mode53-element-manifest-applied.json --apply
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from db import connect  # noqa: E402
from predict.common import ELEMENT_NUMBER_GROUPS, ELEMENT_ORDER  # noqa: E402
from utils.created_prediction_store import (  # noqa: E402
    list_created_content_rows,
    load_element_number_groups,
    rewrite_element_group_content,
    update_created_content_row,
)

#: 本轮修复的目标表（三行中特 / 四行中特）。
DEFAULT_TABLES: tuple[str, ...] = ("mode_payload_53", "mode_payload_482")
MODE_PAYLOAD_TABLE_RE = re.compile(r"^mode_payload_\d+$")


@dataclass(frozen=True)
class PlannedChange:
    """一行待改写的正文（before/after 全量保留，供审阅与回滚）。"""

    table: str
    locator: tuple[tuple[str, str], ...]
    web_id: Any
    year: str
    term: str
    before: str
    after: str

    @property
    def label(self) -> str:
        """报告用标识：`id` 缺失的历史行显示自然键。"""

        return " ".join(f"{column}={value}" for column, value in self.locator)

    def as_manifest(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "locator": [[column, value] for column, value in self.locator],
            "web_id": self.web_id,
            "year": self.year,
            "term": self.term,
            "before": self.before,
            "after": self.after,
        }


@dataclass
class TableScan:
    """单表扫描统计。"""

    table: str
    scanned: int = 0
    pending: int = 0
    already_canonical: int = 0
    not_element_content: int = 0
    unlocatable: int = 0
    web_ids: dict[str, int] = None  # type: ignore[assignment]
    samples: list[PlannedChange] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.web_ids is None:
            self.web_ids = {}
        if self.samples is None:
            self.samples = []


def normalize_codes(codes: Any) -> tuple[str, ...]:
    """把号码序列归一为两位字符串（`'3'` → `'03'`）。"""

    normalized: list[str] = []
    for value in codes or ():
        text = str(value).strip()
        if not text:
            continue
        try:
            normalized.append(f"{int(text):02d}")
        except (TypeError, ValueError):
            continue
    return tuple(normalized)


def resolve_element_groups(conn: Any) -> dict[str, tuple[str, ...]]:
    """读取并校验权威号码五行分组。

    Raises:
        SystemExit: `public.fixed_data` 缺少 ``sign='五行'``，或与
            ``predict.common.ELEMENT_NUMBER_GROUPS`` 不一致时终止（宁可不动数据）。
    """

    canonical = {label: normalize_codes(ELEMENT_NUMBER_GROUPS.get(label, ())) for label in ELEMENT_ORDER}
    try:
        from_db = load_element_number_groups(conn)
    except Exception as exc:  # noqa: BLE001 - 连接/表缺失都视为无法确认权威口径
        raise SystemExit(f"读取 public.fixed_data sign='五行' 失败，终止：{exc}") from exc

    if not from_db:
        raise SystemExit("public.fixed_data 缺少 sign='五行' 分组，终止。")

    resolved = {label: normalize_codes(from_db.get(label, ())) for label in ELEMENT_ORDER}
    if resolved != canonical:
        raise SystemExit(
            "public.fixed_data sign='五行' 与 predict.common.ELEMENT_NUMBER_GROUPS 不一致，"
            f"终止。\n  fixed_data = {resolved}\n  常量       = {canonical}"
        )
    covered = sorted(number for codes in resolved.values() for number in codes)
    if covered != [f"{index:02d}" for index in range(1, 50)]:
        raise SystemExit(f"号码五行分组未覆盖 01-49 且不重复，终止：{covered}")
    return resolved


def scan_table(
    conn: Any,
    table: str,
    element_groups: dict[str, tuple[str, ...]],
    *,
    sample_limit: int,
) -> tuple[list[PlannedChange], TableScan]:
    """扫描单表，返回待改行与统计。"""

    scan = TableScan(table=table)
    changes: list[PlannedChange] = []
    for row in list_created_content_rows(conn, table):
        scan.scanned += 1
        after = rewrite_element_group_content(row.content, element_groups)
        if after is None:
            scan.not_element_content += 1
            continue
        if after == row.content:
            scan.already_canonical += 1
            continue
        if not row.locatable:
            scan.unlocatable += 1
            continue
        change = PlannedChange(
            table=table,
            locator=row.locator,
            web_id=row.web_id,
            year=row.year,
            term=row.term,
            before=row.content,
            after=after,
        )
        changes.append(change)
        scan.pending += 1
        key = str(row.web_id)
        scan.web_ids[key] = scan.web_ids.get(key, 0) + 1
        if len(scan.samples) < sample_limit:
            scan.samples.append(change)
    return changes, scan


def redact_target(target: str) -> str:
    """隐藏 DSN 口令，避免写进日志/报告。"""

    return re.sub(r"://([^:/@]+):[^@]*@", r"://\1:***@", str(target or ""))


def write_manifest(path: str, payload: dict[str, Any]) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)


def load_manifest_changes(path: str) -> list[PlannedChange]:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    changes: list[PlannedChange] = []
    for item in payload.get("changes", []):
        locator = tuple(
            (str(column), str(value)) for column, value in item.get("locator", [])
        )
        if not locator and item.get("id"):
            locator = (("id", str(item["id"])),)
        changes.append(
            PlannedChange(
                table=str(item.get("table") or ""),
                locator=locator,
                web_id=item.get("web_id"),
                year=str(item.get("year") or ""),
                term=str(item.get("term") or ""),
                before=str(item.get("before") or ""),
                after=str(item.get("after") or ""),
            )
        )
    return changes


def apply_changes(conn: Any, changes: list[PlannedChange]) -> tuple[int, list[PlannedChange]]:
    """逐行写入，返回 (成功行数, 冲突行列表)。"""

    updated = 0
    conflicts: list[PlannedChange] = []
    for change in changes:
        if not change.locator:
            conflicts.append(change)
            continue
        affected = update_created_content_row(
            conn,
            change.table,
            locator=change.locator,
            expected_content=change.before,
            new_content=change.after,
        )
        if affected == 1:
            updated += 1
        else:
            conflicts.append(change)
    return updated, conflicts


def print_element_groups(element_groups: dict[str, tuple[str, ...]]) -> None:
    print("权威号码五行（public.fixed_data sign='五行'，与 predict.common.ELEMENT_NUMBER_GROUPS 一致）：")
    for label in ELEMENT_ORDER:
        codes = element_groups.get(label, ())
        print(f"  {label}（{len(codes)} 码）: {','.join(codes)}")
    print()


def print_scan(scan: TableScan, *, dry_run: bool) -> None:
    verb = "将修改" if dry_run else "已修改"
    print(f"created.{scan.table}：扫描 {scan.scanned} 行")
    print(
        f"  {verb} {scan.pending} 行；已是权威口径 {scan.already_canonical} 行；"
        f"非五行正文 {scan.not_element_content} 行"
    )
    if scan.web_ids:
        breakdown = ", ".join(f"{key}={value}" for key, value in sorted(scan.web_ids.items(), key=lambda kv: kv[0]))
        print(f"  web_id 分布：{breakdown}")
    if scan.unlocatable:
        print(f"  ！无法定位（id 与 ctid 都为空）：{scan.unlocatable} 行，已跳过")
    if scan.samples:
        print(f"  -- 前后样例（最多 {len(scan.samples)} 条）--")
        for change in scan.samples:
            print(f"  [{change.label}] web_id={change.web_id} {change.year}-{change.term}")
            print(f"    前：{change.before}")
            print(f"    后：{change.after}")
    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="把 mode_payload_53 / 482 正文五行号码清单统一为号码五行口径",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", dest="apply", action="store_false", help="只统计不写库（默认）")
    mode.add_argument("--apply", dest="apply", action="store_true", help="真正写库")
    parser.set_defaults(apply=False)
    parser.add_argument(
        "--db-path",
        default=os.environ.get("DATABASE_URL", ""),
        help="PostgreSQL DSN；缺省读 DATABASE_URL",
    )
    parser.add_argument(
        "--tables",
        default=",".join(DEFAULT_TABLES),
        help=f"逗号分隔的目标表（默认 {','.join(DEFAULT_TABLES)}）",
    )
    parser.add_argument("--manifest", default="", help="导出 id/原正文/新正文 的 JSON 清单（回滚依据）")
    parser.add_argument("--rollback", default="", help="按 manifest 逐行还原正文（需同时给 --apply 才写库）")
    parser.add_argument("--sample-limit", type=int, default=5, help="每表打印多少条前后样例（默认 5）")
    return parser


def parse_tables(raw: str) -> tuple[str, ...]:
    tables = tuple(item.strip() for item in str(raw or "").split(",") if item.strip())
    if not tables:
        raise SystemExit("--tables 不能为空。")
    for table in tables:
        if not MODE_PAYLOAD_TABLE_RE.fullmatch(table):
            raise SystemExit(f"非法表名 {table!r}：只允许 created.mode_payload_<数字>。")
    return tables


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tables = parse_tables(args.tables)
    dry_run = not args.apply
    started_at = datetime.now(timezone.utc).isoformat()

    with connect(args.db_path) as conn:
        print("== 五行正文清单修复（mode_payload_53 / mode_payload_482）==")
        print(f"数据库：{redact_target(args.db_path or conn.target)}")
        print(f"模式：{'DRY-RUN（不写库）' if dry_run else 'APPLY（写库）'}")
        print()

        if args.rollback:
            return run_rollback(conn, args, dry_run=dry_run, started_at=started_at)

        element_groups = resolve_element_groups(conn)
        print_element_groups(element_groups)

        all_changes: list[PlannedChange] = []
        scans: list[TableScan] = []
        for table in tables:
            changes, scan = scan_table(
                conn, table, element_groups, sample_limit=max(0, int(args.sample_limit))
            )
            all_changes.extend(changes)
            scans.append(scan)
            print_scan(scan, dry_run=True)

        total_scanned = sum(scan.scanned for scan in scans)
        total_web_ids = sorted({str(change.web_id) for change in all_changes}, key=lambda item: item)
        print(
            f"== 合计：扫描 {total_scanned} 行 / 涉及 {len(scans)} 张表 / "
            f"{len(total_web_ids)} 个 web_id（{','.join(total_web_ids) if total_web_ids else '无'}）；"
            f"{'将修改' if dry_run else '待写入'} {len(all_changes)} 行"
        )

        conflicts: list[PlannedChange] = []
        if not dry_run and all_changes:
            updated, conflicts = apply_changes(conn, all_changes)
            print(f"== 已更新 {updated} 行；并发冲突/未命中 {len(conflicts)} 行")
            for change in conflicts[:10]:
                print(f"   [冲突] {change.table} {change.label} {change.year}-{change.term}")
        elif not dry_run:
            print("== 没有需要修改的行，未执行任何 UPDATE")

        if args.manifest:
            write_manifest(
                args.manifest,
                {
                    "generated_at": started_at,
                    "database": redact_target(args.db_path or conn.target),
                    "mode": "dry-run" if dry_run else "apply",
                    "element_groups": {label: list(element_groups.get(label, ())) for label in ELEMENT_ORDER},
                    "total_rows": len(all_changes),
                    "tables": {
                        scan.table: {
                            "scanned": scan.scanned,
                            "pending": scan.pending,
                            "already_canonical": scan.already_canonical,
                            "not_element_content": scan.not_element_content,
                        }
                        for scan in scans
                    },
                    "conflicts": [
                        {"table": change.table, "locator": change.label} for change in conflicts
                    ],
                    "changes": [change.as_manifest() for change in all_changes],
                },
            )
            print(f"== 清单已写入 {args.manifest}")

        if dry_run:
            print("== 复核：本次为 DRY-RUN，未对数据库做任何写操作。")
            print("== 若上面的行数符合预期，加 --apply 执行；执行后再跑一次应显示「将修改 0 行」。")
        return 0


def run_rollback(conn: Any, args: argparse.Namespace, *, dry_run: bool, started_at: str) -> int:
    """按 manifest 把正文逐行还原（仍然只写 content 一列）。"""

    changes = load_manifest_changes(args.rollback)
    print(f"回滚清单：{args.rollback}（{len(changes)} 行）")
    print()
    for change in changes[: max(0, int(args.sample_limit))]:
        print(f"  [{change.label}] {change.table} {change.year}-{change.term}")
        print(f"    当前（应为）：{change.after}")
        print(f"    还原为：{change.before}")
    print()

    if dry_run:
        print(f"== 合计：将还原 {len(changes)} 行（DRY-RUN，未写库）")
        return 0

    restored = 0
    conflicts: list[PlannedChange] = []
    for change in changes:
        affected = update_created_content_row(
            conn,
            change.table,
            locator=change.locator,
            expected_content=change.after,
            new_content=change.before,
        )
        if affected == 1:
            restored += 1
        else:
            conflicts.append(change)
    print(f"== 已还原 {restored} 行；冲突/未命中 {len(conflicts)} 行")
    for change in conflicts:
        print(f"   [冲突] {change.table} {change.label} {change.year}-{change.term}")
    if args.manifest:
        write_manifest(
            args.manifest,
            {
                "generated_at": started_at,
                "mode": "rollback",
                "restored": restored,
                "conflicts": [{"table": c.table, "locator": c.label} for c in conflicts],
            },
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
