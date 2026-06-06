import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { matchSiteRequest } from "@/lib/sites"

export const runtime = "nodejs"

async function resolveArticleLib(siteKey: string) {
  if (siteKey === "twcf888") {
    const mod = await import("@/lib/twcf888-articles")
    return {
      getArticleDetail: (id: string, opts: { lotteryType: number }) =>
        mod.getTwcf888ArticleDetail(id, opts),
      getSiteRequestDefaults: (lt: number) => mod.getTwcf888SiteRequestDefaults(lt),
    }
  }
  // Default: twjinniu (also handles twcaibawang via twjinniu article library)
  const mod = await import("@/lib/twjinniu-articles")
  return {
    getArticleDetail: (id: string, opts: { lotteryType: number }) =>
      mod.getTwjinniuArticleDetail(id, opts),
    getSiteRequestDefaults: (lt: number) => mod.getTwjinniuSiteRequestDefaults(lt),
  }
}

export async function GET(request: Request) {
  try {
    // Resolve site context via host/referer matching
    const match =
      matchSiteRequest(request, "twcaibawang") ||
      matchSiteRequest(request, "twjinniu") ||
      matchSiteRequest(request, "twcf888")
    if (!match) {
      return jsonWithCors({ ok: false, error: "Site not recognized" }, { status: 404 })
    }

    const { searchParams } = new URL(request.url)
    const articleId =
      searchParams.get("article_id") ||
      searchParams.get("articleId") ||
      searchParams.get("id") ||
      ""
    const lotteryType = Number(searchParams.get("lottery_type") || searchParams.get("lotteryType") || String(match.site.defaultLotteryTypeId)) || match.site.defaultLotteryTypeId

    if (!articleId) {
      return jsonWithCors({ ok: false, error: "article_id is required" }, { status: 400 })
    }

    const lib = await resolveArticleLib(match.site.siteKey)
    const article = await lib.getArticleDetail(articleId, { lotteryType })
    if (!article) {
      return jsonWithCors({ ok: false, error: "article not found" }, { status: 404 })
    }

    return jsonWithCors({
      ok: true,
      site: lib.getSiteRequestDefaults(lotteryType),
      article,
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
