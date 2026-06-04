import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import {
  getTwjinniuHomepageModules,
  type TwjinniuLotteryType,
} from "@/lib/twjinniu-homepage"

export const runtime = "nodejs"

function parseLotteryType(value: string | null): TwjinniuLotteryType {
  const parsed = Number(value || "3")
  if (parsed === 1 || parsed === 2 || parsed === 3) {
    return parsed
  }
  return 3
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const lotteryType = parseLotteryType(
      searchParams.get("lottery_type") || searchParams.get("type")
    )

    return jsonWithCors(await getTwjinniuHomepageModules(lotteryType))
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
