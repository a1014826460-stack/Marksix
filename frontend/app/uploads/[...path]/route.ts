import { readFile } from "node:fs/promises"
import { existsSync } from "node:fs"
import path from "node:path"

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
  context: { params: Promise<{ path: string[] }> },
) {
  const { path: segments } = await context.params
  if (!Array.isArray(segments) || segments.length < 3) {
    return new Response("Not Found", { status: 404 })
  }

  const [kind, modeDir, ...rest] = segments
  if (kind !== "mode_474" && kind !== "mode_475" && kind !== "mode_476" && kind !== "mode_478") {
    return new Response("Not Found", { status: 404 })
  }
  if (modeDir !== "prediction") {
    return new Response("Not Found", { status: 404 })
  }

  const filename = path.basename(rest.join("/"))
  if (!filename) {
    return new Response("Not Found", { status: 404 })
  }

  const proxied = await proxyUpload([kind, modeDir, filename])
  if (proxied) {
    return proxied
  }

  const localBaseDir = LEGACY_IMAGE_DIR_CANDIDATES.find((candidate) => existsSync(candidate))
  if (!localBaseDir) {
    return new Response("Not Found", { status: 404 })
  }

  const filePath = path.join(localBaseDir, kind, modeDir, filename)
  try {
    const body = await readFile(filePath)
    return new Response(body, {
      status: 200,
      headers: {
        "Content-Type": contentTypeFor(filename),
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

async function proxyUpload(pathSegments: string[]) {
  try {
    const safePath = pathSegments.map((segment) => encodeURIComponent(segment)).join("/")
    const backendUrl = new URL(`/uploads/${safePath}`, resolveBackendOrigin())
    const response = await fetch(backendUrl, { cache: "no-store" })
    if (!response.ok) {
      return null
    }

    const filename = pathSegments.at(-1) || ""
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
