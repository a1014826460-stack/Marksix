// 台湾彩霸王（twcaibawang）命中高亮 / 判定契约。
//
// 需求：
//   1. 双波、四段中特、稳杀10码、四行中特、四头中特、六肖十八码、绝杀一波、
//      天地两肖、公开一肖一码、必杀一肖、双波12码、24码、三期4肖：
//      命中的波色 / 生肖 / 号码 / 五行 / 段数 / 头尾 / 天地肖 必须标黄，
//      判定文字固定为「对 / 错」（未开奖不显示），三期4肖未命中显示「中0期」；
//   2. 9肖中特：命中生肖标黄；
//   3. 绝杀一波只能出现一次；
//   4. 琴棋书画用「两行分组说明 + 每期一行」的新格式；
//   5. 四字玄机（mode 52）的候选 title/jiexi 成对，且相邻五期不重复；
//   6. 四行中特（mode 482）只按**特码号码五行**判定与标黄：特码 = res_code 最后一项，
//      命中 = 该号码五行 ∈ 预测四行，只标黄命中的那一行；未开奖不判定、零高亮；
//      「生肖五行 ∈ 四行但号码五行 ∉ 四行」必须判「错」（见第 6 节，真跑渲染函数）。
import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

import {
  assertSameGroups,
  codeToElement,
  executableSource,
  parseBackendGroups,
} from "./lib/element-authority.mjs"

const TSX = "frontend/components/twcaibawang/TwcaibawangHomeClient.tsx"
const source = fs.readFileSync(TSX, "utf8")

/** 从 `function name(` 开始取出完整函数源码（先配平形参括号，再配平函数体花括号）。 */
function extractFunction(text, name) {
  const header = `function ${name}(`
  const start = text.indexOf(header)
  assert.notEqual(start, -1, `${TSX} 里找不到 function ${name}`)

  // 形参列表里可能带泛型对象类型（如 `{ module_key: "tiandi_2xiao" }`），
  // 必须先跳过形参再找函数体，否则会误把类型字面量的 `}` 当成函数结束。
  let paren = 0
  let cursor = text.indexOf("(", start)
  for (; cursor < text.length; cursor++) {
    const ch = text[cursor]
    if (ch === "(") paren++
    else if (ch === ")") {
      paren--
      if (paren === 0) {
        cursor++
        break
      }
    }
  }

  let depth = 0
  for (let index = text.indexOf("{", cursor); index < text.length; index++) {
    const ch = text[index]
    if (ch === "{") depth++
    else if (ch === "}") {
      depth--
      if (depth === 0) return text.slice(start, index + 1)
    }
  }
  throw new Error(`function ${name} 花括号不配平`)
}

