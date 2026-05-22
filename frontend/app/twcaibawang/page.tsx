import { TwcaibawangHomeClient } from "@/components/twcaibawang/TwcaibawangHomeClient"
import { getPublicSitePageData, getVendorHomepageModules } from "@/lib/backend-api"
import { getSiteConfig } from "@/lib/sites"

export default async function TwcaibawangPage() {
  const site = getSiteConfig("twcaibawang")
  const siteId = site?.defaultWebId || 5
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

  return (
    <>
      <link rel="stylesheet" href="/vendor/twcaibawang.com/static/css/main.css" />
      <link rel="stylesheet" href="/vendor/twcaibawang.com/static/css/custom.css" />
      <link rel="stylesheet" href="/vendor/twcaibawang.com/static/css/style.css" />
      <link rel="stylesheet" href="/vendor/twcaibawang.com/static/css/nystyle.css" />
      <TwcaibawangHomeClient
        siteData={siteData}
        homepageModules={homepageModules}
        defaultLotteryTypeId={(siteData.site.lottery_type_id as 1 | 2 | 3) || site?.defaultLotteryTypeId || 3}
      />
    </>
  )
}
