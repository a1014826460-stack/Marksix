import { NextRequest, NextResponse } from "next/server"

const PYTHON_API_BASE_URL = process.env.PYTHON_API_BASE_URL || "http://127.0.0.1:8000"
const PROXY_TIMEOUT_MS = 30_000

type RouteContext = {
  params: Promise<{ path: string[] }>
}

function jsonError(status: number, error: string) {
  return NextResponse.json({ ok: false, error }, { status })
}

async function proxy(request: NextRequest, context: RouteContext) {
  const { path } = await context.params
  const targetUrl = new URL(`/api/${path.join("/")}`, PYTHON_API_BASE_URL)
  targetUrl.search = request.nextUrl.search

  const headers = new Headers()
  const contentType = request.headers.get("content-type")
  const authorization = request.headers.get("authorization")
  const cookie = request.headers.get("cookie")
  const forwardedProto = request.headers.get("x-forwarded-proto") || request.nextUrl.protocol.replace(":", "")
  if (contentType) headers.set("content-type", contentType)
  if (authorization) headers.set("authorization", authorization)
  if (cookie) headers.set("cookie", cookie)
  if (forwardedProto) headers.set("x-forwarded-proto", forwardedProto)

  const method = request.method
  const body = method === "GET" || method === "HEAD" ? undefined : await request.text()
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), PROXY_TIMEOUT_MS)

  try {
    const response = await fetch(targetUrl, {
      method,
      headers,
      body,
      cache: "no-store",
      signal: controller.signal,
    })

    const responseBody = await response.text()
    const responseHeaders = new Headers({
      "content-type": response.headers.get("content-type") || "application/json; charset=utf-8",
    })
    const setCookie = response.headers.get("set-cookie")
    if (setCookie) responseHeaders.set("set-cookie", setCookie)
    return new NextResponse(responseBody, {
      status: response.status,
      headers: responseHeaders,
    })
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return jsonError(504, "Python backend request timed out")
    }
    return jsonError(502, "Python backend unavailable")
  } finally {
    clearTimeout(timeout)
  }
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, context)
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, context)
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxy(request, context)
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxy(request, context)
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxy(request, context)
}
