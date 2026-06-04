import type { LotteryGame } from "@/lib/lotteryData"
import type { Metadata } from "next"

export type FrontendSiteConfig = {
  siteKey: string
  routePath: `/${string}` | "/"
  vendorIndexPath: `/${string}`
  domains: string[]
  legacyPublicBasePath: `/${string}`
  defaultGame: LotteryGame
  defaultWebId: number
  defaultLotteryTypeId: 1 | 2 | 3
  forumTitle: string
  metadataTitle?: string
  metadataDescription?: string
  faviconPath?: `/${string}`
  headerImagePath?: `/${string}`
  embedPath?: `/${string}`
  shellCssPaths?: readonly `/${string}`[]
  pageCssPaths?: readonly `/${string}`[]
}

export type SiteRequestMatch = {
  site: FrontendSiteConfig
  refererPath: string
  refererUrl: URL | null
  matchedByHost: boolean
  matchedByRefererHost: boolean
}

const SITE_CONFIGS: FrontendSiteConfig[] = [
  {
    siteKey: "shengshi8800",
    routePath: "/",
    vendorIndexPath: "/vendor/shengshi8800/embed.html?type=3&web=4",
    domains: ["localhost", "127.0.0.1"],
    legacyPublicBasePath: "/vendor/shengshi8800",
    defaultGame: "taiwan",
    defaultWebId: 4,
    defaultLotteryTypeId: 3,
    forumTitle: "台湾六合彩论坛",
    metadataTitle: "全网最准尽在台湾六合彩论坛",
    metadataDescription: "全网最准尽在台湾六合彩论坛",
    faviconPath: "/favicon.ico",
    headerImagePath: "/vendor/shengshi8800/static/picture/header.jpg",
    embedPath: "/vendor/shengshi8800/embed.html",
    shellCssPaths: [
      "/vendor/shengshi8800/static/css/style1.css",
      "/vendor/shengshi8800/static/css/style3.css",
    ],
  },
  {
    siteKey: "twsaimahui",
    routePath: "/twsaimahui",
    vendorIndexPath: "/vendor/twsaimahui/index.html",
    domains: ["www.twsaimahui.com", "twsaimahui.com"],
    legacyPublicBasePath: "/vendor/twsaimahui",
    defaultGame: "taiwan",
    defaultWebId: 6,
    defaultLotteryTypeId: 3,
    forumTitle: "台湾赛马会",
    metadataTitle: "台湾赛马会：官方正版请认准唯一官方",
    metadataDescription: "台湾赛马会：官方正版请认准唯一官方",
    faviconPath: "/vendor/twsaimahui/static/image/favicon.ico",
  },
  {
    siteKey: "twcaibawang",
    routePath: "/twcaibawang",
    vendorIndexPath: "/vendor/twcaibawang.com/index.html",
    domains: ["www.twcaibawang.com", "twcaibawang.com"],
    legacyPublicBasePath: "/vendor/twcaibawang.com",
    defaultGame: "hongkong",
    defaultWebId: 5,
    defaultLotteryTypeId: 3,
    forumTitle: "香港天天彩",
    metadataTitle: "台湾彩霸王：聚合全网高手",
    metadataDescription: "台湾彩霸王：聚合全网高手",
    faviconPath: "/vendor/twcaibawang.com/static/image/favicon.ico",
    pageCssPaths: [
      "/vendor/twcaibawang.com/static/css/main.css",
      "/vendor/twcaibawang.com/static/css/custom.css",
      "/vendor/twcaibawang.com/static/css/style.css",
      "/vendor/twcaibawang.com/static/css/nystyle.css",
    ],
  },
  {
    siteKey: "twjinniu",
    routePath: "/twjinniu",
    vendorIndexPath: "/vendor/twjinniu/index.html",
    domains: ["www.twjinniu.com", "twjinniu.com"],
    legacyPublicBasePath: "/vendor/twjinniu",
    defaultGame: "taiwan",
    defaultWebId: 7,
    defaultLotteryTypeId: 3,
    forumTitle: "台湾金牛论坛",
    metadataTitle: "台湾金牛论坛",
    metadataDescription: "台湾金牛论坛",
    pageCssPaths: [
      "/vendor/twjinniu/static/css/main.css",
      "/vendor/twjinniu/static/css/custom.css",
    ],
  },
]

export function getAllSiteConfigs() {
  return SITE_CONFIGS
}

export function getSiteConfig(siteKey: string) {
  return SITE_CONFIGS.find((site) => site.siteKey === siteKey) || null
}

export function buildSiteMetadata(siteKey: string, fallback?: Metadata): Metadata {
  const site = getSiteConfig(siteKey)
  if (!site) {
    return fallback || {}
  }

  return {
    ...fallback,
    title: site.metadataTitle || fallback?.title,
    description: site.metadataDescription || fallback?.description,
    icons: site.faviconPath
      ? {
          ...(fallback?.icons && typeof fallback.icons === "object" ? fallback.icons : {}),
          icon: site.faviconPath,
        }
      : fallback?.icons,
  }
}

export function normalizeHost(host: string | null | undefined) {
  if (!host) return ""
  return host.trim().toLowerCase().replace(/:\d+$/, "")
}

export function findSiteByHost(host: string | null | undefined) {
  const normalized = normalizeHost(host)
  if (!normalized) return null

  return (
    SITE_CONFIGS.find((site) =>
      site.domains.some((domain) => normalizeHost(domain) === normalized)
    ) || null
  )
}

export function safeParseUrl(value: string | null | undefined) {
  if (!value) return null
  try {
    return new URL(value)
  } catch {
    return null
  }
}

export function matchSiteRequest(
  request: Request,
  siteKey: string
): SiteRequestMatch | null {
  const site = getSiteConfig(siteKey)
  if (!site) return null

  const host = normalizeHost(request.headers.get("host"))
  const refererUrl = safeParseUrl(request.headers.get("referer"))
  const refererHost = normalizeHost(refererUrl?.host)
  const refererPath = refererUrl?.pathname || ""
  const matchedByHost = findSiteByHost(host)?.siteKey === siteKey
  const matchedByRefererHost = findSiteByHost(refererHost)?.siteKey === siteKey
  const matchedByPath =
    refererPath === site.legacyPublicBasePath ||
    refererPath.startsWith(`${site.legacyPublicBasePath}/`) ||
    refererPath.startsWith(site.routePath)

  if (!matchedByHost && !matchedByRefererHost && !matchedByPath) {
    return null
  }

  return {
    site,
    refererPath,
    refererUrl,
    matchedByHost,
    matchedByRefererHost,
  }
}

export function buildLegacyEmbedUrl(
  site: FrontendSiteConfig,
  options: {
    lotteryTypeId?: number
    webId?: number
    debug?: boolean
    pageSwitchEnabled?: boolean
    shellHeaderHidden?: boolean
  } = {}
) {
  if (!site.embedPath) {
    return site.vendorIndexPath
  }

  const params = new URLSearchParams({
    type: String(options.lotteryTypeId ?? site.defaultLotteryTypeId),
    web: String(options.webId ?? site.defaultWebId),
    debug: options.debug ? "1" : "0",
    page_switch: options.pageSwitchEnabled ? "1" : "0",
    shell_header: options.shellHeaderHidden ? "1" : "0",
  })

  return `${site.embedPath}?${params.toString()}`
}
