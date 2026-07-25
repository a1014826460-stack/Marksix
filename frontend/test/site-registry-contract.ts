import {
  getAllSiteKeys,
  getRegisteredSite,
  resolveSiteApiContext,
  resolvePredictionModulesCompatibilityContext,
  type RegisteredSiteKey,
} from "@/lib/site-registry"
import twsaimahuiManifest from "@/sites/twsaimahui/site.manifest"
import twsszManifest from "@/sites/twssz/site.manifest"
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
  "twssz",
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
const twsaimahui = getRegisteredSite("twsaimahui")
if (
  twsaimahui.defaultWebId !== twsaimahuiManifest.identity.webId ||
  twsaimahui.vendorIndexPath !== twsaimahuiManifest.frontend.vendorIndexPath
) {
  throw new Error("twsaimahui registry configuration must be derived from its manifest")
}
if (getRegisteredSite("twssz").defaultWebId !== twsszManifest.identity.webId) {
  throw new Error("twssz registry configuration must be derived from its manifest")
}
const crossSiteOverrideContext = resolveSiteApiContext(
  "twjinniu",
  new URLSearchParams("site_id=5&web=5&web_id=5")
)

if (crossSiteOverrideContext.siteId !== 7 || crossSiteOverrideContext.webId !== 7) {
  throw new Error("A site-private route must ignore cross-site site_id/web query overrides")
}

const compatibilityContext = resolvePredictionModulesCompatibilityContext(
  new URLSearchParams("site_id=5")
)
if (compatibilityContext.siteKey !== "twcaibawang" || compatibilityContext.siteId !== 5) {
  throw new Error("The compatibility prediction route must resolve a registered site_id")
}

let compatibilityConflictRejected = false
try {
  resolvePredictionModulesCompatibilityContext(
    new URLSearchParams("site_key=twjinniu&site_id=5")
  )
} catch {
  compatibilityConflictRejected = true
}
if (!compatibilityConflictRejected) {
  throw new Error("The compatibility prediction route must reject conflicting site identity")
}

let missingCompatibilityIdentityRejected = false
try {
  resolvePredictionModulesCompatibilityContext()
} catch (error) {
  missingCompatibilityIdentityRejected =
    error instanceof Error && error.message === "site_id or a registered site_key is required"
}
if (!missingCompatibilityIdentityRejected) {
  throw new Error("The compatibility prediction route must preserve the missing identity validation error")
}

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
