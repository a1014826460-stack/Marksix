// 展示口径契约（tw8800 / shengshi8800）
//
// 覆盖本轮「命中才显示 / 命中才高亮 / 三期中特 中N期」的展示需求：
//   1. 逻辑用例：mode 197 的「中N期」由三期窗口内已开奖各期的特肖算出；
//   2. 静态不变量：相关渲染脚本必须走统一判定，且不得再写死默认值。
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import vm from "node:vm"

const JS_DIR = "frontend/public/vendor/shengshi8800/static/js"
const ROUTE = "frontend/app/api/kaijiang/[[...path]]/route.ts"
const VERDICT_FILE = `${JS_DIR}/legacy-prediction-verdict.js`

// ── 1. 从 compat 路由里抽出窗口聚合逻辑并做真实断言 ────────────
const routeSource = fs.readFileSync(ROUTE, "utf8")

function extractFunction(source, name) {
  const header = `function ${name}(`
  const start = source.indexOf(header)
  assert.notEqual(start, -1, `${ROUTE} 里找不到 function ${name}`)
  let depth = 0
  let index = source.indexOf("{", start)
  const bodyStart = index
  for (; index < source.length; index++) {
    const ch = source[index]
    if (ch === "{") depth++
    else if (ch === "}") {
      depth--
      if (depth === 0) return source.slice(start, index + 1)
    }
  }
  return source.slice(start, bodyStart)
}

/** 去掉本次抽取函数里用到的少量 TS 注解，便于在 vm 里直接执行。 */
function toPlainJs(source) {
  return source
    .replace(/(function\s+[A-Za-z_$][\w$]*\s*\()([^)]*)(\))/g,
      (_match, head, params, tail) => head + params.replace(/:\s*[^,)]+/g, "") + tail)
    .replace(/\b(const|let|var)\s+([A-Za-z_$][\w$]*)\s*:\s*[^=\n]+=/g, "$1 $2 =")
    .replace(/new\s+Map\s*<[^>]*>\s*\(/g, "new Map(")
}

const harness = [
  "function asString(value) { return value == null ? '' : String(value) }",
  toPlainJs(extractFunction(routeSource, "sanqiWindowZodiacs")),
  toPlainJs(extractFunction(routeSource, "filterSanqiDisplayRows")),
  "globalThis.__sanqi = { sanqiWindowZodiacs, filterSanqiDisplayRows }",
].join("\n")

const sandbox = {}
vm.createContext(sandbox)
vm.runInContext(harness, sandbox)
const { sanqiWindowZodiacs, filterSanqiDisplayRows } = sandbox.__sanqi

const sqztRows = [
  // 窗口 269-271：269 特肖鸡、270 特肖马、271 未开奖
  { start: "269", end: "271", term: "269", res_sx: "龙,狗,羊,猪,龙,鼠,鸡" },
  { start: "269", end: "271", term: "270", res_sx: "兔,猴,蛇,虎,牛,兔,马" },
  { start: "269", end: "271", term: "271", res_sx: ",,,,,," },
  // 窗口 263-265：263 特肖羊、264 特肖兔、265 特肖猪
  { start: "263", end: "265", term: "263", res_sx: "兔,龙,蛇,羊,猴,鸡,羊" },
  { start: "263", end: "265", term: "264", res_sx: "兔,龙,蛇,羊,猴,鸡,兔" },
  { start: "263", end: "265", term: "265", res_sx: "兔,龙,蛇,羊,猴,鸡,猪" },
]

assert.equal(sanqiWindowZodiacs(sqztRows.slice(0, 3)), "鸡,马",
  "269-271 窗口：只统计已开奖各期，且按期中升序")

const picked = filterSanqiDisplayRows(sqztRows)
assert.equal(picked.length, 2, "每个三期窗口只保留一行")
assert.equal(picked[0].term, "270", "窗口内保留最大已开奖期号（271 未开奖）")
assert.equal(picked[0].period_zodiacs, "鸡,马")
assert.equal(picked[1].term, "265")
assert.equal(picked[1].period_zodiacs, "羊,兔,猪")

/** 与 023sqzt.js 完全一致的「中N期」口径。 */
function hitPeriods(pool, periodZodiacs) {
  const zodiacs = String(periodZodiacs || "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
  let hits = 0
  for (const zodiac of zodiacs) {
    if (pool.indexOf(zodiac) !== -1) hits++
  }
  return zodiacs.length > 0 ? `中${hits}期` : "中几期"
}

assert.equal(hitPeriods("牛蛇鼠猴", picked[0].period_zodiacs), "中0期",
  "269-271 窗口候选 [牛蛇鼠猴]，已开奖两期都没中 -> 中0期")
assert.equal(hitPeriods("羊鼠兔龙", picked[1].period_zodiacs), "中2期",
  "263-265 窗口候选 [羊鼠兔龙]，羊与兔命中 -> 中2期")
assert.equal(hitPeriods("牛蛇鼠猴", ""), "中几期", "窗口内一期都没开奖 -> 中几期")

// ── 2. 展示脚本静态不变量 ────────────────────────────────────
const verdictScripts = [
  "016teduan.js", // 65 特码段数：命中高亮整段
  "019ma24.js", // 34 经典24码：命中显示「准」
  "020ssx.js", // 42 绝杀三肖：杀中高亮整池
  "024jsyw.js", // 20 绝杀一尾：杀中高亮
  "027ptw.js", // 43 两肖平特王：命中高亮
  "029sz.js", // 52 四字玄机
  "6w.js", // 2 必中六尾：命中显示「准」
  "ds4x.js", // 31 单双各四肖：命中才标「中:」
  "017yuqian.js", // 62 欲钱解特
  "030ym.js", // 59 独家幽默
  "1.js", // 244 一语破天机
  "003dxzt.js", // 57 大小中特
  "015maishazs.js", // 28 单双中特
  "031dssx.js", // 31 单双四肖
  "dx.js", // 108 大小中特带1头
]

for (const name of verdictScripts) {
  const source = fs.readFileSync(path.join(JS_DIR, name), "utf8")
  assert.ok(
    source.includes("legacyPredictionVerdict"),
    `${name} 必须通过 window.legacyPredictionVerdict 判定/渲染命中`,
  )
}

// ── 4. 不得再定义跨脚本冲突的全局判定函数 ────────────────────
// 曾出现 015maishazs.js 与 031dssx.js 都定义 `window.__parityVerdict`，
// 后加载的那个把前者的实现覆盖掉，导致「单双四肖」按号码单双判定（结果全错）。
// 同理 003dxzt.js 与 dx.js 都定义过 `window.__sizeVerdict`。
function stripComments(source) {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "")
}

