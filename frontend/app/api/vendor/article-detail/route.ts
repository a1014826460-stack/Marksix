import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { getSiteArticleDetail, recordSiteApiCompatHit } from "@/lib/site-api-service"
import { resolveSiteApiContext } from "@/lib/site-registry"
import { matchSiteRequest } from "@/lib/sites"

export const runtime = "nodejs"

export async function GET(request: Request) {
  try {
    const match =
      matchSiteRequest(request, "twcaibawang") ||
      matchSiteRequest(request, "twjinniu") ||
      matchSiteRequest(request, "twcf888")
    if (!match) {
      return jsonWithCors({ ok: false, error: "Site not recognized" }, { status: 404 })
    }

    const { searchParams, pathname } = new URL(request.url)
    const articleId =
      searchParams.get("article_id") ||
      searchParams.get("articleId") ||
      searchParams.get("id") ||
      ""
    if (!articleId) {
      return jsonWithCors({ ok: false, error: "article_id is required" }, { status: 400 })
    }

    const context = resolveSiteApiContext(match.site.siteKey, searchParams)
    void recordSiteApiCompatHit(context, pathname, { article_id: articleId })
    return jsonWithCors(await getSiteArticleDetail(context, articleId))
  } catch (error) {
    const message = error instanceof Error ? error.message : "Request failed"
    return jsonWithCors(
      { ok: false, error: message },
      { status: message.includes("not found") ? 404 : 500 }
    )
  }
}

export function OPTIONS() {
  return buildOptionsResponse()
}
