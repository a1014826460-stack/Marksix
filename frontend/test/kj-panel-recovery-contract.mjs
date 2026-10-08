/** Exercise the shared panel's rollover, recovery, clock and diagnostic behavior without a network. */
import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

const html = fs.readFileSync("frontend/public/vendor/shengshi8800/kj/local.html", "utf8")
const script = /<script>([\s\S]*?)<\/script>/.exec(html)[1]
const T = Date.parse("2026-10-07T22:32:00+08:00") / 1000
const ids = ["m1", "m2", "m3", "m4", "m5", "m6", "s1"]
const beijing = (sec) => new Date((sec + 28800) * 1000).toISOString().replace("T", " ").slice(0, 19)
const CURRENT_DEADLINE = { current_issue: "2026280", next_issue: "2026281", next_time: T + 86400 }
function payload(issue, count, anchor = T + 1) {
  const values = issue === "2026279" ? ["41", "42", "43", "44", "45", "46", "47"] : ["01", "02", "03", "04", "05", "06", "49"]
  const ball = (value) => ({ value, color: "red", zodiac: "鼠", element: "金" })
  return {
    current_issue: issue, draw_time: beijing(anchor - 1), reveal_start: beijing(anchor),
    result_balls: values.slice(0, Math.min(6, count)).map(ball),
    special_ball: count === 7 ? ball(values[6]) : null,
    revealed_count: count, total_balls: 7, reveal_interval_seconds: 25,
    is_complete: count === 7, next_reveal_at: count === 7 ? "" : beijing(anchor + count * 25),
  }
}
async function settle() { for (let i = 0; i < 40; i++) await Promise.resolve() }

function panel({ initial = payload("2026279", 7, T - 86400 + 5), now = T - 2, skew = 0, failLatest = false, holdLatest = false, holdDeadline = false, storage = new Map(), lotteryType = "3", noServerTime = false, deadline = { current_issue: "2026279", next_issue: "2026280", next_time: T } } = {}) {
  let clock = (now + skew) * 1000
  let elapsed = 0
  let timerId = 0
  const timers = new Map(), elements = new Map(), documentListeners = new Map(), windowListeners = new Map()
  const requests = [], messages = []
  const state = { payload: initial, deadline, fail: failLatest, failDeadline: false, hold: holdLatest, holdDeadline, active: 0, maxActive: 0, releases: [], deadlineReleases: [] }
  function on(map, type, fn) { map.set(type, [...(map.get(type) || []), fn]) }
  function element(id) {
    if (!elements.has(id)) {
      const listeners = new Map()
      elements.set(id, { id, textContent: "", innerHTML: "", className: "", style: {}, href: "",
        classList: { values: new Set(), add(v) { this.values.add(v) }, remove(v) { this.values.delete(v) }, contains(v) { return this.values.has(v) } },
        setAttribute() {}, removeAttribute() {}, addEventListener(type, fn) { on(listeners, type, fn) },
        fire(type) { for (const fn of listeners.get(type) || []) fn({ type }) },
      })
    }
    return elements.get(id)
  }
  function timer(fn, ms, repeat) {
    const id = ++timerId
    timers.set(id, { fn, ms, repeat, at: elapsed + ms })
    return id
  }
  const sandbox = {
    window: null,
    document: { visibilityState: "visible", hidden: false, getElementById: element, querySelector() { return null }, addEventListener(type, fn) { on(documentListeners, type, fn) } },
    location: { search: `?lottery_type=${lotteryType}` }, parent: { postMessage(message) { messages.push(message) } },
    addEventListener(type, fn) { on(windowListeners, type, fn) },
    sessionStorage: { getItem: (key) => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key) },
    setTimeout: (fn, ms) => timer(fn, ms, false), clearTimeout: (id) => timers.delete(id),
    setInterval: (fn, ms) => timer(fn, ms, true), clearInterval: (id) => timers.delete(id),
    Date: class extends Date { constructor(...args) { super(...(args.length ? args : [clock])) } static now() { return clock } },
    performance: { now: () => elapsed },
    URLSearchParams, Intl, Math, JSON, Promise, AbortController, console: { log() {} },
    fetch(url, options = {}) {
      requests.push({ url: String(url), at: clock, options })
      if (String(url).includes("next-draw-deadline")) return new Promise((resolve, reject) => {
        const deliver = () => state.failDeadline
          ? reject(new TypeError("Failed to fetch deadline"))
          : resolve({ ok: true, status: 200, json: async () => ({ ...state.deadline, server_time: noServerTime ? null : state.deadlineServerNow ?? Math.floor(clock / 1000) - skew }) })
        if (state.holdDeadline) {
          state.deadlineReleases.push(deliver)
          options.signal?.addEventListener("abort", () => reject(Object.assign(new Error("aborted"), { name: "AbortError" })), { once: true })
        } else deliver()
      })
      state.active++; state.maxActive = Math.max(state.maxActive, state.active)
      return new Promise((resolve, reject) => {
        const finish = () => state.active--
        const deliver = () => {
          finish()
          if (state.fail) return reject(new TypeError("Failed to fetch"))
          resolve({ ok: true, status: 200, headers: { get: () => "MISS" }, json: async () => ({ ...state.payload, server_now: noServerTime ? null : state.serverNow ?? Math.floor(clock / 1000) - skew }) })
        }
        if (state.hold) {
          state.releases.push(deliver)
          options.signal?.addEventListener("abort", () => { finish(); reject(Object.assign(new Error("aborted"), { name: "AbortError" })) }, { once: true })
        } else deliver()
      })
    },
  }
  sandbox.window = sandbox
  vm.runInNewContext(script, sandbox, { filename: "kj-local.html" })
  return {
    state, requests, storage, sandbox, messages,
    values: () => ids.map((id) => element(id).textContent), issue: () => element("q").textContent,
    badge: () => element("countdownBadge").textContent,
    latestCalls: () => requests.filter((r) => r.url.includes("latest-draw")).length,
    jump(ms) { clock += ms; elapsed += ms },
    jumpWall(ms) { clock += ms },
    async tick(ms) {
      clock += ms; elapsed += ms
      for (const [id, item] of [...timers]) {
        if (!timers.has(id) || item.at > elapsed) continue
        if (item.repeat) item.at = elapsed + item.ms
        else timers.delete(id)
        item.fn()
      }
      await settle()
    },
    async event(type) {
      const map = type === "visibilitychange" ? documentListeners : windowListeners
      for (const fn of map.get(type) || []) fn({ type, persisted: true })
      await settle()
    },
    async refresh() { element("refreshButton").fire("click"); await settle() },
  }
}

