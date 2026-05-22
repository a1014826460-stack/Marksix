import { NextResponse } from "next/server"
import { findSiteByHost, normalizeHost } from "@/lib/sites"

const SITE_KEY = "twcaibawang"

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

export async function GET(request: Request) {
  if (!isTwcaibawangRequest(request)) {
    return new NextResponse("Not found", { status: 404 })
  }

  const payload = {
    link: "/twcaibawang",
    name: "香港天天彩",
  }

  return new NextResponse(`window.pt = Object.assign(${JSON.stringify(payload)}, window.pt || {});`, {
    status: 200,
    headers: {
      "Content-Type": "application/javascript; charset=utf-8",
      "Cache-Control": "no-store",
    },
  })
}
