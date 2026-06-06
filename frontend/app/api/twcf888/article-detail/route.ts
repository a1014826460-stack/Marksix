import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import {
  getTwcf888ArticleDetail,
  getTwcf888SiteRequestDefaults,
} from "@/lib/twcf888-articles"

export const runtime = "nodejs"

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const articleId =
      searchParams.get("article_id") ||
      searchParams.get("articleId") ||
      searchParams.get("id") ||
      ""
    const lotteryType = Number(searchParams.get("lottery_type") || searchParams.get("lotteryType") || "3") || 3
    const group = searchParams.get("group") || undefined

    if (!articleId) {
      return jsonWithCors({ ok: false, error: "article_id is required" }, { status: 400 })
    }

    const article = await getTwcf888ArticleDetail(articleId, { lotteryType, group })
    if (!article) {
      return jsonWithCors({ ok: false, error: "article not found" }, { status: 404 })
    }

    return jsonWithCors({
      ok: true,
      site: getTwcf888SiteRequestDefaults(lotteryType),
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
