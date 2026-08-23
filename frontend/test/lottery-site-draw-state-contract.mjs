import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

const source = fs.readFileSync("frontend/public/vendor/_shared/lottery-site-draw-state.js", "utf8")
const context = { window: {} }
vm.runInNewContext(source, context)
const merge = context.window.LotterySiteDrawState.merge

let state = merge(null, { current_issue: "2026170", balls: [{ value: "05" }, { value: "08" }, { value: "12" }] })
state = merge(state, { current_issue: "2026170", balls: [{ value: "05" }, { value: "08" }, { value: "12" }, { value: "24" }] })
assert.deepEqual(Array.from(state.balls, (ball) => ball.value), ["05", "08", "12", "24"])

const old = state
const next = merge(old, { current_issue: "2026171", balls: [{ value: "01" }] })
assert.equal(next.current_issue, "2026171")
assert.deepEqual(Array.from(next.balls, (ball) => ball.value), ["01"])

const partial = merge(next, { current_issue: "2026171", balls: [{ value: "01" }, null, { value: "09" }] })
assert.deepEqual(Array.from(partial.balls, (ball) => ball && ball.value), ["01", undefined, "09"])
console.log("lottery-site-draw-state-contract: ok")
