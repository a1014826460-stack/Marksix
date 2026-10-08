"""跨模块共享工具函数 — 字符串处理、数据转换、SQL 构造、开奖映射。

从 app.py 提取，不改变任何函数签名与行为。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from core.time_utils import beijing_now
from db import quote_identifier
from domains.lottery.draw_time import parse_draw_datetime
from utils.created_prediction_store import (
    CREATED_SCHEMA_NAME,
    normalize_color_label,
    quote_qualified_identifier as quote_schema_table,
    schema_table_exists,
    table_column_names,
)


# 前端需要的站点预测模块 mode_id 清单，按展示顺序排列
REQUIRED_SITE_PREDICTION_MODE_IDS = (
    3, 8, 12
)


def draw_time_to_unix_ms(draw_time: str) -> str:
    """Convert a Beijing-time draw timestamp to a UTC unix-ms string.
    args:
        - draw_time: A string in the format "YYYY-MM-DD HH:MM:SS", representing the draw time in Beijing time (UTC+8).
    return:
        - A string representing the corresponding UTC unix timestamp in milliseconds.
    """
    from calendar import timegm

    draw_dt = datetime.strptime(str(draw_time).strip(), "%Y-%m-%d %H:%M:%S")
    utc_dt = draw_dt - timedelta(hours=8)
    return str(int(timegm(utc_dt.timetuple()) * 1000))


def next_draw_time_from_current_draw(draw_time: str) -> str:
    """将北京时间的下一个抽奖时间戳提前一天返回。
    args：
    - draw_time: 一个字符串，格式为 "YYYY-MM-DD HH:MM:SS"，表示当前抽奖的北京时间。
    return:
    - 一个字符串，格式为 "YYYY-MM-DD HH:MM:SS"，表示下一个抽奖的北京时间，通常是当前抽奖时间加一天。
    """
    draw_dt = datetime.strptime(str(draw_time).strip(), "%Y-%m-%d %H:%M:%S")
    return (draw_dt + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")


def _get_max_terms_per_year(conn: Any) -> int:
    try:
        from runtime_config import get_config_from_conn
        return int(get_config_from_conn(conn, "prediction.max_terms_per_year", 365))
    except Exception:
        return 365


def _compute_next_issue_parts(
    year: int,
    term: int,
    *,
    max_terms_per_year: int,
) -> tuple[int, int]:
    next_term = term + 1
    next_year = year
    if next_term > max_terms_per_year:
        next_term = 1
        next_year += 1
    return next_year, next_term


def _format_issue(year: int, term: int) -> str:
    return f"{int(year)}{int(term):03d}"


def _taiwan_gap_alert_key(year: int, term: int) -> str:
    return f"alert._taiwan_missing_issue_{int(year)}_{int(term):03d}"


def _send_taiwan_issue_gap_alert(
    conn: Any,
    *,
    missing_year: int,
    missing_term: int,
    current_year: int,
    current_term: int,
    observed_future_year: int,
    observed_future_term: int,
) -> None:
    try:
        from alerts.email_service import send_alert_async
    except Exception:
        return

    alert_key = _taiwan_gap_alert_key(missing_year, missing_term)
    if conn.table_exists("system_config"):
        existing = conn.execute(
            "SELECT value_text FROM system_config WHERE key = ? LIMIT 1",
            (alert_key,),
        ).fetchone()
        if existing and str(dict(existing).get("value_text") or "").strip() == "1":
            return

    missing_issue = _format_issue(missing_year, missing_term)
    current_issue = _format_issue(current_year, current_term)
    observed_future_issue = _format_issue(observed_future_year, observed_future_term)
    logging.getLogger("taiwan.issue_gap").warning(
        "Taiwan issue gap detected: current_issue=%s missing_issue=%s observed_future_issue=%s",
        current_issue,
        missing_issue,
        observed_future_issue,
    )

    send_alert_async(
        conn.target,
        subject=f"[六合彩告警] 台湾彩缺失期号 {missing_issue}",
        body_html=f"""
        <h2>台湾彩缺失期号告警</h2>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse">
            <tr><td><b>当前已开奖期号</b></td><td>{current_issue}</td></tr>
            <tr><td><b>缺失期号</b></td><td style="color:red"><b>{missing_issue}</b></td></tr>
            <tr><td><b>已发现更晚期号</b></td><td>{observed_future_issue}</td></tr>
            <tr><td><b>年份</b></td><td>{missing_year}</td></tr>
            <tr><td><b>缺失期数</b></td><td>{missing_term:03d}</td></tr>
        </table>
        <p>系统检测到台湾彩期号发生跳跃，请尽快检查缺失期号数据。</p>
        """,
    )

    try:
        if conn.table_exists("system_config"):
            existing = conn.execute(
                "SELECT id FROM system_config WHERE key = ? LIMIT 1",
                (alert_key,),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE system_config SET value_text = ?, value_type = ?, updated_at = ? WHERE key = ?",
                    ("1", "int", datetime.utcnow().isoformat(), alert_key),
                )
            else:
                now = datetime.utcnow().isoformat()
                conn.execute(
                    """
                    INSERT INTO system_config (
                        key, value_text, value_type, description, is_secret, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        alert_key,
                        "1",
                        "int",
                        f"台湾彩缺失期号告警已发送: {missing_issue}",
                        now,
                        now,
                    ),
                )
    except Exception:
        pass