/** 去掉本次抽取的小函数里用到的少量 TS 注解。 */
function stripTs(text) {
  return text
    .replace(/(function\s+[A-Za-z_$][\w$]*\s*\()([^)]*)(\))/g,
      (_match, head, params, tail) =>
        head +
        params
          .replace(/:\s*[^,)]+/g, "")
          // TS 可选形参（`options?: {…}` → `options`）；形参块去掉了尾部 `)`
          .replace(/\?\s*(?=[,)]|$)/g, "") +
        tail)
    // 函数返回值注解（`): SourceRow[] {` → `) {`）
    .replace(/\)\s*:\s*[A-Za-z_$][\w$<>[\]|, .]*(?=\s*\{)/g, ")")
    .replace(/\b(const|let|var)\s+([A-Za-z_$][\w$]*)\s*:\s*[^=\n]+=/g, "$1 $2 =")
    .replace(/\s+as\s+[A-Za-z_$][\w$<>[\]|" ]*/g, "")
}

function section(text, name) {
  return extractFunction(text, name)
}

// ── 1. 模块接线：13 个模块 + 9肖中特必须走「对/错」判定 ──────────
const JUDGE_MODULES = [
  "renderShuangbo",       // 双波
  "renderSiduanzhongte",  // 四段中特
  "renderWensha10ma",     // 稳杀10码
  "renderSihangzhongte",  // 四行中特
  "renderSitouzhongte",   // 四头中特
  "renderLiuxiao18ma",    // 六肖十八码
  "renderJueshabanbo",    // 绝杀一波
  "renderTiandi2Xiao",    // 天地两肖
  "renderPublicYixiaoYima", // 公开一肖一码
  "renderJuesha1Xiao",    // 必杀一肖
  "renderShuangbo12Ma",   // 双波12码
  "renderMa24",           // 24码
]

const HIGHLIGHT_CALLS = ["#FFFF00", "highlightIf", "renderFontList", "renderDottedCodes", "renderDashCodes"]

for (const name of JUDGE_MODULES) {
  const body = section(source, name)
  assert.ok(body.includes("renderJudgeResult"), `${name} 必须用统一的「对/错」判定渲染`)
  assert.ok(
    HIGHLIGHT_CALLS.some((token) => body.includes(token)),
    `${name} 必须包含命中黄底高亮`,
  )
}

// 9肖中特走通用模块渲染（含逐肖标黄）
const generic = section(source, "renderGenericModule")
assert.ok(generic.includes("renderFontList"), "renderGenericModule 必须逐肖标黄（9肖中特）")
assert.ok(generic.includes("renderJudgeResult"), "renderGenericModule 必须输出「对/错」")

// 只允许出现「对 / 错」，不允许这些模块写「准」
for (const name of JUDGE_MODULES) {
  const body = section(source, name)
  assert.ok(!body.includes(">准<") && !body.includes("准</font>"), `${name} 不得输出「准」`)
}

// ── 2. 绝杀一波不得重复 ───────────────────────────────────────
const genericList = source.slice(
  source.indexOf("const GENERIC_MODULES"),
  source.indexOf("function escapeHtml")
)
assert.ok(!genericList.includes('mechanismKey: "jueshabanbo"'), "GENERIC_MODULES 不得再包含绝杀一波")
assert.equal(
  (source.match(/id="jsyb"/g) || []).length,
  1,
  "页面只能有一个 #jsyb（绝杀一波）容器",
)
assert.equal(
  (source.match(/renderJueshabanbo\(/g) || []).length,
  2,
  "renderJueshabanbo 只应有定义 + 一次调用",
)

// ── 3. 三期4肖：未命中显示「中0期」 ───────────────────────────
const sxjh3 = section(source, "renderSxjh3")
const sxjh3Live = sxjh3.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "")
assert.ok(sxjh3Live.includes("openedCount"), "renderSxjh3 必须区分「窗口未开奖」与「已开奖但未命中」")
assert.ok(!sxjh3Live.includes("中0期"), "「中0期」应由计数拼出而不是写死")
assert.ok(/`中\$\{group\.hitCount\}期`/.test(sxjh3Live), "renderSxjh3 必须按命中数拼出「中N期」")
assert.ok(sxjh3Live.includes('"中几期"'), "窗口内一期都没开奖时才显示「中几期」")
assert.ok(sxjh3.includes("highlightIf"), "三期4肖必须把命中生肖标黄")

// ── 4. 琴棋书画新格式 ─────────────────────────────────────────
const qinqi = section(source, "renderQinqi")
assert.ok(qinqi.includes("qinqi_reference"), "琴棋书画必须使用接口给出的四艺分组说明")
assert.ok(qinqi.includes("琴棋书画→"), "琴棋书画必须按「琴棋书画→画琴书开:鸡46准」格式渲染")
assert.ok(generic.includes('config.mechanismKey === "qinqi"'), "通用模块必须把 qinqi 交给 renderQinqi")
assert.ok(source.includes('renderQinqi(resolveModule(modules, "qinqi")'), "buildPageHtml 必须渲染琴棋书画")

// ── 5. 逻辑用例：从 TSX 抽出的纯函数 ──────────────────────────
const colorPuts = [...source.matchAll(/put\("([\d,]+)", "(red|blue|green)"\)/g)]
  .map((match) => [match[1], match[2]])
assert.equal(colorPuts.length, 3, "波色分组表必须恰好三组")

const tiandiMatch = source.match(/const TIANDI_ZODIACS[\s\S]*?\n\}/)
assert.ok(tiandiMatch, "找不到 TIANDI_ZODIACS")
const tiandiSource = tiandiMatch[0].replace(
  /const TIANDI_ZODIACS: Record<string, string\[\]> =/,
  "const TIANDI_ZODIACS ="
)

