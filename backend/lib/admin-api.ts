"use client"

export type ApiError = {
  ok?: false
  error?: string
  message?: string
  detail?: string
  locked?: boolean
  attempt_count?: number
  max_attempts?: number
}

export function getAdminToken() {
  if (typeof window === "undefined") return ""
  return window.localStorage.getItem("liuhecai_admin_token") || ""
}

export function setAdminToken(token: string) {
  window.localStorage.setItem("liuhecai_admin_token", token)
}

export function clearAdminToken() {
  window.localStorage.removeItem("liuhecai_admin_token")
}

/** 生成简单的设备指纹，用于登录锁定追踪 */
export function getDeviceFingerprint(): string {
  if (typeof window === "undefined") return ""
  const parts = [
    navigator.hardwareConcurrency || "",
    navigator.language || "",
    screen.colorDepth || "",
    screen.width || "",
    screen.height || "",
    new Date().getTimezoneOffset() || "",
    navigator.platform || "",
  ]
  // hash 为短指纹
  let hash = 0
  const raw = parts.join("|")
  for (let i = 0; i < raw.length; i++) {
    const ch = raw.charCodeAt(i)
    hash = ((hash << 5) - hash) + ch
    hash |= 0
  }
  return "fp_" + Math.abs(hash).toString(36)
}

function buildHttpErrorMessage(status: number) {
  return `请求失败：${status}`
}

export type AdminApiError = Error & {
  locked?: boolean
  attemptCount?: number
  maxAttempts?: number
}

export async function adminApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  const token = getAdminToken()
  if (!headers.has("content-type") && options.body) {
    headers.set("content-type", "application/json")
  }
  if (token) {
    headers.set("authorization", `Bearer ${token}`)
  }
  // 设备指纹（登录等敏感操作需要）
  const fp = getDeviceFingerprint()
  if (fp) {
    headers.set("X-Device-Fingerprint", fp)
  }

  const response = await fetch(`/fackyou/api/python${path}`, {
    ...options,
    headers,
    cache: "no-store",
  })

  const rawText = await response.text()
  let data: unknown = null
  if (rawText.trim()) {
    try {
      data = JSON.parse(rawText)
    } catch {
      data = { error: rawText }
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearAdminToken()
    }
    const apiError = (data ?? {}) as ApiError
    const message =
      apiError.error ||
      apiError.message ||
      apiError.detail ||
      (rawText.trim() ? rawText : buildHttpErrorMessage(response.status))
    const err = new Error(message) as AdminApiError
    if (apiError.locked) err.locked = true
    if (apiError.attempt_count != null) err.attemptCount = apiError.attempt_count
    if (apiError.max_attempts != null) err.maxAttempts = apiError.max_attempts
    throw err
  }

  return (data ?? {}) as T
}

export function jsonBody(value: unknown) {
  return JSON.stringify(value)
}
