"""Internal manifest for prediction modules used by accessible site pages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


DependencyKind = Literal["page_module", "composite_source"]


@dataclass(frozen=True)
class SitePageDependency:
    site_key: str
    page_path: str
    source_path: str
    mode_ids: tuple[int, ...]
    kind: DependencyKind = "page_module"
    endpoint: str = ""
    params: tuple[tuple[str, str], ...] = ()
    blocked_reason: str = ""


def _legacy(
    source_path: str,
    endpoint: str,
    mode_id: int,
    *,
    num: int | None = None,
) -> SitePageDependency:
    params = (("num", str(num)),) if num is not None else ()
    return SitePageDependency(
        site_key="twsaimahui",
        page_path="/vendor/twsaimahui/index.html",
        source_path=source_path,
        endpoint=endpoint,
        params=params,
        mode_ids=(mode_id,),
    )


# Only dependencies from non-commented script tags in twsaimahui/index.html
# belong here. The compatibility route owns the exact endpoint/num mapping.
_DEPENDENCIES: tuple[SitePageDependency, ...] = (
    # Shengshi8800 is the reachable legacy shell for site 4. Only scripts
    # loaded by its non-commented index.html are prediction dependencies.
    *(
        SitePageDependency(
            site_key="shengshi8800",
            page_path="/vendor/shengshi8800/index.html",
            source_path=source_path,
            endpoint=endpoint,
            params=params,
            mode_ids=(mode_id,),
        )
        for source_path, endpoint, params, mode_id in (
            ("static/js/027ptw.js", "getPingte", (("num", "2"),), 43),
            ("static/js/023sqzt.js", "getSanqiXiao4new", (), 197),
            ("static/js/012sbzt.js", "sbzt", (), 38),
            ("static/js/001qxqm.js", "qxbm", (), 246),
            ("static/js/wxbm.js", "qxbm", (), 246),
            ("static/js/028sj.js", "getYjzy", (), 50),
            ("static/js/007lxzt.js", "lxzt", (), 46),
            ("static/js/035hblx.js", "getHbnx", (("num", "3"),), 45),
            ("static/js/026sssx.js", "getHllx", (("num", "2"),), 8),
            ("static/js/6w.js", "getWei", (("num", "6"),), 2),
            ("static/js/9xiao.js", "jxzt", (), 49),
            ("static/js/cxqd.js", "getSjsx", (("num", "3"),), 61),
            ("static/js/032cxqd.js", "getSjsx", (("num", "3"),), 61),
            ("static/js/ds4x.js", "getDsnx", (("num", "4"),), 31),
            ("static/js/crc.js", "getRccx", (("num", "2"),), 3),
            ("static/js/033rcc.js", "getRccx", (("num", "2"),), 3),
            ("static/js/tp5.js", "getPmxjcz", (("num", "6"),), 331),
            ("static/js/dx.js", "getDxztt1", (("num", "1"),), 108),
            ("static/js/5xiao.js", "wxzt", (), 48),
            ("static/js/1.js", "yyptj", (), 244),
            ("static/js/014sixiaobama.js", "sxbm", (), 51),
            ("static/js/029sz.js", "getSzxj", (), 52),
            ("static/js/024jsyw.js", "getShaWei", (("num", "1"),), 20),
            ("static/js/013shzt.js", "getXingte", (("num", "3"),), 53),
            ("static/js/006ptyw.js", "ptyw", (), 54),
            ("static/js/031dssx.js", "dssx", (), 31),
            ("static/js/021qqsh.js", "qqsh", (), 26),
            ("static/js/009stzt.js", "getTou", (("num", "3"),), 12),
            ("static/js/016teduan.js", "getCodeDuan", (("num", "12"),), 65),
            ("static/js/002ptyx.js", "getPingte", (("num", "1"),), 56),
            ("static/js/003dxzt.js", "getDxzt", (("num", "1"),), 57),
            ("static/js/022jsbb.js", "getShaBanbo", (("num", "1"),), 58),
            ("static/js/030ym.js", "getDjym", (), 59),
            ("static/js/015maishazs.js", "danshuang", (), 28),
            ("static/js/008jxym.js", "getXmx1", (("num", "9"),), 151),
            ("static/js/020ssx.js", "getShaXiao", (("num", "3"),), 42),
            ("static/js/018shu3x.js", "getShaXiao", (("num", "3"),), 42),
            ("static/js/017yuqian.js", "getJuzi", (("num", "juzi1"),), 62),
            ("static/js/019ma24.js", "getCode", (("num", "24"),), 34),
            ("static/js/004jyzt.js", "getJyzt", (("num", "2"),), 63),
            ("static/js/011yqjt.js", "getJuzi", (("num", "yqmtm"),), 68),
        )
    ),
    _legacy("static/js/061jy2x.js", "getJyxiao2", 251),
    _legacy("static/js/033zuoyou.js", "getZyx", 152, num=2),
    _legacy("static/js/012liuxiao.js", "getXiaoma2", 27),
    _legacy("static/js/044yinyang.js", "getYysx", 141, num=2),
    _legacy("static/js/027six8m.js", "getXiaoma2", 51, num=4),
    _legacy("static/js/003ds4w.js", "getDsWei", 30, num=4),
    _legacy("static/js/071ds.js", "danshuang", 28, num=2),
    _legacy("static/js/073sixiao.js", "getZhongte", 47, num=4),
    _legacy("static/js/006heshuds.js", "getHeds", 132, num=2),
    _legacy("static/js/043tiandi.js", "getTdsx1", 5, num=2),
    _legacy("static/js/049rccx.js", "getRccx", 3, num=2),
    _legacy("static/js/040jiaye.js", "getJyzt", 63, num=2),
    _legacy("static/js/042ycwx.js", "getZhongte", 48, num=5),
    _legacy("static/js/039heibai.js", "getHbx", 45, num=2),
    _legacy("static/js/014jiuxiao.js", "getZhongte", 49, num=9),
    _legacy("static/js/031wuxiao.js", "getZhongte", 69, num=3),
    _legacy("static/js/060ds4x.js", "getDsnx", 31, num=4),
    _legacy("static/js/011jiepaoma.js", "getXiaoma2", 22, num=7),
    _legacy("static/js/030lflx.js", "getZhongte", 47, num=4),
    _legacy("static/js/068chengyupw.js", "getCyptwei", 336, num=2),
    _legacy("static/js/023sanqibizhong.js", "getSanqiXiao4new", 197, num=7),
    _legacy("static/js/075tiandi.js", "getTdsx1", 5, num=2),
    _legacy("static/js/038ma10.js", "getCode", 116, num=10),
    _legacy("static/js/050siji.js", "getSjsx", 61, num=3),
    _legacy("static/js/004danshuang.js", "getDsxiao", 15, num=2),
    _legacy("static/js/036ma12.js", "getYbzt", 143, num=2),
    _legacy("static/js/026siw8m.js", "getWeima2", 123, num=4),
    _legacy("static/js/035ma16.js", "getCode", 9, num=16),
    _legacy("static/js/065yiziptx.js", "getPingte", 56, num=1),
    _legacy("static/js/047liuxiao.js", "getZhongte", 46, num=6),
    _legacy("static/js/046wenwu.js", "getWwx", 144, num=2),
    _legacy("static/js/002daxiao.js", "getDxzt", 57, num=2),
    _legacy("static/js/045youwu.js", "getYwx", 147, num=2),
    _legacy("static/js/067sanzipw.js", "getPingte", 470, num=3),
    _legacy("static/js/062linbei6x.js", "getZhongte", 46, num=6),
    _legacy("static/js/053wfsb.js", "getBmzy", 149, num=3),
    _legacy("static/js/057s1x.js", "getShaXiao", 472, num=1),
    _legacy("static/js/022pt1w.js", "getPtWei", 54, num=2),
    _legacy("static/js/072liangtou.js", "getTou", 471, num=2),
    _legacy("static/js/056s7m.js", "getShama", 88, num=7),
    _legacy("static/js/058s2x.js", "getShaXiao", 473, num=2),
    _legacy("static/js/051fyld.js", "getFyld", 10, num=3),
    _legacy("static/js/066chengyupx.js", "getCypt", 39, num=2),
    SitePageDependency(
        site_key="twsaimahui",
        page_path="/vendor/twsaimahui/index.html",
        source_path="static/js/019liubuzhong.js",
        endpoint="rd70i73lziizczak/0gmqnw/1",
        mode_ids=(),
        blocked_reason="六不中页面需要 u6_code，当前没有语义匹配的 mode_payload 数据源。",
    ),
    _legacy("static/js/013jiux1m.js", "getXysxma", 151, num=9),
    _legacy("static/js/024santou.js", "getTou", 12, num=3),
    _legacy("static/js/025sanhang.js", "getXingte", 53, num=3),
    _legacy("static/js/001sb.js", "sbzt", 38),
    _legacy("static/js/018sha1tou.js", "getShatou", 41, num=1),
    _legacy("static/js/041meichou.js", "getJmxc", 155, num=2),
    _legacy("static/js/015sha3w.js", "getShaWei", 20, num=3),
    _legacy("static/js/016sha3x.js", "getShaXiao", 42, num=3),
    _legacy("static/js/034feishou.js", "getFsx", 157, num=2),
    _legacy("static/js/074ptyx.js", "getPingte", 56, num=1),
    _legacy("static/js/037dandaxiao.js", "getDxd", 158, num=2),
    _legacy("static/js/048hllx.js", "getHllx", 8, num=2),
    _legacy("static/js/052qqsh.js", "qqsh", 26, num=3),
    _legacy("static/js/054sbanbo.js", "getShaBanbo", 58, num=1),
    _legacy("static/js/055sbands.js", "getShaBds", 159, num=1),
    # The React homepage loads these exact source rows with loadLegacyModeRows.
    *(
        SitePageDependency(
            site_key="twjinniu",
            page_path="/twjinniu",
            source_path="frontend/lib/twjinniu-homepage.ts",
            endpoint="loadLegacyModeRows",
            params=(("mode_id", str(mode_id)),),
            mode_ids=(mode_id,),
        )
        for mode_id in (
            15, 31, 43, 49, 50, 51, 56, 72, 77, 78, 79, 81, 103,
            108, 110, 117, 123, 142, 151, 173, 180, 219, 279, 474,
            476, 484,
        )
    ),
    # Every entry below is rendered by the accessible Twjinniu article route.
    # These sources are distinct from the homepage cards above and must remain
    # authorized even when they are not linked from the current homepage layout.
    *(
        SitePageDependency(
            site_key="twjinniu",
            page_path="/twjinniu/article/[id]",
            source_path="frontend/lib/twjinniu-articles.ts",
            endpoint="article_live_module",
            params=(("mode_id", str(mode_id)),),
            mode_ids=(mode_id,),
        )
        for mode_id in (
            479, 12, 481, 472, 20, 482, 198, 48, 144, 483, 14, 5,
            47, 279, 66, 143, 53, 38, 132, 26, 480, 74,
        )
    ),
    # Twcf888 articles with live_backed status have explicit mode IDs. The
    # article for 7637 is a parity+size composite and therefore needs both.
    *(
        SitePageDependency(
            site_key="twcf888",
            page_path="/twcf888",
            source_path="frontend/lib/twcf888-articles.ts",
            endpoint="article_live_backed",
            params=(("mode_id", str(mode_id)),),
            mode_ids=(mode_id,),
        )
        for mode_id in (
            2, 5, 12, 14, 15, 20, 26, 27, 38, 41, 42, 43, 45, 47,
            49, 50, 53, 54, 57, 66, 74, 88, 95, 98, 100, 103, 132,
            143, 180, 198, 279, 470, 472, 473, 482, 483,
        )
    ),
    SitePageDependency(
        site_key="twcf888",
        page_path="/twcf888",
        source_path="frontend/lib/twcf888-articles.ts",
        endpoint="article_live_backed",
        params=(("article_id", "7637"),),
        mode_ids=(28, 57),
        kind="composite_source",
    ),
    SitePageDependency(
        site_key="twcf888",
        page_path="/twcf888",
        source_path="frontend/lib/twcf888-articles.ts",
        endpoint="article_snapshot",
        mode_ids=(),
        blocked_reason="广东5兄弟尚未确认精确的实时预测模块映射。",
    ),
    # React page renderers resolve these public modules by mechanism key.
    *(
        SitePageDependency(
            site_key="twcaibawang",
            page_path="/twcaibawang",
            source_path="frontend/components/twcaibawang/TwcaibawangHomeClient.tsx",
            endpoint="public_site_page",
            params=(("mode_id", str(mode_id)),),
            mode_ids=(mode_id,),
        )
        for mode_id in (
            12, 26, 34, 38, 49, 50, 52, 54, 56, 57, 58, 60, 197,
            472, 474, 475, 476, 478, 479, 480, 481, 482, 483, 484,
        )
    ),
    # Vendor composites render on the same page and require all source rows.
    *(
        SitePageDependency(
            site_key="twcaibawang",
            page_path="/twcaibawang",
            source_path="backend/src/vendor/homepage_modules.py",
            endpoint=module_key,
            mode_ids=mode_ids,
            kind="composite_source",
        )
        for module_key, mode_ids in (
            ("wuxiao_wuma", (47, 69, 151)),
            ("public_yixiao_yima", (49, 44, 151)),
            ("shuangbo_12ma", (38,)),
            ("shujinguang", (44,)),
            ("daxiao_2tou", (57, 108)),
            ("tiandi_2xiao", (5, 251)),
        )
    ),
)


def dependencies_for_site(site_key: str) -> tuple[SitePageDependency, ...]:
    """Return internal dependencies for every accessible prediction page of a site."""
    return tuple(item for item in _DEPENDENCIES if item.site_key == str(site_key))


def blocked_dependencies_for_site(site_key: str) -> tuple[SitePageDependency, ...]:
    return tuple(item for item in dependencies_for_site(site_key) if item.blocked_reason)


def required_mode_ids_for_site_key(site_key: str) -> tuple[int, ...]:
    """Return the ordered, de-duplicated modes an accessible site page needs."""
    return tuple(
        dict.fromkeys(
            mode_id
            for item in dependencies_for_site(site_key)
            if not item.blocked_reason
            for mode_id in item.mode_ids
        )
    )


def generation_assurance_for_mode(
    mode_id: int | None,
    *,
    blocked_reason: str = "",
) -> str:
    """Classify internal future-generation assurance without exposing it via HTTP."""
    if blocked_reason or mode_id is None:
        return "blocked"

    try:
        normalized_mode_id = int(mode_id)
    except (TypeError, ValueError):
        return "blocked"

    # Import lazily to keep the manifest usable by schema migrations without
    # loading dynamic runtime configuration.
    from domains.prediction.generation_rules import get_generation_rule
    from predict.mechanisms import PREDICTION_CONFIGS

    config = next(
        (
            item
            for item in PREDICTION_CONFIGS.values()
            if int(getattr(item, "default_modes_id", 0) or 0) == normalized_mode_id
        ),
        None,
    )
    if config is None:
        return "history_only"
    return "controlled_future" if get_generation_rule(config).supported else "history_only"
