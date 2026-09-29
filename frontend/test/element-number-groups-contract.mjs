// 号码五行「单一权威源 + 全拷贝不漂移」契约
//
// 背景：号码五行表在仓库里有 **1 份后端权威源**（`backend/src/predict/common.py::
// ELEMENT_NUMBER_GROUPS` = `public.fixed_data` sign='五行'）、**1 份前端权威源**
// （`frontend/lib/element-number-groups.ts`）以及若干**必须自包含**的浏览器原生
// （vendor）拷贝（`<script src>` 无法 import ESM）。拷贝一旦漂移，同一个特码会在不同
// 站点被判成不同五行 —— 这正是「24 从木漂到土 / 37 从木漂到火」这类报障的根因
// （那是把**生肖五行**当号码五行用造成的口径漂移；2026-09-29 号码五行表本身也已整体
// 改判为「新表」，见文末说明）。
//
// 本契约**不手写任何期望值**：期望值一律从后端权威源解析出来，再去比对
//   1. `frontend/lib/element-number-groups.ts`（前端唯一权威源）；
//   2. 四个厂站源码拷贝：twcf888 首页内联脚本 / tw8880 统一判定模块 / twsaimahui 三行中特 /
//      twssz 站点数据适配器；
//   3. twsaimahui 的**打包镜像**（文件名是内容哈希，只能按 `bundles.json` 反查）；
//   4. 机器扫描 `frontend/public/vendor/**`，任何**未登记**的新拷贝都必须与权威值一致。
//
// 反向验证（本契约必须能抓到漂移）：
//   - vendor 漂移：把任意一份 vendor 拷贝里的 24 从「木」挪到「土」→ 本契约 FAIL；
//   - 后端漂移：`ELEMENT_AUTHORITY_COMMON_PY=<临时副本> node frontend/test/element-number-groups-contract.mjs`，
//     副本里把 37 从「土」挪到「火」→ 本契约 FAIL（不必改 `backend/**`）。
//
// 说明：2026-09-29 号码五行整体改判为「新表」（相对上一版 25 个号码换组，规律
// `new(x) = old(x-1)`、01 归水）。本文件的期望值仍**不手写**：全部从后端权威源解析；
// 只有「与生肖五行分歧」的说明性 KEY_POINTS 需要跟着新表重算。
//
// 运行：node frontend/test/element-number-groups-contract.mjs
import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

import {
  BACKEND_COMMON_PY,
  ELEMENT_GROUPS_TS,
  assertSameGroups,
  codeToElement,
  executableSource,
  extractGroupsDeclaration,
  hasElementGroupsDeclaration,
  parseBackendGroups,
  parseLibGroups,
  parseVendorGroups,
  readSource,
  twsaimahuiBundlesFor,
} from "./lib/element-authority.mjs"

/**
 * 号码五行与生肖五行会给出不同结果的关键号码（用户报障的分歧点）。
 *
 * 生肖五行（`fixed_data` sign='五行肖'）：虎兔木、蛇马火、猴鸡金、猪鼠水、牛羊龙狗土；
 * 本仓库样本期（2026 丙午马年）的号码→生肖为 `01 起「马」逆序`（01/13/25/37/49 = 马）。
 * 第三项是说明性备注，供人核对；对错由上面的后端权威值兜底。
 * 2026-09-29 换新表后按新表重算（旧值见 git 历史）：以下 12 组已全部按新表核对。
 */
const KEY_POINTS = [
  ["24", "木", "生肖羊 → 生肖五行 土"],
  ["37", "土", "生肖马 → 生肖五行 火（旧表为木，已改判）"],
  ["45", "水", "生肖狗 → 生肖五行 土（旧表为木，已改判）"],
  ["04", "金", "生肖兔 → 生肖五行 木"],
  ["13", "金", "生肖马 → 生肖五行 火（旧表为水，已改判）"],
  ["01", "水", "生肖马 → 生肖五行 火（旧表为火，已改判）"],
  ["05", "金", "生肖虎 → 生肖五行 木（旧表为土，已改判）"],
  ["03", "火", "生肖龙 → 生肖五行 土（旧表为金，已改判）"],
  ["07", "土", "生肖鼠 → 生肖五行 水（旧表为木，已改判）"],
  ["17", "木", "生肖虎 → 生肖五行 木（旧表为火，换表后与生肖五行一致）"],
  ["49", "火", "（旧表为土，已改判）"],
  ["02", "火", ""],
  ["06", "土", ""],
]

