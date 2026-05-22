import { readFile } from "node:fs/promises"
import path from "node:path"

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

  const filePath = path.join(LEGACY_IMAGES_DIR, kind, modeDir, filename)
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
