import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { backendFetchJson } from "@/lib/backend-api"
import { resolveSiteApiContext } from "@/lib/site-registry"

export const runtime = "nodejs"

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const siteKey = searchParams.get("site_key")
    if (!siteKey) {
      return jsonWithCors(
        {
          ok: false,
          error: {
            code: "INVALID_SITE_KEY",
            message: "site_key query parameter is required",
          },
        },
        { status: 400 }
      )
    }

    // Validate site_key against the manifest registry (throws if unknown).
    const apiContext = resolveSiteApiContext(siteKey, searchParams)

    const payload = await backendFetchJson<{
      links: Array<{
        site_key: string
        name: string
        domain: string
        url: string
      }>
    }>("/public/site-links", {
      query: { current_site_key: apiContext.siteKey },
    })

    return jsonWithCors(payload)
  } catch (error) {
    const message = error instanceof Error ? error.message : "Request failed"
    const isUnknownSiteKey = message.includes("Unknown siteKey")
    return jsonWithCors(
      {
        ok: false,
        error: {
          code: isUnknownSiteKey ? "UNKNOWN_SITE_KEY" : "BACKEND",
          message,
          retryable: !isUnknownSiteKey,
        },
      },
      { status: isUnknownSiteKey ? 404 : 502 }
    )
  }
}

export function OPTIONS() {
  return buildOptionsResponse()
}