// ── 1. 后端权威值（唯一期望值来源）────────────────────────────────────
const AUTHORITY = parseBackendGroups()
assert.deepEqual(
  Object.keys(AUTHORITY),
  ["金", "木", "水", "火", "土"],
  `${BACKEND_COMMON_PY}: 后端权威分组必须是 金/木/水/火/土 五组`,
)
assert.deepEqual(
  Object.values(AUTHORITY).flat().sort(),
  Array.from({ length: 49 }, (_, index) => String(index + 1).padStart(2, "0")),
  `${BACKEND_COMMON_PY}: 后端权威分组必须 01-49 全覆盖、互不重叠`,
)
console.log(
  `[authority] ${BACKEND_COMMON_PY}::ELEMENT_NUMBER_GROUPS（49 码）= ` +
    Object.entries(AUTHORITY)
      .map(([element, codes]) => `${element}:${codes.length}`)
      .join(" "),
)

// ── 2. 前端唯一权威源必须与后端逐项一致 ──────────────────────────────
const LIB_SOURCE = readSource(ELEMENT_GROUPS_TS)
const LIB_GROUPS = parseLibGroups(LIB_SOURCE)
assertSameGroups(LIB_GROUPS, AUTHORITY, ELEMENT_GROUPS_TS)

// Next 侧**只允许**权威源自己写这张表：其它 lib/components 文件只能是 import/再导出。
const NEXT_SIDE_ROOTS = ["frontend/lib", "frontend/components"]
const nextSideCopies = listFiles(NEXT_SIDE_ROOTS).filter((file) => {
  if (file === ELEMENT_GROUPS_TS) return false
  const source = readSource(file)
  if (!hasElementGroupsDeclaration(source)) return false
  const { groups } = extractGroupsDeclaration(source, file)
  return Boolean(groups) && Object.keys(groups).length === 5
})
assert.deepEqual(
  nextSideCopies,
  [],
  `Next 侧出现第 6 份号码五行拷贝：${nextSideCopies.join(", ")}；` +
    `请改为 import/再导出 ${ELEMENT_GROUPS_TS}`,
)

// 两个已知消费方：只能是「再导出 / import」，不得自带常量表。
const TWCAIBAWANG_ELEMENTS_TS = "frontend/lib/twcaibawang-elements.ts"
const TWCF888_ARTICLES_TS = "frontend/lib/twcf888-articles.ts"
const twcaibawangShim = readSource(TWCAIBAWANG_ELEMENTS_TS)
assert.ok(
  !hasElementGroupsDeclaration(twcaibawangShim),
  `${TWCAIBAWANG_ELEMENTS_TS}: 不得自带号码五行常量表（应再导出 ${ELEMENT_GROUPS_TS}）`,
)
assert.ok(
  /from\s+["'](?:@\/lib\/element-number-groups|\.\/element-number-groups)["']/.test(twcaibawangShim),
  `${TWCAIBAWANG_ELEMENTS_TS}: 必须从 ${ELEMENT_GROUPS_TS} 再导出号码五行`,
)
for (const name of [
  "ELEMENT_NUMBER_GROUPS",
  "ELEMENT_BY_CODE",
  "elementOfCode",
  "normalizeElementLabel",
  "elementHitJudgement",
]) {
  assert.ok(
    new RegExp(`\\b${name}\\b`).test(twcaibawangShim),
    `${TWCAIBAWANG_ELEMENTS_TS}: 既有导出签名 ${name} 不得丢失`,
  )
}
const twcf888Articles = readSource(TWCF888_ARTICLES_TS)
assert.ok(
  !hasElementGroupsDeclaration(twcf888Articles),
  `${TWCF888_ARTICLES_TS}: 不得自带号码五行常量表（应 import ${ELEMENT_GROUPS_TS}）`,
)
assert.ok(
  /from\s+["'](?:@\/lib\/element-number-groups|\.\/element-number-groups)["']/.test(twcf888Articles),
  `${TWCF888_ARTICLES_TS}: 必须从 ${ELEMENT_GROUPS_TS} 取号码五行`,
)
assert.ok(
  /import\s*\{[^}]*\belementOfCode\b[^}]*\}/.test(twcf888Articles),
  `${TWCF888_ARTICLES_TS}: 必须 import elementOfCode`,
)

