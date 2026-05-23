import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { getPublicSitePageData } from "@/lib/backend-api"

export const runtime = "nodejs"

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const siteIdRaw = searchParams.get("site_id")
    const historyLimitRaw = searchParams.get("history_limit")
    const lotteryTypeRaw = searchParams.get("lottery_type")
    const payload = await getPublicSitePageData({
      siteId: siteIdRaw ? Number(siteIdRaw) : undefined,
      domain: searchParams.get("domain") || undefined,
      historyLimit: historyLimitRaw ? Number(historyLimitRaw) : undefined,
      lotteryType: lotteryTypeRaw ? Number(lotteryTypeRaw) : undefined,
    })
    return jsonWithCors(payload)
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
