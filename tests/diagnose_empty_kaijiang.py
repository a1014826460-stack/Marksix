#!/usr/bin/env python3
"""诊断脚本：精确定位 GET /api/kaijiang/yyptj?web=4&type=2 返回空数据的原因。

逐层追踪从 Next.js 路由 → Python 后端 → PostgreSQL 的完整调用链，
在每个环节打印关键输入/输出，最终输出Diagnosis Summary。

用法：
    python tests/diagnose_empty_kaijiang.py
    python tests/diagnose_empty_kaijiang.py --modes-id 244 --type 2 --web 4
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from textwrap import dedent, indent
from typing import Any
from urllib.parse import urlencode

import requests

# ── 配置 ────────────────────────────────────────────────────
BACKEND_BASE = os.environ.get("LOTTERY_BACKEND_BASE_URL", "http://127.0.0.1:8000/api")
FRONTEND_BASE = os.environ.get("FRONTEND_BASE_URL", "http://127.0.0.1:3000")
PG_DSN = os.environ.get(
    "DIAG_PG_DSN",
    "postgresql://postgres:2225427@localhost:5432/liuhecai",
)


# ── 工具函数 ────────────────────────────────────────────────
SEPARATOR = "─" * 60


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def step(label: str, detail: str = "") -> None:
    print(f"\n{SEPARATOR}")
    print(f"[{label}]")
    if detail:
        print(f"  {detail}")


def step_result(label: str, value: Any) -> None:
    if isinstance(value, (dict, list)):
        formatted = json.dumps(value, ensure_ascii=False, indent=4)
        print(f"[{label}]")
        print(indent(formatted, "  "))
    else:
        print(f"[{label}] {value}")


def code_block(text: str) -> None:
    print(indent(text, "  "))


def fail(msg: str) -> None:
    print(f"\n  [FAIL] {msg}")


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


# ── 数据库连接 ──────────────────────────────────────────────
def get_pg_conn():
    """尝试连接 PostgreSQL，失败返回 None（脚本仍可运行，仅跳过 DB 步骤）。"""
    try:
        import psycopg2

        conn = psycopg2.connect(PG_DSN)
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"  [WARN] 无法连接 PostgreSQL: {e}")
        print(f"    将继续运行非 DB 诊断步骤")
        return None


# ── 诊断逻辑 ────────────────────────────────────────────────
def step1_frontend_proxy(args: argparse.Namespace) -> dict[str, Any]:
    """环节1: 模拟前端 Next.js 路由层 → Python 后端的调用。"""
    section("Step 1 - Frontend /api/kaijiang proxy layer")

    endpoint = args.endpoint
    frontend_url = f"{FRONTEND_BASE}/api/kaijiang/{endpoint}"

    params = {"web": str(args.web), "type": str(args.type)}
    if args.num:
        params["num"] = args.num

    step(
        "1.1 前端 URL",
        f"{frontend_url}?{urlencode(params)}",
    )
    step(
        "1.2 Equivalent Next.js Route Logic",
        dedent(f"""\
        case "{endpoint}":
            fetchLegacyRows(url, modesId={args.modes_id}, limit={args.limit})
            → backendFetchJson("/legacy/module-rows", {{
                query: {{ modes_id: {args.modes_id}, web: {args.web}, type: {args.type}, limit: {args.limit} }}
            }})
        """),
    )

    try:
        resp = requests.get(frontend_url, params=params, timeout=15)
    except requests.ConnectionError:
        fail(f"无法连接前端 {FRONTEND_BASE}，前端 dev server 是否已启动？")
        return {}
    except Exception as e:
        fail(f"请求异常: {e}")
        return {}

    step_result("1.3 HTTP 状态码", resp.status_code)
    step_result("1.4 Content-Type", resp.headers.get("content-type", "(无)"))

    try:
        body = resp.json()
    except ValueError:
        fail(f"响应不是 JSON: {resp.text[:500]}")
        return {}

    data_field = body.get("data")
    if isinstance(data_field, list):
        step_result("1.5 Frontend Returns Rows", f"data 数组长度 = {len(data_field)}")
        if len(data_field) == 0:
            step("1.6 关键发现", "前端代理层返回 data: [] — 上游后端没有返回任何行。进入环节2。")
        else:
            step_result("1.5 First Row Sample", data_field[0] if data_field else "(空)")
    elif isinstance(data_field, dict):
        step_result("1.5 data 格式", f"对象 (非数组): {list(data_field.keys())}")
    else:
        step_result("1.5 data 内容", str(data_field)[:300])

    return body


def step2_backend_direct(args: argparse.Namespace) -> dict[str, Any]:
    """环节2: 直接请求 Python 后端 /api/legacy/module-rows。"""
    section("Step2 - Backend Direct Call")

    backend_url = f"{BACKEND_BASE}/legacy/module-rows"
    params = {
        "modes_id": args.modes_id,
        "type": args.type,
        "web": args.web,
        "limit": args.limit,
    }

    step("2.1 请求 URL", f"{backend_url}?{urlencode(params)}")

    try:
        resp = requests.get(backend_url, params=params, timeout=15)
    except requests.ConnectionError:
        fail(f"无法连接后端 {BACKEND_BASE}，Python 后端是否已启动？")
        return {}
    except Exception as e:
        fail(f"请求异常: {e}")
        return {}

    step_result("2.2 HTTP 状态码", resp.status_code)

    try:
        body = resp.json()
    except ValueError:
        fail(f"响应不是 JSON: {resp.text[:500]}")
        return {}

    step_result("2.3 modes_id", body.get("modes_id"))
    step_result("2.4 表名", body.get("table_name"))
    step_result("2.5 record_count", body.get("record_count"))
    step_result("2.6 rows 行数", f"{len(body.get('rows', []))} 行")

    if body.get("rows"):
        step_result("2.7 First Row Sample", body["rows"][0])
    else:
        step("2.7 关键发现", "后端也未返回任何行。进入环节3检查数据库。")

    return body


def step3a_primary_web_query(args: argparse.Namespace) -> int:
    """环节3a: 检查主 web 值在 created schema 下的数据。"""
    section("Step3a - DB Query (created schema, primary web)")

    conn = get_pg_conn()
    if conn is None:
        return -1

    table_name = f"mode_payload_{args.modes_id}"

    with conn.cursor() as cur:
        # 3a.1 检查 created schema 下表是否存在
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'created' AND table_name = %s
            )
            """,
            (table_name,),
        )
        created_exists = cur.fetchone()[0]
        step_result("3a.1 created.mode_payload_{xx} 是否存在", created_exists)

        if not created_exists:
            ok("created schema 下无此表，跳过 created 查询。")
            conn.close()
            return -1

        # 3a.2 按 type + web 查询 created schema
        sql_created = f"""
            SELECT year, term, type, web_id, res_code, res_sx, content
            FROM created.{table_name}
            WHERE CAST(COALESCE(NULLIF(TRIM(CAST(type AS TEXT)), ''), '0') AS INTEGER) = %s
              AND CAST(COALESCE(NULLIF(TRIM(CAST(web_id AS TEXT)), ''), '0') AS INTEGER) = %s
            ORDER BY
                CAST(COALESCE(NULLIF(TRIM(CAST(year AS TEXT)), ''), '0') AS INTEGER) DESC,
                CAST(COALESCE(NULLIF(TRIM(CAST(term AS TEXT)), ''), '0') AS INTEGER) DESC
            LIMIT 3
        """
        step("3a.2 SQL (created schema)", sql_created)
        step("3a.2 参数", f"type={args.type}, web={args.web}")

        cur.execute(sql_created, (args.type, args.web))
        rows_created = cur.fetchall()
        step_result("3a.2 结果行数", len(rows_created))

        if rows_created:
            # psycopg2 rows need manual dict conversion
            col_names = [desc[0] for desc in (cur.description or [])]
            first_row = dict(zip(col_names, rows_created[0])) if col_names else {}
            step_result("3a.2 首行", first_row)
            conn.close()
            return len(rows_created)

        # 3a.3 如果不指定 type 过滤，有多少行？
        sql_all_types = f"SELECT type, COUNT(*) as cnt FROM created.{table_name} GROUP BY type ORDER BY type"
        step("3a.3 检查 created 中所有 type 分布", sql_all_types)
        cur.execute(sql_all_types)
        type_dist = cur.fetchall()
        step_result("3a.3 type 分布", {r[0]: r[1] for r in type_dist} if type_dist else "(空)")

        conn.close()
        return 0


