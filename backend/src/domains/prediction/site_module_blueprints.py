"""Site prediction blueprint helpers.

Runtime should prefer blueprint data stored in PostgreSQL. Code constants here
are only the last-resort fallback for bootstrap and tests.
"""

from __future__ import annotations

import json
from typing import Any

from database.schema.prediction import DEFAULT_REQUIRED_MODE_IDS as SCHEMA_DEFAULT_REQUIRED_MODE_IDS
from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key


DEFAULT_REQUIRED_MODE_IDS = tuple(int(item) for item in SCHEMA_DEFAULT_REQUIRED_MODE_IDS)
DEFAULT_KNOWN_UNAVAILABLE_MODE_IDS = (
    63,
    64,
    65,
    66,
    67,
    68,
    151,
)

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
TWJINNIU_REQUIRED_MODE_IDS = (
    5,
    12,
    14,
    20,
    15,
    26,
    31,
    38,
    43,
    47,
    48,
    49,
    50,
    51,
    53,
    56,
    66,
    72,
    74,
    77,
    78,
    79,
    81,
    83,
    103,
    108,
    110,
    117,
    123,
    132,
    142,
    143,
    144,
    151,
    173,
    180,
    198,
    219,
    279,
    472,
    474,
    476,
    479,
    480,
    481,
    482,
    483,
    484,
)

TWSAIMAHUI_KNOWN_UNAVAILABLE_MODE_IDS = (
    5,
    9,
    10,
    15,
    22,
    24,
    27,
    30,
    39,
    41,
    47,
    48,
    63,
    88,
    116,
    123,
    132,
    141,
    143,
    144,
    145,
    147,
    149,
    151,
    152,
    155,
    157,
    158,
    159,
    244,
    246,
    251,
    295,
    336,
)
TWCAIBAWANG_KNOWN_UNAVAILABLE_MODE_IDS = ()
TWJINNIU_KNOWN_UNAVAILABLE_MODE_IDS = ()

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
TWJINNIU_BLOCKED_ITEMS = ()

# twcf888 v1 is intentionally conservative: only confirmed live mappings are
# required. Everything else stays blocked or snapshot-only.
TWCF888_REQUIRED_MODE_IDS = (
    2,
    5,
    12,
    14,
    15,
    20,
    26,
    27,
    38,
    41,
    42,
    43,
    45,
    47,
    49,
    50,
    53,
    54,
    57,
    66,
    69,
    74,
    88,
    103,
    132,
    143,
    198,
    279,
    470,
    482,
    472,
    473,
    483,
)

TWCF888_KNOWN_UNAVAILABLE_MODE_IDS = ()

TWCF888_BLOCKED_ITEMS = (
    {
        "frontend_module": "稳料四肖中",
        "page_title": "稳料四肖中",
        "reason": "Prediction-style module, but the backend mechanism and exact mode_id are still unconfirmed.",
        "status": "blocked_requires_backend_work",
    },
    {
        "frontend_module": "6尾中特",
        "page_title": "6尾中特",
        "reason": "Prediction-style module, but the backend mechanism and exact mode_id are still unconfirmed.",
        "status": "blocked_requires_backend_work",
    },
    {
        "frontend_module": "3肖防3码",
        "page_title": "3肖防3码",
        "reason": "Prediction-style module, but the backend mechanism and exact mode_id are still unconfirmed.",
        "status": "blocked_requires_backend_work",
    },
    {
        "frontend_module": "准杀7码",
        "page_title": "准杀7码",
        "reason": "Prediction-style module, but the backend mechanism and exact mode_id are still unconfirmed.",
        "status": "blocked_requires_backend_work",
    },
    {
        "frontend_module": "绝杀一行",
        "page_title": "绝杀一行",
        "reason": "Prediction-style module, but the backend mechanism and exact mode_id are still unconfirmed.",
        "status": "blocked_requires_backend_work",
    },
    {
        "frontend_module": "绝杀二尾",
        "page_title": "绝杀二尾",
        "reason": "Prediction-style module, but the backend mechanism and exact mode_id are still unconfirmed.",
        "status": "blocked_requires_backend_work",
    },
    {
        "frontend_module": "稳中七肖",
        "page_title": "稳中七肖",
        "reason": "Prediction-style module, but the backend mechanism and exact mode_id are still unconfirmed.",
        "status": "blocked_requires_backend_work",
    },
    {
        "frontend_module": "内幕资料",
        "page_title": "内幕资料",
        "reason": "Prediction/article boundary is still unconfirmed, so v1 keeps it out of live mapping.",
        "status": "blocked_requires_backend_work",
    },
    {
        "frontend_module": "18码中特",
        "page_title": "18码中特",
        "reason": "Prediction-style module, but the backend mechanism and exact mode_id are still unconfirmed.",
        "status": "blocked_requires_backend_work",
    },
    {
        "frontend_module": "广东5兄弟",
        "page_title": "广东5兄弟",
        "reason": "Prediction/article boundary is still unconfirmed, so v1 keeps it out of live mapping.",
        "status": "blocked_requires_backend_work",
    },
    {
        "frontend_module": "双波10码",
        "page_title": "双波10码",
        "reason": "Prediction-style module, but the backend mechanism and exact mode_id are still unconfirmed.",
        "status": "blocked_requires_backend_work",
    },
    {
        "frontend_module": "官方图库",
        "page_title": "官方图库",
        "reason": "Gallery content is not a prediction module and remains available only as static snapshot content.",
        "status": "snapshot_only",
    },
)

