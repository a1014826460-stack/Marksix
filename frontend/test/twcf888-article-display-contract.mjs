import fs from "node:fs"
import ts from "typescript"

// 台湾创富网（www.twcf888.com）文章页预测正文展示契约。
//
// 覆盖：
//   1. 单取值玩法三连展示 —— 绝杀一肖/绝禁一肖（472）`兔` → 【兔兔兔】、
//      绝杀一行（98）`["水|13,…"]` → 【水水水】、特码大小（57）`["大|25,…"]` → 【大大大】；
//   2. 头尾类五位数字展示 —— 平特一尾（54）/绝杀一尾（20）`7尾` → 【77777】、
//      绝杀一头/必杀1头（41）`0头` → 【00000】；
//   3. 不得外泄原始 JSON（S5）—— 57/41/20 曾把 `["大|25,…"]` 整串上屏；
//   4. 判定文字必须是「准/错」，不得出现 mojibake（准杀7码 mode 88 曾是 `鍑?`/`閿?`）。
//
// 期望值刻意写成字面量，避免从源码常量读回来导致测试跟着一起错。

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

// 号码五行表已收敛到唯一权威前端共享源（`frontend/lib/element-number-groups.ts`，
// `twcf888-articles.ts` 从它 import），必须一并注入，否则 `@/lib/...` 解析不到。
const elementGroupsStub = toDataModule(compileModule("frontend/lib/element-number-groups.ts"))

const articlesModule = toDataModule(
  compileModule("frontend/lib/twcf888-articles.ts")
    .replace('import "server-only";', "")
    .replace(/"@\/lib\/backend-api"/g, JSON.stringify(backendStub))
    .replace(/"@\/lib\/sites"/g, JSON.stringify(sitesStub))
    .replace(/"@\/lib\/element-number-groups"/g, JSON.stringify(elementGroupsStub))
)

const { getTwcf888ArticleDetail } = await import(articlesModule)

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

/**
 * 构造一行 twcf888 的历史数据（形状对齐 public site-page 接口）。
 * `isCorrect` 由后端 `_check_correct_by_mechanism` 计算，这里直接给定以便逐行断言。
 */
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

/** 取出正文里某一期的整行 HTML，便于按行断言。 */
function lineOf(html, term) {
  const match = html.match(new RegExp(`<p>[^<]*${term}期[\\s\\S]*?</p>`))
  return match ? match[0] : ""
}

// ── 1. 三连字符玩法 ────────────────────────────────────────────────

// 绝杀一肖（2292 / mode 472）：特码 45 马，候选 马 → 杀失败 → 判定错，且候选三连展示
let html = await render("2292", 472, [
  row({ term: "270", content: "马", resCode: "01,02,03,04,05,06,45", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: false }),
])
let line = lineOf(html, "270")
assert(line.includes("【<span style=\"color: #2ecc71\">马马马</span>】"), `绝杀一肖必须三连展示：【马马马】\n${line}`)
assert(line.includes("45狗错"), `绝杀一肖杀失败必须显示「错」：\n${line}`)
assert(!line.includes("【<span style=\"color: #2ecc71\">马</span>】"), "绝杀一肖不得只上屏单个生肖")

// 绝禁一肖（7624 / mode 472）：同一 mode 的另一栏目
html = await render("7624", 472, [
  row({ term: "270", content: "龙", resCode: "01,02,03,04,05,06,45", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: true }),
])
line = lineOf(html, "270")
assert(line.includes("龙龙龙"), `绝禁一肖必须三连展示：【龙龙龙】\n${line}`)
assert(line.includes("45狗对"), `绝禁一肖杀中必须显示「对」：\n${line}`)

// 绝杀一行（2287 / mode 98）：五行三连
html = await render("2287", 98, [
  row({ term: "270", content: '["木|13,14,21,22,29,30,43,44"]', resCode: "01,02,03,04,05,06,45", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: true }),
])
line = lineOf(html, "270")
assert(line.includes("木木木"), `绝杀一行必须三连展示：【木木木】\n${line}`)
assert(!line.includes('["'), `绝杀一行不得外泄原始 JSON：\n${line}`)

