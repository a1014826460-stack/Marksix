import "server-only"

import { promises as fs } from "fs"
import path from "path"

import { getPublicSitePageData } from "@/lib/backend-api"
import { getSiteConfig } from "@/lib/sites"
import type { PublicHistoryRow } from "@/lib/site-page"

export type Twcf888ArticleGroup = "amgst" | "jsb" | "jhq" | "gs"
export type Twcf888ModuleStatus =
  | "live_backed"
  | "snapshot_only"
  | "blocked_requires_backend_work"

type SourceKind = "live-module" | "vendor-snapshot" | "missing-live-data"

export type Twcf888ArticleRow = {
  issue: string
  predictionHtml: string
  resultHtml: string
  isOpened: boolean
  isCorrect: boolean | null
  lineHtml: string
}

export type Twcf888ArticleDefinition = {
  id: string
  title: string
  group: Twcf888ArticleGroup
  moduleStatus: Twcf888ModuleStatus
  modeId: number | null
  snapshotPath: string
  /**
   * 判定取反的栏目。
   *
   * `绝杀一波`（2290）与 `一波中特`（3049）共用 mode 143 的同一份候选与同一个
   * `is_correct`，但玩法相反：mode 143 的 `is_correct=true` 表示「特码波色落在候选里」，
   * 而「绝杀一波」的准 = 特码波色**没有**落在被杀波色里（供应商静态样例
   * `index/index/jsb/id/2290.html`：杀蓝波 + 开 24 红 → 对；杀蓝波 + 开 25 蓝 → 错）。
   * 不做取反就会出现「杀掉的波色开出来了却显示对」。
   */
  verdictInverted?: boolean
}

export type Twcf888ArticleDetail = {
  id: string
  title: string
  author: string
  group: Twcf888ArticleGroup
  sourceKind: SourceKind
  modeId: number | null
  moduleStatus: Twcf888ModuleStatus
  status: "ok" | "fallback_snapshot" | "missing_live_data"
  missingMapping: boolean
  notes: string[]
  contentHtml: string
  rows: Twcf888ArticleRow[]
  requestedLotteryType: number
}

const SITE = getSiteConfig("twcf888")
const AUTHOR = "台湾创富网"
const DEFAULT_HISTORY_LIMIT = 10

