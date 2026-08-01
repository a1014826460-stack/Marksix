# 台湾神预网前端预测模块设计

## 站点、接口与接入边界

- 站点：台湾神预网；域名：`www.twsyw.com`；`siteKey/siteId/webId`：`twsyw/13/13`。
- UI 基线：`frontend/public/vendor/Zz_felwi.am55689.com/index.html`；实际副本：`frontend/public/vendor/twsyw/index.html`。只向现有动态行的 `issue`、`content`、`result` 最小叶节点写值，保留供应商表格、标题、居中 `p`、导航和页脚。
- 开奖接口：`GET /api/sites/twsyw/draw?lottery_type={1|2|3}`。`kai.html` 的台湾彩(3)、澳门彩(2)、香港彩(1) tab 通过同源 `postMessage` 驱动父页；父页校验 origin 与 iframe source 后加载当前期号。
- 预测接口：`GET /api/sites/twsyw/prediction-modules?lottery_type={1|2|3}&history_limit=20`。读取 `data.canonical_modules[].{moduleKey,rows[]}`、`rows[].{issue,prediction.{text,tokens,groups,extra},result.{isOpened,code,zodiac,isCorrect,text}}`。共享 client 以 `lottery_type` 隔离缓存、in-flight 请求与回写。
- 图片预测资料：顶部“大家图片”原静态图已替换为 exact `pmtj_image`（mode 476）的首条 `prediction.imageUrl`；“九肖中特”前原静态图已替换为 exact `brainteaser`（mode 475）的首条 `prediction.imageUrl`。两个 `img[data-prediction-image]` 均是预先存在的最小目标节点，adapter 仅更新其 `src`/`hidden` 属性；无图片 URL 时隐藏图片，绝不回退到供应商图片。
- 结果规则：已开奖仅渲染最后一个特别号为 `开:号码生肖对/错`；未开奖为 `开:待开奖`；仅在正文叶节点用供应商既有黄色背景标记 `isCorrect === true`。无行时清空期号/结果并在正文显示 `暂无后端资料`。

## 静态槽位合同

所有 `data-prediction-section` 均采用三字段 renderer。每个动态 `tr` 恰有一个 `data-prediction-issue`、一个 `data-prediction-content` 和一个 `data-prediction-result`，没有 `content-secondary` 槽位；`#top_xiao_code` 另有 8 个既有开奖表头期号/结果叶节点。`frontend/test/twsyw-adapter-contract.mjs` 静态枚举下面 25 个区块，缺任何槽位、组数不符或 renderer 未定义即失败。

| section ID / 标题 | 组数 | moduleKey 与状态 | 命名 renderer / formatter / 命中规则 |
| --- | ---: | --- | --- |
| `top_xiao_code` 顶部八肖/码 | 8 x 7 | composite `9xzt` + `ma24` | `renderTopXiaoCode`；递进生肖/号码，使用来源模块的特别号结果。 |
| `fslx` 复式连肖 | 20 | approved replacement `title_14` | `renderFslx`；保留家禽、野兽两组，合并候选生肖命中特别号。 |
| `m24` 二十四码 | 20 | exact `ma24` | `renderM24`；24 个号码点分隔，特码号码包含即命中。 |
| `daxiao` 大小中特 | 20 | exact `daxiao` | `renderDaxiao`；大小标签，特码大小相等即命中。 |
| `jiaye` 家野中特 | 20 | exact `title_14` | `renderJiaye`；家禽/野兽结构，特码生肖落入两组即命中。 |
| `qixiao` 七肖中特 | 20 | approved replacement `9xzt` | `renderQixiao`；截取前 7 肖，按 `9xzt` 特别号生肖命中。 |
| `jiaye4xiao` 家野四肖 | 20 | approved replacement `sixiao_sima` | `renderJiaye4xiao`；明确标注“四肖四码资料”，前 4 肖命中。 |
| `gold6xiao` 黄金六肖 | 21 | approved composite `9xzt` + `pt1xiao` | `renderGold6xiao`；明确标注九肖资料前 6 肖与平特一肖资料，分别沿用来源命中。 |
| `pt1wei` 平特一尾 | 21 | approved replacement `title_66` | `renderPt1wei`；明确标注五尾资料，按尾数候选命中。 |
| `winner12` 12码中特 | 20 | approved replacement `selected_22_codes` | `renderWinner12`；明确标注精选22码并截取 12 码，按号码候选命中。 |
| `jiuxiao` 九肖中特 | 20 | exact `9xzt` | `renderJiuxiao`；9 肖，特码生肖包含即命中。 |
| `lianma` 复式连码 | 20 | approved composite `ma24` + `siduanzhongte` | `renderLianma`；明确标注 24码资料前 12 码与四段资料，分别沿用来源命中。 |
| `nannv` 男女中特 | 20 | approved replacement `title_5` | `renderNannv`；明确标注天地生肖资料，不假称男女分类，按其候选生肖命中。 |
| `danshuang` 单双中特 | 20 | approved composite `title_132` + `title_279` | `renderDanshuang`；明确标注合数单双与合数大小资料，使用来源规则。 |
| `dssx` 单双四肖 | 20 | exact `danshuang4xiao` | `renderDssx`；单双两组共 8 肖，特码生肖包含即命中。 |
| `hblvxiao` 红蓝绿肖 | 21 | approved composite `shuangbo` + `title_143` | `renderHblvxiao`；明确标注双波与一波资料，不假称红蓝绿肖，按波色命中。 |
| `santou` 精选三头 | 20 | exact `3tou` | `renderSantou`；3 个头数，特码头数包含即命中。 |
| `qiw` 7尾中特 | 20 | approved replacement `title_66` | `renderQiw`；明确标注五尾资料，不假称 7 尾，按尾数命中。 |
| `kill4xiao` 绝杀四肖 | 20 | approved replacement `sixiao_sima` | `renderKill4xiao`；明确标注四肖资料，不宣称绝杀，按包含规则。 |
| `kill3wei` 绝杀三尾 | 20 | approved replacement `title_66` | `renderKill3wei`；明确标注五尾资料前三项，不宣称绝杀，按包含规则。 |
| `chengyu` 成语平特 | 20 | approved replacement `qinqi` | `renderChengyu`；明确标注琴棋书画资料，不假称成语，按来源生肖规则。 |
| `shuangbo` 双波中特 | 20 | exact `shuangbo` | `renderShuangbo`；两个波色，特码波色包含即命中。 |
| `kill1tou` 绝杀一头 | 20 | approved replacement `3tou` | `renderKill1tou`；明确标注三头资料首项，不宣称绝杀，按包含规则。 |
| `five_no_hit` 平特5不中 | 20 | approved replacement `selected_22_codes` | `renderFiveNoHit`；明确标注五码资料，不宣称不中，按包含规则。 |
| `composite_kill` 综合绝杀 | 20 | approved composite `juesha3xiao` + `title_66` + `3tou` + `title_132` | `renderCompositeKill`；逐项标记“绝杀三肖、五尾资料、三头资料、合数单双”，每项保持来源机制与命中规则。 |

