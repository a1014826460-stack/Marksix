"""报警检测服务。

提供以下报警场景的检测与触发逻辑：

1. 爬虫连续重试失败 — 达到阈值后发送报警
2. 预测数据断层 — 每日预测后检查是否有站点未生成到目标期号
3. 开奖数据滞后 — 检查最新已开奖记录的 next_time 是否已过北京当前时间
4. 精确期号不匹配 — 调度器精确检查失败后触发邮件报警

所有报警均通过 email_service.send_alert_async 异步发送，不阻塞主流程。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from db import connect
from runtime_config import get_config, get_config_from_conn, upsert_system_config

_alert_logger = logging.getLogger("alert.service")

LOTTERY_NAMES: dict[int, str] = {1: "香港彩", 2: "澳门彩", 3: "台湾彩"}


def _cfg(db_path: str | Path, key: str, fallback: Any) -> Any:
    try:
        return get_config(db_path, key, fallback)
    except Exception:
        return fallback


def _cfg_int(db_path: str | Path, key: str, fallback: int) -> int:
    return int(_cfg(db_path, key, fallback))


# ── 爬虫失败计数管理 ─────────────────────────────────────


def _crawler_fail_count_key(lottery_type_id: int) -> str:
    return f"alert._crawler_fail_count_{lottery_type_id}"


def reset_crawler_fail_count(db_path: str | Path, lottery_type_id: int) -> None:
    """爬虫成功后重置失败计数。"""
    try:
        upsert_system_config(
            db_path,
            key=_crawler_fail_count_key(lottery_type_id),
            value=0,
            value_type="int",
            changed_by="alert_service",
            change_reason="爬虫成功，重置失败计数",
        )
    except Exception:
        pass


def increment_crawler_fail_count(db_path: str | Path, lottery_type_id: int) -> int:
    """爬虫失败后递增计数，返回当前连续失败次数。"""
    key = _crawler_fail_count_key(lottery_type_id)
    current = int(_cfg(db_path, key, 0))
    new_count = current + 1
    try:
        upsert_system_config(
            db_path,
            key=key,
            value=new_count,
            value_type="int",
            changed_by="alert_service",
            change_reason=f"爬虫失败，连续失败次数={new_count}",
        )
    except Exception:
        pass
    return new_count


# ── 报警触发函数 ────────────────────────────────────────


def alert_crawler_failure(
    db_path: str | Path,
    lottery_type_id: int,
    error_message: str,
) -> bool:
    """爬虫失败后调用。达到阈值时发送报警邮件。

    :return: True 如果触发了报警
    """
    threshold = _cfg_int(db_path, "alert.crawler_retry_threshold", 3)
    fail_count = increment_crawler_fail_count(db_path, lottery_type_id)
    lt_name = LOTTERY_NAMES.get(lottery_type_id, str(lottery_type_id))

    if fail_count < threshold:
        _alert_logger.info(
            "Crawler failure: lt=%s count=%d/%d (threshold not reached)",
            lt_name, fail_count, threshold,
        )
        return False

    _alert_logger.warning(
        "Crawler ALERT triggered: lt=%s consecutive failures=%d, error=%s",
        lt_name, fail_count, error_message,
    )

    from alerts.email_service import send_alert_async

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    send_alert_async(
        db_path,
        subject=f"[六合彩报警] {lt_name}爬虫连续失败 {fail_count} 次",
        body_html=f"""
        <h2>爬虫采集异常报警</h2>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse">
            <tr><td><b>彩种</b></td><td>{lt_name} (ID={lottery_type_id})</td></tr>
            <tr><td><b>连续失败次数</b></td><td style="color:red"><b>{fail_count}</b></td></tr>
            <tr><td><b>报警阈值</b></td><td>{threshold}</td></tr>
            <tr><td><b>最近错误</b></td><td>{error_message}</td></tr>
            <tr><td><b>触发时间</b></td><td>{now_str}</td></tr>
        </table>
        <p>请检查爬虫数据源或网络连接。</p>
        """,
    )
    return True


def alert_prediction_gap(
    db_path: str | Path,
) -> list[dict[str, Any]]:
    """检查所有启用站点的预测数据是否覆盖到了目标期号。

    目标期号 = 当前已开奖期号 + 1（未来期）。
    如果任何启用站点模块的 created 表缺少目标期数据，触发报警。

    :return: 有断层问题的站点列表
    """
    issues: list[dict[str, Any]] = []
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        with connect(db_path) as conn:
            # 获取所有彩种的最新已开奖期号
            opened = conn.execute(
                """
                SELECT lottery_type_id, year, term
                FROM lottery_draws
                WHERE is_opened = 1 AND numbers IS NOT NULL AND numbers != ''
                ORDER BY lottery_type_id, year DESC, term DESC
                """
            ).fetchall()

            latest_by_type: dict[int, tuple[int, int]] = {}
            for row in opened:
                lt = int(row["lottery_type_id"] or 0)
                if lt not in latest_by_type:
                    latest_by_type[lt] = (int(row["year"] or 0), int(row["term"] or 0))

            # 获取所有启用站点及其模块
            sites = conn.execute(
                """
                SELECT id, name, lottery_type_id, web_id
                FROM managed_sites WHERE enabled = 1
                """
            ).fetchall()

            for site in sites:
                site_id = int(site["id"])
                site_name = str(site["name"] or "")
                lt = int(site["lottery_type_id"] or 3)
                web_id = int(site["web_id"] or 0)

                latest = latest_by_type.get(lt)
                if not latest:
                    continue

                # 计算目标期号（未来一期）
                target_year, target_term = _compute_next_issue(latest[0], latest[1])

                # 取该站点的第一个启用模块对应的 mode_payload 表名
                module = conn.execute(
                    """
                    SELECT mode_id FROM site_prediction_modules
                    WHERE site_id = ? AND status = 1
                    ORDER BY sort_order LIMIT 1
                    """,
                    (site_id,),
                ).fetchone()
                if not module:
                    continue

                mode_id = int(module["mode_id"] or 0)
                if mode_id <= 0:
                    continue

                table_name = f"mode_payload_{mode_id}"
                # 检查 created schema 中是否存在目标期记录
                has_target = conn.execute(
                    f"SELECT 1 FROM created.{table_name} "
                    "WHERE type = ? AND year = ? AND term = ? "
                    "AND content IS NOT NULL AND content != '' LIMIT 1",
                    (str(lt), str(target_year), str(target_term)),
                ).fetchone()

                if not has_target:
                    lt_name = LOTTERY_NAMES.get(lt, str(lt))
                    issue_str = f"{target_year}{target_term:03d}"
                    issues.append({
                        "site_id": site_id,
                        "site_name": site_name,
                        "lottery_type_id": lt,
                        "lottery_name": lt_name,
                        "web_id": web_id,
                        "target_issue": issue_str,
                        "target_year": target_year,
                        "target_term": target_term,
                    })
                    _alert_logger.warning(
                        "Prediction gap: site=%s lt=%s missing target issue=%s",
                        site_name, lt_name, issue_str,
                    )

    except Exception as exc:
        _alert_logger.error("Prediction gap check failed: %s", exc)
        return issues

    if issues:
        from alerts.email_service import send_alert_async

        rows_html = ""
        for item in issues:
            rows_html += f"""
            <tr>
                <td>{item['site_name']}</td>
                <td>{item['lottery_name']}</td>
                <td><span style="color:red"><b>{item['target_issue']}</b></span></td>
            </tr>"""

        send_alert_async(
            db_path,
            subject=f"[六合彩报警] {len(issues)} 个站点预测数据未覆盖到目标期号",
            body_html=f"""
            <h2>预测数据断层报警</h2>
            <p>以下站点的预测数据未生成到目标期号（当前期+1）：</p>
            <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse">
                <tr style="background:#f5f5f5">
                    <th>站点</th><th>彩种</th><th>缺少目标期号</th>
                </tr>
                {rows_html}
            </table>
            <p>触发时间: {now_str}</p>
            <p>请检查 daily_prediction 定时任务是否正常执行。</p>
            """,
        )

    return issues


def alert_draw_staleness(
    db_path: str | Path,
    lottery_type_id: int | None = None,
) -> bool:
    """检查开奖数据是否滞后。

    判定条件：最新已开奖记录的 next_time 已过北京时间现在，
    但还没有更晚一期的已开奖数据入库。

    :return: True 如果存在滞后并发送了报警
    """
    triggered = False
    now_utc = datetime.now(timezone.utc)
    now_beijing_str = (now_utc + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S 北京时间")

    lt_ids = [lottery_type_id] if lottery_type_id else [1, 2, 3]

    try:
        with connect(db_path) as conn:
            for lt in lt_ids:
                row = conn.execute(
                    """
                    SELECT year, term, next_time
                    FROM lottery_draws
                    WHERE lottery_type_id = ? AND is_opened = 1
                    ORDER BY year DESC, term DESC LIMIT 1
                    """,
                    (lt,),
                ).fetchone()

                if not row:
                    continue

                next_time_str = str(row["next_time"] or "").strip()
                if not next_time_str:
                    continue

                try:
                    next_ms = int(next_time_str)
                    if next_ms <= 0:
                        continue
                    next_dt = datetime.fromtimestamp(next_ms / 1000, tz=timezone.utc)
                except (ValueError, OSError):
                    continue

                if next_dt < now_utc:
                    lt_name = LOTTERY_NAMES.get(lt, str(lt))
                    year = int(row["year"] or 0)
                    term = int(row["term"] or 0)
                    _alert_logger.warning(
                        "Draw staleness: lt=%s latest=%s/%s next_time=%s < now=%s",
                        lt_name, year, term,
                        next_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    )
                    triggered = True

        if triggered:
            from alerts.email_service import send_alert_async
            send_alert_async(
                db_path,
                subject="[六合彩报警] 开奖数据可能滞后",
                body_html=f"""
                <h2>开奖数据滞后报警</h2>
                <p>最新已开奖记录的 next_time 已过当前时间（UTC），但未检测到新一期开奖数据入库。</p>
                <p>可能原因：</p>
                <ul>
                    <li>爬虫数据源异常，未能拉取到最新开奖数据</li>
                    <li>开奖改期</li>
                    <li>调度器未正常运行</li>
                </ul>
                <p>触发时间: {now_beijing_str}</p>
                <p>请检查 lottery_draws 表最新记录和调度器日志。</p>
                """,
            )
    except Exception as exc:
        _alert_logger.error("Draw staleness check failed: %s", exc)

    return triggered


def alert_precise_draw_mismatch(
    db_path: str | Path,
    lottery_type_id: int,
    expected_period: str,
    actual_period: str,
    attempt_count: int,
) -> None:
    """精确期号检查全部失败后发送邮件报警（补充已有 error_logs 写入）。"""
    lt_name = LOTTERY_NAMES.get(lottery_type_id, str(lottery_type_id))
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    from alerts.email_service import send_alert_async
    send_alert_async(
        db_path,
        subject=f"[六合彩报警] {lt_name}开奖期号不匹配",
        body_html=f"""
        <h2>开奖期号不匹配报警</h2>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse">
            <tr><td><b>彩种</b></td><td>{lt_name} (ID={lottery_type_id})</td></tr>
            <tr><td><b>预期期号</b></td><td>{expected_period}</td></tr>
            <tr><td><b>实际返回</b></td><td style="color:red"><b>{actual_period}</b></td></tr>
            <tr><td><b>重试次数</b></td><td>{attempt_count}</td></tr>
            <tr><td><b>触发时间</b></td><td>{now_str}</td></tr>
        </table>
        <p>精确开奖检查全部重试失败，数据源返回的期号与预期不一致。</p>
        """,
    )


# ── 辅助函数 ──────────────────────────────────────────


def _compute_next_issue(year: int, term: int) -> tuple[int, int]:
    max_terms = 365
    new_term = term + 1
    new_year = year
    if new_term > max_terms:
        new_term = 1
        new_year += 1
    return new_year, new_term