# Override the initial conservative v1 set with the currently confirmed live
# mappings. Keeping the redefinition here avoids touching older mojibake rows
# one-by-one while still making the blueprint deterministic.
TWCF888_REQUIRED_MODE_IDS = (
    2,
    5,
    12,
    14,
    15,
    20,
    26,
    27,
    28,
    38,
    41,
    42,
    43,
    45,
    47,
    49,
    50,
    51,
    53,
    54,
    57,
    66,
    69,
    74,
    88,
    95,
    98,
    100,
    103,
    122,
    132,
    143,
    180,
    197,
    198,
    224,
    226,
    279,
    470,
    472,
    473,
    482,
    483,
)

TWCF888_BLOCKED_ITEMS = ()

# Preserve public constant imports for older callers while sourcing their
# values from the immutable reachable-page manifest.
TWSAIMAHUI_REQUIRED_MODE_IDS = required_mode_ids_for_site_key("twsaimahui")
TWCAIBAWANG_REQUIRED_MODE_IDS = required_mode_ids_for_site_key("twcaibawang")
TWJINNIU_REQUIRED_MODE_IDS = required_mode_ids_for_site_key("twjinniu")
TWCF888_REQUIRED_MODE_IDS = required_mode_ids_for_site_key("twcf888")

def _normalize_domain(value: Any) -> str:
    return str(value or "").strip().lower()


