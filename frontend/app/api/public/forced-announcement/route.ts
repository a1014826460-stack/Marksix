import { NextResponse } from "next/server"
import { backendFetchJson } from "@/lib/backend-api"
import { findSiteByHost } from "@/lib/sites"

export const runtime = "nodejs"

function noStoreJson(data: unknown, init?: ResponseInit) {
  const response = NextResponse.json(data, init)
  response.headers.set("Cache-Control", "no-store")
  return response
}

export async function GET(request: Request) {
  const url = new URL(request.url)
  const requestedSiteKey = String(url.searchParams.get("site_key") || "").trim()
  const hostSite = findSiteByHost(request.headers.get("host"))
  const siteKey = requestedSiteKey || hostSite?.siteKey || ""

  if (!siteKey) {
    return noStoreJson({ ok: false, error: "site_key is required" }, { status: 400 })
  }

  try {
    const payload = await backendFetchJson("/public/forced-announcement", {
      query: { site_key: siteKey },
    })
    return noStoreJson(payload, {
      headers: { "X-Announcement-Site-Key": siteKey },
    })
  } catch {
    return noStoreJson(
      { ok: false, error: "upstream request failed" },
      { status: 502 },
    )
  }
}
