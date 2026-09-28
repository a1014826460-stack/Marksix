// twsaimahui 展示契约：
//   1) `061jy2x.js`（mode 251 家野两肖 / 容器 .l1）——【组名+两肖】、命中才高亮、
//      未开奖不显示判定也不高亮；
//   2) `023sanqibizhong.js`（mode 197 四肖三期内必出 / 容器 .l21）——窗口内每期各自
//      显示开奖与判定，特码/特肖取开奖串最后一项；
//   3) compat 路由的字段来源：getJyxiao2 的 content 必须由后端 `title`（组名|组成员）组装，
//      getSanqiXiao4new 必须新增 `periods`（逐期开奖）且既有字段不变。
//
// 口径依据：docs/prediction-display-standard.md（S1/S2/S3/S4）与
// 用户死线「命中的生肖/号码才黄色高亮，不命中的一律不高亮；未开奖不显示判定也不高亮」。
import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

const JS_DIR = "frontend/public/vendor/twsaimahui/static/js"
const ROUTE = "frontend/app/api/kaijiang/[[...path]]/route.ts"

const YELLOW = "background-color:\\s*#FFFF00"

function runScript(file, { payload, container, loader }) {
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
  sandbox.window.apiClient = { get: () => ({ done: (cb) => { cb({ data: payload }); return { fail: () => {} } }, fail: () => {} }) }
  vm.createContext(sandbox)
  vm.runInContext(fs.readFileSync(file, "utf8"), sandbox, { filename: file })
  assert.ok(captured.html.includes(container), `${file} 没有渲染到 ${container}`)
  return captured.html
}

/** 拆出「一期」的渲染结果：{ term, text, yellow: [...] }。text 去标签后去掉所有空白。 */
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

// ── 1. 061jy2x.js：mode 251 家野两肖 ──────────────────────────────
// 数据取自真实接口（content = 组名|组成员，xiao = 两肖）。
const jyxiao2Payload = [
  { content: '["家禽|牛,马,羊,鸡,狗,猪"]', res_code: "32,36,39,05,33,37,09", res_sx: "猪,羊,龙,虎,狗,马,狗", term: "189", xiao: "马,虎" }, // 特肖狗 ∈ 家禽 → 准（高亮组名）
  { content: '["野兽|鼠,虎,兔,龙,蛇,猴"]', res_code: "20,19,38,35,23,42,45", res_sx: "猪,鼠,蛇,猴,猴,牛,狗", term: "190", xiao: "虎,马" }, // 特肖狗 ∉ 野兽∪两肖 → 错（零黄底）
  { content: '["野兽|鼠,虎,兔,龙,蛇,猴"]', res_code: "07,27,02,36,49,45,38", res_sx: "鼠,龙,蛇,羊,马,狗,蛇", term: "188", xiao: "虎,马" }, // 特肖蛇 ∈ 野兽 → 准（高亮组名）
  { content: '["家禽|牛,马,羊,鸡,狗,猪"]', res_code: "03,28,07,20,39,30,29", res_sx: "龙,兔,鼠,猪,龙,牛,虎", term: "187", xiao: "马,虎" }, // 特肖虎 ∈ 两肖 → 准（高亮该生肖）
  { content: '["家禽|牛,马,羊,鸡,狗,猪"]', res_code: "", res_sx: "", term: "191", xiao: "马,狗" }, // 未开奖
]

const jyxiao2Html = runScript(`${JS_DIR}/061jy2x.js`, { payload: jyxiao2Payload, container: "189期" })
const jyxiao2Rows = rowsOf(jyxiao2Html)
assert.equal(jyxiao2Rows.length, 5, "家野两肖应渲染 5 期")

const [r189, r190, r188, r187, r191] = jyxiao2Rows
assert.equal(r189.text, "189期家畜野兽:【家禽+马虎】开:狗09准",
  "命中组内生肖 → 准，且展示值只能是【组名+两肖】，不能把 6 肖重复两遍")
assert.deepEqual(r189.yellow, ["家禽"], "命中来自组内成员 → 高亮组名")

assert.equal(r190.text, "190期家畜野兽:【野兽+虎马】开:狗45错", "未命中 → 错")
assert.deepEqual(r190.yellow, [], "未命中必须零黄底")

assert.equal(r188.text, "188期家畜野兽:【野兽+虎马】开:蛇38准")
assert.deepEqual(r188.yellow, ["野兽"], "命中来自组内成员 → 高亮组名")

assert.equal(r187.text, "187期家畜野兽:【家禽+马虎】开:虎29准")
assert.deepEqual(r187.yellow, ["虎"], "命中来自两肖 → 高亮该生肖")

