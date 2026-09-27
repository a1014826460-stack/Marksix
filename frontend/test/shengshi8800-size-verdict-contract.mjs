// 大小中特 / 单双中特 系列「判定恒为正确」修复契约。
//
// 修复前的共同缺陷：
//   1) 高亮条件是「特码号码落在该池内」，而互补两池合起来覆盖 01..49，条件恒为真；
//   2) 模板（或共享的 getResult()）把「准」写死，判定环节根本不存在。
// 修复后按真实维度判定，未开奖不显示「准」。
import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

const ROOT = "frontend/public/vendor/shengshi8800/static/js"

// 大小系列：003dxzt.js（57 大小中特）、dx.js（108 大数小数）
const sizeFiles = [`${ROOT}/003dxzt.js`, `${ROOT}/dx.js`]

function loadFunction(file, name) {
  const source = fs.readFileSync(file, "utf8")
  const match = source.match(new RegExp(`window\\.${name} = function[\\s\\S]*?\\n};`))
  if (!match) throw new Error(`${file}: 未找到 window.${name} 定义`)
  const sandbox = { window: {} }
  vm.createContext(sandbox)
  vm.runInContext(match[0], sandbox)
  return sandbox.window[name]
}

for (const file of sizeFiles) {
  const verdict = loadFunction(file, "__sizeVerdict")

  assert.equal(verdict(["大|25,26"], "48"), "ok", `${file}: 大 对 48`)
  assert.equal(verdict(["大|25,26"], "07"), "miss", `${file}: 大 对 07`)
  assert.equal(verdict(["小|01,02"], "07"), "ok", `${file}: 小 对 07`)
  assert.equal(verdict(["小|01,02"], "48"), "miss", `${file}: 小 对 48`)
  assert.equal(verdict(["小|01,02"], "24"), "ok", `${file}: 24 属小`)
  assert.equal(verdict(["大|25,26"], "25"), "ok", `${file}: 25 属大`)
  assert.equal(verdict(["大|25,26"], ""), "pending", `${file}: 未开奖`)
  assert.equal(verdict(["大|25,26"], "？"), "pending", `${file}: 占位结果`)
  assert.equal(verdict(["大|25,26", "小|01,02"], "48"), "unknown", `${file}: 多标签不判定`)
  assert.equal(verdict(["单|01"], "01"), "unknown", `${file}: 非大小内容不判定`)

  const live = stripComments(fs.readFileSync(file, "utf8"))
  assert.ok(!/开\$\{[^}]*\}准/.test(live), `${file}: 模板仍写死「准」`)
  assert.ok(live.includes("sizeVerdict"), `${file}: 模板未使用 sizeVerdict`)
}

// 单双中特（28 买啥开啥）：单值 单/双 预测，按奇偶判定
{
  const file = `${ROOT}/015maishazs.js`
  const verdict = loadFunction(file, "__parityVerdict")

  assert.equal(verdict(["单|01,03"], "07"), "ok", `${file}: 单 对 07`)
  assert.equal(verdict(["单|01,03"], "08"), "miss", `${file}: 单 对 08`)
  assert.equal(verdict(["双|02,04"], "08"), "ok", `${file}: 双 对 08`)
  assert.equal(verdict(["双|02,04"], "07"), "miss", `${file}: 双 对 07`)
  assert.equal(verdict(["双|02,04"], ""), "pending", `${file}: 未开奖`)
  assert.equal(verdict(["双|02,04"], "？"), "pending", `${file}: 占位结果`)
  assert.equal(verdict(["单|01,03", "双|02,04"], "07"), "unknown", `${file}: 双标签不判定`)

  const live = stripComments(fs.readFileSync(file, "utf8"))
  assert.ok(!/开[^\n]{0,80}?准/.test(live), `${file}: 模板仍写死「准」`)
  assert.ok(live.includes("parityVerdict"), `${file}: 模板未使用 parityVerdict`)
}

// 单双四肖（31）：每期两组是变化的 4+4 生肖拆分，按「特肖是否落在两组内」判定
{
  const file = `${ROOT}/031dssx.js`
  const verdict = loadFunction(file, "__parityVerdict")

  // 190 期 特肖狗 落在 xiao_1('猴,鸡,狗,鼠') -> 命中
  assert.equal(verdict(null, "45", "猴,鸡,狗,鼠", "虎,羊,龙,牛", "狗"), "ok", `${file}: 特肖落单组`)
  assert.equal(verdict(null, "45", "虎,羊,龙,牛", "猴,鸡,狗,鼠", "狗"), "ok", `${file}: 特肖落双组`)
  assert.equal(verdict(null, "12", "虎,羊,龙,牛", "猴,鸡,狗,鼠", "兔"), "miss", `${file}: 特肖不在两组内`)
  assert.equal(verdict(null, "", "猴,鸡,狗,鼠", "虎,羊,龙,牛", ""), "pending", `${file}: 未开奖`)
  assert.equal(verdict(null, "45", "", "", "狗"), "unknown", `${file}: 无生肖分组不判定`)

  const live = stripComments(fs.readFileSync(file, "utf8"))
  assert.ok(!/开[^\n]{0,80}?准/.test(live), `${file}: 模板仍写死「准」`)
  assert.ok(live.includes("parityVerdict"), `${file}: 模板未使用 parityVerdict`)
}

function stripComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "")
}

console.log("size/parity verdict contract passed")
