import fs from "node:fs"
import ts from "typescript"

// 台湾通天网（www.twtongtian.com）「平特一肖」类模块的命中规则契约：
// 开奖 7 个号码对应的生肖中任一命中预测生肖即算命中（平特口径），不是只看特码生肖。

function compileModule(path) {
  return ts.transpileModule(fs.readFileSync(path, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
}

function toDataModule(source) {
  return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
}

const backendStub = toDataModule(
  "export async function backendFetchJson(path, options) {" +
    "  const modesId = Number(options && options.query ? options.query.modes_id : 0);" +
    "  const table = globalThis.__twjinniuRows || {};" +
    "  return { rows: (table[modesId] || []).map((row) => ({ ...row })) };" +
    "}"
)
const sitesStub = toDataModule(
  "export function getSiteConfig() { return { siteKey: 'twjinniu', defaultWebId: 7 } }"
)

const homepageModule = toDataModule(
  compileModule("frontend/lib/twjinniu-homepage.ts")
    .replace('import "server-only";', "")
    .replace(/"@\/lib\/backend-api"/g, JSON.stringify(backendStub))
    .replace(/"@\/lib\/sites"/g, JSON.stringify(sitesStub))
)

const { getTwjinniuHomepageModules } = await import(homepageModule)

const DRAWN_CODES = "21,39,42,02,18,17,08"
const DRAWN_ZODIACS = "狗,龙,牛,蛇,牛,虎,猪" // 特码生肖=猪，平码含蛇

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

// 展示规范 S2/S3：黄底（`background-color: #FFFF00`）只允许落在**候选**上，
// 「开：」开奖段与判定字一律不许黄；未命中 / 未开奖整行零黄底。
// 模块标题用的是 `<font color="#FFFF00">`（前景色属性），不会被下面的统计口径计入。
function highlightCount(html) {
  return (html.match(/background-color: #FFFF00/g) || []).length
}

function drawSegment(html) {
  return html.match(/开：([\s\S]*?)<\/font>/)?.[1] ?? ""
}

function assertHighlightOnlyOnCandidate(html, candidateSpan, context) {
  assert(
    highlightCount(html) === 1,
    `${context}：命中行黄底必须恰好 1 处（只落在候选上），实得 ${highlightCount(html)} 处：${html.slice(0, 400)}`
  )
  assert(html.includes(candidateSpan), `${context}：命中的候选必须标黄：${html.slice(0, 400)}`)
  assert(
    !drawSegment(html).includes("FFFF00"),
    `${context}：开奖段（“开：”）不得标黄 —— 高亮只落在候选上：${html.slice(0, 400)}`
  )
}

async function renderModule(modeId, content, drawIsOpened = 1) {
  globalThis.__twjinniuRows = {
    [modeId]: [
      {
        year: "2026",
        term: "265",
        content,
        res_code: DRAWN_CODES,
        res_sx: DRAWN_ZODIACS,
        draw_is_opened: drawIsOpened,
      },
    ],
  }
  const payload = await getTwjinniuHomepageModules(3)
  return payload.modules
}

// 1) 平特一肖（mode 103）：蛇只在平码里出现，平特口径应判中
let modules = await renderModule(103, JSON.stringify(["蛇|02,14,26,38"]))
let html = modules.pingte_xiao.html
assert(html.includes("<span style=\"background-color: #FFFF00\">蛇蛇蛇</span>"), "平特一肖命中时三连生肖必须高亮")
assert(html.includes("<font color=\"#FF0000\">08猪对</font>"), `平特一肖平码命中必须显示“对”：${html.slice(0, 400)}`)
assert(!html.includes("错</font>"), "平特一肖平码命中不得显示“错”")
assertHighlightOnlyOnCandidate(
  html,
  "<span style=\"background-color: #FFFF00\">蛇蛇蛇</span>",
  "平特一肖平码命中"
)

// 1b) 平特一肖未开奖：只给占位，零高亮、不给判定字
modules = await renderModule(103, JSON.stringify(["蛇|02,14,26,38"]), 0)
html = modules.pingte_xiao.html
assert(highlightCount(html) === 0, `平特一肖未开奖时整行不得有任何黄底：${html.slice(0, 400)}`)
assert(!html.includes("对</font>") && !html.includes("错</font>"), "平特一肖未开奖不得给判定字")

// 2) 平特一肖：预测生肖不在 7 个号码里 → 显示“错”
modules = await renderModule(103, JSON.stringify(["马|01,13,25,37"]))
html = modules.pingte_xiao.html
assert(html.includes("08猪<font color=\"#000\">错</font>"), `未命中必须显示“错”：${html.slice(0, 400)}`)
assert(!html.includes("#FFFF00\">马马马"), "未命中时不得高亮")
assert(highlightCount(html) === 0, `平特一肖未命中时整行不得有任何黄底：${html.slice(0, 400)}`)

// 3) 公式平特肖（mode 56）：同样按平特口径显示 √
modules = await renderModule(56, "蛇")
html = modules.formula_ptx.html
assert(html.includes("蛇√"), `公式平特肖平码命中必须显示 √：${html.slice(0, 400)}`)
assert(!html.includes("蛇×"), "公式平特肖平码命中不得显示 ×")

// 4) 公式平特肖：不在 7 个号码里 → ×
modules = await renderModule(56, "马")
html = modules.formula_ptx.html
assert(html.includes("马×"), `公式平特肖未命中必须显示 ×：${html.slice(0, 400)}`)

// 5) 独胆/平特一肖（mode 79）：平码命中显示“对”
modules = await renderModule(79, "蛇")
html = modules.pingte_erma.html
assert(html.includes("08猪对"), `独胆/平特一肖平码命中必须显示“对”：${html.slice(0, 400)}`)
assert(!html.includes("错</font>"), "独胆/平特一肖平码命中不得显示“错”")

// 6) 平特一尾（mode 173）：尾数只出现在平码上也算命中
modules = await renderModule(173, JSON.stringify(["1尾|01,11,21,31,41"]))
html = modules.pingte_wei.html
assert(html.includes("<span style=\"background-color: #FFFF00\">111</span>"), "平特一尾平码尾数命中必须高亮")
assert(html.includes("08猪对"), `平特一尾平码命中必须显示“对”：${html.slice(0, 400)}`)
assert(!html.includes("错</font>"), "平特一尾平码命中不得显示“错”")
assertHighlightOnlyOnCandidate(
  html,
  "<span style=\"background-color: #FFFF00\">111</span>",
  "平特一尾平码命中"
)

// 6b) 平特一尾未开奖：只给占位，零高亮、不给判定字
modules = await renderModule(173, JSON.stringify(["1尾|01,11,21,31,41"]), 0)
html = modules.pingte_wei.html
assert(highlightCount(html) === 0, `平特一尾未开奖时整行不得有任何黄底：${html.slice(0, 400)}`)
assert(!html.includes("对</font>") && !html.includes("错</font>"), "平特一尾未开奖不得给判定字")

// 7) 平特一尾：尾数不在 7 个号码里 → 显示“错”
modules = await renderModule(173, JSON.stringify(["3尾|03,13,23,33,43"]))
html = modules.pingte_wei.html
assert(html.includes("08猪<font color=\"#000\">错</font>"), `平特一尾未命中必须显示“错”：${html.slice(0, 400)}`)
assert(!html.includes("#FFFF00\">333"), "平特一尾未命中时不得高亮")
assert(highlightCount(html) === 0, `平特一尾未命中时整行不得有任何黄底：${html.slice(0, 400)}`)
