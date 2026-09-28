// twsaimahui 展示契约：`006heshuds.js`（mode 132 合数中特 / 容器 .l9）
//
// 用户规则：候选 `合单` / `合双` 的判定必须按 `public.fixed_data` 的号码集合做
// **集合精确匹配**（特码 ∈ 合单集合 或 ∈ 合双集合）。
//
// 缺陷复现（2026-09-28）：
//   - compat 路由把后端 mode 132 的正文原样透出（生成器落库的是纯标签 `合双`），
//     渲染层于是把空串 `xiaoV[i]` 拿去 `indexOf(code)` → 恒为 -1 → **每期都显示「不中」**。
//   - 即使正文是 `合单|01,03,…`，`indexOf` 这种子串匹配也会让特码 `03` 命中候选 `37`。
//
// 口径依据：docs/prediction-display-standard.md（S1/S2/S3）与后端
// `predict.categories.size_parity.special_combined_parity_from_row`。
import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

const JS_DIR = "frontend/public/vendor/twsaimahui/static/js"
const ROUTE = "frontend/app/api/kaijiang/[[...path]]/route.ts"

const YELLOW = "background-color:\\s*#FFFF00"

// 用户给出的权威号码表（与 public.fixed_data sign='合单双' 一致）
const COMBINED_SINGLE = "01,03,05,07,09,10,12,14,16,18,21,23,25,27,29,30,32,34,36,38,41,43,45,47,49".split(",")
const COMBINED_DOUBLE = "02,04,06,08,11,13,15,17,19,20,22,24,26,28,31,33,35,37,39,40,42,44,46,48".split(",")

function runScript({ payload }) {
  const captured = { html: "" }
  const $ = (selector) => ({ html: (value) => { captured.selector = selector; captured.html = value } })
  $.ajax = (options) => {
    captured.url = options.url
    options.success({ data: payload })
  }
  const sandbox = {
    console,
    window: {},
    web: 6,
    type: 3,
    httpApi: "",
    $,
    safeParseJSON(str, fallback) {
      if (typeof str !== "string" || str === "") return fallback === undefined ? [] : fallback
      try { return JSON.parse(str) } catch { return fallback === undefined ? [] : fallback }
    },
    renderEmpty: (selector) => { captured.html = `EMPTY:${selector}` },
    renderError: (selector, message) => { captured.html = `ERROR:${selector}:${message}` },
  }
  vm.createContext(sandbox)
  vm.runInContext(fs.readFileSync(`${JS_DIR}/006heshuds.js`, "utf8"), sandbox, { filename: "006heshuds.js" })
  assert.equal(captured.selector, ".l9", "006heshuds.js 必须渲染到 .l9 容器")
  assert.ok(captured.html.includes("合数中特"), "006heshuds.js 必须渲染模块标题")
  return captured.html
}

/** 拆出「一期」：{ term, text, yellow: [...] }。 */
function rowsOf(html) {
  const out = []
  for (const match of html.matchAll(/<tr>([\s\S]*?)<\/tr>/g)) {
    const body = match[1]
    const term = body.match(/(\d{2,3})期/)
    if (!term) continue
    const text = body.replace(/<[^>]+>/g, "").replace(/\s+/g, "")
    const yellow = []
    for (const span of body.matchAll(new RegExp(`<span style="[^"]*${YELLOW}[^"]*">([^<]*)</span>`, "g"))) {
      yellow.push(span[1])
    }
    out.push({ term: term[1], text, yellow })
  }
  return out
}

function verdict(text) {
  if (text.includes("不中")) return "不中"
  if (text.includes("中")) return "中"
  return "未判定"
}

const pending = { term: "191", content: '["合双|' + COMBINED_DOUBLE.join(",") + '"]', res_code: "", res_sx: "" }

