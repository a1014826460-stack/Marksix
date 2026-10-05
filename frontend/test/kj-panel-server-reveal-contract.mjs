/**
 * 服务端分片揭示契约 — 驱动真实面板脚本的行为级验证
 * ---------------------------------------------------------------
 * 2026-10-04 起的开奖节奏：**后端** /api/latest-draw 按 reveal_start + 25s×N
 * 逐球下发号码（backend/src/public/draw_reveal.py），载荷带 revealed_count /
 * total_balls / is_complete。面板只负责把「此刻可用」的球画出来并继续轮询。
 *
 * 固定行为：
 *   1. 面板进度以服务端 revealed_count 为权威：本地时钟不会「补看」未开放的球。
 *   2. 号码没齐时保持 5 秒轮询，且窗口按揭示锚点 + 210 秒计算（晚开盘也够）。
 *   3. 第 7 个号码到位的那一刻只通知一次父页（legacy-draw-reveal-complete）。
 *   4. 拿不到全部 7 个号码时：保留已开放的球 + 提示「开奖结果同步中...」，
 *      不清空面板、不抛错。
 *   5. 老后端/旧快照（没有 revealed_count）只拿到部分号码时也会保持轮询，
 *      不会停在半个结果上不动。
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
  load: function (options) { return load(options || { revealOnLoad: true }); },
  state: function () {
    var painted = 0;
    for (var i = 0; i < ballPrefixIds.length; i++) {
      var node = document.getElementById(ballPrefixIds[i]);
      if (node && node.textContent && node.textContent !== "--") painted += 1;
    }
    var badge = document.getElementById("countdownBadge");
    return {
      polling: _revealPolling,
      active: _revealActive,
      serverPaced: _serverPacedReveal,
      revealedCount: _revealedCount,
      windowEndsAtSec: _revealWindowEndsAtSec,
      lastRenderedIssue: _lastRenderedIssue,
      painted: painted,
      badgeText: badge ? String(badge.textContent || "") : "",
    };
  },
  setNow: function (targetSec) {
    serverOffsetSec = targetSec - Math.floor(Date.now() / 1000);
  },
  expireWindow: function () { _revealWindowEndsAtSec = getServerNowSeconds() - 1; },
  fireIntervals: function () {
    recordedIntervals.forEach(function (callback) { callback(); });
  },
  setRevealTarget: function (issue) { _revealTargetIssue = normalizeIssue(issue); },
  polling: function () { return _revealPolling; },
  manualRefresh: function () { return refreshWithDeadlineSync(); },
  timeouts: function () {
    return (globalThis.__recordedTimeouts || []).map(function (item) { return item.delayMs; });
  },
  displayedBalls: function () { return _displayedServerBallCount(); },
  notifications: function () { return notifications; },
};
`

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
      add(value) { this._set.add(value) },
      remove(value) { this._set.delete(value) },
      contains(value) { return this._set.has(value) },
    },
    setAttribute() {},
    removeAttribute() {},
    addEventListener() {},
  }
}

/** 挂载面板；payload 由测试给定，fetch 桩按 URL 直接返回它。 */
function loadPanel({ lotteryType = "3", payload, deadline = null }) {
  const elements = new Map()
  const recordedIntervals = []
  const recordedTimeouts = []
  const notifications = []
  const state = { payload, deadline }
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
    parent: { postMessage(message) { notifications.push(message) } },
    fetch(url) {
      const target = String(url)
      const body = target.includes("next-draw-deadline") ? (state.deadline || {}) : state.payload
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
    },
    sessionStorage: {
      getItem() { return null },
      setItem() {},
      removeItem() {},
      length: 0,
      key() { return null },
    },
    setTimeout(callback, delayMs) {
      recordedTimeouts.push({ callback, delayMs: Number(delayMs) || 0 })
      return recordedTimeouts.length
    },
    clearTimeout() {},
    setInterval(callback) { recordedIntervals.push(callback); return recordedIntervals.length },
    clearInterval() {},
    console: { log() {} },
    URLSearchParams,
    Intl,
    Date,
    Math,
    JSON,
    Promise,
    isFinite,
  }
  sandbox.window = sandbox
  vm.createContext(sandbox)
  vm.runInContext(instrumented, sandbox, { filename: "kj-local.html" })
  sandbox.recordedIntervals = recordedIntervals
  sandbox.recordedTimeouts = recordedTimeouts
  sandbox.__recordedTimeouts = recordedTimeouts
  sandbox.notifications = notifications
  sandbox.__state = state
  sandbox.__hooks.setPayload = (next) => { state.payload = next }
  sandbox.__hooks.setDeadline = (next) => { state.deadline = next }
  return sandbox
}

