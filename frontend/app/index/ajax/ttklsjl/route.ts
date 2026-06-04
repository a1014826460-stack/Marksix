import { NextResponse } from "next/server"
import { backendFetchJson } from "@/lib/backend-api"
import type { DrawHistoryResponse } from "@/lib/draw-history"
import { matchSiteRequest } from "@/lib/sites"

const DEFAULT_LOTTERY_TYPE = 1

function toLegacyOpenTime(value: string) {
  if (!value) return ""
  if (value.includes(" ")) return value
  return `${value} 21:30:00`
}

function toLegacyOpenCode(item: DrawHistoryResponse["items"][number]) {
  const balls = [...item.balls, ...(item.specialBall ? [item.specialBall] : [])]
  return balls.map((ball) => String(ball.value || "").padStart(2, "0")).join(",")
}

export async function GET(request: Request) {
  const match =
    matchSiteRequest(request, "twcaibawang") || matchSiteRequest(request, "twjinniu")
  if (!match) {
    return new NextResponse("Not found", { status: 404 })
  }

  const { searchParams } = new URL(request.url)
  const requestedYear = Number(searchParams.get("year")) || new Date().getFullYear()
  const lotteryType = match.site.defaultLotteryTypeId || DEFAULT_LOTTERY_TYPE

  try {
    const history = await backendFetchJson<DrawHistoryResponse>("/public/draw-history", {
      query: {
        lottery_type: lotteryType,
        year: requestedYear,
        sort: "l",
      },
    })

    const payload = {
      year: history.year || requestedYear,
      data: (history.items || []).map((item) => ({
        issue: String(item.issue || ""),
        openTime: toLegacyOpenTime(item.date || ""),
        openCode: toLegacyOpenCode(item),
      })),
    }

    return new NextResponse(`var historyAO = ${JSON.stringify(payload)};`, {
      status: 200,
      headers: {
        "Content-Type": "application/javascript; charset=utf-8",
        "Cache-Control": "no-store",
      },
    })
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error)
    return new NextResponse(
      `var historyAO = ${JSON.stringify({ year: requestedYear, data: [], error: detail })};`,
      {
        status: 200,
        headers: {
          "Content-Type": "application/javascript; charset=utf-8",
          "Cache-Control": "no-store",
        },
      },
    )
  }
}
