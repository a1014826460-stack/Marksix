# 台湾神算子（twssz）接入记录

## 身份与入口

- `site_key`: `twssz`
- `site_id` / `web_id`: `9`
- 名称：台湾神算子
- 路由：`/twssz`
- 原始入口：`frontend/public/vendor/twssz/index.html`
- 彩种：台湾彩（`lottery_type=3`）

## 原始包审计结论

原包仅包含 `index.html`、`kai.html`、jQuery 和 Cloudflare RUM 脚本；未发现
`fetch`、`$.ajax`、预测 API URL、预测模块 ID 或后端请求签名。`index.html` 的
“A级猛料大公开”从第 185 行起为静态 HTML，因此不存在可以沿用的原始预测模块 ID。

`kai.html` 原来指向 `/kj1/*.html` 和随机外域开奖 iframe。已保持原有标签、Tab、CSS
和交互结构，但将其内容源改为同源
`/vendor/shengshi8800/kj/local.html?lottery_type=<id>`，使开奖数据由统一后端接口加载。

## 后端替代映射

以下为语义近似的、已注册后端 mode，不是对原包 ID 的推断：

| 原始静态栏位 | 后端机制 | mode_id | 说明 |
| --- | --- | ---: | --- |
| 七肖 | `7xiao7ma` | 44 | 7肖7码，最接近的现成七肖机制 |
| 四肖 | `sixiao_sima` | 78 | 四肖四码 |
| 10码 | `wensha10ma` | 481 | 稳杀10码，号码数量相同，语义为替代 |
| 三肖 | `3zxt` | 69 | 3肖中特 |
| 8码 | `4xiao8ma` | 51 | 4肖8码 |
| 二肖 | `pt2xiao` | 43 | 平特2肖 |
| 5码 | `title_66` | 66 | 5尾中特；号码与尾数语义不完全等价 |

这些 mode 由 `site_blueprint_profiles.twssz` 授权。部署时执行版本化迁移会创建
`managed_sites(id=9, web_id=9)` 并同步对应 `site_prediction_modules`；不需要手工插入数据库。

## 逐表动态映射

以下映射均只写入既有文本节点；不会新增、删除、移动 DOM 或修改 CSS。没有原始模块 ID
的资料均采用最相近的既有后端机制，属于明确的替代而非对原站机制的推断。

| 原始定位点 / 静态栏位 | 后端机制（mode） | 写入范围 |
| --- | --- | --- |
| `#top_15` A级猛料：七肖、四肖、10码、三肖、8码、二肖、5码 | `7xiao7ma` (44)、`sixiao_sima` (78)、`wensha10ma` (481)、`3zxt` (69)、`4xiao8ma` (51)、`pt2xiao` (43)、`title_66` (66) | 首个表的既有期号和 `font` 文本节点 |
| `#top_14` 2组连肖连尾 | `title_5` (5)、`title_66` (66)、`pt2xiao` (43) | 既有期号、号码/生肖文本节点 |
| `#top_9` 精选24码 | `ma24` (34) | 既有号码文本节点 |
| `#top_13` 极品大小 | `daxiao` (57) | 既有期号和内容文本节点 |
| 两个 `#top_8`：家野二肖、三头中特 | `title_14` (14)、`3tou` (12) | 既有期号和内容文本节点 |
| `#top_1` 特料专区 | 绝杀一尾、7尾、单双、绝杀三肖、8肖、两肖、9肖、一肖、双波、三肖、5尾、合数大小、四头、家野等最近模块 | “已公开”既有文本节点 |
| `#top_3` 平特一尾 | `pt1wei` (54) | 既有期号和尾数文本节点 |
| `#top_11` 8肖16码 | `9xiao12ma` (60) | 既有期号和号码文本节点 |
| `#top_10` 内幕⑤不中；`#top_4` 绝杀7码 | `wensha10ma` (481) | 既有号码文本节点 |
| `#top_2` 综合资料 | `6xzt` (46)、`3hang` (53)、`shuangbo` (38)、`title_132` (132)、`pt3xiao` (470)、`title_66` (66)、`title_279` (279)、`sitouzhongte` (483)、`title_14` (14) | “已公开”既有文本节点 |
| `#top_6` 双波10码 | `shuangbo` (38) | 既有期号和波色/号码文本节点 |
| 第三个 `#top_8` 四肖中特 | `sixiao_sima` (78) | 既有期号和生肖文本节点 |
| `#top_12` 一头一码；`#top_7` 三期计划 | `3tou` (12)；`danshuangtema` (28)、`shuangbo` (38) | 既有期号和内容文本节点 |

开奖 iframe 固定为且仅为台湾彩（`lottery_type=3`）、澳门彩（`2`）和香港彩（`1`）。

## 原始静态历史导入

原始“A级猛料大公开”表中的 204 至 197 期已在 migration 5 导入到七个对应的
`created.mode_payload_*` 表，每个模块 8 条、合计 56 条。内容逐项沿用原始静态表的
七肖、四肖、10码、三肖、8码、二肖和5码，不生成或猜测任何开奖结果。

原包没有年份、开奖日期或可验证的开奖记录，因此导入行固定为 `year="0"`、
`term="197".."204"`、`type="3"`、`web=web_id="9"`。`year=0` 是供应商静态
历史标识，不是实际彩票年份；公开 API 会将其作为未开奖历史返回，避免把原始素材
误标为真实开奖或命中结果。

## 页面与数据边界

- 共享客户端：`/vendor/_shared/lottery-site-data-client.js`，统一请求、去重、session 缓存和 stale 回退。
- 站点适配器：`frontend/public/vendor/twssz/site-data-adapter.js`，仅预加载同源 draw / prediction API 并发出 `site-data:ready`。
- 既有预测定位点：`#top_15`；`site-data-adapter.js` 仅更新第一个“A级猛料大公开”表内既有 `font` / `span` 文本节点，不创建、删除、移动节点，也不修改样式或表格结构。后端无历史行时保留原始静态内容。
- 映射：七肖 <- `7xiao7ma`，四肖 <- `sixiao_sima`，10码 <- `wensha10ma`，三肖 <- `3zxt`，8码 <- `4xiao8ma`，二肖 <- `pt2xiao`，五码 <- `title_66`。页面保留原有“⑤码”文案；历史导入记录按原始 5 个号码展示。`title_66` 的动态生成语义为 5 尾，属于既有后端替代能力，不能把它误称为原始 5 码机制。
- 原始导航、顶部悬停脚本、图片和静态资料均保留。
- 原始包中所有外部跳转、外部延迟加载资源及 Cloudflare RUM 脚本已移除或替换为本地空目标；`pnpm site:validate --site-key twssz --strict` 必须通过。
