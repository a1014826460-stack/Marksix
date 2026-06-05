import { readFile } from "node:fs/promises"
import { existsSync } from "node:fs"
import path from "node:path"

const LEGACY_BUCKET = "20250322"
const DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000/api"
const LEGACY_IMAGE_DIR_CANDIDATES = [
  path.resolve(process.cwd(), "backend", "data", "Images"),
  path.resolve(process.cwd(), "..", "backend", "data", "Images"),
]

function contentTypeFor(filename: string) {
  const ext = path.extname(filename).toLowerCase()
  switch (ext) {
    case ".png":
      return "image/png"
    case ".jpg":
    case ".jpeg":
      return "image/jpeg"
    case ".gif":
      return "image/gif"
    case ".webp":
      return "image/webp"
    default:
      return "application/octet-stream"
  }
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ bucket: string; filename: string }> },
) {
  const { bucket, filename } = await context.params
  if (bucket !== LEGACY_BUCKET) {
    return new Response("Not Found", { status: 404 })
  }

  // Only allow a bare filename so this compatibility route cannot escape the
  // legacy image directory on disk.
  const safeFilename = path.basename(filename)
  if (safeFilename !== filename) {
    return new Response("Not Found", { status: 404 })
  }

  const proxied = await proxyLegacyImage(bucket, safeFilename)
  if (proxied) {
    return proxied
  }

  const localBaseDir = LEGACY_IMAGE_DIR_CANDIDATES.find((candidate) => existsSync(candidate))
  if (!localBaseDir) {
    return new Response("Not Found", { status: 404 })
  }

  const filePath = path.join(localBaseDir, safeFilename)

  try {
    const body = await readFile(filePath)
    return new Response(body, {
      status: 200,
      headers: {
        "Content-Type": contentTypeFor(safeFilename),
        "Cache-Control": "no-store",
      },
    })
  } catch {
    return new Response("Not Found", { status: 404 })
  }
}

function resolveBackendOrigin() {
  const raw = (process.env.LOTTERY_BACKEND_BASE_URL || DEFAULT_BACKEND_BASE_URL).trim()
  const normalized = raw.replace(/\/+$/, "")
  return new URL(normalized)
}

async function proxyLegacyImage(bucket: string, filename: string) {
  try {
    const backendUrl = new URL(`/uploads/image/${bucket}/${filename}`, resolveBackendOrigin())
    const response = await fetch(backendUrl, { cache: "no-store" })
    if (!response.ok) {
      return null
    }

    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") || contentTypeFor(filename),
        "Cache-Control": response.headers.get("cache-control") || "public, max-age=86400",
      },
    })
  } catch {
    return null
  }
}
