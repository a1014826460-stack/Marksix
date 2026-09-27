// 全站预测判定契约（tw8800 / shengshi8800）
//
// 需求：判断正确才显示「准」，不正确则不显示（本实现统一显示「错」，
// 未开奖与无法判定一律不显示判定文字）。
//
// 本契约做两件事：
//   1. 逻辑用例：对统一判定函数 legacyPredictionVerdict.verdictOf 做正反用例；
//   2. 静态不变量：所有预测渲染脚本的 live 代码里，不得再把「准」写死在结果旁，
//      且必须调用统一判定。
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import vm from "node:vm"

const JS_DIR = "frontend/public/vendor/shengshi8800/static/js"
const VERDICT_FILE = `${JS_DIR}/legacy-prediction-verdict.js`

const sandbox = { window: {} }
vm.createContext(sandbox)
vm.runInContext(fs.readFileSync(VERDICT_FILE, "utf8"), sandbox)
const { verdictOf, verdictText, verdictHit } = sandbox.window.legacyPredictionVerdict

function row(content, resCode, resSx, extra = {}) {
  return { content, res_code: resCode, res_sx: resSx, ...extra }
}

// ── 1. 逻辑用例 ──────────────────────────────────────────────

// 号码池类：命中/未命中必须区分
// mode 63 后端按「特码生肖落入候选生肖」判定（家畜池 vs 野兽池，两池互补），
// 故对 63 这类生肖池结构，用特肖判断；纯号码池（12/54/151 等）用特码判断。
assert.equal(verdictOf(63, row('["家禽|牛,狗,猪,羊,马,鸡"]', "20", "猪,鼠,蛇,猴,猴,牛,狗")), "ok",
  "mode 63: 特肖狗 在家畜池 -> ok")
assert.equal(verdictOf(63, row('["野兽|兔,猴,虎,蛇,鼠,龙"]', "20", "猪,鼠,蛇,猴,猴,牛,狗")), "miss",
  "mode 63: 特肖狗 不在野兽池 -> miss")
assert.equal(verdictOf(63, row('["野兽|兔,猴,虎,蛇,鼠,龙"]', "38", "猪,鼠,蛇,猴,猴,牛,鼠")), "ok",
  "mode 63: 特肖鼠 在野兽池 -> ok")

assert.equal(verdictOf(54, row('["4尾|04,14,24,34,44"]', "24", "猪,鼠,蛇,猴,猴,牛,鼠")), "ok",
  "mode 54: 4尾含24 -> ok")
assert.equal(verdictOf(54, row('["4尾|04,14,24,34,44"]', "20", "猪,鼠,蛇,猴,猴,牛,狗")), "miss",
  "mode 54: 4尾不含20 -> miss")

assert.equal(verdictOf(12, row('["3头|30,31,32,33,34,35,36,37,38,39"]', "35", "x,x,x,x,x,x,x")), "ok",
  "mode 12: 3头含35 -> ok")
assert.equal(verdictOf(12, row('["3头|30,31,32,33,34,35,36,37,38,39"]', "21", "x,x,x,x,x,x,x")), "miss",
  "mode 12: 3头不含21 -> miss")

assert.equal(verdictOf(151, row('["鼠|07,19,31,43", "羊|12,24,36,48"]', "38", "x,x,x,x,x,x,x")), "miss",
  "mode 151: 号码不在任一池 -> miss")
assert.equal(verdictOf(151, row('["鼠|07,19,31,43", "羊|12,24,36,48"]', "43", "x,x,x,x,x,x,x")), "ok",
  "mode 151: 43 在鼠池 -> ok")

// 生肖集合类
assert.equal(verdictOf(42, row("兔,虎,猪", "29", "x,x,x,x,x,x,虎")), "ok", "mode 42: 特肖虎在集合 -> ok")
assert.equal(verdictOf(42, row("兔,虎,猪", "21", "x,x,x,x,x,x,鼠")), "miss", "mode 42: 特肖鼠不在集合 -> miss")
assert.equal(verdictOf(46, row("猴,鼠,羊,猪,马,狗", "38", "x,x,x,x,x,x,蛇")), "miss", "mode 46 -> miss")
assert.equal(verdictOf(46, row("猴,鼠,羊,猪,马,狗", "45", "x,x,x,x,x,x,狗")), "ok", "mode 46 -> ok")

// 单双 / 大小
assert.equal(verdictOf(28, row('["单|01,03"]', "07", "x,x,x,x,x,x,鼠")), "ok", "mode 28: 单对07 -> ok")
assert.equal(verdictOf(28, row('["单|01,03"]', "08", "x,x,x,x,x,x,鼠")), "miss", "mode 28: 单对08 -> miss")
assert.equal(verdictOf(57, row('["大|25,26"]', "48", "x,x,x,x,x,x,鼠")), "ok", "mode 57: 大对48 -> ok")
assert.equal(verdictOf(57, row('["大|25,26"]', "07", "x,x,x,x,x,x,鼠")), "miss", "mode 57: 大对07 -> miss")
assert.equal(verdictOf(108, row('["小|01,02"]', "20", "x,x,x,x,x,x,鼠")), "ok", "mode 108 -> ok")
assert.equal(verdictOf(108, row('["小|01,02"]', "48", "x,x,x,x,x,x,鼠")), "miss", "mode 108 -> miss")

