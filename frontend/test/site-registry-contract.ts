import {
  getAllSiteKeys,
  getRegisteredSite,
  resolveSiteApiContext,
  type RegisteredSiteKey,
} from "@/lib/site-registry"
import {
  getSiteArticleDetail,
  getSiteHomepageModules,
  getSitePage,
  getSitePredictionModules,
  recordSiteTrafficEvent,
  recordSiteApiCompatHit,
} from "@/lib/site-api-service"

const expectedKeys = [
  "shengshi8800",
  "twsaimahui",
  "twcaibawang",
  "twjinniu",
  "twcf888",
] as const satisfies readonly RegisteredSiteKey[]

const keys: readonly RegisteredSiteKey[] = getAllSiteKeys()
for (const siteKey of expectedKeys) {
  if (!keys.includes(siteKey)) {
    throw new Error(`Missing registered site ${siteKey}`)
  }

  const site = getRegisteredSite(siteKey)
  if (!site.capabilities.trafficEvents) {
    throw new Error(`Traffic events must be enabled for ${siteKey}`)
  }
}

const context = resolveSiteApiContext("twjinniu", new URLSearchParams("history_limit=3"))
void getSitePage(context)
void getSiteHomepageModules(context)
void getSitePredictionModules(context)
void getSiteArticleDetail(context, "sample-article")
void recordSiteTrafficEvent(context, {
  event_type: "site_page_view",
  path: "/twjinniu",
  visitor_id: "visitor-1",
})
void recordSiteApiCompatHit(context, "/api/twjinniu/site-page")