const globalOwners = new Map()
for (const name of fs.readdirSync(JS_DIR).filter((entry) => entry.endsWith(".js"))) {
  const live = stripComments(fs.readFileSync(path.join(JS_DIR, name), "utf8"))
  const lines = live.split("\n")
  for (let index = 0; index < lines.length; index++) {
    for (const match of lines[index].matchAll(/window\.(__[A-Za-z0-9_$]+)\s*=/g)) {
      const key = match[1]
      if (!globalOwners.has(key)) globalOwners.set(key, new Set())
      globalOwners.get(key).add(name)
    }
  }
}

const collisions = [...globalOwners.entries()]
  .filter(([, files]) => files.size > 1)
  .map(([key, files]) => `${key} 被多个脚本定义: ${[...files].join(", ")}`)
assert.deepEqual(collisions, [], `存在跨脚本的全局名冲突：\n${collisions.join("\n")}`)

// 三期中特（197）自己算「中N期」，不直接显示「准/错」
const sqzt = fs.readFileSync(path.join(JS_DIR, "023sqzt.js"), "utf8")
assert.ok(sqzt.includes("period_zodiacs"), "023sqzt.js 必须读取接口返回的 period_zodiacs")
assert.ok(sqzt.includes("hitPeriods"), "023sqzt.js 必须统计窗口内命中期数")
assert.ok(!/'中1期'/.test(sqzt), "023sqzt.js 不得把「中1期」写死为默认值")
assert.ok(
  /periodZodiacs\.length\s*>\s*0\s*\?/.test(sqzt),
  "023sqzt.js 只在窗口内已有开奖数据时才显示「中N期」，否则保持「中几期」",
)

// 单双各四肖：未命中不得显示「中:」
const ds4x = fs.readFileSync(path.join(JS_DIR, "ds4x.js"), "utf8")
assert.ok(ds4x.includes("hitMark"), "ds4x.js 必须按判定结果决定是否输出「中:」")
assert.ok(!/中:<font/.test(ds4x), "ds4x.js 不得无条件输出「中:」")

// 精选⑨肖（mode 151 / 008jxym.js）：①/②/③/⑤/⑦/⑨肖 每档只有在特肖落在该档候选内时
// 才显示「中」，未命中不得显示（原来是每档结果后都写死一个「中」）。
const jxym = fs.readFileSync(path.join(JS_DIR, "008jxym.js"), "utf8")
assert.ok(jxym.includes("marks"), "008jxym.js 必须按档位计算是否命中")
assert.equal(
  (jxym.match(/\$\{marks\[\d\]\}/g) || []).length,
  6,
  "008jxym.js 的 ①/②/③/⑤/⑦/⑨肖 六档都必须使用 marks",
)
assert.ok(!/00'\s*\}中/.test(jxym), "008jxym.js 不得在档位结果里写死「中」")

// 命中高亮必须是黄底
for (const name of ["027ptw.js", "020ssx.js", "024jsyw.js", "016teduan.js", "008jxym.js"]) {
  const source = fs.readFileSync(path.join(JS_DIR, name), "utf8")
  assert.ok(
    source.includes("background-color: #FFFF00"),
    `${name} 的命中高亮必须使用黄底 span`,
  )
}

// ── 3. 判定模块新增口径的逻辑用例（与契约测试互补）────────────
const verdictSandbox = { window: {} }
vm.createContext(verdictSandbox)
vm.runInContext(fs.readFileSync(VERDICT_FILE, "utf8"), verdictSandbox)
const { verdictOf, drawnCodes, drawnZodiacs, tailLabel } = verdictSandbox.window.legacyPredictionVerdict

assert.deepEqual([...drawnZodiacs({ res_sx: "兔,猴,蛇,虎,牛,兔,马" })],
  ["兔", "猴", "蛇", "虎", "牛", "兔", "马"])
assert.deepEqual([...drawnCodes({ res_code: "4,18,30" })], ["04", "18", "30"])
assert.equal(tailLabel("07"), "7")
assert.equal(verdictOf(34, { content: "39,23,20,08,22,42", res_code: "28,23,26,17,30,04,37", res_sx: "兔,猴,蛇,虎,牛,兔,马" }),
  "miss", "mode 34: 特码37 不在 24 码里 -> miss")
assert.equal(verdictOf(34, { content: "39,23,20,08,22,42,37", res_code: "28,23,26,17,30,04,37", res_sx: "兔,猴,蛇,虎,牛,兔,马" }),
  "ok", "mode 34: 特码37 在 24 码里 -> ok")

console.log(`display verdict contract passed (${verdictScripts.length} 个展示脚本已覆盖)`)
