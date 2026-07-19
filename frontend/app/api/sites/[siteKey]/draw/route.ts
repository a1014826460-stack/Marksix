import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { backendFetchJson } from "@/lib/backend-api"
import { normalizeSiteDraw, type SiteDrawDeadlineSource, type SiteDrawSource } from "@/lib/site-platform/site-draw"
import { resolveSiteApiContext } from "@/lib/site-registry"

export const runtime = "nodejs"
type RouteContext = { params: Promise<{ siteKey: string }> }

export async function GET(request: Request, context: RouteContext) {
  try {
    const { siteKey } = await context.params
    const apiContext = resolveSiteApiContext(siteKey, new URL(request.url).searchParams)
    const [latest, deadline] = await Promise.all([
      backendFetchJson<SiteDrawSource>("/public/latest-draw", { query: { lottery_type: apiContext.lotteryType } }),
      backendFetchJson<SiteDrawDeadlineSource>("/public/next-draw-deadline", { query: { lottery_type: apiContext.lotteryType } }),
    ])
    return jsonWithCors({ ok: true, site: { site_key: apiContext.siteKey, lottery_type: apiContext.lotteryType }, data: normalizeSiteDraw(latest, deadline) })
  } catch (error) {
    const message = error instanceof Error ? error.message : "Request failed"
    return jsonWithCors({ ok: false, error: { code: "BACKEND", message, retryable: !message.includes("Unknown siteKey") } }, { status: message.includes("Unknown siteKey") ? 404 : 502 })
  }
}

export function OPTIONS() { return buildOptionsResponse() }
