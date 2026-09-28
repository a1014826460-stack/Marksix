/**
 * 号码五行的**唯一取数层**（测试专用工具，不是契约本身）。
 *
 * 背景：号码五行表在仓库里有 1 份后端权威源 + 1 份前端权威源 + 若干**必须自包含**的
 * 浏览器原生（vendor）拷贝。任何契约都不应该再手写「期望的 49 码表」——那等于又抄一份，
 * 抄错了契约还会跟着一起错。本模块统一从**后端权威源**取期望值，并提供从各类源码里
 * 抽取常量块的能力：
 *
 *   - `parseBackendGroups()`  ← `backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS`
 *   - `parseLibGroups()`      ← `frontend/lib/element-number-groups.ts`（前端唯一权威源）
 *   - `parseGroupsFrom(text)` ← 任意 vendor 拷贝（内联 HTML / 原生 JS / 打包镜像）
 *
 * 抽取规则（对后端 Python 与前端 JS/TS 都适用，不各自手写期望值）：
 *   找到 `ELEMENT_NUMBER_GROUPS` 后面紧跟的字面量 `{ … }`（花括号配平），
 *   再把每个 `金|木|水|火|土` 键后面的 `[...]` / `(...)` 列表解析成**两位字符串**数组
 *   （vendor 里的 `[3, 4, …]` 与后端/lib 的 `["03", "04", …]` 归一后可直接逐项比较）。
 *
 * ⚠️ 只读：本模块不写任何文件；后端路径可用环境变量
 *    `ELEMENT_AUTHORITY_COMMON_PY` 覆盖（供「反向验证」在不改 `backend/**` 的前提下
 *    指向一份带 mutation 的临时副本，见 `frontend/test/element-number-groups-contract.mjs`）。
 */
import assert from "node:assert/strict"
import fs from "node:fs"

/** 后端权威源（可用环境变量指向临时副本以模拟 mutation）。 */
export const BACKEND_COMMON_PY =
  process.env.ELEMENT_AUTHORITY_COMMON_PY || "backend/src/predict/common.py"
/** 前端唯一权威源。 */
export const ELEMENT_GROUPS_TS = "frontend/lib/element-number-groups.ts"
/** 五行名与后端 dict 的书写顺序一致。 */
export const ELEMENT_NAMES = ["金", "木", "水", "火", "土"]

/**
 * `ELEMENT_NUMBER_GROUPS` 的声明头：
 *   Python  `ELEMENT_NUMBER_GROUPS: dict[str, tuple[str, ...]] = {`
 *   TS      `export const ELEMENT_NUMBER_GROUPS: Record<string, readonly string[]> = {`
 *   vendor  `var ELEMENT_NUMBER_GROUPS = {`
 * 注释里提到名字（后面跟的不是类型注解）不会命中，因为中间字符被限制在类型注解字符集内。
 */