def step3b_fallback_web_query(args: argparse.Namespace) -> int:
    """环节3b: 检查回退 web=2 在 public schema 下的数据。"""
    section("Step3b - DB Query (public schema, fallback web)")

    conn = get_pg_conn()
    if conn is None:
        return -1

    table_name = f"mode_payload_{args.modes_id}"

    # 查找回退 web
    LEGACY_WEB_FALLBACK_BY_TYPE = {
        2: {1: 2, 2: 2, 3: 2},
        3: {1: 2, 2: 2, 3: 2},
        44: {1: 2, 2: 2, 3: 2},
        48: {1: 2, 2: 2, 3: 2},
        57: {1: 2, 2: 2, 3: 2},
        108: {1: 2, 2: 2, 3: 2},
        244: {1: 2, 2: 2, 3: 2},
        331: {1: 2, 2: 2, 3: 2},
    }
    fallback_map = LEGACY_WEB_FALLBACK_BY_TYPE.get(args.modes_id, {})
    fallback_web = fallback_map.get(args.type)
    step_result("3b.1 回退映射查询", f"LEGACY_WEB_FALLBACK_BY_TYPE[{args.modes_id}]?.[{args.type}] = {fallback_web}")

    with conn.cursor() as cur:
        # 如果有回退值，查询
        if fallback_web is not None:
            sql_fallback = f"""
                SELECT year, term, type, web_id, res_code, res_sx, content
                FROM {table_name}
                WHERE CAST(COALESCE(NULLIF(TRIM(CAST(type AS TEXT)), ''), '0') AS INTEGER) = %s
                  AND CAST(COALESCE(NULLIF(TRIM(CAST(web_id AS TEXT)), ''), '0') AS INTEGER) = %s
                ORDER BY
                    CAST(COALESCE(NULLIF(TRIM(CAST(year AS TEXT)), ''), '0') AS INTEGER) DESC,
                    CAST(COALESCE(NULLIF(TRIM(CAST(term AS TEXT)), ''), '0') AS INTEGER) DESC
                LIMIT 3
            """
            step("3b.2 SQL (public schema, 回退 web)", sql_fallback)
            step("3b.2 参数", f"type={args.type}, web={fallback_web}")

            cur.execute(sql_fallback, (args.type, fallback_web))
            rows_fallback = cur.fetchall()
            step_result("3b.2 结果行数", len(rows_fallback))

            if rows_fallback:
                col_names = [desc[0] for desc in (cur.description or [])]
                first_row = dict(zip(col_names, rows_fallback[0])) if col_names else {}
                step_result("3b.2 首行", first_row)
                conn.close()
                return len(rows_fallback)
        else:
            step("3b.2", "无回退 web 映射 — 这是前端路由代码中的缺失！")
            fail("LEGACY_WEB_FALLBACK_BY_TYPE 没有为当前 modes_id/type 配置回退 web。")

        # 3b.3 不指定 web，只看 type 过滤有数据吗
        sql_type_only = f"SELECT web_id, COUNT(*) as cnt FROM {table_name} WHERE CAST(COALESCE(NULLIF(TRIM(CAST(type AS TEXT)), ''), '0') AS INTEGER) = %s GROUP BY web_id ORDER BY web_id"
        step("3b.3 检查 public 中该 type 的 web 分布", sql_type_only)
        step("3b.3 参数", f"type={args.type}")
        cur.execute(sql_type_only, (args.type,))
        web_dist = cur.fetchall()
        step_result("3b.3 web 分布", {r[0]: r[1] for r in web_dist} if web_dist else "(空)")

        # 3b.4 不指定 type 和 web，看全表有多少数据
        sql_total = f"SELECT type, web_id, COUNT(*) as cnt FROM {table_name} GROUP BY type, web_id ORDER BY type, web_id"
        step("3b.4 全表 type×web 分布", sql_total)
        cur.execute(sql_total)
        total_dist = cur.fetchall()
        step_result("3b.4 全表分布", {f"type={r[0]},web={r[1]}": r[2] for r in total_dist} if total_dist else "(空)")

        conn.close()
        return 0


