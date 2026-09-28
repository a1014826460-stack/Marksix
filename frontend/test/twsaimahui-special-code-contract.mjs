// 台湾赛马会（twsaimahui）开奖号码口径契约。
//
// 缺陷（2026-09-28 修复）：12 个模块把 `res_code` / `res_sx` 的**第 1 项**当成特码/特肖，
// 而本项目口径是**最后一项**才是特码/特肖（`res_code` 与 `lottery_draws.numbers` 同序）。
// 结果【三头中特】【绝杀三尾】等模块展示的开奖号码是第一个平码，不是特码。
//
// 真实数据（web=6 / type=3 / 2026 年第 190 期）：
//   res_code = 20,19,38,35,23,42,45   res_sx = 猪,鼠,蛇,猴,猴,牛,狗
//   特码 = 45（狗）；错误实现会渲染成 20（猪）。
//
// 断言分两层：
//   1. 源码层：所有模块脚本与 bundle 都不得再出现 `codeSplit[0]` / `sxSplit[0]`；
//   2. 渲染层：在 vm 里真跑每个模块的渲染器（stub `$` / httpApi / web / type），
//      断言渲染结果里出现「狗45」而**不出现**「猪20」。
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import vm from "node:vm"

const JS_DIR = "frontend/public/vendor/twsaimahui/static/js"

// 真实数据（第 190 期）：特码是最后一项 45/狗，第一个平码是 20/猪。
const SPECIAL_CODE = "45"
const SPECIAL_ZODIAC = "狗"
const WRONG_CODE = "20"
const WRONG_ZODIAC = "猪"
const RES_CODE = "20,19,38,35,23,42,45"
const RES_SX = "猪,鼠,蛇,猴,猴,牛,狗"

/** 本轮修复的 12 个模块 → 触发它的接口。 */
const MODULES = [
  { file: "004danshuang.js", endpoint: "getDsxiao", num: "2", content: "双生肖|鼠,虎,龙,马,猴,狗", xiao: "兔,鸡" },
  { file: "015sha3w.js", endpoint: "getShaWei", num: "3", content: JSON.stringify(["1尾|01,11,21,31,41"]) },
  { file: "016sha3x.js", endpoint: "getShaXiao", num: "3", content: "猴,兔,猪" },
  { file: "024santou.js", endpoint: "getTou", num: "3", content: JSON.stringify(["0头|01,02,03,04,05,06,07,08,09", "2头|20,21,22,23,24,25,26,27,28,29", "4头|40,41,42,43,44,45,46,47,48,49"]) },
  { file: "035ma16.js", endpoint: "getCode", num: "16", content: "01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16" },
  { file: "054sbanbo.js", endpoint: "getShaBanbo", num: "1", content: JSON.stringify(["红单|01,07,13,19,23,29,35,45"]) },
  { file: "055sbands.js", endpoint: "getShaBds", num: "1", content: JSON.stringify(["红单|01,07,13,19,23,29,35,45"]) },
  { file: "056s7m.js", endpoint: "getShama", num: "7", content: "01,17,14,48,36,24,22" },
  { file: "057s1x.js", endpoint: "getShaXiao", num: "1", content: "猴" },
  { file: "058s2x.js", endpoint: "getShaXiao", num: "2", content: "猴,兔" },
  { file: "068chengyupw.js", endpoint: "getCyptwei", num: "2", content: JSON.stringify(["1尾|01,11,21,31,41"]), title: "成语一尾" },
  { file: "071ds.js", endpoint: "danshuang", num: "2", content: JSON.stringify(["单|01,03,05,07,09,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47,49"]) },
]

// ── 1. 源码层：不得再按第 1 项取特码 ─────────────────────────────────
const targets = [
  ...fs.readdirSync(JS_DIR).filter((n) => /^0\d{2}.*\.js$/.test(n)).map((n) => path.join(JS_DIR, n)),
  ...fs.readdirSync(JS_DIR).filter((n) => /^bundle-[a-f0-9]+\.js$/.test(n)).map((n) => path.join(JS_DIR, n)),
]
assert.ok(targets.length > 0, "找不到任何 twsaimahui 模块脚本")