const cases = []
async function check(name, run) {
  try { await run(); cases.push({ name, ok: true }); console.log("PASS", name) }
  catch (error) { cases.push({ name, ok: false }); console.error("FAIL", name, error.message) }
}

for (const elapsed of [-1, 0, 24, 25, 49, 50, 124, 125, 149, 150, 400]) await check(`Taiwan rejects an erroneous complete seven-ball response at anchor${elapsed < 0 ? "" : "+"}${elapsed}s`, async () => {
  const p = panel({ initial: payload("2026280", 7, T), now: T + elapsed,
    deadline: { current_issue: "2026280", next_issue: "2026281", next_time: T + 86400 } }); await settle()
  const allowed = elapsed < 0 ? 0 : Math.min(7, Math.floor(elapsed / 25) + 1)
  assert.equal(p.values().filter((v) => v !== "--").length, allowed)
  assert.equal(p.messages.filter((m) => m.kind === "legacy-draw-reveal-complete").length, 0)
  if (allowed < 7) {
    assert(p.messages.some((m) => m.kind === "legacy-draw-reveal-gate" && m.unlockAt === T + 150))
    assert.equal(JSON.parse(p.storage.get("liuhecai:kj-local:draw:v1:3")).data.is_complete, false)
    const calls = p.latestCalls(); await p.tick(5000); assert(p.latestCalls() > calls, "false complete must keep polling")
  }
  const record = p.sandbox.LotteryDrawDiagnostics.snapshot().records.find((r) => r.event === "render")
  assert.equal(record.incoming_count, 7, "diagnostics must retain the raw backend count")
  assert.equal(record.rendered_count, allowed)
})

