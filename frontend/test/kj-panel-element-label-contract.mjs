/**
 * 开奖模块小字「五行/生肖」契约 — frontend/public/vendor/shengshi8800/kj/local.html
 * ---------------------------------------------------------------
 * 用户要求：开奖球下方的小字由「生肖」改为「五行/生肖」（25 号球 → 原「马」改为「金/马」）。
 * 七个球（6 正码 + 第 7 个特码）都要有号码五行；五行只能取服务端 /api/latest-draw 的
 * 每个球（含特码）自带的 `element`，权威表是
 *   backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS
 *   = frontend/lib/element-number-groups.ts
 * （**不是** fixed_data 里 sign='五行肖' 的生肖五行，那份只有 48 码且结论不同）。
 *
 * 本契约分两层：
 *   1. 静态（纯磁盘）：面板里存在「五行/生肖」拼装逻辑，且不得再用裸 ball.zodiac
 *      直接覆盖小字节点；element 缺失/为空时只显示生肖（不臆造五行）；小字节点只能由
 *      拼装函数产出（保证所有渲染分支——定时揭示、轮序发布、空态 fillEmpty、错误态——
 *      都走同一条规则）。
 *   2. 行为（真实 Chrome，本机静态服务 + 桩 /api/latest-draw 与 /api/next-draw-deadline）：
 *      覆盖五个五行的 7 球样本、线上真实一期样本、未开奖空态、缺 element/缺生肖回退、
 *      定时揭示进行中；断言七个球的小字（含特码）分别是「五行/生肖」、空态不出现「/」、
 *      小字不换行不溢出、居中与字号层级不变、小字不带任何高亮样式。
 *   3. 号码五行表本身（49 码全覆盖且互斥、与后端权威源零漂移）由
 *      frontend/test/element-number-groups-contract.mjs 负责；这里只做一次便宜的交叉核对。
 *
 * 不连公网、不连数据库。Chrome 起不来时可 `KJ_PANEL_ELEMENT_LABEL_SKIP_BROWSER=1`
 * 只跑静态层（CI 无浏览器时用）。
 *
 * 运行：node frontend/test/kj-panel-element-label-contract.mjs
 */
import assert from "node:assert/strict"
import { spawn, spawnSync } from "node:child_process"
import fs from "node:fs"
import http from "node:http"
import os from "node:os"
import path from "node:path"

const PANEL = "frontend/public/vendor/shengshi8800/kj/local.html"
const ELEMENT_TABLE = "frontend/lib/element-number-groups.ts"
const AUTHORITY_CONTRACT = "frontend/test/element-number-groups-contract.mjs"
const WEB_ROOT = "frontend/public"
const CHROME =
  process.env.KJ_PANEL_ELEMENT_LABEL_CHROME ||
  process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ||
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
const ELEMENTS = ["金", "木", "水", "火", "土"]

// ── 1. 静态断言：小字必须由「五行/生肖」拼装函数产出 ──────────────────────
const panel = fs.readFileSync(PANEL, "utf8")

const BUILDER_SIGNATURE = "function ballSubLabelText(ball) {"
assert.ok(panel.includes(BUILDER_SIGNATURE), `面板缺少「五行/生肖」拼装函数 ${BUILDER_SIGNATURE}`)
const builderAt = panel.indexOf(BUILDER_SIGNATURE)
const builderEnd = panel.indexOf("\n      }", builderAt)
assert.ok(builderEnd > builderAt, "拼装函数没有被正常闭合")
const builder = panel.slice(builderAt, builderEnd)
assert.ok(builder.includes("ball.element"), "拼装函数必须读取号码五行 element")
assert.ok(builder.includes("ball.zodiac"), "拼装函数必须读取生肖 zodiac")
assert.ok(
  /elementText\s*\+\s*"\/"\s*\+\s*zodiacText/.test(builder),
  "拼装函数必须产出「五行/生肖」形式（element + '/' + zodiac）",
)
assert.ok(
  /elementText\s*\|\|\s*zodiacText/.test(builder),
  "拼装函数必须支持「只有五行」或「只有生肖」的回退（不臆造、不残留分隔符）",
)