// 特码大小（7631 / mode 57）：只取标签三连，绝不外泄号码串
html = await render("7631", 57, [
  row({
    term: "270",
    content: '["大|25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49"]',
    resCode: "01,02,03,04,05,06,11",
    resSx: "鼠,牛,虎,兔,龙,蛇,猴",
    isCorrect: false,
  }),
])
line = lineOf(html, "270")
assert(line.includes("大大大"), `特码大小必须三连展示：【大大大】\n${line}`)
assert(!line.includes("25,26"), `特码大小不得把号码串上屏（S5）：\n${line}`)
assert(!line.includes('["'), `特码大小不得外泄原始 JSON：\n${line}`)

// ── 2. 头尾类五位数字 ──────────────────────────────────────────────

// 平特一尾（7626 / mode 54）
html = await render("7626", 54, [
  row({ term: "270", content: '["5尾|05,15,25,35,45"]', resCode: "05,02,03,04,06,07,15", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: true }),
])
line = lineOf(html, "270")
assert(line.includes("55555"), `平特一尾必须五位数字：【55555】\n${line}`)
assert(!line.includes("555】"), `平特一尾不得停留在三位数字：\n${line}`)

// 绝杀一尾（7627 / mode 20）：杀失败（开出的尾数就是被杀尾数）
html = await render("7627", 20, [
  row({ term: "270", content: '["5尾|05,15,25,35,45"]', resCode: "01,02,03,04,06,07,45", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: false }),
])
line = lineOf(html, "270")
assert(line.includes("55555"), `绝杀一尾必须五位数字：【55555】\n${line}`)
assert(!line.includes('["'), `绝杀一尾不得外泄原始 JSON：\n${line}`)

// 绝杀一头（2291 / mode 41）
html = await render("2291", 41, [
  row({ term: "270", content: '["0头|01,02,03,04,05,06,07,08,09"]', resCode: "01,02,03,04,05,06,45", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: true }),
])
line = lineOf(html, "270")
assert(line.includes("00000"), `绝杀一头必须五位数字：【00000】\n${line}`)
assert(!line.includes('["'), `绝杀一头不得外泄原始 JSON：\n${line}`)

// 必杀1头（7639 / mode 41）：同一 mode 的另一栏目
html = await render("7639", 41, [
  row({ term: "270", content: '["2头|20,21,22,23,24,25,26,27,28,29"]', resCode: "01,02,03,04,05,06,45", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: true }),
])
line = lineOf(html, "270")
assert(line.includes("22222"), `必杀1头必须五位数字：【22222】\n${line}`)
assert(!line.includes('["'), `必杀1头不得外泄原始 JSON：\n${line}`)

// ── 3. 判定文字不得出现 mojibake ───────────────────────────────────

// 准杀7码（7629 / mode 88）：特码 45 不在 7 个杀码内 → 杀中 → 必须显示「准」
html = await render("7629", 88, [
  row({ term: "270", content: "17,22,14,42,02,09,15", resCode: "01,03,04,05,06,07,45", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: true }),
])
line = lineOf(html, "270")
assert(line.includes("准"), `准杀7码杀中必须显示「准」：\n${line}`)
for (const broken of ["鍑", "閿", "鏈", "銆", "\uFFFD"]) {
  assert(!html.includes(broken), `文章正文不得出现编码损坏字符 ${JSON.stringify(broken)}：\n${line}`)
}

// 准杀7码杀失败 → 必须显示「错」
html = await render("7629", 88, [
  row({ term: "270", content: "17,22,14,42,02,09,45", resCode: "01,03,04,05,06,07,45", resSx: "鼠,牛,虎,兔,龙,蛇,狗", isCorrect: false }),
])
line = lineOf(html, "270")
assert(line.includes("错"), `准杀7码杀失败必须显示「错」：\n${line}`)
assert(!line.includes("鍑") && !line.includes("閿"), `判定文字不得损坏：\n${line}`)

console.log("twcf888-article-display-contract: OK")
