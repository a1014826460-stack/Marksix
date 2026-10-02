/**
 * twbst528 六项改造契约（源码级）
 * ---------------------------------------------------------------------------
 * 覆盖本轮改动中「可从源码稳定断言」的部分：
 *   1. 标黄口径：命中型 / 绝杀型两张规则表；**判定「错」的期次零黄底（S3）**，
 *      排除型一律零黄底；头/尾候选的单双后缀必须参与命中判定；
 *   2. 展示文本里的候选回推必须能把连写生肖（`天肖+龙狗`、`猪鸡龙猴蛇鼠马狗`）拆成单字，
 *      否则命中项永远匹配不到（曾导致 `天地+②肖` 标黄回归）；
 *   3. `writeCell` 必须能在模板**没有**预埋黄底 span 时自建 marker
 *      （老实现只依赖预埋 span，导致琴棋书画/家野中特等板块永远标不出黄底）；
 *   4. 改期号配对：不得再出现按行号取行的写法（`data[index]` 等），必须走 makeRowResolver；
 *   5. 第 4/5/6 项的语义与改名；
 *   6. 第 2 项「码友来料参考」每期必须带开奖与判定。
 *
 * 运行：node frontend/test/twbst528-display-contract.mjs
 */
import fs from "node:fs"

const ROOT = "frontend/public/vendor/twbst528"
const ADAPTER = `${ROOT}/site-data-adapter.js`
const INDEX = `${ROOT}/index.html`
const INDEX1 = `${ROOT}/index1.html`

const adapter = fs.readFileSync(ADAPTER, "utf8")
const index = fs.readFileSync(INDEX, "utf8")
const index1 = fs.readFileSync(INDEX1, "utf8")

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

// ── 1. 标黄规则表 ─────────────────────────────────────────────────────────
for (const token of [
  "var HIT_RULE_KEYS", "var KILL_RULE_KEYS", "function highlightRuleFor",
  "function highlightTokens", "function parityHit", "function allowMarkedTokens",
]) {
  assert(adapter.includes(token), `标黄引擎缺少 ${token}`)
}
for (const key of ["juesha1xiao", "juesha2xiao", "juesha3xiao", "wensha10ma", "shaliangbanbo", "shujinguang"]) {
  assert(
    new RegExp(`KILL_RULE_KEYS[\\s\\S]{0,400}"${key}"`).test(adapter),
    `绝杀型规则表必须包含 ${key}`,
  )
}
// 绝杀一尾（juesha1wei）是排除型（后端 excludes_hit）：开奖号码落在被杀尾数里 = 错。
// 曾误列进命中型，导致「错」的那一期把开奖值当命中项标黄。
const hitBlock = /var HIT_RULE_KEYS = \[([\s\S]*?)\];/.exec(adapter)
const killBlock = /var KILL_RULE_KEYS = \[([\s\S]*?)\];/.exec(adapter)
assert(hitBlock, "必须能定位 HIT_RULE_KEYS 数组字面量")
assert(killBlock, "必须能定位 KILL_RULE_KEYS 数组字面量")
assert(
  killBlock[1].includes('"juesha1wei"'),
  "juesha1wei（绝杀一尾）必须归入排除型",
)
assert(
  !hitBlock[1].includes('"juesha1wei"'),
  "juesha1wei 不得再留在命中型规则表里",
)

