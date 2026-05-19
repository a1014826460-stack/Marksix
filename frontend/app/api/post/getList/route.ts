import { buildOptionsResponse, jsonWithCors } from "@/lib/api/cors"
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

  async function fetchPostList(pcValue: string | null) {
    return backendFetchJson<BackendLegacyPostListPayload>("/legacy/post-list", {
      query: {
        type: type || undefined,
        web: web || undefined,
        pc: pcValue || undefined,
        limit: 50,
      },
    })
  }

  let payload = await fetchPostList(pc)
  if (payload.data.length === 0 && pc === "72") {
    payload = await fetchPostList("305")
  }

  // The old page only reads `cover_image`, but we keep the rest of the fields
  // in place so future maintenance can audit which DB row backed each image.
  return jsonWithCors({
    data: payload.data.map((item) => ({
      ...item,
      cover_image: normalizeImageUrl(item.cover_image),
    })),
  })
}

export function OPTIONS() {
  return buildOptionsResponse()
}