await check("Taiwan advances a retained full response at fixed absolute 25-second boundaries", async () => {
  const wrong = { ...payload("2026280", 7, T), reveal_interval_seconds: 1 }
  const p = panel({ initial: wrong, now: T, deadline: { current_issue: "2026280", next_issue: "2026281", next_time: T + 86400 } }); await settle()
  p.state.fail = true
  await p.tick(24999); assert.equal(p.values().filter((v) => v !== "--").length, 1)
  await p.tick(1); assert.equal(p.values().filter((v) => v !== "--").length, 2)
  await p.tick(124999); assert.equal(p.values().filter((v) => v !== "--").length, 6)
  await p.tick(1); assert.equal(p.values().filter((v) => v !== "--").length, 7)
  assert.equal(p.messages.filter((m) => m.kind === "legacy-draw-reveal-complete").length, 1)
})

await check("known issue deadline remains a reveal lower bound after it advances to tomorrow", async () => {
  const p = panel(); await settle(); await p.tick(2000)
  p.state.deadline = { current_issue: "2026280", next_issue: "2026281", next_time: T + 86400 }
  p.state.payload = payload("2026280", 7, T - 86400)
  await p.refresh()
  assert.equal(p.values().filter((v) => v !== "--").length, 1)
  assert(p.messages.some((m) => m.kind === "legacy-draw-reveal-gate" && m.issue === "2026280" && m.unlockAt === T + 150))
})

await check("a premature next-issue response preserves the old legal result until its deadline", async () => {
  const p = panel(); await settle()
  p.state.payload = payload("2026280", 7, T)
  await p.refresh()
  assert.equal(p.issue(), "279")
  assert.deepEqual(p.values(), ["41", "42", "43", "44", "45", "46", "47"])
  await p.tick(2000)
  assert.equal(p.issue(), "280")
  assert.deepEqual(p.values(), ["01", "--", "--", "--", "--", "--", "--"])
})

await check("the initial live response waits for its issue schedule before opening an early anchor", async () => {
  const p = panel({ initial: payload("2026280", 7, T - 86400), holdDeadline: true }); await settle()
  assert.deepEqual(p.values(), ["--", "--", "--", "--", "--", "--", "--"])
  p.state.deadlineReleases.shift()(); await settle()
  assert.deepEqual(p.values(), ["--", "--", "--", "--", "--", "--", "--"])
  await p.tick(2000)
  assert.deepEqual(p.values(), ["01", "--", "--", "--", "--", "--", "--"])
})

await check("a newly completed Taiwan issue refreshes tomorrow's deadline exactly once", async () => {
  const p = panel({ initial: payload("2026280", 7, T), now: T,
    deadline: { current_issue: "2026279", next_issue: "2026280", next_time: T } }); await settle()
  p.state.deadline = { current_issue: "2026280", next_issue: "2026281", next_time: T + 86400 }
  await p.tick(150000)
  const calls = p.requests.filter((r) => r.url.includes("next-draw-deadline")).length
  assert.equal(calls, 2)
  await p.tick(30000)
  assert(p.badge().includes("23:"), `expect tomorrow's countdown, got ${p.badge()}`)
  assert.equal(p.requests.filter((r) => r.url.includes("next-draw-deadline")).length, calls)
})

for (const bad of ["2026-02-30 22:32:00", "2026-13-01 22:32:00", "2026-10-07 24:00:00", "not-a-date"]) await check(`invalid reveal anchor is fail closed: ${bad}`, async () => {
  const p = panel({ initial: { ...payload("2026280", 7, T), reveal_start: bad }, now: T + 60, deadline: CURRENT_DEADLINE }); await settle()
  assert.deepEqual(p.values(), ["--", "--", "--", "--", "--", "--", "--"])
})

await check("missing clock evidence never opens Taiwan balls from the device clock", async () => {
  const p = panel({ initial: payload("2026280", 7, T), now: T + 400, noServerTime: true, deadline: CURRENT_DEADLINE }); await settle()
  assert.deepEqual(p.values(), ["--", "--", "--", "--", "--", "--", "--"])
})