def step4_fallback_logic_check(args: argparse.Namespace) -> None:
    """环节4: 验证前端回退逻辑是否按预期工作。"""
    section("Step4 - Fallback Logic Check")

    step("4.1 当前 LEGACY_WEB_FALLBACK_BY_TYPE 映射", "")
    fallback_map = {244: {1: 2, 2: 2, 3: 2}}  # 当前已修复版本
    step_result(f"  [{args.modes_id}]", fallback_map.get(args.modes_id, {}))

    # 模拟 fetchLegacyRows 逻辑
    requested_web = args.web
    type_number = args.type
    modes_id = args.modes_id

    print()
    code_block(dedent(f"""\
    // 伪代码: fetchLegacyRows 的执行路径
    const requestedWeb = {requested_web};           // web={requested_web}
    const typeNumber = {type_number};               // type={type_number}
    const modesId = {modes_id};

    // 1) 主请求
    const primary = await fetchWithWeb({requested_web});
    // → GET /api/legacy/module-rows?modes_id={modes_id}&web={requested_web}&type={type_number}

    // 2) 回退检查
    const fallbackWeb = LEGACY_WEB_FALLBACK_BY_TYPE[{modes_id}]?.[{type_number}];
    // → {fallback_map.get(modes_id, {}).get(type_number)}

    if (primary.rows.length > 0 || !fallbackWeb || fallbackWeb === requestedWeb) {{
        return primary;  // ← {"" if requested_web == (fallback_map.get(modes_id, {}).get(type_number)) else "不" if fallback_map.get(modes_id, {}).get(type_number) is None else ""}命中此分支
    }}

    // 3) 回退请求
    const fallback = await fetchWithWeb(fallbackWeb);
    // → GET /api/legacy/module-rows?modes_id={modes_id}&web={fallback_map.get(modes_id, {}).get(type_number)}&type={type_number}
    return fallback.rows.length > 0 ? fallback : primary;
    """))

    # 判断结论
    has_fallback = fallback_map.get(modes_id, {}).get(type_number)
    if has_fallback:
        print(f"  结论: 存在回退映射 {modes_id}→{{{type_number}: {has_fallback}}}，回退逻辑会触发。")
        print(f"        若仍为空，说明数据库在 type={type_number}, web={has_fallback} 下也无数据。")
    else:
        print(f"  结论: 不存在回退映射 {modes_id}->{{type_number: ?}}，回退逻辑不会触发，直接返回空。")


