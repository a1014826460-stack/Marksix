/**
 * 预测执行器模块 — predictionRunner.ts
 * ---------------------------------------------------------------
 * 职责：管理预测生成的请求，通过 Next.js API Route 代理将请求转发到 Python 后端。
 *
 * 使用场景：
 *   1. 管理后台：管理员手动触发预测生成
 *   2. 公开前端：通过 Next.js API Route（/api/predict/[mechanism]）代理执行
 *
 * 数据流：
 *   管理后台 UI → runPrediction() → Next.js API Route 代理
 *                                    → Python 后端 /api/predict/:mechanism
 *                                    → 预测引擎执行算法
 *                                    → 返回预测结果
 *
 * 注意：预测生成请求必须通过 Next.js API Route 转发，不能直接调用 Python 后端。
 *       这样设计是为了保持 admin 权限边界，防止公开前端直接触发预测进程。
 */

import { backendFetchJson } from "@/lib/backend-api"

/**
 * 预测请求参数
 * @property mechanism      - 预测机制标识（如 "flat_king"、"three_issue"、"double_wave"）
 * @property resCode        - 预留代码，用于特定预测算法
 * @property content        - 预测内容（如 "虎羊"），可为空让系统自动生成
 * @property sourceTable    - 数据源表名，覆盖默认值
 * @property targetHitRate  - 目标命中率，用于优化预测算法
 */
export type PredictionRequest = {
  mechanism: string
  resCode?: string | null
  content?: string | null
  sourceTable?: string | null
  targetHitRate?: number | null
  lotteryType?: number | string | null
  year?: number | string | null
  term?: number | string | null
  web?: number | string | null
}

export type PredictionApiResponse = {
  ok: true
  protocol_version: string
  generated_at: string
  data: {
    mechanism: {
      key: string
      title: string
      default_modes_id: number | null
      default_table: string
      resolved_labels: string[]
    }
    source: {
      db_path: string
      table: string
      source_modes_id: number | null
      source_table_title: string
      history_count: number | null
    }
    request: {
      res_code: string | null
      content: string | null
      source_table: string | null
      target_hit_rate: number | null
      lottery_type: number | string | null
      year: number | string | null
      term: number | string | null
      web: number | string | null
    }
    context: {
      latest_term: number | string | null
      latest_outcome: string | null
      draw: {
        lottery_type_id?: number | null
        year?: string
        term?: string
        issue?: string
        draw_found?: boolean
        is_opened?: boolean | null
        result_visibility: "visible" | "hidden" | "unknown"
        reason: string
      }
    }
    prediction: {
      labels: string[]
      content: unknown
      content_json: string
      display_text: string
    }
    backtest: Record<string, unknown>
    explanation: string[]
    warning: string
  }
  legacy: Record<string, unknown>
}

/**
 * 规范化文本输入
 * 去除首尾空格，空字符串返回 null
 */
function normalizeText(value: unknown) {
  if (typeof value !== "string") {
    return null
  }

  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

/**
 * 从 URL 查询参数中解析预测请求参数
 * 用于 Next.js API Route 处理 GET 请求时提取参数
 *
 * @param searchParams - URLSearchParams 对象
 * @returns 解析后的部分 PredictionRequest（不含 mechanism，需调用方补充）
 */
export function parsePredictionSearchParams(searchParams: URLSearchParams) {
  const targetHitRate = searchParams.get("target_hit_rate")

  return {
    resCode: normalizeText(searchParams.get("res_code")),
    content: normalizeText(searchParams.get("content")),
    sourceTable: normalizeText(searchParams.get("source_table")),
    targetHitRate: targetHitRate ? Number(targetHitRate) : null,
    lotteryType: normalizeText(searchParams.get("lottery_type")),
    year: normalizeText(searchParams.get("year")),
    term: normalizeText(searchParams.get("term")),
    web: normalizeText(searchParams.get("web")),
  }
}

/**
 * 执行预测
 * ---------------------------------------------------------------
 * 向后端发送 POST 请求触发预测生成。
 * 预测生成逻辑完全由 Python 后端处理（backend/src/predict/mechanisms.py），
 * 前端仅负责传递参数和接收结果。
 *
 * @param request       - 预测请求参数
 * @param authorization - 可选的 Authorization 请求头（管理后台传入 JWT token）
 * @returns 后端返回的预测结果（类型由后端决定）
 */
export async function runPrediction(
  request: PredictionRequest,
  authorization?: string | null,
) {
  return backendFetchJson(`/predict/${request.mechanism}`, {
    method: "POST",
    headers: authorization ? { Authorization: authorization } : undefined,
    body: {
      res_code: request.resCode ?? null,
      content: request.content ?? null,
      source_table: request.sourceTable ?? null,
      target_hit_rate: request.targetHitRate ?? null,
      lottery_type: request.lotteryType ?? null,
      year: request.year ?? null,
      term: request.term ?? null,
      web: request.web ?? null,
    },
  }) as Promise<PredictionApiResponse>
}
