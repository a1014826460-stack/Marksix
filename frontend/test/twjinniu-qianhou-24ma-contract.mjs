import fs from "node:fs"
import ts from "typescript"

// 台湾通天网（www.twtongtian.com）「前后24码」静态落码文本契约：
//   1. 静态文本必须是「前落码：<24 个号码>」「后落码：<25 个号码>」两行纯文本；
//   2. 两行合计且不重叠地覆盖 01-49（24 + 25 = 49）；
//   3. 号码之间只允许单个空格，不得出现 `2324` / `3241` 这类号码粘连；
//   4. 静态块不得逐号包 <span class="qianhou-num">（移动端会折叠间隙导致粘连）。
//
// 这里的期望值刻意写成字面量，而不是从源码常量里读回来——否则改坏常量时
// 测试会跟着一起错，起不到契约作用。

const FRONT_EXPECTED =
  "前落码：01 02 03 04 05 06 07 08 17 18 19 20 21 22 23 24 33 34 35 36 37 38 39 40"
const BACK_EXPECTED =
  "后落码：09 10 11 12 13 14 15 16 25 26 27 28 29 30 31 32 41 42 43 44 45 46 47 48 49"

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

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

/** 把渲染出的 HTML 还原成可见文本，便于按行断言静态文本。 */
function visibleText(html) {
  return html
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(p|div|tr|td)>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .split("\n")
    .map((line) => line.replace(/[ \t]+/g, " ").trim())
    .filter(Boolean)
}

async function renderModule(modeId, content) {
  globalThis.__twjinniuRows = {
    [modeId]: [
      {
        year: "2026",
        term: "270",
        content,
        // 特码 = res_code 最后一位 = 45，落在后落码 41-49 区间内 → 本期应为「准」。
        res_code: "07,17,14,44,01,42,45",
        res_sx: "鼠,牛,龙,马,羊,狗,狗",
        draw_is_opened: 1,
      },
    ],
  }
  const payload = await getTwjinniuHomepageModules(3)
  return payload.modules
}

const modules = await renderModule(
  110,
  JSON.stringify([
    "后落码|09,10,11,12,13,14,15,16,25,26,27,28,29,30,31,32,41,42,43,44,45,46,47,48,49",
  ])
)
const html = modules.qianhou_24ma.html
const lines = visibleText(html)

// 1) 两行静态落码必须逐字符一致（含单个空格分隔）
assert(
  lines.includes(FRONT_EXPECTED),
  `前落码静态文本不符合契约，实际可见行：${JSON.stringify(lines.slice(0, 8))}`
)
assert(
  lines.includes(BACK_EXPECTED),
  `后落码静态文本不符合契约，实际可见行：${JSON.stringify(lines.slice(0, 8))}`
)

// 2) 不得出现号码粘连（逐号 <span> 的间隙折叠症状）
for (const glued of ["2324", "3241", "1625", "0817", "4041"]) {
  assert(!html.includes(glued), `静态落码出现号码粘连 ${glued}：${html.slice(0, 600)}`)
}

// 3) 静态块不得再用逐号 <span class="qianhou-num">
assert(
  !html.includes('class="qianhou-num"'),
  "静态落码不得再逐号包 <span class=\"qianhou-num\">（移动端会折叠间隙导致 2324 粘连）"
)

// 4) 两行合计 49 个互不重叠的号码（前 24 + 后 25）
const parsed = new Map()
for (const line of lines) {
  const match = line.match(/^(前落码|后落码)：(.*)$/)
  if (match) parsed.set(match[1], match[2].trim().split(" "))
}
assert(parsed.size === 2, `必须同时渲染前落码与后落码两行：${JSON.stringify([...parsed.keys()])}`)
const front = parsed.get("前落码")
const back = parsed.get("后落码")
assert(front.length === 24, `前落码必须 24 个号码，实际 ${front.length}`)
assert(back.length === 25, `后落码必须 25 个号码，实际 ${back.length}`)
const all = [...front, ...back]
assert(new Set(all).size === 49, "前落码与后落码不得重叠，且必须覆盖 01-49")
assert(
  all.slice().sort().join(",") ===
    Array.from({ length: 49 }, (_, index) => String(index + 1).padStart(2, "0")).join(","),
  `落码必须恰好覆盖 01-49：${JSON.stringify(all)}`
)
assert(
  all.every((code) => /^\d{2}$/.test(code) && Number(code) >= 1 && Number(code) <= 49),
  `落码必须是 01-49 的两位号码：${JSON.stringify(all)}`
)

// 5) 本期数据是「后落码」，动态行仍须按期标注方向并给出判定
assert(
  lines.some((line) => line.includes("【后落码】")),
  `动态行必须标注本期方向：${JSON.stringify(lines.slice(-8))}`
)
assert(
  lines.some((line) => line.includes("270期") && line.includes("开45狗") && line.includes("准")),
  `动态行必须给出逐期判定（45 在后落码内 → 准）：${JSON.stringify(lines.slice(-8))}`
)
assert(!lines.some((line) => line.includes("271期")), "未开奖占位期不得出现（本用例只有一期）")

// 6) 方向必须来自数据而非写死：换成前落码再看一次
const frontModules = await renderModule(
  110,
  JSON.stringify([
    "前落码|01,02,03,04,05,06,07,08,17,18,19,20,21,22,23,24,33,34,35,36,37,38,39,40",
  ])
)
const frontLines = visibleText(frontModules.qianhou_24ma.html)
assert(
  frontLines.some((line) => line.includes("【前落码】")),
  `方向文本必须跟随数据标签：${JSON.stringify(frontLines.slice(-6))}`
)
assert(
  !frontLines.some((line) => line.includes("【后落码】")),
  `数据为前落码时不得渲染后落码方向：${JSON.stringify(frontLines.slice(-6))}`
)

console.log("twjinniu-qianhou-24ma-contract: OK")
