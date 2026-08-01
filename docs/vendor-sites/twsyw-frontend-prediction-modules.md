# 台湾神预网前端预测模块设计

## 站点与接口

- 站点：台湾神预网；域名：`www.twsyw.com`；`siteKey/siteId/webId`：`twsyw/13/13`。
- 入口模板：`frontend/public/vendor/twsyw/index.html`，来自 `Zz_xgg3.cp567.cc`；保留原卡片、表格、标签、颜色、CSS 与供应商脚本顺序。
- 彩票仅为台湾彩（3）、澳门彩（2）、香港彩（1）。父页接收已验证 iframe 的 `lottery-change`，以同一 `lotteryType` 调用 `loadDraw` 与 `loadPredictions`。
- API：`GET /api/sites/twsyw/draw?lottery_type={1|2|3}`；`GET /api/sites/twsyw/prediction-modules?lottery_type={1|2|3}&history_limit=7`。预测响应的 `canonical_modules[]` 使用 `key` 与 `rows[]`；行读取 `issue`、`prediction.tokens/groups/extra`、`raw` 及特别号 `result`。每个模块按规范化 issue 去重。
- 结果只显示特别号：已开 `开:01鼠对/错`，未开 `开:待开奖`。适配器不创建、删除、移动或样式化 DOM，只写入预声明的最小叶节点。

## DOM 槽位合同与清单

所有单行历史卡片预声明 `data-prediction-issue`、`data-prediction-content`、`data-prediction-result`；三节点块级显示。表格的三列布局保持原状并各自写入已有单元格。无资料只向值槽写 `暂无后端资料`，同时清除供应商期号、`????`、结果文字及黄色命中标记。

| TITLE / 锚点 | 状态，moduleKey | 历史组数与格式 / 命中规则 |
| --- | --- | --- |
| 买啥开啥 `#msks` | approved replacement `title_14` | 6；`期号 / 家禽或野兽 / 特别号结果`；分类含特别肖为中。 |
| 绝杀三肖 `#wsxx` | exact `juesha3xiao` | 6；3 肖；特别肖不在预测集为中。 |
| 一肖一码 `#yxym table.yxym` | composite `9xzt` + `selected_22_codes` + `shuangbo` | 6 个表组；一码、三码、五码、七码取号码前 N 项，肖行取 9 肖前 N 项，波色取双波；原三列逐槽更新。 |
| 稳料四肖中 `#wl4x` | exact `sixiao_sima` | 6；四肖，特别肖包含为中。 |
| 大小中特 `#dxzt` | exact `daxiao` | 6；大数/小数，特别号大小匹配为中。 |
| 吉凶六肖 `#jxzt` | unavailable | 7；没有同义成熟机制，逐行空态。 |
| 精准五行 `#jz5x` | unavailable | 7；没有同义成熟机制，逐行空态。 |
| 五尾中特 `#5wzt` | exact `title_66` | 7；五尾，特别号尾数包含为中。 |
| 精选24码 `#jx24m` | exact `ma24` | 6；24 个号码分两行保留在原值槽，特别号包含为中。 |
| 单双各四肖 `#dssx` | exact `danshuang4xiao` | 6；保留单双两组槽，特别肖属于对应组为中。 |
| 四段中特 `#sdzt` | exact `siduanzhongte` | 7；四段，特别号所属段匹配为中。 |
| 一波中特 `#ybzt` | exact `title_143` | 7；波色匹配为中。 |
| 天地生肖 `#tdsx` | exact `title_5` | 6；首行天肖/地肖固定标签不动；天地组和两肖写值槽。 |
| 三头中特 `#3tzt` | exact `3tou` | 7；三头，特别号头数包含为中。 |
| 合数大小 `#hsdx` | exact `title_279` | 7；合数大/小，特别号匹配为中。 |
| 平特一肖（无 ID 标题表） | exact `pt1xiao` | 6；一肖，特别肖匹配为中。 |
| 合数单双 `#hsds` | exact `title_132` | 7；合单/合双，特别号匹配为中。 |
| 琴棋书画 `#qqsh` | exact `qinqi` | 7；首行分类固定标签不动；分类值和结果逐槽更新。 |

合计 18 个可见预测区块：16 个 exact/composite/replacement，2 个 unavailable；最大可见完整历史组为 7，所有 live APIs 请求 7 个 distinct issues，绝不重复 issue。

## 非预测与验证

- 原开奖 iframe、导航、公告、日历和广告属于静态非预测模块。供应商外链/外部图片保留在模板，但 adapter 不会激活或生成它们。
- 已批准将末尾供应商静态图集换为唯一的 `#legacy-attribute-anchor > #legacy-attribute-gallery`，图片固定为三个同源 `/uploads/image/...` URL。
- 验收依次核对 profile 授权、web 13 三种彩票的 distinct issue rows、同源 API payload 与浏览器叶节点。浏览器点击三 tab 和缓存返回，检查选中彩票 marker、特别号结果、无 `2025181` / `????` / 原始 `|` / 跨彩种资料以及三张属性图顺序。
