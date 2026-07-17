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

function parsePositiveInt(value: string | null, fallback: number) {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
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
  const webId = parsePositiveInt(searchParams.get("web_id") || searchParams.get("web"), site.defaultWebId)

  return {
    site,
    siteKey: site.siteKey,
    searchParams,
    historyLimit: parsePositiveInt(searchParams.get("history_limit"), 8),
    siteId: parsePositiveInt(searchParams.get("site_id"), webId),
    webId,
    lotteryType: parseLotteryType(
      searchParams.get("lottery_type") || searchParams.get("type"),
      site.defaultLotteryTypeId
    ),
    modeIds: parseModeIds(searchParams.get("mode_ids")),
  }
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