await check("a valid raw anchor and clock cannot open balls without authoritative current-issue evidence", async () => {
  const p = panel({ initial: payload("2026280", 7, T), now: T + 400, deadline: {} }); await settle()
  assert.deepEqual(p.values(), ["--", "--", "--", "--", "--", "--", "--"])
  p.state.deadline = CURRENT_DEADLINE; await p.refresh()
  assert.deepEqual(p.values(), ["01", "02", "03", "04", "05", "06", "49"])
})

await check("missing anchor evidence preserves an already legal same-issue prefix", async () => {
  const p = panel({ initial: payload("2026280", 7, T), now: T + 26, deadline: CURRENT_DEADLINE }); await settle()
  p.state.payload = { ...payload("2026280", 7, T), reveal_start: "invalid" }; await p.refresh()
  assert.deepEqual(p.values(), ["01", "02", "--", "--", "--", "--", "--"])
})

await check("iframe rebuild restores only the legal prefix and cannot use cache age to advance it", async () => {
  const storage = new Map()
  const deadline = { current_issue: "2026280", next_issue: "2026281", next_time: T + 86400 }
  const p = panel({ initial: payload("2026280", 7, T), now: T + 24, storage, deadline }); await settle()
  assert.deepEqual(p.values(), ["01", "--", "--", "--", "--", "--", "--"])
  const rebuilt = panel({ initial: payload("2026280", 7, T), now: T + 24, skew: 2, storage, deadline: CURRENT_DEADLINE, holdLatest: true }); await settle()
  assert.deepEqual(rebuilt.values(), ["01", "--", "--", "--", "--", "--", "--"])
  const rebuiltLater = panel({ now: T + 90, storage, deadline, holdLatest: true }); await settle()
  assert.deepEqual(rebuiltLater.values(), ["01", "--", "--", "--", "--", "--", "--"])
})

for (const count of [0, 1]) await check(`a delayed deadline restores safe cached two balls after a shorter live prefix of ${count}`, async () => {
  const storage = new Map()
  const deadline = { current_issue: "2026280", next_issue: "2026281", next_time: T + 86400 }
  const original = panel({ initial: payload("2026280", 2, T), now: T + 26, storage, deadline }); await settle()
  const rebuilt = panel({ initial: payload("2026280", count, T), now: T + 90, storage, deadline, holdDeadline: true }); await settle()
  rebuilt.state.deadlineReleases.shift()(); await settle()
  assert.deepEqual(rebuilt.values(), ["01", "02", "--", "--", "--", "--", "--"])
})

await check("late safe-cache restoration cannot discard a newly received full raw payload", async () => {
  const storage = new Map()
  const deadline = { current_issue: "2026280", next_issue: "2026281", next_time: T + 86400 }
  panel({ initial: payload("2026280", 2, T), now: T + 26, storage, deadline }); await settle()
  const rebuilt = panel({ initial: payload("2026280", 7, T), now: T + 30, storage, deadline, holdDeadline: true }); await settle()
  rebuilt.state.deadlineReleases.shift()(); await settle()
  rebuilt.state.fail = true
  await rebuilt.tick(120000)
  assert.deepEqual(rebuilt.values(), ["01", "02", "03", "04", "05", "06", "49"])
})

await check("a shorter same-issue response cannot discard raw balls waiting for later legal boundaries", async () => {
  const p = panel({ initial: payload("2026280", 7, T), now: T, deadline: CURRENT_DEADLINE }); await settle()
  p.state.payload = payload("2026280", 1, T); await p.refresh()
  p.state.fail = true; await p.tick(150000)
  assert.deepEqual(p.values(), ["01", "02", "03", "04", "05", "06", "49"])
})

await check("a future anchor cannot replace legal current results when deadline is unavailable", async () => {
  const p = panel(); await settle()
  p.state.failDeadline = true; p.state.deadline = {}; p.state.payload = payload("2026280", 7, T + 100)
  await p.refresh()
  assert.equal(p.issue(), "279")
  assert.deepEqual(p.values(), ["41", "42", "43", "44", "45", "46", "47"])
})

