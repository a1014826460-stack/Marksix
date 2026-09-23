import { TwcaibawangHomeClient } from "@/components/twcaibawang/TwcaibawangHomeClient"
import { SiteTrafficTracker } from "@/components/SiteTrafficTracker"
import { getPublicSitePageData, getVendorHomepageModules } from "@/lib/backend-api"
import { buildPredictionModulesForSite } from "@/lib/prediction-adapters"
import { getSiteConfig } from "@/lib/sites"
import { SiteDataReadySignal } from "@/components/site-platform/SiteDataReadySignal"
import Script from "next/script"

export default async function TwcaibawangPage() {
  const site = getSiteConfig("twcaibawang")
  const siteId = site?.defaultWebId || 5
  const cssPaths = site?.pageCssPaths || [
    "/vendor/twcaibawang.com/static/css/main.css",
    "/vendor/twcaibawang.com/static/css/custom.css",
    "/vendor/twcaibawang.com/static/css/style.css",
    "/vendor/twcaibawang.com/static/css/nystyle.css",
  ]
  // 站点页面聚合与首页模块聚合互不依赖：并发发起，别再串行等两次后端聚合
  // （两次聚合各自包含多模块查询，串行会把首屏 HTML 推迟一个完整往返）。
  // 常规情况下数据库里的站点彩种与清单默认彩种一致，直接复用并发结果；
  // 只有不一致时才补一次请求，保持原有语义。
  const defaultLotteryTypeId = site?.defaultLotteryTypeId || 3
  const homepageModuleKeys = [
    "wuxiao_wuma",
    "public_yixiao_yima",
    "shuangbo_12ma",
    "shujinguang",
    "daxiao_2tou",
    "tiandi_2xiao",
  ]
  const [siteData, homepageModulesForDefaultType] = await Promise.all([
    getPublicSitePageData({
      siteId,
      historyLimit: 8,
    }),
    getVendorHomepageModules({
      siteId,
      lotteryType: defaultLotteryTypeId,
      historyLimit: 8,
      modules: homepageModuleKeys,
    }),
  ])
  const homepageModules =
    siteData.site.lottery_type_id === defaultLotteryTypeId
      ? homepageModulesForDefaultType
      : await getVendorHomepageModules({
          siteId,
          lotteryType: siteData.site.lottery_type_id,
          historyLimit: 8,
          modules: homepageModuleKeys,
        })
  const adapted = buildPredictionModulesForSite(siteData, homepageModules)

  return (
    <>
      <SiteTrafficTracker siteKey="twcaibawang" eventType="site_page_view" path="/twcaibawang" />
      <Script src="/vendor/_shared/lottery-site-data-client.js" strategy="beforeInteractive" />
      <Script src="/vendor/twcaibawang.com/site-data-adapter.js" strategy="beforeInteractive" />
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
