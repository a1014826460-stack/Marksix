/**
 * 开奖数据 API 代理路由 — /api/latest-draw/route.ts
 * ---------------------------------------------------------------
 * 从 Python 后端获取指定彩种的最新开奖数据。
 * 前端 client component 通过此代理访问后端 /api/public/latest-draw，
 * 避免在前端暴露后端内网地址。
 */
import { NextResponse } from "next/server"
import { getBackendApiBaseUrl } from "@/lib/backend-api"

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const lotteryType = searchParams.get("lottery_type") || "1"

  try {
    const backendUrl = `${getBackendApiBaseUrl()}/public/latest-draw?lottery_type=${lotteryType}`
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
      { error: "获取开奖数据失败", detail: String(error) },
      { status: 502 },
    )
  }
}
