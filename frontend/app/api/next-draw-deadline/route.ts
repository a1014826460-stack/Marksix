/**
 * 下次开奖截止时间 API 代理 — /api/next-draw-deadline/route.ts
 * ---------------------------------------------------------------
 * 从 Python 后端获取指定彩种的下次开奖时间（毫秒时间戳）。
 * 前端 LotteryResult 组件以此计算倒计时。
 */
import { NextResponse } from "next/server"
import { getBackendApiBaseUrl } from "@/lib/backend-api"

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const lotteryType = searchParams.get("lottery_type") || "3"

  try {
    const backendUrl = `${getBackendApiBaseUrl()}/public/next-draw-deadline?lottery_type=${lotteryType}`
    const response = await fetch(backendUrl, { cache: "no-store" })

    if (!response.ok) {
      return NextResponse.json(
        { error: "后端请求失败", detail: await response.text() },
        { status: response.status },
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    return NextResponse.json(
      { error: "获取开奖截止时间失败", detail: String(error) },
      { status: 502 },
    )
  }
}
