import { NextResponse } from "next/server"
import { findSiteByHost, normalizeHost } from "@/lib/sites"

const SITE_KEY = "twcaibawang"

function isTwcaibawangRequest(request: Request) {
  const host = normalizeHost(request.headers.get("host"))
  const referer = request.headers.get("referer")
  const refererUrl = referer ? new URL(referer) : null
  const refererPath = refererUrl?.pathname || ""
  const matchedByHost = findSiteByHost(host)

  if (matchedByHost?.siteKey === SITE_KEY) return true
  if (refererPath.startsWith("/vendor/twcaibawang.com/")) return true
  if (refererPath.startsWith("/twcaibawang")) return true

  return false
}

export async function GET(request: Request) {
  if (!isTwcaibawangRequest(request)) {
    return NextResponse.json({ error: "Not found" }, { status: 404 })
  }

  const url = new URL(request.url)
  const target = new URL("/vendor/twcaibawang.com/wylhc.html", url)
  const year = url.searchParams.get("year")
  if (year) {
    target.searchParams.set("year", year)
  }

  return NextResponse.redirect(target, 307)
}
