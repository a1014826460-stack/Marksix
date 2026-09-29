/**
 * 号码五行（号码 → 五行）—— **唯一权威前端共享源**。
 *
 * 权威来源（本文件必须与它逐项一致）：
 *   `backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS`
 *   = `canonical_element_number_map()` = `public.fixed_data` 的 `sign='五行'`
 *   （后端 `public/api.py::_ELEMENT_MAP` 同源）。
 *
 * 01-49 全覆盖、互不重叠（2026-09-29 整体改判为「新表」：相对上一版 25 个号码换组，
 * 规律为 `new(x) = old(x-1)`、01 归水）：
 *   金 04,05,12,13,26,27,34,35,42,43
 *   木 08,09,16,17,24,25,38,39,46,47
 *   水 01,14,15,22,23,30,31,44,45
 *   火 02,03,10,11,18,19,32,33,40,41,48,49
 *   土 06,07,20,21,28,29,36,37
 *
 * ⚠️ `fixed_data` 里另有一份 `sign='五行肖'`，那是**生肖五行**（虎兔为木、蛇马为火…），
 * **只覆盖 48 码**，且对同一号码给出与号码五行不同的结果：24 ∈ 土、37 ∈ 火、45 ∈ 土。
 * 五行类玩法（四行中特 mode 482 / 三行中特 mode 53 / 精准五行 mode 53…）的展示与判定
 * **只能**由特码号码按本表推导；**禁止**使用 `sign='五行肖'`，也禁止用历史正文里
 * 「五行标签后的号码清单」（那是生肖五行拼出来的）反推命中行。
 *
 * 分层约定（见 `frontend/test/element-number-groups-contract.mjs`）：
 *   - Next 侧（`app/**`、`lib/**`、`components/**`）**只允许**在本文件写这张表：
 *     其它模块一律 import/再导出（`frontend/lib/twcaibawang-elements.ts`、
 *     `frontend/lib/twcf888-articles.ts` 都是这么接的）。
 *   - 浏览器原生脚本（`frontend/public/vendor/**`，`<script src>` 无法 import ESM）
 *     各自**保持自包含拷贝**，不为共享而引入运行时加载顺序依赖；每个拷贝在常量块上方
 *     注明本权威源，并由上述契约从后端权威值逐项比对，任何一处漂移都会 FAIL。
 */

/** 五行名（仅用于类型标注；分组表声明为 `Record<string, …>` 以免破坏既有索引用法）。 */
export type ElementName = "金" | "木" | "水" | "火" | "土"

/** 五行 → 号码清单（两位字符串，与后端常量逐项一致）。 */
export const ELEMENT_NUMBER_GROUPS: Record<string, readonly string[]> = {
  金: ["04", "05", "12", "13", "26", "27", "34", "35", "42", "43"],
  木: ["08", "09", "16", "17", "24", "25", "38", "39", "46", "47"],
  水: ["01", "14", "15", "22", "23", "30", "31", "44", "45"],
  火: ["02", "03", "10", "11", "18", "19", "32", "33", "40", "41", "48", "49"],
  土: ["06", "07", "20", "21", "28", "29", "36", "37"],
}

/** 号码（两位）→ 五行，由 `ELEMENT_NUMBER_GROUPS` 展开。 */
export const ELEMENT_BY_CODE: Record<string, string> = (() => {
  const map: Record<string, string> = {}
  Object.keys(ELEMENT_NUMBER_GROUPS).forEach((element) => {
    ELEMENT_NUMBER_GROUPS[element].forEach((code) => {
      map[code] = element
    })
  })
  return map
})()

/** 号码 → 五行；号码缺失/非法返回空串（**绝不**回退到生肖五行）。 */
export function elementOfCode(code: string) {
  const digits = String(code ?? "").replace(/[^0-9]/g, "")
  if (!digits) return ""
  const normalized = digits.padStart(2, "0")
  return ELEMENT_BY_CODE[normalized] || ""
}

/** 正文标签归一化：去掉引号/括号/空白与后缀「行」（`土行` → `土`）。 */
export function normalizeElementLabel(label: string) {
  return String(label ?? "")
    .replace(/[[\]"'　\s]/g, "")
    .replace(/行$/, "")
    .trim()
}

/**
 * 号码五行是否落在预测的若干行里。
 *
 * @param labels 本期预测的五行标签（取自本行正文，如 `["水","木","金","土"]`）。
 * @param code 特码号码（`res_code` 最后一项）。
 * @returns 命中为 `true`、未命中为 `false`；号码或预测标签缺失（不可判定）返回 `null`。
 */
export function elementHitJudgement(labels: string[], code: string) {
  const element = elementOfCode(code)
  const normalized = (labels || []).map(normalizeElementLabel).filter(Boolean)
  if (!element || !normalized.length) return null
  return normalized.includes(element)
}
