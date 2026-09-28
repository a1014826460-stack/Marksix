/**
 * 开奖揭示锚点契约 — frontend/public/vendor/shengshi8800/kj/local.html
 * ---------------------------------------------------------------
 * 揭示起点必须是「号码首次对外可用的时刻」(reveal_start，后端开盘瞬间写定，
 * 全局唯一)：刷新接着时间线走不重放，不同浏览器同一时刻进度一致；
 * 旧数据没有 reveal_start 时退回 draw_time。预测遮罩门(ajax_interceptor.js)
 * 必须使用同一锚点，保证面板与遮罩同步解锁。
 */
import fs from "node:fs"

const panel = fs.readFileSync("frontend/public/vendor/shengshi8800/kj/local.html", "utf8")
const interceptor = fs.readFileSync(
  "frontend/public/vendor/shengshi8800/static/js/ajax_interceptor.js",
  "utf8",
)

// 1. 面板必须存在统一锚点解析器，且 reveal_start 优先于 draw_time。
if (!panel.includes("function _revealStartRaw(payload)")) {
  throw new Error("panel has no unified reveal-start resolver")
}
const resolverStart = panel.indexOf("function _revealStartRaw(payload) {")
const resolverBody = panel.slice(resolverStart, panel.indexOf("}", resolverStart))
if (resolverBody.indexOf("payload.reveal_start") > resolverBody.indexOf("payload.draw_time")) {
  throw new Error("panel resolver must prefer reveal_start over draw_time")
}

// 2. 三处消费方（窗口判定 / 揭示起点 / 父页门控）都必须走统一解析器。
for (const token of [
  "parseBeijingDateTimeToSeconds(_revealStartRaw(payload))",
]) {
  const hits = panel.split(token).length - 1
  if (hits < 3) {
    throw new Error(`panel uses the unified resolver ${hits} time(s), expected >= 3`)
  }
}
if (/parseBeijingDateTimeToSeconds\(payload\s*&&\s*payload\.draw_time/.test(panel)) {
  throw new Error("panel still anchors the reveal window directly on draw_time")
}

// 3. 遮罩门与面板同锚点：优先 reveal_start，退回 draw_time。
if (!interceptor.includes("payload.reveal_start || payload.draw_time")) {
  throw new Error("ajax interceptor gate is not anchored on reveal_start")
}

console.log("kj panel reveal anchor contract passed")
