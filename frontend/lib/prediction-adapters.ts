import type { PublicHistoryRow, PublicModule, PublicSitePageData } from "@/lib/site-page"
import type {
  CanonicalPredictionModule,
  CanonicalPredictionRow,
  CanonicalPredictionSource,
} from "@/lib/prediction-contract"
import type { VendorHomepageModule, VendorHomepageModulesResponse } from "@/lib/vendor-homepage"
import { buildCanonicalPredictionModules } from "@/lib/prediction-contract"

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

function cleanText(value: unknown) {
  return String(value ?? "").trim()
}

function toPublicHistoryRow(row: CanonicalPredictionRow): PublicHistoryRow {
  const raw = asRecord(row.raw)
  return {
    issue: row.issue,
    year: row.year,
    term: row.term,
    prediction_text: row.prediction.text || row.prediction.tokens.join(" "),
    image_url: row.prediction.imageUrl,
    result_text: row.result.text,
    is_opened: row.result.isOpened,
    is_correct: row.result.isCorrect,
    source_web_id: typeof raw.source_web_id === "number" ? raw.source_web_id : null,
    raw: {
      ...raw,
      prediction: row.prediction,
      result: row.result,
      status: row.status,
    },
  }
}

function toPublicModule(module: CanonicalPredictionModule): PublicModule {
  const source = module.source.extra as Record<string, unknown>
  return {
    id: typeof module.source.moduleId === "number" ? module.source.moduleId : 0,
    mechanism_key: module.source.mechanismKey || module.moduleKey,
    title: module.title,
    default_modes_id: Number(source.default_modes_id || 0),
    default_table: cleanText(source.default_table),
    sort_order: Number(source.sort_order || 0),
    status: source.status !== false,
    history: module.rows.map(toPublicHistoryRow),
    cssClass: cleanText(module.source.displayStyle) || undefined,
  }
}

function toVendorHistoryRow(row: CanonicalPredictionRow) {
  const raw = asRecord(row.raw)
  const result = {
    res_code: cleanText(row.result.code || raw.res_code || raw.code),
    res_sx: cleanText(row.result.zodiac || raw.res_sx || raw.zodiac),
    res_color: cleanText(row.result.color || raw.res_color || raw.color),
    result_text: row.result.text,
    is_opened: row.result.isOpened,
  }

  return {
    ...raw,
    issue: row.issue,
    year: row.year,
    term: row.term,
    result,
    is_opened: row.result.isOpened,
    is_correct: row.result.isCorrect,
    raw: {
      ...raw,
      prediction: row.prediction,
      result,
      status: row.status,
    },
  }
}

function toVendorHomepageModule(module: CanonicalPredictionModule): VendorHomepageModule {
  const history = module.rows.map(toVendorHistoryRow)

  return {
    module_key: module.moduleKey as VendorHomepageModule["module_key"],
    title: module.title,
    display_style: cleanText(module.source.displayStyle),
    history: history as never,
  } as VendorHomepageModule
}

export function adaptPublicSitePageDataWithCanonicalModules(
  siteData: PublicSitePageData,
  canonicalModules: CanonicalPredictionModule[]
): PublicSitePageData {
  if (!canonicalModules.length) return siteData

  const modulesByKey = new Map(canonicalModules.map((module) => [module.moduleKey, module]))
  return {
    ...siteData,
    modules: siteData.modules.map((module) => {
      const canonical = modulesByKey.get(module.mechanism_key) || modulesByKey.get(`legacy_${module.mechanism_key}`)
      return canonical ? toPublicModule(canonical) : module
    }),
  }
}

export function adaptVendorHomepageModulesWithCanonicalModules(
  payload: VendorHomepageModulesResponse,
  canonicalModules: CanonicalPredictionModule[]
): VendorHomepageModulesResponse {
  if (!canonicalModules.length) return payload

  const modulesByKey = new Map(canonicalModules.map((module) => [module.moduleKey, module]))
  return {
    ...payload,
    data: payload.data.map((module) => {
      const canonical = modulesByKey.get(module.module_key) || modulesByKey.get(`legacy_${module.module_key}`)
      return canonical ? toVendorHomepageModule(canonical) : module
    }),
  }
}

export function buildPredictionModulesForSite(
  siteData: PublicSitePageData,
  homepageModules: VendorHomepageModulesResponse
) {
  const canonicalModules = buildCanonicalPredictionModules({
    sitePageData: siteData,
    vendorHomepageModules: homepageModules,
  })

  return {
    canonicalModules,
    siteData: adaptPublicSitePageDataWithCanonicalModules(siteData, canonicalModules),
    homepageModules: adaptVendorHomepageModulesWithCanonicalModules(homepageModules, canonicalModules),
  }
}

export function resolveCanonicalSourceTag(source: CanonicalPredictionSource) {
  return `${source.kind}:${source.moduleKey}`
}
