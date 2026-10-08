/**
 * 开奖数据 API 代理路由 — /api/latest-draw/route.ts
 * ---------------------------------------------------------------
 * 从 Python 后端获取指定彩种的最新开奖数据。
 * 前端 client component 通过此代理访问后端 /api/public/latest-draw，
 * 避免在前端暴露后端内网地址。
 */
import { NextResponse } from "next/server"
import { getBackendApiBaseUrl } from "@/lib/backend-api"
import { guardTaiwanLiveDraw } from "@/lib/taiwan-draw-gate"

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const lotteryType = searchParams.get("lottery_type") || "1"

  try {
    const backendUrl = `${getBackendApiBaseUrl()}/public/latest-draw?lottery_type=${lotteryType}`
    const [response, deadlineResponse] = await Promise.all([
      fetch(backendUrl, { cache: "no-store" }),
      Number(lotteryType) === 3 ? fetch(`${getBackendApiBaseUrl()}/public/next-draw-deadline?lottery_type=3`, { cache: "no-store" }) : Promise.resolve(null),
    ])

    if (!response.ok) {
      return NextResponse.json(
        { error: "后端请求失败", detail: await response.text() },
        { status: response.status, headers: { "Cache-Control": "no-store" } },
      )
    }

    const data = await response.json()
    const deadline = deadlineResponse?.ok ? await deadlineResponse.json() : {}
    return NextResponse.json(guardTaiwanLiveDraw(data, deadline, { lotteryType: Number(lotteryType), nowMs: Date.now() }), { headers: { "Cache-Control": "no-store" } })
  } catch (error) {
    return NextResponse.json(
      { error: "获取开奖数据失败", detail: String(error) },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    )
  }
}
