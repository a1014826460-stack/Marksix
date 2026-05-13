import type { NextRequest } from "next/server"
import { NextResponse } from "next/server"

const VALID_LEGACY_TYPES = new Set(["1", "2", "3"])

function buildCanonicalRootUrl(request: NextRequest, legacyType?: string | null) {
  const url = request.nextUrl.clone()
  const params = new URLSearchParams(url.search)
  const candidate = legacyType && VALID_LEGACY_TYPES.has(legacyType) ? legacyType : null

  params.delete("type")
  params.delete("web")

  if (candidate) {
    params.set("t", candidate)
  } else if (!params.get("t") || !VALID_LEGACY_TYPES.has(params.get("t")!)) {
    params.set("t", "3")
  }

  url.pathname = "/"
  url.search = params.toString()
  return url
}

export function proxy(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl
  const legacyType = searchParams.get("type")
  const modernType = searchParams.get("t")

  if (pathname === "/vendor/shengshi8800/embed.html" && legacyType && VALID_LEGACY_TYPES.has(legacyType)) {
    return NextResponse.redirect(buildCanonicalRootUrl(request, legacyType), 301)
  }

  if (pathname === "/" && legacyType && VALID_LEGACY_TYPES.has(legacyType)) {
    return NextResponse.redirect(buildCanonicalRootUrl(request, legacyType), 301)
  }

  if (pathname === "/" && (!modernType || !VALID_LEGACY_TYPES.has(modernType))) {
    return NextResponse.redirect(buildCanonicalRootUrl(request, null), 301)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/", "/vendor/shengshi8800/embed.html"],
}