// 生肖（小字）节点的每一处赋值都必须走拼装函数，否则会漏掉某个渲染分支。
const subAssignments = [...panel.matchAll(/zodiacNode\.textContent\s*=\s*([^;\n]+);/g)].map((m) => m[1].trim())
assert.ok(subAssignments.length >= 1, "面板里找不到小字节点的赋值")
for (const rhs of subAssignments) {
  assert.ok(
    rhs.includes("ballSubLabelText("),
    `小字节点被绕过拼装函数直接赋值（五行会丢失）: zodiacNode.textContent = ${rhs}`,
  )
}
assert.ok(
  !/zodiacNode\.textContent\s*=\s*ball\s*&&\s*ball\.zodiac/.test(panel),
  "面板仍然用裸 ball.zodiac 直接覆盖生肖节点（小字里没有五行）",
)
assert.ok(
  !/zodiacNode\.textContent\s*=\s*String\(ball\.zodiac\)/.test(panel),
  "面板仍然直接写 String(ball.zodiac)（小字里没有五行）",
)

// ── 2. 号码五行表交叉核对（权威漂移由 element-number-groups-contract.mjs 负责）──
const tableSource = fs.readFileSync(ELEMENT_TABLE, "utf8")
const tableBlock = /export const ELEMENT_NUMBER_GROUPS[\s\S]*?=\s*\{([\s\S]*?)\n\}/.exec(tableSource)
assert.ok(tableBlock, `${ELEMENT_TABLE}: 找不到 ELEMENT_NUMBER_GROUPS 常量表`)
const groups = {}
for (const match of tableBlock[1].matchAll(/(金|木|水|火|土)\s*:\s*\[([^\]]*)\]/g)) {
  groups[match[1]] = [...match[2].matchAll(/"(\d{2})"/g)].map((m) => m[1])
}
assert.deepEqual(
  Object.keys(groups).sort(),
  [...ELEMENTS].sort(),
  `${ELEMENT_TABLE}: 号码五行必须是 金/木/水/火/土 五组`,
)
const allCodes = Object.values(groups).flat()
assert.equal(allCodes.length, 49, `${ELEMENT_TABLE}: 号码五行必须恰好 49 码`)
assert.equal(new Set(allCodes).size, 49, `${ELEMENT_TABLE}: 号码五行必须互斥（出现重复号码）`)
assert.deepEqual(
  [...allCodes].sort(),
  Array.from({ length: 49 }, (_, index) => String(index + 1).padStart(2, "0")),
  `${ELEMENT_TABLE}: 号码五行必须覆盖 01-49`,
)
const elementOf = (code) => Object.keys(groups).find((element) => groups[element].includes(code))
const authorityContractSource = fs.readFileSync(AUTHORITY_CONTRACT, "utf8")
assert.ok(
  /Array\.from\(\{\s*length:\s*49\s*\}/.test(authorityContractSource) &&
    /互不重叠|互斥/.test(authorityContractSource),
  `${AUTHORITY_CONTRACT} 必须先覆盖「01-49 全覆盖 + 互不重叠」的后端权威比对（本契约不重复实现）`,
)

// ── 3. 行为样本 ─────────────────────────────────────────────────────────
// 线上真实一期（2026-09-28 实测）：
//   curl.exe -s "https://www.tw8800.com/api/latest-draw?lottery_type=3"
// 七个球（含特码）element 全部非空。号码与生肖是**那一期的真实开奖**（不变）；
// element 由权威号码五行表派生，2026-09-29 该表整体改判为「新表」（相对上一版 25 码换组，
// `new(x) = old(x-1)`、01 归水），所以下面这一列 element 已按新表重算：
//   36→土 32→火 39→木 12→金 25→木 33→火 35→金（旧表依次为 土 火 火 金 金 金 土）。
// 七个球不再覆盖五行全集（这是真实一期的固有分布），五行走遍由下面的 five-elements 场景负责。
const LIVE_PAIRS = [
  ["36", "羊", "土", "blue"],
  ["32", "猪", "火", "green"],
  ["39", "龙", "木", "green"],
  ["12", "羊", "金", "red"],
  ["25", "马", "木", "blue"],
  ["33", "狗", "火", "green"],
  ["35", "猴", "金", "red"], // 特码
]
for (const [code, zodiac, element] of LIVE_PAIRS) {
  assert.equal(elementOf(code), element, `线上样本自洽：${code} 的号码五行应是 ${element}（号码五行与年份无关）`)
}

// 号码生肖随农历年滚动（2026 = 马年），所以**不写死年份**：号码 1/13/25/37/49 同肖、
// 2/14/26/38 同肖…（按 (code-1) mod 12 分组），每组在 12 生肖循环里依次递降。
// 先证明线上实测的七对号码/生肖都落在同一个循环上（唯一解），再用它生成合成样本；
// 跨年后只要换一期线上样本，本契约自动跟着走。
const ZODIAC_ORDER = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
const ZODIAC_DESCENDING = [...ZODIAC_ORDER].reverse()
const zodiacGroup = (code) => (Number(code) - 1) % 12
const liveOffsets = new Set(
  LIVE_PAIRS.map(([code, zodiac]) => {
    const index = ZODIAC_DESCENDING.indexOf(zodiac)
    assert.ok(index >= 0, `线上样本：${zodiac} 不是合法生肖`)
    return (index - zodiacGroup(code) + 12) % 12
  }),
)
assert.equal(
  liveOffsets.size,
  1,
  `线上实测的号码/生肖必须落在同一个 12 生肖循环上（当前样本自相矛盾：${JSON.stringify(LIVE_PAIRS)}）`,
)
const ZODIAC_OFFSET = [...liveOffsets][0]
const zodiacOfCode = (code) => ZODIAC_DESCENDING[(zodiacGroup(code) + ZODIAC_OFFSET) % 12]
for (const [code, zodiac] of LIVE_PAIRS) {
  assert.equal(zodiacOfCode(code), zodiac, `生肖循环自洽：${code} 应是 ${zodiac}`)
}
const ballOf = (code, extra = {}) => ({
  value: code,
  zodiac: zodiacOfCode(code),
  color: extra.color || "red",
  element: elementOf(code),
  ...extra,
})
const labelOf = (code) => `${elementOf(code)}/${zodiacOfCode(code)}`

// 六个正码 + 第 7 个特码覆盖五个五行（element 由权威表派生，注释按新表重算）。
const FIVE_ELEMENT_CODES = ["01", "03", "07", "13", "05", "25"] // 水 火 土 金 金 木
const FIVE_ELEMENT_SPECIAL = "49" // 火
assert.deepEqual(
  [...new Set([...FIVE_ELEMENT_CODES, FIVE_ELEMENT_SPECIAL].map(elementOf))].sort(),
  [...ELEMENTS].sort(),
  "五行走遍样本必须覆盖金木水火土（含特码）",
)

const payloadOf = (balls, special) => ({
  current_issue: "2026271",
  // 历史有效锚点配合接口权威 server_now，保证全排字号样本已合法完成揭示。
  draw_time: "2026-01-01 00:00:00",
  reveal_start: "2026-01-01 00:00:00",
  result_balls: balls,
  ...(special ? { special_ball: special } : {}),
})

const SCENARIOS = [
  {
    id: "five-elements",
    title: "五行走遍（6 正码 + 第 7 个特码）",
    payload: payloadOf(
      FIVE_ELEMENT_CODES.map((code, index) => ballOf(code, { color: ["red", "blue", "green"][index % 3] })),
      ballOf(FIVE_ELEMENT_SPECIAL, { color: "red" }),
    ),
    expectPainted: 7,
    expected: [...FIVE_ELEMENT_CODES, FIVE_ELEMENT_SPECIAL].map(labelOf),
    viewports: [320, 360, 480, 900],
  },
  {
    id: "live-2026271",
    title: "线上真实一期 2026271（7 球 element 实测非空）",
    payload: payloadOf(
      LIVE_PAIRS.slice(0, 6).map(([code, zodiac, element, color]) => ({ value: code, zodiac, element, color })),
      (() => {
        const [code, zodiac, element, color] = LIVE_PAIRS[6]
        return { value: code, zodiac, element, color }
      })(),
    ),
    expectPainted: 7,
    expected: LIVE_PAIRS.map(([code, zodiac, element]) => `${element}/${zodiac}`),
    viewports: [480],
  },
  {
    id: "unopened",
    title: "未开奖空态",
    payload: { current_issue: "2026272" },
    expectPainted: 0,
    expected: Array.from({ length: 7 }, () => "--"),
    viewports: [480],
  },
  {
    id: "missing-fields",
    title: "缺 element / 缺生肖 / element 空串回退",
    payload: payloadOf(
      [
        { value: "25", zodiac: "马", color: "blue" }, // 无 element → 只显示生肖
        { value: "03", element: "金", color: "green" }, // 无生肖 → 只显示五行
        { value: "07", zodiac: "鼠", element: "", color: "red" }, // element 空串 → 只显示生肖
        null,
        null,
        null,
      ],
      null,
    ),
    expectPainted: 3,
    expected: ["马", "金", "鼠", "--", "--", "--", "--"],
    viewports: [480],
  },
  {
    id: "revealing",
    title: "定时揭示进行中（锚点 30 秒前 → 已揭示 2 球）",
    payload: payloadOf(
      FIVE_ELEMENT_CODES.map((code) => ballOf(code)),
      ballOf(FIVE_ELEMENT_SPECIAL),
    ),
    revealStartOffsetSec: -30,
    expectPainted: 2,
    expected: [...FIVE_ELEMENT_CODES.slice(0, 2).map(labelOf), ...Array.from({ length: 5 }, () => "--")],
    viewports: [480],
  },
]

// ── 4. 真实浏览器行为断言 ────────────────────────────────────────────────
const BALL_IDS = ["m1", "m2", "m3", "m4", "m5", "m6", "s1"]
const SUB_IDS = ["m1x", "m2x", "m3x", "m4x", "m5x", "m6x", "s1x"]
const WRAP_IDS = ["w1", "w2", "w3", "w4", "w5", "w6", "w7"]

const PROBE_SCRIPT = `
(function () {
  var SCENARIO = "__SCENARIO__";
  var EXPECT_PAINTED = __EXPECT_PAINTED__;
  var startedAt = Date.now();
  var lastKey = "";
  var stableTicks = 0;
  var posted = false;

  function snap() {
    var con = document.querySelector(".new-KJ-TabBox-box-con");
    var balls = [];
    for (var i = 0; i < 7; i++) {
      var valueEl = document.getElementById(__BALL_IDS__[i]);
      var subEl = document.getElementById(__SUB_IDS__[i]);
      var wrapEl = document.getElementById(__WRAP_IDS__[i]);
      var subStyle = subEl ? getComputedStyle(subEl) : null;
      var valueStyle = valueEl ? getComputedStyle(valueEl) : null;
      var rangeRects = 0;
      if (subEl && subEl.textContent) {
        var range = document.createRange();
        range.selectNodeContents(subEl);
        rangeRects = range.getClientRects().length;
      }
      var wrapRect = wrapEl ? wrapEl.getBoundingClientRect() : null;
      var subRect = subEl ? subEl.getBoundingClientRect() : null;
      var valueRect = valueEl ? valueEl.getBoundingClientRect() : null;
      var h2 = valueEl ? valueEl.parentElement : null;
      var h2Rect = h2 ? h2.getBoundingClientRect() : null;
      balls.push({
        value: valueEl ? String(valueEl.textContent || "").trim() : null,
        sub: subEl ? String(subEl.textContent || "").trim() : null,
        subHtml: subEl ? String(subEl.innerHTML || "") : null,
        subLines: rangeRects,
        subFontSize: subStyle ? parseFloat(subStyle.fontSize) : null,
        subColor: subStyle ? subStyle.color : null,
        subBackground: subStyle ? subStyle.backgroundColor : null,
        subWidth: subRect ? subRect.width : null,
        subBottom: subRect ? subRect.bottom : null,
        valueFontSize: valueStyle ? parseFloat(valueStyle.fontSize) : null,
        wrapHeight: wrapRect ? wrapRect.height : null,
        wrapWidth: wrapRect ? wrapRect.width : null,
        wrapBottom: wrapRect ? wrapRect.bottom : null,
        valueCenterOffset: valueRect && wrapRect
          ? Math.abs((valueRect.left + valueRect.right) / 2 - (wrapRect.left + wrapRect.right) / 2)
          : null,
        h2CenterOffset: h2Rect && wrapRect
          ? Math.abs((h2Rect.left + h2Rect.right) / 2 - (wrapRect.left + wrapRect.right) / 2)
          : null,
        subClass: subEl ? String(subEl.className || "") : null
      });
    }
    return {
      scenario: SCENARIO,
      issue: (function () { var el = document.getElementById("q"); return el ? String(el.textContent || "").trim() : null; })(),
      viewportWidth: window.innerWidth,
      containerWidth: con ? con.getBoundingClientRect().width : null,
      statusText: (function () { var el = document.getElementById("statusText"); return el ? String(el.textContent || "").trim() : null; })(),
      balls: balls
    };
  }

  function post(data) {
    if (posted) return;
    posted = true;
    try {
      fetch("/__probe?scenario=" + encodeURIComponent(SCENARIO), {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(data)
      });
    } catch (error) {}
  }

  function tick() {
    var data = snap();
    var painted = data.balls.filter(function (b) { return b.value && b.value !== "--"; }).length;
    var key = JSON.stringify(data.balls) + "|" + data.issue + "|" + data.statusText;
    if (key === lastKey) stableTicks += 1; else { stableTicks = 0; lastKey = key; }
    var elapsed = Date.now() - startedAt;
    if (elapsed > 400 && stableTicks >= 3 && painted >= EXPECT_PAINTED) { post(data); return; }
    if (elapsed > 12000) { post(data); return; }
    setTimeout(tick, 120);
  }
  tick();
})();
`

const panelHtml = fs.readFileSync(PANEL, "utf8")
const bodyClose = panelHtml.lastIndexOf("</body>")
assert.ok(bodyClose > 0, "面板 HTML 缺少 </body>，无法注入探针")

const state = { payload: null, revealStartOffsetSec: null, activePanel: null }
const pendingProbes = new Map()
let serverPort = 0

function deadlineStub() {
  const nowSec = Math.floor(Date.now() / 1000)
  return {
    current_issue: "2026271",
    next_issue: "2026272",
    next_time: nowSec + 3600, // 未来 → 不会进入揭示轮询
    server_time: nowSec,
  }
}

function payloadWithRevealAnchor() {
  const payload = { ...(state.payload || {}), server_now: Math.floor(Date.now() / 1000) }
  if (state.revealStartOffsetSec !== null && state.revealStartOffsetSec !== undefined) {
    const target = new Date((Math.floor(Date.now() / 1000) + state.revealStartOffsetSec) * 1000)
    // 面板解析的是「北京墙上时刻」，用 +8h 的 UTC 串表达同一个瞬间。
    payload.reveal_start = new Date(target.getTime() + 8 * 3600 * 1000)
      .toISOString()
      .slice(0, 19)
      .replace("T", " ")
  }
  return payload
}

const CONTENT_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".gif": "image/gif",
  ".ico": "image/x-icon",
}