def _resolve_taiwan_next_issue_payload(conn: Any, latest_opened: dict[str, Any]) -> dict[str, Any]:
    current_year = int(latest_opened.get("year") or 0)
    current_term = int(latest_opened.get("term") or 0)
    draw_time = str(latest_opened.get("draw_time") or "").strip()
    stored_next_time = str(latest_opened.get("next_time") or "").strip()
    max_terms_per_year = _get_max_terms_per_year(conn)
    next_year, next_term = _compute_next_issue_parts(
        current_year,
        current_term,
        max_terms_per_year=max_terms_per_year,
    )

    future_rows = conn.execute(
        """
        SELECT year, term, draw_time
        FROM lottery_draws
        WHERE lottery_type_id = 3
          AND is_opened = 0
          AND (
            year > ?
            OR (year = ? AND term >= ?)
          )
        ORDER BY year ASC, term ASC, id ASC
        """,
        (current_year, current_year, next_term if next_year == current_year else 1),
    ).fetchall()

    next_draw_time = ""
    effective_next_time = stored_next_time
    expected_issue = (next_year, next_term)
    expected_found = False
    observed_future_issue: tuple[int, int] | None = None

    for row in future_rows:
        row_year = int(row["year"] or 0)
        row_term = int(row["term"] or 0)
        if (row_year, row_term) == expected_issue:
            expected_found = True
            next_draw_time = str(row["draw_time"] or "").strip()
            if next_draw_time:
                try:
                    effective_next_time = draw_time_to_unix_ms(next_draw_time)
                except ValueError:
                    pass
            break
        if (row_year, row_term) > expected_issue:
            observed_future_issue = (row_year, row_term)
            break

    if not expected_found:
        if observed_future_issue is not None:
            _send_taiwan_issue_gap_alert(
                conn,
                missing_year=next_year,
                missing_term=next_term,
                current_year=current_year,
                current_term=current_term,
                observed_future_year=observed_future_issue[0],
                observed_future_term=observed_future_issue[1],
            )
        if draw_time:
            next_draw_time = next_draw_time_from_current_draw(draw_time)
            try:
                expected_next_time = draw_time_to_unix_ms(next_draw_time)
                if not effective_next_time or effective_next_time != expected_next_time:
                    effective_next_time = expected_next_time
            except ValueError:
                pass

    return {
        "current_issue": _format_issue(current_year, current_term),
        "next_issue": _format_issue(next_year, next_term),
        "next_draw_time": next_draw_time,
        "next_time": effective_next_time or None,
    }


_HK_MACAU_DRAW_CLOCK_CFG: dict[int, tuple[str, tuple[int, int]]] = {
    1: ("draw.hk_default_draw_time", (21, 30)),
    2: ("draw.macau_default_draw_time", (21, 32)),
}
# 香港六合彩每周二/四/六开奖；澳门每日开奖。可用 system_config 覆盖。
# 星期编号与 Python ``datetime.weekday()`` 一致：周一=0 … 周日=6（周二=1/周四=3/周六=5）。
_HK_DRAW_WEEKDAYS_DEFAULT = "1,3,5"


def _conn_config(conn: Any, key: str, default: Any) -> Any:
    """从系统配置读取值（失败时返回默认值，绝不抛错）。"""
    try:
        from runtime_config import get_config_from_conn

        return get_config_from_conn(conn, key, default)
    except Exception:
        return default


def _as_utc_naive(value: datetime | None) -> datetime:
    now = value or datetime.now(timezone.utc)
    if now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)
    return now


def _configured_draw_weekdays(conn: Any, lottery_type_id: int) -> set[int]:
    """香港开奖星期集合（Python ``weekday()``：周一=0 … 周日=6）；澳门每日开奖返回空集合。"""
    if int(lottery_type_id) != 1:
        return set()
    raw = str(_conn_config(conn, "draw.hk_draw_weekdays", _HK_DRAW_WEEKDAYS_DEFAULT) or "")
    days: set[int] = set()
    for item in raw.replace("，", ",").split(","):
        text = item.strip()
        if not text:
            continue
        try:
            value = int(text)
        except ValueError:
            continue
        if 0 <= value <= 6:
            days.add(value)
    return days or {1, 3, 5}


