/**
 * 开奖揭示时间线契约 — 驱动真实面板脚本的行为级验证
 * ---------------------------------------------------------------
 * 固定三条用户可见行为（2026-09-28 锚点切换到 reveal_start 后）：
 *   1. 揭示期间任意时刻刷新：进度按全局时间线续走，绝不从头重放；
 *      任何浏览器在同一时刻看到的已揭示球数完全相同。
 *   2. 揭示窗口内（reveal_start 后 0~150 秒）绝不会"突然全部出现"：
 *      已揭示数 = floor(已过秒数/25)+1，第 7 球只会在 +150 秒整点出现。
 *   3. 锚点真实生效：号码发布晚于 draw_time 时（reveal_start > draw_time），
 *      刷新仍从"首次可用时刻"开始重放揭示，而不是因窗口已过整排全显。
 * 旧数据没有 reveal_start 时退回 draw_time（兼容契约）。
 */
import fs from "node:fs"
import vm from "node:vm"

const panelPath = "frontend/public/vendor/shengshi8800/kj/local.html"
const html = fs.readFileSync(panelPath, "utf8")
const scriptMatch = /<script>([\s\S]*?)<\/script>/.exec(html)
if (!scriptMatch) throw new Error("panel inline script not found")
const script = scriptMatch[1]

const inject = `
globalThis.__hooks = {
  shouldReveal: function (p) { return _shouldRevealPayload(p); },
  startReveal: function (p) { _startReveal(p); },
  resolveStart: function (p) { return _resolveRevealStartSec(p); },
  revealStartRaw: function (p) { return _revealStartRaw(p); },
  state: function () {
    return {
      active: _revealActive,
      revealedCount: _revealedCount,
      startSec: _revealStartSec,
      now: getServerNowSeconds(),
      painted: ballPrefixIds
        .map(function (id) { var n = document.getElementById(id); return n && n.textContent; })
        .filter(function (t) { return t && t !== "--"; }).length,
    };
  },
  setNow: function (targetSec) {
    serverOffsetSec = targetSec - Math.floor(Date.now() / 1000);
  },
};
`
// 注入点必须在 IIFE 内部（闭包才能拿到 _shouldRevealPayload 等内部函数）。
const iifeClose = script.lastIndexOf("})();")
if (iifeClose < 0) throw new Error("panel script IIFE close not found")
const instrumented = script.slice(0, iifeClose) + inject + script.slice(iifeClose)

function makeElement(id) {
  return {
    id,
    textContent: "",
    innerHTML: "",
    className: "",
    href: "",
    style: {},
    classList: {
      _set: new Set(),
      add(c) { this._set.add(c) },
      remove(c) { this._set.delete(c) },
      contains(c) { return this._set.has(c) },
    },
    setAttribute() {},
    removeAttribute() {},
    addEventListener() {},
  }
}

function loadPanel({ lotteryType = "3" }) {
  const elements = new Map()
  const sandbox = {
    window: null,
    document: {
      getElementById(id) {
        if (!elements.has(id)) elements.set(id, makeElement(id))
        return elements.get(id)
      },
      querySelector() { return null },
    },
    location: { search: `?lottery_type=${lotteryType}` },
    parent: { postMessage() {} },
    fetch() { return new Promise(() => {}) },
    setTimeout() { return 0 },
    clearTimeout() {},
    setInterval() { return 0 },
    clearInterval() {},
    console: { log() {} },
    URLSearchParams,
    Intl,
    Date,
    Math,
    JSON,
    Promise,
  }
  sandbox.window = sandbox
  vm.createContext(sandbox)
  vm.runInContext(instrumented, sandbox, { filename: "kj-local.html" })
  return sandbox.__hooks
}

const MIN = 60
// 北京墙上时刻 W 对应的 UTC 瞬间是 W-8h，所以 UTC(W+8h) 的 ISO 串正是墙上时刻 W。
function beijing(ts) {
  return new Date((ts + 8 * 3600) * 1000).toISOString().replace("T", " ").slice(0, 19)
}