const webRoot = path.resolve(WEB_ROOT)

function sendJson(res, value) {
  res.writeHead(200, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" })
  res.end(JSON.stringify(value))
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://127.0.0.1")
  if (url.pathname === "/api/latest-draw") {
    sendJson(res, payloadWithRevealAnchor())
    return
  }
  if (url.pathname === "/api/next-draw-deadline") {
    sendJson(res, deadlineStub())
    return
  }
  if (url.pathname === "/__probe" && req.method === "POST") {
    let body = ""
    req.on("data", (chunk) => {
      body += chunk
    })
    req.on("end", () => {
      const token = url.searchParams.get("scenario")
      const resolve = pendingProbes.get(token)
      if (resolve) {
        pendingProbes.delete(token)
        try {
          resolve(JSON.parse(body))
        } catch (error) {
          resolve({ parseError: String(error), raw: body.slice(0, 300) })
        }
      }
      res.writeHead(204)
      res.end()
    })
    return
  }
  if (url.pathname === "/__panel") {
    const token = url.searchParams.get("scenario")
    const panelForRun = state.activePanel && state.activePanel.token === token ? state.activePanel.html : panelHtml
    res.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" })
    res.end(panelForRun)
    return
  }
  if (url.pathname === "/__host") {
    // 十个站点都是以 iframe 引用共享面板：用宿主页把 iframe 钉到指定宽度，
    // 才能测到窄屏（Chrome 无头窗口最小宽度约 500px，直接 --window-size 测不到 360px）。
    const token = url.searchParams.get("scenario") || ""
    const width = Math.min(Math.max(Number(url.searchParams.get("w")) || 480, 240), 2000)
    res.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" })
    res.end(
      '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>kj-panel-host</title></head>' +
        '<body style="margin:0;padding:0;background:#fff">' +
        `<iframe src="/__panel?lottery_type=3&scenario=${encodeURIComponent(token)}" ` +
        `style="display:block;width:${width}px;height:900px;border:0"></iframe>` +
        "</body></html>",
    )
    return
  }
  const file = path.resolve(webRoot, `.${decodeURIComponent(url.pathname)}`)
  if (!file.startsWith(webRoot) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
    res.writeHead(404, { "content-type": "text/plain; charset=utf-8" })
    res.end("not found")
    return
  }
  res.writeHead(200, {
    "content-type": CONTENT_TYPES[path.extname(file)] || "application/octet-stream",
    "cache-control": "no-store",
  })
  res.end(fs.readFileSync(file))
})

