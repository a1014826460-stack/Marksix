import { NextResponse } from "next/server"
import { backendFetchJson } from "@/lib/backend-api"
import type { DrawHistoryResponse } from "@/lib/draw-history"
import { matchSiteRequest } from "@/lib/sites"

type LatestDrawResponse = {
  current_issue: string
  draw_time?: string
  result_balls: Array<{
    value: string
    color: "red" | "blue" | "green" | string
    zodiac: string
  }>
  special_ball: {
    value: string
    color: "red" | "blue" | "green" | string
    zodiac: string
  } | null
}

type NextDrawDeadlineResponse = {
  current_issue: string
  next_issue: string
  next_time: string | number | null
  server_time?: string | number | null
}

const DEFAULT_LOTTERY_TYPE = 1
const DEFAULT_NEXT_TIME_SUFFIX = "21:30:00"

function normalizeIssue(issue: string | null | undefined) {
  return String(issue || "").trim()
}

function normalizeWave(color: string | null | undefined) {
  const normalized = String(color || "").trim().toLowerCase()
  if (normalized === "red" || normalized === "blue" || normalized === "green") {
    return normalized
  }
  return "red"
}

function normalizeZodiac(zodiac: string | null | undefined) {
  const raw = String(zodiac || "").trim()
  switch (raw) {
    case "龙":
      return "龙"
    case "馬":
      return "马"
    case "雞":
      return "鸡"
    case "豬":
      return "猪"
    default:
      return raw
  }
}

function resolveNextTime(value: string | number | null | undefined) {
  if (typeof value === "number" && Number.isFinite(value)) {
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? "" : formatDateTime(date)
  }

  const raw = String(value || "").trim()
  if (!raw) return ""

  if (/^\d+$/.test(raw)) {
    const numeric = Number(raw)
    if (Number.isFinite(numeric)) {
      const asMs = raw.length >= 13 ? numeric : numeric * 1000
      const date = new Date(asMs)
      if (!Number.isNaN(date.getTime())) {
        return formatDateTime(date)
      }
    }
  }

  const parsed = new Date(raw.replace(/-/g, "/"))
  return Number.isNaN(parsed.getTime()) ? raw : formatDateTime(parsed)
}

function formatDateTime(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  const hours = String(date.getHours()).padStart(2, "0")
  const minutes = String(date.getMinutes()).padStart(2, "0")
  const seconds = String(date.getSeconds()).padStart(2, "0")

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

function fallbackNextTime(currentIssue: string, nextIssue: string) {
  const issue = normalizeIssue(nextIssue) || normalizeIssue(currentIssue)
  if (issue.length < 8) return ""

  const year = issue.slice(0, 4)
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, "0")
  const day = String(now.getDate()).padStart(2, "0")
  return `${year}-${month}-${day} ${DEFAULT_NEXT_TIME_SUFFIX}`
}

async function loadLatestDraw(lotteryType: number) {
  return backendFetchJson<LatestDrawResponse>("/public/latest-draw", {
    query: { lottery_type: lotteryType },
  })
}

async function loadNextDeadline(lotteryType: number) {
  return backendFetchJson<NextDrawDeadlineResponse>("/public/next-draw-deadline", {
    query: { lottery_type: lotteryType },
  })
}

async function loadHistorySnapshot(lotteryType: number, issue: string) {
  const year = Number(issue.slice(0, 4)) || new Date().getFullYear()
  const response = await backendFetchJson<DrawHistoryResponse>("/public/draw-history", {
    query: {
      lottery_type: lotteryType,
      year,
      sort: "l",
    },
  })

  return response.items.find((item) => `${year}${item.issue}` === issue) || null
}

export async function GET(request: Request) {
  const match =
    matchSiteRequest(request, "twcaibawang") || matchSiteRequest(request, "twjinniu")
  if (!match) {
    return NextResponse.json({ error: "Not found" }, { status: 404 })
  }

  const lotteryType = match.site.defaultLotteryTypeId || DEFAULT_LOTTERY_TYPE

  try {
    const [latestDraw, nextDeadline] = await Promise.all([
      loadLatestDraw(lotteryType),
      loadNextDeadline(lotteryType),
    ])

    const issue = normalizeIssue(latestDraw.current_issue)
    const historyItem = issue ? await loadHistorySnapshot(lotteryType, issue) : null
    const historyBalls = historyItem
      ? [...historyItem.balls, ...(historyItem.specialBall ? [historyItem.specialBall] : [])]
      : []

    const resultBalls = [
      ...latestDraw.result_balls,
      ...(latestDraw.special_ball ? [latestDraw.special_ball] : []),
    ]

    const zodiac = resultBalls.map((ball) => normalizeZodiac(ball.zodiac)).join(",")
    const wave = resultBalls.map((ball) => normalizeWave(ball.color)).join(",")
    const wuxin = resultBalls
      .map((ball, index) => historyBalls[index]?.element || "")
      .join(",")

    const nextIssue = normalizeIssue(nextDeadline.next_issue)
    const nextTime =
      resolveNextTime(nextDeadline.next_time) || fallbackNextTime(issue, nextIssue)

    return NextResponse.json(
      [
        {
          expect: issue,
          openCode: resultBalls.map((ball) => String(ball.value || "").padStart(2, "0")).join(","),
          zodiac,
          wave,
          wuxin,
          nextexpect: nextIssue,
          nextTime,
        },
      ],
      {
        headers: {
          "Cache-Control": "no-store",
        },
      },
    )
  } catch (error) {
    return NextResponse.json(
      {
        error: "Failed to build wy.json",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 502 },
    )
  }
}
