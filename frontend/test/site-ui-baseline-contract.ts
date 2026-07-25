import { SITE_UI_BASELINES } from "@/lib/site-platform/site-ui-baseline"

const expectedSiteKeys = [
  "shengshi8800",
  "twsaimahui",
  "twcaibawang",
  "twjinniu",
  "twcf888",
  "twssz",
] as const

for (const siteKey of expectedSiteKeys) {
  const baseline = SITE_UI_BASELINES[siteKey]
  if (!baseline?.routePath || !baseline.vendorEntry) {
    throw new Error(`missing route baseline: ${siteKey}`)
  }
  if (!baseline.drawSentinel || !baseline.navigationSentinel || !baseline.footerSentinel) {
    throw new Error(`missing visual sentinels: ${siteKey}`)
  }
}