function killChrome(child) {
  if (!child || child.killed) return
  try {
    if (process.platform === "win32") {
      spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" })
    } else {
      child.kill("SIGKILL")
    }
  } catch (error) {
    // 进程可能已自行退出。
  }
}

/** 启动一次 Chrome，等页面里的探针把快照 POST 回来。 */
async function collectScenario(scenario, viewport) {
  const token = `${scenario.id}@${viewport}`
  const probe = PROBE_SCRIPT.replace("__SCENARIO__", token)
    .replace("__EXPECT_PAINTED__", String(scenario.expectPainted))
    .replace("__BALL_IDS__", JSON.stringify(BALL_IDS))
    .replace("__SUB_IDS__", JSON.stringify(SUB_IDS))
    .replace("__WRAP_IDS__", JSON.stringify(WRAP_IDS))
  state.activePanel = {
    token,
    html: panelHtml.slice(0, bodyClose) + `<script>${probe}</script>\n` + panelHtml.slice(bodyClose),
  }

  const url = `http://127.0.0.1:${serverPort}/__host?scenario=${encodeURIComponent(token)}&w=${viewport}`
  const dataPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pendingProbes.delete(token)
      reject(
        new Error(
          `浏览器探针超时（${token}）：Chrome 未启动、未渲染或未回传快照。` +
            (lastStderr ? `Chrome stderr: ${lastStderr.slice(-400)}` : ""),
        ),
      )
    }, 25000)
    pendingProbes.set(token, (data) => {
      clearTimeout(timer)
      resolve(data)
    })
  })

  // 每个场景用独立 profile：既避免复用用户正在运行的 Chrome 实例，也保证
  // sessionStorage 里的开奖载荷缓存不会串场。
  const profileDir = fs.mkdtempSync(path.join(os.tmpdir(), "kj-element-label-"))
  const child = spawn(
    CHROME,
    [
      "--headless=new",
      "--disable-gpu",
      "--disable-extensions",
      "--disable-background-networking",
      "--disable-sync",
      "--no-first-run",
      "--no-default-browser-check",
      "--hide-scrollbars",
      "--mute-audio",
      `--user-data-dir=${profileDir}`,
      "--window-size=1200,980",
      url,
    ],
    { stdio: ["ignore", "ignore", "pipe"] },
  )
  lastStderr = ""
  child.stderr.on("data", (chunk) => {
    lastStderr += chunk.toString()
  })
  const exited = new Promise((resolve) => child.on("exit", (code) => resolve(code)))
  child.on("error", (error) => {
    lastStderr += String(error && error.message ? error.message : error)
  })

  try {
    return await dataPromise
  } finally {
    killChrome(child)
    await Promise.race([exited, new Promise((resolve) => setTimeout(resolve, 3000))])
    try {
      fs.rmSync(profileDir, { recursive: true, force: true })
    } catch (error) {
      // 临时 profile 清不掉不影响结论。
    }
  }
}

