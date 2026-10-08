/** Compare the real Python response gate and real shared HTML panel without HTTP or a database. */
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import vm from "node:vm"
import { spawnSync } from "node:child_process"
import { fileURLToPath } from "node:url"

const repoRoot = fileURLToPath(new URL("../../", import.meta.url))
const recoverySource = fs.readFileSync(path.join(repoRoot, "frontend/test/kj-panel-recovery-contract.mjs"), "utf8")
const harnessEnd = recoverySource.indexOf("const cases = []")
assert(harnessEnd > 0, "the existing panel recovery harness must expose its case boundary")
// Reuse its DOM, clock and fetch doubles while executing the current HTML script itself.
// The harness contains no reveal algorithm; that stays in the actual shared panel.
const harness = vm.runInNewContext(
  recoverySource.slice(0, harnessEnd).replace(/^import .*$/gm, "") + "\n;({ panel, settle, T, beijing })",
  { fs: { readFileSync: (file, encoding) => fs.readFileSync(path.resolve(repoRoot, file), encoding) },
    vm, assert, URLSearchParams, Intl, AbortController, console },
  { filename: "kj-panel-recovery-harness.mjs" },
)
const { panel, settle, T, beijing } = harness
const values = ["01", "02", "03", "04", "05", "06", "49"]
const ball = (value) => ({ value, color: "red", zodiac: "鼠", element: "金" })
function rawPayload({ source = 7, reported = source, start = beijing(T), planned = beijing(T), issue = "2026280" } = {}) {
  return {
    current_issue: issue, draw_time: planned, reveal_start: start,
    result_balls: values.slice(0, Math.min(6, source)).map(ball),
    special_ball: source === 7 ? ball(values[6]) : null,
    revealed_count: reported, total_balls: 7, reveal_interval_seconds: 25,
    is_complete: reported === 7, next_reveal_at: "",
  }
}
const cases = []
function add(name, now, expected, fields = {}, lotteryType = 3) {
  cases.push({ name, now, expected, payload: rawPayload(fields), lottery_type: lotteryType })
}
const boundaries = [[-1, 0], [-0.001, 0], [0, 1], [24, 1], [24.999, 1], [25, 2], [49, 2], [50, 3],
  [74, 3], [75, 4], [99, 4], [100, 5], [124, 5], [125, 6], [149, 6], [149.999, 6], [150, 7], [400, 7]]
for (const [elapsed, expected] of boundaries) {
  add(`ordinary anchor ${elapsed}s`, T + elapsed, expected)
  add(`early opened_at cannot beat planned ${elapsed}s`, T + elapsed, expected, { start: beijing(T - 120) })
  add(`late opened_at controls progress ${elapsed}s`, T + 5 + elapsed, expected, { start: beijing(T + 5) })
}
for (const source of [0, 1, 2, 3, 4, 5, 6, 7]) add(`source prefix ${source} caps late progress`, T + 400, source, { source })
for (const badBall of [null, {}, { value: "" }, { value: "  " }, "not-a-ball"]) {
  add(`source hole cannot shift the special slot: ${JSON.stringify(badBall)}`, T + 400, 2)
  cases.at(-1).payload.result_balls[2] = badBall
}
for (const source of [0, 1, 3, 5]) {
  add(`premature special stays hidden with ${source} regular slots`, T + 400, source, { source })
  cases.at(-1).payload.special_ball = ball(values[6])
}
for (const badSpecial of [null, {}, { value: "" }, { value: "  " }, "not-a-ball"]) {
  add(`invalid special stays in its seventh slot: ${JSON.stringify(badSpecial)}`, T + 400, 6)
  cases.at(-1).payload.special_ball = badSpecial
}
for (const regular of [[], [null, ball("02")], "invalid-list"]) {
  add("raw numbers without issue or valid anchor stay hidden", T + 400, 0, { issue: "", start: "invalid", planned: "" })
  cases.at(-1).payload.result_balls = regular
}
for (const hasSpecial of [true, false]) {
  add(`extra regular slot cannot stand in for special: ${hasSpecial}`, T + 400, hasSpecial ? 7 : 6)
  cases.at(-1).payload.result_balls.push(ball("31"))
  if (!hasSpecial) cases.at(-1).payload.special_ball = null
}
for (const preferred of ["invalid", "2026-02-30 22:32:00", "2026-13-01 22:32:00", "2026-10-07 24:00:00",
  "2026-10-07", "2026-2-3 2:3:4", "2026-10-07T22:32:00+08:00"]) {
  add(`invalid preferred cannot fall back: ${preferred}`, T + 400, 0, { start: preferred })
}
for (const preferred of [null, "", "  "]) add(`empty preferred uses draw_time: ${JSON.stringify(preferred)}`, T + 25, 2, { start: preferred })
add("missing both anchors is closed", T + 400, 0, { start: "", planned: "" })
add("valid canonical T separator", T + 25, 2, { start: beijing(T).replace(" ", "T"), planned: "" })
add("valid start can survive invalid planned time", T + 50, 3, { planned: "invalid" })
add("server interval metadata cannot speed Taiwan", T + 24, 1)
cases.at(-1).payload.reveal_interval_seconds = 1
for (const lotteryType of [1, 2]) {
  add(`type ${lotteryType} seven public balls at future planned time`, T, 7, { planned: beijing(T + 86400) }, lotteryType)
  add(`type ${lotteryType} legacy invalid preferred still returns all`, T, 7, { start: "invalid" }, lotteryType)
  add(`type ${lotteryType} source prefix remains immediate`, T, 3, { source: 3 }, lotteryType)
}
const lastYearAnchor = Date.parse("2026-12-31T23:59:00+08:00") / 1000
for (const [elapsed, expected] of [[125, 6], [150, 7]]) {
  add(`last-year issue crosses midnight at ${elapsed}s`, lastYearAnchor + elapsed, expected,
    { issue: "2026365", start: beijing(lastYearAnchor), planned: beijing(lastYearAnchor) })
  cases.at(-1).deadline = { current_issue: "2026365", next_issue: "2027001", next_time: lastYearAnchor + 86400 }
}
const newYearAnchor = Date.parse("2027-01-01T22:32:00+08:00") / 1000
add("new-year issue retains the same absolute 25-second rule", newYearAnchor + 25, 2,
  { issue: "2027001", start: beijing(newYearAnchor), planned: beijing(newYearAnchor) })