// 双组生肖
assert.equal(verdictOf(31, { xiao_1: "猴,鸡,狗,鼠", xiao_2: "虎,羊,龙,牛", res_code: "45", res_sx: "x,x,x,x,x,x,狗" }), "ok",
  "mode 31: 特肖狗在 xiao_1 -> ok")
assert.equal(verdictOf(31, { xiao_1: "猴,鸡,猪,蛇", xiao_2: "马,鼠,羊,龙", res_code: "23", res_sx: "x,x,x,x,x,x,虎" }), "miss",
  "mode 31: 特肖虎不在两组 -> miss")
assert.equal(verdictOf(45, { hei: "猪,狗,龙", bai: "鸡,羊,鼠", res_code: "45", res_sx: "x,x,x,x,x,x,狗" }), "ok",
  "mode 45: 特肖狗在 hei -> ok")
assert.equal(verdictOf(45, { hei: "猪,狗,龙", bai: "鸡,羊,鼠", res_code: "21", res_sx: "x,x,x,x,x,x,蛇" }), "miss",
  "mode 45: 特肖蛇不在两组 -> miss")

// 波色（与库内 res_color 一致：20 属蓝波，30 属红波）
assert.equal(verdictOf(38, row("红波,蓝波", "20", "x,x,x,x,x,x,猪")), "ok", "mode 38: 20 属蓝波 在候选 -> ok")
assert.equal(verdictOf(38, row("红波,绿波", "20", "x,x,x,x,x,x,猪")), "miss", "mode 38: 蓝波不在候选 -> miss")
assert.equal(verdictOf(38, row("红波,绿波", "30", "x,x,x,x,x,x,鼠")), "ok", "mode 38: 30 属红波 -> ok")

// 文本类 / 无预测值：不得显示判定
assert.equal(verdictOf(244, row("山深古木含秋色，夜久寒蛩伴客吟", "20", "x,x,x,x,x,x,猪")), "unknown",
  "mode 244 诗句无法核对 -> unknown")
assert.equal(verdictOf(62, { title: "欲钱解特诗", res_code: "20", res_sx: "x" }), "unknown",
  "mode 62 无候选 -> unknown")
assert.equal(verdictOf(59, row("独家幽默：段子", "20", "x,x,x,x,x,x,猪")), "unknown",
  "mode 59 无号码组 -> unknown")

// 未开奖：不得显示判定
assert.equal(verdictOf(42, row("兔,虎,猪", "", "")), "pending", "未开奖 -> pending")
assert.equal(verdictOf(28, row('["单|01,03"]', "", "")), "pending", "未开奖 -> pending")
assert.equal(verdictOf(63, row('["家禽|牛"]', "", "")), "pending", "未开奖 -> pending")

// 显示规则：只有 ok 显示「准」
assert.equal(verdictText("ok"), "准")
assert.equal(verdictText("miss"), "错")
assert.equal(verdictText("pending"), "")
assert.equal(verdictText("unknown"), "")
assert.equal(verdictHit("ok"), true)
assert.equal(verdictHit("miss"), false)
assert.equal(verdictHit("pending"), false)
assert.equal(verdictHit("unknown"), false)

// ── 2. 静态不变量：脚本不得再写死「准」 ──────────────────────

function stripComments(source) {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "")
}

const scripts = fs
  .readdirSync(JS_DIR)
  .filter((name) => name.endsWith(".js"))
  .filter((name) => name !== "legacy-prediction-verdict.js")
  .filter((name) => {
    const source = fs.readFileSync(path.join(JS_DIR, name), "utf8")
    return source.includes("api/kaijiang/")
  })

const offenders = []
for (const name of scripts) {
  const live = stripComments(fs.readFileSync(path.join(JS_DIR, name), "utf8"))
  const lines = live.split("\n")
  const hits = []
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index]
    if (!line.includes("准")) continue
    // 允许的唯一形态：判定三元里输出「准」
    const isVerdictTernary = /\?\s*['"]准['"]/.test(line) && /legacyPredictionVerdict|verdict/.test(line)
    const usesSharedVerdict = line.includes("verdictText")
    if (isVerdictTernary || usesSharedVerdict) continue
    // 「精准大小」这类词是模块名，不是判定输出
    if (/精准/.test(line) && !/['"]准['"]/.test(line)) continue
    hits.push(`${name}:${index + 1}: ${line.trim().slice(0, 90)}`)
  }
  if (hits.length) offenders.push(hits)
}

assert.deepEqual(
  offenders.flat(),
  [],
  `以下位置仍把「准」写死在结果旁（应改为判定输出）：\n${offenders.flat().join("\n")}`,
)

console.log(`legacy verdict contract passed (${scripts.length} 个脚本已接入统一判定)`)
