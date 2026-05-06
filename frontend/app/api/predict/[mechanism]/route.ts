import { NextResponse } from "next/server"
import {
  parsePredictionSearchParams,
  runPrediction,
} from "@/lib/api/predictionRunner"

export const runtime = "nodejs"

type RouteContext = {
  params: Promise<{
    mechanism: string
  }>
}

export async function GET(request: Request, context: RouteContext) {
  const { mechanism } = await context.params
  const { searchParams } = new URL(request.url)
  const authorization = request.headers.get("authorization")

  try {
    return NextResponse.json(
      await runPrediction({
        mechanism,
        ...parsePredictionSearchParams(searchParams),
      }, authorization),
    )
  } catch (error) {
    return NextResponse.json(
      {
        error: "预测结果生成失败",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    )
  }
}

export async function POST(request: Request, context: RouteContext) {
  const { mechanism } = await context.params
  const authorization = request.headers.get("authorization")

  try {
    const body = await request.json().catch(() => ({}))

    return NextResponse.json(
      await runPrediction({
        mechanism,
        resCode: body?.res_code ?? body?.resCode ?? null,
        content: body?.content ?? null,
        sourceTable: body?.source_table ?? body?.sourceTable ?? null,
        targetHitRate: body?.target_hit_rate ?? body?.targetHitRate ?? null,
      }, authorization),
    )
  } catch (error) {
    return NextResponse.json(
      {
        error: "预测结果生成失败",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    )
  }
}
