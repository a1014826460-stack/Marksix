import { readFile } from "node:fs/promises"
import path from "node:path"

const LEGACY_BUCKET = "20250322"
const LEGACY_IMAGES_DIR = path.resolve(process.cwd(), "..", "backend", "data", "Images")

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

  const filePath = path.join(LEGACY_IMAGES_DIR, safeFilename)

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