let lastStderr = ""

function verifyScenario(scenario, viewport, data) {
  const where = `${scenario.title}（${scenario.id}@${viewport}px）`
  assert.ok(!data.parseError, `${where}: 探针回传无法解析: ${JSON.stringify(data).slice(0, 300)}`)
  assert.ok(
    Math.abs(Number(data.viewportWidth) - viewport) <= 20,
    `${where}: 面板 iframe 实际宽度 ${data.viewportWidth}px 与目标 ${viewport}px 不符（该宽度的布局没被真正测到）`,
  )
  assert.deepEqual(
    data.balls.map((ball) => ball.sub),
    scenario.expected,
    `${where}: 七球小字必须是「五行/生肖」（第 7 个特码同样要有五行）`,
  )

  // 小字里的五行必须与号码一致（不是生肖五行）——直接用号码反查权威表。
  for (let index = 0; index < scenario.expected.length; index += 1) {
    const expected = scenario.expected[index]
    if (!expected.includes("/")) continue
    const [element, zodiac] = expected.split("/")
    assert.ok(ELEMENTS.includes(element), `${where}: 第 ${index + 1} 球「${expected}」的五行不合法`)
    assert.equal(
      element,
      elementOf(data.balls[index].value),
      `${where}: 第 ${index + 1} 球号码 ${data.balls[index].value} 的号码五行应是「${elementOf(data.balls[index].value)}」，` +
        `实际显示「${element}」`,
    )
    assert.ok(zodiac.length > 0, `${where}: 第 ${index + 1} 球缺少生肖`)
  }

  // 空态/未揭示：不得出现分隔符残留（「／--」「马/」「/--」）。
  for (const ball of data.balls) {
    assert.ok(!/[/／]\s*--|--\s*[/／]/.test(ball.sub || ""), `${where}: 小字出现「/--」残留: ${ball.sub}`)
    assert.ok(!/[/／]$/.test(ball.sub || ""), `${where}: 小字出现尾部分隔符: ${ball.sub}`)
    if (ball.sub === "--") {
      assert.equal(ball.value, "--", `${where}: 空态号码与小字必须同时是 --（号码 ${ball.value}）`)
    }
  }

  const painted = data.balls.filter((ball) => ball.value !== "--").length
  assert.equal(painted, scenario.expectPainted, `${where}: 已渲染号码数应为 ${scenario.expectPainted}`)

  // 命中高亮规则不变：小字是纯文本、默认色 #333 白底，不得带高亮标签/类。
  for (const ball of data.balls) {
    assert.ok(!String(ball.subHtml).includes("<"), `${where}: 小字被包了 HTML 标签（可能引入高亮）: ${ball.subHtml}`)
    assert.ok(!/FFFF00|yellow/i.test(String(ball.subHtml) + String(ball.subClass)), `${where}: 小字带高亮标记`)
    assert.equal(ball.subColor, "rgb(51, 51, 51)", `${where}: 小字颜色被改动（应保持 #333）: ${ball.subColor}`)
    assert.equal(ball.subBackground, "rgb(255, 255, 255)", `${where}: 小字底色被改动: ${ball.subBackground}`)
    assert.ok(!/red|yellow/i.test(String(ball.subClass || "")), `${where}: 小字 class 出现高亮样式: ${ball.subClass}`)
    assert.equal(ball.subClass, "whsx", `${where}: 小字 class 被改动: ${ball.subClass}`)
  }

  // 布局：小字一行不换行、不超出球身、不撑高球身；号码仍居中；字号层级不变。
  for (let index = 0; index < data.balls.length; index += 1) {
    const ball = data.balls[index]
    if (ball.sub && ball.sub !== "--") {
      assert.equal(ball.subLines, 1, `${where}: 第 ${index + 1} 球小字「${ball.sub}」换行了（${ball.subLines} 行）`)
      assert.ok(
        ball.subWidth <= ball.wrapWidth + 0.5,
        `${where}: 第 ${index + 1} 球小字「${ball.sub}」宽 ${ball.subWidth.toFixed(1)}px 溢出球身 ${ball.wrapWidth.toFixed(1)}px`,
      )
      assert.ok(
        ball.subBottom <= ball.wrapBottom + 0.5,
        `${where}: 第 ${index + 1} 球小字底部 ${ball.subBottom.toFixed(1)}px 超出球身 ${ball.wrapBottom.toFixed(1)}px`,
      )
      assert.ok(
        ball.subFontSize < ball.valueFontSize,
        `${where}: 字号层级被破坏（小字 ${ball.subFontSize}px ≥ 号码 ${ball.valueFontSize}px）`,
      )
      assert.ok(ball.subFontSize <= 14, `${where}: 小字字号被放大到 ${ball.subFontSize}px`)
    }
    assert.ok(
      ball.valueCenterOffset === null || ball.valueCenterOffset <= 1.5,
      `${where}: 第 ${index + 1} 球号码不再居中（偏移 ${Number(ball.valueCenterOffset).toFixed(2)}px）`,
    )
    assert.ok(
      ball.h2CenterOffset === null || ball.h2CenterOffset <= 1.5,
      `${where}: 第 ${index + 1} 球号码容器不再居中（偏移 ${Number(ball.h2CenterOffset).toFixed(2)}px）`,
    )
    assert.ok(
      ball.wrapHeight <= 62,
      `${where}: 第 ${index + 1} 球球身被小字撑高（${Number(ball.wrapHeight).toFixed(1)}px > 61px）`,
    )
  }
}

