import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { getSitePage, recordSiteApiCompatHit } from "@/lib/site-api-service"
import { resolveSiteApiContext } from "@/lib/site-registry"

export const runtime = "nodejs"

export async function GET(request: Request) {
  try {
    const { searchParams, pathname } = new URL(request.url)
    const context = resolveSiteApiContext("twjinniu", searchParams)
    void recordSiteApiCompatHit(context, pathname)
    const payload = await getSitePage(context)
    const sitePage = payload.data.site_page
    const missingModules = sitePage.modules
      .filter((module) => !module.history?.length)
      .map((module) => ({
        mechanism_key: module.mechanism_key,
        mode_id: module.default_modes_id,
        title: module.title,
      }))

    return jsonWithCors({
      ok: true,
      site: {
        ...payload.site,
        requested_site_key:
          searchParams.get("site_key") || searchParams.get("siteKey") || context.siteKey,
      },
      data: {
        site_page: sitePage,
        canonical_modules: [],
        missing_modules: missingModules,
        homepage_source_status: {
          data_source: "local-postgresql",
          source_chain: [
            "frontend /api/twjinniu/site-page",
            "frontend /api/sites/twjinniu/site-page",
            "backend /api/public/site-page",
          ],
          live_sections: [],
          confirmed_postgresql_sections: [],
          unresolved_sections: [],
          snapshot_only_sections: [],
          live_article_module_count: sitePage.modules.length,
          missing_article_module_count: missingModules.length,
        },
      },
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
