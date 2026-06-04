import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { getPublicSitePageData, getVendorHomepageModules } from "@/lib/backend-api"
import {
  adaptPublicSitePageDataWithCanonicalModules,
  adaptVendorHomepageModulesWithCanonicalModules,
} from "@/lib/prediction-adapters"
import { buildCanonicalPredictionModules } from "@/lib/prediction-contract"
import { getSiteConfig } from "@/lib/sites"

export const runtime = "nodejs"

const DEFAULT_VENDOR_MODULES = [
  "wuxiao_wuma",
  "public_yixiao_yima",
  "shuangbo_12ma",
  "shujinguang",
  "daxiao_2tou",
  "tiandi_2xiao",
]

function parsePositiveInt(value: string | null, fallback?: number) {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
}

function parseModules(value: string | null) {
  return (value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const siteKey = searchParams.get("site_key") || searchParams.get("siteKey") || undefined
    const site = siteKey ? getSiteConfig(siteKey) : null
    const siteId = parsePositiveInt(searchParams.get("site_id"), site?.defaultWebId)

    if (!siteId) {
      return jsonWithCors(
        { ok: false, error: "site_id or a registered site_key is required" },
        { status: 400 }
      )
    }

    const historyLimit = parsePositiveInt(searchParams.get("history_limit"), 8) || 8
    const lotteryType = parsePositiveInt(searchParams.get("lottery_type"), site?.defaultLotteryTypeId)
    const vendorModules = parseModules(searchParams.get("vendor_modules") || searchParams.get("modules"))
    const includeVendor = searchParams.get("include_vendor") !== "0"

    const sitePageData = await getPublicSitePageData({
      siteId,
      historyLimit,
      lotteryType,
    })
    const homepageModules = includeVendor
      ? await getVendorHomepageModules({
          siteId,
          lotteryType: lotteryType || sitePageData.site.lottery_type_id,
          historyLimit,
          modules: vendorModules.length ? vendorModules : DEFAULT_VENDOR_MODULES,
        })
      : null
    const canonicalModules = buildCanonicalPredictionModules({
      sitePageData,
      vendorHomepageModules: homepageModules,
    })

    return jsonWithCors({
      ok: true,
      site: {
        site_id: sitePageData.site.id,
        site_key: site?.siteKey || siteKey || null,
        lottery_type: sitePageData.site.lottery_type_id,
        domain: sitePageData.site.domain,
      },
      data: canonicalModules,
      compatibility: {
        site_page: adaptPublicSitePageDataWithCanonicalModules(sitePageData, canonicalModules),
        vendor_homepage_modules: homepageModules
          ? adaptVendorHomepageModulesWithCanonicalModules(homepageModules, canonicalModules)
          : null,
      },
    })
  } catch (error) {
    return jsonWithCors(
      { ok: false, error: error instanceof Error ? error.message : "Request failed" },
      { status: 500 }
    )
  }
}

export function OPTIONS() {
  return buildOptionsResponse()
}

