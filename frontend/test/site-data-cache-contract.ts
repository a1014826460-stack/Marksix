import { siteDataCacheHeaders } from "@/lib/site-platform/site-data-cache"

if (siteDataCacheHeaders("draw")["Cache-Control"] !== "private, max-age=5, stale-while-revalidate=55") {
  throw new Error("draw cache policy changed")
}

if (siteDataCacheHeaders("predictions")["Cache-Control"] !== "private, max-age=60, stale-while-revalidate=840") {
  throw new Error("prediction cache policy changed")
}
