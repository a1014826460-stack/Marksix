import { NextResponse } from "next/server"

import { backendFetchJson } from "@/lib/backend-api"

export const runtime = "nodejs"

type NoticePayload = {
  code: number
  data: {
    content: string
  }
}

/**
 * GET /api/index/notice?web=6
 *
 * 旧前端 (twsaimahui) 公告弹窗接口。
 * 代码必须等于 600，否则 index.html 中的内联脚本会跳过公告展示。
 */
export async function GET(request: Request) {
  const url = new URL(request.url)
  const web = url.searchParams.get("web") || ""

  try {
    const payload = await backendFetchJson<NoticePayload>("/public/notice", {
      query: { web: web || undefined },
    })

    // 透传 Python 后端的完整响应（包含 code 字段）
    return NextResponse.json(payload)
  } catch (error) {
    // 公告获取失败不应阻断页面，返回空公告
    console.error("notice fetch failed:", error)
    return NextResponse.json({
      code: 200,
      data: { content: "" },
    })
  }
}