assert.equal(r191.text, "191期家畜野兽:【家禽+马狗】开:待开奖", "未开奖 → 显示待开奖")
assert.equal(/[准错]/.test(r191.text), false, "未开奖不得显示判定")
assert.deepEqual(r191.yellow, [], "未开奖不得高亮")

// 特肖/特码取开奖串最后一项（不是第一项）
assert.ok(r190.text.includes("狗45"), "特肖/特码必须取开奖串最后一项")
// 展示值必须是【组名+两肖】（1 个分组名 + 恰好 2 个生肖），不能把 6 肖原样当两肖用
for (const row of jyxiao2Rows) {
  const shown = row.text.match(/【([^】]*)】/)
  assert.ok(shown, `${row.text} 缺少【组名+两肖】展示值`)
  assert.match(shown[1], /^[^+]{1,4}\+[^+]{2}$/, `展示值必须是「组名+两肖」，实际 ${shown[1]}`)
}

// ── 2. 023sanqibizhong.js：mode 197 四肖三期内必出 ────────────────
// periods = 接口新增的逐期开奖字段（真实数据）。
const sanqiPayload = [
  {
    content: '["兔|04,16,28,40","马|01,13,25,37,49","羊|12,24,36,48","狗|09,21,33,45"]',
    name: "191-193",
    res_code: "",
    res_sx: "",
    periods: [{ term: "191", res_code: "", res_sx: "" }],
  },
  {
    content: '["牛|06,18,30,42","马|01,13,25,37,49","狗|09,21,33,45","鼠|07,19,31,43"]',
    name: "188-190",
    res_code: "20,19,38,35,23,42,45",
    res_sx: "猪,鼠,蛇,猴,猴,牛,狗",
    periods: [
      { term: "188", res_code: "07,27,02,36,49,45,38", res_sx: "鼠,龙,蛇,羊,马,狗,蛇" },
      { term: "189", res_code: "32,36,39,05,33,37,09", res_sx: "猪,羊,龙,虎,狗,马,狗" },
      { term: "190", res_code: "20,19,38,35,23,42,45", res_sx: "猪,鼠,蛇,猴,猴,牛,狗" },
    ],
  },
]

const sanqiHtml = runScript(`${JS_DIR}/023sanqibizhong.js`, { payload: sanqiPayload, container: "191期" })
const sanqiRows = rowsOf(sanqiHtml)
assert.equal(sanqiRows.length, 6, "两个窗口各 3 期 → 6 行")

// 顺序：最新期在上
assert.deepEqual(
  sanqiRows.map((row) => row.term),
  ["193", "192", "191", "190", "189", "188"],
  "窗口内按期号降序渲染"
)

const byTerm = Object.fromEntries(sanqiRows.map((row) => [row.term, row]))
assert.equal(byTerm["190"].text, "190期牛马狗鼠开:狗45准", "190 期特肖狗 ∈ 候选 → 准")
assert.deepEqual(byTerm["190"].yellow, ["狗"], "命中生肖标黄（每期独立）")
assert.equal(byTerm["189"].text, "189期牛马狗鼠开:狗09准")
assert.deepEqual(byTerm["189"].yellow, ["狗"])
assert.equal(byTerm["188"].text, "188期牛马狗鼠开:蛇38错", "188 期特肖蛇 ∉ 候选 → 错")
assert.deepEqual(byTerm["188"].yellow, [], "判错的一期整行零黄底（S3）")
for (const term of ["191", "192", "193"]) {
  assert.equal(byTerm[term].text, `${term}期兔马羊狗开:待开奖`, "未开奖期显示待开奖")
  assert.equal(/[准错]/.test(byTerm[term].text), false, "未开奖期不得显示判定（S1）")
  assert.deepEqual(byTerm[term].yellow, [], "未开奖期不得高亮")
}

// ── 3. compat 路由字段来源（静态不变量） ─────────────────────────
const routeSource = fs.readFileSync(ROUTE, "utf8")
assert.ok(/row\.title/.test(routeSource), "getJyxiao2 的 content 必须来自后端 title（组名|组成员）")
assert.ok(/function sanqiWindowPeriods\(/.test(routeSource), "缺失 sanqiWindowPeriods：窗口逐期开奖未组装")
assert.ok(/periods:\s*sanqiWindowPeriods\(bucket\)/.test(routeSource), "filterSanqiDisplayRows 未把逐期开奖带出")
assert.ok(/periods:\s*Array\.isArray\(row\.periods\)/.test(routeSource), "mapSanqiTwsaimahui 未透出新增字段 periods")

console.log("twsaimahui 家野两肖 / 四肖三期内必出 展示契约通过")