await check("a premature future issue cannot discard the current issue's unopened raw balls", async () => {
  const p = panel({ initial: payload("2026280", 7, T), now: T, deadline: CURRENT_DEADLINE }); await settle()
  p.state.payload = payload("2026281", 7, T + 86400); await p.refresh()
  p.state.fail = true; await p.tick(25000)
  assert.equal(p.issue(), "280")
  assert.deepEqual(p.values(), ["01", "02", "--", "--", "--", "--", "--"])
})

await check("a malformed short regular prefix cannot move the special ball before its seventh slot", async () => {
  const wrong = payload("2026280", 7, T)
  wrong.result_balls = wrong.result_balls.slice(0, 2)
  const p = panel({ initial: wrong, now: T + 60, deadline: CURRENT_DEADLINE }); await settle()
  assert.deepEqual(p.values(), ["01", "02", "--", "--", "--", "--", "--"])
  const calls = p.latestCalls(); await p.tick(5000); assert(p.latestCalls() > calls)
})

await check("an empty value inside a declared complete payload cannot stop polling", async () => {
  const wrong = payload("2026280", 7, T)
  wrong.result_balls[2] = { value: "" }
  const p = panel({ initial: wrong, now: T + 400, deadline: CURRENT_DEADLINE }); await settle()
  assert.deepEqual(p.values(), ["01", "02", "--", "--", "--", "--", "--"])
  const calls = p.latestCalls(); await p.tick(5000); assert(p.latestCalls() > calls)
})

for (const slot of [2, 6]) await check(`a whitespace-only Taiwan ball in slot ${slot + 1} ends the valid prefix`, async () => {
  const wrong = payload("2026280", 7, T)
  if (slot === 6) wrong.special_ball = { value: "  " }
  else wrong.result_balls[slot] = { value: "  " }
  const p = panel({ initial: wrong, now: T + 400, deadline: CURRENT_DEADLINE }); await settle()
  assert.deepEqual(p.values(), slot === 6
    ? ["01", "02", "03", "04", "05", "06", "--"]
    : ["01", "02", "--", "--", "--", "--", "--"])
  const calls = p.latestCalls(); await p.tick(5000); assert(p.latestCalls() > calls)
})

await check("deadline clears old seven balls and rejects a cached old issue", async () => {
  const p = panel(); await settle()
  assert.deepEqual(p.values(), ["41", "42", "43", "44", "45", "46", "47"])
  await p.tick(2000)
  assert.equal(p.issue(), "280")
  assert.deepEqual(p.values(), ["--", "--", "--", "--", "--", "--", "--"])
  await p.tick(5000)
  assert.equal(p.issue(), "280")
  assert.deepEqual(p.values(), ["--", "--", "--", "--", "--", "--", "--"])
  p.state.payload = payload("2026280", 1)
  await p.tick(5000)
  assert.deepEqual(p.values(), ["01", "--", "--", "--", "--", "--", "--"])
  p.state.payload = payload("2026280", 2)
  await p.tick(16000)
  await p.refresh()
  assert.deepEqual(p.values(), ["01", "02", "--", "--", "--", "--", "--"])
  p.state.payload = payload("2026280", 1)
  await p.refresh()
  assert.deepEqual(p.values(), ["01", "02", "--", "--", "--", "--", "--"])
})

for (const first of ["latest", "deadline"]) await check(`authoritative current issue replaces an old complete response when ${first} arrives first`, async () => {
  const p = panel({ now: T + 200, holdLatest: first === "deadline", holdDeadline: first === "latest",
    deadline: { current_issue: "2026280", next_issue: "2026281", next_time: T + 86400 } }); await settle()
  if (first === "latest") {
    assert.equal(p.issue(), "", "the first response waits for the concurrent authoritative issue schedule")
    p.state.holdDeadline = false
    p.state.deadlineReleases.shift()()
  } else {
    p.state.hold = false
    p.state.releases.shift()()
  }
  await settle()
  assert.equal(p.issue(), "280", "wait for the authoritative current issue, never tomorrow's 281 or yesterday's 279")
  assert.deepEqual(p.values(), ["--", "--", "--", "--", "--", "--", "--"])
  p.state.payload = payload("2026280", 7)
  await p.tick(5000)
  assert.equal(p.issue(), "280")
  assert.deepEqual(p.values(), ["01", "02", "03", "04", "05", "06", "49"])
  assert.equal(p.state.maxActive, 1)
})

