/**
 * 共享开奖面板加载契约 — frontend/public/vendor/shengshi8800/kj/local.html
 * ---------------------------------------------------------------
 * 面板被十个站点以多层 iframe 引用，首屏出号时间直接决定“开奖模块卡顿”的观感。
 * 本契约固定两条改造后的行为：
 *   1. 倒计时截止时间（/api/next-draw-deadline）与开奖号码（/api/latest-draw）
 *      并发发起，号码不得等截止时间返回后才开始加载；
 *   2. 开奖号码读取层带 5 秒新鲜窗口的 sessionStorage 缓存与进行中请求去重，
 *      手动刷新始终直连网络。
 */
import fs from "node:fs"

const panel = fs.readFileSync("frontend/public/vendor/shengshi8800/kj/local.html", "utf8")

// 1. 并发启动：初始化尾段必须先发起 load(...)，再发 fetchCountdownDeadline()。
const initAnchor = panel.lastIndexOf("setInterval(updateBeijingDate, 1000);")
if (initAnchor < 0) throw new Error("panel initialisation block was not found")
const initBlock = panel.slice(initAnchor, panel.lastIndexOf("})();"))
const loadIndex = initBlock.indexOf("load({ revealOnLoad: true })")
const deadlineIndex = initBlock.indexOf("fetchCountdownDeadline()")
if (loadIndex < 0) throw new Error("panel no longer starts the first draw load explicitly")
if (deadlineIndex < 0) throw new Error("panel no longer fetches the next draw deadline on startup")
if (loadIndex > deadlineIndex) {
  throw new Error("next draw deadline is still awaited before the first draw load (serialised startup)")
}
if (/fetchCountdownDeadline\(\)\.then\(function \(\) \{[\s\S]*?\} else \{\s*load\(/.test(panel)) {
  throw new Error("panel still loads the draw inside the deadline callback")
}

// 2. 短缓存 + 去重：读取层必须存在，且 load() 通过它取数。
for (const token of [
  "DRAW_CACHE_FRESH_MS = 3000",
  "sessionStorage",
  "_latestDrawInFlight",
  "function loadLatestDrawPayload(",
  "loadLatestDrawPayload(!!isManual)",
]) {
  if (!panel.includes(token)) throw new Error(`panel cache layer missing ${token}`)
}
if (!panel.includes("writeDrawCache(payload)")) throw new Error("panel never caches the draw payload")
if (!panel.includes('debugLog("latest-draw:cache-hit"')) {
  throw new Error("panel cache hits are not observable in the console")
}

// 3. 手动刷新必须绕过缓存直连网络。
if (!/loadLatestDrawPayload\(!!isManual\)/.test(panel)) {
  throw new Error("manual refresh no longer bypasses the draw cache")
}

// 4. 请求去重不得绕过既有的加载互斥量。
if (!panel.includes("if (_loadingLatestDraw) return;")) {
  throw new Error("panel lost its concurrent load guard")
}

console.log("kj panel loading contract passed")