def step5_check_created_generation(args: argparse.Namespace) -> None:
    """环节5: 检查 created schema 的生成/同步状态"""
    section("Step5 - Created Schema Generation Status")

    conn = get_pg_conn()
    if conn is None:
        return

    table_name = f"mode_payload_{args.modes_id}"

    with conn.cursor() as cur:
        # 检查 site_prediction_modules 中是否配置了此模块
        cur.execute(
            """
            SELECT spm.id, spm.mechanism_key, spm.mode_id, spm.status, ms.name AS site_name, ms.lottery_type_id
            FROM site_prediction_modules spm
            JOIN managed_sites ms ON ms.id = spm.site_id
            WHERE spm.mode_id = %s AND ms.enabled = 1
            """,
            (args.modes_id,),
        )
        modules = cur.fetchall()
        if modules:
            step_result("5.1 site_prediction_modules 配置", "")
            for m in modules:
                print(f"  id={m[0]} key={m[1]} mode_id={m[2]} status={'启用' if m[3] else '禁用'} site={m[4]} type={m[5]}")
        else:
            step_result("5.1 site_prediction_modules 配置", f"未找到 mode_id={args.modes_id} 的站点配置")

        # 检查 created schema 的整体状态
        cur.execute(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name = %s AND table_schema IN ('created', 'public')
            """,
            (table_name,),
        )
        schemas = cur.fetchall()
        step_result("5.2 表分布", {r[0]: r[1] for r in schemas})

        # 如果 created 存在，检查最新数据的生成时间
        if any(s[0] == "created" for s in schemas):
            cur.execute(f"SELECT MAX(created_at) FROM created.{table_name}")
            latest = cur.fetchone()[0]
            step_result("5.3 created 最新生成时间", latest)

        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="诊断 /api/kaijiang/* 空数据原因")
    parser.add_argument("--endpoint", default="yyptj", help="kaijiang endpoint 名称 (默认: yyptj)")
    parser.add_argument("--modes-id", type=int, default=244, help="modes_id (默认: 244)")
    parser.add_argument("--type", type=int, default=2, help="彩种 type (默认: 2=澳门)")
    parser.add_argument("--web", type=int, default=4, help="web 来源 (默认: 4)")
    parser.add_argument("--num", default="", help="可选的 num 参数")
    parser.add_argument("--limit", type=int, default=10, help="limit 行数 (默认: 10)")
    args = parser.parse_args()

    print("+" + "=" * 58 + "+")
    print(f"|  Diagnose: GET /api/kaijiang/{args.endpoint}?web={args.web}&type={args.type}")
    print(f"|  modes_id={args.modes_id} | type={args.type}({ {1:'HK',2:'Macau',3:'TW'}.get(args.type,'?')}) | web={args.web} | limit={args.limit}")
    print("+" + "=" * 58 + "+")

    # ── 逐环节执行 ──
    frontend_body = step1_frontend_proxy(args)
    step2_backend_direct(args)
    created_rows = step3a_primary_web_query(args)
    fallback_rows = step3b_fallback_web_query(args)
    step4_fallback_logic_check(args)
    step5_check_created_generation(args)

    # ── 总结论 ──
    section("Diagnosis Summary")
    print()

    if created_rows is None or created_rows < 0:
        print("  [WARN] 无法连接数据库，仅完成了 API 层面的诊断。")
        print("    请检查 PostgreSQL 连接配置: PG_DSN 环境变量")
    elif created_rows == 0 and fallback_rows == 0:
        print(f"  根因: **数据库缺数据**")
        print(f"  ----------------------------------------------------------")
        print(f"  mode_payload_{args.modes_id} 表中 type={args.type} 的数据不存在。")
        print(f"  这既不是后端过滤逻辑的 Bug，也不是前端回退映射的问题。")
        print()
        print(f"  修复方向:")
        print(f"    1. 检查上游数据采集是否覆盖了 type={args.type} 的彩种")
        print(f"    2. 检查 site_prediction_modules 是否为此彩种启用了该模块")
        print(f"    3. 若确实需要此模块的数据，需重新执行采集或手动补充")
    elif created_rows > 0:
        print(f"  [OK] data 不为空: created schema 有 {created_rows} 行")
        print(f"    数据已存在，问题可能是前端渲染或 JSON 序列化层面的。")
    elif fallback_rows is not None and fallback_rows > 0:
        print(f"  [OK] data 不为空: public schema (回退 web) 有 {fallback_rows} 行")
        print(f"    数据通过回退映射返回。主 web 无数据但回退成功。")
    else:
        print(f"  诊断结果不明确，请查看上方各环节输出。")

    print()


if __name__ == "__main__":
    main()
