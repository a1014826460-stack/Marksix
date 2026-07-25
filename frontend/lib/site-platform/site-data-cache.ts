export type SiteDataResource = "draw" | "predictions"

export function siteDataCacheHeaders(resource: SiteDataResource): Record<string, string> {
  return resource === "draw"
    ? { "Cache-Control": "private, max-age=5, stale-while-revalidate=55" }
    : { "Cache-Control": "private, max-age=60, stale-while-revalidate=840" }
}
