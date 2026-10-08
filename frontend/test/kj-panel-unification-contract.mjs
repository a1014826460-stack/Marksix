/**
 * 十站开奖模块单一来源契约
 * ---------------------------------------------------------------
 * 用户可见要求：十个站点的开奖模块必须是同一个（一份实现、一份行为），
 * 并且台湾彩（lottery_type=3）必须满足：
 *   1. 准时开奖 —— 时序零改动（面板不参与开奖时刻，纯展示）；
 *   2. 刷新不会重新开始 —— 进度是「全局锚点 + 服务端时间」的纯函数；
 *   3. 不会突然全部出现 —— 已揭示数 = floor(已过秒/25)+1，第 7 球只在 +150 秒整出现。
 *
 * 本契约只读磁盘，不联网；真实浏览器行为由
 *   - frontend/test/kj-panel-reveal-anchor-contract.mjs
 *   - frontend/test/kj-panel-reveal-timeline-contract.mjs
 *   - frontend/test/live-site-draw-smoke.py
 * 负责。
 */
import fs from "node:fs"
import path from "node:path"

const SHARED = "/vendor/shengshi8800/kj/local.html"
const PANEL = "frontend/public/vendor/shengshi8800/kj/local.html"
const VENDOR = "frontend/public/vendor"

// ── 1. 只有一份揭示实现：共享面板之外不得出现分叉副本 ──────────────
const REVEAL_MARKERS = [
  "_computeRevealCountForTime",
  "REVEAL_INTERVAL_MS",
  "_syncRevealProgress",
  "function _startReveal(",
  "function _resolveRevealStartSec(",
]

// 构建产物（Next standalone 会把 public/ 复制一份）不算源码分叉。
const BUILD_DIRS = new Set(["node_modules", ".git", ".next", "dist", "out", "build", ".turbo"])

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (BUILD_DIRS.has(entry.name)) continue
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) walk(full, out)
    else out.push(full.split(path.sep).join("/"))
  }
  return out
}

const frontendFiles = walk("frontend").filter((f) => !f.startsWith("frontend/test/"))
// 只有真正会被浏览器加载的前端文件才算开奖模块引用；文档(.md)里的路径不算。
const SERVED = /\.(html|js|mjs|ts|tsx|json|css)$/
for (const file of frontendFiles) {
  if (!SERVED.test(file)) continue
  let text
  try {
    text = fs.readFileSync(file, "utf8")
  } catch {
    continue
  }
  if (!REVEAL_MARKERS.some((marker) => text.includes(marker))) continue
  if (file === PANEL) continue
  throw new Error(`揭示时间线出现第二份实现（开奖模块必须唯一）: ${file}`)
}

const panelCopies = walk(VENDOR).filter((f) => /\/kj\/local\.html$/.test(f))
if (panelCopies.length !== 1 || panelCopies[0] !== PANEL) {
  throw new Error(`vendor 下开奖面板必须唯一，实际: ${JSON.stringify(panelCopies)}`)
}

const panel = fs.readFileSync(PANEL, "utf8")

// ── 2. 十个站点都必须引用同一个共享面板 ──────────────────────────
// 每个站点的「开奖入口文件」必须出现共享面板路径；路径必须是绝对共享路径，
// 不允许站点私有的 kj/local.html 副本。
const SITES = {
  shengshi8800: ["frontend/public/vendor/shengshi8800/static/js/kj.js"],
  "twcaibawang.com": ["frontend/public/vendor/twcaibawang.com/index.html"],
  twsaimahui: ["frontend/public/vendor/twsaimahui/static/js/kj.js"],
  twjinniu: ["frontend/public/vendor/twjinniu/index.html"],
  "twcf888.com": ["frontend/public/vendor/twcf888.com/index.html"],
  twssz: ["frontend/public/vendor/twssz/site-config.js", "frontend/public/vendor/twssz/kai.html"],
  twbst528: ["frontend/public/vendor/twbst528/index.html"],
  twjsz666: ["frontend/public/vendor/twjsz666/kai.html"],
  twwanli: ["frontend/public/vendor/twwanli/kai.html"],
  twsyw: ["frontend/public/vendor/twsyw/kai.html", "frontend/public/vendor/twsyw/index.html"],
}
const siteNames = Object.keys(SITES)
if (siteNames.length !== 10) throw new Error(`站点清单必须是十站，实际 ${siteNames.length}`)