// draw_time 名义在 T-40min，号码 T 时刻才真正发布（reveal_start = T）→ 晚发布场景。
const T = 1_800_000_000
const payloadLate = {
  current_issue: "2026271",
  draw_time: beijing(T - 40 * MIN),
  reveal_start: beijing(T),
  result_balls: Array.from({ length: 6 }, (_, i) => ({ value: String(i + 1), zodiac: "鼠", color: "red", element: "金" })),
  special_ball: { value: "7", zodiac: "牛", color: "red", element: "金" },
}
// 准时发布场景：锚点与 draw_time 相同（回归旧行为）。
const payloadOnTime = { ...payloadLate, draw_time: beijing(T), reveal_start: beijing(T) }

// ── 1. 晚发布：锚点用 reveal_start，T 时刻起逐球重放，而不是整排全显 ──
{
  const hooks = loadPanel({})
  hooks.setNow(T)
  if (!hooks.shouldReveal(payloadLate)) throw new Error("late-published payload at T should enter staged reveal")
  hooks.startReveal(payloadLate)
  const atT0 = hooks.state()
  if (atT0.revealedCount !== 1 || atT0.painted !== 1) {
    throw new Error(`at reveal_start expect 1 ball, got count=${atT0.revealedCount} painted=${atT0.painted}`)
  }
}

// ── 2. 刷新续走 + 跨浏览器一致：T+60/T+100/T+149 三个"新开页面"进度单调且一致 ──
const expected = { 60: 3, 100: 5, 149: 6 }
for (const [elapsed, count] of Object.entries(expected)) {
  const a = loadPanel({}); a.setNow(T + Number(elapsed)); a.startReveal(payloadLate)
  const sa = a.state()
  if (sa.revealedCount !== count || sa.painted !== count) {
    throw new Error(`T+${elapsed}s: expect ${count} balls, got count=${sa.revealedCount} painted=${sa.painted}`)
  }
  const b = loadPanel({}); b.setNow(T + Number(elapsed)); b.startReveal(payloadLate)
  const sb = b.state()
  if (sb.revealedCount !== sa.revealedCount) {
    throw new Error(`T+${elapsed}s: two browsers disagree (${sa.revealedCount} vs ${sb.revealedCount})`)
  }
  if (sa.revealedCount >= 7) throw new Error(`T+${elapsed}s must not reveal all balls yet`)
}

// 同一浏览器连续刷新：进度只能前进，不能回到 1。
{
  const seq = [60, 100, 149].map((e) => {
    const h = loadPanel({}); h.setNow(T + e); h.startReveal(payloadLate)
    return h.state().revealedCount
  })
  for (let i = 1; i < seq.length; i++) {
    if (seq[i] < seq[i - 1]) throw new Error(`refresh went backwards: ${seq.join(" -> ")}`)
  }
  if (seq[0] === 1) throw new Error("refresh restarted the reveal from ball 1")
}

// ── 3. 第 7 球恰在 +150s 出现并完成；之后任何刷新都是完整结果（全局一致）──
// 完成时 _stopReveal 会清内部计数，但已绘制的 7 球保留在 DOM 上。
{
  const h = loadPanel({}); h.setNow(T + 150); h.startReveal(payloadLate)
  const s = h.state()
  if (s.painted !== 7) {
    throw new Error(`T+150s expect all 7 balls painted, got painted=${s.painted}`)
  }
  if (s.active !== false) throw new Error("reveal should be completed at +150s")
  const h2 = loadPanel({}); h2.setNow(T + 300); h2.startReveal(payloadLate)
  if (h2.state().painted !== 7) throw new Error("T+300s must show the completed result")
}

// ── 4. 准时发布：锚点=draw_time，行为与旧行为一致 ──
{
  const h = loadPanel({}); h.setNow(T + 60); h.startReveal(payloadOnTime)
  if (h.state().revealedCount !== 3) throw new Error("on-time publish at T+60s expect 3 balls")
}

// ── 5. 兼容：无 reveal_start 的旧 payload 退回 draw_time ──
{
  const hooks = loadPanel({})
  const legacy = { ...payloadLate }
  delete legacy.reveal_start
  if (hooks.revealStartRaw(legacy) !== legacy.draw_time) {
    throw new Error("resolver must fall back to draw_time when reveal_start is absent")
  }
  if (hooks.revealStartRaw(payloadLate) !== payloadLate.reveal_start) {
    throw new Error("resolver must prefer reveal_start when present")
  }
}

console.log("kj panel reveal timeline contract passed")
