/**
 * 台湾彩霸王（twcaibawang）**号码五行**分组 —— 该站五行类玩法（四行中特 mode 482 等）
 * 展示与判定的唯一口径。
 *
 * 权威来源：`backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS`
 * （= `public.fixed_data` 的 `sign='五行'`；后端 `public/api.py::_ELEMENT_MAP` 也由它派生）。
 * 01-49 全覆盖、互不重叠：
 *   金 03,04,11,12,25,26,33,34,41,42
 *   木 07,08,15,16,23,24,37,38,45,46
 *   水 13,14,21,22,29,30,43,44
 *   火 01,02,09,10,17,18,31,32,39,40,47,48
 *   土 05,06,19,20,27,28,35,36,49
 *
 * ⚠️ `fixed_data` 里另有一份 `sign='五行肖'`，那是**生肖五行**（虎兔为木、蛇马为火…），
 * 只用于生肖类玩法。四行中特历史上（正文 `木|04,05,16,17,28,29,40,41` 这种清单）
 * 用的就是生肖五行，于是 17 虎被算成「木」（号码五行应为「火」）、37 马被算成「火」
 * （号码五行应为「木」）。号码五行只能由**特码号码**推导，禁止回退到生肖五行。
 */

/** 五行 → 号码清单（两位字符串，与后端常量逐项一致）。 */
export const ELEMENT_NUMBER_GROUPS: Record<string, readonly string[]> = {
  金: ["03", "04", "11", "12", "25", "26", "33", "34", "41", "42"],
  木: ["07", "08", "15", "16", "23", "24", "37", "38", "45", "46"],
  水: ["13", "14", "21", "22", "29", "30", "43", "44"],
  火: ["01", "02", "09", "10", "17", "18", "31", "32", "39", "40", "47", "48"],
  土: ["05", "06", "19", "20", "27", "28", "35", "36", "49"],
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
