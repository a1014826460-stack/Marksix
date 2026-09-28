// 五行口径契约（twsaimahui 「三行中特」 mode 53）
//
// 回归背景：`static/js/025sanhang.js`（及打包镜像 `static/js/bundle-823ff3282a9b98f2.js`）
// 是本站三行中特的**唯一**判定与高亮来源（`/api/kaijiang/getXingte` 不返回 `is_correct`）。
// 旧实现两件事都读**正文里每个五行标签后的号码清单**：
//     if (code && xiaoV[i].indexOf(code) !== -1) { zj = true; 黄底 }
// 而历史落库的 mode 53 正文清单是按**生肖五行**（`fixed_data` sign='五行肖'）拼出来的，
// 不是号码五行（= `backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS`
// = `public.fixed_data` sign='五行'）。两者对同一号码给出不同五行：
//   24 → 号码五行 木（生肖羊 → 生肖五行 土）
//   37 → 号码五行 木（马 → 生肖五行 火）
//   45 → 号码五行 木（狗 → 生肖五行 土）
//   04 → 号码五行 金（兔 → 生肖五行 木）
// 于是「生肖五行 ∈ 三行、号码五行 ∉ 三行」的期会被判成「准」并把黄底点在错行上。
//
// 本契约锁定三条口径：
//   1. 判定与高亮只看特码**号码五行**；
//   2. 只点亮命中的那一行，未命中/未开奖零黄底；
//   3. 两种正文形态（后端修复后的号码五行清单 / 未修复的生肖五行清单）结论一致
//      —— 口径不得依赖正文清单。
//
// 运行：node frontend/test/twsaimahui-sanhang-element-contract.mjs
import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

const SANHANG_FILE = "frontend/public/vendor/twsaimahui/static/js/025sanhang.js"
const BUNDLE_FILE = "frontend/public/vendor/twsaimahui/static/js/bundle-823ff3282a9b98f2.js"

const YELLOW = '<span style="background-color: #FFFF00">'

// ── 1. 号码五行分组必须与后端权威常量逐字一致 ────────────────────────
// 期望值刻意写成字面量（抄自 backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS），
// 避免从源码常量读回来导致测试跟着一起错。
const EXPECTED_ELEMENT_GROUPS = {
  金: [3, 4, 11, 12, 25, 26, 33, 34, 41, 42],
  木: [7, 8, 15, 16, 23, 24, 37, 38, 45, 46],
  水: [13, 14, 21, 22, 29, 30, 43, 44],
  火: [1, 2, 9, 10, 17, 18, 31, 32, 39, 40, 47, 48],
  土: [5, 6, 19, 20, 27, 28, 35, 36, 49],
}

/** 取出「三行中特」那一块源码（从 getXingte 请求到写入 .l56 为止）。 */
function sanhangBlock(source) {
  const start = source.indexOf("/api/kaijiang/getXingte")
  assert.ok(start >= 0, "三行中特的 getXingte 请求必须存在")
  const end = source.indexOf('.l56', start)
  assert.ok(end > start, "三行中特必须写入 .l56 容器")
  return source.slice(start, end)
}

