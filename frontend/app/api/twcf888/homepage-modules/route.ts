import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
import {
  getTwcf888HomepageModules,
  type Twcf888LotteryType,
} from "@/lib/twcf888-homepage"

export const runtime = "nodejs"

function parseLotteryType(value: string | null): Twcf888LotteryType {
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

    return jsonWithCors(await getTwcf888HomepageModules(lotteryType))
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
