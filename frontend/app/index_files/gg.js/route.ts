import { NextResponse } from "next/server"
import { matchSiteRequest } from "@/lib/sites"

export async function GET(request: Request) {
  const match =
    matchSiteRequest(request, "twcaibawang") || matchSiteRequest(request, "twjinniu")
  if (!match) {
    return new NextResponse("Not found", { status: 404 })
  }

  const payload = {
    link: match.site.routePath,
    name: match.site.forumTitle,
  }

  return new NextResponse(`window.pt = Object.assign(${JSON.stringify(payload)}, window.pt || {});`, {
    status: 200,
    headers: {
      "Content-Type": "application/javascript; charset=utf-8",
      "Cache-Control": "no-store",
    },
  })
}
