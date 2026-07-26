import { getAllSiteConfigs, getSiteConfig, type FrontendSiteConfig } from "@/lib/sites"

export type RegisteredSiteKey = FrontendSiteConfig["siteKey"]

export type SiteApiContext = {
  site: FrontendSiteConfig
  siteKey: RegisteredSiteKey
  searchParams: URLSearchParams
  historyLimit: number
  siteId: number
  webId: number
  lotteryType: 1 | 2 | 3
  modeIds?: number[]
}

export function getAllRegisteredSites() {
  return getAllSiteConfigs()
}

export function getAllSiteKeys() {
  return getAllRegisteredSites().map((site) => site.siteKey)
}

export function getRegisteredSite(siteKey: string) {
  const site = getSiteConfig(siteKey)
  if (!site) {
    throw new Error(`Unknown siteKey: ${siteKey}`)
  }
  return site
}

function getRegisteredSiteByDefaultSiteId(siteId: number) {
  const site = getAllSiteConfigs().find((candidate) => candidate.defaultSiteId === siteId)
  if (!site) {
    throw new Error(`Unknown site_id: ${siteId}`)
  }
  return site
}

function parsePositiveInt(value: string | null, fallback: number) {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? Math.min(parsed, 20) : fallback
}

function parseLotteryType(value: string | null, fallback: 1 | 2 | 3): 1 | 2 | 3 {
  const parsed = Number(value)
  return parsed === 1 || parsed === 2 || parsed === 3 ? parsed : fallback
}

function parseModeIds(value: string | null) {
  if (!value) return undefined
  const modeIds = value
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isInteger(item) && item > 0)
  return modeIds.length ? modeIds : undefined
}

export function resolveSiteApiContext(
  siteKey: string,
  searchParams: URLSearchParams = new URLSearchParams()
): SiteApiContext {
  const site = getRegisteredSite(siteKey)
  return {
    site,
    siteKey: site.siteKey,
    searchParams,
    historyLimit: parsePositiveInt(searchParams.get("history_limit"), 8),
    // The path site owns identity; query values may only refine non-site options.
    siteId: site.defaultSiteId,
    webId: site.defaultWebId,
    lotteryType: parseLotteryType(
      searchParams.get("lottery_type") || searchParams.get("type"),
      site.defaultLotteryTypeId
    ),
    modeIds: parseModeIds(searchParams.get("mode_ids")),
  }
}

/**
 * The legacy non-path prediction route needs an explicit registered site.
 * Unlike path-owned routes, it has no path segment from which to derive identity.
 */
export function resolvePredictionModulesCompatibilityContext(
  searchParams: URLSearchParams = new URLSearchParams()
): SiteApiContext {
  const siteKey = searchParams.get("site_key") || searchParams.get("siteKey")
  const siteIdValue = searchParams.get("site_id")
  const siteByKey = siteKey ? getRegisteredSite(siteKey) : null
  const siteById = siteIdValue ? getRegisteredSiteByDefaultSiteId(Number(siteIdValue)) : null

  if (!siteByKey && !siteById) {
    throw new Error("site_id or a registered site_key is required")
  }
  if (siteByKey && siteById && siteByKey.siteKey !== siteById.siteKey) {
    throw new Error("site_key and site_id must identify the same registered site")
  }

  return resolveSiteApiContext((siteByKey || siteById)!.siteKey, searchParams)
}

export function buildSiteEnvelope<T>(context: SiteApiContext, data: T) {
  return {
    ok: true as const,
    site: {
      site_key: context.site.siteKey,
      site_id: context.site.defaultWebId,
      web_id: context.site.defaultWebId,
      requested_site_id: context.siteId,
      requested_web_id: context.webId,
      lottery_type: context.lotteryType,
      domain: context.site.domains[0] || null,
      render_mode: context.site.renderMode,
    },
    data,
  }
}
