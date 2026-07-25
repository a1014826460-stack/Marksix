import { TwcaibawangHomeClient } from "@/components/twcaibawang/TwcaibawangHomeClient"
import { SiteTrafficTracker } from "@/components/SiteTrafficTracker"
import { getPublicSitePageData, getVendorHomepageModules } from "@/lib/backend-api"
import { buildPredictionModulesForSite } from "@/lib/prediction-adapters"
import { getSiteConfig } from "@/lib/sites"
import { SiteDataReadySignal } from "@/components/site-platform/SiteDataReadySignal"

export default async function TwcaibawangPage() {
  const site = getSiteConfig("twcaibawang")
  const siteId = site?.defaultWebId || 5
  const cssPaths = site?.pageCssPaths || [
    "/vendor/twcaibawang.com/static/css/main.css",
    "/vendor/twcaibawang.com/static/css/custom.css",
    "/vendor/twcaibawang.com/static/css/style.css",
    "/vendor/twcaibawang.com/static/css/nystyle.css",
  ]
  const siteData = await getPublicSitePageData({
    siteId,
    historyLimit: 8,
  })
  const homepageModules = await getVendorHomepageModules({
    siteId,
    lotteryType: siteData.site.lottery_type_id,
    historyLimit: 8,
    modules: [
      "wuxiao_wuma",
      "public_yixiao_yima",
      "shuangbo_12ma",
      "shujinguang",
      "daxiao_2tou",
      "tiandi_2xiao",
    ],
  })
  const adapted = buildPredictionModulesForSite(siteData, homepageModules)

  return (
    <>
      <SiteTrafficTracker siteKey="twcaibawang" eventType="site_page_view" path="/twcaibawang" />
      <SiteDataReadySignal siteKey="twcaibawang" />
      {cssPaths.map((href) => (
        <link key={href} rel="stylesheet" href={href} />
      ))}
      <TwcaibawangHomeClient
        siteData={adapted.siteData}
        homepageModules={adapted.homepageModules}
        defaultLotteryTypeId={(adapted.siteData.site.lottery_type_id as 1 | 2 | 3) || site?.defaultLotteryTypeId || 3}
      />
    </>
  )
}
