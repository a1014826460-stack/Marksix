import { NextResponse } from "next/server"
import { findSiteByHost, getSiteConfig, normalizeHost } from "@/lib/sites"

const SITE_KEY = "twcaibawang"
const DEFAULT_SITE_ID = "xgttc-108"

function safeParseUrl(value: string | null) {
  if (!value) return null
  try {
    return new URL(value)
  } catch {
    return null
  }
}

function isTwcaibawangRequest(request: Request) {
  const host = normalizeHost(request.headers.get("host"))
  const refererUrl = safeParseUrl(request.headers.get("referer"))
  const refererHost = normalizeHost(refererUrl?.host)
  const refererPath = refererUrl?.pathname || ""
  const matchedByHost = findSiteByHost(host)
  const matchedByReferer = findSiteByHost(refererHost)

  if (matchedByHost?.siteKey === SITE_KEY) return true
  if (matchedByReferer?.siteKey === SITE_KEY) return true
  if (refererPath.startsWith("/vendor/twcaibawang.com/")) return true
  if (refererPath.startsWith("/twcaibawang")) return true

  return false
}

function resolveCurrentPage(request: Request) {
  const refererUrl = safeParseUrl(request.headers.get("referer"))
  const pathname = refererUrl?.pathname || ""

  if (pathname.endsWith("/index/index/history.html") || pathname.endsWith("/wylhc.html")) {
    return "history"
  }

  if (pathname.endsWith("/wy.html")) {
    return "draw"
  }

  return "index"
}

export async function GET(request: Request) {
  if (!isTwcaibawangRequest(request)) {
    return new NextResponse("Not found", { status: 404 })
  }

  const site = getSiteConfig(SITE_KEY)

  const payload = {
    siteid: DEFAULT_SITE_ID,
    cur: resolveCurrentPage(request),
    web_id: site?.defaultWebId || 5,
    lottery_type: site?.defaultLotteryTypeId || 3,
    site_key: SITE_KEY,
  }

  return new NextResponse(`window.jy = Object.assign(${JSON.stringify(payload)}, window.jy || {});`, {
    status: 200,
    headers: {
      "Content-Type": "application/javascript; charset=utf-8",
      "Cache-Control": "no-store",
    },
  })
}