// 该站号码五行分组（四行中特 mode 482 的判定/标黄口径）。这里**真跑**唯一权威前端共享源
// `frontend/lib/element-number-groups.ts`（`twcaibawang-elements.ts` 现在只是它的再导出
// shim），而不是在测试里另抄一份表，保证「改回生肖五行」必定 FAIL。
const ELEMENTS_TS = "frontend/lib/twcaibawang-elements.ts"
const ELEMENT_GROUPS_TS = "frontend/lib/element-number-groups.ts"
const elementsShimSource = fs.readFileSync(ELEMENTS_TS, "utf8")
assert.ok(
  /from\s+["'](?:@\/lib\/element-number-groups|\.\/element-number-groups)["']/.test(
    elementsShimSource,
  ) &&
    elementsShimSource.includes("ELEMENT_NUMBER_GROUPS") &&
    elementsShimSource.includes("elementHitJudgement"),
  `${ELEMENTS_TS} 必须从 ${ELEMENT_GROUPS_TS} 再导出号码五行分组与命中判定`,
)
assert.ok(
  !/\bELEMENT_NUMBER_GROUPS\b[\w:,[\]<>()| '"=.]{0,100}\{/.test(elementsShimSource),
  `${ELEMENTS_TS} 不得再自带号码五行常量表`,
)
const elementsSource = executableSource(fs.readFileSync(ELEMENT_GROUPS_TS, "utf8"))
// 期望值唯一来源 = 后端权威常量（不在本契约里另抄 49 码表）。
const AUTHORITY_GROUPS = parseBackendGroups()
const AUTHORITY_BY_CODE = codeToElement(AUTHORITY_GROUPS)

const harness = [
  stripTs(section(source, "mapColorToWave")),
  "const COLOR_BY_CODE = (() => { const map = {}; const put = (codes, name) => { codes.split(',').forEach((code) => { map[code] = name }) };",
  ...colorPuts.map(([codes, name]) => `put("${codes}", "${name}");`),
  "return map; })();",
  stripTs(section(source, "waveLabelOfCode")),
  stripTs(section(source, "halfWaveLabelOfCode")),
  stripTs(section(source, "stripLeadingKai")),
  stripTs(section(source, "parseResultParts")),
  stripTs(section(source, "specialPartsOf")),
  stripTs(section(source, "resolveJudgement")),
  stripTs(section(source, "labelForCode")),
  tiandiSource,
  stripTs(section(source, "tiandiZodiacsOf")),
  // ── 四行中特：整段真跑渲染函数所需的依赖 ─────────────────────
  elementsSource,
  stripTs(section(source, "escapeHtml")),
  stripTs(section(source, "normalizePredictionText")),
  stripTs(section(source, "parseJsonStringArray")),
  stripTs(section(source, "sortRowsByTermDesc")),
  stripTs(section(source, "toSourceRows")),
  stripTs(section(source, "getRowContent")),
  stripTs(section(source, "parseLabelCodeEntries")),
  stripTs(section(source, "formatOpenResult")),
  stripTs(section(source, "renderResultWithCustomJudge")),
  stripTs(section(source, "renderJudgeResult")),
  stripTs(section(source, "getLotteryLiuheName")),
  stripTs(section(source, "renderTitleTable")),
  stripTs(section(source, "renderLiuhePredictionTitleTable")),
  stripTs(section(source, "renderSihangzhongte")),
  "globalThis.__tcbw = { COLOR_BY_CODE, waveLabelOfCode, halfWaveLabelOfCode, specialPartsOf, resolveJudgement, labelForCode, tiandiZodiacsOf, ELEMENT_NUMBER_GROUPS, ELEMENT_BY_CODE, elementOfCode, normalizeElementLabel, elementHitJudgement, renderSihangzhongte }",
].join("\n")

const sandbox = {}
vm.createContext(sandbox)
vm.runInContext(harness, sandbox)
const api = sandbox.__tcbw

// 波色分组：与库内 res_color 的标准分组一致
assert.equal(api.waveLabelOfCode("37"), "蓝波", "37 属蓝波")
assert.equal(api.waveLabelOfCode("24"), "红波", "24 属红波")
assert.equal(api.waveLabelOfCode("08"), "红波", "08 属红波")
assert.equal(api.waveLabelOfCode("12"), "红波", "12 属红波")
assert.equal(api.waveLabelOfCode("01"), "红波", "01 属红波")
assert.equal(api.waveLabelOfCode("38"), "绿波", "38 属绿波")
assert.equal(api.halfWaveLabelOfCode("37"), "蓝单")
assert.equal(api.halfWaveLabelOfCode("10"), "蓝双")

// 开奖结果解析：twcaibawang 的 result_text 是 `马37` / `开37马` 两种写法
assert.deepEqual({ ...api.specialPartsOf("马37", true) }, { code: "37", sx: "马" })
assert.deepEqual({ ...api.specialPartsOf("开37马", true) }, { code: "37", sx: "马" })
assert.deepEqual({ ...api.specialPartsOf("马37", false) }, { code: "", sx: "" })

// 判定优先级：接口给结论时用接口，接口为 null 时用本地复算
assert.equal(api.resolveJudgement(true, false), true, "接口 true 优先")
assert.equal(api.resolveJudgement(false, true), false, "接口 false 优先")
assert.equal(api.resolveJudgement(null, true), true, "接口 null 时用复算")
assert.equal(api.resolveJudgement(undefined, null), null)

// 段 / 行 / 头：找出包含特码的那一档
const entries = [
  { label: "1段", codes: ["01", "02", "03"] },
  { label: "2段", codes: ["04", "05", "06"] },
  { label: "3段", codes: ["07", "08", "09"] },
]
assert.equal(api.labelForCode(entries, "8"), "3段", "号码需补零后匹配")
assert.equal(api.labelForCode(entries, "09"), "3段")
assert.equal(api.labelForCode(entries, "49"), "")

// 天地肖分组
assert.deepEqual([...api.tiandiZodiacsOf("天肖")], ["兔", "马", "猴", "猪", "牛", "龙"])
assert.deepEqual([...api.tiandiZodiacsOf("地肖")], ["鼠", "虎", "蛇", "羊", "鸡", "狗"])

// ── 6. 四行中特（mode 482）只按**特码号码五行**判定与标黄 ──────────
//
// 背景：twcaibawang 的 mode 482 正文里的号码清单来自供应商的**生肖五行**
// （`fixed_data` sign='五行肖'）：`木|04,05,16,17,28,29,40,41`、`火|01,02,13,14,25,26,37,38,49`
// —— 只覆盖 48 码，且 05 虎算「木」（新表号码五行是金）、37 马算「火」（新表号码五行是土）、
// 24 羊算「土」（新表号码五行是木）。
// 旧实现用 `labelForCode(entries, hitCode)`（正文清单）定位命中行，于是：
//   · 号码五行命中但生肖五行不命中 → 该期「对」却零黄底；
//   · 生肖五行命中而号码五行不命中 → 黄底落在生肖那一行（用户报障）。
// 现在的口径：特码 = res_code 最后一项，命中 = 该号码五行 ∈ 预测四行，只标黄该行。
// 注：2026-09-29 号码五行整体改判为「新表」（相对上一版 25 码换组，`new(x) = old(x-1)`、
// 01 归水），6.3 的「生肖/号码五行分歧」样例已按新表重算（17 虎在新表下两个口径一致，
// 不再是分歧点，改用 05 虎）。
const LEGACY_ZODIAC_ELEMENT_GROUPS = {
  金: [10, 11, 22, 23, 34, 35, 46, 47],
  木: [4, 5, 16, 17, 28, 29, 40, 41],
  水: [7, 8, 19, 20, 31, 32, 43, 44],
  火: [1, 2, 13, 14, 25, 26, 37, 38, 49],
  土: [3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48],
}
const ALL_ELEMENTS = ["金", "木", "水", "火", "土"]

/** 该站真实正文形态（生肖五行的号码清单）。 */
function elementContent(labels, groups = LEGACY_ZODIAC_ELEMENT_GROUPS) {
  return `[${labels.map((label) => `"${label}|${groups[label].join(",")}"`).join(", ")}]`
}

function tcbwRow({ term, content, result, isOpened = true, isCorrect = null }) {
  return {
    term,
    prediction_text: content,
    result_text: result,
    is_opened: isOpened,
    is_correct: isCorrect,
    raw: { content },
  }
}

function renderSihangRows(rows) {
  return api.renderSihangzhongte({ mechanism_key: "sihangzhongte", history: rows }, 3)
}

function yellowLabels(html) {
  return [...html.matchAll(/background-color: #FFFF00">([^<]*)<\/span>/g)].map((match) => match[1])
}

/** 去掉标签后的可见文字（判定文字「对」被 font 包裹、「错」不被包裹）。 */
function plainText(html) {
  return html.replace(/<[^>]*>/g, "")
}

// 6.1 号码五行分组：与后端权威常量逐项一致（键顺序 / 每组顺序 / 49 码全覆盖 / 不重叠）
const PROBE_CODES = ["24", "37", "01", "05", "13", "03"]
assertSameGroups(
  // vm 里的对象来自另一个 realm，先 JSON 往返成本地普通对象。
  JSON.parse(JSON.stringify(api.ELEMENT_NUMBER_GROUPS)),
  AUTHORITY_GROUPS,
  `${ELEMENTS_TS}（四行中特口径）`,
)
assert.equal(Object.keys(api.ELEMENT_BY_CODE).length, 49, "号码 → 五行索引必须覆盖 49 码")
for (const code of PROBE_CODES) {
  assert.equal(
    api.elementOfCode(code),
    AUTHORITY_BY_CODE[code],
    `${code} 的号码五行应为 ${AUTHORITY_BY_CODE[code]}（后端权威值）`,
  )
}
assert.equal(api.elementOfCode(""), "", "空号码不得回退到生肖五行")
assert.equal(api.elementHitJudgement([], "37"), null, "没有预测标签时不可判定")
assert.equal(api.elementHitJudgement(["木"], ""), null, "没有特码时不可判定")

// 6.2 需求②：号码五行 ∈ 四行 → 判「对」，且只标黄那一行
for (const code of PROBE_CODES) {
  const element = AUTHORITY_BY_CODE[code]
  const excluded = ALL_ELEMENTS.find((item) => item !== element)
  const predicted = ALL_ELEMENTS.filter((item) => item !== excluded)
  assert.ok(predicted.includes(element), `${code} 样例必须把 ${element} 排进预测四行`)
  const html = renderSihangRows([
    tcbwRow({ term: "270", content: elementContent(predicted), result: `兔${code}` }),
  ])
  assert.ok(plainText(html).includes(`${code}兔对`), `${code}（号码五行 ${element}）命中预测四行应判「对」`)
  assert.deepEqual(yellowLabels(html), [element], `${code} 只应标黄号码五行那一行（${element}）`)
}

// 6.3 需求①：生肖五行 ∈ 四行、号码五行 ∉ 四行 → 必须判「错」，零黄底
// 05 虎：生肖五行 = 木（旧正文 `木|04,05,16,17,28,29,40,41`），新表号码五行 = 金
// 24 羊：旧正文把 24 放进「土」（生肖五行）；新表号码五行 = 木
for (const [code, zodiac, zodiacElement, predicted] of [
  ["05", "虎", "木", ["木", "水", "火", "土"]],
  ["24", "羊", "土", ["土", "金", "水", "火"]],
]) {
  const numberElement = AUTHORITY_BY_CODE[code]
  assert.equal(api.elementOfCode(code), numberElement, `${code} 号码五行应为 ${numberElement}（后端权威值）`)
  assert.ok(
    LEGACY_ZODIAC_ELEMENT_GROUPS[zodiacElement].includes(Number(code)),
    `前提：供应商旧正文把 ${code} 归到 ${zodiacElement}（生肖五行）`,
  )
  assert.ok(predicted.includes(zodiacElement), `前提：${zodiacElement}（生肖五行）在预测四行内`)
  assert.ok(!predicted.includes(numberElement), `前提：${numberElement}（号码五行）不在预测四行内`)
  // 接口即使（旧口径 / 快照缓存）说「对」，也必须以号码五行为准改判「错」
  for (const apiValue of [null, true]) {
    const html = renderSihangRows([
      tcbwRow({
        term: "270",
        content: elementContent(predicted),
        result: `${zodiac}${code}`,
        isCorrect: apiValue,
      }),
    ])
    assert.ok(
      plainText(html).includes(`${code}${zodiac}错`),
      `${code}（生肖五行 ${zodiacElement} ∈ 四行、号码五行 ${numberElement} ∉ 四行）必须判「错」（接口值 ${apiValue}）`,
    )
    assert.deepEqual(yellowLabels(html), [], `${code} 判「错」时不得有任何黄底`)
  }
}

// 6.4 需求③：未开奖不显示判定、零高亮
const unopened = renderSihangRows([
  tcbwRow({
    term: "271",
    content: elementContent(["木", "金", "水", "土"]),
    result: "待开奖",
    isOpened: false,
  }),
])
assert.ok(unopened.includes("??????"), "未开奖只显示开奖占位")
assert.ok(
  !plainText(unopened).includes("对") && !plainText(unopened).includes("错"),
  "未开奖不得显示「对 / 错」",
)
assert.deepEqual(yellowLabels(unopened), [], "未开奖零高亮")

// 6.5 需求③：号码五行不在预测四行 → 判「错」且零黄底
const missHtml = renderSihangRows([
  tcbwRow({ term: "269", content: elementContent(["金", "水", "火", "木"]), result: "马37" }),
])
assert.ok(plainText(missHtml).includes("37马错"), "37 号码五行 = 土，不在 金/水/火/木 里应判「错」")
assert.deepEqual(yellowLabels(missHtml), [], "错期零黄底")

// 6.6 结构约束：四行中特不得再用正文号码清单（生肖五行）定位命中行
const sihangBody = section(source, "renderSihangzhongte")
assert.ok(
  !sihangBody.includes("labelForCode("),
  "四行中特不得再用正文号码清单（生肖五行）定位命中行",
)
assert.ok(sihangBody.includes("elementHitJudgement"), "四行中特必须用号码五行判定命中")
assert.ok(sihangBody.includes("elementOfCode"), "四行中特必须用号码五行决定标黄落点")

console.log(`twcaibawang verdict contract passed (${JUDGE_MODULES.length} 个判定模块)`)

