// 六肖三码（twsaimahui #hao012 / static/js/012liuxiao.js）展示契约
//
// 覆盖本轮修复的缺陷：候选正文来自 `num=6` → mode 27（mode_payload_tables 标题「6肖12码」），
// 渲染器必须从 `"肖|码,码,码"` 里分别取「肖名」与「该肖的码组」，
// 且判定口径为：特肖 ∈ 六肖 **或** 特码 ∈ 首个候选肖码组的前三码 → 准，否则错；未开奖不给判定。
//
// 断言分三层：
//   1. 路由映射：route.ts 的 getXiaoma2 分支把 num=6/4/7 映射到 27/51/22；
//   2. 映射函数：mapTwsaimahuiXiaomaRows 产出可 JSON.parse 的 `"肖|码,码,码"` 数组；
//   3. 渲染器：在 vm 里真跑 012liuxiao.js（stub 掉 apiClient / safeParseJSON / render*），
//      用真实形状的接口数据驱动，断言六肖、三码与准/错都出现在渲染结果里。
import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

const ROUTE = "frontend/app/api/kaijiang/[[...path]]/route.ts"
const RENDERER = "frontend/public/vendor/twsaimahui/static/js/012liuxiao.js"

const routeSource = fs.readFileSync(ROUTE, "utf8")
const rendererSource = fs.readFileSync(RENDERER, "utf8")

// ── 1. 路由映射：num → mode ────────────────────────────────────────────
// getXiaoma2 的候选正文按 num 分派：
//   num=4 → 51（4肖8码）、num=7 → 22（7肖14码），其余（含 num=6）→ 27（6肖12码）。
// mode 27 就是「6肖12码」正文表，六肖三码页面的候选必须来自它。
const xiaomaCase = routeSource.slice(
  routeSource.indexOf('case "getXiaoma2"'),
  routeSource.indexOf('case "getHbnx"'),
)
assert.notEqual(xiaomaCase, "", `${ROUTE} 里找不到 getXiaoma2 分支`)
for (const [numValue, modesId] of [
  ["4", 51],
  ["7", 22],
]) {
  const pattern = new RegExp(`num === "${numValue}"[\\s\\S]{0,200}?fetchLegacyRows\\(url, ${modesId},`)
  assert.match(xiaomaCase, pattern, `getXiaoma2 的 num=${numValue} 必须走 mode ${modesId}`)
}
// num=6 走默认分支：紧跟在 num=7 分支之后的 fetchLegacyRows(url, 27, 6)。
const num6Match = xiaomaCase.match(/num === "7"[\s\S]*?fetchLegacyRows\(url, 27, 6\)/)
assert.ok(
  num6Match,
  "getXiaoma2 的默认分支（num=6 精品六肖）必须走 mode 27（6肖12码）",
)

// tvsaimahui（web=6）的 n 肖模块必须走 twsaimahui 专用映射，否则 content 形状不对。
assert.match(
  xiaomaCase,
  /mapTwsaimahuiXiaomaRows\(payload\.rows\)/,
  "getXiaoma2 必须用 mapTwsaimahuiXiaomaRows 产出渲染器要的 content 形状",
)

// ── 2. 从 route.ts 抽出映射函数并在 vm 里真跑 ─────────────────────────
function extractFunction(source, name) {
  const header = `function ${name}(`
  const start = source.indexOf(header)
  assert.notEqual(start, -1, `${ROUTE} 里找不到 function ${name}`)
  let depth = 0
  let index = source.indexOf("{", start)
  for (; index < source.length; index++) {
    const ch = source[index]
    if (ch === "{") depth++
    else if (ch === "}") {
      depth--
      if (depth === 0) return source.slice(start, index + 1)
    }
  }
  throw new Error(`function ${name} 没有闭合`)
}

function toPlainJs(source) {
  return source
    .replace(/(function\s+[A-Za-z_$][\w$]*\s*\()([^)]*)(\))/g,
      (_match, head, params, tail) => head + params.replace(/:\s*[^,)]+/g, "") + tail)
    .replace(/\b(const|let|var)\s+([A-Za-z_$][\w$]*)\s*:\s*[^=\n]+=/g, "$1 $2 =")
}

const mapHarness = [
  "function asString(value) { return value == null ? '' : String(value) }",
  "function parseJsonArray(value) { const raw = asString(value).trim(); if (!raw) return []; try { const parsed = JSON.parse(raw); return Array.isArray(parsed) ? parsed.map((item) => String(item)) : [] } catch { return [] } }",
  "function parseJsonObject(value) { const raw = asString(value).trim(); if (!raw || !raw.startsWith('{')) return null; try { const parsed = JSON.parse(raw); return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null } catch { return null } }",
  toPlainJs(extractFunction(routeSource, "buildTwsaimahuiXiaomaContentItems")),
  toPlainJs(extractFunction(routeSource, "mapTwsaimahuiXiaomaRows")),
  "globalThis.__map = { buildTwsaimahuiXiaomaContentItems, mapTwsaimahuiXiaomaRows }",
].join("\n")

