import "server-only"

import { backendFetchJson, getPublicSitePageData, getVendorHomepageModules } from "@/lib/backend-api"
import {
  adaptPublicSitePageDataWithCanonicalModules,
  adaptVendorHomepageModulesWithCanonicalModules,
} from "@/lib/prediction-adapters"
import { buildCanonicalPredictionModules } from "@/lib/prediction-contract"
import type { PublicSitePageData } from "@/lib/site-page"
import {
  buildSiteEnvelope,
  type SiteApiContext,
} from "@/lib/site-registry"
import { getTwcf888ArticleCatalog } from "@/lib/twcf888-articles"
import { getTwcf888HomepageModules } from "@/lib/twcf888-homepage"
import { getTwjinniuHomepageModules } from "@/lib/twjinniu-homepage"

const DEFAULT_VENDOR_MODULES = [
  "wuxiao_wuma",
  "public_yixiao_yima",
  "shuangbo_12ma",
  "shujinguang",
  "daxiao_2tou",
  "tiandi_2xiao",
]

export type SiteTrafficEventType =
  | "site_page_view"
  | "article_view"
  | "vendor_page_view"
  | "api_compat_hit"

export type SiteTrafficEventInput = {
  event_type: SiteTrafficEventType
  visitor_id?: string
  path?: string
  route?: string
  article_id?: string
  referrer?: string
  occurred_at?: string
  utm_source?: string
  utm_medium?: string
  utm_campaign?: string
}

