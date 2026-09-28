import fs from "node:fs"

// 台湾创富网（www.twcf888.com）vendor 首页 `formatPredictionContent()` 的展示契约。
//
// 首页走 vendor 内联脚本，与文章页 `frontend/lib/twcf888-articles.ts` 是**两条独立**
// 的渲染路径，两边都要满足同一套展示格式，否则「首页对、卡片错」或反之。
// 这里只做源码级契约（该脚本依赖浏览器 DOM，无法在 Node 里整体运行）。
//
// 期望值刻意写成字面量，避免从源码常量读回来导致测试跟着一起错。

const html = fs.readFileSync("frontend/public/vendor/twcf888.com/index.html", "utf8")

function functionBody(source, name) {
  const start = source.indexOf(`function ${name}(`)
  if (start === -1) throw new Error(`missing function ${name}`)
  const next = source.indexOf("\n    function ", start + 1)
  return source.slice(start, next === -1 ? source.length : next)
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

/**
 * 取 `if (…) { … }` 分支的完整源码。
 *
 * 必须按花括号配对取完整分支：分支体里也有嵌套的 `{ … }` 与 `if (`，
 * 用缩进或「下一个 if」切分都会把分支截断，导致断言看到的是残缺代码。
 */
function branchFor(body, condition) {
  const start = body.indexOf(condition)
  if (start === -1) throw new Error(`branch not found: ${condition}`)
  const open = body.indexOf("{", start)
  if (open === -1) throw new Error(`branch has no body: ${condition}`)
  let depth = 0
  for (let i = open; i < body.length; i++) {
    const ch = body[i]
    if (ch === "{") depth++
    else if (ch === "}") {
      depth--
      if (depth === 0) return body.slice(start, i + 1)
    }
  }
  throw new Error(`unbalanced branch: ${condition}`)
}

// ── buildModeSpecificPrediction：首页真正渲染这些 mode 的分支 ──────────
// 注意：vendor 首页有**两个**渲染函数。
//   · `formatPredictionContent` 只被 `buildLiveModuleSection` 调用，覆盖 mode 103/54 等；
//   · `buildModeSpecificPrediction` 被 `buildSsxztSection` / `buildBz9xSection` /
//     `buildModuleCell` 调用，覆盖 54/41/98/57/20/472 等。
// 两边都必须满足同一套格式，所以这里分别断言。
const body = functionBody(html, "buildModeSpecificPrediction")

// 平特一尾（mode 54）：必须五位数字，不能停留在三位
const mode54 = branchFor(body, "if (meta.modeId === 54)")
assert(
  mode54.includes("tailDigit + tailDigit + tailDigit + tailDigit + tailDigit"),
  "首页平特一尾必须按五位数字展示（7尾 → 【77777】）"
)
// 条数用「标识符出现次数」判定，比正则匹配三连字样更稳（注释里也会出现三连字样）。
function countOccurrences(haystack, needle) {
  return haystack.split(needle).length - 1
}

assert(
  countOccurrences(mode54, "tailDigit") === 7,
  `首页平特一尾必须恰好重复五位数字（tailDigit 应为 7 处：1 处声明 + 1 处三元的 5 连 + 1 处取值），` +
    `实际 ${countOccurrences(mode54, "tailDigit")} 处`
)

// 绝杀一行（mode 98）：必须有独立分支 + 三连展示
const mode98 = branchFor(body, "if (meta.modeId === 98)")
assert(mode98.includes("wx98Label + wx98Label + wx98Label"), "首页绝杀一行必须三连展示（水 → 【水水水】）")

// 绝杀一头 / 必杀1头（mode 41）：必须从 14/38/483 分支拆出来，且五位数字
const mode41 = branchFor(body, "if (meta.modeId === 41)")
assert(
  mode41.includes("head41Digit + head41Digit + head41Digit + head41Digit + head41Digit"),
  "首页绝杀一头必须按五位数字展示（0头 → 【00000】）"
)
const sharedRawBranch = branchFor(body, "if (meta.modeId === 14 || meta.modeId === 38")
assert(
  !sharedRawBranch.includes("meta.modeId === 41"),
  "首页绝杀一头不得与 14/38/483 共用原样输出分支（会把 [\"0头|01,…\"] 原始串上屏）"
)

// 特码大小（mode 57）：只取标签三连，不得外泄号码串
const mode57 = branchFor(body, "if (meta.modeId === 57)")
assert(mode57.includes("size57Label + size57Label + size57Label"), "首页特码大小必须三连展示（大 → 【大大大】）")
assert(mode57.includes('replace(/[\\[\\]\\"]/g, "")'), "首页特码大小必须剥掉 JSON 括号与引号")

// 绝杀一尾（mode 20）：命中与未命中两条路径都要五位数字，且都不得上屏原始串
assert(
  body.includes("if (meta.modeId === 20)") || body.includes("meta.modeId === 20"),
  "首页绝杀一尾必须有独立分支"
)
const mode20Hits = html.split("meta.modeId === 20").length - 1
assert(mode20Hits >= 2, `首页绝杀一尾需要覆盖命中与未命中两条路径，实际出现 ${mode20Hits} 次`)

// 绝杀一肖 / 绝禁一肖（mode 472）：三连展示
const mode472 = branchFor(body, "if (meta.modeId === 472)")
assert(
  mode472.includes("killOneZodiac + killOneZodiac + killOneZodiac"),
  "首页绝杀一肖/绝禁一肖必须三连展示（兔 → 【兔兔兔】）"
)

// ── mode 143 高亮回归（首页路径） ────────────────────────────────────
// `一波中特`（命中型）与 `绝杀一波`（verdictInverted）共用 mode 143。
// 判定为「错」的绝杀一波那一期，开奖波色其实落在候选里（杀失败），必须标黄。
const mode143 = branchFor(body, "if (meta.modeId === 38 || meta.modeId === 143")
assert(
  mode143.includes("background-color:#FFFF00"),
  "首页 mode 143 必须有标黄分支"
)
assert(
  mode143.includes("meta.verdictInverted === true ? row.is_correct === false : row.is_correct === true"),
  "首页绝杀一波（取反）必须以「取反后判定为错」作为标黄条件，否则整列零黄底"
)

// 取反栏目的判定必须在所有渲染路径上收敛（否则卡片显示相反的对/错）
assert(
  (html.match(/effectiveVerdictRow\(meta, module\.history\[index\]\)|effectiveVerdictRow\(meta, latest\)/g) || []).length >= 2,
  "必中九肖 / 模块卡片路径也必须用 effectiveVerdictRow 收敛取反判定"
)

// 判定文字不得出现编码损坏
for (const broken of ["鍑", "閿", "鏈", "銆", "\uFFFD"]) {
  assert(!html.includes(broken), `首页脚本不得出现编码损坏字符 ${JSON.stringify(broken)}`)
}

// 友情链接板块必须与站内其他板块同宽（800px），不能铺满整屏
assert(
  html.includes(
    '<managed-site-links site-key="twcf888" style="display:block;width:100%;max-width:800px;margin:0 auto;box-sizing:border-box;"></managed-site-links>'
  ),
  "友情链接板块必须约束到与站宽一致的 800px"
)

console.log("twcf888-vendor-display-contract: OK")
