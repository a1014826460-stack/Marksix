/**
 * twsaimahui「平特」模块七码口径契约（2026-09-30）
 * ---------------------------------------------------------------------------
 * 规则（用户口径 + 后端 `flat_zodiac` / `flat_tail`）：所有「x平特x」模块的命中判定
 * 都要跟**本期七个开奖号码**比，不是只看最后一个特码/特尾。
 *
 * 真实数据（web=6 / type=3 / 2026 年第 190 期）：
 *   res_code = 20,19,38,35,23,42,45   res_sx = 猪,鼠,蛇,猴,猴,牛,狗
 *   特码 = 45（狗，尾 5）；第一个平码 = 20（猪，尾 0）
 *
 * 修复前：【成语平特尾】只比 `code`（特码）的尾数 —— 「零」（尾 0）遇上 20（平码，尾 0）
 * 判「错」，「六」（尾 6）遇上 36（平码，尾 6）也判「错」；用户报障的 271 期即此类。
 * 断言分两层：
 *   1. 源码层：平特模块的命中必须遍历整期开奖串（不得只取 `codeSplit[last]` / `sxSplit[last]`）；
 *   2. 渲染层：在 vm 里真跑渲染器，用「只有平码命中」的数据断言判为命中、且只点亮命中项。
 */
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import vm from "node:vm"

const JS_DIR = "frontend/public/vendor/twsaimahui/static/js"

const RES_CODE = "20,19,38,35,23,42,45"
const RES_SX = "猪,鼠,蛇,猴,猴,牛,狗"

// ── 1. 源码层：平特命中必须看整期开奖串 ──────────────────────────────
function readModule(name) {
  return fs.readFileSync(path.join(JS_DIR, name), "utf8")
}

{
  const chengyupw = readModule("068chengyupw.js")
  assert.match(
    chengyupw,
    /for \(let k = 0; k < codeSplit\.length; k\+\+\)/,
    "成语平特尾必须遍历本期七个开奖号码（codeSplit 全串），不能只看特码",
  )
  assert.match(
    chengyupw,
    /charAt\(digits\.length - 1\) === num/,
    "成语平特尾必须用「号码末位 == 成语对应尾数」判定",
  )
  assert.doesNotMatch(
    chengyupw,
    /tail\s*===\s*num/,
    "成语平特尾不得再退化成「只比特码尾数」（旧实现 tail === num）",
  )
  const pt1w = readModule("022pt1w.js")
  assert.match(pt1w, /charAt\(digits\.length - 1\) === digit/, "平特一尾必须按号码末位（尾数）比对")
  assert.doesNotMatch(pt1w, /getZjIndex\(xiao\[i\],\s*codeSplit\)/, "平特一尾不得再用子串包含判定（19 会被候选尾 1 误命中）")
  for (const [file, pattern, why] of [
    ["065yiziptx.js", /getZjIndex\(xiao\[0\],\s*sxSplit\)/, "平特一肖必须按整期七肖（sxSplit）判定"],
    ["074ptyx.js", /getZjIndex\(xiao\[i\],\s*sxSplit\)/, "平特一肖必须按整期七肖（sxSplit）判定"],
    ["066chengyupx.js", /getZjIndex\(d\.title,\s*sxSplit\)/, "成语平特肖必须按整期七肖（sxSplit）判定"],
    ["067sanzipw.js", /getZjIndex\(xiao\[i\],\s*sxSplit\)/, "平特三肖必须按整期七肖（sxSplit）判定"],
  ]) {
    assert.match(readModule(file), pattern, `${file}: ${why}`)
  }
  for (const file of ["065yiziptx.js", "074ptyx.js", "066chengyupx.js", "067sanzipw.js"]) {
    assert.doesNotMatch(
      readModule(file),
      /getZjIndex\([^,]+,\s*\[\s*sxSplit\[sxSplit\.length\s*-\s*1\]\s*\]\)/,
      `${file}: 不得只拿特肖参与判定`,
    )
  }
}