for (const [site, entries] of Object.entries(SITES)) {
  if (!fs.existsSync(path.join(VENDOR, site))) throw new Error(`站点目录缺失: ${site}`)
  for (const entry of entries) {
    if (!fs.existsSync(entry)) throw new Error(`${site} 的开奖入口文件缺失: ${entry}`)
    const text = fs.readFileSync(entry, "utf8")
    if (!text.includes(SHARED)) {
      throw new Error(`${site} 的开奖入口未引用共享面板 ${SHARED}: ${entry}`)
    }
  }
}

// 全仓任何指向面板的绝对 URL 都必须落在共享面板上（禁止站点私有副本）。
for (const file of frontendFiles) {
  if (!SERVED.test(file)) continue
  let text
  try {
    text = fs.readFileSync(file, "utf8")
  } catch {
    continue
  }
  const matches = [...text.matchAll(/\/vendor\/[\w./-]*kj\/local\.html/g)]
  for (const match of matches) {
    if (match[0] !== SHARED) {
      throw new Error(`${file} 引用了非共享开奖面板: ${match[0]}`)
    }
  }
}

// Next 侧入口（前端三彩种）也必须指向共享面板，台湾彩 = lottery_type=3。
const lotteryData = fs.readFileSync("frontend/lib/lotteryData.ts", "utf8")
for (const [key, type] of [["taiwan", "3"], ["macau", "2"], ["hongkong", "1"]]) {
  const pattern = new RegExp(`${key}:\\s*\\{\\s*url:\\s*"${SHARED.replace(/[/.]/g, "\\$&")}\\?lottery_type=${type}`)
  if (!pattern.test(lotteryData)) {
    throw new Error(`frontend/lib/lotteryData.ts 的 ${key} 入口未指向共享面板 lottery_type=${type}`)
  }
}