const ARTICLE_DEFINITIONS: readonly Twcf888ArticleDefinition[] = [
  { id: "6097", title: "逢买必中", group: "amgst", moduleStatus: "live_backed", modeId: 198, snapshotPath: "amgst/6097.html" },
  { id: "6098", title: "四头必中", group: "amgst", moduleStatus: "live_backed", modeId: 483, snapshotPath: "amgst/6098.html" },
  { id: "6099", title: "家禽野兽", group: "amgst", moduleStatus: "live_backed", modeId: 14, snapshotPath: "amgst/6099.html" },
  { id: "6100", title: "天地生肖", group: "amgst", moduleStatus: "live_backed", modeId: 5, snapshotPath: "amgst/6100.html" },
  { id: "6101", title: "稳料四肖中", group: "amgst", moduleStatus: "live_backed", modeId: 47, snapshotPath: "amgst/6101.html" },
  { id: "6102", title: "合数大小", group: "amgst", moduleStatus: "live_backed", modeId: 279, snapshotPath: "amgst/6102.html" },
  { id: "6103", title: "5尾中特", group: "amgst", moduleStatus: "live_backed", modeId: 66, snapshotPath: "amgst/6103.html" },
  { id: "6104", title: "精准五行", group: "amgst", moduleStatus: "live_backed", modeId: 53, snapshotPath: "amgst/6104.html" },
  { id: "6105", title: "双波中特", group: "amgst", moduleStatus: "live_backed", modeId: 38, snapshotPath: "amgst/6105.html" },
  { id: "6106", title: "合数单双", group: "amgst", moduleStatus: "live_backed", modeId: 132, snapshotPath: "amgst/6106.html" },
  { id: "6107", title: "琴棋书画", group: "amgst", moduleStatus: "live_backed", modeId: 26, snapshotPath: "amgst/6107.html" },
  { id: "6108", title: "平特三肖连", group: "amgst", moduleStatus: "live_backed", modeId: 470, snapshotPath: "amgst/6108.html" },
  { id: "6109", title: "6尾中特", group: "amgst", moduleStatus: "live_backed", modeId: 2, snapshotPath: "amgst/6109.html" },
  { id: "6110", title: "三头中特", group: "amgst", moduleStatus: "live_backed", modeId: 12, snapshotPath: "amgst/6110.html" },
  { id: "6111", title: "三行中特", group: "amgst", moduleStatus: "live_backed", modeId: 53, snapshotPath: "amgst/6111.html" },
  { id: "6112", title: "一句中特", group: "amgst", moduleStatus: "live_backed", modeId: 50, snapshotPath: "amgst/6112.html" },

  { id: "2287", title: "绝杀一行", group: "jsb", moduleStatus: "live_backed", modeId: 98, snapshotPath: "index/index/jsb/id/2287.html" },
  { id: "2288", title: "绝杀二肖", group: "jsb", moduleStatus: "live_backed", modeId: 473, snapshotPath: "index/index/jsb/id/2288.html" },
  { id: "2289", title: "绝杀二尾", group: "jsb", moduleStatus: "live_backed", modeId: 95, snapshotPath: "index/index/jsb/id/2289.html" },
  { id: "2290", title: "绝杀一波", group: "jsb", moduleStatus: "live_backed", modeId: 143, snapshotPath: "index/index/jsb/id/2290.html", verdictInverted: true },
  { id: "2291", title: "绝杀一头", group: "jsb", moduleStatus: "live_backed", modeId: 41, snapshotPath: "index/index/jsb/id/2291.html" },
  { id: "2292", title: "绝杀一肖", group: "jsb", moduleStatus: "live_backed", modeId: 472, snapshotPath: "index/index/jsb/id/2292.html" },

  { id: "7621", title: "千秋霸业", group: "jhq", moduleStatus: "live_backed", modeId: 14, snapshotPath: "index/index/jhq/id/7621.html" },
  { id: "7622", title: "高级六肖", group: "jhq", moduleStatus: "live_backed", modeId: 27, snapshotPath: "index/index/jhq/id/7622.html" },
  { id: "7623", title: "4行4头", group: "jhq", moduleStatus: "live_backed", modeId: 482, snapshotPath: "index/index/jhq/id/7623.html" },
  { id: "7624", title: "绝禁一肖", group: "jhq", moduleStatus: "live_backed", modeId: 472, snapshotPath: "index/index/jhq/id/7624.html" },
  { id: "7625", title: "绝杀三肖", group: "jhq", moduleStatus: "live_backed", modeId: 42, snapshotPath: "index/index/jhq/id/7625.html" },
  { id: "7626", title: "平特一尾", group: "jhq", moduleStatus: "live_backed", modeId: 54, snapshotPath: "index/index/jhq/id/7626.html" },
  { id: "7627", title: "绝杀一尾", group: "jhq", moduleStatus: "live_backed", modeId: 20, snapshotPath: "index/index/jhq/id/7627.html" },
  { id: "7628", title: "原创双波", group: "jhq", moduleStatus: "live_backed", modeId: 38, snapshotPath: "index/index/jhq/id/7628.html" },
  { id: "7629", title: "准杀7码", group: "jhq", moduleStatus: "live_backed", modeId: 88, snapshotPath: "index/index/jhq/id/7629.html" },
  { id: "7630", title: "平特一肖", group: "jhq", moduleStatus: "live_backed", modeId: 103, snapshotPath: "index/index/jhq/id/7630.html" },
  { id: "7631", title: "特码大小", group: "jhq", moduleStatus: "live_backed", modeId: 57, snapshotPath: "index/index/jhq/id/7631.html" },
  { id: "7632", title: "特码九肖", group: "jhq", moduleStatus: "live_backed", modeId: 49, snapshotPath: "index/index/jhq/id/7632.html" },
  { id: "7633", title: "平特两肖", group: "jhq", moduleStatus: "live_backed", modeId: 43, snapshotPath: "index/index/jhq/id/7633.html" },
  { id: "7634", title: "绝版杀肖", group: "jhq", moduleStatus: "live_backed", modeId: 473, snapshotPath: "index/index/jhq/id/7634.html" },
  { id: "7635", title: "3头中特", group: "jhq", moduleStatus: "live_backed", modeId: 12, snapshotPath: "index/index/jhq/id/7635.html" },
  { id: "7636", title: "八肖来财", group: "jhq", moduleStatus: "live_backed", modeId: 180, snapshotPath: "index/index/jhq/id/7636.html" },
  { id: "7637", title: "特码单双", group: "jhq", moduleStatus: "live_backed", modeId: null, snapshotPath: "index/index/jhq/id/7637.html" },
  { id: "7638", title: "精准7尾", group: "jhq", moduleStatus: "live_backed", modeId: 74, snapshotPath: "index/index/jhq/id/7638.html" },
  { id: "7639", title: "必杀1头", group: "jhq", moduleStatus: "live_backed", modeId: 41, snapshotPath: "index/index/jhq/id/7639.html" },
  { id: "7640", title: "琴棋书画", group: "jhq", moduleStatus: "live_backed", modeId: 26, snapshotPath: "index/index/jhq/id/7640.html" },

  { id: "3049", title: "一波中特", group: "gs", moduleStatus: "live_backed", modeId: 143, snapshotPath: "index/index/gs/id/3049.html" },
  { id: "3050", title: "平特一尾", group: "gs", moduleStatus: "live_backed", modeId: 54, snapshotPath: "index/index/gs/id/3050.html" },
  { id: "3051", title: "稳中七肖", group: "gs", moduleStatus: "live_backed", modeId: 100, snapshotPath: "index/index/gs/id/3051.html" },
  { id: "3052", title: "5尾中特", group: "gs", moduleStatus: "live_backed", modeId: 66, snapshotPath: "index/index/gs/id/3052.html" },
  { id: "3053", title: "内幕资料", group: "gs", moduleStatus: "live_backed", modeId: 198, snapshotPath: "index/index/gs/id/3053.html" },
  { id: "3054", title: "必杀两肖", group: "gs", moduleStatus: "live_backed", modeId: 473, snapshotPath: "index/index/gs/id/3054.html" },
  { id: "3055", title: "单双公式", group: "gs", moduleStatus: "live_backed", modeId: 15, snapshotPath: "index/index/gs/id/3055.html" },
  { id: "3056", title: "黑白中特", group: "gs", moduleStatus: "live_backed", modeId: 45, snapshotPath: "index/index/gs/id/3056.html" },
]

const ARTICLE_DEFINITION_OVERRIDES = new Map<
  string,
  Pick<Twcf888ArticleDefinition, "moduleStatus" | "modeId">
>([
  ["3051", { moduleStatus: "live_backed", modeId: 100 }],
  ["7637", { moduleStatus: "live_backed", modeId: 0 }],
])

function resolveArticleDefinition(definition: Twcf888ArticleDefinition): Twcf888ArticleDefinition {
  const override = ARTICLE_DEFINITION_OVERRIDES.get(definition.id)
  return override ? { ...definition, ...override } : definition
}

const ARTICLE_MAP = new Map(
  ARTICLE_DEFINITIONS.map((definition) => {
    const resolved = resolveArticleDefinition(definition)
    return [resolved.id, resolved]
  })
)

function resolvePublicRoot() {
  const cwd = process.cwd()
  return cwd.endsWith(`${path.sep}frontend`) ? path.join(cwd, "public") : path.join(cwd, "frontend", "public")
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;")
}

function normalizeSnapshotHtml(html: string) {
  return html
    .replaceAll("新香港六合彩", "台湾创富网")
    .replaceAll("1230888888.com", "twcf888.com")
}

function buildSnapshotAbsolutePath(snapshotPath: string) {
  return path.join(resolvePublicRoot(), "vendor", "twcf888.com", snapshotPath)
}

function extractSnapshotContent(html: string) {
  const normalized = normalizeSnapshotHtml(html)
  const contentMatch = normalized.match(/<div class="cgi-info"[^>]*>([\s\S]*?)<\/div>/i)
  return contentMatch?.[1]?.trim() || "<p>当前暂无内容。</p>"
}

