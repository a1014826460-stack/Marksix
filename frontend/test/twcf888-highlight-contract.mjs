import fs from "node:fs"
import ts from "typescript"

// 台湾创富网（www.twcf888.com）**高亮口径**契约（用户 2026-09-28 确认）。
//
// 口径：**开奖目标落在候选里才标黄**。
//   · 绝杀/排除类（473 绝杀二肖·绝版杀肖、95 绝杀二尾、41 绝杀一头、42 绝杀三肖、
//     143 绝杀一波）：杀失败那一期把「被杀中的那一项」标黄；杀中（对）那一期
//     开奖值本就不在候选里 → 零黄底。
//   · 命中类（38 原创双波、88 准杀7码）：命中时才标黄。
//
// 重点回归 mode 143：`一波中特`（3049，命中型）与 `绝杀一波`（2290，verdictInverted）
// 共用同一份数据与 `is_correct`，取反栏目的 `is_correct` 被翻成「杀中=true」。
// 修复前取反栏目拿它当命中标志，导致**绝杀一波永远不标黄**
// （线上实测 263 期 `【蓝波】开 马37错` 零黄底，而镜像栏目同期是标黄的）。

function compileModule(path) {
  return ts.transpileModule(fs.readFileSync(path, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
}

function toDataModule(source) {
  return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
}

const backendStub = toDataModule(
  "export async function getPublicSitePageData() {" +
    "  const table = globalThis.__twcf888Modules || {};" +
    "  return { modules: Object.keys(table).map((modeId) => ({" +
    "    id: Number(modeId), mechanism_key: 'm' + modeId, title: ''," +
    "    default_modes_id: Number(modeId), default_table: '', sort_order: 0, status: true," +
    "    history: (table[modeId] || []).map((row) => ({ ...row }))," +
    "  })) };" +
    "}"
)
const sitesStub = toDataModule(
  "export function getSiteConfig() { return { siteKey: 'twcf888', defaultWebId: 8, defaultLotteryTypeId: 3 } }"
)

const articlesModule = toDataModule(
  compileModule("frontend/lib/twcf888-articles.ts")
    .replace('import "server-only";', "")
    .replace(/"@\/lib\/backend-api"/g, JSON.stringify(backendStub))
    .replace(/"@\/lib\/sites"/g, JSON.stringify(sitesStub))
)

const { getTwcf888ArticleDetail } = await import(articlesModule)

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const HIGHLIGHT = '<span style="background-color: #FFFF00">'

/** `isCorrect` 由后端 `_check_correct_by_mechanism` 计算；取反栏目由渲染层自行翻转。 */
function row({ term, content, resCode = "", resSx = "", resColor = "", opened = true, isCorrect = null }) {
  return {
    issue: `2026${term}`,
    year: "2026",
    term,
    prediction_text: content,
    result_text: "",
    is_opened: opened,
    is_correct: isCorrect,
    source_web_id: 8,
    raw: { content, res_code: resCode, res_sx: resSx, res_color: resColor },
  }
}

async function render(articleId, modeId, rows) {
  globalThis.__twcf888Modules = { [modeId]: rows }
  const detail = await getTwcf888ArticleDetail(articleId, { lotteryType: 3 })
  assert(detail, `article ${articleId} must resolve`)
  return detail.contentHtml
}

function lineOf(html, term) {
  const match = html.match(new RegExp(`<p>[^<]*${term}期[\\s\\S]*?</p>`))
  return match ? match[0] : ""
}

/** 只统计预测区（【…】）里的黄底，开奖区不算。 */
function predictionHighlighted(line, token) {
  return line.includes(`${HIGHLIGHT}${token}</span>`) || line.includes(`${HIGHLIGHT}${token}`)
}

// ── 绝杀类：杀失败 → 被杀死的那一项标黄 ─────────────────────────────
// 线上实例 2292 / 270 期：候选「马」，开 45狗 → 杀失败，之前已按此口径标黄。
let html = await render("2292", 472, [
  row({ term: "270", content: "马", resCode: "01,02,03,04,05,06,37", resSx: "鼠,牛,虎,兔,龙,蛇,马", isCorrect: false }),
])
let line = lineOf(html, "270")
assert(predictionHighlighted(line, "马马马"), `绝杀一肖杀失败必须把候选标黄：\n${line}`)

// 绝杀一肖杀中 → 零黄底
html = await render("2292", 472, [
  row({ term: "269", content: "龙", resCode: "01,02,03,04,05,06,45", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: true }),
])
line = lineOf(html, "269")
assert(!line.includes("FFFF00"), `绝杀一肖杀中（对）不得有黄底：\n${line}`)

// 绝杀二肖（2288 / 473）：杀失败 → 开出的那一肖标黄
html = await render("2288", 473, [
  row({ term: "270", content: "鸡,马", resCode: "01,02,03,04,05,06,37", resSx: "鼠,牛,虎,兔,龙,蛇,马", isCorrect: false }),
])
line = lineOf(html, "270")
assert(line.includes(`${HIGHLIGHT}马</span>`), `绝杀二肖杀失败必须把被杀中的那一肖标黄：\n${line}`)
assert(!line.includes(`${HIGHLIGHT}鸡</span>`), `绝杀二肖不得把没被开出的另一肖也标黄：\n${line}`)

// 绝版杀肖（7634 / 473）同 mode，另一栏目
html = await render("7634", 473, [
  row({ term: "270", content: "狗,龙", resCode: "01,02,03,04,05,06,09", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: false }),
])
line = lineOf(html, "270")
assert(line.includes(`${HIGHLIGHT}狗</span>`), `绝版杀肖杀失败必须把被杀中的那一肖标黄：\n${line}`)

// 绝杀三肖（7625 / 42）
html = await render("7625", 42, [
  row({ term: "270", content: "鸡,猴,狗", resCode: "01,02,03,04,05,06,09", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: false }),
])
line = lineOf(html, "270")
assert(line.includes(`${HIGHLIGHT}狗</span>`), `绝杀三肖杀失败必须把被杀中的那一肖标黄：\n${line}`)

// 绝杀二尾（2289 / 95）：杀失败 → 被杀中的那一尾标黄
html = await render("2289", 95, [
  row({
    term: "270",
    content: '["9尾|09,19,29,39,49", "5尾|05,15,25,35,45"]',
    resCode: "01,02,03,04,06,07,45",
    resSx: "鼠,牛,虎,兔,龙,蛇,狗",
    isCorrect: false,
  }),
])
line = lineOf(html, "270")
assert(line.includes(`${HIGHLIGHT}5尾</span>`), `绝杀二尾杀失败必须把被杀中的那一尾标黄：\n${line}`)
assert(!line.includes(`${HIGHLIGHT}9尾</span>`), `绝杀二尾不得把没被开出的那一尾也标黄：\n${line}`)

// ── mode 143 回归：绝杀一波（取反） vs 一波中特（命中型） ────────────

// 线上实例 2290 / 263 期：开 37 红波，候选里含红波（杀失败）→ 必须标黄。
// 修复前该栏目的取反判定让高亮条件恒为假，整列零黄底。
html = await render("2290", 143, [
  row({ term: "263", content: "蓝波,红波", resCode: "01,02,03,04,05,06,37", resSx: "鼠,牛,虎,兔,龙,蛇,马", resColor: "red,red,red,red,red,red,red", isCorrect: true }),
])
line = lineOf(html, "263")
assert(line.includes("蓝波+红波"), `绝杀一波必须渲染候选波色：\n${line}`)
assert(line.includes("错"), `绝杀一波杀失败必须显示「错」（取反后）：\n${line}`)
assert(
  line.includes(`${HIGHLIGHT}蓝波+红波</span>`),
  `绝杀一波杀失败必须把被杀中的波色标黄（本次修复点）：\n${line}`
)

// 绝杀一波杀中：候选「绿波」，开 37 红波 → 零黄底
html = await render("2290", 143, [
  row({ term: "262", content: "绿波", resCode: "01,02,03,04,05,06,37", resSx: "鼠,牛,虎,兔,龙,蛇,马", resColor: "red,red,red,red,red,red,red", isCorrect: false }),
])
line = lineOf(html, "262")
assert(line.includes("对"), `绝杀一波杀中必须显示「对」：\n${line}`)
assert(!line.includes("FFFF00"), `绝杀一波杀中不得有黄底：\n${line}`)

// 镜像栏目 一波中特（3049 / 143，非取反）：命中 → 标黄
html = await render("3049", 143, [
  row({ term: "270", content: "红波", resCode: "01,02,03,04,05,06,37", resSx: "鼠,牛,虎,兔,龙,蛇,马", resColor: "red,red,red,red,red,red,red", isCorrect: true }),
])
line = lineOf(html, "270")
assert(line.includes(`${HIGHLIGHT}红波</span>`), `一波中特命中必须标黄：\n${line}`)

// 一波中特未命中 → 零黄底
html = await render("3049", 143, [
  row({ term: "269", content: "绿波", resCode: "01,02,03,04,05,06,37", resSx: "鼠,牛,虎,兔,龙,蛇,马", resColor: "red,red,red,red,red,red,red", isCorrect: false }),
])
line = lineOf(html, "269")
assert(!line.includes("FFFF00"), `一波中特未命中不得有黄底：\n${line}`)

// ── 命中类：命中时标黄 ────────────────────────────────────────────

// 原创双波（7628 / 38）：开 37 红波，候选含红波 → 命中 → 标黄
html = await render("7628", 38, [
  row({ term: "270", content: "红波,绿波", resCode: "01,02,03,04,05,06,37", resSx: "鼠,牛,虎,兔,龙,蛇,马", resColor: "red,red,red,red,red,red,red", isCorrect: true }),
])
line = lineOf(html, "270")
assert(line.includes(`${HIGHLIGHT}红波+绿波</span>`), `原创双波命中必须整组标黄：\n${line}`)

// 准杀7码（7629 / 88）：开 45 不在 7 个杀码内 → 杀中 → 无被杀中的项 → 零黄底
html = await render("7629", 88, [
  row({ term: "270", content: "17,22,14,42,02,09,15", resCode: "01,03,04,05,06,07,45", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: true }),
])
line = lineOf(html, "270")
assert(!line.includes("FFFF00"), `准杀7码杀中不得有黄底：\n${line}`)

// 准杀7码杀失败：开出的号码在杀码里 → 该号码标黄
html = await render("7629", 88, [
  row({ term: "269", content: "17,22,14,42,02,09,45", resCode: "01,03,04,05,06,07,45", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: false }),
])
line = lineOf(html, "269")
assert(line.includes(`${HIGHLIGHT}45</span>`), `准杀7码杀失败必须把被杀中的号码标黄：\n${line}`)

console.log("twcf888-highlight-contract: OK")
