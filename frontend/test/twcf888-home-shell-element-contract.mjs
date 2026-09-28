// 五行口径契约（台湾创富网**首页静态壳** `frontend/public/vendor/twcf888.com/index.html`）
//
// 首页是 react-template：`Twcf888HomeClient.tsx` 用 iframe 加载 `/vendor/twcf888.com/index.html`，
// 因此这份内联脚本就是首页「精准五行」(jzwx, mode 53) 等面板的**真实**判定/高亮实现。
//
// 回归背景：内联脚本旧实现用 `pickMatchedLabel(list, resultCode)`（正文里每个五行标签后的
// **号码清单**）定位命中行，而历史落库正文清单是按**生肖五行**（fixed_data sign='五行肖'）
// 拼的，不是号码五行（= backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS
// = fixed_data sign='五行'）。两者对同一号码给出不同五行：
//   24 → 号码五行 木（生肖羊 → 生肖五行 土）
//   37 → 号码五行 木（马 → 生肖五行 火）
//   04 → 号码五行 金（兔 → 生肖五行 木）
//
// 运行：node frontend/test/twcf888-home-shell-element-contract.mjs
import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

const SHELL = "frontend/public/vendor/twcf888.com/index.html"
const source = fs.readFileSync(SHELL, "utf8")

// ── 1. 抽出内联的号码五行常量与 elementOfCode，真跑一遍 ────────────────
const start = source.indexOf("var ELEMENT_NUMBER_GROUPS = {")
assert.ok(start >= 0, `${SHELL}: 首页壳必须自带号码五行常量`)
const end = source.indexOf("var HEAD_MODES", start)
assert.ok(end > start, `${SHELL}: 号码五行常量块必须完整`)
const sandbox = { JSON, String, Number, Object, Array, Math, parseInt, isNaN }
sandbox.window = sandbox
vm.createContext(sandbox)
vm.runInContext(source.slice(start, end), sandbox, { filename: "twcf888-home-element.js" })

const groups = sandbox.ELEMENT_NUMBER_GROUPS
const elementOfCode = sandbox.elementOfCode
assert.equal(typeof elementOfCode, "function", `${SHELL}: 必须导出 elementOfCode`)

const EXPECTED = {
  金: [3, 4, 11, 12, 25, 26, 33, 34, 41, 42],
  木: [7, 8, 15, 16, 23, 24, 37, 38, 45, 46],
  水: [13, 14, 21, 22, 29, 30, 43, 44],
  火: [1, 2, 9, 10, 17, 18, 31, 32, 39, 40, 47, 48],
  土: [5, 6, 19, 20, 27, 28, 35, 36, 49],
}
assert.deepEqual(Object.keys(groups).sort(), Object.keys(EXPECTED).sort(), "必须是金/木/水/火/土五组")
for (const [element, codes] of Object.entries(EXPECTED)) {
  assert.deepEqual(
    [...groups[element]],
    codes,
    `号码五行分组【${element}】必须与后端 predict.common.ELEMENT_NUMBER_GROUPS 一致`,
  )
}

// 49 码全覆盖、互不重叠。
const seen = new Map()
for (const [element, codes] of Object.entries(groups)) {
  for (const code of codes) {
    assert.ok(!seen.has(code), `${code} 同时属于 ${seen.get(code)} 与 ${element}`)
    seen.set(code, element)
  }
}
assert.deepEqual(
  [...seen.keys()].sort((a, b) => a - b),
  Array.from({ length: 49 }, (_, index) => index + 1),
  "号码五行必须 01-49 全覆盖",
)

// 用户报障的关键分歧点：这三个号码的生肖五行与号码五行不同。
assert.equal(elementOfCode("24"), "木", "24 的号码五行是木（生肖羊 → 生肖五行 土）")
assert.equal(elementOfCode("37"), "木", "37 的号码五行是木（马 → 生肖五行 火）")
assert.equal(elementOfCode("45"), "木", "45 的号码五行是木（狗 → 生肖五行 土）")
assert.equal(elementOfCode("04"), "金", "04 的号码五行是金（兔 → 生肖五行 木）")
assert.equal(elementOfCode("49"), "土", "49 的号码五行是土")
assert.equal(elementOfCode("5"), "土", "单位数号码必须补零后匹配")
assert.equal(elementOfCode(""), "", "缺失号码不得给出五行（绝不回退生肖五行）")
assert.equal(elementOfCode("50"), "", "非法号码不得给出五行")

// ── 2. 命中行必须由特码号码推导，且只对命中语义的五行玩法生效 ────────────
assert.ok(
  /var ELEMENT_HIT_MODES = \[53, 482\];/.test(source),
  `${SHELL}: 命中语义的五行玩法必须是 [53, 482]（98 绝杀一行是排除语义，不在此列）`,
)
assert.ok(
  /matchedLabel = ELEMENT_HIT_MODES\.indexOf\(meta\.modeId\) !== -1 \? elementOfCode\(resultCode\) : pickMatchedLabel\(list, resultCode\);/.test(
    source,
  ),
  `${SHELL}: mode 53/482 的命中行必须走 elementOfCode（不得再用正文号码清单）`,
)
assert.ok(
  !/^\s*matchedLabel = pickMatchedLabel\(list, resultCode\);\s*$/m.test(source),
  `${SHELL}: 不得保留无条件的正文清单命中行定位`,
)
// 98（绝杀一行）仍按原有取反/标签三连口径，不受本次改动影响。
assert.ok(
  source.includes("ELEMENT_MODES = [53, 98, 482]"),
  `${SHELL}: ELEMENT_MODES 必须保持 [53, 98, 482]（98 的展示分支不变）`,
)

console.log("twcf888-home-shell-element-contract: OK（首页壳 mode 53/482 只按特码号码五行）")