// ── 3. 真跑前端权威源的实现（补零 / 非法号码 / 判定语义）──────────────
const sandbox = { JSON, String, Number, Object, Array, Math, parseInt, RegExp, console }
sandbox.window = sandbox
sandbox.globalThis = sandbox
vm.createContext(sandbox)
vm.runInContext(
  `${executableSource(LIB_SOURCE)}
globalThis.__elementApi = {
  ELEMENT_NUMBER_GROUPS: ELEMENT_NUMBER_GROUPS,
  ELEMENT_BY_CODE: ELEMENT_BY_CODE,
  elementOfCode: elementOfCode,
  normalizeElementLabel: normalizeElementLabel,
  elementHitJudgement: elementHitJudgement,
};`,
  sandbox,
  { filename: ELEMENT_GROUPS_TS },
)
const { elementOfCode, normalizeElementLabel, elementHitJudgement } = sandbox.__elementApi
assert.equal(typeof elementOfCode, "function", `${ELEMENT_GROUPS_TS}: 必须导出 elementOfCode`)
// vm 里的对象来自另一个 realm，先 JSON 往返成本地普通对象再比对。
assertSameGroups(
  JSON.parse(JSON.stringify(sandbox.__elementApi.ELEMENT_NUMBER_GROUPS)),
  AUTHORITY,
  `${ELEMENT_GROUPS_TS}（vm 里真跑）`,
)

for (const [code, element, note] of KEY_POINTS) {
  assert.equal(
    elementOfCode(code),
    element,
    `${ELEMENT_GROUPS_TS}: elementOfCode("${code}") 必须是「${element}」${note ? `（${note}）` : ""}`,
  )
}
assert.equal(elementOfCode("5"), "金", `${ELEMENT_GROUPS_TS}: 单位数号码必须补零后匹配（05 → 金）`)
assert.equal(elementOfCode("49"), "火", `${ELEMENT_GROUPS_TS}: 49 必须补零后匹配（49 → 火）`)
assert.equal(elementOfCode(""), "", `${ELEMENT_GROUPS_TS}: 缺失号码不得给出五行（绝不回退生肖五行）`)
assert.equal(elementOfCode("50"), "", `${ELEMENT_GROUPS_TS}: 非法号码不得给出五行`)
assert.equal(normalizeElementLabel(" 土行 "), "土", `${ELEMENT_GROUPS_TS}: 正文标签需归一化（去空白与「行」后缀）`)
assert.equal(elementHitJudgement(["水", "木", "金", "土"], "37"), true, "37（土）落在预测四行内 → 命中")
assert.equal(elementHitJudgement(["水", "木", "金", "火"], "37"), false, "37（土）不在预测四行内 → 未命中")
assert.equal(elementHitJudgement([], "37"), null, "没有预测标签时不可判定")
assert.equal(elementHitJudgement(["木"], ""), null, "没有特码时不可判定")

// ── 4. 已知 vendor 拷贝（自包含，但必须与权威值一致）──────────────────
const TWCF888_SHELL = "frontend/public/vendor/twcf888.com/index.html"
const SHENGSHI_VERDICT = "frontend/public/vendor/shengshi8800/static/js/legacy-prediction-verdict.js"
const TWSAIMAHUI_SANHANG = "frontend/public/vendor/twsaimahui/static/js/025sanhang.js"
const TWSAIMAHUI_SANHANG_SOURCE = "static/js/025sanhang.js"
const TWSSZ_ADAPTER = "frontend/public/vendor/twssz/site-data-adapter.js"

/** twsaimahui 打包镜像：文件名是内容哈希，按 `bundles.json` 反查（不得硬编码）。 */
const SANHANG_MIRRORS = twsaimahuiBundlesFor(TWSAIMAHUI_SANHANG_SOURCE)
assert.ok(
  SANHANG_MIRRORS.length > 0,
  `bundles.json 里找不到包含 ${TWSAIMAHUI_SANHANG_SOURCE} 的 bundle（打包镜像必须存在）`,
)