await check("an unfinished issue survives window expiry and failures until the final response", async () => {
  const p = panel({ initial: payload("2026280", 1), now: T + 1, deadline: { current_issue: "2026280", next_issue: "2026281", next_time: T + 86400 } }); await settle()
  p.state.fail = true
  await p.tick(250000)
  assert.deepEqual(p.values(), ["01", "--", "--", "--", "--", "--", "--"])
  const calls = p.latestCalls()
  await p.tick(5000)
  assert.equal(p.latestCalls(), calls + 1)
  p.state.fail = false; p.state.payload = payload("2026280", 7)
  await p.tick(5000)
  assert.deepEqual(p.values(), ["01", "02", "03", "04", "05", "06", "49"])
  const completedCalls = p.latestCalls()
  await p.tick(10000)
  assert.equal(p.latestCalls(), completedCalls)
  assert.equal(p.state.maxActive, 1)
})

for (const event of ["visibilitychange", "pageshow"]) await check(`${event} fetches current progress immediately after sleep without replay`, async () => {
  const p = panel({ initial: payload("2026280", 1), now: T + 1, deadline: { current_issue: "2026280", next_issue: "2026281", next_time: T + 86400 } }); await settle()
  p.jump(170000); p.state.payload = payload("2026280", 7)
  await p.event(event)
  assert.deepEqual(p.values(), ["01", "02", "03", "04", "05", "06", "49"])
  assert.equal(p.latestCalls(), 2)
})

await check("a failed deadline sync preserves the known rollover and retries the sync", async () => {
  const p = panel(); await settle()
  p.state.failDeadline = true
  await p.refresh()
  await p.tick(2000)
  assert.equal(p.issue(), "280")
  assert.deepEqual(p.values(), ["--", "--", "--", "--", "--", "--", "--"])
  const before = p.requests.filter((r) => r.url.includes("next-draw-deadline")).length
  p.state.failDeadline = false
  await p.tick(5000)
  assert.equal(p.requests.filter((r) => r.url.includes("next-draw-deadline")).length, before + 1)
  assert(p.sandbox.LotteryDrawDiagnostics.snapshot().records.some((r) => r.event === "error" && r.resource === "deadline"))
})

await check("server_now calibrates the next fetch even with a one-hour client clock error", async () => {
  const p = panel({ initial: payload("2026280", 1), now: T + 1, skew: 3600, deadline: CURRENT_DEADLINE }); await settle()
  assert.deepEqual(p.values(), ["01", "--", "--", "--", "--", "--", "--"])
  p.state.payload = payload("2026280", 2)
  await p.tick(25400)
  assert.deepEqual(p.values(), ["01", "02", "--", "--", "--", "--", "--"])
  const records = p.sandbox.LotteryDrawDiagnostics.snapshot().records
  assert(records.some((r) => r.event === "result" && r.response_server_now === T + 1))
})

await check("a cache timestamp from a previously incorrect client clock cannot hide the new issue", async () => {
  const storage = new Map([["liuhecai:kj-local:draw:v1:3", JSON.stringify({
    cachedAt: (T + 3600) * 1000,
    data: { ...payload("2026279", 7, T - 86400 + 5), server_now: T - 2 },
  })]])
  const p = panel({ storage, initial: payload("2026280", 1), now: T + 1, deadline: CURRENT_DEADLINE }); await settle()
  assert.equal(p.issue(), "280")
  assert.deepEqual(p.values(), ["01", "--", "--", "--", "--", "--", "--"])
  assert.equal(p.latestCalls(), 1)
})

