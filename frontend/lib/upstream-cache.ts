/**
 * 上游取数缓存 — frontend/lib/upstream-cache.ts
 * ---------------------------------------------------------------
 * 前端节点上每个 `/api/*` 请求最终都要跨公网回到中心节点（`central-api`），
 * 一个旧站页面会并发几十个预测资料请求。nginx 微缓存只能挡住浏览器侧重复，
 * Next 路由/SSR 侧的重复调用仍会各自跨节点一次。
 *
 * 这个模块在 Next 进程内做两件事：
 *   1. 按路径分档的短 TTL 缓存（开奖 3 秒、聚合资料 60 秒等）；
 *   2. 进行中请求合并（in-flight dedup），同一 key 的并发调用只回源一次。
 *
 * 约束：
 *   - 只缓存成功结果，异常不缓存也不合并；
 *   - 有容量上限，避免无界增长（单进程 Map）；
 *   - `LOTTERY_UPSTREAM_CACHE=0` 可整体关停（不需要改代码）。
 */

type CacheEntry = { expiresAt: number; value: unknown }

const MAX_ENTRIES = 400
const store = new Map<string, CacheEntry>()
const inflight = new Map<string, Promise<unknown>>()

const DEFAULT_TTL_MS = 0
const TTL_RULES: Array<{ prefix: string; ttlMs: number }> = [
  // 开奖相关：1 秒微缓存——开奖必须尽快可见，只用于合并瞬时并发。
  { prefix: "/public/latest-draw", ttlMs: 1000 },
  { prefix: "/public/next-draw-deadline", ttlMs: 1000 },
  { prefix: "/public/current-period", ttlMs: 1000 },
  // 站点资料聚合与旧站逐模块资料：与既有 60 秒预测资料缓存策略一致。
  // 预测资料：开奖后的"对/错"回填会改写载荷，且后台改资料随时可能发生，
  // 因此这三档 TTL 收紧到 10～30 秒（python-api 侧是事件失效 + KV 读，重建很便宜）。
  { prefix: "/public/site-page", ttlMs: 30000 },
  { prefix: "/vendor/homepage-modules", ttlMs: 30000 },
  { prefix: "/legacy/module-rows", ttlMs: 10000 },
  { prefix: "/legacy/current-term", ttlMs: 15000 },
  { prefix: "/public/site-links", ttlMs: 30000 },
  { prefix: "/public/forced-announcement", ttlMs: 5000 },
  { prefix: "/public/draw-history", ttlMs: 30000 },
]

export function upstreamCacheEnabled(): boolean {
  const raw = (process.env.LOTTERY_UPSTREAM_CACHE || "1").trim().toLowerCase()
  return !["0", "false", "no", "off"].includes(raw)
}

export function upstreamCacheTtlMs(pathname: string): number {
  for (const rule of TTL_RULES) {
    if (pathname === rule.prefix || pathname.startsWith(`${rule.prefix}/`) || pathname.startsWith(rule.prefix)) {
      return rule.ttlMs
    }
  }
  return DEFAULT_TTL_MS
}

function evictIfNeeded() {
  while (store.size > MAX_ENTRIES) {
    const oldest = store.keys().next()
    if (oldest.done) return
    store.delete(oldest.value)
  }
}

/**
 * 命中缓存或合并进行中的请求；未命中时调用 `load` 并写入缓存。
 * `ttlMs <= 0` 或开关关闭时退化为直连。
 */
export async function withUpstreamCache<T>(
  key: string,
  ttlMs: number,
  load: () => Promise<T>,
): Promise<T> {
  if (ttlMs <= 0 || !upstreamCacheEnabled()) {
    return load()
  }

  const cached = store.get(key)
  if (cached && cached.expiresAt > Date.now()) {
    return cached.value as T
  }

  const pending = inflight.get(key)
  if (pending) {
    return pending as Promise<T>
  }

  const promise = load()
    .then((value) => {
      store.set(key, { expiresAt: Date.now() + ttlMs, value })
      evictIfNeeded()
      return value
    })
    .finally(() => {
      inflight.delete(key)
    })

  inflight.set(key, promise as Promise<unknown>)
  return promise
}

/** 测试用：清空缓存与进行中请求。 */
export function resetUpstreamCache() {
  store.clear()
  inflight.clear()
}

/** 测试/排障用：当前缓存条目数。 */
export function upstreamCacheSize(): number {
  return store.size
}