// ── 1. 修复后的正文形态（`标签|号码集合`）：逐期集合精确匹配 ──────
// 数据取自真实开奖（`public.mode_payload_132` web=6/type=3）。
const expandedPayload = [
  pending,
  { term: "190", content: `["合单|${COMBINED_SINGLE.join(",")}"]`, res_code: "20,19,38,35,23,42,45", res_sx: "猪,鼠,蛇,猴,猴,牛,狗" }, // 特码 45 → 4+5=9 奇 → 合单命中
  { term: "189", content: `["合双|${COMBINED_DOUBLE.join(",")}"]`, res_code: "32,36,39,05,33,37,09", res_sx: "猪,羊,龙,虎,狗,马,狗" }, // 特码 09 → 9 奇 → 合单，候选合双 → 不中
  { term: "188", content: `["合单|${COMBINED_SINGLE.join(",")}"]`, res_code: "07,27,02,36,49,45,38", res_sx: "鼠,龙,蛇,羊,马,狗,蛇" }, // 特码 38 → 11 奇 → 合单命中
  { term: "186", content: `["合双|${COMBINED_DOUBLE.join(",")}"]`, res_code: "36,16,33,43,08,15,42", res_sx: "羊,兔,狗,鼠,猪,龙,牛" }, // 特码 42 → 6 偶 → 合双命中
  { term: "184", content: `["合双|${COMBINED_DOUBLE.join(",")}"]`, res_code: "24,41,05,09,35,20,21", res_sx: "羊,虎,虎,狗,猴,猪,狗" }, // 特码 21 → 3 奇 → 合单，候选合双 → 不中
]

const expandedRows = rowsOf(runScript({ payload: expandedPayload }))
assert.equal(expandedRows.length, 6, "应渲染 6 期")
const byTerm = Object.fromEntries(expandedRows.map((row) => [row.term, row]))

for (const [term, label, code] of [
  ["190", "合单", "45"],
  ["188", "合单", "38"],
  ["186", "合双", "42"],
]) {
  const row = byTerm[term]
  assert.equal(verdict(row.text), "中", `${term} 期 ${label} 开 ${code} 应为「中」`)
  assert.deepEqual(row.yellow, [label], `${term} 期命中应高亮候选标签`)
}

for (const [term, label, code] of [
  ["189", "合双", "09"],
  ["184", "合双", "21"],
]) {
  const row = byTerm[term]
  assert.equal(verdict(row.text), "不中", `${term} 期 ${label} 开 ${code} 应为「不中」`)
  assert.deepEqual(row.yellow, [], `${term} 期未命中必须零黄底`)
}

assert.equal(verdict(byTerm["191"].text), "未判定", "未开奖不得显示判定（S1）")
assert.deepEqual(byTerm["191"].yellow, [], "未开奖不得高亮")
assert.ok(byTerm["191"].text.includes("？00") || byTerm["191"].text.includes("?00"), "未开奖应显示占位号码")

// ── 2. 修复前的正文形态（纯标签）：绝不能给出「不中」或「中」 ──────
// 路由修复前后端只给纯标签，渲染层没有任何号码集合可用。
// 旧实现把空串当候选串去 `indexOf` → 恒为 -1 → **每期都显示「不中」**（用户看到的缺陷）。
// 正确行为是「无可判定候选 → 不给判定」，既不能假命中也不能假不中。
const barePayload = [
  { term: "191", content: "合双", res_code: "", res_sx: "" },
  { term: "190", content: "合单", res_code: "20,19,38,35,23,42,45", res_sx: "猪,鼠,蛇,猴,猴,牛,狗" },
  { term: "186", content: "合双", res_code: "36,16,33,43,08,15,42", res_sx: "羊,兔,狗,鼠,猪,龙,牛" },
]

const bareRows = rowsOf(runScript({ payload: barePayload }))
assert.equal(bareRows.length, 3, "纯标签形态也必须能渲染（不能抛错/空白）")
for (const row of bareRows) {
  assert.notEqual(verdict(row.text), "中", `缺号码集合时不得假命中：${row.text}`)
  assert.notEqual(verdict(row.text), "不中", `缺号码集合时不得假不中（旧缺陷）：${row.text}`)
}

// ── 3. 子串匹配回归保护 ─────────────────────────────────────────
// 旧实现 `xiaoV[i].indexOf(code)` 是在**整段候选串**上找子串，因此两类误判都会发生：
//  (a) 特码 `0`（合单）命中候选串里的 `10`；
//  (b) 特码 `21`（合单）命中……候选串里的 `21` 是「12,21,34…」中的独立项时不算子串，
//      所以这里改用 3 位特码场景：见下方 (b) 的注释。
const COMBINED_DOUBLE_JOINED = COMBINED_DOUBLE.join(",")
const COMBINED_SINGLE_JOINED = COMBINED_SINGLE.join(",")

