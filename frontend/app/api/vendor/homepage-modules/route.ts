import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import { getVendorHomepageModules } from "@/lib/backend-api"

export const runtime = "nodejs"

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const siteId = Number(searchParams.get("site_id") || "0")
    if (!Number.isInteger(siteId) || siteId <= 0) {
      return jsonWithCors({ ok: false, error: "site_id is required" }, { status: 400 })
    }
    const historyLimit = Number(searchParams.get("history_limit") || "8")
    const lotteryTypeRaw = searchParams.get("lottery_type")
    const modules = (searchParams.get("modules") || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
    const payload = await getVendorHomepageModules({
      siteId,
      lotteryType: lotteryTypeRaw ? Number(lotteryTypeRaw) : undefined,
      modules,
      historyLimit,
    })
    return jsonWithCors(payload)
  } catch (error) {
    return jsonWithCors(
      { ok: false, error: error instanceof Error ? error.message : "Request failed" },
      { status: 500 }
    )
  }
}

export function OPTIONS() {
  return buildOptionsResponse()
}
