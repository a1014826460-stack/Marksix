# TWCF888 Prediction Modules

## 2026-06-06 Update (batch 2)

- 批量转 live_backed：
  - `2287 绝杀一行 -> mode 98`
  - `2289 绝杀二尾 -> mode 95`
  - `2290 绝杀一波 -> mode 143`
  - `3051 稳中七肖 -> mode 100`
  - `3053 内幕资料 -> mode 198`
  - `7636 八肖来财 -> mode 180`
  - `7637 特码单双 -> 复合 mode 28(单双) + mode 57(大小)`
- 后端 blocked 清单中补转 live：
  - `3肖防3码 -> mode 226`
  - `18码中特 -> mode 122`
  - `双波10码 -> mode 224`
- 当前 `twcf888` required mode ids 更新为：

```text
2, 5, 12, 14, 15, 20, 26, 27, 28, 38, 41, 42, 43, 45, 47, 49, 50, 53, 54, 57, 66, 69, 74, 88, 95, 98, 100, 103, 122, 132, 143, 180, 198, 224, 226, 279, 470, 472, 473, 482, 483
```

- 当前仍保持 `blocked_requires_backend_work`
  - `广东5兄弟`
- 当前仍保持 `snapshot_only`
  - `官方图库`

站点信息:
- `site_key=twcf888`
- `site_id=8`
- `web_id=8`
- `lottery_type=3`
- `domain=www.twcf888.com`

模块状态定义:
- `live_backed`: 已确认接入共享预测模块
- `snapshot_only`: 仅保留原站静态快照，不接实时预测
- `blocked_requires_backend_work`: 语义已识别，但后端机制或 mode_id 尚未确认

## v2 Live-Backed Mode IDs

固定 required mode ids:

```text
2, 5, 12, 14, 15, 20, 26, 27, 28, 38, 41, 42, 43, 45, 47, 49, 50, 53, 54, 57, 66, 69, 74, 88, 95, 98, 100, 103, 122, 132, 143, 180, 198, 224, 226, 279, 470, 472, 473, 482, 483
```

映射表:

| 前端模块 | mode_id | 状态 |
| --- | ---: | --- |
| 天地生肖 / 天地两肖 | 5 | live_backed |
| 三头必中 / 3头中特 | 12 | live_backed |
| 家禽野兽 / 千秋霸业 | 14 | live_backed |
| 单双公式 / 单双两肖 | 15 | live_backed |
| 绝杀一尾 | 20 | live_backed |
| 高级六肖 | 27 | live_backed |
| 琴棋书画 | 26 | live_backed |
| 单双中特 | 28 | live_backed |
| 双波中特 / 原创双波 | 38 | live_backed |
| 必杀1头 / 绝杀一头 | 41 | live_backed |
| 绝杀三肖 | 42 | live_backed |
| 平特两肖 | 43 | live_backed |
| 黑白中特 | 45 | live_backed |
| 稳料四肖中 / 四肖中特 | 47 | live_backed |
| 必中九肖 / 特码九肖 | 49 | live_backed |
| 一句中特 | 50 | live_backed |
| 精准五行 / 三行中特 | 53 | live_backed |
| 平特一尾 | 54 | live_backed |
| 特码大小 | 57 | live_backed |
| 5尾中特 | 66 | live_backed |
| 三肖中特 | 69 | live_backed |
| 精准7尾 | 74 | live_backed |
| 准杀7码 | 88 | live_backed |
| 绝杀二尾 | 95 | live_backed |
| 绝杀一行 | 98 | live_backed |
| 稳中七肖 | 100 | live_backed |
| 平特一肖 | 103 | live_backed |
| 18码中特 | 122 | live_backed |
| 合数单双 | 132 | live_backed |
| 一波中特 / 绝杀一波 | 143 | live_backed |
| 八肖来财 | 180 | live_backed |
| 逢买必中 / 内幕资料 | 198 | live_backed |
| 双波10码 | 224 | live_backed |
| 3肖防3码 | 226 | live_backed |
| 合数大小 | 279 | live_backed |
| 平特三肖连 | 470 | live_backed |
| 绝杀一肖 / 绝禁一肖 | 472 | live_backed |
| 绝杀二肖 / 必杀两肖 / 绝版杀肖 | 473 | live_backed |
| 4行4头 | 482 + 483 | live_backed |
| 四行中特 | 482 | live_backed |
| 四头必中 | 483 | live_backed |
| 特码单双 | 28 + 57 | live_backed (复合) |
| 6尾中特 | 2 | live_backed |

说明:
- `7637 特码单双` 使用复合渲染: `mode 28(单双) + mode 57(大小)`.
- `7623 4行4头` 使用复合渲染: `mode 482(四行中特) + mode 483(四头必中)`.
- `黑白中特(mode 45)` 展示规则固定为: 未开奖默认显示白肖；已开奖命中黑肖就显示黑肖，命中白肖就显示白肖.

## Snapshot-Only Items

| 模块 | 说明 |
| --- | --- |
| 官方图库 | 非预测模块，继续允许静态快照访问 |

## Blocked Items

| 模块 | 状态 |
| --- | --- |
| 广东5兄弟 | blocked_requires_backend_work |

规则:
- blocked 项不允许假映射到别的 mode_id.
- blocked 项首页与详情页都不能伪造 live 数据.
- 后续若要 live 化，必须先补后端机制或确认精确语义，再从 blocked 清单移入 required mode ids.
