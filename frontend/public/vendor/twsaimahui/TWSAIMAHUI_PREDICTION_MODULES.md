# twsaimahui 预测模块部署清单

本文档只基于 `twsaimahui` 前端页面的真实接口依赖整理，不沿用 `web=4` 的旧站模块列表。

## 1. 结论

`www.twsaimahui.com` 应使用站点专用预测模块蓝图，不能继续使用全站统一 `REQUIRED_SITE_PREDICTION_MODE_IDS`。

本次已在后端加入 `twsaimahui` 专用蓝图入口：

- 识别条件：
  - `domain=www.twsaimahui.com` 或 `domain=twsaimahui.com`
  - 或 `lottery_type_id=3` 且 `web_id=6`
- 生效位置：
  - `backend/src/domains/prediction/site_module_blueprints.py`
  - `backend/src/domains/prediction/generation_service.py`

## 2. 已确认应启用的模块

以下模块已确认与前端页面语义匹配，且当前系统存在可用 `mechanism_key`：

| 前端页面 | 接口 | 语义 | mode_id | mechanism_key |
|---|---|---:|---:|---|
| `049rccx.js` | `getRccx` | 肉草菜 | 3 | `rcca` |
| `043tiandi.js` / `075tiandi.js` | `getTdsx1` | 天地生肖 | 5 | `title_5` |
| `048hllx.js` | `getHllx` | 红蓝绿肖 | 8 | `hllx` |
| `035ma16.js` | `getCode?num=16` | 16码 | 9 | `title_9` |
| `051fyld.js` | `getFyld` | 风雨雷电 | 10 | `title_10` |
| `024santou.js` | `getTou?num=3` | 三头中特 | 12 | `3tou` |
| `004danshuang.js` | `getDsxiao` | 单双中特 | 15 | `title_15` |
| `015sha3w.js` | `getShaWei?num=3` | 绝杀三尾 | 20 | `juesha1wei` |
| `011jiepaoma.js` | `getXiaoma2?num=7` | 跑马图/解跑马 | 22 | `title_22` |
| `020nn4x.js` | `getNnnx` | 男女中特 | 24 | `title_24` |
| `052qqsh.js` | `qqsh` | 琴棋书画 | 26 | `qinqi` |
| `012liuxiao.js` | `getXiaoma2?num=6` | 精品六肖 | 27 | `title_27` |
| `071ds.js` | `danshuang` | 单双 | 28 | `danshuangtema` |
| `003ds4w.js` | `getDsWei` | 单双各4尾 | 30 | `title_30` |
| `060ds4x.js` | `getDsnx` | 单双各4肖 | 31 | `danshuang4xiao` |
| `066chengyupx.js` | `getCypt` | 成语平特 | 39 | `title_39` |
| `018sha1tou.js` | `getShatou` | 绝杀1头 | 41 | `title_41` |
| `022pt1w.js` | `getPtWei` | 平特1尾 | 54 | `pt1wei` |
| `065yiziptx.js` / `074ptyx.js` | `getPingte?num=1` | 平特1肖 | 56 | `pt1xiao` |
| `067sanzipw.js` | `getPingte?num=3` | 平特三肖 | 470 | `pt3xiao` |
| `002daxiao.js` | `getDxzt` | 大小中特 | 57 | `daxiao` |
| `054sbanbo.js` | `getShaBanbo` | 绝杀半波 | 58 | `jueshabanbo` |
| `050siji.js` | `getSjsx` | 四季生肖 | 61 | `siji3` |
| `029yizixuanji.js` 旧文档写 `getYzxj`，语义上对应一字玄机 | 一字玄机文本 | 295 | `title_295` |
| `zx.js` 对应推荐位，不属于预测模块 | - | - | - | - |

以下是 `getZhongte` 系列已确认拆分结果：

| 前端页面 | 接口参数 | 正确语义 | mode_id | mechanism_key |
|---|---|---:|---:|---|
| `031wuxiao.js` | `getZhongte?num=3` | 三肖中特 | 69 | `3zxt` |
| `072liangtou.js` | `getTou?num=2` | 两头中特 | 471 | `liangtouzxt` |
| `073sixiao.js` | `getZhongte?num=4` | 四肖中特 | 47 | `title_47` |
| `030lflx.js` | `getZhongte?num=4` | 四肖中特 | 47 | `title_47` |
| `042ycwx.js` | `getZhongte?num=5` | 五肖中特 | 48 | `title_48` |
| `047liuxiao.js` | `getZhongte?num=6` | 六肖中特 | 46 | `6xzt` |
| `062linbei6x.js` | `getZhongte?num=6` | 六肖中特 | 46 | `6xzt` |
| `014jiuxiao.js` | `getZhongte?num=9` | 九肖中特 | 49 | `9xzt` |

以下是站点蓝图中已纳入、当前系统已有机制但本文未逐页展开的模块：

- `45 -> heibai3xiao`
- `50 -> yijuzhenyan`
- `51 -> 4xiao8ma`
- `62 -> yqjs`
- `63 -> title_63`
- `88 -> title_88`
- `108 -> dxztt1`
- `116 -> title_116`
- `123 -> title_123`
- `132 -> title_132`
- `141 -> title_141`
- `143 -> title_143`
- `144 -> title_144`
- `145 -> title_145`
- `147 -> title_147`
- `149 -> title_149`
- `151 -> title_151`
- `152 -> title_152`
- `155 -> title_155`
- `157 -> title_157`
- `158 -> title_158`
- `159 -> title_159`
- `197 -> title_197`
- `244 -> title_244`
- `246 -> title_246`
- `251 -> title_251`
- `336 -> title_336`

## 3. 阻塞项

以下页面不能假装“已支持”：

| 前端页面 | 接口 | 当前问题 | 处理状态 |
|---|---|---|---|
| `019liubuzhong.js` | `/api/kaijiang/rd70i73lziizczak/0gmqnw/1` | 前端要求 `u6_code`，但当前本地核对中 `mode_payload_333` 实际是“天地4肖”，不是六不中数据 | `blocked_data_source` |

说明：

- 这不是“少同步一个模块”。
- 这是底层 payload 表语义与前端页面不一致。
- 已补齐的新玩法不再属于阻塞项：
- `067sanzipw.js` -> `getPingte?num=3` -> `470 / pt3xiao`
- `072liangtou.js` -> `getTou?num=2` -> `471 / liangtouzxt`
- `057s1x.js` -> `getShaXiao?num=1` -> `472 / juesha1xiao`
- `058s2x.js` -> `getShaXiao?num=2` -> `473 / juesha2xiao`

## 4. 后端检查方法

打印站点实际启用蓝图：

```powershell
python backend/scripts/print_site_prediction_blueprint.py --db-path "<DATABASE_URL>" --site-id 6
```

输出会包含：

- `enabled_modules`
- `blocked_frontend_items`

## 5. 新站点复用方式

如果后续要新建一个和 `twsaimahui` 类似的旧前端站点，不要直接复制旧站模块列表。应按以下顺序做：

1. 先整理前端真实页面与接口清单。
2. 再把每个页面映射到正确 `mode_id / mechanism_key`。
3. 对于同一路径多玩法的接口，按页面语义拆开。
4. 对于缺少底层 payload 支撑的页面，单独列为阻塞项，不要硬塞到站点模块蓝图。
5. 在 `backend/src/domains/prediction/site_module_blueprints.py` 中新增站点专用蓝图。

## 6. 备注

本次蓝图的目标是“按前端真实依赖部署正确模块”，不是把旧环境模块原样搬过来。
