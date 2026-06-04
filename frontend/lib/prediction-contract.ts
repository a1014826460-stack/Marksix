import type { PublicHistoryRow, PublicModule, PublicSitePageData } from "@/lib/site-page"
import type { VendorHomepageModule, VendorHomepageModulesResponse } from "@/lib/vendor-homepage"

export type CanonicalPredictionDisplayKind =
  | "text"
  | "tokens"
  | "groups"
  | "image"
  | "composite"
  | "unknown"

export type CanonicalPredictionStatus =
  | "pending"
  | "opened-hit"
  | "opened-miss"
  | "opened-unknown"

export type CanonicalPredictionGroup = {
  key: string
  label?: string
  tokens: string[]
}

export type CanonicalPredictionValue = {
  text: string
  tokens: string[]
  groups: CanonicalPredictionGroup[]
  imageUrl?: string
  extra: Record<string, unknown>
}

export type CanonicalPredictionResult = {
  isOpened: boolean
  isCorrect: boolean | null
  code?: string
  zodiac?: string
  color?: string
  text: string
}

export type CanonicalPredictionSource = {
  kind: "public-site-page" | "vendor-homepage-modules" | "mode-payload-legacy"
  moduleId?: number
  moduleKey: string
  mechanismKey?: string
  displayStyle?: string
  sourceWebId?: number | null
  extra: Record<string, unknown>
}

export type CanonicalPredictionRow = {
  issue: string
  year: string
  term: string
  prediction: CanonicalPredictionValue
  result: CanonicalPredictionResult
  status: CanonicalPredictionStatus
  raw: Record<string, unknown>
}

export type CanonicalPredictionModule = {
  moduleKey: string
  title: string
  displayKind: CanonicalPredictionDisplayKind
  rows: CanonicalPredictionRow[]
  source: CanonicalPredictionSource
}

export type CanonicalPredictionBuildInput = {
  sitePageData?: PublicSitePageData | null
  vendorHomepageModules?: VendorHomepageModulesResponse | null
}

