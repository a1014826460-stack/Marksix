// 大小 / 单双 系列「判定恒为正确」修复契约。
//
// 修复前的共同缺陷：
//   1) 高亮条件是「特码号码落在该池内」，而互补两池合起来覆盖 01..49，条件恒为真；
//   2) 模板（或共享的 getResult()）把「准」写死，判定环节根本不存在。
// 修复后统一走 legacy-prediction-verdict.js，按真实维度判定，未开奖不显示判定。
//
// 另外锁定一个回归：这些脚本曾经各自定义同名全局（`window.__sizeVerdict`、
// `window.__parityVerdict`），后加载的脚本会覆盖前一个的实现，导致模块按错误维度判定。
import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

const ROOT = "frontend/public/vendor/shengshi8800/static/js"
const VERDICT_FILE = `${ROOT}/legacy-prediction-verdict.js`

const sandbox = { window: {} }
vm.createContext(sandbox)
vm.runInContext(fs.readFileSync(VERDICT_FILE, "utf8"), sandbox)
const { verdictOf } = sandbox.window.legacyPredictionVerdict

function stripComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "")
}

// 大小系列：003dxzt.js（57 大小中特）、dx.js（108 大数小数）
const sizeFiles = [`${ROOT}/003dxzt.js`, `${ROOT}/dx.js`]
const sizeModes = [57, 108]

sizeFiles.forEach((file, index) => {
  const modeId = sizeModes[index]
  const row = (content, resCode) => ({ content, res_code: resCode, res_sx: "x,x,x,x,x,x,鼠" })

  assert.equal(verdictOf(modeId, row('["大|25,26"]', "48")), "ok", `${file}: 大 对 48`)
  assert.equal(verdictOf(modeId, row('["大|25,26"]', "07")), "miss", `${file}: 大 对 07`)
  assert.equal(verdictOf(modeId, row('["小|01,02"]', "07")), "ok", `${file}: 小 对 07`)
  assert.equal(verdictOf(modeId, row('["小|01,02"]', "48")), "miss", `${file}: 小 对 48`)
  assert.equal(verdictOf(modeId, row('["小|01,02"]', "24")), "ok", `${file}: 24 属小`)
  assert.equal(verdictOf(modeId, row('["大|25,26"]', "25")), "ok", `${file}: 25 属大`)
  assert.equal(verdictOf(modeId, row('["大|25,26"]', "")), "pending", `${file}: 未开奖`)
  assert.equal(verdictOf(modeId, row('["大|25,26"]', "？")), "pending", `${file}: 占位结果`)
  assert.equal(verdictOf(modeId, row('["单|01"]', "01")), "unknown", `${file}: 非大小内容不判定`)

  const live = stripComments(fs.readFileSync(file, "utf8"))
  assert.ok(!/开\$\{[^}]*\}准/.test(live), `${file}: 模板仍写死「准」`)
  assert.ok(live.includes("legacyPredictionVerdict"), `${file}: 模板未使用统一判定`)
  assert.ok(!/window\.__sizeVerdict/.test(live), `${file}: 仍在定义跨脚本冲突的 window.__sizeVerdict`)
})

// 单双中特（28 买啥开啥）：单值 单/双 预测，按奇偶判定
{
  const file = `${ROOT}/015maishazs.js`
  const row = (content, resCode) => ({ content, res_code: resCode, res_sx: "x,x,x,x,x,x,鼠" })

  assert.equal(verdictOf(28, row('["单|01,03"]', "07")), "ok", `${file}: 单 对 07`)
  assert.equal(verdictOf(28, row('["单|01,03"]', "08")), "miss", `${file}: 单 对 08`)
  assert.equal(verdictOf(28, row('["双|02,04"]', "08")), "ok", `${file}: 双 对 08`)
  assert.equal(verdictOf(28, row('["双|02,04"]', "07")), "miss", `${file}: 双 对 07`)
  assert.equal(verdictOf(28, row('["双|02,04"]', "")), "pending", `${file}: 未开奖`)
  assert.equal(verdictOf(28, row('["双|02,04"]', "？")), "pending", `${file}: 占位结果`)

  const live = stripComments(fs.readFileSync(file, "utf8"))
  assert.ok(!/开[^\n]{0,80}?准/.test(live), `${file}: 模板仍写死「准」`)
  assert.ok(live.includes("legacyPredictionVerdict"), `${file}: 模板未使用统一判定`)
  assert.ok(!/window\.__parityVerdict/.test(live), `${file}: 仍在定义跨脚本冲突的 window.__parityVerdict`)
}

// 单双四肖（31）：每期两组是变化的 4+4 生肖拆分，按「特肖是否落在两组内」判定
{
  const file = `${ROOT}/031dssx.js`
  const row = (one, two, resCode, resSx) => ({
    xiao_1: one,
    xiao_2: two,
    res_code: resCode,
    res_sx: resSx,
  })

  // 190 期真实数据：特肖狗 落在 xiao_1('猴,鸡,狗,鼠') -> 命中
  assert.equal(
    verdictOf(31, row("猴,鸡,狗,鼠", "虎,羊,龙,牛", "20,19,38,35,23,42,45", "猪,鼠,蛇,猴,猴,牛,狗")),
    "ok", `${file}: 特肖落单组`)
  assert.equal(
    verdictOf(31, row("虎,羊,龙,牛", "猴,鸡,狗,鼠", "20,19,38,35,23,42,45", "猪,鼠,蛇,猴,猴,牛,狗")),
    "ok", `${file}: 特肖落双组`)
  // 188 期真实数据：xiao_1='鸡,猴,蛇,龙'，特肖蛇 -> 命中（曾因全局被覆盖而误判为错）
  assert.equal(
    verdictOf(31, row("鸡,猴,蛇,龙", "牛,羊,鼠,狗", "07,27,02,36,49,45,38", "鼠,龙,蛇,羊,马,狗,蛇")),
    "ok", `${file}: 188 期特肖蛇 落在单组`)
  // 187 期真实数据：两组都不含特肖虎 -> 未命中
  assert.equal(
    verdictOf(31, row("猴,鸡,猪,蛇", "马,鼠,羊,龙", "03,28,07,20,39,30,29", "龙,兔,鼠,猪,龙,牛,虎")),
    "miss", `${file}: 187 期特肖虎 不在两组`)
  assert.equal(verdictOf(31, row("猴,鸡,狗,鼠", "虎,羊,龙,牛", "", "")), "pending", `${file}: 未开奖`)
  assert.equal(verdictOf(31, row("", "", "45", "x,x,x,x,x,x,狗")), "unknown", `${file}: 无生肖分组不判定`)

  const live = stripComments(fs.readFileSync(file, "utf8"))
  assert.ok(!/开[^\n]{0,80}?准/.test(live), `${file}: 模板仍写死「准」`)
  assert.ok(live.includes("legacyPredictionVerdict"), `${file}: 模板未使用统一判定`)
  assert.ok(!/window\.__parityVerdict/.test(live), `${file}: 仍在定义跨脚本冲突的 window.__parityVerdict`)
}

console.log("size/parity verdict contract passed")