const KNOWN_VENDOR_COPIES = [
  { file: TWCF888_SHELL, how: "twcf888 首页内联脚本（iframe 壳）" },
  { file: SHENGSHI_VERDICT, how: "tw8880 统一判定模块（<script src>）" },
  { file: TWSAIMAHUI_SANHANG, how: "twsaimahui 三行中特源脚本（<script>）" },
  { file: TWSSZ_ADAPTER, how: "twssz 站点数据适配器（<script src>，mode 53「综合资料」命中行）" },
  ...SANHANG_MIRRORS.map((file) => ({
    file,
    how: `twsaimahui 打包镜像（按 bundles.json 反查 ${TWSAIMAHUI_SANHANG_SOURCE}）`,
  })),
]

/** 每份拷贝：常量块与权威值逐项一致 + 关键号码归属一致 + 带权威源注释。 */
function checkCopy(file, how) {
  const groups = parseVendorGroups(file)
  assertSameGroups(groups, AUTHORITY, `${file}（${how}）`)
  const byCode = codeToElement(groups)
  for (const [code, element, note] of KEY_POINTS) {
    assert.equal(
      byCode[code],
      element,
      `${file}: 拷贝里 ${code} 的号码五行必须是「${element}」${note ? `（${note}）` : ""}`,
    )
  }
  assert.ok(
    /backend\/src\/predict\/common\.py::ELEMENT_NUMBER_GROUPS/.test(readSource(file)),
    `${file}: 常量块上方必须注明权威源 backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS`,
  )
  return Object.keys(groups).length
}

for (const { file, how } of KNOWN_VENDOR_COPIES) {
  const groupCount = checkCopy(file, how)
  console.log(`[vendor] ${file}（${how}）: ${groupCount} 组一致`)
}

// ── 5. 机器扫描：vendor 下任何「未登记」的拷贝都必须与权威值一致 ────────
const VENDOR_ROOT = "frontend/public/vendor"
const knownFiles = new Set(KNOWN_VENDOR_COPIES.map((item) => item.file))
const scanned = []
const unregistered = []
const ignored = []
let skippedBySize = 0
for (const file of listFiles([VENDOR_ROOT])) {
  const { size } = fs.statSync(file)
  if (size > 8 * 1024 * 1024) {
    skippedBySize += 1
    continue
  }
  const source = readSource(file)
  if (!hasElementGroupsDeclaration(source)) continue
  const { groups } = extractGroupsDeclaration(source, file)
  if (!groups || Object.keys(groups).length !== 5) {
    // 只提到名字（注释 / 文档）而没有五组常量 → 不是拷贝。
    ignored.push(file)
    continue
  }
  scanned.push(file)
  assertSameGroups(groups, AUTHORITY, `${file}（vendor 扫描发现）`)
  if (!knownFiles.has(file)) unregistered.push(file)
}
assert.deepEqual(
  unregistered,
  [],
  `发现未登记的号码五行拷贝：${unregistered.join(", ")}；` +
    `浏览器原生脚本可以自包含，但必须与权威值一致并登记到本契约的 KNOWN_VENDOR_COPIES`,
)
for (const file of KNOWN_VENDOR_COPIES) {
  assert.ok(scanned.includes(file.file), `${file.file}: 必须能在 vendor 扫描里被识别为号码五行拷贝`)
}
console.log(
  `[scan] ${VENDOR_ROOT}: 发现 ${scanned.length} 份拷贝（全部与权威值一致）、` +
    `${ignored.length} 个仅提及名字的文件被忽略、${skippedBySize} 个超大文件跳过`,
)

console.log(
  `element-number-groups-contract: OK（权威 ${BACKEND_COMMON_PY} → ${ELEMENT_GROUPS_TS} → ` +
    `${KNOWN_VENDOR_COPIES.length} 份 vendor 拷贝，49 码零漂移）`,
)

/** 递归列出指定根目录下的文本源码文件（只收可能承载常量的后缀）。 */
function listFiles(roots) {
  const out = []
  const pattern = /\.(?:js|mjs|cjs|ts|tsx|jsx|html|htm)$/i
  const walk = (dir) => {
    if (!fs.existsSync(dir)) return
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = `${dir}/${entry.name}`
      if (entry.isDirectory()) walk(full)
      else if (pattern.test(entry.name)) out.push(full)
    }
  }
  for (const root of roots) walk(root)
  return out
}
