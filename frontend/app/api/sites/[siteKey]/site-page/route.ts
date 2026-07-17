import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { getSitePage, getTwcf888SitePagePayload } from "@/lib/site-api-service"
import { resolveSiteApiContext } from "@/lib/site-registry"

export const runtime = "nodejs"

type RouteContext = {
  params: Promise<{ siteKey: string }>
}

export async function GET(request: Request, context: RouteContext) {
  try {
    const { siteKey } = await context.params
    const { searchParams } = new URL(request.url)
    const apiContext = resolveSiteApiContext(siteKey, searchParams)
    const payload =
      apiContext.siteKey === "twcf888"
        ? await getTwcf888SitePagePayload(apiContext)
        : await getSitePage(apiContext)
    return jsonWithCors(payload)
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
