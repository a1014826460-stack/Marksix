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
  { id: "2290", title: "绝杀一波", group: "jsb", moduleStatus: "live_backed", modeId: 143, snapshotPath: "index/index/jsb/id/2290.html" },
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
      const digit = label.replace(/[^\d]/g, "").slice(0, 1)
      const display = digit ? `${digit}${digit}${digit}` : "--"
      const inner =
        row.is_opened && row.is_correct === true
          ? `<span style="background-color: #FFFF00">${escapeHtml(display)}</span>`
          : escapeHtml(display)
      return buildPredictionSpan(inner)
    }
    case 20:
      return buildPredictionSpan(escapeHtml(parsePipeValue(predictionList[0] || "").label || "--"))
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
    case 472:
    case 473: {
      const values = splitCsv(raw.content || getPredictionSourceText(row))
      return buildPredictionSpan(
        wrapJoinedValues(values, {
          highlight: row.is_opened && row.is_correct === false ? resultZodiac : "",
        })
      )
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
    case 41:
      return buildPredictionSpan(escapeHtml(parsePipeValue(predictionList[0] || "").label || "--"))
    case 98: {
      const matchedLabel = pickMatchedPipeLabel(predictionList, resultCode)
      return buildPredictionSpan(
        row.is_opened && row.is_correct === false && matchedLabel
          ? `<span style="background-color: #FFFF00">${escapeHtml(matchedLabel)}</span>`
          : escapeHtml(parsePipeValue(predictionList[0] || "").label || "--")
      )
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
    case 74:
    case 482:
    case 483:
    case 12:
    case 53:
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
      return buildPredictionSpan(
        wrapWholeHighlight(
          escapeHtml(joined),
          row.is_opened && row.is_correct === true && joined.indexOf(matchedWave) !== -1
        )
      )
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
    case 57:
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
    const predictionHtml = buildArticlePredictionHtml(definition, row)
    const effectiveCorrect =
      definition.modeId === 45 ? resolveBlackWhiteDisplay(row).isCorrect : row.is_correct

    let resultHtml = "???????"
    if (row.is_opened) {
      const baseResultText = escapeHtml(String(row.result_text || buildFallbackResult(row) || ""))
      const resultText =
        definition.modeId === 88
          ? effectiveCorrect === true
            ? `${baseResultText}鍑?`
            : effectiveCorrect === false
              ? `${baseResultText}閿?`
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
      const matchedElement = pickMatchedPipeLabel(parsePredictionList(elementRow), resultCode)
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
          isOpened && !matchedHead && matchedElement === label
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
        lineHtml: `<p>${escapeHtml(elementRow.issue)}鏈?${escapeHtml(definition.title)} 銆?span style="color: #2ecc71">${predictionInner}</span>銆戝紑 ${resultHtml}</p>`,
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
