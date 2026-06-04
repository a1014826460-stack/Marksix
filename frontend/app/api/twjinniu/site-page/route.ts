import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { getPublicSitePageData } from "@/lib/backend-api"
import { adaptPublicSitePageDataWithCanonicalModules } from "@/lib/prediction-adapters"
import { buildCanonicalPredictionModules } from "@/lib/prediction-contract"
import { getSiteConfig } from "@/lib/sites"

export const runtime = "nodejs"

const TWJINNIU_LIVE_HOMEPAGE_SECTIONS = ["本站出品精华版", "精华版文章详情页"]
const TWJINNIU_CONFIRMED_POSTGRESQL_HOMEPAGE_SECTIONS = [
  "公式平特肖",
  "一肖一码大公开",
  "四肖八码",
  "单双四肖八码",
  "平特一肖",
  "平特一尾",
  "一句话中特码",
  "合数大小",
  "八肖十六码",
]
const TWJINNIU_UNCONFIRMED_HOMEPAGE_SECTIONS: string[] = []

function parsePositiveInt(value: string | null, fallback: number) {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
}

export async function GET(request: Request) {
  try {
    const site = getSiteConfig("twjinniu")
    if (!site) {
      return jsonWithCors({ ok: false, error: "twjinniu site config is missing" }, { status: 500 })
    }

    const { searchParams } = new URL(request.url)
    const historyLimit = parsePositiveInt(searchParams.get("history_limit"), 8)
    const webId = parsePositiveInt(searchParams.get("web_id") || searchParams.get("web"), site.defaultWebId)
    const siteId = parsePositiveInt(searchParams.get("site_id"), webId)
    const lotteryType = parsePositiveInt(searchParams.get("lottery_type"), site.defaultLotteryTypeId)
    const siteData = await getPublicSitePageData({
      siteId,
      lotteryType,
      historyLimit,
    })
    const canonicalModules = buildCanonicalPredictionModules({ sitePageData: siteData })
    const missingModules = siteData.modules
      .filter((module) => !module.history?.length)
      .map((module) => ({
        mechanism_key: module.mechanism_key,
        mode_id: module.default_modes_id,
        title: module.title,
      }))

    return jsonWithCors({
      ok: true,
      site: {
        site_key: site.siteKey,
        site_id: site.defaultWebId,
        web_id: site.defaultWebId,
        requested_site_key: searchParams.get("site_key") || searchParams.get("siteKey") || site.siteKey,
        requested_site_id: siteId,
        requested_web_id: webId,
        lottery_type: lotteryType,
        domain: site.domains[0],
      },
      data: {
        site_page: adaptPublicSitePageDataWithCanonicalModules(siteData, canonicalModules),
        canonical_modules: canonicalModules,
        missing_modules: missingModules,
        homepage_source_status: {
          data_source: "local-postgresql",
          source_chain: [
            "frontend /api/twjinniu/site-page",
            "backend /api/public/site-page",
            "PostgreSQL",
          ],
          live_sections: TWJINNIU_LIVE_HOMEPAGE_SECTIONS,
          confirmed_postgresql_sections: TWJINNIU_CONFIRMED_POSTGRESQL_HOMEPAGE_SECTIONS,
          unresolved_sections: TWJINNIU_UNCONFIRMED_HOMEPAGE_SECTIONS,
          snapshot_only_sections: [],
          live_article_module_count: siteData.modules.length,
          missing_article_module_count: missingModules.length,
        },
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
