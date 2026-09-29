/**
 * twsaimahui「黑白生肖」显示契约（mode 45 / heibai3xiao / getHbx）
 * ---------------------------------------------------------------
 * 背景（用户报障）：该板块连续 6 期都显示「黑肖」，违反"预测内容不得连续三期相同"。
 * 根因不是生成侧（接口每期 hei/bai 两组 3 肖都在变），而是旧渲染逻辑：
 *   1) 用**开奖特肖**反查命中分组（预测内容由真实开奖结果反推）；
 *   2) 查不到时退回 content[0]，而 payload 恒把「黑」放第一组 → 显示恒为「黑肖」。
 * 现按项目约定（twbst528 mode 45「黑白各3肖」）改为显示**生成内容本身**：
 *   显示「黑肖：<3肖> 白肖：<3肖>」；命中 = 特码生肖 ∈ 任一组；只把命中的生肖标黄。
 *
 * 本契约同时校验**源文件**与 index.html 实际加载的 **bundle**（两者都必须修）。
 */
import fs from "node:fs"
import vm from "node:vm"

const SOURCE = "frontend/public/vendor/twsaimahui/static/js/039heibai.js"
const INDEX = "frontend/public/vendor/twsaimahui/index.html"
const MANIFEST = "frontend/public/vendor/twsaimahui/static/js/bundles.json"

// bundle 名 = `sha256(源文件名+源文件内容)[:16]`，由 scripts/bundle-twsaimahui-modules.py
// --rebuild 生成：**源文件一改，文件名就变**（vendor 静态资源带 immutable 长缓存，
// 不换名就永远拿不到新代码）。所以这里动态解析，不写死哈希，避免重建后契约失效。
function resolveBundle() {
  const html = fs.readFileSync(INDEX, "utf8")
  const srcs = [...html.matchAll(/src="(static\/js\/bundle-[0-9a-f]{16}\.js)"/g)].map((m) => m[1])
  if (srcs.length === 0) throw new Error("index.html 未引用任何 bundle")
  const manifest = JSON.parse(fs.readFileSync(MANIFEST, "utf8"))
  const heibaiRun = (manifest.runs || []).find((run) =>
    (run.sources || []).some((name) => String(name).endsWith("/039heibai.js")),
  )
  if (!heibaiRun) throw new Error("bundles.json 里找不到包含 039heibai.js 的 bundle")
  const manifestBundle = String(heibaiRun.bundle)
  if (!srcs.includes(manifestBundle)) {
    throw new Error(`bundles.json 与 index.html 不一致：${manifestBundle} 不在 index.html 引用里`)
  }
  return `frontend/public/vendor/twsaimahui/${manifestBundle}`
}

const BUNDLE = resolveBundle()

// ── 1. 静态：两份文件都不得再出现"由开奖结果反推分组"的旧逻辑 ──────────
const FORBIDDEN = [
  "let shownXiao = hitXiao || xiao[0]",
  "供应商原样式每期只渲染一个分组标签",
  "hitXiao = xiao[i]",
]
const REQUIRED = [
  "let zodiacs = String(xiaoV[i] || '').split(',');",
  "let hit = !!sx && zodiacs.indexOf(sx) !== -1;",
  "if (tokens) c1.push(xiao[i] + '肖：' + tokens);",
  "${c1.join(' ')}",
]
for (const file of [SOURCE, BUNDLE]) {
  const text = fs.readFileSync(file, "utf8")
  for (const token of FORBIDDEN) {
    if (text.includes(token)) throw new Error(`${file} 仍保留结果反推的旧逻辑: ${token}`)
  }
  for (const token of REQUIRED) {
    if (!text.includes(token)) throw new Error(`${file} 缺少新显示逻辑: ${token}`)
  }
  // 标黄只能出现在「命中的那个生肖」上，不能在分组标签上。
  if (text.includes('<span style="background-color: #FFFF00">${shownXiao}肖</span>')) {
    throw new Error(`${file} 仍在给分组标签标黄`)
  }
}
// 被修补的 bundle 必须就是 index.html 实际加载的那一份（名字由内容哈希决定）。
if (!fs.readFileSync(INDEX, "utf8").includes(`static/js/${BUNDLE.split("/").pop()}`)) {
  throw new Error("index.html 不再加载被修补的 bundle，契约的 bundle 目标已失效")
}

