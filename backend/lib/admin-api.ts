"use client"

export type ApiError = {
  ok?: false
  error?: string
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

export async function adminApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  const token = getAdminToken()
  if (!headers.has("content-type") && options.body) {
    headers.set("content-type", "application/json")
  }
  if (token) {
    headers.set("authorization", `Bearer ${token}`)
  }

  const response = await fetch(`/api/python${path}`, {
    ...options,
    headers,
    cache: "no-store",
  })
  const data = await response.json()
  if (!response.ok) {
    const message = (data as ApiError).error || `请求失败：${response.status}`
    throw new Error(message)
  }
  return data as T
}

export function jsonBody(value: unknown) {
  return JSON.stringify(value)
}
