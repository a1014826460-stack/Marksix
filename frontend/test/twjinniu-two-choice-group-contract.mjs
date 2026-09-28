import fs from "node:fs"
import ts from "typescript"

// 台湾通天网（www.twtongtian.com）「二选一」生肖分组模块（144 文武中特 / 480 吉凶六肖）
// 的分组说明契约（展示规范 S6）与生肖别名归一契约。
//
// 背景：这两个模块在 created.mode_payload_* 里每期只落**一个**组标签
// （`["文肖|免,猪,羊,鸡,鼠,龙"]` / `["凶丑|鼠,牛,虎,猴,狗,猪"]`），
// 因此分组说明必须由该模块自己的历史行合成，且**两组都要显示**；
// 只显示本期恰好抽到的那一组就是 S6 违规。
//
// 另外 `public.fixed_data` 的「文武肖」沿用了厂商写法「免」（实为「兔」），
// 展示必须归一成「兔」，否则用户会看到错别字。

function compileModule(path) {
  return ts.transpileModule(fs.readFileSync(path, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
}

function toDataModule(source) {
  return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
}

const backendStub = toDataModule(
  "export async function backendFetchJson() { return {} }" +
    "export async function getPublicSitePageData() { return { modules: [] } }"
)
const contractStub = toDataModule(
  "export function splitPredictionTokens(value) {" +
    "  return String(value == null ? '' : value).split(/[,\\s.、，|+/-]+/).filter(Boolean);" +
    "}"
)
const sitesStub = toDataModule(
  "export function getSiteConfig() { return { siteKey: 'twjinniu', defaultWebId: 7 } }"
)

const articlesModule = toDataModule(
  compileModule("frontend/lib/twjinniu-articles.ts")
    .replace('import "server-only";', "")
    .replace(/"@\/lib\/backend-api"/g, JSON.stringify(backendStub))
    .replace(/"@\/lib\/prediction-contract"/g, JSON.stringify(contractStub))
    .replace(/"@\/lib\/sites"/g, JSON.stringify(sitesStub))
)

const { buildGroupLegendHtml } = await import(articlesModule)

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function row(term, content, { isOpened = true, resCode = "", resSx = "" } = {}) {
  return {
    issue: `2026${term}`,
    year: "2026",
    term,
    prediction_text: content,
    result_text: "",
    is_opened: isOpened,
    is_correct: null,
    source_web_id: 7,
    raw: { content, res_code: resCode, res_sx: resSx },
  }
}

const WENWU_CONTENT = ["文肖|免,猪,羊,鸡,鼠,龙", "武肖|牛,狗,猴,虎,蛇,马"]
const XIONGJI_CONTENT = ["凶丑|鼠,牛,虎,猴,狗,猪", "吉美|兔,龙,蛇,马,羊,鸡"]

// 1) mode 144：历史行交替出现两组 → 分组说明必须同时列出文肖与武肖
const wenwuRows = [
  row("270", JSON.stringify([WENWU_CONTENT[0]]), { resCode: "01,02,03,04,05,06,37", resSx: "鼠,牛,虎,兔,龙,蛇,马" }),
  row("269", JSON.stringify([WENWU_CONTENT[1]]), { resCode: "01,02,03,04,05,06,46", resSx: "鼠,牛,虎,兔,龙,蛇,鸡" }),
]
const wenwuLegend = buildGroupLegendHtml(wenwuRows, 144)
assert(wenwuLegend.includes("文肖"), `144 分组说明必须包含文肖：${wenwuLegend}`)
assert(wenwuLegend.includes("武肖"), `144 分组说明必须包含武肖：${wenwuLegend}`)
assert(
  wenwuLegend.includes("文肖：兔猪羊鸡鼠龙"),
  `144 文肖成员必须按落库顺序显示且「免」归一为「兔」：${wenwuLegend}`
)
assert(wenwuLegend.includes("武肖：牛狗猴虎蛇马"), `144 武肖成员必须显示：${wenwuLegend}`)
assert(wenwuLegend.includes("（本期）"), `144 必须标出本期抽到的那一组：${wenwuLegend}`)
assert(!wenwuLegend.includes("免"), `144 不得把厂商错别字「免」上屏：${wenwuLegend}`)
assert(!wenwuLegend.includes('["'), `144 分组说明不得外泄原始 JSON：${wenwuLegend}`)

// 2) mode 480：同样必须同时列出凶丑与吉美
const xiongjiRows = [
  row("270", JSON.stringify([XIONGJI_CONTENT[0]])),
  row("269", JSON.stringify([XIONGJI_CONTENT[1]])),
]
const xiongjiLegend = buildGroupLegendHtml(xiongjiRows, 480)
assert(xiongjiLegend.includes("凶丑"), `480 分组说明必须包含凶丑：${xiongjiLegend}`)
assert(xiongjiLegend.includes("吉美"), `480 分组说明必须包含吉美：${xiongjiLegend}`)
assert(xiongjiLegend.includes("凶丑：鼠牛虎猴狗猪"), `480 凶丑成员必须显示：${xiongjiLegend}`)
assert(xiongjiLegend.includes("吉美：兔龙蛇马羊鸡"), `480 吉美成员必须显示：${xiongjiLegend}`)
assert(xiongjiLegend.includes("（本期）"), `480 必须标出本期抽到的那一组：${xiongjiLegend}`)

// 3) 二期都抽到同一组、但更早的行里有另一组时（线上最常见的连续同组情形），
//    仍然必须把两组都显示出来。
const runWithHistoryRows = [
  row("271", JSON.stringify([WENWU_CONTENT[0]])),
  row("270", JSON.stringify([WENWU_CONTENT[0]])),
  row("269", JSON.stringify([WENWU_CONTENT[0]])),
  row("268", JSON.stringify([WENWU_CONTENT[1]])),
]
const runWithHistoryLegend = buildGroupLegendHtml(runWithHistoryRows, 144)
assert(
  runWithHistoryLegend.includes("文肖：兔猪羊鸡鼠龙"),
  `144 连续多期同一组时仍必须显示本期那一组：${runWithHistoryLegend}`
)
assert(
  runWithHistoryLegend.includes("武肖：牛狗猴虎蛇马"),
  `144 连续多期同一组时必须从更早的行取到另一组：${runWithHistoryLegend}`
)

// 4) 非二选一模块不产出分组说明
assert(buildGroupLegendHtml(xiongjiRows, 77) === "", "非二选一模块不得产出分组说明")
assert(buildGroupLegendHtml(xiongjiRows, 20) === "", "非二选一模块不得产出分组说明")

// 5) 整段历史里只有一组时宁缺勿造（不得凭空编出另一组的成员）
const oneGroupLegend = buildGroupLegendHtml([row("270", JSON.stringify([WENWU_CONTENT[0]]))], 144)
assert(oneGroupLegend === "", `只有一组数据时不得产出分组说明：${oneGroupLegend}`)

console.log("twjinniu-two-choice-group-contract: OK")
