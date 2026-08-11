import fs from "node:fs"
import ts from "typescript"

function compileModule(path) {
  return ts.transpileModule(fs.readFileSync(path, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
}

function toDataModule(source) {
  return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
}

const backendApiModule = toDataModule(`
  export async function backendFetchJson(pathname, options) {
    globalThis.__announcementBackendCall = { pathname, options }
    if (globalThis.__announcementBackendFailure) throw new Error("private upstream detail")
    return { id: 1, version: "v1", title: "公告", html: "<p>内容</p>", starts_at: "2026-08-11T22:32:00+08:00", ends_at: null }
  }
`)

const nextServerModule = toDataModule(`
  export const NextResponse = { json(data, init = {}) { const response = new Response(JSON.stringify(data), { ...init, headers: { "content-type": "application/json", ...(init.headers || {}) } }); return response } }
`)

const sitesModule = toDataModule(`
  export function findSiteByHost(host) {
    return host === "www.twcf888.com" ? { siteKey: "twcf888" } : null
  }
`)

const routeModule = toDataModule(
  compileModule("frontend/app/api/public/forced-announcement/route.ts")
    .replace('"next/server"', JSON.stringify(nextServerModule))
    .replace('"@/lib/backend-api"', JSON.stringify(backendApiModule))
    .replace('"@/lib/sites"', JSON.stringify(sitesModule))
)

const { GET } = await import(routeModule)

function assertNoStore(response, scenario) {
  if (response.headers.get("Cache-Control") !== "no-store") {
    throw new Error(`${scenario} must prohibit browser and CDN caching`)
  }
}

{
  const response = await GET(new Request("http://localhost/api/public/forced-announcement?site_key=twcf888"))
  if (response.status !== 200) throw new Error(`announcement proxy returned ${response.status}, expected 200`)
  assertNoStore(response, "successful announcement proxy response")
  const body = await response.json()
  if (body.version !== "v1") throw new Error("announcement proxy must preserve backend payload")
  if (globalThis.__announcementBackendCall?.pathname !== "/public/forced-announcement") {
    throw new Error("announcement proxy must call Python public endpoint")
  }
  if (globalThis.__announcementBackendCall?.options?.query?.site_key !== "twcf888") {
    throw new Error("announcement proxy must forward site_key")
  }
}

{
  const response = await GET(new Request("http://localhost/api/public/forced-announcement", {
    headers: { host: "www.twcf888.com" },
  }))
  if (response.status !== 200) throw new Error(`host fallback returned ${response.status}, expected 200`)
  if (globalThis.__announcementBackendCall?.options?.query?.site_key !== "twcf888") {
    throw new Error("announcement proxy must fall back to the registered Host identity")
  }
}

{
  const response = await GET(new Request("http://localhost/api/public/forced-announcement"))
  if (response.status !== 400) throw new Error(`missing identity returned ${response.status}, expected 400`)
  assertNoStore(response, "missing identity response")
}

{
  globalThis.__announcementBackendFailure = true
  const response = await GET(new Request("http://localhost/api/public/forced-announcement?site_key=twcf888"))
  globalThis.__announcementBackendFailure = false
  if (response.status !== 502) throw new Error(`backend failure returned ${response.status}, expected 502`)
  assertNoStore(response, "backend failure response")
  const body = await response.json()
  if (body.error !== "upstream request failed") {
    throw new Error("announcement proxy must not expose private upstream error details")
  }
}

console.log("forced announcement route contract passed")
