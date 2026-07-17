import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { getTwcf888SitePagePayload, recordSiteApiCompatHit } from "@/lib/site-api-service"
import { resolveSiteApiContext } from "@/lib/site-registry"

export const runtime = "nodejs"

export async function GET(request: Request) {
  try {
    const { searchParams, pathname } = new URL(request.url)
    const context = resolveSiteApiContext("twcf888", searchParams)
    void recordSiteApiCompatHit(context, pathname)
    const payload = await getTwcf888SitePagePayload(context)
    return jsonWithCors({
      ok: true,
      site: payload.site,
      data: payload.data,
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
