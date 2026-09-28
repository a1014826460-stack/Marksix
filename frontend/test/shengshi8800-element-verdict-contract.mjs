// 五行口径契约（tw8800 / shengshi8800，mode 53 = 三行中特 / 灭庄三行）
//
// 回归背景（用户报障）：`static/js/013shzt.js` 的「灭庄三行」判定与高亮都在读
// **正文里每个五行标签后的号码清单**，而历史遗留的 mode 53 正文清单是按**生肖五行**
// 拼出来的（`土|03,06,…,24,…,45,48` 里含 24），不是号码五行（24 → 木）。
// 于是 267 期 `灭庄三行«土木水»` + 特码 24 会把黄底点在【土】上，并可能把
// 「生肖五行 ∈ 三行但号码五行 ∉ 三行」的期次判成「准」。
//
// 本契约锁定三条口径：
//   1. 判定只看特码**号码五行**（= backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS
//      = public.fixed_data sign='五行'）；
//   2. 高亮只点亮命中的那一行，且与判定同源（未命中/未开奖零黄底）；
//   3. 两种正文形态（后端修复后的号码五行清单 / 未修复的生肖五行清单）判定一致。
//
// 运行：node frontend/test/shengshi8800-element-verdict-contract.mjs
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import vm from "node:vm"

import {
  assertSameGroups,
  codeToElement,
  parseBackendGroups,
  parseVendorGroups,
} from "./lib/element-authority.mjs"

const JS_DIR = "frontend/public/vendor/shengshi8800/static/js"
const VERDICT_FILE = `${JS_DIR}/legacy-prediction-verdict.js`
const RENDER_FILE = `${JS_DIR}/013shzt.js`

const YELLOW = '<span style="background-color: #FFFF00">'

// ── 1. 号码五行常量必须与后端权威分组逐项一致 ──────────────────
// 期望值唯一来源 = 后端权威常量 `backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS`
// （= fixed_data sign='五行'）；本契约不再另抄 49 码表。
const AUTHORITY_GROUPS = parseBackendGroups()
const AUTHORITY_BY_CODE = codeToElement(AUTHORITY_GROUPS)

const verdictSandbox = { window: {} }
vm.createContext(verdictSandbox)
vm.runInContext(fs.readFileSync(VERDICT_FILE, "utf8"), verdictSandbox, { filename: VERDICT_FILE })
const verdictApi = verdictSandbox.window.legacyPredictionVerdict

assert.ok(verdictApi, `${VERDICT_FILE} 必须导出 window.legacyPredictionVerdict`)

// 文件里的常量块（文本解析）与运行期导出（vm 真跑）都要与权威值一致。
assertSameGroups(parseVendorGroups(VERDICT_FILE), AUTHORITY_GROUPS, `${VERDICT_FILE} 常量块`)
const groups = verdictApi.elementNumberGroups
assertSameGroups(
  // vm 里的对象来自另一个 realm，先 JSON 往返成本地普通对象。
  JSON.parse(JSON.stringify(groups)),
  AUTHORITY_GROUPS,
  `${VERDICT_FILE} 运行期 elementNumberGroups`,
)

// 号码五行 vs 生肖五行：这三组是用户报障里的关键分歧点。
assert.equal(verdictApi.specialElement("24"), "木", "24 的号码五行是木（生肖羊 → 生肖五行土：不得混用）")
assert.equal(verdictApi.specialElement("37"), "木", "37 的号码五行是木（生肖马 → 生肖五行火：不得混用）")
assert.equal(verdictApi.specialElement("45"), "木", "45 的号码五行是木（生肖狗 → 生肖五行土：不得混用）")
assert.equal(verdictApi.specialElement("04"), "金", "04 的号码五行是金")
assert.equal(verdictApi.specialElement("49"), "土", "49 的号码五行是土")
// 全 49 码逐一比对后端权威值（判定 API 必须与权威分组同源）。
for (let number = 1; number <= 49; number += 1) {
  const code = String(number).padStart(2, "0")
  assert.equal(
    verdictApi.specialElement(code),
    AUTHORITY_BY_CODE[code],
    `${VERDICT_FILE}: specialElement("${code}") 必须与后端权威值一致`,
  )
}

