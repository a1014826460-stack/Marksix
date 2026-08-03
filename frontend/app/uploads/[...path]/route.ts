const DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000/api"

function extensionOf(filename: string) {
  const dot = filename.lastIndexOf(".")
  return dot >= 0 ? filename.slice(dot).toLowerCase() : ""
}

function contentTypeFor(filename: string) {
  const ext = extensionOf(filename)
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

  const filename = rest.join("/")
  if (!filename || rest.some((segment) => !segment || segment === "." || segment === "..")) {
    return new Response("Not Found", { status: 404 })
  }

  const proxied = await proxyUpload([kind, modeDir, filename])
  if (proxied) {
    return proxied
  }

  return new Response("Not Found", { status: 404 })
}

function resolveBackendOrigin() {
  const raw = (
    process.env.LOTTERY_UPLOADS_BASE_URL ||
    process.env.LOTTERY_BACKEND_BASE_URL ||
    DEFAULT_BACKEND_BASE_URL
  ).trim()
  const normalized = raw.replace(/\/+$/, "")
  return new URL(normalized)
}

function buildUploadUrl(origin: URL, relativePath: string) {
  const basePath = origin.pathname.replace(/\/+$/, "")
  const uploadPath = basePath.endsWith("/uploads")
    ? basePath
    : basePath.endsWith("/api")
      ? `${basePath.slice(0, -4)}/uploads`
      : `${basePath}/uploads`
  return new URL(`${uploadPath}/${relativePath}`, origin.origin)
}

async function proxyUpload(pathSegments: string[]) {
  try {
    const safePath = pathSegments.map((segment) => encodeURIComponent(segment)).join("/")
    const origin = resolveBackendOrigin()
    const backendUrl = buildUploadUrl(origin, safePath)
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