const mapContext = { globalThis: {}, console }
vm.createContext(mapContext)
vm.runInContext(mapHarness, mapContext)
const { mapTwsaimahuiXiaomaRows } = mapContext.globalThis.__map

const mapped = mapTwsaimahuiXiaomaRows([
  {
    term: "190",
    res_sx: "猪,鼠,蛇,猴,猴,牛,狗",
    res_code: "20,19,38,35,23,42,45",
    content: '["狗|09,21,33,45","猪|08,20,32,44","鸡|10,22,34,46","龙|03,15,27,39","猴|11,23,35,47","马|01,13,25,37,49"]',
  },
])[0]

assert.deepEqual(
  Object.keys(mapped).sort(),
  ["content", "res_code", "res_sx", "term"],
  "getXiaoma2 响应字段必须保持 content/res_code/res_sx/term",
)
const mappedItems = JSON.parse(mapped.content)
assert.equal(mappedItems.length, 6, "六肖三码必须透出 6 个候选肖")
assert.deepEqual(mappedItems[0], "狗|09,21,33,45", "每项必须是「肖名|码,码,码」")
for (const item of mappedItems) {
  const [name, codes] = item.split("|")
  assert.match(name, /^[\u4e00-\u9fff]+$/, `肖名不合法：${item}`)
  assert.match(codes, /^\d{2}(,\d{2})+$/, `码组必须是两位逗号串：${item}`)
}

// ── 3. 渲染器真跑：六肖 + 三码 + 准/错 ────────────────────────────────
const FIXTURE = [
  {
    term: "190",
    res_sx: "猪,鼠,蛇,猴,猴,牛,狗", // 特肖 = 狗
    res_code: "20,19,38,35,23,42,45", // 特码 = 45
    content: mapped.content, // 首个候选肖「狗」的码组前三码 = 09,21,33，不含 45 → 靠特肖命中
  },
  {
    term: "189",
    res_sx: "猪,羊,龙,虎,狗,马,狗", // 特肖 = 狗，不在六肖里
    res_code: "32,36,39,05,33,37,09", // 特码 = 09
    content: '["猪|08,20,32,44","猴|11,23,35,47","龙|03,15,27,39","蛇|02,14,26,38","鸡|10,22,34,46","鼠|07,19,31,43"]',
  },
  {
    term: "188",
    res_sx: "鼠,龙,蛇,羊,马,狗,蛇", // 特肖 = 蛇
    res_code: "07,27,02,36,49,45,38", // 特码 = 38
    content: '["蛇|02,14,26,38","龙|03,15,27,39","猴|11,23,35,47","鸡|10,22,34,46","猪|08,20,32,44","狗|09,21,33,45"]',
  },
  {
    term: "191",
    res_sx: "",
    res_code: "",
    content: '["鼠|07,19,31,43","龙|03,15,27,39","猪|08,20,32,44","羊|12,24,36,48","鸡|10,22,34,46","狗|09,21,33,45"]',
  },
]

const rendered = []
const sandbox = {
  console,
  window: {},
  document: { querySelector: () => null },
}
sandbox.window.web = "6"
sandbox.window.type = "3"
sandbox.window.apiClient = {
  get: () => ({
    done: (handler) => {
      handler({ data: FIXTURE })
      return { fail: () => {} }
    },
    fail: () => {},
  }),
}
sandbox.safeParseJSON = (value, fallback) => {
  try {
    const parsed = JSON.parse(value)
    return parsed == null ? fallback : parsed
  } catch {
    return fallback
  }
}
sandbox.renderEmpty = (selector) => rendered.push(`<EMPTY:${selector}>`)
sandbox.renderError = (selector, message) => rendered.push(`<ERROR:${selector}:${message}>`)
sandbox.applyLotteryRegionTitlePrefix = () => {}
sandbox.$ = () => ({
  html: (markup) => {
    rendered.push(String(markup))
    return { length: 1 }
  },
})
sandbox.jQuery = sandbox.$

vm.createContext(sandbox)
vm.runInContext(rendererSource, sandbox)