const MIN = 60
// 北京墙上时刻 W 对应的 UTC 瞬间是 W-8h，所以 UTC(W+8h) 的 ISO 串正是墙上时刻 W。
function beijing(ts) {
  return new Date((ts + 8 * 3600) * 1000).toISOString().replace("T", " ").slice(0, 19)
}

async function settle() {
  for (let index = 0; index < 16; index += 1) await Promise.resolve()
}

const T = Math.floor(Date.now() / 1000)

function ball(value, zodiac = "鼠") {
  return { value, zodiac, color: "red", element: "金" }
}

/** 服务端分片载荷：只带 revealed_count 个号码。 */
function slicedPayload({ issue = "2026281", revealedCount, revealStartSec = T, total = 7 }) {
  const values = ["01", "02", "03", "04", "05", "06", "49"]
  const visible = values.slice(0, revealedCount)
  return {
    current_issue: issue,
    draw_time: beijing(revealStartSec),
    reveal_start: beijing(revealStartSec),
    result_balls: visible.slice(0, 6).map((value) => ball(value)),
    special_ball: visible.length >= total ? ball(visible[total - 1], "牛") : null,
    revealed_count: revealedCount,
    total_balls: total,
    reveal_interval_seconds: 25,
    is_complete: revealedCount >= total,
    next_reveal_at: revealedCount >= total ? "" : beijing(revealStartSec + 25 * revealedCount),
  }
}

// ── 1. 只开放 1 个号码：画 1 个、继续轮询、不通知父页 ─────────────────────
{
  const panel = loadPanel({ payload: slicedPayload({ revealedCount: 1 }) })
  panel.__hooks.setNow(T)
  await settle()
  await panel.__hooks.load({ revealOnLoad: true })
  await settle()
  const state = panel.__hooks.state()
  if (state.painted !== 1) throw new Error(`server-paced reveal must paint exactly 1 ball, got ${state.painted}`)
  if (!state.polling) throw new Error("server-paced reveal must keep polling until 7 balls")
  if (!state.serverPaced) throw new Error("panel must remember it is on the server-paced path")
  if (state.windowEndsAtSec !== T + 210) {
    throw new Error(`reveal window must end at anchor+210s, got ${state.windowEndsAtSec - T}`)
  }
  if (state.badgeText !== "开奖中...") throw new Error(`badge must show reveal-in-progress, got ${state.badgeText}`)
  // 揭示没结束前只允许通知「父页门控」，不允许通知「揭示完成」。
  const completions = panel.notifications.filter((message) => message.kind === "legacy-draw-reveal-complete")
  if (completions.length !== 0) throw new Error("must not notify completion before 7 balls")
  const gates = panel.notifications.filter((message) => message.kind === "legacy-draw-reveal-gate")
  if (gates.length < 1) throw new Error("panel must announce the parent reveal gate while revealing")
  if (gates.some((gate) => gate.unlockAt !== T + 150)) {
    throw new Error(`parent gate must unlock at anchor+150s, got ${gates.map((gate) => gate.unlockAt - T)}`)
  }
}

// ── 2. 服务端是权威：本地时钟已过 60 秒也不补看未开放的号码 ────────────────
{
  const panel = loadPanel({ payload: slicedPayload({ revealedCount: 1, revealStartSec: T - 60 }) })
  panel.__hooks.setNow(T)
  await settle()
  await panel.__hooks.load({ revealOnLoad: true })
  await settle()
  const state = panel.__hooks.state()
  if (state.painted !== 1) {
    throw new Error(`server revealed_count is authoritative: expect 1 painted, got ${state.painted}`)
  }
  if (state.revealedCount !== 1) throw new Error(`revealedCount must equal the server value, got ${state.revealedCount}`)
}

// ── 3. 第 7 个号码到位：画满、停轮询、只通知一次 ──────────────────────────
{
  const panel = loadPanel({ payload: slicedPayload({ revealedCount: 6 }) })
  panel.__hooks.setNow(T)
  await settle()
  await panel.__hooks.load({ revealOnLoad: true })
  await settle()
  if (panel.__hooks.state().painted !== 6) throw new Error("expect 6 painted balls before the last one")
  if (!panel.__hooks.state().polling) throw new Error("must keep polling while the 7th ball is missing")

  panel.__hooks.setPayload(slicedPayload({ revealedCount: 7 }))
  await panel.__hooks.load({ reveal: true, background: true, preserveWhenPending: true })
  await settle()
  const state = panel.__hooks.state()
  if (state.painted !== 7) throw new Error(`expect 7 painted balls when complete, got ${state.painted}`)
  if (state.polling) throw new Error("polling must stop once the issue is complete")
  if (state.serverPaced) throw new Error("server-paced flag must clear once complete")
  const completions = panel.notifications.filter((message) => message.kind === "legacy-draw-reveal-complete")
  if (completions.length !== 1) throw new Error(`expect exactly one completion notification, got ${completions.length}`)
}

