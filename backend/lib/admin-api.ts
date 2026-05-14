"use client"

export type ApiError = {
  ok?: false
  error?: string
  message?: string
  detail?: string
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

function buildHttpErrorMessage(status: number) {
  return `请求失败：${status}`
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
    throw new Error(message)
  }

  return (data ?? {}) as T
}

export function jsonBody(value: unknown) {
  return JSON.stringify(value)
}
