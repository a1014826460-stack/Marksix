"""报警检测服务。

提供以下报警场景的检测与触发逻辑：

1. 爬虫连续重试失败 — 达到阈值后发送报警
2. 预测数据断层 — 每日预测后检查是否有站点未生成到目标期号
3. 开奖数据滞后 — 检查最新已开奖记录的 next_time 是否已过北京当前时间
4. 精确期号不匹配 — 调度器精确检查失败后触发邮件报警

所有报警均通过 email_service.send_alert_async 异步发送，不阻塞主流程。
"""

from __future__ import annotations

from html import escape
import logging
import time as _time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from db import connect
from runtime_config import get_config, get_config_from_conn, upsert_system_config

_alert_logger = logging.getLogger("alert.service")

# 模块级报警冷却期缓存，防止同一报警在短时间内重复发送
# key: 报警标识符 → value: 上次发送时间戳 (time.time())
_alert_last_sent: dict[str, float] = {}
_DEFAULT_COOLDOWN_SECONDS = 3600  # 默认冷却 1 小时
_DRAW_STALENESS_STATE_KEY = "alert._draw_staleness_state"


def _is_alert_suppressed(alert_key: str, db_path, default_cooldown: int = _DEFAULT_COOLDOWN_SECONDS) -> bool:
    """检查报警是否应被冷却期抑制。"""
    try:
        cooldown = int(_cfg(db_path, "alert.cooldown_seconds", default_cooldown))
    except Exception:
        cooldown = default_cooldown
    if cooldown <= 0:
        return False
    now = _time.time()
    last = _alert_last_sent.get(alert_key)
    if last is not None and (now - last) < cooldown:
        return True
    _alert_last_sent[alert_key] = now
    return False

LOTTERY_NAMES: dict[int, str] = {1: "香港彩", 2: "澳门彩", 3: "台湾彩"}

_PAYLOAD_VALUE_COLUMNS = (
    "content", "res_code", "res_sx", "res_color", "image_url",
    "answer", "tips", "jiexi", "jia", "ye",
)


def _payload_value_columns(
    conn: Any,
    table_name: str,
    *,
    schema: str | None = None,
) -> tuple[str, ...]:
    """Return payload columns actually present in the queried schema table."""
    try:
        columns = set(conn.table_columns(table_name, schema=schema))
    except Exception:
        columns = set()
    return tuple(column for column in _PAYLOAD_VALUE_COLUMNS if column in columns)


def _cfg(db_path: str | Path, key: str, fallback: Any) -> Any:
    try:
        return get_config(db_path, key, fallback)
    except Exception:
        return fallback


def _cfg_int(db_path: str | Path, key: str, fallback: int) -> int:
    return int(_cfg(db_path, key, fallback))


def _draw_staleness_repair_hint(lottery_type_id: int) -> str:
    if lottery_type_id == 1:
        return (
            "香港彩源站先给部分号码再补全，通常再等 1~3 分钟即可。"
            "需要立即重试：POST /api/admin/crawler/run-hk"
        )
    if lottery_type_id == 2:
        return (
            "澳门彩源站常在计划时间后 2~6 分钟发布。"
            "需要立即重试：POST /api/admin/crawler/run-macau"
        )
    if lottery_type_id == 3:
        return (
            "台湾彩由持久化任务 taiwan_precise_open 在 22:32（北京）自动开盘；"
            "先确认 scheduler-worker 存活并查看 scheduler_tasks 中该任务的 status，"
            "再在后台开奖记录页（POST /api/admin/draws）补录真实号码"
        )
    return "检查对应彩种的采集/录入入口"


def _beijing_text_from_stored_timestamp(value: Any) -> str:
    """把库里的时间戳文本（多为 UTC）转成北京时间 HH:MM:SS 显示。"""
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = text.replace("Z", "+00:00")
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                parsed = datetime.strptime(normalized[:19], fmt)
                break
            except ValueError:
                continue
    if parsed is None:
        return text[:19]
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (parsed.astimezone(timezone.utc) + timedelta(hours=8)).strftime("%m-%d %H:%M:%S")


