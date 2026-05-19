import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
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

    return jsonWithCors({
      code: 600,
      data: { content: payload?.data?.content || "" },
    })
  } catch (error) {
    console.error("notice fetch failed:", error)
    return jsonWithCors({
      code: 600,
      data: { content: "" },
    })
  }
}

export function OPTIONS() {
  return buildOptionsResponse()
}
