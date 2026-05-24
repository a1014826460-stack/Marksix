"""Site-specific prediction module blueprints.

Keep the global default blueprint as a fallback, but allow certain sites to
declare a tighter module set that matches the frontend's real dependency map.
"""

from __future__ import annotations

from typing import Any

from helpers import REQUIRED_SITE_PREDICTION_MODE_IDS


DEFAULT_REQUIRED_MODE_IDS = tuple(int(item) for item in REQUIRED_SITE_PREDICTION_MODE_IDS)

# twsaimahui frontend pages that are confirmed to map to working prediction
# mechanisms in the current backend.
TWSAIMAHUI_REQUIRED_MODE_IDS = (
    3,    # getRccx / 肉菜草肖
    5,    # getTdsx1 / 天地生肖
    8,    # getHllx / 红蓝绿肖
    9,    # getCode num=16 / 16码
    10,   # getFyld / 风雨雷电
    12,   # getTou num=3 / 三头中特
    15,   # getDsxiao / 单双中特
    20,   # getShaWei / 绝杀三尾
    22,   # getXiaoma2 num=7 / 跑马图解
    24,   # getNnnx / 男女中特
    26,   # qqsh / 琴棋书画
    27,   # getXiaoma2 num=6 / 精品六肖
    28,   # danshuang / 单双
    30,   # getDsWei / 单双四尾
    31,   # getDsnx / 单双四肖
    39,   # getCypt / 成语平特肖
    41,   # getShatou / 绝杀一头
    42,   # getShaXiao num=3 / 绝杀三肖
    45,   # getHbx / 黑白各三肖
    46,   # getZhongte num=6 / 六肖中特
    47,   # getZhongte num=4 / 四肖中特
    48,   # getZhongte num=5 / 五肖中特
    49,   # getZhongte num=9 / 九肖中特
    50,   # getYjzy / 一句真言
    51,   # getXiaoma2 num=4 / 四肖八码
    54,   # getPtWei / 平特1尾
    56,   # getPingte num=1 / 平特1肖
    57,   # getDxzt / 大小中特
    58,   # getShaBanbo / 绝杀半波
    61,   # getSjsx / 四季生肖
    62,   # getJuzi / 欲钱解特字
    63,   # getJyzt / 家野中特
    69,   # getZhongte num=3 / 三肖中特
    88,   # getShama / 杀7码
    108,  # getDxztt1 / 大小中特带头
    116,  # getCode num=10 / 10码
    123,  # getWeima2 / 4尾8码
    132,  # getHeds / 合数单双
    141,  # getYysx / 阴阳生肖
    143,  # getYbzt / 1波中特
    144,  # getWwx / 文武生肖
    145,  # getX2jiam8 / 2肖加8码
    147,  # getYwx / 有无肖
    149,  # getBmzy / 笔墨纸砚
    151,  # getXysxma / 九肖一码
    152,  # getZyx / 左右生肖
    155,  # getJmxc / 吉美凶丑
    157,  # getFsx / 肥瘦肖
    158,  # getDxd / 大小胆
    159,  # getShaBds / 杀半波单双
    197,  # getSanqiXiao4new / 三期必中
    244,  # yyptj / 一语破天机
    246,  # qxbm / 七肖八码
    251,  # getJyxiao2 / 家野两肖
    295,  # getYzxj / 一字玄机
    336,  # getCyptwei / 成语平特尾
    470,  # getPingte num=3 / 平特3肖
    471,  # getTou num=2 / 两头中特
    472,  # getShaXiao num=1 / 绝杀1肖
    473,  # getShaXiao num=2 / 绝杀2肖
    475,  # brain teaser / 脑筋急转弯
    476,  # 跑马图解（带图）
    478,  # 台湾跑马图（带图）
)

TWSAIMAHUI_BLOCKED_ITEMS = (
    {
        "frontend_module": "019liubuzhong.js",
        "endpoint": "/api/kaijiang/rd70i73lziizczak/0gmqnw/1",
        "page_title": "六不中",
        "reason": "Current local data source does not match 六不中 payload semantics. mode_payload_333 is 天地4肖, not u6_code data.",
        "expected_fields": ("term", "u6_code", "res_code", "res_sx"),
        "status": "blocked_data_source",
    },
)

# twcaibawang homepage modules that can already be mapped to working
# mechanisms without changing shared routes or inventing new payload shapes.
# Keep this list intentionally conservative: only include modules whose
# frontend semantics are already clear in the current backend.
TWCAIBAWANG_REQUIRED_MODE_IDS = (
    12,
    26,
    34,
    38,
    49,
    50,
    52,
    54,
    56,
    57,
    58,
    60,
    197,
    472,
    479,
    480,
    481,
    482,
    483,
    484,
)