// ── 4. 老后端（没有 revealed_count）只给部分号码：也要继续轮询 ─────────────
{
  const legacy = {
    current_issue: "2026282",
    draw_time: beijing(T - 10),
    reveal_start: beijing(T - 10),
    result_balls: [ball("01"), ball("02")],
    special_ball: null,
  }
  const panel = loadPanel({ payload: legacy })
  panel.__hooks.setNow(T)
  await settle()
  await panel.__hooks.load({ revealOnLoad: true })
  await settle()
  const state = panel.__hooks.state()
  if (state.painted !== 2) throw new Error(`legacy partial payload must paint its 2 balls, got ${state.painted}`)
  if (!state.polling) throw new Error("legacy partial payload must keep polling instead of freezing")
}

// ── 5. 窗口结束仍不足 7 个号码：保留已开放的球 + 提示同步中 ────────────────
{
  const panel = loadPanel({ payload: slicedPayload({ revealedCount: 3 }) })
  panel.__hooks.setNow(T)
  await settle()
  await panel.__hooks.load({ revealOnLoad: true })
  await settle()
  if (panel.__hooks.state().painted !== 3) throw new Error("expect 3 painted balls before the stall")

  panel.__hooks.expireWindow()
  panel.__hooks.fireIntervals()
  await settle()
  const state = panel.__hooks.state()
  if (state.painted !== 3) throw new Error(`stalled reveal must keep the 3 revealed balls, got ${state.painted}`)
  if (state.polling) throw new Error("polling must stop after the reveal window")
  if (state.badgeText !== "开奖结果同步中...") {
    throw new Error(`stalled reveal must show the sync-pending text, got ${state.badgeText}`)
  }
  if (state.serverPaced) throw new Error("stalled reveal must leave the server-paced state")
}

// ── 6. 等新期时收到「上一期的完整结果」（快照/短缓存陈旧）不能停掉轮询 ────────
// 真实事故（2026-10-04 23:52 本地演练）：倒计时归零 → 开始轮询新期，但开盘瞬间
// 缓存仍返回上一期的完整 7 码；若把它当成「本轮已收尾」，轮询会被停止，
// 面板会永远停在上一期。这里固定：旧期完整载荷必须保持待揭示空态并继续轮询。
{
  const nowSec = Math.floor(Date.now() / 1000)
  const panel = loadPanel({
    // 上一期的完整结果：reveal_start 已过揭示窗口（真实事故里 271 的 23:45 锚点，
    // 到 23:52 已经过去 420 秒），所以不会被当成「正在揭示的当期」。
    payload: slicedPayload({ issue: "2026271", revealedCount: 7, revealStartSec: nowSec - 600 }),
    deadline: { next_issue: "2026272", next_time: nowSec - 1 },
  })
  panel.__hooks.setNow(nowSec)
  panel.__hooks.setRevealTarget("2026272")
  await settle()
  await panel.__hooks.load({ revealOnLoad: true })
  await settle()
  let state = panel.__hooks.state()
  if (!state.polling) throw new Error("stale complete payload must not stop the reveal polling loop")
  if (state.painted !== 0) {
    throw new Error(`waiting for a newer issue must keep the pending empty state, got ${state.painted} painted`)
  }

  // 新期数据到达：画服务端已开放的号码，并继续轮询到 7 个。
  panel.__hooks.setPayload(slicedPayload({ issue: "2026272", revealedCount: 2 }))
  await panel.__hooks.load({ reveal: true, background: true, preserveWhenPending: true })
  await settle()
  state = panel.__hooks.state()
  if (state.painted !== 2) throw new Error(`new issue must paint its 2 revealed balls, got ${state.painted}`)
  if (!state.polling) throw new Error("new issue must keep polling until complete")
  if (state.revealedCount !== 2) throw new Error(`revealedCount must follow the server, got ${state.revealedCount}`)
}

