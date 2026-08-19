import type { NextRequest } from "next/server"
import { NextResponse } from "next/server"
import { findSiteByHost } from "@/lib/sites"

const VALID_LEGACY_TYPES = new Set(["1", "2", "3"])

export default function proxy(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl
  const legacyType = searchParams.get("type") || searchParams.get("t")
  const host = request.headers.get("host")
  const matchedSite = findSiteByHost(host)

  const legacyHistoryPath =
    pathname === "/index/index/history.html" ||
    pathname === "/baomaqg/am/kaijiangjilu.html" ||
    pathname.endsWith("/history.html") ||
    pathname.endsWith("/wylhc.html")
  if (legacyHistoryPath) {
    const url = request.nextUrl.clone()
    url.pathname = "/history"
    if (!url.searchParams.has("type")) url.searchParams.set("type", "3")
    return NextResponse.rewrite(url)
  }

  if (pathname === "/") {
    if (matchedSite && matchedSite.routePath !== "/") {
      const url = request.nextUrl.clone()
      url.pathname = matchedSite.routePath
      url.search = ""
      return NextResponse.rewrite(url)
    }
  }

  if (pathname === "/" && legacyType && VALID_LEGACY_TYPES.has(legacyType)) {
    const url = request.nextUrl.clone()
    url.pathname = "/"
    url.search = ""
    return NextResponse.redirect(url, 301)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    "/",
    "/index/index/history.html",
    "/baomaqg/am/kaijiangjilu.html",
    "/vendor/:path*/history.html",
    "/vendor/:path*/wylhc.html",
    "/vendor/shengshi8800/embed.html",
    "/twsaimahui",
    "/twcaibawang",
  ],
}