TWCAIBAWANG_BLOCKED_ITEMS = (
    {
        "frontend_module": "五肖五码",
        "page_title": "五肖五码",
        "reason": "Homepage block combines 五肖/四肖/三肖/二肖 and 五码/四码/三码/二码 in one custom static layout. No single existing mechanism matches its exact payload shape yet.",
        "expected_fields": ("issue", "xiao_5", "xiao_4", "xiao_3", "xiao_2", "code_5", "code_4", "code_3", "code_2"),
        "status": "blocked_exact_payload_mapping",
    },
    {
        "frontend_module": "公开一肖一码",
        "page_title": "一肖一码",
        "reason": "Homepage block contains 九肖/七肖/五肖/三肖 plus 14码/8码/5码 and a final 一肖一码 summary. Existing mechanisms cover parts of it, but not this exact combined payload shape.",
        "expected_fields": ("issue", "xiao_9", "xiao_7", "xiao_5", "xiao_3", "code_14", "code_8", "code_5", "best_xiao", "best_code"),
        "status": "blocked_exact_payload_mapping",
    },
    {
        "frontend_module": "高手榜单",
        "page_title": "高手榜单",
        "reason": "This section links to standalone detail pages like 11169.html and needs article/detail content APIs rather than prediction-module history rows.",
        "expected_fields": ("id", "slug", "title", "term", "html"),
        "status": "blocked_requires_article_api",
    },
    {
        "frontend_module": "输尽光",
        "page_title": "输尽光",
        "reason": "The homepage section name is clear, but its exact backend payload contract and matching mechanism are not yet confirmed from existing tables.",
        "expected_fields": ("issue", "content", "result_text"),
        "status": "blocked_unconfirmed_mechanism_mapping",
    },
    {
        "frontend_module": "六尾中特",
        "page_title": "六尾中特网",
        "reason": "The current backend has generic tail-based mechanisms, but this homepage module's exact six-tail layout and source mode_id are not confirmed yet.",
        "expected_fields": ("issue", "tail_values", "result_text"),
        "status": "blocked_unconfirmed_mode_id",
    },
    {
        "frontend_module": "四行中特",
        "page_title": "四行中特",
        "reason": "Current backend ships a stable 3行 mechanism (mode 53), but the homepage requests four-line semantics. This needs either a confirmed existing mode_id or a new mechanism.",
        "expected_fields": ("issue", "element_values", "result_text"),
        "status": "blocked_missing_matching_mechanism",
    },
    {
        "frontend_module": "绝杀10码",
        "page_title": "绝杀10码",
        "reason": "The site layout is known, but the exact source mode_id and stored payload columns still need confirmation from PostgreSQL history tables.",
        "expected_fields": ("issue", "codes", "result_text"),
        "status": "blocked_unconfirmed_mode_id",
    },
)


def _normalize_domain(value: Any) -> str:
    return str(value or "").strip().lower()


def _site_matches_twsaimahui(site: dict[str, Any] | None) -> bool:
    if not site:
        return False

    domain = _normalize_domain(site.get("domain"))
    if domain in {"www.twsaimahui.com", "twsaimahui.com"}:
        return True

    try:
        lottery_type_id = int(site.get("lottery_type_id") or 0)
    except (TypeError, ValueError):
        lottery_type_id = 0
    try:
        web_id = int(site.get("web_id") or site.get("start_web_id") or 0)
    except (TypeError, ValueError):
        web_id = 0

    return lottery_type_id == 3 and web_id == 6


def _site_matches_twcaibawang(site: dict[str, Any] | None) -> bool:
    if not site:
        return False

    domain = _normalize_domain(site.get("domain"))
    if domain in {"www.twcaibawang.com", "twcaibawang.com"}:
        return True

    try:
        web_id = int(site.get("web_id") or site.get("start_web_id") or 0)
    except (TypeError, ValueError):
        web_id = 0

    return web_id == 5


def get_required_mode_ids_for_site(site: dict[str, Any] | None) -> tuple[int, ...]:
    if _site_matches_twsaimahui(site):
        return TWSAIMAHUI_REQUIRED_MODE_IDS
    if _site_matches_twcaibawang(site):
        return TWCAIBAWANG_REQUIRED_MODE_IDS
    return DEFAULT_REQUIRED_MODE_IDS


def get_blocked_items_for_site(site: dict[str, Any] | None) -> list[dict[str, Any]]:
    if _site_matches_twsaimahui(site):
        return [dict(item) for item in TWSAIMAHUI_BLOCKED_ITEMS]
    if _site_matches_twcaibawang(site):
        return [dict(item) for item in TWCAIBAWANG_BLOCKED_ITEMS]
    return []


def get_blueprint_name_for_site(site: dict[str, Any] | None) -> str:
    if _site_matches_twsaimahui(site):
        return "twsaimahui"
    if _site_matches_twcaibawang(site):
        return "twcaibawang"
    return "default"