def _format_lag(lag_seconds: int) -> str:
    """滞后时长统一按“X分Y秒”展示，保留秒级敏感度。"""
    seconds = max(0, int(lag_seconds))
    return f"{seconds // 60}分{seconds % 60:02d}秒" if seconds >= 60 else f"{seconds}秒"


def _runtime_env_label(db_path: str | Path) -> str:
    import os

    raw = str(os.environ.get("LIUHECAI_RUNTIME_ENV") or "").strip()
    if raw:
        return raw
    try:
        return str(_cfg(db_path, "runtime.environment", "") or "").strip() or "unknown"
    except Exception:
        return "unknown"


def _staleness_grade(db_path: str | Path, grace_seconds: int, lag_seconds: int) -> tuple[str, str]:
    """按与分级告警一致的阈值给出 (级别, 中文标签)。"""

    def _threshold(key: str, default: int) -> int:
        try:
            return max(0, int(_cfg(db_path, key, default)))
        except (TypeError, ValueError):
            return default

    yellow = max(_threshold("alert.draw_yellow_timeout_seconds", 180), grace_seconds + 30)
    orange = max(_threshold("alert.draw_orange_timeout_seconds", 300), grace_seconds + 120)
    red = max(_threshold("alert.draw_red_timeout_seconds", 600), grace_seconds + 300)
    if lag_seconds >= red:
        return "red", "严重"
    if lag_seconds >= orange:
        return "orange", "警告"
    if lag_seconds >= yellow:
        return "yellow", "提示"
    return "info", "观察"


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    """安全读取一行记录里的字段，兼容 sqlite3.Row / psycopg row / dict。"""
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    return default if value is None else value


def _recent_source_fetch_summary(conn: Any, lottery_type_id: int, limit: int = 3) -> str:
    """最近几次源站抓取的结论，直接来自 draw_audit_log。"""
    try:
        rows = conn.execute(
            "SELECT created_at, status, detail FROM draw_audit_log "
            "WHERE lottery_type_id = ? AND event = 'source_fetch' "
            "ORDER BY id DESC LIMIT ?",
            (int(lottery_type_id), int(limit)),
        ).fetchall()
    except Exception:
        return ""

    lines: list[str] = []
    try:
        for row in rows:
            detail = str(_row_value(row, "detail", "") or "")
            source = ""
            outcome = ""
            http_status = ""
            for token in detail.split():
                if token.startswith("source="):
                    source = token.split("=", 1)[1]
                elif token.startswith("outcome="):
                    outcome = token.split("=", 1)[1]
                elif token.startswith("http_status="):
                    http_status = token.split("=", 1)[1]
            stamp = _beijing_text_from_stored_timestamp(_row_value(row, "created_at", ""))
            pieces = [stamp, source or "-", outcome or "-"]
            if http_status:
                pieces.append(f"HTTP {http_status}")
            pieces.append(f"[{_row_value(row, 'status', '')}]")
            lines.append(" ".join(piece for piece in pieces if piece))
    except Exception:
        return "；".join(lines)
    return "；".join(lines)


def _draw_staleness_state_for_item(item: dict[str, Any]) -> dict[str, str]:
    return {
        "issue": str(item.get("issue") or ""),
        "next_time_utc": str(item.get("next_time_utc") or ""),
        "next_time_ms": str(item.get("next_time_ms") or ""),
    }


def _load_draw_staleness_state(conn: Any) -> dict[str, dict[str, str]]:
    raw = get_config_from_conn(conn, _DRAW_STALENESS_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}

    state: dict[str, dict[str, str]] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        lt_key = str(key).strip()
        if not lt_key:
            continue
        state[lt_key] = {
            "issue": str(value.get("issue") or ""),
            "next_time_utc": str(value.get("next_time_utc") or ""),
            "next_time_ms": str(value.get("next_time_ms") or ""),
        }
    return state