const DECLARATION = /\bELEMENT_NUMBER_GROUPS\b[\w:,[\]<>()| '"=.]{0,100}\{/

/** 单个分组条目：`金: [3, 4, …]` / `"金": ("03", "04", …)` / `'金': ['03', …]`。 */
const GROUP_ENTRY = /["']?([金木水火土])["']?\s*:\s*[\[(]([^\])]*)[\])]/g

/** 归一化号码：去掉引号/空白/前导零差异，统一成两位字符串。 */
export function normalizeCode(value) {
  const digits = String(value).replace(/[^0-9]/g, "")
  assert.ok(digits.length > 0, `非法号码字面量：${JSON.stringify(value)}`)
  return digits.padStart(2, "0")
}

/**
 * 从任意源码文本里抽出 `ELEMENT_NUMBER_GROUPS` 字面量。
 * @returns {{ open: number, close: number, text: string, groups: object|null }}
 */
export function extractGroupsDeclaration(source, label = "<source>") {
  const match = DECLARATION.exec(source)
  if (!match) return { found: false, open: -1, close: -1, text: "", groups: null }

  const open = match.index + match[0].length - 1
  let depth = 0
  let close = -1
  for (let index = open; index < source.length; index += 1) {
    const ch = source[index]
    if (ch === "{") depth += 1
    else if (ch === "}") {
      depth -= 1
      if (depth === 0) {
        close = index
        break
      }
    }
  }
  assert.ok(close > open, `${label}: ELEMENT_NUMBER_GROUPS 的花括号不配平`)

  const body = source.slice(open + 1, close)
  const groups = {}
  GROUP_ENTRY.lastIndex = 0
  let entry
  while ((entry = GROUP_ENTRY.exec(body)) !== null) {
    const codes = entry[2]
      .split(",")
      .map((token) => token.trim())
      .filter(Boolean)
      .map(normalizeCode)
    assert.ok(!(entry[1] in groups), `${label}: 五行分组【${entry[1]}】重复声明`)
    groups[entry[1]] = codes
  }
  return { found: true, open, close, text: source.slice(open, close + 1), groups }
}

/** 该文本里是否出现 `ELEMENT_NUMBER_GROUPS` 的**声明**（注释里只提名字不算）。 */
export function hasElementGroupsDeclaration(source) {
  return DECLARATION.test(source)
}

/** 从源码文本里抽分组；数量不是五组时按调用方要求处理。 */
export function parseGroupsFrom(source, label) {
  const { groups } = extractGroupsDeclaration(source, label)
  assert.ok(groups, `${label}: 必须自带号码五行常量 ELEMENT_NUMBER_GROUPS`)
  return groups
}

export function readSource(file) {
  assert.ok(fs.existsSync(file), `缺少文件：${file}`)
  return fs.readFileSync(file, "utf8")
}

/** 后端权威分组（唯一期望值来源）。 */
export function parseBackendGroups(source = readSource(BACKEND_COMMON_PY)) {
  return parseGroupsFrom(source, BACKEND_COMMON_PY)
}

/** 前端唯一权威源的分组。 */
export function parseLibGroups(source = readSource(ELEMENT_GROUPS_TS)) {
  return parseGroupsFrom(source, ELEMENT_GROUPS_TS)
}

/** 从 vendor 源码里抽分组（内联 HTML / 原生 JS / 打包镜像同一条路径）。 */
export function parseVendorGroups(file) {
  return parseGroupsFrom(readSource(file), file)
}

/**
 * twsaimahui 的打包镜像**文件名是内容哈希**（`scripts/bundle-twsaimahui-modules.py`
 * 取 `sha256(源文件名 + 源内容)[:16]`），任何源文件改动都会改名。所以镜像路径不能硬编码，
 * 只能从 `bundles.json` 清单里按**源文件**反查（返回所有包含该源的 bundle 路径）。
 */
export const TWSAIMAHUI_ROOT = "frontend/public/vendor/twsaimahui"
export const TWSAIMAHUI_MANIFEST = `${TWSAIMAHUI_ROOT}/static/js/bundles.json`

export function twsaimahuiBundlesFor(source) {
  const manifest = JSON.parse(readSource(TWSAIMAHUI_MANIFEST))
  assert.ok(Array.isArray(manifest.runs), `${TWSAIMAHUI_MANIFEST}: runs 缺失`)
  return manifest.runs
    .filter((run) => Array.isArray(run.sources) && run.sources.includes(source))
    .map((run) => `${TWSAIMAHUI_ROOT}/${run.bundle}`)
}

/** `{金:[…]} → {03:'金', …}`（号码 → 五行）。 */
export function codeToElement(groups) {
  const map = {}
  for (const element of Object.keys(groups)) {
    for (const code of groups[element]) {
      assert.ok(!(code in map), `${code} 同时属于 ${map[code]} 与 ${element}`)
      map[code] = element
    }
  }
  return map
}

/** 49 码全覆盖（返回按号码排序的清单，便于断言）。 */
export function coveredCodes(groups) {
  return Object.values(groups).flat().sort()
}

/**
 * 与权威值逐项比对（键顺序 + 每组的号码顺序都要一致）。
 * @param {object} actual   待检查的分组
 * @param {object} expected 权威分组（一般是 `parseBackendGroups()`）
 */
export function assertSameGroups(actual, expected, label) {
  assert.deepEqual(
    Object.keys(actual),
    Object.keys(expected),
    `${label}: 五行分组必须是 ${ELEMENT_NAMES.join("/")} 五组（顺序与后端一致）`,
  )
  for (const element of Object.keys(expected)) {
    assert.deepEqual(
      [...actual[element]],
      [...expected[element]],
      `${label}: 号码五行分组【${element}】必须与后端 predict.common.ELEMENT_NUMBER_GROUPS 一致`,
    )
  }
  assert.deepEqual(
    coveredCodes(actual),
    Array.from({ length: 49 }, (_, index) => String(index + 1).padStart(2, "0")),
    `${label}: 号码五行必须 01-49 全覆盖、互不重叠`,
  )
}

/**
 * 去掉 ESM 语法，让 TS 源码可以在 `vm` 里逐句执行（契约里「真跑」用）。
 * 只处理本仓库这两种写法：`import …` 行、`export … from "…"` 行、`export type …` 行、`export ` 前缀。
 */
export function stripModuleSyntax(text) {
  return text
    .replace(/^\s*import\s[^\n]*\n/gm, "")
    .replace(/^\s*export\s*\{[^}]*\}\s*from\s*["'][^"']+["'][^\n]*\n/gm, "")
    .replace(/^\s*export\s+type\s[^\n]*\n/gm, "")
    .replace(/^export\s+/gm, "")
}

/** 去掉本仓库 TS 里用到的少量类型注解（与 `twcaibawang-verdict-contract.mjs` 同一套规则）。 */
export function stripTypeAnnotations(text) {
  return text
    .replace(
      /(function\s+[A-Za-z_$][\w$]*\s*\()([^)]*)(\))/g,
      (_match, head, params, tail) =>
        head + params.replace(/:\s*[^,)]+/g, "").replace(/\?\s*(?=[,)]|$)/g, "") + tail,
    )
    .replace(/\)\s*:\s*[A-Za-z_$][\w$<>[\]|, .]*(?=\s*\{)/g, ")")
    .replace(/\b(const|let|var)\s+([A-Za-z_$][\w$]*)\s*:\s*[^=\n]+=/g, "$1 $2 =")
    .replace(/\s+as\s+[A-Za-z_$][\w$<>[\]|" ]*/g, "")
}

/** ESM/TS → 可在 `vm` 里执行的脚本。 */
export function executableSource(text) {
  return stripTypeAnnotations(stripModuleSyntax(text))
}
