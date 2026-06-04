import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import {
  getTwjinniuArticleDetail,
  getTwjinniuSiteRequestDefaults,
} from "@/lib/twjinniu-articles"

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

    if (!articleId) {
      return jsonWithCors({ ok: false, error: "article_id is required" }, { status: 400 })
    }

    const article = await getTwjinniuArticleDetail(articleId, { lotteryType })
    if (!article) {
      return jsonWithCors({ ok: false, error: "article not found" }, { status: 404 })
    }

    return jsonWithCors({
      ok: true,
      site: getTwjinniuSiteRequestDefaults(lotteryType),
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