def _save_draw_staleness_state(db_path: str | Path, state: dict[str, dict[str, str]]) -> None:
    try:
        upsert_system_config(
            db_path,
            key=_DRAW_STALENESS_STATE_KEY,
            value=state,
            value_type="json",
            changed_by="alert_service",
            change_reason="更新开奖滞后报警状态",
        )
    except Exception as exc:
        _alert_logger.warning("Failed to persist draw staleness state: %s", exc)


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

    # 仅在首次达到阈值时发送报警，后续连续失败不再重复发送
    if fail_count != threshold:
        _alert_logger.info(
            "Crawler ALERT suppressed: lt=%s consecutive failures=%d (already alerted at threshold=%d)",
            lt_name, fail_count, threshold,
        )
        return False

    alert_key = f"crawler_failure_{lottery_type_id}"
    if _is_alert_suppressed(alert_key, db_path):
        _alert_logger.info(
            "Crawler ALERT cooldown suppressed: lt=%s consecutive failures=%d",
            lt_name, fail_count,
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
                if not conn.table_exists(table_name, schema="created"):
                    continue
                value_columns = _payload_value_columns(conn, table_name, schema="created")
                if not value_columns:
                    continue
                value_predicate = " OR ".join(
                    f"{column} IS NOT NULL AND {column} != ''"
                    for column in value_columns
                )
                # 检查 created schema 中是否存在目标期记录
                has_target = conn.execute(
                    f"SELECT 1 FROM created.{table_name} "
                    "WHERE type = ? AND year = ? AND term = ? "
                    f"AND ({value_predicate}) LIMIT 1",
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
        if _is_alert_suppressed("prediction_gap", db_path):
            _alert_logger.info("Prediction gap alert suppressed by cooldown")
            return issues

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
    *,
    grace_seconds: int = 0,
    grace_by_lottery: Mapping[int, int] | None = None,
) -> bool:
    """检查开奖数据是否滞后。

    判定条件：最新已开奖记录的 next_time 已过北京时间现在，
    但还没有更晚一期的已开奖数据入库。

    上游源站通常在计划开奖时间之后 2~6 分钟才发布结果，因此调用方应传入基于
    自身历史入库时延的宽限（``grace_seconds`` 或按彩种的 ``grace_by_lottery``），
    否则每一期都会触发一次“开奖数据滞后”误报。

    :return: True 如果当前仍存在滞后问题（即使同一问题已被去重抑制）
    """
    now_utc = datetime.now(timezone.utc)
    now_beijing_str = (now_utc + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S 北京时间")

    def _grace_for(lottery_type: int) -> int:
        if grace_by_lottery:
            try:
                return max(0, int(grace_by_lottery.get(int(lottery_type), grace_seconds)))
            except (TypeError, ValueError):
                return max(0, int(grace_seconds or 0))
        return max(0, int(grace_seconds or 0))

    lt_ids = [lottery_type_id] if lottery_type_id else [1, 2, 3]
    stale_items: list[dict[str, Any]] = []
    previous_state: dict[str, dict[str, str]] = {}
    current_state: dict[str, dict[str, str]] = {}
    checked_lt_keys = {str(int(lt)) for lt in lt_ids}

    try:
        with connect(db_path) as conn:
            previous_state = _load_draw_staleness_state(conn)
            for lt in lt_ids:
                row = conn.execute(
                    """
                    SELECT year, term, next_time, draw_time
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

                grace_seconds = _grace_for(lt)
                if next_dt < now_utc and (now_utc - next_dt).total_seconds() >= grace_seconds:
                    lt_name = LOTTERY_NAMES.get(lt, str(lt))
                    year = int(row["year"] or 0)
                    term = int(row["term"] or 0)
                    lag_seconds = max(0, int((now_utc - next_dt).total_seconds()))
                    issue = f"{year}{term:03d}"
                    expected_year, expected_term = _compute_next_issue(year, term)
                    expected_issue = f"{expected_year}{expected_term:03d}"
                    level, level_label = _staleness_grade(db_path, grace_seconds, lag_seconds)
                    _alert_logger.warning(
                        "Draw staleness: lt=%s latest=%s/%s next_time=%s < now=%s lag=%ss grace=%ss level=%s",
                        lt_name, year, term,
                        next_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        lag_seconds, grace_seconds, level,
                    )
                    stale_items.append({
                        "lottery_type_id": lt,
                        "lottery_name": lt_name,
                        "issue": issue,
                        "expected_issue": expected_issue,
                        "draw_time_beijing": str(_row_value(row, "draw_time", "") or ""),
                        "next_time_ms": str(next_ms),
                        "next_time_beijing": (next_dt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S"),
                        "next_time_utc": next_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "lag_seconds": lag_seconds,
                        "lag_text": _format_lag(lag_seconds),
                        "grace_seconds": grace_seconds,
                        "level": level,
                        "level_label": level_label,
                        # 兼容既有字段
                        "lag_minutes": max(1, (lag_seconds + 59) // 60),
                        "repair_hint": _draw_staleness_repair_hint(lt),
                        "source_fetch": _recent_source_fetch_summary(conn, lt),
                    })
                    current_state[str(lt)] = _draw_staleness_state_for_item(stale_items[-1])
    except Exception as exc:
        _alert_logger.error("Draw staleness check failed: %s", exc)
        return False

    recovered_state = {
        key: value
        for key, value in previous_state.items()
        if key in checked_lt_keys and key not in current_state
    }

    next_state = {
        key: value
        for key, value in previous_state.items()
        if key not in checked_lt_keys
    }
    next_state.update(current_state)
    if next_state != previous_state:
        _save_draw_staleness_state(db_path, next_state)

    if recovered_state:
        _send_draw_staleness_recovery(
            db_path,
            recovered_state,
            now_utc=now_utc,
        )

    if not stale_items:
        return False

    changed_items = [
        item
        for item in stale_items
        if previous_state.get(str(item["lottery_type_id"])) != _draw_staleness_state_for_item(item)
    ]
    if not changed_items:
        _alert_logger.info(
            "Draw staleness alert suppressed: same active issue still pending for lt=%s",
            ", ".join(sorted(current_state.keys())),
        )
        return True

    from alerts.email_service import send_alert_async

    env_label = _runtime_env_label(db_path)
    try:
        admin_base = str(_cfg(db_path, "alert.admin_base_url", "") or "").strip().rstrip("/")
    except Exception:
        admin_base = ""
    admin_link = (
        f'<a href="{escape(admin_base)}/fackyou/login">{escape(admin_base)}/fackyou/login</a>'
        if admin_base
        else "<code>/fackyou/login</code>（未配置 alert.admin_base_url）"
    )
    try:
        cooldown = int(_cfg(db_path, "alert.cooldown_seconds", 3600))
    except (TypeError, ValueError):
        cooldown = 3600

    worst = max(stale_items, key=lambda item: int(item["lag_seconds"]))
    subject_names = " / ".join(item["lottery_name"] for item in stale_items) or "开奖数据"
    rows_html = "".join(
        f"""
        <tr>
            <td>{escape(str(item["lottery_name"]))}</td>
            <td>{escape(str(item["level_label"]))}</td>
            <td>{escape(str(item["issue"]))}<br><span style="color:#888;font-size:12px">开奖 {escape(str(item["draw_time_beijing"])) or "-"}</span></td>
            <td>{escape(str(item["expected_issue"]))}</td>
            <td>{escape(str(item["next_time_beijing"]))} 北京<br><span style="color:#888;font-size:12px">{escape(str(item["next_time_utc"]))}</span></td>
            <td style="color:red"><b>{escape(str(item["lag_text"]))}</b><br><span style="color:#888;font-size:12px">基线 {int(item["grace_seconds"])}s</span></td>
            <td style="font-size:12px">{escape(str(item["repair_hint"]))}</td>
        </tr>
        """
        for item in stale_items
    )
    diagnostics_html = "".join(
        f"""
        <tr>
            <td>{escape(str(item["lottery_name"]))}</td>
            <td style="font-size:12px">{escape(str(item["source_fetch"])) or "（无 source_fetch 审计记录）"}</td>
        </tr>
        """
        for item in stale_items
    )
    send_alert_async(
        db_path,
        subject=(
            f"[{env_label}][{worst['level_label']}] 开奖数据滞后 · {subject_names} · "
            f"超计划 {worst['lag_text']}（期号 {worst['issue']}）"
        ),
        body_html=f"""
        <h2>开奖数据滞后报警</h2>
        <p>以下彩种最新已开奖期的下一期计划时间已过，且超过该彩种的历史入库时延基线（正常源站发布延迟），
        仍未看到更晚一期入库。时间为<b>北京时间</b>，括号内为 UTC。</p>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse">
            <tr style="background:#f5f5f5">
                <th>彩种</th><th>级别</th><th>最新已开奖期</th><th>期望期号</th>
                <th>下一期计划时间</th><th>超计划时长</th><th>建议动作</th>
            </tr>
            {rows_html}
        </table>
        <p><b>最近源站抓取结论</b>（来自 draw_audit_log）</p>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse">
            {diagnostics_html}
        </table>
        <p>触发时间: <b>{escape(now_beijing_str)}</b>（{(now_utc).strftime("%Y-%m-%d %H:%M:%S UTC")}）</p>
        <p><b>快速修复顺序</b></p>
        <ol>
            <li>先看上面的「最近源站抓取结论」：若为 <code>old_period</code>，说明源站还没出新期，等待即可。</li>
            <li>香港彩: <code>POST /api/admin/crawler/run-hk</code></li>
            <li>澳门彩: <code>POST /api/admin/crawler/run-macau</code></li>
            <li>台湾彩: 由持久化任务 <code>taiwan_precise_open</code> 在 22:32（北京）自动开盘；先确认 <code>scheduler-worker</code> 存活并查看该任务状态，再在后台开奖记录页补录真实号码。</li>
            <li>需要重跑当日预测生成: <code>POST /api/admin/lottery-types/&lt;id&gt;/crawl-and-generate</code></li>
        </ol>
        <p>后台入口: {admin_link}</p>
        <p style="color:#666;font-size:12px">
            同类告警在 {cooldown} 秒冷却窗口内不会重复发送；仅当“期号/计划时间”变化或状态恢复时再次通知。
            恢复时会单独发送一封「已恢复」邮件。
        </p>
        """,
    )
    return True


def _send_draw_staleness_recovery(
    db_path: str | Path,
    recovered_state: Mapping[str, dict[str, str]],
    *,
    now_utc: datetime,
) -> None:
    """滞后状态恢复时补发一封恢复通知，避免管理员只能靠“不再收到邮件”推断。"""
    if not recovered_state:
        return
    try:
        from alerts.email_service import send_alert_async

        env_label = _runtime_env_label(db_path)
        rows_html = ""
        names: list[str] = []
        for lt_key, state in sorted(recovered_state.items()):
            try:
                lt_id = int(lt_key)
            except (TypeError, ValueError):
                continue
            lt_name = LOTTERY_NAMES.get(lt_id, lt_key)
            names.append(lt_name)
            rows_html += f"""
            <tr>
                <td>{escape(lt_name)}</td>
                <td>{escape(str(state.get("issue") or "-"))}</td>
                <td style="font-size:12px">{escape(str(state.get("next_time_utc") or "-"))}</td>
            </tr>"""
        now_beijing = (now_utc + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        send_alert_async(
            db_path,
            subject=f"[{env_label}][已恢复] 开奖数据滞后已恢复 · {' / '.join(names) or '开奖数据'}",
            body_html=f"""
        <h2>开奖数据滞后已恢复</h2>
        <p>以下彩种已看到更晚一期入库，滞后状态解除。</p>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse">
            <tr style="background:#f5f5f5"><th>彩种</th><th>此前落后的期号</th><th>此前的计划时间 (UTC)</th></tr>
            {rows_html}
        </table>
        <p>恢复时间: <b>{escape(now_beijing)} 北京时间</b>（{now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")}）</p>
        """,
        )
        _alert_logger.info(
            "Draw staleness recovery notice sent for lt=%s", ", ".join(sorted(recovered_state))
        )
    except Exception as exc:
        _alert_logger.error("Draw staleness recovery notice failed: %s", exc)


def alert_precise_draw_mismatch(
    db_path: str | Path,
    lottery_type_id: int,
    expected_period: str,
    actual_period: str,
    attempt_count: int,
) -> None:
    """精确期号检查全部失败后发送邮件报警（补充已有 error_logs 写入）。"""
    lt_name = LOTTERY_NAMES.get(lottery_type_id, str(lottery_type_id))

    alert_key = f"precise_mismatch_{lottery_type_id}"
    if _is_alert_suppressed(alert_key, db_path):
        _alert_logger.info("Precise draw mismatch alert suppressed by cooldown: lt=%s", lt_name)
        return

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