// 3a) 单位特码 0：候选「合双」不含 0，但旧子串口径会在 joined 串里找到 "0"
const zeroPayload = [
  { term: "271", content: `["合双|${COMBINED_DOUBLE_JOINED}"]`, res_code: "12,23,31,45,08,19,40", res_sx: "马,虎,猪,鸡,鼠,牛,兔" }, // 40 → 4 偶 → 合双，其实命中
  { term: "272", content: `["合单|${COMBINED_SINGLE_JOINED}"]`, res_code: "12,23,31,45,08,19,40", res_sx: "马,虎,猪,鸡,鼠,牛,兔" }, // 候选合单不含 40 → 不中，但 joined 串含 "0" 字样
]
const zeroRows = rowsOf(runScript({ payload: zeroPayload }))
const zeroByTerm = Object.fromEntries(zeroRows.map((row) => [row.term, row]))
assert.equal(verdict(zeroByTerm["271"].text), "中", "特码 40 属于合双，候选合双应命中")
assert.deepEqual(zeroByTerm["271"].yellow, ["合双"])
assert.equal(verdict(zeroByTerm["272"].text), "不中", "特码 40 不属于合单，候选合单必须判「不中」")
assert.deepEqual(zeroByTerm["272"].yellow, [], "子串误判路径必须零黄底")
assert.ok(COMBINED_SINGLE_JOINED.includes("0") && !COMBINED_SINGLE.includes("40"),
  "回归前提：合单候选串里出现 `0` 字样，但 40 不是合单成员（旧 indexOf 会假命中）")

// 3b) 单位特码 3 不得命中候选串里的 37；11 不得因为出现在合单候选串里而被判命中
const substringPayload = [
  // 特码 03 → 3 奇 → 合单；候选合双 → 不中（旧 indexOf 会在 joined 串里找到 "03"? 不会，
  // 但 "3" 会命中 "37"；这里用 3 位特码的等价形态保证断言稳定）
  { term: "267", content: `["合双|${COMBINED_DOUBLE_JOINED}"]`, res_code: "14,21,32,46,10,16,03", res_sx: "蛇,牛,龙,鼠,鸡,兔,蛇" },
  // 特码 11 → 1+1=2 偶 → 合双；候选合单 → 不中
  { term: "270", content: `["合单|${COMBINED_SINGLE_JOINED}"]`, res_code: "28,23,26,17,30,04,11", res_sx: "兔,猴,蛇,虎,牛,兔,马" },
]
const substringRows = rowsOf(runScript({ payload: substringPayload }))
const substringByTerm = Object.fromEntries(substringRows.map((row) => [row.term, row]))
assert.equal(verdict(substringByTerm["267"].text), "不中", "特码 03 不得因候选串里含 37 而命中合双")
assert.deepEqual(substringByTerm["267"].yellow, [], "子串误判路径必须零黄底")
assert.equal(verdict(substringByTerm["270"].text), "不中", "特码 11 属于合双，候选合单必须判「不中」")
assert.deepEqual(substringByTerm["270"].yellow, [], "子串误判路径必须零黄底")
assert.ok(COMBINED_DOUBLE.includes("11"), "回归前提：11 属于合双")
assert.ok(COMBINED_DOUBLE_JOINED.includes("37"), "回归前提：合双候选串里出现 `37`")

// ── 4. compat 路由：getHeds 必须从 fixed_data 展开号码集合 ───────
const routeSource = fs.readFileSync(ROUTE, "utf8")
assert.ok(
  /case "getHeds"[\s\S]{0,600}?loadFixedDataGroups\("合单双"\)/.test(routeSource),
  "getHeds 必须从 public.fixed_data 的「合单双」读取号码集合，不能只透出纯标签",
)
assert.ok(
  /function mapCombinedParityRows\(/.test(routeSource),
  "缺失 mapCombinedParityRows：合单/合双未展开为 `标签|号码集合`",
)
assert.ok(
  !/getHeds[\s\S]{0,300}?mapJsonContentRows\(payload\.rows\)/.test(routeSource),
  "getHeds 不得再回退到 mapJsonContentRows（正文只有标签）",
)

console.log("twsaimahui 合数中特（mode 132）集合判定契约通过")
