import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { recordSiteTrafficEvent } from "@/lib/site-api-service"
import { resolveSiteApiContext } from "@/lib/site-registry"

export const runtime = "nodejs"

const TRAFFIC_EVENT_TYPES = new Set([
  "site_page_view",
  "article_view",
  "vendor_page_view",
  "api_compat_hit",
])

type RouteContext = {
  params: Promise<{ siteKey: string }>
}

export async function POST(request: Request, context: RouteContext) {
  try {
    const { siteKey } = await context.params
    const { searchParams } = new URL(request.url)
    const body = (await request.json().catch(() => ({}))) as Record<string, unknown>
    const eventType = typeof body.event_type === "string" ? body.event_type : ""
    if (!TRAFFIC_EVENT_TYPES.has(eventType)) {
      return jsonWithCors({ ok: false, error: "valid event_type is required" }, { status: 400 })
    }

    const apiContext = resolveSiteApiContext(siteKey, searchParams)
    return jsonWithCors(
      await recordSiteTrafficEvent(apiContext, {
        event_type: eventType as never,
        visitor_id: typeof body.visitor_id === "string" ? body.visitor_id : undefined,
        path: typeof body.path === "string" ? body.path : undefined,
        route: typeof body.route === "string" ? body.route : undefined,
        article_id:
          typeof body.article_id === "string"
            ? body.article_id
            : typeof body.articleId === "string"
              ? body.articleId
              : undefined,
        referrer: typeof body.referrer === "string" ? body.referrer : undefined,
        occurred_at: typeof body.occurred_at === "string" ? body.occurred_at : undefined,
        utm_source: typeof body.utm_source === "string" ? body.utm_source : undefined,
        utm_medium: typeof body.utm_medium === "string" ? body.utm_medium : undefined,
        utm_campaign: typeof body.utm_campaign === "string" ? body.utm_campaign : undefined,
      })
    )
  } catch (error) {
    return jsonWithCors(
      { ok: false, error: error instanceof Error ? error.message : "Request failed" },
      { status: error instanceof Error && error.message.includes("Unknown siteKey") ? 404 : 500 }
    )
  }
}

export function OPTIONS() {
  return buildOptionsResponse()
}
