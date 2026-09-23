/**
 * 上游取数缓存契约 — frontend/lib/upstream-cache.ts
 * ---------------------------------------------------------------
 * 前端节点上的每个 /api/* 请求都要跨公网回中心节点，旧站一页并发几十个预测资料请求。
 * 本契约固定三件事：路径分档 TTL、命中/并发合并、失败不缓存与可关停。
 */
import fs from "node:fs"
import ts from "typescript"

const source = ts.transpileModule(fs.readFileSync("frontend/lib/upstream-cache.ts", "utf8"), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
const cache = await import(moduleUrl)

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

// 1. 路径分档
const ttlCases = [
  ["/public/latest-draw", 1000],
  ["/public/next-draw-deadline", 1000],
  ["/public/site-page", 30000],
  ["/vendor/homepage-modules", 30000],
  ["/legacy/module-rows", 10000],
  ["/legacy/current-term", 15000],
  ["/public/site-links", 30000],
  ["/public/forced-announcement", 5000],
  ["/api/unknown-endpoint", 0],
]
for (const [pathname, expected] of ttlCases) {
  const actual = cache.upstreamCacheTtlMs(pathname)
  if (actual !== expected) throw new Error(`ttl for ${pathname} = ${actual}, expected ${expected}`)
}

// 2. 命中缓存：相同 key 只回源一次
cache.resetUpstreamCache()
let loads = 0
const loadOnce = async () => {
  loads += 1
  return { value: loads }
}
const first = await cache.withUpstreamCache("k1", 60000, loadOnce)
const second = await cache.withUpstreamCache("k1", 60000, loadOnce)
if (loads !== 1) throw new Error(`cache hit failed: loader ran ${loads} times`)
if (first.value !== second.value) throw new Error("cached value differs")

// 3. 并发合并：同时在途的相同 key 只回源一次
cache.resetUpstreamCache()
loads = 0
const slowLoad = async () => {
  loads += 1
  await sleep(20)
  return loads
}
const concurrent = await Promise.all([
  cache.withUpstreamCache("k2", 60000, slowLoad),
  cache.withUpstreamCache("k2", 60000, slowLoad),
  cache.withUpstreamCache("k2", 60000, slowLoad),
])
if (loads !== 1) throw new Error(`in-flight dedup failed: loader ran ${loads} times`)
if (concurrent.some((value) => value !== concurrent[0])) throw new Error("concurrent results differ")

// 4. TTL 过期后重新回源
cache.resetUpstreamCache()
loads = 0
await cache.withUpstreamCache("k3", 5, loadOnce)
await sleep(30)
await cache.withUpstreamCache("k3", 5, loadOnce)
if (loads !== 2) throw new Error(`ttl expiry failed: loader ran ${loads} times`)

// 5. 失败不缓存
cache.resetUpstreamCache()
let attempts = 0
const failing = async () => {
  attempts += 1
  throw new Error("upstream down")
}
for (const _ of [1, 2]) {
  try {
    await cache.withUpstreamCache("k4", 60000, failing)
  } catch {
    // 预期
  }
}
if (attempts !== 2) throw new Error(`failure must not be cached: attempts=${attempts}`)

// 6. 关停开关
process.env.LOTTERY_UPSTREAM_CACHE = "0"
cache.resetUpstreamCache()
loads = 0
await cache.withUpstreamCache("k5", 60000, loadOnce)
await cache.withUpstreamCache("k5", 60000, loadOnce)
if (loads !== 2) throw new Error(`kill switch failed: loader ran ${loads} times`)
delete process.env.LOTTERY_UPSTREAM_CACHE

// 7. 容量上限
cache.resetUpstreamCache()
for (let index = 0; index < 600; index += 1) {
  await cache.withUpstreamCache(`bulk-${index}`, 60000, async () => index)
}
if (cache.upstreamCacheSize() > 400) {
  throw new Error(`cache size ${cache.upstreamCacheSize()} exceeds the 400 entry bound`)
}

console.log("upstream cache contract passed")