await check("a completed issue never regresses through an older full or partial response", async () => {
  const p = panel({ initial: payload("2026280", 7), now: T + 200, deadline: { current_issue: "2026280", next_issue: "2026281", next_time: T + 86400 } }); await settle()
  p.state.payload = payload("2026279", 7, T - 86400 + 5)
  p.state.serverNow = T - 400
  await p.refresh()
  assert.equal(p.issue(), "280")
  assert.deepEqual(p.values(), ["01", "02", "03", "04", "05", "06", "49"])
  assert.equal(JSON.parse(p.storage.get("liuhecai:kj-local:draw:v1:3")).data.current_issue, "2026280")
  const oldResult = p.sandbox.LotteryDrawDiagnostics.snapshot().records.findLast((r) => r.event === "result" && r.incoming_issue === "2026279")
  assert.equal(oldResult.server_now, T + 200, "old issue must be rejected before its server clock can rewind the panel")
  assert.equal(oldResult.ignored, true)
  const notifications = p.messages.length
  p.state.payload = payload("2026279", 1, T + 200)
  p.state.serverNow = T + 200
  await p.refresh()
  assert.equal(p.messages.length, notifications, "an ignored partial old issue must not notify the parent reveal gate")
  assert.equal(p.issue(), "280")
})

await check("the first failed draw request retries every five seconds before the future deadline", async () => {
  const p = panel({ failLatest: true, now: T - 100 }); await settle()
  assert.equal(p.latestCalls(), 1)
  await p.tick(4000)
  assert.equal(p.latestCalls(), 1)
  await p.tick(1000)
  assert.equal(p.latestCalls(), 2)
  await p.tick(5000)
  assert.equal(p.latestCalls(), 3)
  p.state.fail = false
  await p.tick(5000)
  assert.equal(p.issue(), "279")
  assert.deepEqual(p.values(), ["41", "42", "43", "44", "45", "46", "47"])
  const calls = p.latestCalls()
  await p.tick(10000)
  assert.equal(p.latestCalls(), calls, "successful complete response must cancel the failure retry")
  assert.equal(p.state.maxActive, 1)
})

await check("trusted server time rejects stale metadata and keeps accepting same-second responses", async () => {
  const p = panel({ initial: payload("2026280", 1), now: T + 1, skew: -3600, deadline: CURRENT_DEADLINE }); await settle()
  p.state.payload = payload("2026280", 2)
  p.state.serverNow = T - 599
  await p.refresh()
  let result = p.sandbox.LotteryDrawDiagnostics.snapshot().records.findLast((r) => r.event === "result")
  assert.equal(result.server_now, T + 1, "same-issue stale clock cannot rewind trusted time")
  p.state.serverNow = T + 1
  await p.refresh()
  result = p.sandbox.LotteryDrawDiagnostics.snapshot().records.findLast((r) => r.event === "result")
  assert.equal(result.server_now, T + 1)
  p.state.serverNow = T // One second of integer rounding is tolerated without moving time back.
  await p.refresh()
  result = p.sandbox.LotteryDrawDiagnostics.snapshot().records.findLast((r) => r.event === "result")
  assert.equal(result.server_now, T + 1)
  await p.tick(5000)
  p.state.serverNow = T + 6
  await p.refresh()
  result = p.sandbox.LotteryDrawDiagnostics.snapshot().records.findLast((r) => r.event === "result")
  assert.equal(result.server_now, T + 6, "same-second responses must not stop the trusted clock advancing")
  assert.deepEqual(p.values(), ["01", "--", "--", "--", "--", "--", "--"])
  p.state.serverNow = T + 26
  await p.tick(20000)
  await p.refresh()
  assert.deepEqual(p.values(), ["01", "02", "--", "--", "--", "--", "--"])
})

await check("a device wall-clock jump cannot advance the trusted countdown", async () => {
  const p = panel(); await settle()
  p.state.serverNow = T - 1
  p.state.deadlineServerNow = T - 1
  p.jumpWall(3600000)
  await p.event("pageshow")
  assert.equal(p.issue(), "279", "the real server deadline is still one second in the future")
  assert.deepEqual(p.values(), ["41", "42", "43", "44", "45", "46", "47"])
  const result = p.sandbox.LotteryDrawDiagnostics.snapshot().records.findLast((r) => r.event === "result")
  assert.equal(result.server_now, T - 1)
  await p.tick(1000)
  assert.equal(p.issue(), "280", "monotonic elapsed time must still advance the countdown to its real deadline")
  assert.deepEqual(p.values(), ["--", "--", "--", "--", "--", "--", "--"])
})

