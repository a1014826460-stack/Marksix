import { TwcaibawangHomeClient } from "@/components/twcaibawang/TwcaibawangHomeClient"
import { getPublicSitePageData, getVendorHomepageModules } from "@/lib/backend-api"
import { getSiteConfig } from "@/lib/sites"

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

  return (
    <>
      {cssPaths.map((href) => (
        <link key={href} rel="stylesheet" href={href} />
      ))}
      <TwcaibawangHomeClient
        siteData={siteData}
        homepageModules={homepageModules}
        defaultLotteryTypeId={(siteData.site.lottery_type_id as 1 | 2 | 3) || site?.defaultLotteryTypeId || 3}
      />
    </>
  )
}