// ── 2. 真跑渲染器（注入站点 util.js 与统一判定模块，与既有契约同一模式）──
function renderShzt(rows) {
  const captured = []
  const jquery = (selector) => ({
    html(value) {
      if (value !== undefined) captured.push(String(value))
      return this
    },
    append(value) {
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
    web: "4",
    type: "3",
    console,
    JSON, String, Number, Boolean, Object, Array, Math, Date, RegExp, Error,
    isNaN, parseInt, parseFloat, encodeURIComponent, decodeURIComponent,
    setTimeout, clearTimeout,
  }
  sandbox.window = sandbox
  sandbox.globalThis = sandbox
  vm.createContext(sandbox)
  vm.runInContext(fs.readFileSync(path.join(JS_DIR, "util.js"), "utf8"), sandbox, { filename: "util.js" })
  vm.runInContext(fs.readFileSync(VERDICT_FILE, "utf8"), sandbox, { filename: "legacy-prediction-verdict.js" })
  vm.runInContext(fs.readFileSync(RENDER_FILE, "utf8"), sandbox, { filename: "013shzt.js" })

  assert.ok(captured.length > 0, `${RENDER_FILE}: 渲染脚本必须把 HTML 注入容器`)
  return captured.join("\n")
}

function yellowSpans(html) {
  return [...html.matchAll(/<span style="background-color: #FFFF00">([^<]*)<\/span>/g)].map((match) => match[1])
}

/** 去掉黄底 span 只留文字，便于断言候选三行的文字（命中项被黄底包起来）。 */
function stripYellow(html) {
  return html.replace(/<span style="background-color: #FFFF00">([^<]*)<\/span>/g, "$1")
}

// 未修复的 mode 53 正文（生肖五行推导出来的号码清单，抄自
// backend/src/tests/unit/test_repair_mode53_element_content.py 的 LEGACY_53，条目顺序改成
// 用户报障样例的「土木水」）。注意：24 在这里属于【土】（生肖五行），而它的号码五行是木。
const LEGACY_CONTENT_53 =
  '["土|03,06,09,12,15,18,21,24,27,30,33,36,39,42,45,48", "木|04,05,16,17,28,29,40,41", "水|07,08,19,20,31,32,43,44"]'
// 后端修复后的正文（号码五行清单，同上测试的 CANONICAL_53）。
const CANONICAL_CONTENT_53 =
  '["土|05,06,19,20,27,28,35,36,49", "木|07,08,15,16,23,24,37,38,45,46", "水|13,14,21,22,29,30,43,44"]'

// 自证非空操作：两套口径对 24 / 04 的分组确实不同。
assert.ok(/土\|[^"]*\b24\b/.test(LEGACY_CONTENT_53), "旧正文【土】里必须含 24（生肖五行口径）")
assert.ok(!/木\|[^"]*\b24\b/.test(LEGACY_CONTENT_53), "旧正文【木】里不得含 24（否则本用例不成立）")
assert.ok(/木\|04,05,16,17,28,29,40,41/.test(LEGACY_CONTENT_53), "旧正文【木】里必须含 04（生肖五行口径）")
assert.ok(/木\|07,08,15,16,23,24,37,38,45,46/.test(CANONICAL_CONTENT_53), "新正文【木】里必须含 24（号码五行口径）")

// ── 3. 267 期样例：灭庄三行«土木水» + 特码 24 → 准，且只高亮「木」──
const TERM_267 = {
  term: "267",
  content: LEGACY_CONTENT_53,
  res_code: "05,11,19,31,42,07,24",
  res_sx: "牛,马,狗,龙,猪,蛇,羊",
}
assert.equal(
  verdictApi.verdictOf(53, TERM_267),
  "ok",
  "267 期：特码 24 的号码五行（木）落在预测的「土木水」内 → 准",
)
assert.equal(verdictApi.hitElementOf(53, TERM_267), "木", "267 期命中行必须是「木」（不是生肖五行对应的「土」）")

const rendered267 = renderShzt([TERM_267])
assert.ok(rendered267.includes("灭庄三行"), `必须渲染灭庄三行面板：${rendered267.slice(0, 300)}`)
assert.ok(
  stripYellow(rendered267).includes("土木水"),
  `候选三行必须是«土木水»：${stripYellow(rendered267).slice(0, 400)}`,
)
assert.deepEqual(
  yellowSpans(rendered267),
  ["木"],
  `267 期只允许「木」黄底（生肖五行口径会把黄底点在「土」上）：${rendered267.slice(0, 400)}`,
)
assert.ok(rendered267.includes("准"), "267 期必须显示「准」")
assert.ok(!rendered267.includes("错"), "267 期不得显示「错」")
assert.ok(rendered267.includes("羊24"), "开奖列必须照旧渲染 生肖+号码")

// 同一期、后端修复后的号码五行正文：判定与高亮必须完全一致（口径不依赖正文清单）。
const rendered267Canonical = renderShzt([{ ...TERM_267, content: CANONICAL_CONTENT_53 }])
assert.deepEqual(yellowSpans(rendered267Canonical), ["木"], "修复后的正文同样只允许「木」黄底")
assert.ok(rendered267Canonical.includes("准"), "修复后的正文同样必须显示「准」")

// ── 4. 反例：生肖五行 ∈ 三行，但号码五行 ∉ 三行 → 必须判「错」且零黄底 ──
// 特码 04：号码五行 = 金（不在「土木水」里）；旧正文里 04 写在【木】组
// （04 的生肖是木肖 → 生肖五行 = 木 ∈ 三行）。旧口径会判「准」+ 黄底「木」。
const COUNTER_EXAMPLE = {
  term: "266",
  content: LEGACY_CONTENT_53,
  res_code: "05,11,19,31,42,07,04",
  res_sx: "牛,马,狗,龙,猪,蛇,兔",
}
assert.equal(verdictApi.specialElement("04"), "金", "04 的号码五行是金")
assert.equal(
  verdictApi.verdictOf(53, COUNTER_EXAMPLE),
  "miss",
  "生肖五行 ∈ 三行但号码五行 ∉ 三行（04 = 金）→ 必须「错」",
)
assert.equal(verdictApi.hitElementOf(53, COUNTER_EXAMPLE), "", "未命中不得给出命中行")

const renderedMiss = renderShzt([COUNTER_EXAMPLE])
assert.deepEqual(yellowSpans(renderedMiss), [], `错期必须零黄底：${renderedMiss.slice(0, 400)}`)
assert.ok(renderedMiss.includes("错"), "未命中必须显示「错」")
assert.ok(!renderedMiss.includes("准"), "未命中不得显示「准」")

// ── 5. 未开奖：不显示判定且零高亮 ─────────────────────────────
const PENDING_ROW = {
  term: "268",
  content: LEGACY_CONTENT_53,
  res_code: ",,,,,,",
  res_sx: ",,,,,,",
}
assert.equal(verdictApi.verdictOf(53, PENDING_ROW), "pending", "未开奖必须 pending")
assert.equal(verdictApi.hitElementOf(53, PENDING_ROW), "", "未开奖不得给出命中行")

const renderedPending = renderShzt([PENDING_ROW])
assert.deepEqual(yellowSpans(renderedPending), [], `未开奖必须零黄底：${renderedPending.slice(0, 400)}`)
assert.ok(!renderedPending.includes("准") && !renderedPending.includes("错"), "未开奖不得显示判定")

// ── 5b. 标签带修饰（引号/括号/空白/「行」后缀）时判定与高亮不得脱节 ──
const DECORATED_CONTENT_53 =
  '["「土」|03,06,09,12,15,18,21,24,27,30,33,36,39,42,45,48", "木行|04,05,16,17,28,29,40,41", " 水 |07,08,19,20,31,32,43,44"]'
assert.equal(
  verdictApi.verdictOf(53, { ...TERM_267, content: DECORATED_CONTENT_53 }),
  "ok",
  "带修饰的标签必须仍能识别成五行候选行（24 → 木 ∈ 三行 → 准）",
)
const renderedDecorated = renderShzt([{ ...TERM_267, content: DECORATED_CONTENT_53 }])
assert.deepEqual(
  yellowSpans(renderedDecorated),
  ["木行"],
  `带修饰的标签必须用与判定层相同的归一化点亮命中行：${renderedDecorated.slice(0, 400)}`,
)
assert.ok(renderedDecorated.includes("准"), "带修饰的标签同样必须显示「准」")

// ── 6. 静态不变量：渲染层不得再按正文号码清单点行 ────────────────
const renderSource = fs.readFileSync(RENDER_FILE, "utf8")
assert.ok(
  renderSource.includes("hitElementOf"),
  `${RENDER_FILE} 的高亮必须走统一判定层的 hitElementOf（与 verdictOf 同源）`,
)
assert.ok(
  !/maValue\s*\[\s*i\s*\]\s*\.\s*indexOf/.test(renderSource),
  `${RENDER_FILE} 不得再用正文号码清单（生肖五行口径）决定黄底行`,
)
assert.ok(
  /background-color:\s*#FFFF00/.test(renderSource),
  `${RENDER_FILE} 的命中高亮必须沿用既有黄底 span 机制`,
)
assert.ok(
  fs.readFileSync(VERDICT_FILE, "utf8").includes("case 53: {"),
  `${VERDICT_FILE} 的 mode 53 必须有独立的号码五行分支（不得落回号码池/生肖池通用分支）`,
)

console.log("shengshi8800 element verdict contract passed (mode 53 = 只按特码号码五行)")
