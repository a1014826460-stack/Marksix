import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { getSitePredictionModules } from "@/lib/site-api-service"
import { resolveSiteApiContext } from "@/lib/site-registry"
import { siteDataCacheHeaders } from "@/lib/site-platform/site-data-cache"

export const runtime = "nodejs"

type RouteContext = {
  params: Promise<{ siteKey: string }>
}

export async function GET(request: Request, context: RouteContext) {
  try {
    const { siteKey } = await context.params
    const { searchParams } = new URL(request.url)
    return jsonWithCors(
      await getSitePredictionModules(resolveSiteApiContext(siteKey, searchParams)),
      { headers: siteDataCacheHeaders("predictions") }
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