async function main() {
  if (process.env.KJ_PANEL_ELEMENT_LABEL_SKIP_BROWSER === "1") {
    console.log("kj panel element label contract passed（静态层；已按环境变量跳过浏览器行为层）")
    return
  }
  assert.ok(fs.existsSync(CHROME), `找不到本机 Chrome: ${CHROME}（可用 KJ_PANEL_ELEMENT_LABEL_CHROME 覆盖）`)

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve))
  serverPort = server.address().port
  const report = []
  try {
    for (const scenario of SCENARIOS) {
      for (const viewport of scenario.viewports || [480]) {
        state.payload = scenario.payload
        state.revealStartOffsetSec =
          scenario.revealStartOffsetSec === undefined ? null : scenario.revealStartOffsetSec
        const data = await collectScenario(scenario, viewport)
        verifyScenario(scenario, viewport, data)
        const slack = data.balls
          .filter((ball) => ball.sub && ball.sub !== "--")
          .reduce((min, ball) => Math.min(min, ball.wrapWidth - ball.subWidth), Number.POSITIVE_INFINITY)
        report.push(
          `[browser] ${scenario.id}@${viewport}px（iframe ${data.viewportWidth}px）: ` +
            data.balls.map((ball) => ball.sub).join(" ") +
            `｜小字 ${data.balls[0].subFontSize}px < 号码 ${data.balls[0].valueFontSize}px` +
            (Number.isFinite(slack) ? `｜小字距球身最窄余量 ${slack.toFixed(1)}px（单行未溢出）` : ""),
        )
      }
    }
  } finally {
    await new Promise((resolve) => server.close(resolve))
  }

  for (const line of report) console.log(line)
  console.log("kj panel element label contract passed")
}

main().catch((error) => {
  console.error(String((error && error.message) || error))
  process.exitCode = 1
})
