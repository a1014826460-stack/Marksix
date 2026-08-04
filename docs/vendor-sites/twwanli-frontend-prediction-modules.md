# 台湾万利网前端预测模块设计

## 站点与接口

- 站点：台湾万利网；域名：`www.twwanli.com`；`siteKey/siteId/webId`：`twwanli/12/12`。
- 入口模板：`frontend/public/vendor/twwanli/index.html`，来自 `Zz_xgg3.cp567.cc`；保留原卡片、表格、标签、颜色、CSS 与供应商脚本顺序。
- 彩票仅为台湾彩（3）、澳门彩（2）、香港彩（1）。父页接收已验证 iframe 的 `lottery-change`，以同一 `lotteryType` 调用 `loadDraw` 与 `loadPredictions`。
- API：`GET /api/sites/twwanli/draw?lottery_type={1|2|3}`；`GET /api/sites/twwanli/prediction-modules?lottery_type={1|2|3}&history_limit=8`。预测响应的 `canonical_modules[]` 使用 `key` 与 `rows[]`；行读取 `issue`、`prediction.tokens/groups/extra`、`raw` 及特别号 `result`。每个模块按规范化 issue 去重。
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
| 吉凶六肖 `#jxzt` | approved mature fallback `6xzt` | 7；后端 `6xzt`（mode 46）提供六肖中特，以 `prediction.tokens` 前六项写入现有正文槽；保留供应商固定吉/凶生肖说明，不伪装为原始吉凶分类机制。 |
| 精准五行 `#jz5x` | approved mature fallback `3hang` | 7；后端五行类 `3hang`（mode 53）提供金木水火土中的三行，使用 `prediction.tokens` 的标签字段，以特别号所属五行包含为中；该卡不把它伪装成五行全选。 |
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
| 琴棋书画 `#qqsh` | exact `qinqi` | 8；首行分类固定标签不动；分类值和结果逐槽更新。 |
| 精华帖子 `#jhtz` | composite, four reviewed mappings | 6 个动态链接行：第 1/5 行 `pt1wei`（mode 54，尾数前 1 项）；第 2/6 行 `pt1xiao`（mode 56，生肖前 1 项）；第 3 行 `title_14`（mode 14，沿同源文章页映射，分别展示 `jia`/`ye` 字段）；第 4 行 `sitouzhongte`（mode 483，头数前 4 项）。每行恰好 1 个 issue/content/result 槽，特别号命中沿后端 mechanism 的 `result.isCorrect`。若对应模块或历史行缺失，值槽显示命名空态 `暂无后端资料`，不使用相似模块伪造。 |

### 2026-08-04 展示格式补充

- `#hsds`（`title_132`）：正文读取 `prediction.text`/`raw.content`，将后端 `合单`、`合双`展示为 `合数单`、`合数双`；期号与特别号结果仍分别写入既有 issue/result 叶节点。
- `#hsdx`（`title_279`）：正文完整保留 `合数大`、`合数小`，不得按 token 截断为“合”。
- `#qqsh`（`qinqi`）：首行固定说明由 `public.fixed_data.sign='四艺生肖'` 生成；每期正文使用 `raw.title` 的原始分类顺序，展示为 `琴棋书画→{画琴棋}`，结果只显示特别生肖和两位号码。
- `#msks`（`title_14`）：分类由同源 API 的 `raw.domestic_wild_category` 提供，该字段服务端根据 `public.fixed_data.sign='家禽|野兽'`（牛、马、羊、鸡、狗、猪 / 鼠、虎、兔、龙、蛇、猴）和特别生肖计算。已开奖期仅当该分类对应的本期 `jia` 或 `ye` 预测列表包含特别生肖时显示“准”；否则显示“错”。未来期固定为“待开奖 / ？00”，不推断命中。

合计 19 个可见预测区块（含 `jhtz`）：18 个原首页 exact/composite/replacement 加 1 个精华帖子 composite；最大可见完整历史组为 8，所有 live APIs 请求 8 个 distinct issues，绝不重复 issue。

### 精华帖子原始展示片段与合同

入口保留供应商的六个 `<a href="25.html|26.html|27.html|28.html|21.html|22.html">` 链接、`ul/li/font/span/b/u` 拓扑、行高、边框和背景图。原始片段的静态文本为 `181期:【平特一尾】`、`181期:【平特一肖】`、`181期:【独家精料】`、`181期:【四头必中】`、`180期:【平特一尾】`、`180期:【平特一肖】`；接入时仅移除这些固定期号/快照文字，在原 `<u>` 内声明并写入：

```html
<span data-prediction-issue></span><span data-prediction-content></span><span data-prediction-result></span>
```

静态合同：section ID `jhtz`；动态历史组 6；`issue=6`、`content=6`、`result=6`、`content-secondary=0`；实际 renderer 为 `renderFeaturedPosts`，格式化器为 `formatFeaturedPost`。行顺序和 moduleKey 由既有 `data-prediction-module` 明确绑定，不能按标题或 DOM 位置猜测。

### 精华帖子子页合同

六个供应商链接页保留原 `.post-list > h1 + p + 历史 p` 拓扑，移除 `2025181/2025180`、`???????` 与旧命中快照。每个 `p[data-prediction-row]` 恰好包含一个 issue/content/result 叶节点，由 `featured-post-data-adapter.js` 的 `renderArticle` 写入；三字段 computed display 为 block。首页每次切换彩种时只更新既有链接的 `lottery_type` 查询参数，子页据此调用同源预测接口。

| 页面 | moduleKey / 业务语义 | 历史组 / formatter / 命中 |
| --- | --- | --- |
| `21.html`、`25.html` | `pt1wei` mode 54，平特一肖尾 | 6 / 7；`raw.tail[0]` 或首个尾标签；特别号尾数命中。 |
| `22.html`、`26.html` | `pt1xiao` mode 56，平特一肖 | 6 / 7；首个生肖标签；特别号生肖命中。 |
| `27.html` | `title_14` mode 14，供应商同源“独家精料”文章页的已审核映射 | 7；分别格式化 `raw.jia` 与 `raw.ye`，不把大小/单双近似模块混入；特别号生肖落入合并集合时命中。 |
| `28.html` | `sitouzhongte` mode 483，四头必中 | 7；四个头数去掉显示后缀并以 `-` 分隔；特别号十位头数命中。 |

子页无对应模块/历史行时仅该行显示 `暂无后端资料`；未来期显示 `开:待开奖`，已开奖只显示特别号号码、生肖和对错。后端 dependency manifest 对六个可达页面逐页声明 endpoint/mode，避免只有首页授权而子页遗漏。

## 非预测与验证

- 原开奖 iframe、导航、公告、日历和广告属于静态非预测模块。供应商外链/外部图片保留在模板，但 adapter 不会激活或生成它们。
- 已批准将末尾供应商静态图集换为唯一的 `#legacy-attribute-anchor > #legacy-attribute-gallery`，图片固定为三个同源 `/uploads/image/...` URL。
- `jhtz` 与六个子页均共用同源预测接口；后端 `site_page_dependencies.py` 与 migration 25 授权 mode 54、483，profile 仍按 web_id=12 隔离生成三种彩票资料。
- 验收依次核对 profile 授权、web 12 三种彩票的 distinct issue rows、同源 API payload 与浏览器叶节点。浏览器点击三 tab 和缓存返回，检查选中彩票 marker、特别号结果、无 `2025181` / `????` / 原始 `|` / 跨彩种资料以及三张属性图顺序。
