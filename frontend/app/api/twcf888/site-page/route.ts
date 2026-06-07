import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { backendFetchJson } from "@/lib/backend-api"
import type { PublicSitePageData } from "@/lib/site-page"
import { getTwcf888ArticleCatalog } from "@/lib/twcf888-articles"
import { getSiteConfig } from "@/lib/sites"

export const runtime = "nodejs"

const REQUIRED_MODE_IDS = [
  2, 5, 12, 14, 15, 20, 26, 27, 28, 38, 41, 42, 43, 45, 47, 49, 50, 51, 53, 54,
  57, 66, 69, 74, 88, 95, 98, 100, 103, 122, 132, 143, 180, 197, 198, 224, 226,
  279, 470, 472, 473, 482, 483,
]

function parsePositiveInt(value: string | null, fallback: number) {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
}

function parseModeIds(value: string | null) {
  if (!value) return undefined

  const modeIds = value
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isInteger(item) && item > 0)

  return modeIds.length ? modeIds : undefined
}

export async function GET(request: Request) {
  try {
    const site = getSiteConfig("twcf888")
    if (!site) {
      return jsonWithCors({ ok: false, error: "twcf888 site config is missing" }, { status: 500 })
    }

    const { searchParams } = new URL(request.url)
    const historyLimit = parsePositiveInt(searchParams.get("history_limit"), 8)
    const webId = parsePositiveInt(searchParams.get("web_id") || searchParams.get("web"), site.defaultWebId)
    const siteId = parsePositiveInt(searchParams.get("site_id"), webId)
    const lotteryType = parsePositiveInt(searchParams.get("lottery_type"), site.defaultLotteryTypeId)
    const modeIds = parseModeIds(searchParams.get("mode_ids"))

    const sitePage = await backendFetchJson<PublicSitePageData>("/public/site-page", {
      query: {
        site_id: siteId,
        history_limit: historyLimit,
        lottery_type: lotteryType,
        mode_ids: modeIds?.join(","),
      },
    })

    const liveModeMap = new Map(
      sitePage.modules.map((module) => [Number(module.default_modes_id), module.history.length])
    )

    const articleCatalog = getTwcf888ArticleCatalog()
    const liveBackedArticles = articleCatalog.filter(
      (item) => item.moduleStatus === "live_backed" && item.modeId !== null
    )
    const blockedItems = articleCatalog
      .filter((item) => item.moduleStatus === "blocked_requires_backend_work")
      .map((item) => item.title)
    const snapshotOnlyItems = articleCatalog
      .filter((item) => item.moduleStatus === "snapshot_only")
      .map((item) => item.title)

    return jsonWithCors({
      ok: true,
      site: {
        site_key: site.siteKey,
        site_id: site.defaultWebId,
        web_id: site.defaultWebId,
        requested_site_id: siteId,
        requested_web_id: webId,
        lottery_type: lotteryType,
        domain: site.domains[0],
      },
      data: {
        site_page: sitePage,
        required_mode_ids: REQUIRED_MODE_IDS,
        blocked_items: blockedItems,
        snapshot_only_items: snapshotOnlyItems,
        live_backed_articles: liveBackedArticles.map((item) => ({
          article_id: item.id,
          title: item.title,
          group: item.group,
          mode_id: item.modeId,
          has_live_rows: (item.modeId !== null ? liveModeMap.get(item.modeId) || 0 : 0) > 0,
        })),
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
