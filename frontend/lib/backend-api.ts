/**
 * 后端 API 客户端模块 — backend-api.ts
 * ---------------------------------------------------------------
 * 职责：封装前端对 Python 后端 API 的所有 HTTP 请求。
 *
 * 数据流架构：
 *   React 页面 → 本模块请求函数 → fetch() → Python 后端 API
 *                                                          ↓
 *                                         返回 JSON 响应 → 组件渲染
 *
 * 关键函数：
 *   - backendFetchJson()   — 通用 JSON 请求方法
 *   - getPublicSitePageData() — 获取完整页面数据（站点+开奖+所有预测模块）
 *   - getBackendApiBaseUrl()  — 获取后端基础 URL
 *   - getConfiguredSiteId()   — 获取当前站点 ID
 *
 * 环境变量配置：
 *   - LOTTERY_BACKEND_BASE_URL  — 后端 API 地址（默认 http://127.0.0.1:8000/api）
 *   - LOTTERY_SITE_ID           — 站点 ID（默认 1）
 *
 * 旧站对比：
 *   旧站每个 JS 文件各自通过 $.ajax() 直接调用后端 API，
 *   新架构统一由此模块管理所有请求，便于维护和错误处理。
 */

import type { PublicSitePageData } from "@/lib/site-page"

// 通用类型：URL 查询参数允许的原始值类型
type PrimitiveQueryValue = string | number | boolean | null | undefined

// 请求选项类型定义
type BackendFetchOptions = {
  method?: "GET" | "POST"                        // HTTP 方法，默认 GET
  query?: Record<string, PrimitiveQueryValue>    // URL 查询参数
  body?: unknown                                 // 请求体（POST 时使用）
  headers?: HeadersInit                          // 额外的请求头
}

// 后端 API 默认地址（Python 后端默认运行在 8000 端口）
const DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000/api"

/**
 * 规范化后端基础 URL
 * ---------------------------------------------------------------
 * 确保 URL 格式正确：去除尾部斜杠，保证以 /api 结尾。
 * 例如: "http://localhost:8000" → "http://localhost:8000/api"
 *
 * @param rawValue - 从环境变量读取的原始 URL 值
 * @returns 规范化的 API 基础 URL
 */
function normalizeBackendBaseUrl(rawValue: string | undefined) {
  const value = (rawValue || DEFAULT_BACKEND_BASE_URL).trim()
  const withoutTrailingSlash = value.replace(/\/+$/, "")
  return /\/api$/i.test(withoutTrailingSlash)
    ? withoutTrailingSlash
    : `${withoutTrailingSlash}/api`
}

/**
 * 获取后端 API 基础 URL
 * 优先级：环境变量 LOTTERY_BACKEND_BASE_URL > 默认值
 */
export function getBackendApiBaseUrl() {
  return normalizeBackendBaseUrl(process.env.LOTTERY_BACKEND_BASE_URL)
}

/**
 * 获取已配置的站点 ID
 * 优先级：LOTTERY_SITE_ID > NEXT_PUBLIC_LOTTERY_SITE_ID > 默认值 1
 */
export function getConfiguredSiteId() {
  const rawValue = process.env.LOTTERY_SITE_ID || process.env.NEXT_PUBLIC_LOTTERY_SITE_ID
  const parsed = Number(rawValue)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1
}

/**
 * 构建完整后端请求 URL
 * ---------------------------------------------------------------
 * 将路径和查询参数拼接为完整的 URL 对象。
 * 自动过滤掉值为 null / undefined / 空字符串 的查询参数。
 *
 * @param pathname - API 路径（例如 /public/site-page）
 * @param query    - 查询参数键值对
 */
function buildBackendUrl(pathname: string, query?: Record<string, PrimitiveQueryValue>) {
  const url = new URL(`${getBackendApiBaseUrl()}${pathname}`)
  for (const [key, value] of Object.entries(query || {})) {
    if (value === null || value === undefined || value === "") {
      continue
    }
    url.searchParams.set(key, String(value))
  }
  return url
}

/**
 * 解析 HTTP 错误响应
 * ---------------------------------------------------------------
 * 尝试从 JSON 响应体中提取 error 或 detail 字段，
 * 同时也支持纯文本错误消息的提取。
 *
 * @param response - fetch API 的 Response 对象
 * @returns 人类可读的错误消息字符串
 */
async function parseErrorMessage(response: Response) {
  const contentType = response.headers.get("content-type") || ""
  if (contentType.includes("application/json")) {
    const payload = (await response.json().catch(() => null)) as
      | { error?: string; detail?: string }
      | null
    if (payload?.detail) return `${payload.error || "Request failed"}: ${payload.detail}`
    if (payload?.error) return payload.error
  }

  const text = await response.text().catch(() => "")
  return text || `Request failed with status ${response.status}`
}

/**
 * 通用 JSON 请求函数
 * ---------------------------------------------------------------
 * 所有后端 API 请求的统一入口。
 * 自动处理：URL 构建、JSON 序列化、错误解析、类型推断。
 *
 * @param pathname - API 路径
 * @param options  - 请求选项（方法、查询参数、请求体、请求头）
 * @returns 解析后的 JSON 响应，类型由泛型 T 指定
 *
 * 使用示例:
 *   await backendFetchJson<PublicSitePageData>("/public/site-page", {
 *     query: { site_id: 1, history_limit: 8 }
 *   })
 *
 *   await backendFetchJson("/api/predict/flat_king", {
 *     method: "POST",
 *     body: { res_code: "123", content: "虎羊" }
 *   })
 */
export async function backendFetchJson<T>(pathname: string, options: BackendFetchOptions = {}) {
  const response = await fetch(buildBackendUrl(pathname, options.query), {
    method: options.method || "GET",
    headers: {
      // POST 请求自动添加 Content-Type: application/json
      ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    cache: "no-store",  // 禁用缓存，确保每次都获取最新数据
  })

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response))
  }

  return (await response.json()) as T
}

// 公开页面数据请求选项
type PublicSiteRequestOptions = {
  siteId?: number     // 站点 ID（用于多站点场景）
  domain?: string     // 域名过滤
  historyLimit?: number // 每个预测模块返回的最大历史行数
}

/**
 * 获取公开站点页面数据
 * ---------------------------------------------------------------
 * 向前端页面提供完整数据，包括：
 *   - site:     站点基本信息（名称、域名、彩票类型等）
 *   - draw:     当前开奖快照（期号、开奖号码球、特码球）
 *   - modules:  所有启用的预测模块列表（含历史预测行）
 *
 * 这是新 React 架构的核心数据接口，
 * 对应旧站中 43 个独立 JS 文件各自 AJAX 请求的总和。
 *
 * @param options - 查询选项（站点 ID、域名、历史行数限制）
 * @returns      PublicSitePageData 类型的完整页面数据
 */
export async function getPublicSitePageData(options: PublicSiteRequestOptions = {}) {
  return backendFetchJson<PublicSitePageData>("/public/site-page", {
    query: {
      site_id: options.siteId,
      domain: options.domain,
      history_limit: options.historyLimit ?? 8,
    },
  })
}