const GROUP_LABELS: Record<string, string> = {
  xiao_9: "九肖",
  xiao_7: "七肖",
  xiao_5: "五肖",
  xiao_4: "四肖",
  xiao_3: "三肖",
  xiao_2: "二肖",
  code_14: "14码",
  code_12: "12码",
  code_8: "8码",
  code_5: "五码",
  code_4: "四码",
  code_3: "三码",
  code_2: "二码",
  wave_groups: "波色",
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

function cleanText(value: unknown) {
  return String(value ?? "").trim()
}

function uniqueStrings(items: unknown[]) {
  return [...new Set(items.map((item) => cleanText(item)).filter(Boolean))]
}

function normalizeCode(value: unknown) {
  const text = cleanText(value)
  if (!text) return ""
  return /^\d{1,2}$/.test(text) ? text.padStart(2, "0") : text
}

export function splitPredictionTokens(value: unknown): string[] {
  const text = cleanText(value)
  if (!text) return []

  try {
    const parsed = JSON.parse(text)
    if (Array.isArray(parsed)) {
      return uniqueStrings(parsed)
    }
  } catch {
    // Plain text is common for legacy mode_payload rows.
  }

  const stripped = text.replace(/^[\["']+|[\]"']+$/g, "")
  const split = stripped
    .split(/[,\s.、，|+/-]+/)
    .map((item) => item.trim())
    .filter(Boolean)
  if (split.length > 1) return uniqueStrings(split)

  const chineseChars = Array.from(stripped).filter((item) => /[\u4e00-\u9fff]/.test(item))
  return chineseChars.length > 1 ? uniqueStrings(chineseChars) : [stripped].filter(Boolean)
}

function collectGroupsFromValue(value: unknown, prefix = ""): CanonicalPredictionGroup[] {
  if (Array.isArray(value)) {
    const tokens = uniqueStrings(value)
    return tokens.length
      ? [
          {
            key: prefix || "items",
            label: GROUP_LABELS[prefix],
            tokens,
          },
        ]
      : []
  }

  if (!value || typeof value !== "object") return []

  const groups: CanonicalPredictionGroup[] = []
  for (const [key, nested] of Object.entries(value as Record<string, unknown>)) {
    const groupKey = prefix ? `${prefix}.${key}` : key
    if (Array.isArray(nested)) {
      const objectItems = nested.filter((item) => item && typeof item === "object")
      if (objectItems.length === nested.length && objectItems.length > 0) {
        for (const [index, item] of objectItems.entries()) {
          const itemRecord = asRecord(item)
          const label = cleanText(itemRecord.label) || `${GROUP_LABELS[key] || key}${index + 1}`
          const tokens = uniqueStrings([
            ...("codes" in itemRecord && Array.isArray(itemRecord.codes) ? itemRecord.codes : []),
            ...("items" in itemRecord && Array.isArray(itemRecord.items) ? itemRecord.items : []),
          ])
          if (tokens.length) groups.push({ key: `${groupKey}.${index}`, label, tokens })
        }
        continue
      }

      const tokens = uniqueStrings(nested)
      if (tokens.length) {
        groups.push({ key: groupKey, label: GROUP_LABELS[key], tokens })
      }
      continue
    }

    groups.push(...collectGroupsFromValue(nested, groupKey))
  }
  return groups
}

function collectGroups(...values: unknown[]) {
  const groups = values.flatMap((value) => collectGroupsFromValue(value))
  const seen = new Set<string>()
  return groups.filter((group) => {
    const id = `${group.key}:${group.tokens.join(",")}`
    if (seen.has(id)) return false
    seen.add(id)
    return true
  })
}

function resultFromLegacyFields(input: {
  resultText?: unknown
  isOpened?: unknown
  isCorrect?: unknown
  raw?: Record<string, unknown>
  result?: Record<string, unknown>
}): CanonicalPredictionResult {
  const raw = input.raw || {}
  const result = input.result || {}
  const text =
    cleanText(input.resultText) ||
    cleanText(result.result_text) ||
    cleanText(raw.result_text) ||
    cleanText(raw.res_text)
  const code = normalizeCode(result.res_code || raw.res_code || raw.code)
  const zodiac = cleanText(result.res_sx || raw.res_sx || raw.zodiac || raw.sx)
  const color = cleanText(result.res_color || raw.res_color || raw.color)
  const isOpened = Boolean(input.isOpened ?? result.is_opened ?? raw.is_opened)
  const isCorrectValue = input.isCorrect ?? raw.is_correct
  const isCorrect = typeof isCorrectValue === "boolean" ? isCorrectValue : null

  return {
    isOpened,
    isCorrect,
    code: code || undefined,
    zodiac: zodiac || undefined,
    color: color || undefined,
    text,
  }
}

function statusFromResult(result: CanonicalPredictionResult): CanonicalPredictionStatus {
  if (!result.isOpened) return "pending"
  if (result.isCorrect === true) return "opened-hit"
  if (result.isCorrect === false) return "opened-miss"
  return "opened-unknown"
}

function inferDisplayKind(row: CanonicalPredictionRow): CanonicalPredictionDisplayKind {
  if (row.prediction.imageUrl) return "image"
  if (row.prediction.groups.length > 0) return "groups"
  if (row.prediction.tokens.length > 1) return "tokens"
  if (row.prediction.text) return "text"
  return "unknown"
}

function mergeDisplayKind(kinds: CanonicalPredictionDisplayKind[]): CanonicalPredictionDisplayKind {
  if (kinds.includes("composite")) return "composite"
  if (kinds.includes("groups")) return "groups"
  if (kinds.includes("image")) return "image"
  if (kinds.includes("tokens")) return "tokens"
  if (kinds.includes("text")) return "text"
  return "unknown"
}

function canonicalRowFromPublicHistory(row: PublicHistoryRow): CanonicalPredictionRow {
  const raw = asRecord(row.raw)
  const text = cleanText(row.prediction_text || raw.content || raw.prediction)
  const groups = collectGroups(raw.groups, raw.xiao_groups, raw.code_groups, raw.wave_groups)
  const prediction: CanonicalPredictionValue = {
    text,
    tokens: groups.length ? uniqueStrings(groups.flatMap((group) => group.tokens)) : splitPredictionTokens(text),
    groups,
    imageUrl: cleanText(row.image_url) || undefined,
    extra: {
      content: raw.content,
    },
  }
  const result = resultFromLegacyFields({
    resultText: row.result_text,
    isOpened: row.is_opened,
    isCorrect: row.is_correct,
    raw,
  })

  return {
    issue: cleanText(row.issue),
    year: cleanText(row.year),
    term: cleanText(row.term),
    prediction,
    result,
    status: statusFromResult(result),
    raw: {
      ...raw,
      source_web_id: row.source_web_id,
      prediction_text: row.prediction_text,
      image_url: row.image_url,
      result_text: row.result_text,
      is_opened: row.is_opened,
      is_correct: row.is_correct,
    },
  }
}

export function canonicalizePublicSitePageData(data: PublicSitePageData | null | undefined) {
  if (!data?.modules?.length) return [] as CanonicalPredictionModule[]

  return data.modules.map((module) => {
    const rows = (module.history || []).map(canonicalRowFromPublicHistory)
    return {
      moduleKey: module.mechanism_key,
      title: module.title,
      displayKind: mergeDisplayKind(rows.map(inferDisplayKind)),
      rows,
      source: {
        kind: "public-site-page",
        moduleId: module.id,
        moduleKey: module.mechanism_key,
        mechanismKey: module.mechanism_key,
        displayStyle: module.cssClass,
        extra: {
          default_modes_id: module.default_modes_id,
          default_table: module.default_table,
          sort_order: module.sort_order,
          status: module.status,
          cssClass: module.cssClass,
        },
      },
    } satisfies CanonicalPredictionModule
  })
}

function vendorResult(row: Record<string, unknown>) {
  return resultFromLegacyFields({
    result: asRecord(row.result),
    isOpened: row.is_opened,
    isCorrect: row.is_correct,
    raw: row,
  })
}

function canonicalRowFromVendorHistory(row: Record<string, unknown>): CanonicalPredictionRow {
  const groups = collectGroups(row.groups, row.xiao_groups, row.code_groups, row.wave_groups)
  const text =
    cleanText(row.display_text) ||
    cleanText(row.text) ||
    cleanText(asRecord(row.best_pick).text) ||
    uniqueStrings([
      ...groups.flatMap((group) => group.tokens),
      ...(Array.isArray(row.picks) ? row.picks : []),
      ...(Array.isArray(row.xiao_pair) ? row.xiao_pair : []),
    ]).join(" ")
  const tokens = uniqueStrings([
    ...splitPredictionTokens(text),
    ...groups.flatMap((group) => group.tokens),
    ...(Array.isArray(row.picks) ? row.picks : []),
    ...(Array.isArray(row.xiao_pair) ? row.xiao_pair : []),
  ])
  const result = vendorResult(row)

  return {
    issue: cleanText(row.issue),
    year: cleanText(row.year),
    term: cleanText(row.term),
    prediction: {
      text,
      tokens,
      groups,
      imageUrl: cleanText(row.image_url) || undefined,
      extra: {
        best_pick: row.best_pick,
        daxiao: row.daxiao,
        tou_code: row.tou_code,
        tiandi: row.tiandi,
        xiao_pair: row.xiao_pair,
        picks: row.picks,
        wave_groups: row.wave_groups,
      },
    },
    result,
    status: statusFromResult(result),
    raw: row,
  }
}

export function canonicalizeVendorHomepageModules(data: VendorHomepageModulesResponse | null | undefined) {
  if (!data?.data?.length) return [] as CanonicalPredictionModule[]

  return data.data.map((module: VendorHomepageModule) => {
    const moduleRecord = module as unknown as Record<string, unknown>
    const rows = (Array.isArray(moduleRecord.history) ? moduleRecord.history : []).map((row) =>
      canonicalRowFromVendorHistory(asRecord(row))
    )
    return {
      moduleKey: cleanText(moduleRecord.module_key),
      title: cleanText(moduleRecord.title),
      displayKind: "composite",
      rows,
      source: {
        kind: "vendor-homepage-modules",
        moduleKey: cleanText(moduleRecord.module_key),
        displayStyle: cleanText(moduleRecord.display_style),
        sourceWebId: data.site.web_id,
        extra: {
          site: data.site,
          display_style: moduleRecord.display_style,
        },
      },
    } satisfies CanonicalPredictionModule
  })
}

export function buildCanonicalPredictionModules(input: CanonicalPredictionBuildInput) {
  return [
    ...canonicalizePublicSitePageData(input.sitePageData),
    ...canonicalizeVendorHomepageModules(input.vendorHomepageModules),
  ]
}

export function findCanonicalPredictionModule(
  modules: CanonicalPredictionModule[],
  moduleKey: string
) {
  return modules.find(
    (module) =>
      module.moduleKey === moduleKey ||
      module.source.mechanismKey === moduleKey ||
      module.moduleKey === `legacy_${moduleKey}` ||
      module.source.mechanismKey === `legacy_${moduleKey}`
  )
}