await check("repeated same-second metadata cannot discard fractional monotonic elapsed time", async () => {
  const p = panel(); await settle()
  p.state.serverNow = T - 2
  p.state.deadlineServerNow = T - 2
  for (let i = 0; i < 5; i++) {
    await p.tick(400)
    await p.refresh()
  }
  assert.equal(p.issue(), "280", "trusted elapsed time must reach the deadline despite repeated integer clock samples")
  assert.deepEqual(p.values(), ["--", "--", "--", "--", "--", "--", "--"])
  assert(p.sandbox.LotteryDrawDiagnostics.snapshot().records.at(-1).server_now >= T)
})

await check("authoritative time catches up after sleep even if the monotonic clock paused", async () => {
  const p = panel({ initial: payload("2026280", 1), now: T + 1, deadline: { current_issue: "2026280", next_issue: "2026281", next_time: T + 86400 } }); await settle()
  // Some browsers pause performance.now during device sleep. A fresh API response advances its anchor.
  p.jumpWall(170000)
  p.state.payload = payload("2026280", 7)
  await p.event("pageshow")
  assert.equal(p.issue(), "280")
  assert.deepEqual(p.values(), ["01", "02", "03", "04", "05", "06", "49"])
  const result = p.sandbox.LotteryDrawDiagnostics.snapshot().records.findLast((r) => r.event === "result")
  assert.equal(result.server_now, T + 171)
})

await check("request timeout frees the polling lock and recovery events never overlap requests", async () => {
  const p = panel({ initial: payload("2026280", 1), now: T + 1 }); await settle()
  p.state.hold = true
  await p.tick(5000)
  await p.event("pageshow"); await p.event("visibilitychange")
  await p.tick(10000)
  assert.equal(p.state.maxActive, 1)
  assert.equal(p.latestCalls(), 3, "queued resume must fetch again after the timed-out request releases its lock")
  p.state.hold = false; p.state.payload = payload("2026280", 2)
  // The resumed request is already in flight; the recovered network delivers its response.
  p.state.releases.at(-1)()
  await settle()
  assert.deepEqual(p.values(), ["01", "--", "--", "--", "--", "--", "--"], "recovered payload remains time gated")
  assert(p.sandbox.LotteryDrawDiagnostics.snapshot().records.some((r) => r.event === "error" && r.error_kind === "AbortError"))
})

await check("diagnostics retain bounded metadata across iframe rebuilds without touching the draw cache", async () => {
  const storage = new Map()
  const p = panel({ initial: payload("2026280", 2), now: T + 30, storage }); await settle()
  p.state.payload = payload("2026280", 1); await p.refresh()
  p.state.fail = true; await p.tick(5000)
  const snapshot = p.sandbox.LotteryDrawDiagnostics.snapshot()
  assert(snapshot.records.some((r) => r.event === "render" && r.incoming_issue === "2026280" && r.incoming_count === 1 && r.rendered_issue === "2026280" && r.rendered_count === 2))
  assert(snapshot.records.some((r) => r.event === "error"))
  assert(snapshot.records.some((r) => r.event === "request" && Number(r.request_ts) > 0))
  assert.equal(JSON.stringify(snapshot).includes('"value"'), false)
  const drawCache = storage.get("liuhecai:kj-local:draw:v1:3")
  assert.equal(JSON.parse(drawCache).data.current_issue, "2026280")
  for (let i = 0; i < 110; i++) await p.tick(5000)
  assert(p.sandbox.LotteryDrawDiagnostics.snapshot().records.length <= 100)
  const retained = p.sandbox.LotteryDrawDiagnostics.snapshot().records
  const rebuilt = panel({ storage, now: T + 1000 }); await settle()
  assert(rebuilt.sandbox.LotteryDrawDiagnostics.snapshot().records.some((r) => r.event === "error" && retained.some((old) => old.client_time_ms === r.client_time_ms)))
  const other = panel({ storage, lotteryType: "2", now: T + 1000 }); await settle()
  assert.equal(other.sandbox.LotteryDrawDiagnostics.snapshot().records.some((r) => r.event === "error"), false)
})

assert.equal(cases.filter((c) => !c.ok).length, 0, "shared panel recovery contract failures")
console.log(`kj panel recovery contract passed (${cases.length} cases)`)