def _parse_int_tuple(raw_value: Any) -> tuple[int, ...]:
    try:
        parsed = json.loads(str(raw_value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return ()
    values: list[int] = []
    for item in parsed if isinstance(parsed, list) else []:
        try:
            values.append(int(item))
        except (TypeError, ValueError):
            continue
    return tuple(values)


def _parse_blocked_items(raw_value: Any) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(str(raw_value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [dict(item) for item in parsed if isinstance(item, dict)]


def _load_blueprint_profile_from_db(site: dict[str, Any] | None) -> dict[str, Any] | None:
    if not site:
        return None

    blueprint_name = str(site.get("blueprint_name") or "").strip()
    if not blueprint_name:
        return None

    raw_profile = site.get("_blueprint_profile")
    if isinstance(raw_profile, dict):
        return dict(raw_profile)

    has_json_payload = any(
        site.get(key) not in (None, "")
        for key in (
            "blueprint_required_mode_ids_json",
            "blueprint_known_unavailable_mode_ids_json",
            "blueprint_blocked_items_json",
        )
    )
    if not has_json_payload:
        return None

    return {
        "blueprint_name": blueprint_name,
        "required_mode_ids": _parse_int_tuple(site.get("blueprint_required_mode_ids_json")),
        "known_unavailable_mode_ids": _parse_int_tuple(site.get("blueprint_known_unavailable_mode_ids_json")),
        "blocked_items": _parse_blocked_items(site.get("blueprint_blocked_items_json")),
    }


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
        web_id = int(site.get("web_id") or 0)
    except (TypeError, ValueError):
        web_id = 0

    # Minimal callers such as audits may only have the business web ID.  A
    # complete SiteContext still supplies lottery_type_id in production.
    return web_id == 6 and lottery_type_id in {0, 3}


def _site_matches_shengshi8800(site: dict[str, Any] | None) -> bool:
    if not site:
        return False

    domain = _normalize_domain(site.get("domain"))
    if domain in {"www.tw8800.com", "tw8800.com"}:
        return True

    try:
        lottery_type_id = int(site.get("lottery_type_id") or 0)
    except (TypeError, ValueError):
        lottery_type_id = 0
    try:
        web_id = int(site.get("web_id") or 0)
    except (TypeError, ValueError):
        web_id = 0

    return web_id == 4 and lottery_type_id in {0, 3}


def _site_matches_twcaibawang(site: dict[str, Any] | None) -> bool:
    if not site:
        return False

    domain = _normalize_domain(site.get("domain"))
    if domain in {"www.twcaibawang.com", "twcaibawang.com"}:
        return True

    try:
        web_id = int(site.get("web_id") or 0)
    except (TypeError, ValueError):
        web_id = 0

    return web_id == 5


def _site_matches_twjinniu(site: dict[str, Any] | None) -> bool:
    if not site:
        return False

    domain = _normalize_domain(site.get("domain"))
    if domain in {"www.twtongtian.com", "twtongtian.com", "www.twjinniu.com", "twjinniu.com"}:
        return True

    try:
        web_id = int(site.get("web_id") or 0)
    except (TypeError, ValueError):
        web_id = 0

    return web_id == 7


def _site_matches_twcf888(site: dict[str, Any] | None) -> bool:
    if not site:
        return False

    domain = _normalize_domain(site.get("domain"))
    if domain in {"www.twcf888.com", "twcf888.com"}:
        return True

    try:
        web_id = int(site.get("web_id") or 0)
    except (TypeError, ValueError):
        web_id = 0

    return web_id == 8


def get_required_mode_ids_for_site(site: dict[str, Any] | None) -> tuple[int, ...]:
    profile = _load_blueprint_profile_from_db(site)
    if profile:
        return tuple(int(item) for item in profile.get("required_mode_ids") or ())
    if _site_matches_shengshi8800(site):
        return required_mode_ids_for_site_key("shengshi8800")
    if _site_matches_twsaimahui(site):
        return required_mode_ids_for_site_key("twsaimahui")
    if _site_matches_twcaibawang(site):
        return required_mode_ids_for_site_key("twcaibawang")
    if _site_matches_twjinniu(site):
        return required_mode_ids_for_site_key("twjinniu")
    if _site_matches_twcf888(site):
        return required_mode_ids_for_site_key("twcf888")
    return DEFAULT_REQUIRED_MODE_IDS


def get_known_unavailable_mode_ids_for_site(site: dict[str, Any] | None) -> tuple[int, ...]:
    profile = _load_blueprint_profile_from_db(site)
    if profile:
        return tuple(int(item) for item in profile.get("known_unavailable_mode_ids") or ())
    if _site_matches_shengshi8800(site):
        return ()
    if _site_matches_twsaimahui(site):
        return TWSAIMAHUI_KNOWN_UNAVAILABLE_MODE_IDS
    if _site_matches_twcaibawang(site):
        return TWCAIBAWANG_KNOWN_UNAVAILABLE_MODE_IDS
    if _site_matches_twjinniu(site):
        return TWJINNIU_KNOWN_UNAVAILABLE_MODE_IDS
    if _site_matches_twcf888(site):
        return TWCF888_KNOWN_UNAVAILABLE_MODE_IDS
    return DEFAULT_KNOWN_UNAVAILABLE_MODE_IDS


def get_blocked_items_for_site(site: dict[str, Any] | None) -> list[dict[str, Any]]:
    profile = _load_blueprint_profile_from_db(site)
    if profile:
        return [dict(item) for item in profile.get("blocked_items") or []]
    if _site_matches_shengshi8800(site):
        return []
    if _site_matches_twsaimahui(site):
        return [dict(item) for item in TWSAIMAHUI_BLOCKED_ITEMS]
    if _site_matches_twcaibawang(site):
        return [dict(item) for item in TWCAIBAWANG_BLOCKED_ITEMS]
    if _site_matches_twjinniu(site):
        return [dict(item) for item in TWJINNIU_BLOCKED_ITEMS]
    if _site_matches_twcf888(site):
        return [dict(item) for item in TWCF888_BLOCKED_ITEMS]
    return []


def get_blueprint_name_for_site(site: dict[str, Any] | None) -> str:
    profile = _load_blueprint_profile_from_db(site)
    if profile:
        return str(profile.get("blueprint_name") or "default")
    if _site_matches_shengshi8800(site):
        return "shengshi8800"
    if _site_matches_twsaimahui(site):
        return "twsaimahui"
    if _site_matches_twcaibawang(site):
        return "twcaibawang"
    if _site_matches_twjinniu(site):
        return "twjinniu"
    if _site_matches_twcf888(site):
        return "twcf888"
    return "default"
