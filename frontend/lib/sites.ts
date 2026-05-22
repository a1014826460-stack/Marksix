import type { LotteryGame } from "@/lib/lotteryData"

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
  headerImagePath?: `/${string}`
  embedPath?: `/${string}`
  shellCssPaths?: readonly `/${string}`[]
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
  },
]

export function getAllSiteConfigs() {
  return SITE_CONFIGS
}

export function getSiteConfig(siteKey: string) {
  return SITE_CONFIGS.find((site) => site.siteKey === siteKey) || null
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
