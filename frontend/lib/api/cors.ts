import { NextResponse } from "next/server"

export function withCors(response: NextResponse): NextResponse {
  response.headers.set("Access-Control-Allow-Origin", "*")
  response.headers.set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
  response.headers.set("Access-Control-Allow-Headers", "Content-Type, Authorization")
  return response
}

export function jsonWithCors(data: unknown, init?: ResponseInit) {
  return withCors(NextResponse.json(data, init))
}

export function buildOptionsResponse() {
  return withCors(new NextResponse(null, { status: 204 }))
}