function splitCsv(value: unknown) {
  return String(value ?? "")
    .split(/[,\s，、;；]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function getRowRaw(row: PublicHistoryRow) {
  return (row.raw || {}) as Record<string, unknown>
}

function getPredictionSourceText(row: PublicHistoryRow) {
  const raw = getRowRaw(row)
  return String(row.prediction_text || raw.content || raw.title || "").trim()
}

function parsePredictionList(row: PublicHistoryRow) {
  const text = getPredictionSourceText(row)
  if (!text) {
    return [] as string[]
  }
  try {
    const parsed = JSON.parse(text)
    if (Array.isArray(parsed)) {
      return parsed.map((item) => String(item || "").trim()).filter(Boolean)
    }
  } catch {}
  return [text]
}

function parsePipeValue(text: string) {
  const [label, valueText = ""] = String(text || "").split("|")
  return {
    label: label.trim(),
    values: splitCsv(valueText),
  }
}

/**
 * 号码 → 五行（**号码五行**）——「精准五行 / 三行中特 / 4行4头」的唯一权威口径。
 *
 * 抄自 `backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS`
 * （= `public.fixed_data` 的 `sign='五行'`；后端 `public/api.py::_ELEMENT_MAP` 同源）。
 * 01-49 全覆盖、互不重叠：
 *   金 03,04,11,12,25,26,33,34,41,42
 *   木 07,08,15,16,23,24,37,38,45,46
 *   水 13,14,21,22,29,30,43,44
 *   火 01,02,09,10,17,18,31,32,39,40,47,48
 *   土 05,06,19,20,27,28,35,36,49
 *
 * ⚠️ `fixed_data` 里另有一份 `sign='五行肖'`，那是**生肖五行**（虎兔为木、蛇马为火…）。
 * 本站 mode 53/482 的历史正文清单就是按生肖五行拼的（`火|01,02,13,14,25,26,37,38,49`
 * 这种只覆盖 48 码的形态），于是 37 马被算成「火」（号码五行应为「木」）、
 * 24 羊被算成「土」（号码五行应为「木」）。号码五行只能由**特码号码**推导，
 * 禁止回退到生肖五行，也禁止用正文清单反推命中行。
 */
const ELEMENT_NUMBER_GROUPS: Record<string, readonly string[]> = {
  金: ["03", "04", "11", "12", "25", "26", "33", "34", "41", "42"],
  木: ["07", "08", "15", "16", "23", "24", "37", "38", "45", "46"],
  水: ["13", "14", "21", "22", "29", "30", "43", "44"],
  火: ["01", "02", "09", "10", "17", "18", "31", "32", "39", "40", "47", "48"],
  土: ["05", "06", "19", "20", "27", "28", "35", "36", "49"],
}

const ELEMENT_BY_CODE: Record<string, string> = Object.keys(ELEMENT_NUMBER_GROUPS).reduce<
  Record<string, string>
>((map, element) => {
  ELEMENT_NUMBER_GROUPS[element].forEach((code) => {
    map[code] = element
  })
  return map
}, {})

/** 特码号码 → 号码五行；号码缺失/非法返回空串（**绝不**回退到生肖五行）。 */
function elementOfCode(code: string) {
  const digits = String(code || "").replace(/[^0-9]/g, "")
  if (!digits) return ""
  return ELEMENT_BY_CODE[digits.padStart(2, "0")] || ""
}

/** 正文标签归一化：去掉引号/括号/空白与后缀「行」（`土行` → `土`）。 */
function normalizeElementLabel(label: string) {
  return String(label || "")
    .replace(/[[\]"'　\s]/g, "")
    .replace(/行$/, "")
    .trim()
}

function getOpenedResultZodiac(row: PublicHistoryRow) {
  if (!row.is_opened) {
    return ""
  }
  const raw = getRowRaw(row)
  const zodiacs = splitCsv(raw.res_sx || "")
  if (zodiacs.length > 0) {
    return zodiacs[zodiacs.length - 1] || ""
  }
  const matches = String(row.result_text || "").match(/[\u4e00-\u9fa5]/g)
  return matches?.[matches.length - 1] || ""
}

function getOpenedResultColor(row: PublicHistoryRow) {
  if (!row.is_opened) {
    return ""
  }
  const raw = getRowRaw(row)
  const colors = splitCsv(raw.res_color || "")
  return colors.length > 0 ? String(colors[colors.length - 1] || "").toLowerCase() : ""
}

function getOpenedResultCode(row: PublicHistoryRow) {
  if (!row.is_opened) {
    return ""
  }
  const raw = getRowRaw(row)
  const codes = splitCsv(raw.res_code || "")
  if (codes.length > 0) {
    return String(codes[codes.length - 1] || "").padStart(2, "0")
  }
  return String(row.result_text || "").match(/(\d{1,2})/)?.[1]?.padStart(2, "0") || ""
}

function buildFallbackResult(row: PublicHistoryRow) {
  const raw = getRowRaw(row)
  const resCode = splitCsv(raw.res_code || "").at(-1) || ""
  const resSx = splitCsv(raw.res_sx || "").at(-1) || ""
  return `${resCode}${resSx}`.trim()
}

function appendResultOutcome(resultText: string, isCorrect: boolean | null) {
  if (isCorrect === true && !/[对中]$/.test(resultText)) {
    return `${resultText}对`
  }
  if (isCorrect === false && !/[错不中]$/.test(resultText)) {
    return `${resultText}错`
  }
  return resultText
}

function buildPredictionSpan(innerHtml: string) {
  return `<span style="color: #2ecc71">${innerHtml}</span>`
}

/**
 * 单标签预测的「重复字符」展示：一个字符重复 N 次。
 *
 * 原站对只有单个取值的玩法（绝杀一肖 / 绝禁一肖 / 绝杀一行 / 特码大小）用
 * 三连写法 `【马马马】`、`【木木木】`、`【大大大】`；对头尾类
 * （平特一尾 / 绝杀一尾 / 绝杀一头 / 必杀1头）用五位数字写法 `【55555】`、`【00000】`。
 * 重复字数按玩法区分，不能统一成一个常量。
 */
const REPEAT_COUNT_CHARACTER = 3
const REPEAT_COUNT_DIGIT = 5

function repeatText(value: string, times: number) {
  const text = String(value || "").trim()
  if (!text) return ""
  return text.repeat(times)
}

/** 从 `7尾` / `0头` / `555` 这类文本里取第一个数字字符；取不到返回空串。 */
function firstDigit(value: string) {
  const match = String(value || "").match(/\d/)
  return match ? match[0] : ""
}

function wrapWholeHighlight(content: string, enabled: boolean) {
  return enabled ? `<span style="background-color: #FFFF00">${content}</span>` : content
}

function wrapJoinedValues(
  values: string[],
  options?: {
    highlight?: string
    joiner?: string
  }
) {
  const highlight = String(options?.highlight || "")
  const joiner = options?.joiner ?? ""
  return values
    .map((value) => {
      const escaped = escapeHtml(String(value || ""))
      if (highlight && String(value || "") === highlight) {
        return `<span style="background-color: #FFFF00">${escaped}</span>`
      }
      return escaped
    })
    .join(joiner)
}

function pickMatchedPipeLabel(predictionList: string[], resultCode: string) {
  for (const item of predictionList) {
    const pipeValue = parsePipeValue(item)
    if (pipeValue.values.includes(resultCode)) {
      return pipeValue.label
    }
  }
  return ""
}

function resolveBlackWhiteDisplay(row: PublicHistoryRow) {
  const raw = getRowRaw(row)
  const resultZodiac = getOpenedResultZodiac(row)
  const hei = splitCsv(raw.hei || "")
  const bai = splitCsv(raw.bai || "")

  if (!row.is_opened) {
    return {
      sideLabel: "白肖",
      values: bai.length > 0 ? bai : hei,
      highlightValue: "",
      isCorrect: null as boolean | null,
    }
  }

  if (resultZodiac && hei.includes(resultZodiac)) {
    return {
      sideLabel: "黑肖",
      values: hei,
      highlightValue: resultZodiac,
      isCorrect: true,
    }
  }

  if (resultZodiac && bai.includes(resultZodiac)) {
    return {
      sideLabel: "白肖",
      values: bai,
      highlightValue: resultZodiac,
      isCorrect: true,
    }
  }

  return {
    sideLabel: "白肖",
    values: bai.length > 0 ? bai : hei,
    highlightValue: "",
    isCorrect: false,
  }
}

function buildArticlePredictionHtml(
  definition: Twcf888ArticleDefinition,
  row: PublicHistoryRow
) {
  const raw = getRowRaw(row)
  const predictionList = parsePredictionList(row)
  const resultZodiac = getOpenedResultZodiac(row)
  const resultColor = getOpenedResultColor(row)
  const resultCode = getOpenedResultCode(row)

  switch (definition.modeId) {
    case 103: {
      const zodiac = splitCsv(raw.content || getPredictionSourceText(row))[0] || ""
      const display = zodiac ? `${zodiac}${zodiac}${zodiac}` : "--"
      const inner =
        row.is_opened && row.is_correct === true
          ? `<span style="background-color: #FFFF00">${escapeHtml(display)}</span>`
          : escapeHtml(display)
      return buildPredictionSpan(inner)
    }
    case 54: {
      const label = parsePipeValue(predictionList[0] || "").label
      const display = repeatText(firstDigit(label), REPEAT_COUNT_DIGIT) || "--"
      const inner =
        row.is_opened && row.is_correct === true
          ? `<span style="background-color: #FFFF00">${escapeHtml(display)}</span>`
          : escapeHtml(display)
      return buildPredictionSpan(inner)
    }
    case 20: {
      // 绝杀一尾：`["7尾|07,17,27,37,47"]` → 【77777】
      const label = parsePipeValue(predictionList[0] || "").label
      const display = repeatText(firstDigit(label), REPEAT_COUNT_DIGIT)
      return buildPredictionSpan(escapeHtml(display || label || "--"))
    }
    case 95: {
      const matchedLabel = pickMatchedPipeLabel(predictionList, resultCode)
      const labels = predictionList
        .map((item) => parsePipeValue(item).label.trim())
        .filter(Boolean)
        .map((label) =>
          row.is_opened && row.is_correct === false && matchedLabel && label === matchedLabel
            ? `<span style="background-color: #FFFF00">${escapeHtml(label)}</span>`
            : escapeHtml(label)
        )
      return buildPredictionSpan(labels.join("-"))
    }
    case 27:
    case 43:
    case 44:
    case 47:
    case 49:
    case 69:
    case 100:
    case 180: {
      const values =
        definition.modeId === 44
          ? predictionList
              .map((item) => parsePipeValue(item).label.trim())
              .filter(Boolean)
          : splitCsv(raw.content || getPredictionSourceText(row))
      return buildPredictionSpan(
        wrapJoinedValues(values, {
          highlight: row.is_opened && row.is_correct === true ? resultZodiac : "",
        })
      )
    }
    case 42:
    case 473: {
      const values = splitCsv(raw.content || getPredictionSourceText(row))
      return buildPredictionSpan(
        wrapJoinedValues(values, {
          highlight: row.is_opened && row.is_correct === false ? resultZodiac : "",
        })
      )
    }
    case 472: {
      // 绝杀一肖 / 绝禁一肖：单个生肖按原站样式三连展示 `兔` → 【兔兔兔】。
      const zodiac = splitCsv(raw.content || getPredictionSourceText(row))[0] || ""
      const display = repeatText(zodiac, REPEAT_COUNT_CHARACTER) || "--"
      const inner =
        row.is_opened && row.is_correct === false && resultZodiac === zodiac
          ? `<span style="background-color: #FFFF00">${escapeHtml(display)}</span>`
          : escapeHtml(display)
      return buildPredictionSpan(inner)
    }
    case 5: {
      const side = parsePipeValue(predictionList[0] || "").label || "天地肖"
      const values = splitCsv(raw.xiao || "")
      const highlightSide = row.is_opened && row.is_correct === true && resultZodiac && !values.includes(resultZodiac)
      const sideHtml = highlightSide
        ? `<span style="background-color: #FFFF00">${escapeHtml(side)}</span>`
        : escapeHtml(side)
      return buildPredictionSpan(
        `${sideHtml}+${wrapJoinedValues(values, {
          highlight: row.is_opened && row.is_correct === true ? resultZodiac : "",
        })}`
      )
    }
    case 14: {
      const jia = splitCsv(raw.jia || "")
      const ye = splitCsv(raw.ye || "")
      return buildPredictionSpan(
        `家禽：${wrapJoinedValues(jia, {
          highlight: row.is_opened && row.is_correct === true ? resultZodiac : "",
        })}+野兽：${wrapJoinedValues(ye, {
          highlight: row.is_opened && row.is_correct === true ? resultZodiac : "",
        })}`
      )
    }
    case 15: {
      const pipeValue = parsePipeValue(String(raw.content || getPredictionSourceText(row)))
      const label = pipeValue.label.replace("生肖", "数")
      const values = splitCsv(raw.xiao || "")
      return buildPredictionSpan(
        `${escapeHtml(label)}+${wrapJoinedValues(values.length ? values : pipeValue.values, {
          highlight: row.is_opened && row.is_correct === true ? resultZodiac : "",
        })}`
      )
    }
    case 26: {
      const values = splitCsv(raw.title || "")
      return buildPredictionSpan(escapeHtml(values.join("") || getPredictionSourceText(row)))
    }
    case 45: {
      const display = resolveBlackWhiteDisplay(row)
      return buildPredictionSpan(
        `${escapeHtml(display.sideLabel)}：${wrapJoinedValues(display.values, {
          highlight: display.highlightValue,
        })}`
      )
    }
    case 41: {
      // 绝杀一头 / 必杀1头：`["0头|01,…"]` → 【00000】
      const label = parsePipeValue(predictionList[0] || "").label
      const display = repeatText(firstDigit(label), REPEAT_COUNT_DIGIT)
      return buildPredictionSpan(escapeHtml(display || label || "--"))
    }
    case 98: {
      // 绝杀一行（mode 98，五行杀）：`["水|13,14,…"]` → 【水水水】。
      // 原实现只上屏 `pickMatchedPipeLabel` 的标签，命中判定的黄色高亮因此永远落空。
      const label = parsePipeValue(predictionList[0] || "").label
      const display = repeatText(label, REPEAT_COUNT_CHARACTER) || "--"
      const inner =
        row.is_opened && row.is_correct === false && label
          ? `<span style="background-color: #FFFF00">${escapeHtml(display)}</span>`
          : escapeHtml(display)
      return buildPredictionSpan(inner)
    }
    case 2: {
      const matchedLabel = pickMatchedPipeLabel(predictionList, resultCode)
      const labels = predictionList
        .map((item) => parsePipeValue(item).label.trim())
        .filter(Boolean)
        .map((label) =>
          row.is_opened && row.is_correct === true && matchedLabel && label === matchedLabel
            ? `<span style="background-color: #FFFF00">${escapeHtml(label)}</span>`
            : escapeHtml(label)
        )
      return buildPredictionSpan(labels.join(""))
    }
    case 53:
    case 482: {
      // 精准五行（6104）/ 三行中特（6111）/ 4行4头（7623 的五行部分，mode 482）。
      //
      // 判定取接口 `is_correct`（后端 `_compute_outcome_from_row` 的 element 原子 =
      // 号码五行）；**高亮必须同源**：命中行 = 特码号码的号码五行所对应的那一行。
      // 旧实现用 `pickMatchedPipeLabel`（正文里每个五行标签后的号码清单）定位命中行，
      // 而历史正文清单是**生肖五行**口径，于是「号码五行命中却零黄底」或
      // 「黄底落在生肖五行那一行」——正是用户报障的 24/37/45 一类错判。
      const specialElement = row.is_opened && row.is_correct === true ? elementOfCode(resultCode) : ""
      const labels = predictionList
        .map((item) => {
          const label = parsePipeValue(item).label.trim()
          if (!label) return ""
          return specialElement && normalizeElementLabel(label) === specialElement
            ? `<span style="background-color: #FFFF00">${escapeHtml(label)}</span>`
            : escapeHtml(label)
        })
        .filter(Boolean)
      return buildPredictionSpan(labels.join("-"))
    }
    case 74:
    case 483:
    case 12:
    case 66: {
      const matchedLabel = pickMatchedPipeLabel(predictionList, resultCode)
      const labels = predictionList
        .map((item) => {
          const pipeValue = parsePipeValue(item)
          const digitParts = pipeValue.label.match(/\d+/g)
          const display =
            digitParts && pipeValue.label.replace(/\d+/g, "").replace(/\s+/g, "").length <= 2
              ? digitParts.join("")
              : pipeValue.label.trim()
          if (!display) {
            return ""
          }
          return row.is_opened && row.is_correct === true && matchedLabel && pipeValue.label === matchedLabel
            ? `<span style="background-color: #FFFF00">${escapeHtml(display)}</span>`
            : escapeHtml(display)
        })
        .filter(Boolean)
      return buildPredictionSpan(labels.join("-"))
    }
    case 88: {
      const values = splitCsv(raw.content || getPredictionSourceText(row))
      return buildPredictionSpan(
        values
          .map((value) => {
            const padded = String(value || "").padStart(2, "0")
            return row.is_opened && row.is_correct === false && padded === resultCode
              ? `<span style="background-color: #FFFF00">${escapeHtml(padded)}</span>`
              : escapeHtml(padded)
          })
          .join(".")
      )
    }
    case 122: {
      const values = splitCsv(raw.content || getPredictionSourceText(row))
      return buildPredictionSpan(
        values
          .map((value) => {
            const padded = String(value || "").padStart(2, "0")
            return row.is_opened && row.is_correct === true && padded === resultCode
              ? `<span style="background-color: #FFFF00">${escapeHtml(padded)}</span>`
              : escapeHtml(padded)
          })
          .join(" ")
      )
    }
    case 38:
    case 143:
    case 224: {
      const values = splitCsv(raw.content || getPredictionSourceText(row))
      const joined = values.join("+") || getPredictionSourceText(row)
      const matchedWave =
        resultColor === "red"
          ? "红波"
          : resultColor === "blue"
            ? "蓝波"
            : resultColor === "green"
              ? "绿波"
              : ""
      // 高亮口径（与其它绝杀/命中类一致）：开奖目标落在候选里才标黄。
      //
      // mode 143 被两个相反的栏目共用：`一波中特`（3049，命中型）与
      // `绝杀一波`（2290，verdictInverted）。取反栏目的 `row.is_correct` 已被
      // `buildArticleRows` 翻成「杀中=true」，这里不能再拿它当命中标志，否则
      // 杀失败那期永远不标黄（线上实测 263 期 `【蓝波】开 马37错` 零黄底，
      // 而镜像栏目同一期是标黄的）。取反栏目必须用原始判定判断「开奖波色是否落在候选里」。
      const drawerInCandidate = Boolean(matchedWave) && joined.indexOf(matchedWave) !== -1
      const shouldHighlight =
        row.is_opened &&
        drawerInCandidate &&
        (definition.verdictInverted === true || row.is_correct === true)
      return buildPredictionSpan(wrapWholeHighlight(escapeHtml(joined), shouldHighlight))
    }
    case 226:
    case 470: {
      const values = splitCsv(raw.content || getPredictionSourceText(row))
      return buildPredictionSpan(
        wrapJoinedValues(values, {
          highlight: row.is_opened && row.is_correct === true ? resultZodiac : "",
        })
      )
    }
    case 28: {
      const label = parsePipeValue(predictionList[0] || "").label || getPredictionSourceText(row)
      return buildPredictionSpan(
        wrapWholeHighlight(escapeHtml(label), row.is_opened && row.is_correct === true)
      )
    }
    case 57: {
      // 特码大小：正文是 `["大|25,26,…"]`，只取标签并三连展示 `【大大大】`。
      // 原实现落到默认分支，把整串 `["大|25,26,…"]` 直接上屏（S5 原始 JSON 外泄）。
      const label = parsePipeValue(predictionList[0] || "").label
      const html = escapeHtml(repeatText(label, REPEAT_COUNT_CHARACTER) || label || "--")
      return buildPredictionSpan(
        wrapWholeHighlight(html, row.is_opened && row.is_correct === true)
      )
    }
    case 198:
    case 279:
    case 132: {
      const text = escapeHtml(getPredictionSourceText(row))
      return buildPredictionSpan(wrapWholeHighlight(text, row.is_opened && row.is_correct === true))
    }
    case 50: {
      const text = String(raw.content || getPredictionSourceText(row))
      const jiexi = splitCsv(raw.jiexi || "")
      let html = escapeHtml(text)
      if (row.is_opened && row.is_correct === true && resultZodiac && jiexi.includes(resultZodiac)) {
        html = html.replace(
          new RegExp(resultZodiac, "g"),
          `<span style="background-color: #FFFF00">${escapeHtml(resultZodiac)}</span>`
        )
      }
      return buildPredictionSpan(html)
    }
    default:
      return buildPredictionSpan(escapeHtml(getPredictionSourceText(row)))
  }
}

function buildArticleLineHtml(
  definition: Twcf888ArticleDefinition,
  row: PublicHistoryRow,
  predictionHtml: string,
  resultHtml: string
) {
  const raw = getRowRaw(row)
  const predictionList = parsePredictionList(row)
  const resultZodiac = getOpenedResultZodiac(row)

  if (definition.modeId === 14) {
    const jia = splitCsv(raw.jia || "")
    const ye = splitCsv(raw.ye || "")
    const jiaHtml = wrapJoinedValues(jia, {
      highlight: row.is_opened && row.is_correct === true ? resultZodiac : "",
    })
    const yeHtml = wrapJoinedValues(ye, {
      highlight: row.is_opened && row.is_correct === true ? resultZodiac : "",
    })
    return (
      `<p>${escapeHtml(row.issue)}期 家: 【<span style="color: #2ecc71">${jiaHtml}</span>】开 ;` +
      `野: 【<span style="color: #2ecc71">${yeHtml}</span>】开 ${resultHtml}</p>`
    )
  }

  if (definition.modeId === 5) {
    const side = parsePipeValue(predictionList[0] || "").label || "天地肖"
    const values = splitCsv(raw.xiao || "")
    const highlightSide = row.is_opened && row.is_correct === true && resultZodiac && !values.includes(resultZodiac)
    const sideHtml = highlightSide
      ? `<span style="background-color: #FFFF00">${escapeHtml(side)}</span>`
      : escapeHtml(side)
    const valuesHtml = wrapJoinedValues(values, {
      highlight: row.is_opened && row.is_correct === true ? resultZodiac : "",
    })
    return (
      `<p>${escapeHtml(row.issue)}期 ${escapeHtml(definition.title)} ` +
      `【<span style="color: #2ecc71">${sideHtml}+${valuesHtml}</span>】开 ${resultHtml}</p>`
    )
  }

  return `<p>${escapeHtml(row.issue)}期 ${escapeHtml(definition.title)} 【${predictionHtml}】开 ${resultHtml}</p>`
}

function buildArticleRows(
  definition: Twcf888ArticleDefinition,
  history: PublicHistoryRow[]
): Twcf888ArticleRow[] {
  return history.map((row) => {
    const rawCorrect =
      definition.modeId === 45 ? resolveBlackWhiteDisplay(row).isCorrect : row.is_correct
    // 绝杀一波（2290）与一波中特（3049）共用 mode 143 的候选与 is_correct，但玩法相反：
    // 先按 `verdictInverted` 收敛成该栏目自己的判定，再交给展示分支，
    // 否则「杀掉的波色开出来」会被显示成「对」。取反后也没有可高亮的命中项
    // （杀号命中 = 候选里没有开奖目标），因此渲染行不会残留黄色高亮。
    const effectiveCorrect =
      definition.verdictInverted && row.is_opened && rawCorrect !== null ? !rawCorrect : rawCorrect
    const renderRow =
      effectiveCorrect === rawCorrect ? row : { ...row, is_correct: effectiveCorrect }
    const predictionHtml = buildArticlePredictionHtml(definition, renderRow)

    let resultHtml = "???????"
    if (row.is_opened) {
      const baseResultText = escapeHtml(String(row.result_text || buildFallbackResult(row) || ""))
      const resultText =
        definition.modeId === 88
          ? effectiveCorrect === true
            ? `${baseResultText}准`
            : effectiveCorrect === false
              ? `${baseResultText}错`
              : baseResultText
          : appendResultOutcome(baseResultText, effectiveCorrect)
      if (effectiveCorrect === true) {
        resultHtml = `<font color="#FF0000">${resultText}</font>`
      } else if (effectiveCorrect === false) {
        resultHtml = `<font color="#000000">${resultText}</font>`
      } else {
        resultHtml = resultText
      }
    }

    return {
      issue: row.issue,
      predictionHtml,
      resultHtml,
      isOpened: row.is_opened,
      isCorrect: effectiveCorrect,
      lineHtml: buildArticleLineHtml(definition, row, predictionHtml, resultHtml),
    }
  })
}

function buildContentFromRows(rows: Twcf888ArticleRow[]) {
  if (!rows.length) {
    return "<p>当前彩种暂无实时预测记录。</p>"
  }
  return rows.map((row) => row.lineHtml).join("")
}

function buildFourLineFourHeadRows(
  definition: Twcf888ArticleDefinition,
  elementHistory: PublicHistoryRow[],
  headHistory: PublicHistoryRow[]
): Twcf888ArticleRow[] {
  const headMap = new Map(headHistory.map((row) => [row.issue, row]))

  return elementHistory
    .map((elementRow) => {
      const headRow = headMap.get(elementRow.issue)
      if (!headRow) {
        return null
      }

      const resultCode = getOpenedResultCode(elementRow)
      const matchedHead = pickMatchedPipeLabel(parsePredictionList(headRow), resultCode)
      // 五行部分（mode 482）只认**特码号码五行**：正文清单是生肖五行口径，
      // 拿它定位命中行会点错行（4行4头 7623）。
      const matchedElement =
        elementRow.is_opened && resultCode ? elementOfCode(resultCode) : ""
      const elementLabels = parsePredictionList(elementRow)
        .map((item) => parsePipeValue(item).label.trim())
        .filter(Boolean)
      const headLabels = parsePredictionList(headRow)
        .map((item) => parsePipeValue(item).label.replace(/[^\d]/g, "").trim())
        .filter(Boolean)

      const isOpened = Boolean(elementRow.is_opened && headRow.is_opened)
      const isCorrect = isOpened ? Boolean(matchedHead || matchedElement) : null
      const elementHtml = elementLabels
        .map((label) =>
          isOpened && !matchedHead && normalizeElementLabel(label) === matchedElement
            ? `<span style="background-color: #FFFF00">${escapeHtml(label)}</span>`
            : escapeHtml(label)
        )
        .join("")
      const headHtml = headLabels
        .map((label) =>
          isOpened && matchedHead === `${label}头`
            ? `<span style="background-color: #FFFF00">${escapeHtml(label)}</span>`
            : escapeHtml(label)
        )
        .join("")

      let resultHtml = "??????"
      if (isOpened) {
        const baseResultText = escapeHtml(String(elementRow.result_text || buildFallbackResult(elementRow) || ""))
        const resultText = appendResultOutcome(baseResultText, isCorrect)
        resultHtml =
          isCorrect === true
            ? `<font color="#FF0000">${resultText}</font>`
            : isCorrect === false
              ? `<font color="#000000">${resultText}</font>`
              : resultText
      }

      const predictionInner = `${elementHtml}+${headHtml}头`
      return {
        issue: elementRow.issue,
        predictionHtml: buildPredictionSpan(predictionInner),
        resultHtml,
        isOpened,
        isCorrect,
        lineHtml: `<p>${escapeHtml(elementRow.issue)}期 ${escapeHtml(definition.title)} 【<span style="color: #2ecc71">${predictionInner}</span>】开 ${resultHtml}</p>`,
      }
    })
    .filter((row): row is Twcf888ArticleRow => Boolean(row))
}

function buildParitySizeRows(
  definition: Twcf888ArticleDefinition,
  parityHistory: PublicHistoryRow[],
  sizeHistory: PublicHistoryRow[]
): Twcf888ArticleRow[] {
  const sizeMap = new Map(sizeHistory.map((row) => [row.issue, row]))

  return parityHistory
    .map((parityRow) => {
      const sizeRow = sizeMap.get(parityRow.issue)
      if (!sizeRow) {
        return null
      }

      const parityRaw = getRowRaw(parityRow)
      const sizeRaw = getRowRaw(sizeRow)
      const parityText = String(parityRaw.content || parityRow.prediction_text || "").trim()
      const sizeText = String(sizeRaw.content || sizeRow.prediction_text || "").trim()
      const predictionText = `${parityText}+${sizeText}`

      const isOpened = Boolean(parityRow.is_opened && sizeRow.is_opened)
      const isCorrect = isOpened ? Boolean(parityRow.is_correct && sizeRow.is_correct) : null

      let resultHtml = "??????"
      if (isOpened) {
        const baseResultText = escapeHtml(
          String(parityRow.result_text || buildFallbackResult(parityRow) || "")
        )
        const resultText = appendResultOutcome(baseResultText, isCorrect)
        resultHtml =
          isCorrect === true
            ? `<font color="#FF0000">${resultText}</font>`
            : isCorrect === false
              ? `<font color="#000000">${resultText}</font>`
              : resultText
      }

      return {
        issue: parityRow.issue,
        predictionHtml: buildPredictionSpan(escapeHtml(predictionText)),
        resultHtml,
        isOpened,
        isCorrect,
        lineHtml: `<p>${escapeHtml(parityRow.issue)}期 ${escapeHtml(definition.title)} 【<span style="color: #2ecc71">${escapeHtml(predictionText)}</span>】开 ${resultHtml}</p>`,
      }
    })
    .filter((row): row is Twcf888ArticleRow => Boolean(row))
}

async function loadSnapshotHtml(definition: Twcf888ArticleDefinition) {
  const filePath = buildSnapshotAbsolutePath(definition.snapshotPath)
  const rawHtml = await fs.readFile(filePath, "utf-8")
  return extractSnapshotContent(rawHtml)
}

async function loadLiveModules(modeIds: number[], lotteryType: number) {
  const sitePage = await getPublicSitePageData({
    siteId: SITE?.defaultWebId ?? 8,
    lotteryType,
    historyLimit: DEFAULT_HISTORY_LIMIT,
  })
  const modeMap = new Map(
    sitePage.modules.map((module) => [Number(module.default_modes_id), module])
  )
  return modeIds.map((modeId) => modeMap.get(modeId) || null)
}

async function loadLiveModule(modeId: number, lotteryType: number) {
  const [module] = await loadLiveModules([modeId], lotteryType)
  return module
}

function buildBlockedNotes(title: string) {
  return [
    `${title} 当前属于 blocked_requires_backend_work。`,
    "v1 仅保留原站静态快照访问，不会伪造成 live 数据。",
  ]
}

function buildSnapshotNotes(title: string) {
  return [
    `${title} 当前属于 snapshot_only。`,
    "该栏目不是已确认 live_backed 的预测模块，当前继续提供静态快照访问。",
  ]
}

function buildMissingLiveNotes(title: string, modeId: number, lotteryType: number) {
  return [
    `${title} 在 twcf888 v1 蓝图中要求接入 live_backed 数据。`,
    `当前 lottery_type=${lotteryType} 未返回 mode_id=${modeId} 的实时记录，因此页面不会伪造开奖结果。`,
  ]
}

export function getTwcf888ArticleDefinition(articleId: string) {
  return ARTICLE_MAP.get(articleId) || null
}

export function getTwcf888ArticleCatalog() {
  return ARTICLE_DEFINITIONS.map(resolveArticleDefinition)
}

export function getTwcf888SiteRequestDefaults(
  lotteryType: number = SITE?.defaultLotteryTypeId ?? 3
) {
  return {
    site_key: SITE?.siteKey || "twcf888",
    site_id: SITE?.defaultWebId ?? 8,
    web_id: SITE?.defaultWebId ?? 8,
    lottery_type: lotteryType,
    domain: SITE?.domains[0] || "www.twcf888.com",
  }
}

export async function getTwcf888ArticleDetail(
  articleId: string,
  options: {
    lotteryType: number
    group?: string
  }
): Promise<Twcf888ArticleDetail | null> {
  const definition = ARTICLE_MAP.get(articleId)
  if (!definition) {
    return null
  }
  if (options.group && options.group !== definition.group) {
    return null
  }

  if (definition.moduleStatus === "live_backed" && definition.modeId !== null) {
    if (definition.id === "7637") {
      const [parityModule, sizeModule] = await loadLiveModules([28, 57], options.lotteryType)
      if (parityModule?.history?.length && sizeModule?.history?.length) {
        const rows = buildParitySizeRows(definition, parityModule.history, sizeModule.history)
        if (rows.length > 0) {
          return {
            id: definition.id,
            title: definition.title,
            author: AUTHOR,
            group: definition.group,
            sourceKind: "live-module",
            modeId: definition.modeId,
            moduleStatus: definition.moduleStatus,
            status: "ok",
            missingMapping: false,
            notes: [],
            contentHtml: buildContentFromRows(rows),
            rows,
            requestedLotteryType: options.lotteryType,
          }
        }
      }

      return {
        id: definition.id,
        title: definition.title,
        author: AUTHOR,
        group: definition.group,
        sourceKind: "missing-live-data",
        modeId: definition.modeId,
        moduleStatus: definition.moduleStatus,
        status: "missing_live_data",
        missingMapping: false,
        notes: buildMissingLiveNotes(definition.title, 0, options.lotteryType),
        contentHtml: "<p>当前彩种缺少 mode 28(单双) 或 mode 57(大小) 的实时预测记录。</p>",
        rows: [],
        requestedLotteryType: options.lotteryType,
      }
    }

    if (definition.id === "7623") {
      const [elementModule, headModule] = await loadLiveModules([482, 483], options.lotteryType)
      if (elementModule?.history?.length && headModule?.history?.length) {
        const rows = buildFourLineFourHeadRows(definition, elementModule.history, headModule.history)
        if (rows.length > 0) {
          return {
            id: definition.id,
            title: definition.title,
            author: AUTHOR,
            group: definition.group,
            sourceKind: "live-module",
            modeId: definition.modeId,
            moduleStatus: definition.moduleStatus,
            status: "ok",
            missingMapping: false,
            notes: [],
            contentHtml: buildContentFromRows(rows),
            rows,
            requestedLotteryType: options.lotteryType,
          }
        }
      }

      return {
        id: definition.id,
        title: definition.title,
        author: AUTHOR,
        group: definition.group,
        sourceKind: "missing-live-data",
        modeId: definition.modeId,
        moduleStatus: definition.moduleStatus,
        status: "missing_live_data",
        missingMapping: false,
        notes: buildMissingLiveNotes(definition.title, definition.modeId, options.lotteryType),
        contentHtml: "<p>褰撳墠褰╃缂哄皯瀵瑰簲鐨勫疄鏃堕娴嬭褰曘€?/p>",
        rows: [],
        requestedLotteryType: options.lotteryType,
      }
    }

    const module = await loadLiveModule(definition.modeId, options.lotteryType)
    if (module && module.history.length > 0) {
      const rows = buildArticleRows(definition, module.history)
      return {
        id: definition.id,
        title: definition.title,
        author: AUTHOR,
        group: definition.group,
        sourceKind: "live-module",
        modeId: definition.modeId,
        moduleStatus: definition.moduleStatus,
        status: "ok",
        missingMapping: false,
        notes: [],
        contentHtml: buildContentFromRows(rows),
        rows,
        requestedLotteryType: options.lotteryType,
      }
    }

    return {
      id: definition.id,
      title: definition.title,
      author: AUTHOR,
      group: definition.group,
      sourceKind: "missing-live-data",
      modeId: definition.modeId,
      moduleStatus: definition.moduleStatus,
      status: "missing_live_data",
      missingMapping: false,
      notes: buildMissingLiveNotes(definition.title, definition.modeId, options.lotteryType),
      contentHtml: "<p>当前彩种缺少对应的实时预测记录。</p>",
      rows: [],
      requestedLotteryType: options.lotteryType,
    }
  }

  const contentHtml = await loadSnapshotHtml(definition)
  const notes =
    definition.moduleStatus === "snapshot_only"
      ? buildSnapshotNotes(definition.title)
      : buildBlockedNotes(definition.title)

  return {
    id: definition.id,
    title: definition.title,
    author: AUTHOR,
    group: definition.group,
    sourceKind: "vendor-snapshot",
    modeId: definition.modeId,
    moduleStatus: definition.moduleStatus,
    status: "fallback_snapshot",
    missingMapping: definition.moduleStatus === "blocked_requires_backend_work",
    notes,
    contentHtml,
    rows: [],
    requestedLotteryType: options.lotteryType,
  }
}