// ── 2. 行为：用真实 vendor 文件 + 真实线上 6 期数据渲染，检查显示与标黄 ──
// 数据取自 https://www.twsaimahui.com/api/kaijiang/getHbx?web=6&type=3&num=2
const ROWS = [
  { term: "272", res_code: "", res_sx: "", content: '["黑|鼠,猪,鸡", "白|猴,龙,蛇"]', expectShown: "黑肖：鼠猪鸡 白肖：猴龙蛇", expectVerdict: "??", expectYellow: [] },
  { term: "271", res_code: "36,32,39,12,25,33,35", res_sx: "羊,猪,龙,羊,马,狗,猴", content: '["黑|龙,猪,狗", "白|羊,鸡,牛"]', expectShown: "黑肖：龙猪狗 白肖：羊鸡牛", expectVerdict: "错", expectYellow: [] },
  { term: "270", res_code: "28,23,26,17,30,04,37", res_sx: "兔,猴,蛇,虎,牛,兔,马", content: '["黑|猴,虎,鸡", "白|龙,猪,牛"]', expectShown: "黑肖：猴虎鸡 白肖：龙猪牛", expectVerdict: "错", expectYellow: [] },
  { term: "269", res_code: "39,21,36,20,03,19,46", res_sx: "龙,狗,羊,猪,龙,鼠,鸡", content: '["黑|猴,羊,龙", "白|蛇,猪,兔"]', expectShown: "黑肖：猴羊龙 白肖：蛇猪兔", expectVerdict: "错", expectYellow: [] },
  { term: "268", res_code: "07,29,25,15,32,43,11", res_sx: "鼠,虎,马,龙,猪,鼠,猴", content: '["黑|羊,龙,猴", "白|鸡,兔,虎"]', expectShown: "黑肖：羊龙猴 白肖：鸡兔虎", expectVerdict: "准", expectYellow: ["猴"] },
  { term: "267", res_code: "02,49,04,38,22,27,24", res_sx: "蛇,马,兔,蛇,鸡,龙,羊", content: '["黑|狗,猪,羊", "白|猴,龙,马"]', expectShown: "黑肖：狗猪羊 白肖：猴龙马", expectVerdict: "准", expectYellow: ["羊"] },
  // 命中落在白组：标黄必须跟着命中生肖走，而不是固定在黑组。
  { term: "266", res_code: "01,13,25,37,49,12,24", res_sx: "马,马,马,马,马,羊,龙", content: '["黑|鼠,牛,虎", "白|猴,龙,马"]', expectShown: "黑肖：鼠牛虎 白肖：猴龙马", expectVerdict: "准", expectYellow: ["龙"] },
]

// bundle 是上百个模块拼成的，整份执行需要大量全局桩；只抽取「黑白生肖」这一段
// （从它自己的 $.ajax({ 到该模块的 });），两份文件用同一条抽取规则，保证测的是真代码。
function heibaiModule(text, file) {
  const urlAt = text.indexOf("/api/kaijiang/getHbx")
  if (urlAt < 0) throw new Error(`${file} 找不到 getHbx 模块`)
  const start = text.lastIndexOf("$.ajax({", urlAt)
  const htmlAt = text.indexOf('$(".l14").html', urlAt)
  if (start < 0 || htmlAt < 0) throw new Error(`${file} 无法定位 getHbx 模块边界`)
  const end = text.indexOf("});", htmlAt)
  if (end < 0) throw new Error(`${file} 找不到 getHbx 模块结尾`)
  const slice = text.slice(start, end + 3)
  if (!slice.includes(REQUIRED[1])) throw new Error(`${file} 抽取到的不是修补后的模块`)
  if (slice.includes(FORBIDDEN[0])) throw new Error(`${file} 抽取到的模块仍是旧逻辑`)
  return slice
}

function renderWith(file) {
  const script = heibaiModule(fs.readFileSync(file, "utf8"), file)
  let rendered = ""
  const sandbox = {
    httpApi: "",
    web: 6,
    type: 3,
    safeParseJSON(value, fallback) {
      try {
        return JSON.parse(value)
      } catch {
        return fallback
      }
    },
    console: { error() {}, log() {} },
  }
  const jq = (selector) => ({ html: (markup) => { rendered = markup; return { length: 1, selector } } })
  jq.ajax = (options) => { options.success({ data: ROWS }); return {} }
  sandbox.$ = jq
  sandbox.window = sandbox
  vm.createContext(sandbox)
  vm.runInContext(script, sandbox, { filename: file })
  if (!rendered) throw new Error(`${file} 未渲染任何 HTML`)
  return rendered
}

function parseRows(html) {
  const rows = []
  for (const match of html.matchAll(/<tr>([\s\S]*?)<\/tr>/g)) {
    const block = match[1]
    const term = /(\d+)期<\/strong>/.exec(block)
    if (!term) continue
    if (!/align='center'/.test(block)) throw new Error(`第 ${term[1]} 期未保持居中对齐`)
    const yellow = [...block.matchAll(/background-color: #FFFF00">([^<]*)</g)].map((m) => m[1])
    const text = block
      .replace(/<[^>]+>/g, "")
      .replace(/\s+/g, " ")
      .trim()
    rows.push({ term: term[1], text, yellow })
  }
  return rows
}

for (const file of [SOURCE, BUNDLE]) {
  const rows = parseRows(renderWith(file))
  if (rows.length !== ROWS.length) throw new Error(`${file} 渲染行数 ${rows.length} != ${ROWS.length}`)

  for (const expected of ROWS) {
    const row = rows.find((item) => item.term === expected.term)
    if (!row) throw new Error(`${file} 缺少 ${expected.term} 期`)
    if (!row.text.includes(expected.expectShown)) {
      throw new Error(`${file} ${expected.term} 期显示错误: "${row.text}" 不含 "${expected.expectShown}"`)
    }
    if (!row.text.includes(`开:？`) && !row.text.includes(expected.expectVerdict)) {
      throw new Error(`${file} ${expected.term} 期判定错误: "${row.text}"`)
    }
    const marks = row.yellow.join("")
    const want = expected.expectYellow.join("")
    if (marks !== want) {
      throw new Error(`${file} ${expected.term} 期标黄错误: 期望 "${want}" 实际 "${marks}"`)
    }
  }

  // 用户报障的回归点：显示内容不得连续相同（更不允许整列恒为「黑肖」）。
  const shown = rows.map((row) => (/黑白生肖:(.*?) 开:/.exec(row.text) || [, ""])[1].trim())
  if (new Set(shown).size !== shown.length) {
    throw new Error(`${file} 出现相邻期显示内容相同: ${shown.join(" | ")}`)
  }
  if (shown.some((text) => text === "黑肖")) {
    throw new Error(`${file} 仍在显示单一分组标签「黑肖」`)
  }
}

console.log("twsaimahui heibai display contract passed")
