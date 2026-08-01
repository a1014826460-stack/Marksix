import type { LotteryGame } from "@/lib/lotteryData"
import type { Metadata } from "next"
import type { VendorSiteManifest } from "@/lib/site-platform/site-manifest"
import shengshi8800Manifest from "@/sites/shengshi8800/site.manifest"
import twsaimahuiManifest from "@/sites/twsaimahui/site.manifest"
import twcaibawangManifest from "@/sites/twcaibawang/site.manifest"
import twjinniuManifest from "@/sites/twjinniu/site.manifest"
import twcf888Manifest from "@/sites/twcf888/site.manifest"
import twsszManifest from "@/sites/twssz/site.manifest"
import twbst528Manifest from "@/sites/twbst528/site.manifest"
import twjsz666Manifest from "@/sites/twjsz666/site.manifest"
import twwanliManifest from "@/sites/twwanli/site.manifest"
import twsywManifest from "@/sites/twsyw/site.manifest"

export type FrontendSiteConfig = {
  siteKey: string
  renderMode: "legacy-shell" | "iframe-vendor" | "react-home"
  capabilities: {
    sitePage: boolean
    homepageModules: boolean
    articleDetail: boolean
    predictionModules: boolean
    trafficEvents: boolean
  }
  routePath: `/${string}` | "/"
  vendorIndexPath: `/${string}`
  domains: string[]
  legacyPublicBasePath: `/${string}`
  defaultGame: LotteryGame
  defaultSiteId: number
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

export function toFrontendSiteConfig(manifest: VendorSiteManifest): FrontendSiteConfig {
  return {
    siteKey: manifest.identity.siteKey,
    renderMode:
      manifest.frontend.renderMode === "legacy-dom"
        ? "legacy-shell"
        : manifest.frontend.renderMode === "react-template"
          ? "react-home"
          : "iframe-vendor",
    capabilities: {
      sitePage: true,
      homepageModules: true,
      articleDetail: false,
      predictionModules: true,
      trafficEvents: true,
    },
    routePath: manifest.identity.routePath,
    vendorIndexPath: manifest.frontend.vendorIndexPath,
    domains: [...manifest.identity.domains],
    legacyPublicBasePath: manifest.frontend.legacyPublicBasePath,
    defaultGame: manifest.frontend.defaultGame,
    defaultSiteId: manifest.identity.siteId,
    defaultWebId: manifest.identity.webId,
    defaultLotteryTypeId: manifest.identity.defaultLotteryType,
    forumTitle: manifest.frontend.forumTitle,
    metadataTitle: manifest.frontend.metadataTitle,
    metadataDescription: manifest.frontend.metadataDescription,
    faviconPath: manifest.frontend.faviconPath,
  }
}

const SITE_CONFIGS: FrontendSiteConfig[] = [
  {
    ...toFrontendSiteConfig(shengshi8800Manifest),
    routePath: "/",
    vendorIndexPath: "/vendor/shengshi8800/embed.html?type=3&web=4",
    renderMode: "legacy-shell",
    capabilities: {
      sitePage: true,
      homepageModules: true,
      articleDetail: false,
      predictionModules: true,
      trafficEvents: true,
    },
    headerImagePath: "/vendor/shengshi8800/static/picture/header.jpg",
    embedPath: "/vendor/shengshi8800/embed.html",
    shellCssPaths: [
      "/vendor/shengshi8800/static/css/style1.css",
      "/vendor/shengshi8800/static/css/style3.css",
    ],
  },
  toFrontendSiteConfig(twsaimahuiManifest),
  {
    ...toFrontendSiteConfig(twcaibawangManifest),
    capabilities: {
      sitePage: true,
      homepageModules: true,
      articleDetail: true,
      predictionModules: true,
      trafficEvents: true,
    },
    pageCssPaths: [
      "/vendor/twcaibawang.com/static/css/main.css",
      "/vendor/twcaibawang.com/static/css/custom.css",
      "/vendor/twcaibawang.com/static/css/style.css",
      "/vendor/twcaibawang.com/static/css/nystyle.css",
    ],
  },
  {
    ...toFrontendSiteConfig(twjinniuManifest),
    capabilities: {
      sitePage: true,
      homepageModules: true,
      articleDetail: true,
      predictionModules: true,
      trafficEvents: true,
    },
    pageCssPaths: [
      "/vendor/twjinniu/static/css/main.css",
      "/vendor/twjinniu/static/css/custom.css",
    ],
  },
  {
    ...toFrontendSiteConfig(twcf888Manifest),
    capabilities: {
      sitePage: true,
      homepageModules: true,
      articleDetail: true,
      predictionModules: true,
      trafficEvents: true,
    },
    pageCssPaths: [
      "/vendor/twcf888.com/static/css/main.css",
      "/vendor/twcf888.com/static/css/custom.css",
      "/vendor/twcf888.com/static/css/style.css",
    ],
  },
  toFrontendSiteConfig(twbst528Manifest),
  toFrontendSiteConfig(twjsz666Manifest),
  toFrontendSiteConfig(twsszManifest),
  toFrontendSiteConfig(twwanliManifest),
  toFrontendSiteConfig(twsywManifest),
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

export function findSiteByPathname(pathname: string | null | undefined) {
  const normalized = String(pathname || "").trim()
  if (!normalized.startsWith("/")) {
    return null
  }

  return (
    SITE_CONFIGS.find((site) => {
      const routeMatch =
        site.routePath !== "/" &&
        (normalized === site.routePath || normalized.startsWith(`${site.routePath}/`))
      const legacyMatch =
        normalized === site.legacyPublicBasePath ||
        normalized.startsWith(`${site.legacyPublicBasePath}/`)
      const vendorPath = site.vendorIndexPath.split("?", 1)[0]
      const vendorMatch = normalized === vendorPath || normalized.startsWith(`${vendorPath}/`)
      return routeMatch || legacyMatch || vendorMatch
    }) || null
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
