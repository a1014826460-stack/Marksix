import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { getSitePredictionModules, recordSiteApiCompatHit } from "@/lib/site-api-service"
import { resolveSiteApiContext } from "@/lib/site-registry"

export const runtime = "nodejs"

export async function GET(request: Request) {
  try {
    const { searchParams, pathname } = new URL(request.url)
    const siteKey = searchParams.get("site_key") || searchParams.get("siteKey") || undefined
    if (!siteKey && !searchParams.get("site_id")) {
      return jsonWithCors(
        { ok: false, error: "site_id or a registered site_key is required" },
        { status: 400 }
      )
    }

    const context = resolveSiteApiContext(siteKey || "shengshi8800", searchParams)
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
    return jsonWithCors(
      { ok: false, error: error instanceof Error ? error.message : "Request failed" },
      { status: 500 }
    )
  }
}

export function OPTIONS() {
  return buildOptionsResponse()
}
