import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { projectPublicBridgeConfig } from "@/lib/site-platform/site-bridge-config"
import { getVendorSiteManifest } from "@/lib/site-platform/site-manifests"
import { resolveSiteApiContext } from "@/lib/site-registry"

export const runtime = "nodejs"

type RouteContext = { params: Promise<{ siteKey: string }> }

export async function GET(request: Request, context: RouteContext) {
  try {
    const { siteKey } = await context.params
    const apiContext = resolveSiteApiContext(siteKey, new URL(request.url).searchParams)
    const manifest = getVendorSiteManifest(apiContext.siteKey)
    if (!manifest) {
      return jsonWithCors({ ok: false, error: "bridge config is not enabled for this site" }, { status: 404 })
    }
    return jsonWithCors({ ok: true, site: projectPublicBridgeConfig(manifest).site, data: projectPublicBridgeConfig(manifest) })
  } catch (error) {
    const message = error instanceof Error ? error.message : "Request failed"
    return jsonWithCors({ ok: false, error: message }, { status: message.includes("Unknown siteKey") ? 404 : 500 })
  }
}

export function OPTIONS() { return buildOptionsResponse() }
