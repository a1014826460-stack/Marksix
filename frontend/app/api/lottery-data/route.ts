import { NextResponse } from "next/server"
import {
  getConfiguredSiteId,
  getPublicSitePageData,
} from "@/lib/backend-api"

function normalizeDomainHeader(value: string | null) {
  const normalized = String(value || "")
    .split(",")[0]
    .trim()
    .replace(/:\d+$/, "")
    .toLowerCase()

  if (!normalized || normalized === "localhost" || normalized === "127.0.0.1") {
    return undefined
  }

  return normalized
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const siteId = Number(searchParams.get("site_id") || getConfiguredSiteId())
  const historyLimit = Number(searchParams.get("history_limit") || 8)
  const domain =
    normalizeDomainHeader(request.headers.get("x-forwarded-host")) ||
    normalizeDomainHeader(request.headers.get("host"))

  try {
    const payload = await getPublicSitePageData({
      siteId: Number.isInteger(siteId) && siteId > 0 ? siteId : getConfiguredSiteId(),
      historyLimit: Number.isInteger(historyLimit) && historyLimit > 0 ? historyLimit : 8,
      domain,
    })
    return NextResponse.json(payload)
  } catch (error) {
    return NextResponse.json(
      {
        error: "Failed to load site data from backend",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 502 },
    )
  }
}
