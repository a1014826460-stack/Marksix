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

import { assertSameGroups, codeToElement, parseBackendGroups } from "./lib/element-authority.mjs"

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

// 期望值唯一来源 = 后端权威常量（不在本契约里另抄 49 码表）。
const AUTHORITY_GROUPS = parseBackendGroups()
const AUTHORITY_BY_CODE = codeToElement(AUTHORITY_GROUPS)

// 首页壳里写的是数字数组（`金: [3, 4, …]`），归一成两位字符串后与权威值逐项比对
// （键顺序 / 每组顺序 / 49 码全覆盖 / 不重叠由 assertSameGroups 一并锁定）。
const shellGroups = Object.fromEntries(
  Object.entries(groups).map(([element, codes]) => [
    element,
    codes.map((code) => String(code).padStart(2, "0")),
  ]),
)
assertSameGroups(shellGroups, AUTHORITY_GROUPS, `${SHELL}（首页内联脚本）`)

// 用户报障的关键分歧点：这三个号码的生肖五行与号码五行不同。
assert.equal(elementOfCode("24"), "木", "24 的号码五行是木（生肖羊 → 生肖五行 土）")
assert.equal(elementOfCode("37"), "木", "37 的号码五行是木（马 → 生肖五行 火）")
assert.equal(elementOfCode("45"), "木", "45 的号码五行是木（狗 → 生肖五行 土）")
assert.equal(elementOfCode("04"), "金", "04 的号码五行是金（兔 → 生肖五行 木）")
assert.equal(elementOfCode("49"), "土", "49 的号码五行是土")
assert.equal(elementOfCode("5"), "土", "单位数号码必须补零后匹配")
assert.equal(elementOfCode(""), "", "缺失号码不得给出五行（绝不回退生肖五行）")
assert.equal(elementOfCode("50"), "", "非法号码不得给出五行")
// 全 49 码逐一比对后端权威值（首页壳的 elementOfCode 必须与权威分组同源）。
for (let number = 1; number <= 49; number += 1) {
  const code = String(number).padStart(2, "0")
  assert.equal(
    elementOfCode(code),
    AUTHORITY_BY_CODE[code],
    `${SHELL}: elementOfCode("${code}") 必须与后端权威值一致`,
  )
}

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
