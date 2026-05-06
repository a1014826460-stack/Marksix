import { NextResponse } from "next/server"

import { backendFetchJson } from "@/lib/backend-api"

type LegacyPostImage = {
  id: number
  title?: string
  file_name: string
  storage_path: string
  legacy_upload_path: string
  cover_image: string
  mime_type: string
  file_size: number
  sort_order: number
  enabled: boolean
}

type BackendLegacyPostListPayload = {
  data: LegacyPostImage[]
}

function normalizeImageUrl(value: string) {
  if (!value) return ""
  return value.startsWith("/") ? value : `/${value.replace(/^\/+/, "")}`
}

export async function GET(request: Request) {
  const url = new URL(request.url)
  const type = url.searchParams.get("type")
  const web = url.searchParams.get("web")
  const pc = url.searchParams.get("pc")

  const payload = await backendFetchJson<BackendLegacyPostListPayload>("/legacy/post-list", {
    query: {
      type: type || undefined,
      web: web || undefined,
      pc: pc || undefined,
      limit: 50,
    },
  })

  // The old page only reads `cover_image`, but we keep the rest of the fields
  // in place so future maintenance can audit which DB row backed each image.
  return NextResponse.json({
    data: payload.data.map((item) => ({
      ...item,
      cover_image: normalizeImageUrl(item.cover_image),
    })),
  })
}
