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
//   5. 四字玄机（mode 52）的候选 title/jiexi 成对，且相邻五期不重复。
import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

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
      (_match, head, params, tail) => head + params.replace(/:\s*[^,)]+/g, "") + tail)
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
  "globalThis.__tcbw = { COLOR_BY_CODE, waveLabelOfCode, halfWaveLabelOfCode, specialPartsOf, resolveJudgement, labelForCode, tiandiZodiacsOf }",
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

console.log(`twcaibawang verdict contract passed (${JUDGE_MODULES.length} 个判定模块)`)
