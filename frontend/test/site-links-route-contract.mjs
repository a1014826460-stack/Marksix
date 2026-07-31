import fs from "node:fs"
import ts from "typescript"

function compileModule(path) {
  return ts.transpileModule(fs.readFileSync(path, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText
}

function toDataModule(source) {
  return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
}

// ---------------------------------------------------------------------------
// Stub: backend-api
// Uses globalThis so the test harness can control success / failure and
// inspect the last call.
// ---------------------------------------------------------------------------
const backendApiModule = toDataModule(`
  export async function backendFetchJson(pathname, options) {
    const meta = globalThis.__backendMeta
    meta.calls.push({ pathname, options })
    if (meta.shouldFail) throw new Error("Backend connection refused")
    return meta.response
  }
`)

// ---------------------------------------------------------------------------
// Stub: cors (mirrors the real lib/api/cors.ts contract)
// ---------------------------------------------------------------------------
const corsModule = toDataModule(`
  export function withCors(response) {
    response.headers.set("Access-Control-Allow-Origin", "*")
    response.headers.set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
    response.headers.set("Access-Control-Allow-Headers", "Content-Type, Authorization")
    return response
  }
  export function jsonWithCors(data, init) {
    return withCors(new Response(JSON.stringify(data), {
      ...init,
      headers: { "content-type": "application/json", ...(init && init.headers) },
    }))
  }
  export function buildOptionsResponse() {
    return withCors(new Response(null, { status: 204 }))
  }
`)

// ---------------------------------------------------------------------------
// Stub: sites (minimal registered site for manifest-registry validation)
// ---------------------------------------------------------------------------
const sitesModule = toDataModule(`
  const TEST_SITE = {
    siteKey: "twjsz666",
    renderMode: "legacy-shell",
    capabilities: { sitePage: true, homepageModules: true, articleDetail: false, predictionModules: true, trafficEvents: true },
    routePath: "/twjsz666",
    vendorIndexPath: "/vendor/twjsz666/index.html",
    domains: ["twjsz666.example.com"],
    legacyPublicBasePath: "/vendor/twjsz666",
    defaultGame: "mark-six",
    defaultSiteId: 8,
    defaultWebId: 8,
    defaultLotteryTypeId: 3,
    forumTitle: "twjsz666",
  }
  const SITE_CONFIGS = [TEST_SITE]
  export function getAllSiteConfigs() { return SITE_CONFIGS }
  export function getSiteConfig(siteKey) { return SITE_CONFIGS.find(function (s) { return s.siteKey === siteKey }) || null }
`)

// ---------------------------------------------------------------------------
// Real site-registry compiled against the sites stub
// ---------------------------------------------------------------------------
const registryModule = toDataModule(
  compileModule("frontend/lib/site-registry.ts").replace(
    '"@/lib/sites"',
    JSON.stringify(sitesModule)
  )
)

// ---------------------------------------------------------------------------
// Route under test (compiled against stubs)
// ---------------------------------------------------------------------------
const routeModule = toDataModule(
  compileModule("frontend/app/api/site-links/route.ts")
    .replace('"@/lib/api/cors"', JSON.stringify(corsModule))
    .replace('"@/lib/backend-api"', JSON.stringify(backendApiModule))
    .replace('"@/lib/site-registry"', JSON.stringify(registryModule))
)

const { GET, OPTIONS } = await import(routeModule)

// ---------------------------------------------------------------------------
// Shared test state (communicates with stubs via globalThis)
// ---------------------------------------------------------------------------
function resetBackendMeta(response = null, shouldFail = false) {
  globalThis.__backendMeta = { calls: [], response, shouldFail }
}

// ---------------------------------------------------------------------------
// Test 1 — missing site_key returns 400 with structured error
// ---------------------------------------------------------------------------
{
  resetBackendMeta()
  const res = await GET(new Request("http://localhost/api/site-links"))
  if (res.status !== 400) {
    throw new Error(`missing site_key returned ${res.status}, expected 400`)
  }
  const body = await res.json()
  if (body.ok !== false) {
    throw new Error("missing site_key must set ok: false")
  }
  if (!body.error || body.error.code !== "INVALID_SITE_KEY") {
    throw new Error(
      `missing site_key error code: ${JSON.stringify(body.error)}, expected code INVALID_SITE_KEY`
    )
  }
}

// ---------------------------------------------------------------------------
// Test 2 — unknown site_key returns 404 with structured error
// ---------------------------------------------------------------------------
{
  resetBackendMeta()
  const res = await GET(
    new Request("http://localhost/api/site-links?site_key=nonexistent")
  )
  if (res.status !== 404) {
    throw new Error(`unknown site_key returned ${res.status}, expected 404`)
  }
  const body = await res.json()
  if (!body.error || body.error.code !== "UNKNOWN_SITE_KEY") {
    throw new Error(
      `unknown site_key error code: ${JSON.stringify(body.error)}, expected UNKNOWN_SITE_KEY`
    )
  }
}

// ---------------------------------------------------------------------------
// Test 3 — valid site_key, backend success: 200 + CORS + pass-through JSON
// ---------------------------------------------------------------------------
{
  const backendPayload = {
    links: [
      {
        site_key: "shengshi8800",
        name: "盛世台湾六合彩",
        domain: "www.tw8800.com",
        url: "https://www.tw8800.com/",
      },
    ],
  }
  resetBackendMeta(backendPayload, false)

  const res = await GET(
    new Request("http://localhost/api/site-links?site_key=twjsz666")
  )
  if (res.status !== 200) {
    throw new Error(`valid request returned ${res.status}, expected 200`)
  }
  if (res.headers.get("Access-Control-Allow-Origin") !== "*") {
    throw new Error("valid request must include CORS Allow-Origin header")
  }

  const body = await res.json()
  if (!body.links || body.links.length !== 1) {
    throw new Error("valid request must return links array")
  }
  if (body.links[0].site_key !== "shengshi8800") {
    throw new Error("valid request must pass through backend JSON unchanged")
  }
  if (body.links[0].url !== "https://www.tw8800.com/") {
    throw new Error("valid request must preserve backend link fields")
  }

  // Verify parameter mapping: frontend site_key -> backend current_site_key
  const meta = globalThis.__backendMeta
  if (meta.calls.length !== 1) {
    throw new Error(`expected 1 backend call, got ${meta.calls.length}`)
  }
  if (meta.calls[0].pathname !== "/public/site-links") {
    throw new Error(
      `backend path: ${meta.calls[0].pathname}, expected /public/site-links`
    )
  }
  const query = meta.calls[0].options.query
  if (!query || query.current_site_key !== "twjsz666") {
    throw new Error(
      `backend query.current_site_key: ${query && query.current_site_key}, expected twjsz666`
    )
  }
}

// ---------------------------------------------------------------------------
// Test 4 — valid site_key, backend failure: 502 with structured error
// ---------------------------------------------------------------------------
{
  resetBackendMeta(null, true)

  const res = await GET(
    new Request("http://localhost/api/site-links?site_key=twjsz666")
  )
  if (res.status !== 502) {
    throw new Error(`backend failure returned ${res.status}, expected 502`)
  }
  const body = await res.json()
  if (!body.error || body.error.code !== "BACKEND") {
    throw new Error(
      `backend failure error code: ${JSON.stringify(body.error)}, expected BACKEND`
    )
  }
  if (body.error.retryable !== true) {
    throw new Error("backend failure must be marked retryable")
  }
  if (res.headers.get("Access-Control-Allow-Origin") !== "*") {
    throw new Error("error response must still include CORS header")
  }
}

// ---------------------------------------------------------------------------
// Test 5 — OPTIONS preflight returns 204 with CORS headers
// ---------------------------------------------------------------------------
{
  const res = OPTIONS()
  if (res.status !== 204) {
    throw new Error(`OPTIONS returned ${res.status}, expected 204`)
  }
  if (res.headers.get("Access-Control-Allow-Origin") !== "*") {
    throw new Error("OPTIONS must include CORS Allow-Origin header")
  }
  if (!res.headers.get("Access-Control-Allow-Methods")) {
    throw new Error("OPTIONS must include CORS Allow-Methods header")
  }
}

// ---------------------------------------------------------------------------
// Test 6 — empty site_key query parameter treated as missing
// ---------------------------------------------------------------------------
{
  resetBackendMeta()
  const res = await GET(
    new Request("http://localhost/api/site-links?site_key=")
  )
  if (res.status !== 400) {
    throw new Error(`empty site_key returned ${res.status}, expected 400`)
  }
}

console.log("All site-links route contract tests passed")
