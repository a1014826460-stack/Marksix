import { readFile } from "node:fs/promises"
import path from "node:path"
import { NextResponse } from "next/server"
import { getBackendApiBaseUrl } from "@/lib/backend-api"
import {
  LOTTERY_TYPE_NAMES,
  type DrawHistoryBall,
  type DrawHistoryItem,
  type DrawHistoryResponse,
  normalizeHistorySort,
  normalizeLotteryType,
} from "@/lib/draw-history"

const SNAPSHOT_BY_YEAR: Record<number, string> = {
  2026: "history-2_1000555062.html",
  2025: "history-2025_2.html",
}

const DEFAULT_PAGE_SIZE = 20
const MAX_PAGE_SIZE = 50

function stripTags(value: string) {
  return value
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim()
}

function parseBallColor(className: string) {
  if (className.includes("ball-red")) return "red"
  if (className.includes("ball-blue")) return "blue"
  if (className.includes("ball-green")) return "green"
  return ""
}

function parseBall(liHtml: string): DrawHistoryBall | null {
  const valueMatch = liHtml.match(/<dt\s+class="([^"]*)"[^>]*>([\s\S]*?)<\/dt>/i)
  if (!valueMatch) return null

  const ddMatches = [...liHtml.matchAll(/<dd[^>]*>([\s\S]*?)<\/dd>/gi)].map((match) => stripTags(match[1]))
  const zodiacElement = ddMatches[0]?.split("/") || []
  const waveSize = ddMatches[1]?.split("/") || []
  const oddEven = ddMatches[2]?.split("/") || []
  const animalSum = ddMatches[3]?.split("/") || []

  return {
    value: stripTags(valueMatch[2]),
    color: parseBallColor(valueMatch[1]),
    zodiac: zodiacElement[0]?.trim() || "",
    element: zodiacElement[1]?.trim() || "",
    wave: waveSize[0]?.trim() || "",
    size: waveSize[1]?.trim() || "",
    oddEven: oddEven[0]?.trim() || "",
    combinedOddEven: oddEven[1]?.trim() || "",
    animalType: animalSum[0]?.trim() || "",
    sumOddEven: animalSum[1]?.trim() || "",
  }
}

function normalizePositiveInteger(value: string | null, fallback: number) {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback
}

function normalizePageSize(value: string | null) {
  return Math.min(MAX_PAGE_SIZE, normalizePositiveInteger(value, DEFAULT_PAGE_SIZE))
}

function paginateItems(items: DrawHistoryItem[], page: number, pageSize: number) {
  const total = items.length
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const safePage = Math.min(Math.max(1, page), totalPages)
  const start = (safePage - 1) * pageSize

  return {
    page: safePage,
    page_size: pageSize,
    total,
    total_pages: totalPages,
    items: items.slice(start, start + pageSize),
  }
}

function withPaginationMetadata(response: DrawHistoryResponse, requestedPage: number, requestedPageSize: number) {
  if (
    Number.isFinite(response.page) &&
    Number.isFinite(response.page_size) &&
    Number.isFinite(response.total) &&
    Number.isFinite(response.total_pages)
  ) {
    if (
      response.items.length > requestedPageSize &&
      response.total > requestedPageSize &&
      response.items.length === response.total
    ) {
      return {
        ...response,
        ...paginateItems(response.items, requestedPage, requestedPageSize),
      }
    }
    return response
  }

  return {
    ...response,
    ...paginateItems(response.items || [], requestedPage, requestedPageSize),
  }
}

function parseSnapshot(html: string, lotteryType: 1 | 2 | 3, year: number, sort: "l" | "d"): DrawHistoryResponse {
  const titleRegex =
    /<div\s+class="kj-tit">([\s\S]*?)第<span\s+class="text-blue text-strong">([\s\S]*?)<\/span>期\s*<\/div>\s*<div\s+class="kj-box">\s*<ul\s+class="clearfix">([\s\S]*?)<\/ul>\s*<\/div>/gi
  const items: DrawHistoryItem[] = []
  let match: RegExpExecArray | null

  while ((match = titleRegex.exec(html))) {
    const rawTitle = stripTags(match[1])
    const dateMatch = rawTitle.match(/(\d{4}年\d{2}月\d{2}日)/)
    const issue = stripTags(match[2])
    const liMatches = [...match[3].matchAll(/<li[^>]*>([\s\S]*?)<\/li>/gi)]
    const parsedBalls = liMatches
      .filter((liMatch) => !/class="[^"]*kj-jia/.test(liMatch[0]))
      .map((liMatch) => parseBall(liMatch[1]))
      .filter((ball): ball is DrawHistoryBall => Boolean(ball))
    const balls = parsedBalls.slice(0, 6)
    const specialBall = parsedBalls[6]

    if (sort === "d") {
      balls.sort((left, right) => Number(left.value) - Number(right.value))
    }

    items.push({
      issue,
      date: dateMatch?.[1] || "",
      title: `${LOTTERY_TYPE_NAMES[lotteryType]}开奖记录 ${dateMatch?.[1] || ""} 第${issue}期`,
      balls,
      specialBall,
    })
  }

  return {
    lottery_type: lotteryType,
    lottery_name: LOTTERY_TYPE_NAMES[lotteryType],
    year,
    sort,
    years: [2026, 2025],
    page: 1,
    page_size: items.length || DEFAULT_PAGE_SIZE,
    total: items.length,
    total_pages: 1,
    items,
  }
}

async function getFallbackHistory(lotteryType: 1 | 2 | 3, year: number, sort: "l" | "d", page: number, pageSize: number) {
  const fallbackYear = SNAPSHOT_BY_YEAR[year] ? year : 2026
  const filePath = path.join(
    process.cwd(),
    "Zz_admin.shengshi8800.com",
    SNAPSHOT_BY_YEAR[fallbackYear],
  )
  const html = await readFile(filePath, "utf8")
  const snapshot = parseSnapshot(html, lotteryType, fallbackYear, sort)
  return {
    ...snapshot,
    ...paginateItems(snapshot.items, page, pageSize),
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const lotteryType = normalizeLotteryType(searchParams.get("lottery_type") || searchParams.get("type"))
  const year = Number(searchParams.get("year")) || new Date().getFullYear()
  const sort = normalizeHistorySort(searchParams.get("sort"))
  const page = normalizePositiveInteger(searchParams.get("page"), 1)
  const pageSize = normalizePageSize(searchParams.get("page_size") || searchParams.get("limit"))

  try {
    const backendUrl = new URL(`${getBackendApiBaseUrl()}/public/draw-history`)
    backendUrl.searchParams.set("lottery_type", String(lotteryType))
    backendUrl.searchParams.set("year", String(year))
    backendUrl.searchParams.set("sort", sort)
    backendUrl.searchParams.set("page", String(page))
    backendUrl.searchParams.set("page_size", String(pageSize))

    const response = await fetch(backendUrl, { cache: "no-store" })
    if (response.ok) {
      return NextResponse.json(withPaginationMetadata((await response.json()) as DrawHistoryResponse, page, pageSize))
    }
  } catch {
    // 后端接口尚未接入时使用原站快照兜底，方便前端先完整还原页面。
  }

  return NextResponse.json(await getFallbackHistory(lotteryType, year, sort, page, pageSize))
}