def compute_next_draw_time_ms(
    conn: Any,
    lottery_type_id: int,
    *,
    now_utc: datetime | None = None,
) -> str:
    """按开奖排期推算下一次开奖时间（毫秒时间戳字符串）；台湾彩返回空串。

    为什么需要它：源站在开奖后的一段时间内可能不提供 ``next_time``，
    而备用源（``macaumarksix.com`` / ``api.csjid.com``）的响应里**完全没有该字段**。
    一旦新期是由备用源开盘的，``lottery_draws.next_time`` 就是空值，
    于是 ``lottery_types.next_time`` 与 ``system_config.lottery.*_next_time`` 被清空，
    ``/api/next-draw-deadline`` 返回 ``next_time: null``，
    站点面板"下次开奖"倒计时变成 ``--:--:--``（2026-09-26 港澳两期即为此故障）。

    香港按 ``draw.hk_draw_weekdays``（默认周二/四/六），澳门每日；
    钟点取 ``draw.hk_default_draw_time`` / ``draw.macau_default_draw_time``。
    """
    lottery_type = int(lottery_type_id)
    if lottery_type not in _HK_MACAU_DRAW_CLOCK_CFG:
        return ""
    cfg_key, fallback_clock = _HK_MACAU_DRAW_CLOCK_CFG[lottery_type]
    raw_clock = str(_conn_config(conn, cfg_key, "") or "").strip()
    hour, minute = fallback_clock
    if raw_clock:
        try:
            parts = raw_clock.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            hour, minute = fallback_clock

    beijing_now = _as_utc_naive(now_utc) + timedelta(hours=8)
    weekdays = _configured_draw_weekdays(conn, lottery_type)
    for offset in range(0, 8):
        candidate = (beijing_now + timedelta(days=offset)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        if weekdays and candidate.weekday() not in weekdays:
            continue
        if candidate <= beijing_now:
            continue
        candidate_utc = candidate - timedelta(hours=8)
        return str(int(candidate_utc.replace(tzinfo=timezone.utc).timestamp() * 1000))
    return ""


def resolve_next_time_ms(
    conn: Any,
    lottery_type_id: int,
    *,
    source_next_time: Any = "",
    stored_next_time: Any = "",
    now_utc: datetime | None = None,
) -> str:
    """决定最终对外的"下一期开奖时间"（毫秒时间戳字符串），绝不把排期清空。

    优先级：
    1. 最新已开奖行记录的 ``next_time``（源站或开盘时的真实值）；
    2. 已存配置值且仍在未来（保留，避免被空值覆盖）；
    3. 按开奖排期推导（仅香港/澳门；台湾彩返回空串，保持其原有推导路径）。
    """
    source = str(source_next_time or "").strip()
    if source:
        return source

    stored = str(stored_next_time or "").strip()
    if stored:
        try:
            stored_dt = datetime.fromtimestamp(int(stored) / 1000, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            stored_dt = None
        if stored_dt is not None and stored_dt > _as_utc_naive(now_utc).replace(tzinfo=timezone.utc):
            return stored

    derived = compute_next_draw_time_ms(conn, lottery_type_id, now_utc=now_utc)
    if derived:
        return derived
    return stored


def get_effective_next_draw_payload(conn: Any, lottery_type_id: int) -> dict[str, Any]:
    """返回该彩票类型的标准下一期抽奖的有效载荷。

    对于香港/澳门（type 1/2），唯一的真实信息来源是爬虫程序
    在最新打开的期数上保留了`lottery_draws.next_time`。
    对于台湾（type3），保持现有的派生回退行为。
    """
    row = conn.execute(
        """
        SELECT year, term, next_term, draw_time, next_time
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND is_opened = 1
          AND draw_time IS NOT NULL AND draw_time != ''
        ORDER BY year DESC, term DESC, id DESC
        LIMIT 1
        """,
        (int(lottery_type_id),),
    ).fetchone()

    # 优先使用最新已开奖数据的 next_time；台湾彩按 current_issue + 1 统一计算下一期期号，
    # 若存在对应未开奖记录则以该记录的 draw_time 为准，否则回退到 draw_time + 1 天。
    if row:
        data = dict(row)
        if int(lottery_type_id) == 3:
            return _resolve_taiwan_next_issue_payload(conn, data)

        current_year = int(data.get("year") or 0)
        current_term = int(data.get("term") or 0)
        next_term = int(data.get("next_term") or (current_term + 1 if current_term else 0))
        stored_next_time = str(data.get("next_time") or "").strip()
        return {
            "current_issue": f"{current_year}{current_term}",
            "next_issue": f"{current_year}{next_term}" if next_term else "",
            "next_draw_time": "",
            "next_time": stored_next_time or None,
        }

    # 没有已开奖数据时，fallback 到 lottery_types.next_time（通常是 crawler 预设的下一期开奖时间，或管理员手动设置的值）
    lt_row = conn.execute(
        "SELECT next_time FROM lottery_types WHERE id = ?",
        (int(lottery_type_id),),
    ).fetchone()
    return {
        "current_issue": "",
        "next_issue": "",
        "next_draw_time": "",
        "next_time": str(lt_row["next_time"]) if lt_row and lt_row["next_time"] else None,
    }


def sync_lottery_type_next_time_from_latest_draw(
    conn: Any,
    lottery_type_id: int,
    *,
    updated_at: str,
    source: str = "sync",
) -> str:
    """从lottery_draws中同步lottery_types.next_time。
        并且记录到 system_config 中，供前台页面直接读取，避免每次都要 join lottery_draws 来获取下一期开奖时间。

    args:
    - conn: 数据库连接对象，必须具有 execute 方法。
    - lottery_type_id: 彩票类型ID。
    - updated_at: 用于记录更新时间的字符串，格式为 "YYYY-MM-DD HH:MM:SS"。
    - source: 可选的字符串，表示同步来源，用于日志记录，默认为 "sync"。
    return:
    - 同步后的 next_time 字符串。
    """
    current_row = conn.execute(
        "SELECT next_time FROM lottery_types WHERE id = ?",
        (int(lottery_type_id),),
    ).fetchone()
    current_next_time = str(current_row["next_time"] or "") if current_row else ""
    payload = get_effective_next_draw_payload(conn, int(lottery_type_id))
    # 关键：绝不用"空值"覆盖已有排期。源站（尤其是备用源 macaumarksix / api.csjid.com）
    # 在新期开盘时可能不提供 next_time，直接用 payload 会把排期清空，
    # 站点面板"下次开奖"倒计时随即变成 --:--:--。
    next_time = resolve_next_time_ms(
        conn,
        int(lottery_type_id),
        source_next_time=payload.get("next_time"),
        stored_next_time=current_next_time,
    )
    if current_next_time != next_time:
        logging.getLogger("next_time.sync").warning(
            "lottery_types.next_time mismatch detected: source=%s lottery_type_id=%s stored=%s effective=%s current_issue=%s next_issue=%s",
            source,
            int(lottery_type_id),
            current_next_time,
            next_time,
            payload.get("current_issue") or "",
            payload.get("next_issue") or "",
        )
    conn.execute(
        "UPDATE lottery_types SET next_time = ?, updated_at = ? WHERE id = ?",
        (next_time, updated_at, int(lottery_type_id)),
    )
    # 同步写入 system_config，使前台页面可直接从配置中心读取
    _lt_cfg_prefix = {1: "lottery.hk", 2: "lottery.macau", 3: "lottery.taiwan"}
    _cfg_prefix = _lt_cfg_prefix.get(int(lottery_type_id))
    # 只有在有明确配置前缀的彩种（即香港/澳门/台湾）才同步到 system_config，其他彩种不处理
    if _cfg_prefix:
        # 获取最新已开奖记录的期号和年份
        _latest = conn.execute(
            """
            SELECT year, term FROM lottery_draws
            WHERE lottery_type_id = ? AND is_opened = 1
            ORDER BY year DESC, term DESC LIMIT 1
            """,
            (int(lottery_type_id),),
        ).fetchone()
        _current_period = ""
        _current_year = 0
        if _latest:
            _current_year = int(_latest["year"])
            _current_period = f"{_current_year}{int(_latest['term']):03d}"

        _config_updates = [
            (f"{_cfg_prefix}_next_time", next_time, "string", "彩种下一期开奖时间（自动同步）"),
            (f"{_cfg_prefix}_current_period", _current_period, "string", "彩种当前期号（自动同步）"),
            (f"{_cfg_prefix}_current_year", str(_current_year), "int", "彩种当前年份（自动同步）"),
        ]
        for _key, _val, _vtype, _desc in _config_updates:
            try:
                existing = conn.execute(
                    "SELECT id FROM system_config WHERE key = ? LIMIT 1", (_key,)
                ).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE system_config SET value_text = ?, updated_at = ? WHERE key = ?",
                        (_val, updated_at, _key),
                    )
                else:
                    conn.execute(
                        "INSERT INTO system_config (key, value_text, value_type, description, is_secret, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, 0, ?, ?)",
                        (_key, _val, _vtype, _desc, updated_at, updated_at),
                    )
            except Exception:
                pass  # system_config 表可能尚未初始化，静默跳过
    return next_time


def row_to_dict(row: Any | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "是", "启用"}


def split_csv(value: Any) -> list[str]:
    """把逗号分隔的字符串安全转成列表，去除空白项。 
    例如 "01, 02,03,, " → ["01", "02", "03"]，而不是 ["01", "02", "03", "", ""]。
    
    param 
        - value: 可能是逗号分隔的字符串，也可能是 None 或其他类型。
    return: 
        - list[str]: 去除空白项后的字符串列表。
    
    """
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def normalize_issue_part(value: Any) -> str:
    """把 year / term 统一成可比较的纯文本，避免空白字符串污染排序与匹配。"""
    return str(value or "").strip()


def parse_issue_int(value: Any) -> int | None:
    """把 year / term / type 这类期号字段安全转成整数。"""
    text = normalize_issue_part(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def sql_safe_int_expr(column_name: str, *, engine: str = "") -> str:
    """构造不会因空值或非数字种子行失败的整数表达式。"""
    quoted = quote_identifier(column_name)
    text_value = f"TRIM(CAST({quoted} AS TEXT))"
    if engine == "postgres":
        return (
            f"CASE WHEN {text_value} ~ '^[0-9]+$' "
            f"THEN CAST({text_value} AS INTEGER) ELSE 0 END"
        )
    return (
        f"CAST(COALESCE(NULLIF({text_value}, ''), '0') AS INTEGER)"
    )


def sql_normalized_csv_text_expr(column_name: str) -> str:
    """归一化逗号分隔文本，把只含逗号/空白的“伪空值”视为空串。"""
    quoted = quote_identifier(column_name)
    return f"TRIM(REPLACE(COALESCE(CAST({quoted} AS TEXT), ''), ',', ''))"


def normalize_csv_placeholder_text(value: Any) -> str:
    """把只含逗号/空白的逗号分隔文本归一为空串。"""
    text = str(value or "")
    return "" if text.replace(",", "").strip() == "" else text


def build_mode_payload_order_clause(columns: set[str], *, engine: str = "") -> str:
    """统一 mode_payload_* 历史记录排序，避免空字符串强转整数报错。"""
    order_parts: list[str] = []
    if "year" in columns:
        order_parts.append(f"{sql_safe_int_expr('year', engine=engine)} DESC")
    if "term" in columns:
        order_parts.append(f"{sql_safe_int_expr('term', engine=engine)} DESC")
    if "source_record_id" in columns:
        order_parts.append("CAST(source_record_id AS TEXT) DESC")
    elif "created_at" in columns:
        order_parts.append("CAST(created_at AS TEXT) DESC")
    elif "id" in columns:
        order_parts.append("CAST(id AS TEXT) DESC")
    return f" ORDER BY {', '.join(order_parts)}" if order_parts else ""


def build_mode_payload_filters(
    columns: set[str],
    *,
    engine: str = "",
    lottery_type_id: int | None = None,
    web_start: int | None = None,
    web_end: int | None = None,
    web_exact: int | None = None,
    require_result_consistency: bool = False,
) -> tuple[list[str], list[Any]]:
    """按彩种与站点来源构造 mode_payload 过滤条件。"""
    filters: list[str] = []
    params: list[Any] = []

    if lottery_type_id is not None and "type" in columns:
        filters.append(f"{sql_safe_int_expr('type', engine=engine)} = ?")
        params.append(int(lottery_type_id))

    web_column = "web_id" if "web_id" in columns else ("web" if "web" in columns else "")
    if web_column:
        if web_exact is not None:
            filters.append(f"{sql_safe_int_expr(web_column, engine=engine)} = ?")
            params.append(int(web_exact))
        elif web_start is not None and web_end is not None:
            filters.append(f"{sql_safe_int_expr(web_column, engine=engine)} BETWEEN ? AND ?")
            params.extend((int(web_start), int(web_end)))

    return filters, params


def load_fixed_data_maps(conn: Any) -> tuple[dict[str, str], dict[str, str]]:
    """读取 fixed_data 中的生肖 / 波色映射，统一给多个公开接口复用。
    
    params:
    - conn: 数据库连接对象，必须具有 table_exists 和 execute 方法。
    returns:
    - tuple[dict[str, str], dict[str, str]]: 包含两个字典的元组，分别是：
        - zodiac_map: 号码（两位字符串）到生肖标签的映射，以及号码（整数形式）到生肖标签的映射。
        - color_map: 号码（两位字符串）到波色标签的映射，以及号码（整数形式）到波色标签的映射。
    """
    zodiac_map: dict[str, str] = {}
    color_map: dict[str, str] = {}
    if not conn.table_exists("fixed_data"):
        return zodiac_map, color_map

    for sign, target in (("生肖", zodiac_map), ("波色", color_map)):
        rows = conn.execute(
            """
            SELECT name, code
            FROM fixed_data
            WHERE sign = ?
            """,
            (sign,),
        ).fetchall()
        for row in rows:
            label = str(row["name"] or "").strip()
            if not label:
                continue
            for code in split_csv(row["code"]):
                try:
                    normalized = f"{int(str(code)):02d}"
                except ValueError:
                    continue
                target.setdefault(normalized, label)
                target.setdefault(str(int(normalized)), label)

    return zodiac_map, color_map


def color_name_to_key(value: str) -> str:
    """把中文/英文波色名统一为前端使用的英文字符串。"""
    lowered = str(value or "").strip().lower()
    if lowered in {"red", "blue", "green"}:
        return lowered
    mapping = {
        "红": "red",
        "红波": "red",
        "red波": "red",
        "蓝": "blue",
        "蓝波": "blue",
        "blue波": "blue",
        "绿": "green",
        "绿波": "green",
        "green波": "green",
    }
    return mapping.get(str(value or "").strip(), "red")


def build_draw_result_payload(
    numbers: Any,
    zodiac_map: dict[str, str],
    color_map: dict[str, str],
) -> dict[str, Any]:
    """把 lottery_draws.numbers 还原成旧表 / 新站都能复用的开奖结构。"""
    normalized_codes: list[str] = []
    zodiacs: list[str] = []
    colors: list[str] = []
    balls: list[dict[str, str]] = []

    for raw_number in split_csv(numbers):
        try:
            normalized_code = f"{int(str(raw_number)):02d}"
        except ValueError:
            continue

        zodiac = zodiac_map.get(normalized_code, "")
        color = normalize_color_label(color_map.get(normalized_code, ""))
        normalized_codes.append(normalized_code)
        zodiacs.append(zodiac)
        colors.append(color)
        balls.append(
            {
                "value": normalized_code,
                "zodiac": zodiac,
                "color": color_name_to_key(color),
            }
        )

    return {
        "res_code": ",".join(normalized_codes),
        "res_sx": ",".join(zodiacs) if any(zodiacs) else "",
        "res_color": ",".join(colors) if any(colors) else "",
        "balls": balls,
    }


def load_lottery_draw_map(
    conn: Any,
    lottery_type_id: int,
    issues: set[tuple[int, int]],
) -> dict[tuple[int, int], dict[str, Any]]:
    """按 `year + term` 批量读取开奖状态，统一覆盖各类模块历史结果。"""
    if not issues:
        return {}
    if not conn.table_exists("lottery_draws"):
        return {}

    # Old SQLite fixtures/schemas predate opened_at; an absent column uses the
    # planned draw time, while a present invalid value remains fail-closed.
    opened_at_column = "opened_at" if "opened_at" in conn.table_columns("lottery_draws") else "NULL AS opened_at"

    years = sorted({year for year, _term in issues})
    terms = sorted({term for _year, term in issues})
    if not years or not terms:
        return {}

    year_placeholders = ", ".join("?" for _ in years)
    term_placeholders = ", ".join("?" for _ in terms)
    rows = conn.execute(
        f"""
        SELECT id, lottery_type_id, year, term, numbers, is_opened, next_term, draw_time, {opened_at_column}
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND year IN ({year_placeholders})
          AND term IN ({term_placeholders})
        ORDER BY year DESC, term DESC, id DESC
        """,
        (int(lottery_type_id), *years, *terms),
    ).fetchall()

    draw_map: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        key = (int(row["year"]), int(row["term"]))
        draw_map.setdefault(key, dict(row))
    return draw_map


def _resolve_history_delay_minutes(conn: Any, default: float = 8.0) -> float:
    """读取历史开奖展示闸门分钟数（system_config.history_backfill_delay_after_draw）。"""
    try:
        from runtime_config import get_config_from_conn

        minutes = float(get_config_from_conn(conn, "history_backfill_delay_after_draw", default))
    except Exception:
        return float(default)
    return max(0.0, minutes)


def _history_result_visible_after_delay(conn: Any, draw_row: dict[str, Any], *, now: datetime | None = None) -> bool:
    """Only expose historical draw results at draw_time plus the configured delay.

    旧站预测出口与 /public/draw-history 共用同一个闸门，闸门分钟数由
    ``system_config.history_backfill_delay_after_draw`` 控制（默认 20 分钟）。
    """
    from public.draw_reveal import is_full_draw_released

    now_dt = now or beijing_now()
    if not is_full_draw_released(draw_row, lottery_type_id=draw_row.get("lottery_type_id"), now=now_dt):
        return False

    draw_dt = parse_draw_datetime(str(draw_row.get("draw_time") or "").strip())
    if draw_dt is None:
        return False

    if now_dt <= draw_dt:
        return False

    elapsed_minutes = (now_dt - draw_dt).total_seconds() / 60.0
    return elapsed_minutes >= _resolve_history_delay_minutes(conn)


_PUBLIC_ACTUAL_RESULT_FIELDS = frozenset({
    "res_code", "res_sx", "res_color", "numbers", "draw_numbers", "result_numbers",
    "special_number", "special_code", "special_zodiac", "special_sx", "special_color",
    "special_wave", "special_element", "special_tail", "special_head",
    "specialNumber", "specialCode", "specialZodiac", "specialColor",
    "domestic_wild_category", "outcome", "actual_result", "last_result",
})
_PUBLIC_PREDICTION_FIELDS = frozenset({
    "content", "prediction_text", "prediction", "prediction_payload", "candidate", "candidates",
    "best_pick", "code_groups", "xiao_groups", "labels", "codes", "candidate_numbers",
})


def _hide_public_result_fields(value: Any, *, result_context: bool = False) -> Any:
    """Blank actual outcomes and their verdicts; keep supplier candidates intact."""
    if isinstance(value, list):
        return [_hide_public_result_fields(item, result_context=result_context) for item in value]
    if not isinstance(value, dict):
        return value
    hidden = {}
    for key, item in value.items():
        if key in _PUBLIC_PREDICTION_FIELDS:
            hidden[key] = item
        elif key in _PUBLIC_ACTUAL_RESULT_FIELDS or (result_context and key in {"value", "code", "number", "zodiac", "color", "wave", "element", "head", "tail"}):
            hidden[key] = ""
        elif key in {"is_correct", "isCorrect", "hit", "is_hit"}:
            hidden[key] = None
        elif key in {"is_opened", "draw_is_opened", "isOpened"}:
            hidden[key] = False
        elif key in {"result_text", "resultText", "hit_text"}:
            hidden[key] = "待开奖"
        elif key in {"special_ball", "specialBall"}:
            hidden[key] = None
        elif key == "result_balls":
            hidden[key] = []
        elif key == "result" and not isinstance(item, (dict, list)):
            hidden[key] = "待开奖"
        else:
            hidden[key] = _hide_public_result_fields(item, result_context=result_context or key == "result")
    return hidden


def _public_row_identity(row: dict[str, Any], default_lottery_type_id: Any = None) -> tuple[int | None, int | None, int | None]:
    raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
    type_value = default_lottery_type_id
    if type_value in (None, ""):
        type_value = row.get("lottery_type_id", row.get("type", raw.get("lottery_type_id", raw.get("type"))))
    lottery_type = parse_issue_int(type_value)
    lottery_type = lottery_type if lottery_type in {1, 2, 3} else None
    year = parse_issue_int(row.get("year", raw.get("year")))
    term = parse_issue_int(row.get("term", raw.get("term")))
    return lottery_type, year, term


def apply_public_result_gate(conn: Any, payload: Any, *, default_lottery_type_id: int | None = None, respect_history_delay: bool = True) -> Any:
    """Recheck cached historical outcome rows against authoritative draw state.

    Only Taiwan/unknown types are paced. The top-level live ``draw`` is left to
    the per-ball slicer; candidate columns never participate in this decision.
    """
    from public.draw_reveal import is_full_draw_released

    grouped: dict[int, set[tuple[int, int]]] = {}

    def collect(value: Any, *, top: bool = False) -> None:
        if isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            lottery_type, year, term = _public_row_identity(value, default_lottery_type_id)
            if lottery_type == 3 and year is not None and term is not None:
                grouped.setdefault(lottery_type, set()).add((year, term))
            for key, item in value.items():
                if not (top and key == "draw") and key not in _PUBLIC_PREDICTION_FIELDS:
                    collect(item)

    collect(payload, top=True)
    maps = {lottery_type: load_lottery_draw_map(conn, lottery_type, issues) for lottery_type, issues in grouped.items()}
    now = beijing_now()

    def gate(value: Any, *, top: bool = False, inherited_identity: tuple[int | None, int | None, int | None] | None = None) -> Any:
        if isinstance(value, list):
            return [gate(item, inherited_identity=inherited_identity) for item in value]
        if not isinstance(value, dict):
            return value
        raw = value.get("raw") if isinstance(value.get("raw"), dict) else {}
        is_period_row = any(key in value or key in raw for key in ("year", "term", "issue", "current_issue", "result_text", "resultText", "hit_text", "is_correct", "isCorrect", "is_hit", "special_ball", "specialBall", "result_balls"))
        nested_result = value.get("result")
        is_period_row = is_period_row or (isinstance(nested_result, dict) and any(key in nested_result for key in {"value", "number", "zodiac", "special_ball", "specialBall", "result_balls"}))
        is_period_row = is_period_row or any(
            key in value or key in raw for key in _PUBLIC_ACTUAL_RESULT_FIELDS - {"numbers"}
        ) or any(isinstance(row.get("numbers"), str) for row in (value, raw))
        lottery_type, year, term = _public_row_identity(value, default_lottery_type_id)
        has_own_issue = any(key in value or key in raw for key in ("year", "term", "issue", "current_issue"))
        if not has_own_issue and inherited_identity is not None:
            lottery_type, year, term = inherited_identity
        identity = (lottery_type, year, term)
        released = False
        if is_period_row and lottery_type not in {1, 2}:
            draw = maps.get(3, {}).get((year, term)) if lottery_type == 3 else None
            if not draw or not is_full_draw_released(draw, lottery_type_id=3, now=now) or (respect_history_delay and not _history_result_visible_after_delay(conn, draw, now=now)):
                result = _hide_public_result_fields(value)
                result["result_restricted"] = True
                return result
            released = True
        result = {key: item if (top and key == "draw") or key in _PUBLIC_PREDICTION_FIELDS else gate(item, inherited_identity=identity) for key, item in value.items()}
        if released:
            result["result_restricted"] = False
        return result

    return gate(payload, top=True)


def apply_lottery_draw_overlay(
    conn: Any,
    rows: list[dict[str, Any]],
    *,
    default_lottery_type_id: int | None = None,
) -> list[dict[str, Any]]:
    """以 `public.lottery_draws` 为准修正开奖结果，并隐藏未开奖期的号码。"""
    if not rows:
        return rows

    grouped_issues: dict[int, set[tuple[int, int]]] = {}
    for row in rows:
        lottery_type_id, year, term = _public_row_identity(row, default_lottery_type_id)
        if lottery_type_id is None or year is None or term is None:
            continue
        grouped_issues.setdefault(lottery_type_id, set()).add((year, term))

    if not grouped_issues:
        return [dict(row) if _public_row_identity(row, default_lottery_type_id)[0] in {1, 2} else _hide_public_result_fields(row) for row in rows]

    zodiac_map, color_map = load_fixed_data_maps(conn)
    draw_maps = {
        lottery_type_id: load_lottery_draw_map(conn, lottery_type_id, issues)
        for lottery_type_id, issues in grouped_issues.items()
    }

    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized = dict(row)
        lottery_type_id, year, term = _public_row_identity(row, default_lottery_type_id)
        if lottery_type_id is None or year is None or term is None:
            normalized_rows.append(_hide_public_result_fields(normalized) if lottery_type_id not in {1, 2} else normalized)
            continue

        draw_row = draw_maps.get(lottery_type_id, {}).get((year, term))
        if not draw_row:
            normalized_rows.append(_hide_public_result_fields(normalized) if lottery_type_id == 3 else normalized)
            continue

        is_opened = bool(draw_row.get("is_opened"))
        normalized["draw_is_opened"] = is_opened
        normalized["draw_issue"] = f"{draw_row.get('year') or ''}{draw_row.get('term') or ''}"
        normalized["draw_time"] = str(draw_row.get("draw_time") or "")
        normalized["reveal_start"] = str(draw_row.get("opened_at") or draw_row.get("draw_time") or "")

        if not _history_result_visible_after_delay(conn, draw_row):
            normalized = _hide_public_result_fields(normalized)
            normalized_rows.append(normalized)
            continue

        draw_result = build_draw_result_payload(
            draw_row.get("numbers"),
            zodiac_map,
            color_map,
        )
        if draw_result["res_code"]:
            normalized["res_code"] = draw_result["res_code"]
        if draw_result["res_sx"]:
            normalized["res_sx"] = draw_result["res_sx"]
        if draw_result["res_color"]:
            normalized["res_color"] = draw_result["res_color"]
        normalized_rows.append(normalized)

    return normalized_rows


def build_mode_payload_row_key(row: dict[str, Any]) -> tuple[str, str, str]:
    """为 created / public 双来源记录构造期号去重键，保证 created 优先。"""
    type_value = normalize_issue_part(row.get("type"))
    year = normalize_issue_part(row.get("year"))
    term = normalize_issue_part(row.get("term"))
    if year or term:
        # A site may have several source records for one issue. Public pages
        # expose one historical row per issue, independent of source web_id.
        return (type_value, year, term)
    return (
        type_value,
        normalize_issue_part(row.get("source_record_id")),
        normalize_issue_part(row.get("id")),
    )


def merge_preferred_mode_payload_rows(
    preferred_rows: list[dict[str, Any]],
    fallback_rows: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    """合并 created / public 两套来源，保留 created 优先级并按期号去重。"""
    merged: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for row in [*preferred_rows, *fallback_rows]:
        row_key = build_mode_payload_row_key(row)
        if row_key in seen_keys:
            continue
        seen_keys.add(row_key)
        merged.append(row)
        if len(merged) >= limit:
            break

    # 合并后可能因回填打破降序，重新按 year/term 降序排列
    merged.sort(
        key=lambda row: (
            _safe_issue_int(row.get("year")),
            _safe_issue_int(row.get("term")),
        ),
        reverse=True,
    )

    return merged


def _safe_issue_int(value: Any) -> int:
    """将 year/term 安全转为整数用于排序，无效值返回 0。"""
    try:
        s = str(value).strip() if value is not None else ""
        return int(s) if s else 0
    except (ValueError, TypeError):
        return 0


def load_mode_payload_rows_from_source(
    conn: Any,
    *,
    table_name: str,
    limit: int,
    schema_name: str | None = None,
    lottery_type_id: int | None = None,
    web_start: int | None = None,
    web_end: int | None = None,
    web_exact: int | None = None,
    require_result_consistency: bool = False,
) -> list[dict[str, Any]]:
    """按来源 schema 读取 mode_payload 历史记录。
    
    args:
    - conn: 数据库连接对象，必须具有 table_exists 和 execute 方法。
    - table_name: 表名，通常是 "mode_payload_created" 或 "mode_payload
    - limit: 读取记录的最大数量。
    - schema_name: 可选的模式名，如果提供则从 "schema_name.table_name"
    - lottery_type_id:
    - web_start: 站点ID范围起始值，配合 web_end 使用
    - web_end: 站点ID范围结束值，配合 web_start 使用
    - web_exact: 站点ID精确匹配值，优先级高于 web_start/web_end
    - require_result_consistency: 是否只读取结果与 lottery_draws 一致的记录
    """
    if schema_name:
        if getattr(conn, "engine", "") != "postgres" or not schema_table_exists(conn, schema_name, table_name):
            return []
        columns = set(table_column_names(conn, schema_name, table_name))
        table_ref = quote_schema_table(schema_name, table_name)
    else:
        if not conn.table_exists(table_name):
            return []
        columns = set(conn.table_columns(table_name))
        table_ref = quote_identifier(table_name)

    filters, params = build_mode_payload_filters(
        columns,
        engine=str(getattr(conn, "engine", "")),
        lottery_type_id=lottery_type_id,
        web_start=web_start,
        web_end=web_end,
        web_exact=web_exact,
        require_result_consistency=require_result_consistency,
    )
    where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""
    order_clause = build_mode_payload_order_clause(
        columns,
        engine=str(getattr(conn, "engine", "")),
    )

    rows = conn.execute(
        f"""
        SELECT *
        FROM {table_ref}
        {where_clause}
        {order_clause}
        LIMIT ?
        """,
        (*params, max(1, limit)),
    ).fetchall()
    return [dict(row) for row in rows]