// ── 1b. S3 硬门槛：判定为「错」的整期零黄底 ───────────────────────────────
// 这是线上 twbst528 5 处 R3 的根因：候选串里常常同时列着本期**没有**命中的另一组
// （红蓝绿肖两组、头数单双五个组合、绝杀类被杀集合…），只按「值出现在候选串里」
// 就标黄，会让判定「错」的行带黄底。
assert(
  /if \(row\.result\.isCorrect === false\) return \[\];/.test(adapter),
  "highlightTokens 必须先把判定为「错」的期次整体拦掉（S3：错行零黄底）",
)
// 排除型（杀号）没有「可高亮的命中项」：杀中时开奖值不在被杀集合里，
// 杀失败时开奖值确实落在被杀集合里 —— 但 S3 明令禁止标黄。故一律返回空。
assert(
  /rule === "kill"[\s\S]{0,400}?return \[\];/.test(adapter),
  "排除型必须一律零黄底（杀中 / 杀失败都不给标记）",
)
assert(
  !/isCorrect === false[\s\S]{0,80}drawnTokens\(/.test(adapter),
  "不得再按「杀失败（isCorrect === false）就标黄开奖值」标黄（S3 违规）",
)
assert(
  !/function drawnTokens/.test(adapter),
  "drawnTokens()（专为「杀失败标黄开奖值」而生）必须删除，避免被重新接回高亮链路",
)
// 命中型：只标黄「真正被开出的那一项」，且**不依赖 result.isCorrect**
// （部分模块该字段为空：六肖十八码 / ⑤肖⑩码；以它为门槛会导致整块永远标不出黄底）。
assert(
  /命中型的候选是\*\*候选集合\*\*[\s\S]{0,400}row\.result\.code/.test(adapter),
  "命中型必须按「开奖值落在候选集合里」判定，而不是依赖 result.isCorrect",
)

// ── 2. 连写生肖必须能拆成单字 ─────────────────────────────────────────────
assert(
  adapter.includes("function splitCandidateToken"),
  "缺少 splitCandidateToken：连写生肖（龙狗）必须拆成单字，否则命中项匹配不到",
)
assert(
  /var ZODIAC_CHARS = "鼠牛虎兔龙蛇马羊猴鸡狗猪"/.test(adapter),
  "splitCandidateToken 必须以内置生肖表判断是否为纯生肖串",
)
assert(
  /allZodiac \? chars : \[token\]/.test(adapter),
  "只有整串都是生肖字时才拆单字（`4头单`/`琴棋书` 必须保持原样）",
)

// ── 3. writeCell 必须自建 marker（不能依赖模板预埋） ──────────────────────
assert(
  /function writeCell[\s\S]{0,1600}var marker = doc\.createElement\("span"\)/.test(adapter),
  "writeCell 必须自建黄底 marker（模板只在部分板块预埋 span，依赖它会让这些板块永远标不出黄底）",
)
assert(
  /marker\.style\.backgroundColor = "#FFFF00"/.test(adapter),
  "自建的 marker 必须设置 #FFFF00 背景",
)
// 旧实现的三段式还原会因残留 marker 截断整串文本，必须已经移除。
assert(
  !/var markerIndex = leaves\.indexOf\(markerLeaf\)/.test(adapter),
  "writeCell 不得再用「markerLeaf + leaves[0] + suffix」的三段式还原（会把整串文本截断）",
)

// ── 4. 改期号配对：不得再按行号取行 ───────────────────────────────────────
for (const token of ["function templateTermKey", "function rowTermKey", "function makeRowResolver"]) {
  assert(adapter.includes(token), `按期号配对缺少 ${token}`)
}
const indexPairingPatterns = [
  /data\[index\]/,
  /data\[issueIndex\]/,
  /tailRows\[index\]/,
  /lineRows\[index\]/,
  /zodiacRows\[index\]/,
  /codeRows\[index\]/,
  /seasonRows\[index\]/,
]
for (const pattern of indexPairingPatterns) {
  assert(
    !pattern.test(adapter),
    `仍存在按行号取行的写法 ${pattern} —— 必须改成 makeRowResolver（按期号配对）`,
  )
}
// makeRowResolver 的兜底才允许 rows[index]
assert(
  /function makeRowResolver[\s\S]{0,400}return rows\[index\] \|\| null/.test(adapter),
  "makeRowResolver 必须保留「模板读不到期号时按行号」的兜底",
)

// ── 5. 第 4/5/6 项语义与改名 ──────────────────────────────────────────────
assert(adapter.includes("function siyiTriple"), "第 4 项缺少 siyiTriple")
assert(adapter.includes("function siyiHitArts"), "第 4 项缺少 siyiHitArts（标黄要落在艺名上）")
assert(
  /SIYI_ZODIAC = \{[\s\S]{0,300}"琴": \["兔", "蛇", "鸡"\]/.test(adapter),
  "四艺生肖映射必须以 fixed_data 为准：琴=兔蛇鸡 / 棋=鼠牛狗 / 书=虎龙马 / 画=羊猴猪",
)
assert(adapter.includes("function groupLabelFor"), "第 5/6 项缺少 groupLabelFor")
assert(
  /DANXIAO_GROUP = \{ "胆大": \["牛", "虎", "马", "猴", "狗", "猪"\]/.test(adapter),
  "胆大生肖必须是 牛虎马猴狗猪",
)
assert(
  /XIONGJI_GROUP = \{[\s\S]{0,80}"吉美肖": \["兔", "龙", "蛇", "马", "羊", "鸡"\]/.test(adapter),
  "吉美肖必须是 兔龙蛇马羊鸡",
)
// 分组归属按多数，而不是「第一个命中的分组」
assert(
  /var bestScore = -1;/.test(adapter) && /score \+= zodiacs\.length - index/.test(adapter),
  "groupLabelFor 必须按多数归属（候选跨两组时不能一律取第一个分组）",
)

const RENAMES = [
  [index, "台湾百事通【胆大胆小】", "台湾百事通【四肖中特】"],
  [index, "台湾百事通【吉美丑凶】", "台湾百事通【三肖六码】"],
  [index1, "澳门新新彩【胆大胆小】", "澳门新新彩【四肖中特】"],
  [index1, "澳门新新彩【吉美丑凶】", "澳门新新彩【三肖六码】"],
  // 2026-09-30：【八肖来袭】→【七肖来袭】（数据源是 mode 44「7肖7码」，标题与玩法对齐）。
  [index, "台湾百事通【七肖来袭】", "台湾百事通【八肖来袭】"],
  [index1, "澳门新新彩【七肖来袭】", "澳门新新彩【八肖来袭】"],
]
for (const [html, newTitle, oldTitle] of RENAMES) {
  assert(html.includes(`<div class="pb-tit tzlb-tit">${newTitle}</div>`), `板块标题未改名：${oldTitle} -> ${newTitle}`)
  assert(!html.includes(`<div class="pb-tit tzlb-tit">${oldTitle}</div>`), `板块标题仍残留旧名：${oldTitle}`)
}
// [码友二（四肖中特）] 这类卡片文字**不属于板块标题**，必须保持不变
assert(index.includes("码友二（四肖中特）"), "码友卡片标题「码友二（四肖中特）」不得被改名")
// 2026-09-30：【码友三（10码中特）】→【码友三（六肖中特）】。
// 该卡片的数据源是 `6xzt`（mode 46 六肖中特），旧标题「10码中特」与正文不符。
for (const [html, name] of [[index, "index.html"], [index1, "index1.html"]]) {
  assert(html.includes("码友三（六肖中特）"), `${name} 的码友三卡片必须改名为「码友三（六肖中特）」`)
  assert(!html.includes("码友三（10码中特）"), `${name} 不得再残留旧卡片名「码友三（10码中特）」`)
}

// ── 6. 第 2 项：码友每期必须带开奖与判定 ──────────────────────────────────
assert(
  /function renderMayouLailiaoHistory[\s\S]{0,1400}resultValue\(row\)/.test(adapter),
  "码友来料参考每期必须输出开奖与对/错（resultValue）",
)
assert(
  /function renderMayouLailiaoHistory[\s\S]{0,1600}writeLineGroup\(group, "",?\)|writeLineGroup\(group, ""\)/.test(adapter),
  "码友来料参考必须清空模板里多出来的静态样例期号，避免不同期数挤在一起",
)

// ── 7. 第 3 项：间隔符号 ──────────────────────────────────────────────────
assert(
  /function renderBaxiaoShiliumaHistory[\s\S]{0,900}function zodiacCodeGroups/.test(adapter) ||
    /function zodiacCodeGroups/.test(adapter),
  "8肖16码 必须有「生肖+号码」分组展示（间隔符号）",
)
assert(
  /pairs\.slice\(0, 3\)\.join\("-"\)/.test(adapter),
  "六肖六码 生肖对之间必须用间隔符号（-）分离",
)

// ── 9. 头/尾候选与「候选集合」命中口径 ───────────────────────────────────
// 头数候选写作 `4头` / `4头单`（带单双后缀），尾数写作 `7尾` / `2尾双`，必须用正则取头/尾数字。
assert(
  /headMatch = \/\^\(\\d\)\\s\*头\(\[单双\]\?\)\/\.exec\(candidate\)/.test(adapter),
  "头数候选必须用正则取头数字与单双后缀（候选如 `4头单`）",
)
assert(
  /tailMatch = \/\^\(\\d\)\\s\*尾\(\[单双\]\?\)\/\.exec\(candidate\)/.test(adapter),
  "尾数候选必须用正则取尾数字与单双后缀（候选如 `2尾双`）",
)
assert(
  /repeatTail = \/\^\(\\d\)\\1\+\\s\*尾\(\[单双\]\?\)\/\.exec\(candidate\)/.test(adapter),
  "重复尾数候选（`555尾`）同样必须带单双后缀匹配",
)
// 单双后缀必须参与命中判定：只比头/尾数字会把**同头数的另一个组合**标黄
// （线上实测：开 42 = `4头双`，却把候选里排在前面的 `4头单` 标黄）。
assert(
  /function parityHit[\s\S]{0,500}flag === "单"[\s\S]{0,120}% 2 === 1/.test(adapter) &&
    /flag === "双"[\s\S]{0,120}% 2 === 0/.test(adapter),
  "parityHit 必须按开奖号码奇偶校验单双后缀（单=奇数、双=偶数）",
)
for (const name of ["headMatch", "tailMatch", "repeatTail"]) {
  assert(
    new RegExp(`${name}[\\s\\S]{0,120}parityHit\\(${name}\\[2\\], digits\\)`).test(adapter),
    `${name} 的命中判定必须调用 parityHit 校验单双后缀`,
  )
}
// 一位数号码（09）的头数是 0，`0头` 必须能匹配。
assert(
  /digits\.length > 1 \? digits\.charAt\(0\) : "0"/.test(adapter),
  "一位数号码的头数必须是 0（`09` → `0头`）",
)
// 命中型不能以 isCorrect 为门槛：部分模块该字段为空（六肖十八码 / ⑤肖⑩码），
// 以它为门槛会让整块永远标不出黄底。
assert(
  !/if \(row\.result\.isCorrect !== true\) return \[\];/.test(adapter),
  "命中型不得以 result.isCorrect === true 为门槛（该字段可能为空）",
)
// 排除型模块的渲染入口必须显式把 kill 键交给 highlightRuleFor。
// 不传键会退回默认的「命中型」口径 → 判定「错」（杀失败）时开奖值恰好等于候选，
// 会被当成命中项标黄（线上 `?|狗` / `?|本期` / `?|蓝单` 等 R3 的根因）。
for (const [pattern, where] of [
  [/renderThreeColumnRows\(sectionByTitle\("绝杀①肖"\), module, function \(row\) \{[\s\S]{0,200}?\}, "juesha1xiao"\)/, "绝杀①肖"],
  [/renderThreeColumnRows\(sectionByTitle\("绝杀①波"\), module, function \(row\) \{ return tokens\(row\)\.join\(""\); \}, "jueshabanbo"\)/, "绝杀①波"],
  [/renderThreeColumnRows\(sectionByTitle\("绝杀一肖一尾"\), module, function \(row\) \{ return tokens\(row\)\.join\(""\); \}, "juesha1wei"\)/, "绝杀一肖一尾"],
  [/renderThreeColumnRows\(sectionByTitle\("杀两半波"\), module, function \(row\) \{[\s\S]{0,120}\}, "shaliangbanbo"\)/, "杀两半波"],
  [/renderRemainingThreeColumnHistory\("杀肖杀码", modules\.juesha3xiao, null, "juesha3xiao"\)/, "杀肖杀码"],
  [/renderRemainingThreeColumnHistory\("本期输尽光", modules\.shujinguang, null, "shujinguang"\)/, "本期输尽光"],
  [/renderRemainingThreeColumnHistory\("绝杀⑩码", module, function \(row\) \{[\s\S]{0,120}\}, "wensha10ma"\)/, "绝杀⑩码"],
]) {
  assert(pattern.test(adapter), `${where} 必须显式传排除型模块键（否则退回命中型口径 → 错行标黄）`)
}

// ── 10. 展示源必须唯一：不得跨模块兜底 ────────────────────────────────────
// `moduleWithRows(primary, fallback)` 会在 primary 缺失时改用**另一个模块**，
// 于是「一肖一码」画出了 9肖12码的 12 个号码、「⑤肖⑩码」画出了 4肖8码。
// 缺失就该隐藏板块（或显示「暂无后端资料」），不得借别的模块数据。
for (const [primary, wrong] of [
  ["public_yixiao_yima", "9xiao12ma"],
  ["wuxiao_wuma", "4xiao8ma"],
]) {
  assert(
    !new RegExp(`moduleWithRows\\(\\s*modules\\.${primary}\\s*,\\s*modules(?:\\.|\\[")${wrong}`).test(adapter),
    `${primary} 不得跨模块兜底到 ${wrong}（会把别的板块数据画进来）`,
  )
}
assert(
  /renderBaxiaoShiliumaHistory\(modules\["9xiao12ma"\]\)/.test(adapter),
  "8肖16码 的数据源是 mode_id 60 = 9xiao12ma，不得复用六肖十八码（会让两个面板显示同一组 18 码）",
)
assert(
  /renderShibamaHistory\(null\)/.test(adapter),
  "18码中特 在 site_module_blueprints 里是 blocked_requires_backend_work，必须渲染空态而不是借别人的数据",
)
// ── 10b. 分类中特板块：数据源必须与面板图例同一口径（2026-09-30）──────────
// 【天地+②肖】= 天地组选 1 + 生肖选 2，绑定 mode 5「天地生肖」（title_5，本站有数据）；
// 【前后中特】绑定 mode 219「前后特肖」（qianhou_texiao）—— 面板图例是「前肖/后肖」，
// 与 `qianhou_texiao` 的正文标签同一口径（判定另由 `qianhouJudgement` 本地复算，
// 见第 20 节）。
// 而【日夜特肖】【左右中特】【阴阳⑧码中特】本站没有对应分类数据，过去分别借
// `qianhou_texiao`（前后肖）/ `title_5`（天地肖）/ `title_48`（8肖中特）顶上，
// 页面出现「图例是日/夜、内容是前/后」这类错位；现在一律不借 → 整块隐藏。
assert(
  /renderTiandiErxiaoHistory\(modules\.title_5\)/.test(adapter),
  "【天地+②肖】必须绑定 mode 5 = title_5（天地生肖：天地组 + 两肖），不得绑 0 行的 tiandi_2xiao",
)
assert(
  /renderQianhouZhongteHistory\(modules\.qianhou_shengxiao\)/.test(adapter),
  "【前后中特】必须绑定 mode 133「前后生肖」（qianhou_shengxiao），与面板展示的前/后分组同口径",
)
for (const title of ["日夜特肖", "左右中特", "阴阳⑧码中特"]) {
  assert(
    !new RegExp(`render[A-Za-z]*History\\("${title}"`).test(adapter) && !adapter.includes(`renderCategoryHistory("${title}"`),
    `【${title}】本站无对应分类数据，不得再接别的模块渲染（应整块隐藏）`,
  )
}
assert(
  !/renderTiandiErxiaoHistory\(modules\.tiandi_2xiao\)/.test(adapter),
  "【天地+②肖】不得再绑 0 行的 tiandi_2xiao 模块",
)

// ── 11. 「代号生肖」标黄：代号要能反查回生肖 ───────────────────────────────
// 候选是「生肖|代号」（狗|狗牙），单元格只显示代号，命中项却是开奖特肖。
// 不反查就会整块 0 标记（线上实测 4 期命中一个都没标出来）。
assert(
  /function daimingDrawnNames/.test(adapter) && /function daimingPairName/.test(adapter),
  "代号生肖 必须把「生肖|代号」反查成代号再标黄，否则整块标不出来",
)
assert(
  /renderRemainingThreeColumnHistory\("代号生肖",\s*module,\s*function \(row\) \{\s*return tokens\(row\)\.map\(daimingPairName\)/.test(adapter),
  "代号生肖 的展示与标黄都必须走 daimingPairName 反查",
)

// ── 12. 空态必须清干净模板里烤死的样例数据 ────────────────────────────────
// 配对卡片模板把行内容放在占位 span **之后**（`<span data-prediction-line=""></span>龙蛇兔马牛<br>`）。
// 只写 host.textContent 会把内容留在 span 外面，出现「暂无后端资料」和旧模板码并存。
assert(
  /var next = host\.nextSibling;[\s\S]{0,220}next\.nodeValue = "";/.test(adapter),
  "writeLineGroup 必须把紧随占位 span 的文本节点并进 host，否则旧模板号码永远清不掉",
)
assert(
  /groups\.forEach\(function \(group\) \{ writeLineGroup\(group, "暂无后端资料"\); \}\)/.test(adapter),
  "配对卡片无后端行时必须把**每一行**都写成占位，不能只写第一行（旧模板码会残留在其余行）",
)

// ── 13. 语义标签与号码清单命中 ────────────────────────────────────────────
// 展示文本会把分隔符换成 `-`（`0-4-3-2头`）、把标签加字（`大` → `大数`）、
// 把尾数重复三次（`5尾` → `555尾`）。只按展示文本全等匹配时，
// 大小中特 / 大小 / 梭哈⑦尾 / 火爆④头 / 平特一尾 / 稳中单双 / 单双二肖
// 实测整块 0 标记（应标未标）。必须再用 payload 的号码清单 + 大小/单双语义判定。
assert(
  /function candidateCodeList/.test(adapter) && /function normalizeCandidateLabel/.test(adapter),
  "必须能用 payload 的号码清单（`5尾|05,15,25,35,45`）判定命中，并归一化 `777尾`/`大数`/`4头单`",
)
assert(
  /function semanticHit[\s\S]{0,400}value >= 25[\s\S]{0,200}value >= 1 && value <= 24/.test(adapter),
  "大/小 必须按号码区间判定（大 25-49、小 01-24），否则大小中特永远标不出来",
)
assert(
  /semanticHit\(candidate, digits\)/.test(adapter),
  "highlightTokens 必须调用 semanticHit",
)
assert(
  /if \(code && candidateCodeList\(row, candidate\)\.indexOf\(code\) !== -1\) return true;/.test(adapter),
  "highlightTokens 必须用号码清单判定命中（头/尾/段/五行/尾数面板都依赖它）",
)
// 单双只对纯单双候选生效，不能把 `4头单` 这类带后缀的候选当成单双标签。
assert(
  /label = String\(candidate \|\| ""\)\.trim\(\)\.replace\(\/\[\\s数肖\]\/g, ""\);[\s\S]{0,120}label\.length !== 1/.test(adapter),
  "单双语义只能匹配纯「单/双」候选，避免 `4头单` 被误判",
)

// ── 15. 有壳无数据板块隐藏（区别于「缺数据源」）─────────────────────────────
// `public_yixiao_yima` / `wuxiao_wuma` 在 payload 里存在，但直接调用对应
// `_build_*` 实测 history = 0 行（两者都依赖 mode 151，该 mode 全表 0 行）。
// 18码中特（2026-09-30 需求）在 `site_module_blueprints` 里是
// `blocked_requires_backend_work`：后端 mechanism/mode_id 未确认，连模块都没有。
// 日夜特肖 / 左右中特 / 阴阳⑧码中特（2026-09-30 追加）：本站没有对应的分类数据
// （`created.mode_payload_164` 全站 0 行、`created.mode_payload_152` 无 web=10 行），
// 过去借别的模块顶上 → 图例与内容不符，现在同样整块隐藏。
// 按「有壳无数据 → 删」处理；有数据的板块不得被误伤。
const emptyBlock = /var EMPTY_PANEL_TITLES = \[([\s\S]{0,400}?)\]/.exec(adapter)
assert(emptyBlock, "必须维护有壳无数据板块清单 EMPTY_PANEL_TITLES")
const emptyList = emptyBlock[1]
for (const name of ["一肖一码", "⑤肖⑩码", "18码中特", "日夜特肖", "左右中特", "阴阳⑧码中特"]) {
  assert(emptyList.includes(`"${name}"`), `有壳无数据清单必须包含 ${name}`)
}
for (const keep of ["独家公式", "本期输尽光", "双波⑩码", "大小", "六肖六码", "天地+②肖", "前后中特"]) {
  assert(!emptyList.includes(`"${keep}"`), `${keep} 有数据/已修复，不得列入静态有壳无数据清单`)
}
// 【天地+②肖】按 `title_5` 的行数**动态判断**：后端有行就渲染（本项目 web=10 有 69 期），
// 没行才隐藏 —— 不能塞进静态清单（否则有数据也不会显示）。
assert(
  /var UNBACKED_PANELS = \[([\s\S]{0,300}?)\]/.test(adapter),
  "必须维护按行数动态隐藏的无数据板块清单 UNBACKED_PANELS",
)
assert(
  /UNBACKED_PANELS = \[[\s\S]{0,200}title: "天地\+②肖", moduleKey: "title_5"/.test(adapter),
  "天地+②肖 必须按 title_5 的行数动态隐藏（数据源已从 tiandi_2xiao 改为 title_5）",
)
assert(
  /function hideUnbackedPanels\(modules\)[\s\S]{0,400}distinctRows\(modules\[panel\.moduleKey\]\)\.length/.test(adapter),
  "hideUnbackedPanels 必须按模块行数判断（有数据就保持显示）",
)
assert(
  !emptyList.includes(`"天地+②肖"`),
  "天地+②肖 有数据时应恢复显示，不得列入静态有壳无数据清单",
)
assert(
  /data-prediction-empty/.test(adapter),
  "隐藏有壳无数据板块时必须打 data-prediction-empty 标记，便于验收与还原",
)
assert(
  /hideEmptyPanels\(\);/.test(adapter),
  "DOMContentLoaded 必须先调用 hideEmptyPanels()",
)
assert(
  /applyFlatVerdicts\(modules\);[\s\S]{0,200}hideUnbackedPanels\(modules\);/.test(adapter),
  "renderPredictions 必须先按平特口径重算判定，再隐藏无数据板块",
)

// ── 16. 「大小」面板（原「大小+①头」）────────────────────────────────────
// `dxztt1` 的 raw 是 `content: '["大|45"]'`，**没有** `daxiao` / `tou_code` 键，
// 只读那两个键会连「大数」都取不到。面板已改名为「大小」：`dxztt1` 只提供大小，
// 原来的「+①头」没有对应数据列（显示的只是用预测号码推出来的头数），已去掉。
assert(
  /function firstRawItem/.test(adapter),
  "必须能从 JSON 数组 / 逗号串形态的 raw 字段里取第一项（dxztt1 用 content）",
)
assert(
  /renderRemainingThreeColumnHistory\("大小", module/.test(adapter),
  "面板必须按新标题「大小」查找（旧标题「大小+①头」已废弃）",
)
assert(
  !/renderRemainingThreeColumnHistory\("大小\+①头"/.test(adapter),
  "适配器里不得再引用旧标题「大小+①头」",
)
assert(
  !index.includes("大小+①头") && !index1.includes("大小+①头"),
  "index.html / index1.html 里不得再出现旧标题「大小+①头」",
)
assert(
  /【大小】/.test(index) && /【大小】/.test(index1),
  "index.html / index1.html 必须已改名为【大小】",
)

// ── 17. sectionByTitle 必须精确优先 ──────────────────────────────────────
// 面板标题都在【】里。子串匹配会让短标题命中更长的标题：
// 「大小中特」排在「大小」之前时，sectionByTitle("大小") 会先命中「大小中特」。
assert(
  /function sectionByTitle[\s\S]{0,900}\/\u3010\(\[\^\u3011\]\*\)\u3011\/\.exec/.test(adapter),
  "sectionByTitle 必须先按【标题】精确匹配，避免短标题命中更长的标题",
)
assert(
  /var exact = sections\.filter/.test(adapter) && /if \(exact\) return exact;/.test(adapter),
  "sectionByTitle 精确匹配命中时必须直接返回，不再退回子串匹配",
)

// ── 18. 「综合绝杀」3头中特 / 3行中特 按排除型重做 ─────────────────────────
// 该面板是杀号语义（每个小节都写 `NNN期稳杀【…】`），而后端 mode 12（3头中特）/
// mode 53（3行中特）的 `is_correct` 是**命中型**（特码头 / 特码五行落在候选里 → true）。
// 直接上接口判定会渲染成「稳杀…对」，并把整段候选标黄（线上 188 期
// `稳杀【3头2头1头】开:38蛇对` 带 1 处黄底 = 「对」与杀号语义混排）。
// 本面板必须按排除型取反：被杀集合**不含**开奖目标 → 对，含 → 错；排除型零黄底。
// 真渲染断言见 `frontend/test/twbst528-zonghe-juesha-contract.py`。
for (const [key, moduleExpr] of [["3tou", 'modules["3tou"]'], ["3hang", 'modules["3hang"]']]) {
  assert(
    adapter.includes(`{ key: "${key}", module: ${moduleExpr}, rule: "kill", invertVerdict: true }`),
    `${key} 在「综合绝杀」面板里必须显式按排除型渲染（rule:"kill" + invertVerdict:true）`,
  )
}
assert(
  /function resultValue\(row, invert\)/.test(adapter),
  "resultValue 必须支持 invert 参数（展示层按排除型取反）",
)
assert(
  /var correct = result\.isCorrect;/.test(adapter) &&
    /if \(invert === true\)[\s\S]{0,240}result\.isCorrect === true \? false[\s\S]{0,120}result\.isCorrect === false \? true/.test(adapter),
  "resultValue 的 invert 分支必须把命中型 is_correct 取反（true→错、false→对），不传时沿用接口判定",
)
assert(
  /var text = formatter\(row, moduleIndex, entry\);/.test(adapter) &&
    /highlightTokens\(row, entry\.rule \|\| highlightRuleFor\(entry\.key\)/.test(adapter),
  "renderCompositeLines 必须把小节条目交给 formatter，并让 entry.rule 覆盖标黄口径",
)
// 取反的对象必须是「开奖号码是否落在**本行候选自己声明的号码清单**里」，而不是接口
// `is_correct` 直接取反：上游 mode 53 用 fixed_data 五行表（37→木）判定，而供应商正文的
// 分组是另一套划分（`土|03,06,09,…,45,48` 里含 45）——直接取反会出现
// 「开奖号码明明写在候选【土】组里，却判杀中（对）」的自相矛盾展示。
assert(
  /function candidateNumberLists/.test(adapter) &&
    /function killedSetContainsTarget/.test(adapter) &&
    /function withResultCorrect/.test(adapter),
  "综合绝杀 3tou/3hang 必须按本行候选清单本地复算（candidateNumberLists + killedSetContainsTarget + withResultCorrect）",
)
assert(
  /var hitInKillSet = invert \? killedSetContainsTarget\(row\) : null;/.test(adapter) &&
    /var judged = hitInKillSet === null \? row : withResultCorrect\(row, hitInKillSet\);/.test(adapter),
  "排除型小节必须优先按本行候选清单复算，拿不到清单时才退回接口判定",
)
// `3tou` / `3hang` 不得进全局 KILL_RULE_KEYS：`renderWuxingLailiaoHistory(modules["3hang"])`
// 仍把「3行中特」当**命中型**渲染（五行来料面板），全局改键会连带改掉它的口径。
for (const key of ["3tou", "3hang"]) {
  assert(
    !killBlock[1].includes(`"${key}"`),
    `${key} 不得进全局 KILL_RULE_KEYS（会连带改掉「五行来料」等命中型面板的口径）`,
  )
}

// ── 13. 拆包残留 marker span（供应商候选列 CSS 兜底芥末黄）──────────────────
// home.css `.mtbl td:nth-child(2) span { background-color:#d1be18 }` 给候选列里**任何**
// span 兜底芥末黄（rgb(209,190,24)）。clearMarkers 只清内联 #FFFF00 时模板预埋 marker
// span 仍在，writeCell 的 leaves[0] 又往往落在它里面，整段候选文本被写回该 span ——
// 「错」行整行被染成芥末黄（线上实测：代号生肖 268 期、两波突围等 21 个板块 57 处）。
// 修复：writeCell 路径 clearMarkers(cell, true) 在清样式后**拆包**（子节点前移、删壳）；
// writeWaveNumbers 复用模板 marker span 存命中底色，不得拆（调用处不传第二参）。
assert(
  /function clearMarkers\(cell, unwrapMarkers\)/.test(adapter) &&
    /if \(unwrapMarkers\) \{[\s\S]{0,200}while \(marker\.firstChild\) marker\.parentNode\.insertBefore\(marker\.firstChild, marker\);[\s\S]{0,80}marker\.parentNode\.removeChild\(marker\);/.test(adapter),
  "clearMarkers 必须支持拆包：清掉黄底的 marker span 要从 DOM 移除（子节点前移），不能只清样式",
)
{
  const writeCellBody = /function writeCell\(cell, value, hitValues\) \{([\s\S]*?)\n  \}/.exec(adapter)
  assert(writeCellBody, "必须能定位 writeCell 函数体")
  assert(
    /clearMarkers\(cell, true\)/.test(writeCellBody[1]),
    "writeCell 必须以拆包模式调用 clearMarkers(cell, true)，否则候选文本会落回带 CSS 兜底黄底的 span",
  )
  // 拆包调用只允许出现在两个**候选格**渲染点：writeCell（通用候选单元格），
  // 以及【吉美丑凶】（`renderSanxiaoLiumaHistory`，两行候选、不能用 writeCell）。
  // 后者同样必须拆包：模板 323/319 期预埋了 `<span style="background-color:#FFFF00">`
  // 的样例黄底，只清样式会留下空黄底 → 判定「错」的期次照样有黄底（R3）。
  // 其余 clearMarkers 调用保持默认（writeWaveNumbers 复用模板 span）。
  const unwrapCallSites = adapter.match(/clearMarkers\([^)]*,\s*true\)/g) || []
  assert(
    unwrapCallSites.length === 2,
    `拆包调用只允许出现在 writeCell 与【吉美丑凶】候选格，实际发现 ${unwrapCallSites.length} 处`,
  )
  assert(
    /function renderSanxiaoLiumaHistory[\s\S]{0,1600}clearMarkers\(cells\[1\], true\)[\s\S]{0,400}writePlainLine\(groups\[0\]/.test(adapter),
    "【吉美丑凶】候选格必须拆包模板黄底后再按行写纯文本，命中项由 writePlainLine 单独标黄",
  )
}

// ── 19. 2026-09-30 七项改造（源码级口径）────────────────────────────────────
// 需求清单：
//   1. 【八肖来袭】→【七肖来袭】（上面的 RENAMES）；
//   2. 【平特①肖】【绝杀①肖】内容显示改「生肖重复三次」；**所有平特**按七个开奖号码判定；
//      绝杀①肖按用户确认仍按最后一个开奖号码（特码）判定，不做七码复算；
//   3. 天地+②肖 / 18码中特 无后端资料 → 整块隐藏（上面第 15 节）；
//   4. 独家公式：去 `T37`、去「整体准确率…参弃随意」、加「开：」；
//   5. 家野中特改用 mode 14（title_14）显示家禽/野兽两组；
//   6. 码友三（10码中特）→ 码友三（六肖中特）（上面的 RENAMES）；
//   7. 暴富⑦肖只显示生肖，不显示号码。

// 2a. 平特判定引擎：七个开奖号码（六个平码 + 特码）
for (const token of [
  "function fullDrawnCodes", "function fullDrawnZodiacs",
  "function flatZodiacHit", "function flatTailHit",
  "function withFlatVerdict", "var FLAT_MODULE_KINDS", "function applyFlatVerdicts",
]) {
  assert(adapter.includes(token), `平特七码判定缺少 ${token}`)
}
assert(
  /FLAT_MODULE_KINDS = \{[\s\S]{0,200}pt1xiao: "zodiac"[\s\S]{0,120}pt1wei: "tail"/.test(adapter),
  "平特一肖/一尾必须走七码口径（一尾按号码尾数、其余按生肖）",
)
// `pt3xiao`（平特3肖，mode 470）**不得**再走七码口径：本站首页没有「平特③肖」面板，
// 它只作为【吉美丑凶】【③肖防③码】的数据源，而这两个面板按中特口径判定
// （七码口径下这两块 20 期里 19 期恒「对」，已在第 20 节登记）。需要七码口径的
// 【平特③肖连】在 `static-article-data-adapter.js` 里，与本文件无关。
{
  const flatBlock = /var FLAT_MODULE_KINDS = \{([\s\S]*?)\};/.exec(adapter)
  assert(flatBlock, "必须能定位 FLAT_MODULE_KINDS 数组字面量")
  assert(
    !flatBlock[1].includes("pt3xiao"),
    "pt3xiao 不得再走七码平特口径（它只喂【吉美丑凶】【③肖防③码】两个中特面板）",
  )
}
// 完整开奖串必须能从嵌套的 `raw.raw.res_code`（供应商模块外层只留特码）里取到，
// 并按长度取最长的那一份。
assert(
  /valueList\(nested\.res_code\)/.test(adapter) && /valueList\(nested\.res_sx\)/.test(adapter),
  "完整开奖串必须读取 raw.raw.res_code / raw.raw.res_sx（独家公式等模块外层只有特码）",
)
assert(
  /function longestDrawnList[\s\S]{0,220}list\.length > best\.length/.test(adapter),
  "开奖串必须按「取最长一份」读取，避免只拿到特码",
)
// 平特的命中项可能来自平码（不是特码），标黄链路必须按整组开奖值比对。
assert(
  /if \(flatDraw && flatDraw\.zodiacs\.indexOf\(candidate\) !== -1\) return true;/.test(adapter) &&
    /if \(flatDraw && flatDraw\.codes\.indexOf\(candidate\) !== -1\) return true;/.test(adapter),
  "平特命中项可能来自平码，highlightTokens 必须按 flatDraw（七个开奖值）判定标黄",
)

// 2b. 【平特①肖】生肖 ×3 + 命中整段标黄
assert(
  /function renderPingteYixiaoHistory[\s\S]{0,500}var value = zodiactsOf\(row\)\[0\] \|\| "";[\s\S]{0,120}value \+ value \+ value/.test(adapter),
  "【平特①肖】内容必须显示成「生肖重复三次」（鸡鸡鸡），与供应商模板一致",
)
assert(
  /function renderPingteYixiaoHistory[\s\S]{0,700}row\.result\.isCorrect === true && text \? \[text\]/.test(adapter),
  "【平特①肖】命中时整段三个重复生肖一起标黄",
)
// 2c. 【绝杀①肖】同样三次显示，但**判定口径不变**（用户明确：仍按最后一个开奖号码）。
assert(
  /function renderJueshaYixiaoHistory[\s\S]{0,600}value \+ value \+ value[\s\S]{0,200}"juesha1xiao"/.test(adapter),
  "【绝杀①肖】内容同样显示成「生肖重复三次」，并保留排除型模块键",
)
assert(
  /function renderJueshaYixiaoHistory[\s\S]{0,700}withFlatVerdict/.test(adapter) === false,
  "【绝杀①肖】不得接入平特七码复算（用户确认：绝杀仍按最后一个开奖号码判定）",
)
// 2d. 【平特一尾】命中时只标尾数数字（`<span>555</span>尾`）。
assert(
  /function renderPingteYiweiHistory[\s\S]{0,700}return \[text\.replace\(\/尾\$\/, ""\) \|\| text\];/.test(adapter),
  "【平特一尾】命中时只标尾数数字部分（「尾」字不标）",
)

// 4. 【独家公式】排版：去 T 前缀 / 去准确率说明 / 加「开：」
assert(
  /function renderDujiaGongshiHistory[\s\S]{0,1800}整体准确率\|参弃随意/.test(adapter),
  "【独家公式】必须清空模板烤死的「整体准确率：96.96%。参弃随意」说明行",
)
assert(
  /function renderDujiaGongshiHistory[\s\S]{0,2400}" 开：" \+ \(opened \? drawnSummary\(row\) : "待开奖"\)/.test(adapter),
  "【独家公式】每行必须补「开：xx」（未开奖给「开：待开奖」）",
)
assert(
  /function drawnSummary[\s\S]{0,300}codes\.join\("-"\) \+ zodiac/.test(adapter),
  "【独家公式】开奖串必须是七个号码（前六平码 + 末位特码）连特肖",
)
assert(
  !/T" \+ resultToken\(row\.result\.code, true\)/.test(adapter),
  "【独家公式】不得再输出 `T37` 这类无意义前缀",
)
assert(
  /function renderDujiaGongshiHistory[\s\S]{0,2600}entry\.is_correct === true \? "√" : "x"/.test(adapter),
  "【独家公式】√/x 必须取维度判定 raw.formula[kind].is_correct（行级 isCorrect 恒为 null）",
)

// 5. 【家野中特】改用 mode 14（title_14），显示家禽/野兽两组。
assert(
  /renderJiayeZhongteHistory\(modules\.title_14\)/.test(adapter),
  "【家野中特】数据源必须是 mode 14 = title_14（家禽野兽），不得再借平特2肖",
)
assert(
  /function domesticWildGroups[\s\S]{0,900}DOMESTIC_WILD_LABELS/.test(adapter),
  "【家野中特】必须按「组名 + 生肖」还原家禽/野兽两组（tokens 形态不稳定）",
)
assert(
  /group\.label \+ "：" \+ group\.values\.join\(""\)/.test(adapter),
  "【家野中特】展示成 `家禽：猪鸡羊马+野兽：猴龙鼠兔` 形态",
)

// 7. 【暴富⑦肖】只保留生肖（候选是 `生肖|号码`）
assert(
  /function renderBaofuQixiaoHistory[\s\S]{0,300}return zodiactsOf\(row\)\.join\(""\);/.test(adapter),
  "【暴富⑦肖】必须只显示生肖串（不得再把 `生肖|号码` 一起写进正文）",
)
assert(
  /function renderBaxiaoLaixiHistory[\s\S]{0,400}sectionByTitle\("七肖来袭"\)[\s\S]{0,400}return zodiactsOf\(row\)\.join\(""\);/.test(adapter),
  "【七肖来袭】必须按新标题查找，且只显示生肖串",
)
assert(
  !adapter.includes('sectionByTitle("八肖来袭")'),
  "适配器里不得再引用旧标题「八肖来袭」",
)

// ── 20. 2026-10-01 三个中特面板：绑定权威 mode（155 / 117 / 133）──────────────
// 上一轮（同日）先把判定改成本地中特口径，但数据源仍是借来的模块；本轮按需求换成
// 语义对应的权威 mode：
//   【吉美丑凶】← 155「吉美凶丑（2选1，全肖）」= `jimei_xiongchou`
//   【③肖防③码】← 117「3肖4码」= `sanxiao_siwei_xiao`
//   【前后中特】← 133「前后生肖」= `qianhou_shengxiao`（原 219「前后特肖」只比 2 肖）
// 口径：
//   155/133 展示「分组名 + 6 个成员生肖」，命中 = 特肖 ∈ 该分组成员（与后端
//   `outcome_loader` 把特肖映射成分组名 + `contains_hit` 同口径）；
//   117 展示「3 肖 + 4 码」，命中 = 特肖 ∈ 3 肖（与后端 `hit_checker=contains_hit`、
//   `RULE_BY_MODE_ID[117]=zodiac` 一致；码组只展示，号码半区属于 mode 123）。
// 语义与 DOM 级回归见 `frontend/test/twbst528-zhongte-verdict-contract.py`；这里只钉
// 源码级事实（口径函数存在、面板真的接上新模块、旧模块不再被首页面板引用）。
for (const token of [
  "function displayedZodiacList", "function displayedNumberList",
  "function specialZodiacOf", "function specialCodeOf",
  "function groupMembers", "function groupMemberJudgement",
  "function qianhouJudgement", "function jimeiXiongchouJudgement",
  "function sanxiaoSiweiJudgement", "var QIANHOU_GROUP",
]) {
  assert(adapter.includes(token), `面板级中特口径缺少 ${token}`)
}
for (const gone of ["function zodiacPanelJudgement", "function sanxiaoFangSanmaJudgement"]) {
  assert(!adapter.includes(gone), `${gone} 已被权威 mode 的实现取代，不得残留`)
}
// 三块面板必须绑到新模块键，且不得再引用借来的模块。
assert(
  /renderSanxiaoLiumaHistory\(modules\.jimei_xiongchou\)/.test(adapter),
  "【吉美丑凶】必须绑 mode 155 = `jimei_xiongchou`",
)
assert(
  /renderSanxiaoFangSanmaHistory\(modules\.sanxiao_siwei_xiao\)/.test(adapter),
  "【③肖防③码】必须绑 mode 117 = `sanxiao_siwei_xiao`",
)
assert(
  /renderQianhouZhongteHistory\(modules\.qianhou_shengxiao\)/.test(adapter),
  "【前后中特】必须绑 mode 133 = `qianhou_shengxiao`",
)
for (const stale of [
  "renderSanxiaoLiumaHistory(modules.pt3xiao)",
  "renderSanxiaoFangSanmaHistory(modules.pt3xiao",
  "renderQianhouZhongteHistory(modules.qianhou_texiao)",
]) {
  assert(!adapter.includes(stale), `首页面板不得再引用借来的模块：${stale}`)
}
// 吉美丑凶：展示「分组名 + 成员」，判定走 `jimeiXiongchouJudgement`，结果格写本地判定。
assert(
  /function renderSanxiaoLiumaHistory[\s\S]{0,1200}groupMembers\(row, XIONGJI_GROUP\)[\s\S]{0,300}jimeiXiongchouJudgement\(row\)/.test(adapter),
  "【吉美丑凶】必须展示 mode 155 的分组与成员，并按 `jimeiXiongchouJudgement` 判定",
)
assert(
  /function renderSanxiaoLiumaHistory[\s\S]{0,2200}writeResultCell\(cells\[2\], judged \? withResultCorrect\(row, judged\.correct\) : row\)/.test(adapter),
  "【吉美丑凶】结果格必须写本地判定（`judged`），未判定时才回退接口值",
)
// 「凶丑肖 / 丑凶肖」两种写法都要能解析（mode 155 用前者，本站面板/模板用后者）。
assert(
  /var XIONGJI_GROUP = \{[\s\S]{0,300}"凶丑肖"[\s\S]{0,200}"丑凶肖"/.test(adapter),
  "XIONGJI_GROUP 必须同时收「凶丑肖」（mode 155 正文）与「丑凶肖」（本站面板文案）",
)
// ③肖防③码：展示 3 肖 + 码组，判定看 3 肖，卡片头部的开奖段也要用本地判定。
assert(
  /function renderSanxiaoFangSanmaHistory[\s\S]{0,900}sanxiaoSiweiJudgement\(row\)[\s\S]{0,400}writeCardHeader\(cell, judged \? withResultCorrect\(row, judged\.correct\) : row\)/.test(adapter),
  "【③肖防③码】必须走 `sanxiaoSiweiJudgement` 并把结果写进卡片头部",
)
assert(
  /function sanxiaoSiweiJudgement[\s\S]{0,600}token: hit \? zodiac : ""/.test(adapter),
  "【③肖防③码】只点亮命中的特肖（码组不参与判定）",
)
// 前后中特：分组从行内容解析，特肖落在组内即「对」，命中点亮分组名。
assert(
  /function groupMembers[\s\S]{0,900}rawValue\(row, "content"\)/.test(adapter) &&
    /function groupMemberJudgement[\s\S]{0,700}token: hit \? \(tokenKind === "label" \? group\.label : zodiac\) : ""/.test(adapter),
  "分组必须从行内容（`content`）解析，缺成员时用兜底表；命中项按面板展示形态决定",
)
assert(
  /function qianhouJudgement\(row\) \{[\s\S]{0,200}groupMemberJudgement\(row, QIANHOU_GROUP, "label"\)/.test(adapter),
  "【前后中特】必须按展示分组判定（点亮分组名），不得沿用接口两肖判定",
)
// 候选格拆包后写纯文本 + 单点 marker：`.mtbl td:nth-child(2) span` 会被 CSS 染成芥末黄。
assert(
  /function markTokenInLeaf[\s\S]{0,900}marker\.style\.backgroundColor = "#FFFF00"/.test(adapter) &&
    /function writePlainLine[\s\S]{0,400}markTokenInLeaf\(group\[0\], text, hitTokens\)/.test(adapter),
  "【吉美丑凶】候选格必须用 `writePlainLine` 写纯文本叶子并只给命中项加 inline 黄底 marker",
)

console.log("twbst528-display-contract: OK")