for (const file of [SANHANG_FILE, BUNDLE_FILE]) {
  const source = fs.readFileSync(file, "utf8")
  const block = sanhangBlock(source)

  // 1a. 权威号码五行分组必须逐个出现在该模块里（49 码全覆盖）。
  const declared = block.match(/ELEMENT_NUMBER_GROUPS\s*=\s*\{([\s\S]*?)\}/)
  assert.ok(declared, `${file}: 三行中特必须自带号码五行分组常量`)
  const numbers = (declared[1].match(/\d+/g) || []).map(Number)
  const expectedFlat = Object.values(EXPECTED_ELEMENT_GROUPS).flat().sort((a, b) => a - b)
  assert.deepEqual(
    [...new Set(numbers)].sort((a, b) => a - b),
    expectedFlat,
    `${file}: 号码五行分组必须 01-49 全覆盖且与后端 ELEMENT_NUMBER_GROUPS 一致`,
  )

  // 1b. 高亮/判定必须走特码号码五行，不得再拿正文号码清单定位。
  assert.ok(
    block.includes("specialElementOfCode"),
    `${file}: 三行中特必须由特码号码推导命中行（specialElementOfCode）`,
  )
  assert.ok(
    !/\bif\s*\(\s*code\s*&&\s*xiaoV\s*\[\s*i\s*\]\s*\.\s*indexOf/.test(block),
    `${file}: 三行中特不得再用正文号码清单（生肖五行口径）决定黄底与准/错`,
  )
  assert.ok(block.includes("background-color: #FFFF00"), `${file}: 命中高亮必须沿用既有黄底 span`)
}

// ── 2. 真跑渲染器（jquery / safeParseJSON 注入，与既有 vendor 契约同一模式）──
function renderSanhang(rows, file = SANHANG_FILE) {
  const captured = []
  const jquery = () => ({
    html(value) {
      if (value !== undefined) captured.push(String(value))
      return this
    },
  })
  jquery.ajax = (options) => {
    if (typeof options.success === "function") options.success({ data: rows })
    return {}
  }

  const sandbox = {
    $: jquery,
    httpApi: "",
    web: "6",
    type: "3",
    console,
    JSON,
    String,
    Number,
    Boolean,
    Object,
    Array,
    Math,
    Date,
    RegExp,
    Error,
    isNaN,
    parseInt,
    parseFloat,
    // 取自 static/js/util.js（同一实现，无需加载整份 util）。
    safeParseJSON(str, fallback) {
      if (typeof str !== "string" || str === "") return fallback !== undefined ? fallback : []
      try {
        return JSON.parse(str)
      } catch {
        return fallback !== undefined ? fallback : []
      }
    },
    setTimeout,
    clearTimeout,
  }
  sandbox.window = sandbox
  sandbox.globalThis = sandbox
  vm.createContext(sandbox)
  vm.runInContext(fs.readFileSync(file, "utf8"), sandbox, { filename: file })

  assert.ok(captured.length > 0, `${file}: 渲染脚本必须把 HTML 注入容器`)
  return captured.join("\n")
}

function yellowSpans(html) {
  return [...html.matchAll(/<span style="background-color: #FFFF00">([^<]*)<\/span>/g)].map(
    (match) => match[1],
  )
}

// 未修复的 mode 53 正文（生肖五行推导出来的号码清单，抄自
// backend/src/tests/unit/test_repair_mode53_element_content.py 的 LEGACY_53）。
const LEGACY_CONTENT_53 =
  '["土|03,06,09,12,15,18,21,24,27,30,33,36,39,42,45,48", "木|04,05,16,17,28,29,40,41", "水|07,08,19,20,31,32,43,44"]'
// 后端修复后的正文（号码五行清单，同上测试的 CANONICAL_53）。
const CANONICAL_CONTENT_53 =
  '["土|05,06,19,20,27,28,35,36,49", "木|07,08,15,16,23,24,37,38,45,46", "水|13,14,21,22,29,30,43,44"]'

const row = ({ term, content, resCode, resSx }) => ({
  term,
  year: "2026",
  content,
  res_code: resCode,
  res_sx: resSx,
})

// ── 3. 267 期样例：三行«土木水» + 特码 24 → 准，且只高亮「木」──
// 24 的号码五行是木（在«土木水»内）；生肖五行是土 —— 旧口径会把黄底点在【土】上。
const TERM_267 = row({
  term: "267",
  content: LEGACY_CONTENT_53,
  resCode: "05,11,19,31,42,07,24",
  resSx: "牛,马,狗,龙,猪,蛇,羊",
})

const rendered267 = renderSanhang([TERM_267])
assert.ok(rendered267.includes("三行中特"), `必须渲染三行中特面板：${rendered267.slice(0, 300)}`)
assert.ok(
  rendered267.includes(`土${YELLOW}木</span>水`),
  `候选三行必须是«土木水»且黄底落在「木」上：${rendered267.slice(0, 400)}`,
)
assert.deepEqual(
  yellowSpans(rendered267),
  ["木"],
  `267 期只允许「木」黄底（生肖五行口径会把黄底点在「土」上）：${rendered267.slice(0, 400)}`,
)
assert.ok(rendered267.includes("准"), "267 期必须显示「准」")
assert.ok(!rendered267.includes("错"), "267 期不得显示「错」")
assert.ok(rendered267.includes("羊24"), "开奖列必须照旧渲染 生肖+号码")

// 同一期、后端修复后的号码五行正文：结论必须完全一致（口径不依赖正文清单）。
const rendered267Canonical = renderSanhang([{ ...TERM_267, content: CANONICAL_CONTENT_53 }])
assert.deepEqual(yellowSpans(rendered267Canonical), ["木"], "修复后的正文同样只允许「木」黄底")
assert.ok(rendered267Canonical.includes("准"), "修复后的正文同样必须显示「准」")

// 打包镜像是本站真正加载的脚本（`index.html` 只引 bundle，不引 025sanhang.js），
// 它依赖站点运行时（apiClient/axios/vue）无法在无头 sandbox 里整体执行，因此这里锁定
// 「两块源码去掉注释后逐字同源」：镜像与源码任何一处漂移都会在这里失败。
function stripComments(block) {
  return block
    .replace(/\r\n/g, "\n")
    .split("\n")
    .filter((line) => !line.trim().startsWith("//"))
    .join("\n")
    .trim()
}
assert.equal(
  stripComments(sanhangBlock(fs.readFileSync(BUNDLE_FILE, "utf8"))),
  stripComments(sanhangBlock(fs.readFileSync(SANHANG_FILE, "utf8"))),
  `${BUNDLE_FILE}: 三行中特块必须与 ${SANHANG_FILE} 同源（仅注释差异）`,
)

// ── 4. 反例：生肖五行 ∈ 三行，但号码五行 ∉ 三行 → 必须判「错」且零黄底 ──
// 特码 04：号码五行 = 金（不在«土木水»里）；旧正文把 04 写在【木】组
// （兔 → 木肖 → 生肖五行 = 木 ∈ 三行）。旧口径会判「准」+ 黄底「木」。
const COUNTER_EXAMPLE = row({
  term: "266",
  content: LEGACY_CONTENT_53,
  resCode: "05,11,19,31,42,07,04",
  resSx: "牛,马,狗,龙,猪,蛇,兔",
})
const renderedMiss = renderSanhang([COUNTER_EXAMPLE])
assert.deepEqual(yellowSpans(renderedMiss), [], `错期必须零黄底：${renderedMiss.slice(0, 400)}`)
assert.ok(renderedMiss.includes("错"), "未命中必须显示「错」")
assert.ok(!renderedMiss.includes("准"), "未命中不得显示「准」")

// 45（号码五行木、生肖狗 → 生肖五行土）是同一类分歧：正文旧清单把它写在【土】组。
const TERM_45 = row({
  term: "265",
  content: LEGACY_CONTENT_53,
  resCode: "05,11,19,31,42,07,45",
  resSx: "牛,马,狗,龙,猪,蛇,狗",
})
const rendered45 = renderSanhang([TERM_45])
assert.deepEqual(yellowSpans(rendered45), ["木"], `45 的号码五行是木，黄底必须落在【木】：${rendered45.slice(0, 400)}`)
assert.ok(rendered45.includes("准"), "45 号码五行落在三行内 → 必须「准」")

// ── 5. 未开奖：不显示判定且零高亮 ─────────────────────────────────────
const PENDING_ROW = row({ term: "268", content: LEGACY_CONTENT_53, resCode: ",,,,,,", resSx: ",,,,,," })
const renderedPending = renderSanhang([PENDING_ROW])
assert.deepEqual(yellowSpans(renderedPending), [], `未开奖必须零黄底：${renderedPending.slice(0, 400)}`)
assert.ok(
  !renderedPending.includes("准") && !renderedPending.includes("错"),
  "未开奖不得显示判定",
)

console.log("twsaimahui-sanhang-element-contract: OK（mode 53 只按特码号码五行）")