const html = rendered.join("\n")
// 命中项会被包进 <span style="background-color:#FFFF00">，因此正文断言先剥掉标签。
const plainText = html.replace(/<[^>]*>/g, "")
assert.ok(!/renderEmpty|EMPTY:/.test(html), "有候选数据时不应该走 renderEmpty")
assert.ok(plainText.includes("190期：六肖三码"), "必须渲染 190 期行")
assert.ok(plainText.includes("开:狗45"), "必须渲染开奖「开:狗45」")
assert.ok(plainText.includes("开:狗45准"), "特肖 狗 ∈ 六肖 时必须判「准」")
assert.ok(plainText.includes("189期：六肖三码"), "必须渲染 189 期行")
assert.ok(plainText.includes("开:狗09错"), "特肖与特码都不命中时必须判「错」")
assert.ok(plainText.includes("开:蛇38准"), "特码 38 命中首个候选肖码组前三码时必须判「准」")
assert.ok(plainText.includes("191期：六肖三码 开:？00"), "未开奖期必须保留占位且不给判定")
assert.ok(!plainText.includes("191期：六肖三码 开:？00准"), "未开奖期不得判「准」")
assert.ok(!plainText.includes("191期：六肖三码 开:？00错"), "未开奖期不得判「错」")

// 真实候选必须出现在正文里（不能只显示「开:xxx错」）。
for (const zone of [
  ["必中六肖：", "狗.猪.鸡.龙.猴.马"],
  ["必中三肖：", "狗.猪.鸡"],
  ["必中一肖：", "狗"],
  ["精选12码：", "09.21.33.45.08.20.32.44.10.22.34.46.03.15.27.39.11.23.35.47.01.13.25.37.49"],
  ["精选六码：", "09.21.33.45.08.20"],
  ["必中一码：", "09"],
]) {
  assert.ok(
    plainText.includes(zone[0] + zone[1]),
    `渲染结果必须包含 ${zone[0]}${zone[1]}`,
  )
}

// 命中项必须高亮，未命中项不得高亮（审计 R3/R4）。
const hitSegments = html.match(/#FFFF00/g) || []
assert.ok(hitSegments.length > 0, "命中项必须带黄底高亮")
assert.ok(
  html.includes('<span style="background-color: #FFFF00">狗</span>'),
  "命中的特肖「狗」必须标黄",
)
function segmentOf(markup, term, nextTerm) {
  const start = markup.indexOf(`${term}期`)
  const end = markup.indexOf(`${nextTerm}期`)
  assert.notEqual(start, -1, `渲染结果里找不到 ${term} 期`)
  assert.notEqual(end, -1, `渲染结果里找不到 ${nextTerm} 期`)
  return markup.slice(start, end)
}

const segment189 = segmentOf(html, "189", "188")
assert.ok(
  !/<span style="background-color: #FFFF00">鸡<\/span>/.test(segment189) &&
    !/<span style="background-color: #FFFF00">鼠<\/span>/.test(segment189),
  "189 期未命中的候选肖不得标黄",
)
assert.ok(
  !/<span style="background-color: #FFFF00">\d/.test(segment189),
  "189 期未命中的候选码不得标黄",
)
const segment188 = segmentOf(html, "188", "191")
assert.ok(
  /<span style="background-color: #FFFF00">蛇<\/span>/.test(segment188),
  "188 期命中的特肖「蛇」必须标黄",
)

// 渲染器不得再用「肖名数组里混入码串」的写法（本次缺陷根因）。
assert.ok(
  !/xiao\[k \+ 1\]/.test(rendererSource),
  "012liuxiao.js 不得再按固定步长读取码串去匹配肖名",
)
assert.ok(
  /codesByXiao/.test(rendererSource),
  "012liuxiao.js 必须分别保存肖名与码组",
)

// index.html 只加载 bundle，源文件改了必须同步重建 bundle，否则线上仍是旧逻辑。
const bundles = JSON.parse(
  fs.readFileSync("frontend/public/vendor/twsaimahui/static/js/bundles.json", "utf8"),
)
const entry = bundles.runs.find((run) => run.sources.includes("static/js/012liuxiao.js"))
assert.ok(entry, "bundles.json 必须记录 012liuxiao.js 所在的 bundle")
const bundleFile = entry.bundle.split("/").pop()
const bundleSource = fs.readFileSync(
  `frontend/public/vendor/twsaimahui/static/js/${bundleFile}`,
  "utf8",
)
assert.ok(
  bundleSource.includes("codesByXiao") && !bundleSource.includes("xiao[k + 1]"),
  `${bundleFile} 未随 012liuxiao.js 一起重建`,
)
const indexHtml = fs.readFileSync("frontend/public/vendor/twsaimahui/index.html", "utf8")
assert.ok(indexHtml.includes(bundleFile), `index.html 必须引用重建后的 ${bundleFile}`)

console.log("twsaimahui-012-liuxiao-display-contract: OK")
