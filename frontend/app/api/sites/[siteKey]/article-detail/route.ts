import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { getSiteArticleDetail } from "@/lib/site-api-service"
import { resolveSiteApiContext } from "@/lib/site-registry"

export const runtime = "nodejs"

type RouteContext = {
  params: Promise<{ siteKey: string }>
}

export async function GET(request: Request, context: RouteContext) {
  try {
    const { siteKey } = await context.params
    const { searchParams } = new URL(request.url)
    const articleId =
      searchParams.get("article_id") ||
      searchParams.get("articleId") ||
      searchParams.get("id") ||
      ""
    if (!articleId) {
      return jsonWithCors({ ok: false, error: "article_id is required" }, { status: 400 })
    }
    return jsonWithCors(
      await getSiteArticleDetail(resolveSiteApiContext(siteKey, searchParams), articleId)
    )
  } catch (error) {
    const message = error instanceof Error ? error.message : "Request failed"
    return jsonWithCors(
      { ok: false, error: message },
      {
        status: message.includes("Unknown siteKey")
          ? 404
          : message.includes("not found")
            ? 404
            : 500,
      }
    )
  }
}

export function OPTIONS() {
  return buildOptionsResponse()
}
