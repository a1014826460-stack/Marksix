import { NextResponse } from "next/server"
import { matchSiteRequest } from "@/lib/sites"

const DEFAULT_SITE_ID = "xgttc-108"

function resolveCurrentPage(request: Request) {
  const match =
    matchSiteRequest(request, "twcaibawang") || matchSiteRequest(request, "twjinniu")
  const pathname = match?.refererPath || ""

  if (pathname.endsWith("/index/index/history.html") || pathname.endsWith("/wylhc.html")) {
    return "history"
  }

  if (pathname.endsWith("/wy.html")) {
    return "draw"
  }

  return "index"
}

export async function GET(request: Request) {
  const match =
    matchSiteRequest(request, "twcaibawang") || matchSiteRequest(request, "twjinniu")
  if (!match) {
    return new NextResponse("Not found", { status: 404 })
  }

  const payload = {
    siteid: DEFAULT_SITE_ID,
    cur: resolveCurrentPage(request),
    web_id: match.site.defaultWebId,
    lottery_type: match.site.defaultLotteryTypeId,
    site_key: match.site.siteKey,
  }

  return new NextResponse(`window.jy = Object.assign(${JSON.stringify(payload)}, window.jy || {});`, {
    status: 200,
    headers: {
      "Content-Type": "application/javascript; charset=utf-8",
      "Cache-Control": "no-store",
    },
  })
}