// ── 3. 台湾彩三条规则的不变量（共享面板代码级）────────────────────
const required = [
  // 规则 3：25 秒一球，第 7 球恰在 +150s
  ["var REVEAL_INTERVAL_MS = 25000;", "揭示间隔必须保持 25 秒"],
  ["var count = Math.floor(elapsedSec / REVEAL_INTERVAL_SEC) + 1;", "已揭示数必须是 floor(已过秒/25)+1"],
  ["if (count > 7) return 7;", "已揭示数必须截断到 7"],
  ["var unlockAt = revealStartSec + (REVEAL_INTERVAL_SEC * 6);", "解锁门必须等于锚点 + 6×25 秒"],
  ["var nextRevealAtMs = (_revealStartSec + (_revealedCount * REVEAL_INTERVAL_SEC)) * 1000;", "下一跳必须按绝对锚点排程（不按 now+25）"],
  // 规则 2：刷新续走，纯函数
  ["_revealedCount = Math.max(1, _computeRevealCountForTime(_revealStartSec, getServerNowSeconds()));", "启动揭示必须按全局锚点续走"],
  ["return Math.floor(Date.now() / 1000) + serverOffsetSec;", "服务端时间必须是 Date.now()+服务端校时偏移"],
  ["function _revealStartRaw(payload) {", "必须存在统一锚点解析器"],
]
for (const [token, why] of required) {
  if (!panel.includes(token)) throw new Error(`共享面板不变量丢失（${why}）: ${token}`)
}
const resolverAt = panel.indexOf("function _revealStartRaw(payload) {")
const resolverBody = panel.slice(resolverAt, panel.indexOf("}", resolverAt))
if (resolverBody.indexOf("payload.reveal_start") > resolverBody.indexOf("payload.draw_time")) {
  throw new Error("锚点解析器必须优先 reveal_start、退回 draw_time")
}
for (const token of ["parseBeijingDateTimeToSeconds(_revealStartRaw(payload))"]) {
  if (panel.split(token).length - 1 < 3) {
    throw new Error("锚点解析器必须被窗口判定/揭示起点/父页门控三处共用")
  }
}
// 安全载荷缓存只持久化已经合法展示的前缀；进度仍按全局锚点推导。
// 载荷缓存与只读诊断使用独立键；诊断不得恢复/驱动揭示进度。
for (const line of panel.split("\n")) {
  if (!line.includes("sessionStorage.setItem(")) continue
  if (!line.includes("drawCacheKey()") && !line.includes("DIAGNOSTICS_KEY")) {
    throw new Error(`共享面板的 sessionStorage 写入必须使用独立载荷/诊断键: ${line.trim()}`)
  }
  if (/_revealedCount|_revealStartSec|revealStart|revealedCount/.test(line)) {
    throw new Error(`共享面板不得把揭示进度写入 sessionStorage: ${line.trim()}`)
  }
}
const REVEAL_STATE_ASSIGN = {
  _revealedCount: [
    "0",
    "nextCount",
    "Math.max(1, _computeRevealCountForTime(_revealStartSec, getServerNowSeconds()))",
    // 服务端分片揭示：revealed_count 由后端按同一锚点 + 25 秒节拍算出，面板直接采用
    // （见下方对 backend/src/public/draw_reveal.py 的同时间线断言）。
    "_serverRevealCountForPayload(payload)",
    "_displayedServerBallCount()",
  ],
  _revealStartSec: ["0", "_resolveRevealStartSec(payload)", "anchor"],
}
for (const [variable, allowed] of Object.entries(REVEAL_STATE_ASSIGN)) {
  const assignments = [...panel.matchAll(new RegExp(`${variable}\\s*=\\s*([^;\\n]+);`, "g"))].map((m) =>
    m[1].trim(),
  )
  if (assignments.length === 0) throw new Error(`共享面板缺少 ${variable} 赋值`)
  for (const rhs of assignments) {
    if (!allowed.includes(rhs)) {
      throw new Error(`${variable} 只能由全局锚点/服务端时间推出，出现非法赋值: ${rhs}`)
    }
  }
}
// 服务端分片揭示（2026-10-04）后进度可以由后端下发，但后端必须与面板共用同一条
// 时间线：同一个 25 秒间隔、同一个锚点（reveal_start 优先 draw_time）、同一个
// floor(已过秒/25)+1 公式。否则「准时轮询」就退化成各算各的。
const revealModule = fs.readFileSync("backend/src/public/draw_reveal.py", "utf8")
const revealTimeline = [
  ["REVEAL_INTERVAL_SECONDS = 25", "后端分片间隔必须是 25 秒"],
  ['for key in ("reveal_start", "draw_time"):', "后端锚点必须 reveal_start 优先、退回 draw_time"],
  ["int(elapsed_seconds // max(1, int(interval_seconds))) + 1", "后端揭示数必须是 floor(已过秒/25)+1"],
  ["result[\"special_ball\"] = revealed[DRAW_BALL_COUNT - 1] if is_complete else None", "后端只在第 7 个号码开放时才下发特码"],
]
for (const [token, why] of revealTimeline) {
  if (!revealModule.includes(token)) throw new Error(`后端分片揭示不变量丢失（${why}）: ${token}`)
}
// 台湾必须在原始号码进入绘制、缓存和完成判定前经过独立限球分支。
if (!panel.includes("_applyTaiwanPayload(payload);") || !panel.includes("_taiwanAllowedCount(payload)")) {
  throw new Error("台湾开奖必须独立按可信时间与固定25秒限球")
}
// 拿不到全部 7 个号码时必须降级为「同步中」，而不是清空面板或报错。
for (const token of [
  "function _markRevealStalled() {",
  "resultSyncPending:",
  "function _keepPollingUntilComplete(payload, issue) {",
]) {
  if (!panel.includes(token)) {
    throw new Error(`部分号码降级路径缺失: ${token}`)
  }
}
// 台湾彩（3）必须走定时揭示，而不是香港彩（1）的轮序发布分支。
if (!panel.includes("var PROGRESSIVE_REVEAL_LOTTERY_TYPES = { 1: true };")) {
  throw new Error("轮序发布只能用于香港彩(lottery_type=1)，台湾彩必须走 25 秒定时揭示")
}
// 规则 1：号码可见性由后端 is_opened 决定，面板不得自行提前/推迟展示窗口以外的东西。
if (!panel.includes("var REVEAL_WINDOW_SEC = 210;")) {
  throw new Error("揭示窗口常量缺失（揭示只在锚点后 210 秒内逐球重放）")
}

// 父页门控（预测遮罩）必须与面板同锚点、同 +150 秒门槛。
const interceptor = fs.readFileSync(
  "frontend/public/vendor/shengshi8800/static/js/ajax_interceptor.js",
  "utf8",
)
if (!interceptor.includes("payload.reveal_start || payload.draw_time")) {
  throw new Error("预测遮罩门必须与面板同锚点（reveal_start 优先）")
}
if (!interceptor.includes("var unlockAtSec = gateTimeSec + (25 * 6);")) {
  throw new Error("预测遮罩门的解锁时刻必须是锚点 + 150 秒")
}

console.log("kj panel unification contract passed")
