import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { getSitePredictionModules, recordSiteApiCompatHit } from "@/lib/site-api-service"
import { resolvePredictionModulesCompatibilityContext } from "@/lib/site-registry"

export const runtime = "nodejs"

export async function GET(request: Request) {
  try {
    const { searchParams, pathname } = new URL(request.url)
    const context = resolvePredictionModulesCompatibilityContext(searchParams)
    void recordSiteApiCompatHit(context, pathname)
    const payload = await getSitePredictionModules(context)
    return jsonWithCors({
      ok: true,
      site: {
        site_id: context.siteId,
        site_key: context.siteKey,
        lottery_type: context.lotteryType,
        domain: context.site.domains[0],
      },
      data: payload.data.canonical_modules,
      compatibility: payload.data.compatibility,
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : "Request failed"
    const status = message === "site_id or a registered site_key is required" ? 400 : 500
    return jsonWithCors(
      { ok: false, error: message },
      { status }
    )
  }
}

export function OPTIONS() {
  return buildOptionsResponse()
}
