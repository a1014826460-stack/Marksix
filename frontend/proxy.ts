import type { NextRequest } from "next/server"
import { NextResponse } from "next/server"

const VALID_LEGACY_TYPES = new Set(["1", "2", "3"])

export function proxy(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl
  const legacyType = searchParams.get("type") || searchParams.get("t")

  if (pathname === "/" && legacyType && VALID_LEGACY_TYPES.has(legacyType)) {
    const url = request.nextUrl.clone()
    url.pathname = "/"
    url.search = ""
    return NextResponse.redirect(url, 301)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/", "/vendor/shengshi8800/embed.html"],
}