cases.at(-1).deadline = { current_issue: "2027001", next_issue: "2027002", next_time: newYearAnchor + 86400 }

const childEnv = { ...process.env, PYTHONUTF8: "1", PYTHONIOENCODING: "utf-8", PYTHONDONTWRITEBYTECODE: "1" }
for (const key of ["DATABASE_URL", "TEST_DATABASE_URL", "DATABASE_WRITE_URL", "DATABASE_READ_URL"]) delete childEnv[key]
const backend = spawnSync(process.env.PYTHON || "python", ["-c", `
import json, sys
from datetime import datetime
from core.time_utils import BEIJING_TZ
from public.draw_reveal import apply_reveal_slice
results = []
for case in json.load(sys.stdin):
    payload = case['payload']
    original_start = payload.get('reveal_start')
    output = apply_reveal_slice(payload, lottery_type_id=case['lottery_type'], now=datetime.fromtimestamp(case['now'], BEIJING_TZ))
    assert payload.get('reveal_start') == original_start, 'complete source payload must stay unchanged'
    results.append(output)
json.dump(results, sys.stdout)
`], { cwd: path.join(repoRoot, "backend/src"), env: childEnv, input: JSON.stringify(cases), encoding: "utf8" })
assert.equal(backend.status, 0, `real Python gate must run successfully: ${backend.stderr}`)
const backendResults = JSON.parse(backend.stdout)
assert.equal(backendResults.length, cases.length)

function shown(p) { return Array.from(p.values()).filter((value) => value !== "--") }
for (const [index, sample] of cases.entries()) {
  const output = backendResults[index]
  assert.equal(output.revealed_count, sample.expected, `backend: ${sample.name}`)
  const deadline = sample.deadline || { current_issue: sample.payload.current_issue, next_issue: "2026281", next_time: T + 86400 }
  const apiPanel = panel({ initial: output, now: sample.now, lotteryType: String(sample.lottery_type), deadline })
  await settle()
  assert.deepEqual(shown(apiPanel), values.slice(0, sample.expected), `actual backend response → HTML: ${sample.name}; ${JSON.stringify(apiPanel.sandbox.LotteryDrawDiagnostics.snapshot().records)}`)
  // Also deliver the raw, possibly premature complete response to exercise the independent browser gate.
  const defensivePanel = panel({ initial: sample.payload, now: sample.now, lotteryType: String(sample.lottery_type), deadline })
  await settle()
  assert.deepEqual(shown(defensivePanel), shown(apiPanel), `raw response → HTML has the same legal prefix: ${sample.name}`)
  if (sample.lottery_type === 3 && output.revealed_count > 0) {
    const record = defensivePanel.sandbox.LotteryDrawDiagnostics.snapshot().records.find((item) => item.event === "render")
    assert.equal(record.effective_reveal_start_sec, Date.parse(output.reveal_start.replace(" ", "T") + "+08:00") / 1000,
      `effective anchor agrees across languages: ${sample.name}`)
  }
}
console.log(`kj panel timing parity contract passed (${cases.length} absolute-time cases, backend + raw responses)`)
