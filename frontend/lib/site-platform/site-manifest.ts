import type { LotteryGame } from "@/lib/lotteryData"

export type VendorRenderMode = "iframe-vendor" | "legacy-dom" | "react-template"

export type VendorSiteManifestInput = {
  identity: {
    siteKey: string
    domains: string[]
    routePath: `/${string}` | "/"
    siteId: number
    webId: number
    defaultLotteryType: 1 | 2 | 3
  }
  frontend: {
    renderMode: VendorRenderMode
    vendorIndexPath: `/${string}`
    legacyPublicBasePath: `/${string}`
    defaultGame: LotteryGame
    forumTitle: string
    metadataTitle?: string
    metadataDescription?: string
    faviconPath?: `/${string}`
  }
  bridge: {
    api: {
      httpApiBase: string
      kaijiangApiBase: string
    }
    autoLoad: {
      draw: boolean
      prediction: boolean
    }
    predictionModuleKeys: string[]
  }
  brand: {
    siteName: string
    logoUrl?: `/${string}`
    faviconUrl?: `/${string}`
    theme?: {
      primary?: string
      accent?: string
      background?: string
    }
    navigation: Array<{ label: string; href: string }>
    footer: {
      copyright: string
      icpImageUrl?: `/${string}`
      contacts?: Array<{ label: string; href: string }>
    }
  }
  security: {
    externalScriptOrigins: string[]
    externalNavigationOrigins: string[]
  }
}

export type VendorSiteManifest = {
  readonly identity: Readonly<{
    siteKey: string
    domains: readonly string[]
    routePath: `/${string}` | "/"
    siteId: number
    webId: number
    defaultLotteryType: 1 | 2 | 3
  }>
  readonly frontend: Readonly<VendorSiteManifestInput["frontend"]>
  readonly bridge: Readonly<{
    api: Readonly<VendorSiteManifestInput["bridge"]["api"]>
    autoLoad: Readonly<VendorSiteManifestInput["bridge"]["autoLoad"]>
    predictionModuleKeys: readonly string[]
  }>
  readonly brand: Readonly<{
    siteName: string
    logoUrl?: `/${string}`
    faviconUrl?: `/${string}`
    theme?: Readonly<NonNullable<VendorSiteManifestInput["brand"]["theme"]>>
    navigation: readonly Readonly<{ label: string; href: string }>[]
    footer: Readonly<{
      copyright: string
      icpImageUrl?: `/${string}`
      contacts: readonly Readonly<{ label: string; href: string }>[]
    }>
  }>
  readonly security: Readonly<{
    externalScriptOrigins: readonly string[]
    externalNavigationOrigins: readonly string[]
  }>
}

const SITE_KEY_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

function assertPositiveInteger(value: number, field: string) {
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`${field} must be a positive integer`)
  }
}

function assertPath(value: string, field: string) {
  if (!value.startsWith("/")) {
    throw new Error(`${field} must start with /`)
  }
}

function assertOrigins(origins: string[], field: string) {
  for (const origin of origins) {
    try {
      const parsed = new URL(origin)
      if (parsed.origin !== origin || !["http:", "https:"].includes(parsed.protocol)) {
        throw new Error("invalid origin")
      }
    } catch {
      throw new Error(`${field} must contain absolute http(s) origins`)
    }
  }
}

export function defineVendorSiteManifest(input: VendorSiteManifestInput): VendorSiteManifest {
  const { identity, frontend, bridge, brand, security } = input
  if (!SITE_KEY_PATTERN.test(identity.siteKey)) {
    throw new Error("identity.siteKey must be lowercase kebab-case")
  }
  if (!identity.domains.length || identity.domains.some((domain) => !domain.trim())) {
    throw new Error("identity.domains must contain at least one non-empty domain")
  }
  assertPath(identity.routePath, "identity.routePath")
  if (identity.routePath !== `/${identity.siteKey}`) {
    throw new Error("identity.routePath must equal /<siteKey>")
  }
  assertPositiveInteger(identity.siteId, "identity.siteId")
  assertPositiveInteger(identity.webId, "identity.webId")
  assertPath(frontend.vendorIndexPath, "frontend.vendorIndexPath")
  assertPath(frontend.legacyPublicBasePath, "frontend.legacyPublicBasePath")
  if (!frontend.vendorIndexPath.startsWith("/vendor/")) {
    throw new Error("frontend.vendorIndexPath must be under /vendor/")
  }
  if (!frontend.legacyPublicBasePath.startsWith("/vendor/")) {
    throw new Error("frontend.legacyPublicBasePath must be under /vendor/")
  }
  const moduleKeys = bridge.predictionModuleKeys.map((key) => key.trim()).filter(Boolean)
  if (moduleKeys.length !== bridge.predictionModuleKeys.length) {
    throw new Error("bridge.predictionModuleKeys cannot contain empty values")
  }
  if (new Set(moduleKeys).size !== moduleKeys.length) {
    throw new Error("bridge.predictionModuleKeys must be unique")
  }
  assertOrigins(security.externalScriptOrigins, "security.externalScriptOrigins")
  assertOrigins(security.externalNavigationOrigins, "security.externalNavigationOrigins")

  return Object.freeze({
    ...input,
    identity: Object.freeze({ ...identity, domains: Object.freeze([...identity.domains]) }),
    frontend: Object.freeze({ ...frontend }),
    bridge: Object.freeze({
      ...bridge,
      api: Object.freeze({ ...bridge.api }),
      autoLoad: Object.freeze({ ...bridge.autoLoad }),
      predictionModuleKeys: Object.freeze(moduleKeys),
    }),
    brand: Object.freeze({
      ...brand,
      navigation: Object.freeze(brand.navigation.map((item) => Object.freeze({ ...item }))),
      footer: Object.freeze({
        ...brand.footer,
        contacts: Object.freeze((brand.footer.contacts || []).map((item) => Object.freeze({ ...item }))),
      }),
    }),
    security: Object.freeze({
      externalScriptOrigins: Object.freeze([...security.externalScriptOrigins]),
      externalNavigationOrigins: Object.freeze([...security.externalNavigationOrigins]),
    }),
  })
}
