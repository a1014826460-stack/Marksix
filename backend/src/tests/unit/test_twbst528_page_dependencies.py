from __future__ import annotations


def test_twbst528_page_manifest_authorizes_homepage_and_reviewed_article_modules():
    from domains.prediction.site_page_dependencies import (
        dependencies_for_site,
        required_mode_ids_for_site_key,
    )

    dependencies = dependencies_for_site("twbst528")

    assert {item.endpoint for item in dependencies} == {
        "yijuzhenyan",
        "shuangbo",
        "7xiao7ma",
        "pt2xiao",
        "jueshabanbo",
        "pt1wei",
        "daxiao",
        "4xiao8ma",
        "pt1xiao",
        "title_5",
        "title_47",
        "pt3xiao",
        "juesha1xiao",
        "danshuangtema",
        "juesha1wei",
        "juesha3xiao",
        "title_198",
        "sitouzhongte",
        "title_14",
        "title_279",
        "title_66",
        "3hang",
        "title_132",
        "qinqi",
        "3tou",
        "shujinguang",
        "9xzt",
        "title_15",
        "title_74",
        "6xzt",
        "liuxiao18ma",
        "hllx",
        "wensha10ma",
        "9xiao12ma",
        "heibai3xiao",
        "title_48",
        "3zxt",
        "title_197",
        "juesha2xiao",
        "dxztt1",
        "qianhou_texiao",
        "sihangzhongte",
        "siji3",
        "siduanzhongte",
        "wuzhong5ma",
    }
    assert required_mode_ids_for_site_key("twbst528") == (
        50, 38, 44, 43, 58, 54, 57, 51, 56, 5, 47, 470, 472, 28, 20,
        42, 12, 26, 49, 15, 74, 46, 484, 8, 481, 60, 45, 48, 69,
        197, 473, 108, 219, 482, 61, 479, 485, 198, 483, 14, 279, 66, 53, 132,
    )