// ── 7. 手动刷新不得清屏（2026-10-05 用户反馈）────────────────────────────
// 修复前：揭示轮询中点击「刷新」会 showPendingIssue() 把 7 个球清成 `--`，
// 然后直接返回等下一次 5 秒轮询，用户看到"号码全没了、几秒后才回来"。
// 现在固定：刷新期间当前号码原地保留，新载荷与倒计时并发获取，原地替换。
{
  const nowSec = Math.floor(Date.now() / 1000)
  const panel = loadPanel({
    payload: slicedPayload({ issue: "2026275", revealedCount: 7, revealStartSec: nowSec - 600 }),
    deadline: { next_issue: "2026276", next_time: nowSec + 60 },
  })
  panel.__hooks.setNow(nowSec)
  await settle()
  await panel.__hooks.load({ revealOnLoad: true })
  await settle()
  if (panel.__hooks.state().painted !== 7) throw new Error("baseline must show 7 balls")

  // 刷新进行中（尚未 await）：号码必须还在屏幕上。
  const refresh = panel.__hooks.manualRefresh()
  if (panel.__hooks.state().painted !== 7) {
    throw new Error("manual refresh must not clear the rendered balls")
  }
  await refresh
  await settle()
  if (panel.__hooks.state().painted !== 7) {
    throw new Error("manual refresh must keep the balls after it settles")
  }

  // 倒计时已过、新期待揭示：刷新同样不清屏，并继续轮询等新期。
  panel.__hooks.setDeadline({ next_issue: "2026276", next_time: nowSec - 1 })
  await panel.__hooks.manualRefresh()
  await settle()
  let state = panel.__hooks.state()
  if (state.painted !== 7) {
    throw new Error(`refresh while waiting for a new issue must keep the balls, got ${state.painted}`)
  }
  if (!state.polling) throw new Error("refresh while waiting for a new issue must keep polling")

  // 新期号码到达 → 原地替换成新期已开放的号码。
  panel.__hooks.setPayload(slicedPayload({ issue: "2026276", revealedCount: 3 }))
  await panel.__hooks.load({ reveal: true, background: true, preserveWhenPending: true })
  await settle()
  state = panel.__hooks.state()
  if (state.painted !== 3) throw new Error(`new issue must replace the old balls once it arrives, got ${state.painted}`)
}

// ── 8. 诚实展示 + 后端控节奏（2026-10-05）───────────────────────────────
// 需求：前端只老实展示后端下发的号码（收到几个画几个、按后端顺序），
// 不等待 7 个齐全再轮播；下一次拉取按后端 next_reveal_at 排程。
{
  const nowSec = Math.floor(Date.now() / 1000)
  // 后端只说 "已开放 2 个"，但实际下发了 3 个球（缓存/版本差异）→ 前端照实画 3 个。
  const honest = slicedPayload({ issue: "2026280", revealedCount: 2, revealStartSec: nowSec })
  honest.result_balls = [...honest.result_balls, ball("22")]
  const panel = loadPanel({ payload: honest })
  panel.__hooks.setNow(nowSec)
  await settle()
  await panel.__hooks.load({ revealOnLoad: true })
  await settle()
  let state = panel.__hooks.state()
  if (state.painted !== 3) {
    throw new Error(`panel must display every ball the backend sent, got ${state.painted} of 3`)
  }
  if (state.badgeText !== "开奖中...") throw new Error("reveal must start before all 7 balls arrive")

  // 按后端 next_reveal_at 排下一次拉取（不该等固定 5 秒轮询）。
  const expectedDelay = (Date.parse(`${honest.next_reveal_at.replace(" ", "T")}+08:00`) / 1000 - nowSec) * 1000 + 400
  const delays = panel.__hooks.timeouts()
  if (!delays.some((delay) => Math.abs(delay - expectedDelay) <= 2000)) {
    throw new Error(`panel must schedule the next fetch from next_reveal_at (≈${expectedDelay}ms), got ${JSON.stringify(delays)}`)
  }

  // 同一期内短缓存回退（先 3 个、后只回 1 个）不得把已展示的球抹掉。
  const stale = slicedPayload({ issue: "2026280", revealedCount: 1, revealStartSec: nowSec })
  panel.__hooks.setPayload(stale)
  await panel.__hooks.load({ reveal: true, background: true, preserveWhenPending: true })
  await settle()
  state = panel.__hooks.state()
  if (state.painted !== 3) {
    throw new Error(`same-issue payload regression must not remove displayed balls, got ${state.painted}`)
  }
}

console.log("kj panel server-paced reveal contract passed")
