import { NextResponse } from "next/server"
import { matchSiteRequest } from "@/lib/sites"

export async function GET(request: Request) {
  const match =
    matchSiteRequest(request, "twcaibawang") ||
    matchSiteRequest(request, "twjinniu") ||
    matchSiteRequest(request, "twcf888")
  if (!match) {
    return NextResponse.json({ error: "Not found" }, { status: 404 })
  }

  const url = new URL(request.url)
  const target = new URL(`${match.site.legacyPublicBasePath}/wylhc.html`, url)
  const year = url.searchParams.get("year")
  if (year) {
    target.searchParams.set("year", year)
  }

  return NextResponse.redirect(target, 307)
}
