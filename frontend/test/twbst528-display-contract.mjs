/**
 * twbst528 六项改造契约（源码级）
 * ---------------------------------------------------------------------------
 * 覆盖本轮改动中「可从源码稳定断言」的部分：
 *   1. 标黄口径：命中型 / 绝杀型两张规则表，且绝杀型只在杀失败时标黄；
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
  "function highlightTokens", "function drawnTokens", "function allowMarkedTokens",
]) {
  assert(adapter.includes(token), `标黄引擎缺少 ${token}`)
}
for (const key of ["juesha1xiao", "juesha2xiao", "juesha3xiao", "wensha10ma", "shaliangbanbo", "shujinguang"]) {
  assert(
    new RegExp(`KILL_RULE_KEYS[\\s\\S]{0,400}"${key}"`).test(adapter),
    `绝杀型规则表必须包含 ${key}`,
  )
}
// 绝杀型只有「杀失败」那期才给标记（isCorrect === false）。
assert(
  /rule === "kill"[\s\S]{0,200}isCorrect === false[\s\S]{0,80}drawnTokens\(row\)[\s\S]{0,20}:\s*\[\]/.test(adapter),
  "绝杀型必须只在杀失败（isCorrect === false）时标黄，杀中零黄底",
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
  /XIONGJI_GROUP = \{ "吉美肖": \["兔", "龙", "蛇", "马", "羊", "鸡"\]/.test(adapter),
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
]
for (const [html, newTitle, oldTitle] of RENAMES) {
  assert(html.includes(`<div class="pb-tit tzlb-tit">${newTitle}</div>`), `板块标题未改名：${oldTitle} -> ${newTitle}`)
  assert(!html.includes(`<div class="pb-tit tzlb-tit">${oldTitle}</div>`), `板块标题仍残留旧名：${oldTitle}`)
}
// [码友二（四肖中特）] 这类卡片文字**不属于板块标题**，必须保持不变
assert(index.includes("码友二（四肖中特）"), "码友卡片标题「码友二（四肖中特）」不得被改名")

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
// 头数候选写作 `4头` / `4头单`（带单双后缀），尾数写作 `7尾` / `2尾双`，
// 必须用正则取头/尾数字后比较，不能只做全等匹配
// （线上实测 `头数单双` 整块 5 期一个都标不出来）。
assert(
  /headMatch = \/\^\(\\d\)\\s\*头\/\.exec\(candidate\)/.test(adapter),
  "头数候选必须用正则取头数字（候选可能带单双后缀，如 `4头单`）",
)
assert(
  /tailMatch = \/\^\(\\d\)\\s\*尾\/\.exec\(candidate\)/.test(adapter),
  "尾数候选必须用正则取尾数字（候选可能带单双后缀，如 `2尾双`）",
)
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

console.log("twbst528-display-contract: OK")
