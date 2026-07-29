# twbst528 Homepage Complete Dynamic Design

## Scope

The supplied homepage contains 51 visible prediction sections. Completion is
defined by the HTML inventory, not by the subset initially named in a request.
Every prediction section must either have a backend mapping and existing-DOM
renderer or be identified as a static non-prediction legend.

## Mapping

| Vendor section | Backend mechanism | DOM topology |
| --- | --- | --- |
| 高手论坛 | latest row across enabled modules | existing `#tiezi li` text prefix |
| 代号生肖 | `9xzt` | three-column history |
| 杀肖杀码 | `juesha3xiao` | three-column history |
| 独家公式 | `title_15` | composite line groups |
| 六尾出特 / 梭哈⑦尾 | `title_74` | three-column history |
| 六肖六码 | `6xzt` | paired header/detail cards |
| 一肖一码 | `pt1xiao` | six tables with staged rows |
| 码友来料参考 | `3zxt`, `title_47`, `6xzt` | three composite cells |
| 六肖十八码 / 18码中特 | `liuxiao18ma` | paired two-line cards |
| 红蓝绿肖 | `hllx` | legend plus three-column history |
| 五行来料 | `3hang` | three-column history |
| 绝杀⑩码 | `wensha10ma` | three-column history |
| ⑥肖12码 | `9xiao12ma` | paired two-line cards |
| 黑白三肖 | `heibai3xiao` / legacy `title_45` | legend plus three-column history |
| 阴阳⑧码中特 / 8肖16码 | `title_48` | legend/history and paired cards |
| ③肖防③码 | `pt3xiao`, `wuzhong5ma` | paired composite cards |
| 三期计划 | `shuangbo`, `danshuangtema`, `pt1xiao`, `3zxt` | composite line groups |
| ⑤肖⑩码 | `4xiao8ma` | paired two-line cards |
| 稳中单双 | `danshuangtema` | three-column history |
| 综合绝杀 | `juesha2xiao`, `juesha1wei`, `3tou`, `3hang` | four composite categories |
| 大小+①头 | `dxztt1` | three-column history |
| 四肖八码 | `4xiao8ma` | legend plus paired cards |
| 日夜特肖 / 左右中特 / 前后中特 | `qianhou_texiao` | legend plus three-column history |
| 七尾四行 | `title_74`, `sihangzhongte` | composite three-column history |
| 四季九肖 | `siji3`, `9xzt` | legend plus composite history |

Existing first-wave mappings remain unchanged. All renderers update existing
text nodes and retained `font`, `span`, and `br` slots only.

## Result And Empty States

Opened history displays the special ball only as `开:号码生肖对/错`. Pending
history displays `开:待开奖`. A newly authorized mechanism has no fabricated
history: only future predictions generated before draw are shown; unused
supplier rows become `暂无后端资料` until genuine history accumulates.

## Regression Gate

The browser contract supplies seven-value result CSV fields, switches all
three lottery tabs, checks forum term/region updates, and inventories every
newly mapped section. It fails on `233期`, `323期`, `????`, or an unchanged
regional prefix.