for (const file of targets) {
  const text = fs.readFileSync(file, "utf8")
  assert.doesNotMatch(
    text,
    /codeSplit\[\s*0\s*\]/,
    `${file}: 特码必须取 res_code 最后一项，不得取 codeSplit[0]`,
  )
  assert.doesNotMatch(
    text,
    /sxSplit\[\s*0\s*\]/,
    `${file}: 特肖必须取 res_sx 最后一项，不得取 sxSplit[0]`,
  )
}

// ── 2. 渲染层：真跑渲染器 ────────────────────────────────────────────
/** 建一个捕获 `.html()` 注入内容的 jQuery stub，并驱动 $.ajax 成功回调。 */
function render(file, endpoint, num, content, xiao, title) {
  const source = fs.readFileSync(path.join(JS_DIR, file), "utf8")
  const captured = []

  const ajax = () => ({})
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
  jquery.ajax = function (options) {
    ajax(options)
    return {}
  }

  const sandbox = {
    $: jquery,
    jQuery: jquery,
    httpApi: "",
    web: "6",
    type: "3",
    // 站点公共工具（static/js/util.js 提供）；渲染器直接调用，必须注入。
    safeParseJSON: (value, fallback) => {
      try {
        const parsed = JSON.parse(value)
        return parsed === null || parsed === undefined ? fallback : parsed
      } catch {
        return fallback
      }
    },
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
    encodeURIComponent,
    decodeURIComponent,
    setTimeout,
    clearTimeout,
  }
  sandbox.window = sandbox
  sandbox.globalThis = sandbox

  // 站点公共脚本（common.js / legacy_runtime.js 等）在页面里先于模块加载，
  // 这里只需要「存在且不抛错」的桩；本契约关心的是开奖段取的哪一项。
  const noop = () => undefined
  for (const name of [
    "applyLotteryRegionTitlePrefix",
    "resolveLotteryRegion",
    "getLotteryRegionLabel",
    "formatLotteryIssue",
    "getRegionLabel",
    "lotteryRegionTitlePrefix",
    "safeJsonParse",
    "escapeHtmlText",
  ]) {
    sandbox[name] = noop
  }
  sandbox.document = {
    querySelector: () => null,
    querySelectorAll: () => [],
    getElementById: () => null,
    addEventListener: noop,
    createElement: () => ({ style: {}, setAttribute: noop, appendChild: noop }),
  }

  vm.createContext(sandbox)
  vm.runInContext(source, sandbox, { filename: file })

  // 取出模块注册的 ajax 配置并驱动成功回调（不同模块写法不同，统一从源码抓 url）。
  const responses = [
    { term: "190", content, xiao, title, res_code: RES_CODE, res_sx: RES_SX },
  ]
  let driven = false
  jquery.ajax = function (options) {
    driven = true
    if (typeof options.success === "function") {
      options.success({ data: responses })
    }
    return {}
  }
  // 重新执行一次，这次 ajax 会立即回调。
  vm.runInContext(source, sandbox, { filename: file })
  assert.ok(driven, `${file}: 模块必须发起一次 $.ajax`)

  assert.ok(
    captured.length > 0,
    `${file}: 渲染器必须把 HTML 注入到页面（未捕获到任何注入内容）`,
  )
  assert.ok(
    source.includes(endpoint),
    `${file}: 源码里应包含接口 ${endpoint}`,
  )
  assert.ok(num.length > 0, `${file}: num 参数缺失`)
  return captured.join("\n")
}

for (const mod of MODULES) {
  const html = render(mod.file, mod.endpoint, mod.num, mod.content, mod.xiao, mod.title)

  assert.ok(
    html.includes(`${SPECIAL_ZODIAC}${SPECIAL_CODE}`),
    `${mod.file}: 开奖段必须是特码「${SPECIAL_ZODIAC}${SPECIAL_CODE}」，实际渲染：\n${html.slice(0, 400)}`,
  )
  assert.ok(
    !html.includes(`${WRONG_ZODIAC}${WRONG_CODE}`),
    `${mod.file}: 不得把第一个平码「${WRONG_ZODIAC}${WRONG_CODE}」当成开奖号码：\n${html.slice(0, 400)}`,
  )
}

console.log(`twsaimahui-special-code-contract: OK (${MODULES.length} 个模块真跑渲染器)`)