另有两个不属于历史三字段表格的图片预测模块：`[data-prediction-image-section="pmtj_image"]` 是单张图片槽位，对应 mode 476 / `pmtj_image` / 跑马图解；`[data-prediction-image-section="brainteaser"]` 是单张图片槽位，对应 mode 475 / `brainteaser` / 脑筋急转弯。它们由命名 `renderPredictionImage` renderer 使用当前彩种的最新 image URL，不与历史行混用。

## 原始 HTML 展示基线

入口 HTML 的普通历史行（`#fslx`，其他单列表格同构）直接保留如下结构；接入只对三个既有叶节点赋值：

```html
<tr>
  <td bgcolor="#ffffff" height="30"><p align="center"><span data-prediction-issue></span><span data-prediction-content></span><span data-prediction-result></span></p></td>
</tr>
```

三个叶节点由入口已有 CSS 设置为块级，供应商 `p align="center"` 保持正文、期号和结果居中；不使用整行 `textContent`、`innerHTML` 或新增 DOM。复杂区块仍复用这三个既有叶节点，但 formatter 输出具名资料段，避免原始 `|`、JSON 或供应商快照残留。

## 统一末尾图片模块

预测末块 `#composite_kill` 后、公共链接和供应商页脚前存在唯一的 `#legacy-attribute-anchor`。它固定包含 `#legacy-attribute-gallery` 及以下三个同源图片，顺序不变，均使用 `loading="lazy"` 与 `decoding="async"`：

1. `/uploads/image/20250322/1742580086567063.png`
2. `/uploads/image/20250322/1742580119746508.jpg`
3. `/uploads/image/20250322/1742580130762983.jpg`

`frontend/sites/twsyw/site.manifest.ts` 与 `frontend/sites/twsyw/site-adapter.ts` 均以该 anchor 为 footer 合同；浏览器合同滚动至此模块并检查每张图片 `complete && naturalWidth > 0`。

该站点页面内容容器 `.cgi-body` 的最大宽度为 800px；此前属性模块直接放在该容器外，却只设置图片 `width="100%"`，百分比因此按 iframe/视口计算，导致宽度超出站点版心。现仅对既有 `#legacy-attribute-anchor` 增加 `max-width:800px;margin-left:auto;margin-right:auto;box-sizing:border-box`，使其与供应商页面容器同宽，不新增 wrapper 或修改三张固定图片。静态合同检查该宽度约束，浏览器合同检查 computed max width 与实际宽度不超过 800px。

公共站点链接的宿主 `.white-box` 同样位于 `.cgi-body` 外；已应用相同的 800px 宽度合同并在浏览器测试中检查其 computed `max-width` 和实际宽度。以后凡是新增或替换到 `.cgi-body` 之后的可见模块，必须显式继承该 800px 版心并增加浏览器宽度断言，不能只依赖子元素或图片的 `width="100%"`。

## 验收合同

- 静态合同覆盖 25 个 section 的组数、所有三字段槽位、命名 renderer、禁止 DOM 构造 API、两张动态预测图的 mode/module 映射，以及固定图片模块的 ID、顺序、版心宽度与懒加载属性。
- 浏览器合同使用 18 个真实请求 moduleKey 的 fixture，依次点击 3、2、1、3，验证请求参数、期号、正文、特别号结果、缓存回切、命中状态、所有 section 不再误报“暂无后端资料”、无 console/page error 与图片自然宽度。
- 实际同源接口已验证 `lottery_type=3` 返回 `title_14` 等 canonical modules 的台湾彩历史数据；adapter 使用 `moduleKey` 和去重期号接入这些数据。