// ── 2. 渲染层：真跑渲染器 ────────────────────────────────────────────
function renderModule(file, { content, title, resCode = RES_CODE, resSx = RES_SX }) {
  const source = fs.readFileSync(path.join(JS_DIR, file), "utf8")
  const captured = []

  const jquery = () => ({
    html(value) {
      if (value !== undefined) captured.push(String(value))
      return this
    },
    append(value) {
      if (value !== undefined) captured.push(String(value))
      return this
    },
  })
  jquery.ajax = () => ({})

  const sandbox = {
    $: jquery,
    jQuery: jquery,
    httpApi: "",
    web: "6",
    type: "3",
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
  // util.js 提供 getZjIndex / safeParseJSON 等公共工具，先注入。
  vm.runInContext(fs.readFileSync(path.join(JS_DIR, "util.js"), "utf8"), sandbox, { filename: "util.js" })

  const responses = [{ term: "190", content, title, res_code: resCode, res_sx: resSx }]
  let driven = false
  jquery.ajax = function (options) {
    driven = true
    if (typeof options.success === "function") options.success({ data: responses })
    return {}
  }
  vm.runInContext(source, sandbox, { filename: file })
  assert.ok(driven, `${file}: 模块必须发起一次 $.ajax`)
  assert.ok(captured.length > 0, `${file}: 渲染器必须注入 HTML`)
  return captured.join("\n")
}

function assertHit(html, token, label) {
  // 各模块的黄底写法有 `background-color: #FFFF00` / `background-color:#FFFF00` 两种。
  const pattern = new RegExp(`<span style="background-color:\\s*#FFFF00[^"]*">${token}</span>`)
  assert.ok(
    pattern.test(html),
    `${label}: 命中项「${token}」必须标黄，实际：\n${html.slice(0, 400)}`,
  )
}

// 2a. 成语平特尾：命中来自**平码**（尾 0 的 20 / 尾 6 的 36），不是特码 45（尾 5）。
{
  const zero = renderModule("068chengyupw.js", { content: "", title: "成语零尾" })
  assert.ok(zero.includes("准"), `尾 0 命中平码 20 → 必须判「准」：\n${zero.slice(0, 300)}`)
  assertHit(zero, "成语零尾", "成语平特尾（平码命中）")
  assert.ok(zero.includes("狗45"), `开奖段仍显示本期特码：\n${zero.slice(0, 300)}`)

  const six = renderModule("068chengyupw.js", { content: "", title: "成语六尾", resCode: "36,19,38,35,23,42,45" })
  assert.ok(six.includes("准"), `第一个开奖号码 36（尾 6）→ 必须判「准」：\n${six.slice(0, 300)}`)
  assertHit(six, "成语六尾", "成语平特尾（用户报障样例）")

  const miss = renderModule("068chengyupw.js", { content: "", title: "成语一尾" })
  assert.ok(miss.includes("错"), `七码里没有尾 1 → 必须判「错」：\n${miss.slice(0, 300)}`)
  assert.ok(!miss.includes("background-color: #FFFF00"), `判「错」不得有黄底：\n${miss.slice(0, 300)}`)
}

// 2b. 成语平特肖 / 平特一肖 / 平特三肖：命中来自平码「鼠」（特肖是狗）。
{
  const chengyupx = renderModule("066chengyupx.js", { content: "", title: "投鼠忌器" })
  assert.ok(chengyupx.includes("准"), `成语里的「鼠」是平码 → 必须判「准」：\n${chengyupx.slice(0, 300)}`)
  assertHit(chengyupx, "投鼠忌器", "成语平特肖（平码命中）")

  const ptyx = renderModule("074ptyx.js", { content: "鼠" })
  assert.ok(ptyx.includes("准"), `平特一肖「鼠」是平码 → 必须判「准」：\n${ptyx.slice(0, 300)}`)
  assertHit(ptyx, "鼠", "平特一肖（平码命中）")

  const yiziptx = renderModule("065yiziptx.js", { content: "鼠" })
  assert.ok(yiziptx.includes("准"), `平特一肖「鼠」是平码 → 必须判「准」：\n${yiziptx.slice(0, 300)}`)

  const sanzipw = renderModule("067sanzipw.js", { content: "狗,猴,龙" })
  // 狗是特肖、猴是平码 → 两项都命中；龙不在七肖里 → 不得标黄。
  assertHit(sanzipw, "猴", "平特三肖（平码命中）")
  assert.ok(
    !sanzipw.includes('background-color: #FFFF00">龙'),
    "平特三肖未命中的候选「龙」不得标黄",
  )
}

// 2c. 平特一尾：只看**尾数**（19 的尾数是 9，不能被候选尾 1 误命中）。
{
  const miss = renderModule("022pt1w.js", { content: JSON.stringify(["1尾|01,11,21,31,41"]) })
  assert.ok(miss.includes("不中"), `七码里没有尾 1（19 的尾数是 9）→ 必须「不中」：\n${miss.slice(0, 300)}`)
  assert.ok(!miss.includes("background-color: #FFFF00"), `不中不得有黄底：\n${miss.slice(0, 300)}`)

  const hit = renderModule("022pt1w.js", { content: JSON.stringify(["5尾|05,15,25,35,45"]) })
  assert.ok(hit.includes("中"), `45 的尾数是 5 → 必须「中」：\n${hit.slice(0, 300)}`)
}

console.log("twsaimahui-flat-verdict-contract: OK（平特肖/平特尾均按七个开奖号码判定）")