function parseModules(value: string | null) {
  return (value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
}

export async function getSitePage(context: SiteApiContext) {
  const sitePage = await getPublicSitePageData({
    siteId: context.siteId,
    historyLimit: context.historyLimit,
    lotteryType: context.lotteryType,
  })
  return buildSiteEnvelope(context, { site_page: sitePage })
}

export async function getSiteHomepageModules(context: SiteApiContext) {
  if (context.siteKey === "twjinniu") {
    return buildSiteEnvelope(context, await getTwjinniuHomepageModules(context.lotteryType))
  }
  if (context.siteKey === "twcf888") {
    return buildSiteEnvelope(context, await getTwcf888HomepageModules(context.lotteryType))
  }

  const modules = parseModules(
    context.searchParams.get("vendor_modules") || context.searchParams.get("modules")
  )
  const data = await getVendorHomepageModules({
    siteId: context.siteId,
    lotteryType: context.lotteryType,
    historyLimit: context.historyLimit,
    modules: modules.length ? modules : DEFAULT_VENDOR_MODULES,
  })
  return buildSiteEnvelope(context, data)
}

export async function getSitePredictionModules(context: SiteApiContext) {
  const vendorModules = parseModules(
    context.searchParams.get("vendor_modules") || context.searchParams.get("modules")
  )
  const historyWebStart = context.siteKey === "twssz" ? 1 : context.webId
  const historyWebEnd = context.siteKey === "twssz" ? 1000 : context.webId
  const [sitePageData, homepageModules] = await Promise.all([
    getPublicSitePageData({
      siteId: context.siteId,
      historyLimit: context.historyLimit,
      lotteryType: context.lotteryType,
      historyWebStart,
      historyWebEnd,
    }),
    context.searchParams.get("include_vendor") === "0"
      ? Promise.resolve(null)
      : getVendorHomepageModules({
          siteId: context.siteId,
          lotteryType: context.lotteryType,
          historyLimit: context.historyLimit,
          modules: vendorModules.length ? vendorModules : DEFAULT_VENDOR_MODULES,
        }),
  ])
  const canonicalModules = buildCanonicalPredictionModules({
    sitePageData,
    vendorHomepageModules: homepageModules,
  })

  return buildSiteEnvelope(context, {
    canonical_modules: canonicalModules,
    compatibility: {
      site_page: adaptPublicSitePageDataWithCanonicalModules(sitePageData, canonicalModules),
      vendor_homepage_modules: homepageModules
        ? adaptVendorHomepageModulesWithCanonicalModules(homepageModules, canonicalModules)
        : null,
    },
  })
}

async function resolveArticleLib(siteKey: string) {
  if (siteKey === "twcf888") {
    const mod = await import("@/lib/twcf888-articles")
    return {
      getArticleDetail: (id: string, opts: { lotteryType: number; group?: string }) =>
        mod.getTwcf888ArticleDetail(id, opts),
      getSiteRequestDefaults: (lotteryType: number) =>
        mod.getTwcf888SiteRequestDefaults(lotteryType),
    }
  }

  const mod = await import("@/lib/twjinniu-articles")
  return {
    getArticleDetail: (id: string, opts: { lotteryType: number }) =>
      mod.getTwjinniuArticleDetail(id, opts),
    getSiteRequestDefaults: (lotteryType: number) =>
      mod.getTwjinniuSiteRequestDefaults(lotteryType),
  }
}

export async function getSiteArticleDetail(context: SiteApiContext, articleId: string) {
  if (!context.site.capabilities.articleDetail) {
    throw new Error(`Article detail is not enabled for ${context.siteKey}`)
  }

  const lib = await resolveArticleLib(context.siteKey)
  const article = await lib.getArticleDetail(articleId, {
    lotteryType: context.lotteryType,
    group: context.searchParams.get("group") || undefined,
  })
  if (!article) {
    throw new Error("article not found")
  }

  return {
    ok: true as const,
    site: lib.getSiteRequestDefaults(context.lotteryType),
    article,
  }
}

export async function getTwcf888SitePagePayload(context: SiteApiContext) {
  const sitePage = await backendFetchJson<PublicSitePageData>("/public/site-page", {
    query: {
      site_id: context.siteId,
      history_limit: context.historyLimit,
      lottery_type: context.lotteryType,
      mode_ids: context.modeIds?.join(","),
    },
  })
  const liveModeMap = new Map(
    sitePage.modules.map((module) => [Number(module.default_modes_id), module.history.length])
  )
  const articleCatalog = getTwcf888ArticleCatalog()

  return buildSiteEnvelope(context, {
    site_page: sitePage,
    required_mode_ids: [
      2, 5, 12, 14, 15, 20, 26, 27, 28, 38, 41, 42, 43, 45, 47, 49, 50, 51, 53, 54,
      57, 66, 69, 74, 88, 95, 98, 100, 103, 122, 132, 143, 180, 197, 198, 224,
      226, 279, 470, 472, 473, 482, 483,
    ],
    blocked_items: articleCatalog
      .filter((item) => item.moduleStatus === "blocked_requires_backend_work")
      .map((item) => item.title),
    snapshot_only_items: articleCatalog
      .filter((item) => item.moduleStatus === "snapshot_only")
      .map((item) => item.title),
    live_backed_articles: articleCatalog
      .filter((item) => item.moduleStatus === "live_backed" && item.modeId !== null)
      .map((item) => ({
        article_id: item.id,
        title: item.title,
        group: item.group,
        mode_id: item.modeId,
        has_live_rows: (item.modeId !== null ? liveModeMap.get(item.modeId) || 0 : 0) > 0,
      })),
  })
}

export async function recordSiteTrafficEvent(
  context: SiteApiContext,
  event: SiteTrafficEventInput
) {
  if (!context.site.capabilities.trafficEvents) {
    return { ok: false as const, error: "traffic events disabled" }
  }

  return backendFetchJson("/public/traffic-events", {
    method: "POST",
    body: {
      site_key: context.siteKey,
      site_id: context.siteId,
      web_id: context.webId,
      lottery_type: context.lotteryType,
      ...event,
    },
  })
}

export async function recordSiteApiCompatHit(
  context: SiteApiContext,
  path: string,
  extra: Partial<SiteTrafficEventInput> = {}
) {
  try {
    return await recordSiteTrafficEvent(context, {
      event_type: "api_compat_hit",
      path,
      route: path,
      ...extra,
    })
  } catch {
    return null
  }
}
