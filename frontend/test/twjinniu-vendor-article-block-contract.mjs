import fs from "node:fs"
import vm from "node:vm"

// 台湾通天网（www.twtongtian.com / site key `twjinniu`）**厂商首页**文章预测块的展示契约。
//
// 报障来源就是这条路径：`frontend/public/vendor/twjinniu/index.html` 里的内联脚本
// `formatPredictionLabel` + `buildArticleBlock` 直接把 `prediction_text`（= 按标签展开的
// 9 个候选生肖）上屏，并把它原样吐到 `【…】` 槽位：
//   `2026271期 琴棋书画 【羊,猴,猪,兔,蛇,鸡,虎,龙,马】 开 35猴对`
// 要求上屏的是**艺名**（琴/棋/书/画，如 `画棋书`），且只把特肖命中的那一个艺高亮。
//
// 测试方式沿用该站既有契约的「把真实源码取出来跑」思路：这里把 index.html 的内联脚本
// 放进 `node:vm`，配一个只实现读取面的假 DOM（getElementById / querySelector(All)）与
// fetch stub，驱动**真实**的 `applyModulePayload → buildArticlePredictionBlocks →
// buildArticleBlock` 全链路，然后从 `#twjinniu-article-blocks` 的 innerHTML 里断言渲染结果。
// 不做任何源码文本替换，因此断言的是真的会上线的那段逻辑。
//
// 反向验证：`TWJINNIU_VENDOR_INDEX` 指向改动前的 index.html 时必须 FAIL。

const INDEX_FILE =
  process.env.TWJINNIU_VENDOR_INDEX || "frontend/public/vendor/twjinniu/index.html"

const ARTICLE_BLOCK_HOST_ID = "twjinniu-article-blocks"
const QINQI_REFERENCE = "琴:兔蛇鸡　棋:鼠牛狗\n书:虎龙马　画:羊猴猪"
const ZODIAC_RE = /[鼠牛虎兔龙蛇马羊鸡狗豬龍馬雞免]/
const ART_RE = /^[琴棋书画]+$/
const HIGHLIGHT_OPEN = "<span style=background-color:#FFFF00>"
const HIGHLIGHT_RE = /<span style=background-color:#FFFF00>([\s\S]*?)<\/span>/g

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function extractInlineScript(html) {
  const scripts = Array.from(
    html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g),
    (match) => match[1]
  )
  const target = scripts.find((script) => script.includes("ARTICLE_MODULES"))
  assert(target, "index.html 里必须存在包含 ARTICLE_MODULES 的内联脚本")
  return target
}

// 只实现该脚本用到的读取面：getElementById 恒返回可写假元素，选择器返回空。
function createFakeDom() {
  const elements = new Map()
  function element(id) {
    if (!elements.has(id)) {
      elements.set(id, {
        id,
        innerHTML: "",
        className: "",
        src: "",
        style: {},
        classList: { add() {} },
        getAttribute() { return null },
        setAttribute() {},
        addEventListener() {},
      })
    }
    return elements.get(id)
  }
  return {
    elements,
    document: {
      getElementById: (id) => element(id),
      querySelector: () => null,
      querySelectorAll: () => [],
    },
  }
}

async function renderVendorArticleBlocks({ indexHtml, modules }) {
  const dom = createFakeDom()
  const sandbox = {
    console,
    URLSearchParams,
    document: dom.document,
    window: { location: { search: "" }, setTimeout: (handler) => handler() },
    fetch: (url) => {
      const isHomepage = String(url).includes("homepage-modules")
      const payload = isHomepage ? { modules: {} } : { data: { site_page: { modules } } }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(payload) })
    },
  }
  vm.createContext(sandbox)
  vm.runInContext(extractInlineScript(indexHtml), sandbox, {
    filename: `${INDEX_FILE}#inline-script`,
  })
  // 让 fetch().then().then() 两跳微任务全部结算。
  for (let i = 0; i < 4; i += 1) await new Promise((resolve) => setImmediate(resolve))
  return dom.elements.get(ARTICLE_BLOCK_HOST_ID).innerHTML
}

function plain(html) {
  return String(html).replace(/<[^>]*>/g, "")
}

function highlights(html) {
  return Array.from(String(html).matchAll(HIGHLIGHT_RE), (match) => match[1])
}

/**
 * 文章块/行的包裹标记直接从 index.html 源码取，避免测试手写标记串与模板漂移
 * （模板字符本身由下面的 startsWith / includes 断言单独把关）。
 */
function templateMarkers(indexHtml) {
  const blockOpen = (indexHtml.match(/'<div style=margin[^']*>'/) || [])[0]
  const rowOpen = (indexHtml.match(/'<p style=margin[^']*>'/) || [])[0]
  assert(blockOpen && rowOpen, "index.html 必须仍用 <div|<p style=margin…> 包裹文章块")
  return { blockOpen: blockOpen.slice(1, -1), rowOpen: rowOpen.slice(1, -1) }
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

function parseBlocks(containerHtml, markers) {
  const blocks = new Map()
  const rowRe = new RegExp(escapeRegExp(markers.rowOpen) + "[\\s\\S]*?<\\/p>", "g")
  const chunks = String(containerHtml).split(markers.blockOpen).slice(1)
  for (const chunk of chunks) {
    const titleMatch = chunk.match(
      /<font color=#FFFF00 face=楷体 style=font-size:18pt>([^<]*)<\/font>/
    )
    const rows = chunk.match(rowRe) || []
    if (rows.length) blocks.set(titleMatch ? titleMatch[1] : "", rows)
  }
  return blocks
}

/** 拆出预测槽位与结果槽位（模板里 】 与 开 之间保留既有空格）。 */
function splitRow(rowHtml) {
  const match = String(rowHtml).match(
    /【<span style=color:#2ecc71>([\s\S]*?)<\/span>】 开 ([\s\S]*?)<\/p>$/
  )
  assert(match, `行模板必须保持 【…】 开 … 槽位（含 】 后空格）：${rowHtml}`)
  return { prediction: match[1], result: match[2] }
}

function qinqiRow({ issue, title, content, resSx = "", resCode = "", opened, correct, reference = QINQI_REFERENCE }) {
  return {
    issue,
    prediction_text: content,
    is_opened: opened,
    is_correct: correct,
    raw: { title, content, res_sx: resSx, res_code: resCode, qinqi_reference: reference },
  }
}

// ── mode 26 真实线上数据（4 期报障样本 + 2 期兜底/漂移样本）──────────────────
const QINQI_CASES = [
  {
    row: qinqiRow({
      issue: "2026271",
      title: "画,琴,书",
      content: "羊,猴,猪,兔,蛇,鸡,虎,龙,马",
      opened: false,
      correct: null,
    }),
    arts: "画琴书",
    hit: "",
    why: "2026271 未开奖：上屏艺名 画琴书，零高亮",
  },
  {
    row: qinqiRow({
      issue: "2026190",
      title: "画,琴,棋",
      content: "羊,猴,猪,兔,蛇,鸡,鼠,牛,狗",
      resCode: "20,19,38,35,23,42,45",
      resSx: "猪,鼠,蛇,猴,猴,牛,狗",
      opened: true,
      correct: true,
    }),
    arts: "画琴棋",
    hit: "棋",
    why: "2026190 命中：特肖狗→棋，恰好 1 处高亮且等于命中的艺",
  },
  {
    row: qinqiRow({
      issue: "2026189",
      title: "棋,琴,书",
      content: "鼠,牛,狗,兔,蛇,鸡,虎,龙,马",
      resCode: "32,36,39,05,33,37,09",
      resSx: "猪,羊,龙,虎,狗,马,狗",
      opened: true,
      correct: true,
    }),
    arts: "棋琴书",
    hit: "棋",
    why: "2026189 命中：顺序保持数据原文 棋琴书（不得重排）",
  },
  {
    row: qinqiRow({
      issue: "2026181",
      title: "画,书,棋",
      content: "羊,猴,猪,虎,龙,马,鼠,牛,狗",
      resCode: "17,23,19,16,14,39,02",
      resSx: "虎,猴,鼠,兔,蛇,龙,蛇",
      opened: true,
      correct: false,
    }),
    arts: "画书棋",
    hit: "",
    why: "2026181 未命中：特肖蛇(琴) 不在 画书棋 内 → 零高亮",
  },
  {
    row: qinqiRow({
      issue: "2026170",
      title: "",
      content: "羊,猴,猪,兔,蛇,鸡,虎,龙,马",
      opened: false,
      correct: null,
    }),
    arts: "画琴书",
    hit: "",
    why: "2026170 title 为空：靠 qinqi_reference 反查仍上屏 画琴书（不是 9 肖）",
  },
  {
    row: qinqiRow({
      issue: "2026169",
      title: "",
      content: "兔,蛇,鸡,羊,猴,猪,鼠,牛,狗",
      opened: false,
      correct: null,
      reference: "琴:羊猴猪　棋:兔蛇鸡\n书:虎龙马　画:鼠牛狗",
    }),
    arts: "棋琴画",
    hit: "",
    why: "2026169 行自带 qinqi_reference 优先于兜底常量表",
  },
]

// ── 其它 mode：必须与旧口径逐字节一致 ────────────────────────────────────────
// 3tou（稳中三头, mode 12）：raw.title 是整句标题（现实中 mode 50 一字玄机就是这样），
// 该行不得被「四艺」逻辑劫持；标签仍按 formatPredictionLabel(JSON 数组) = `0头.2头`。
const OTHER_MODE_ROW = {
  issue: "2026190",
  prediction_text: '["0头|01,02,03,04,05,06,07,08,09", "2头|20,21,22,23,24,25,26,27,28,29"]',
  is_opened: true,
  is_correct: true,
  raw: {
    title: "晓色微茫开画卷",
    content: '["0头|01,02,03,04,05,06,07,08,09", "2头|20,21,22,23,24,25,26,27,28,29"]',
    res_code: "01,27,37,20,43,02,45",
    res_sx: "马,龙,马,猪,鼠,蛇,狗",
  },
}
// shuangbo（双波中特, mode 38）：title 是「标签形态」但**不是**四艺 → 仍按旧口径原样上屏。
const WAVE_MODE_ROW = {
  issue: "2026190",
  prediction_text: "红波,蓝波",
  is_opened: false,
  is_correct: null,
  raw: { title: "红波,蓝波", content: "红波,蓝波", res_code: "", res_sx: "" },
}

const indexHtml = fs.readFileSync(INDEX_FILE, "utf8")
const containerHtml = await renderVendorArticleBlocks({
  indexHtml,
  modules: [
    { mechanism_key: "qinqi", history: QINQI_CASES.map((item) => item.row) },
    { mechanism_key: "3tou", history: [OTHER_MODE_ROW] },
    { mechanism_key: "shuangbo", history: [WAVE_MODE_ROW] },
  ],
})

assert(containerHtml, "首页文章预测块容器必须有内容（内联脚本必须跑到 applyModulePayload）")
// 模板字符未变：块/行包裹标记必须仍是既有形态
assert(
  indexHtml.includes("'<div style=margin:8px 0>'") && indexHtml.includes("'<p style=margin:4px 0;text-align:center>'"),
  "index.html 的文章块/行包裹标记不得改动"
)
assert(indexHtml.includes("' 开 ' + resultHtml"), "】 与 开 之间的既有空格不得改动")
const blocks = parseBlocks(containerHtml, templateMarkers(indexHtml))

// ── 1) mode 26：上屏艺名 + 只高亮命中的艺 ──────────────────────────────────
const qinqiRows = blocks.get("琴棋书画")
assert(qinqiRows, `必须渲染出「琴棋书画」块：${[...blocks.keys()].join(" / ")}`)
assert(
  qinqiRows.length === QINQI_CASES.length,
  `琴棋书画必须逐期渲染 ${QINQI_CASES.length} 行：${qinqiRows.length}`
)

const seenPrediction = new Set()
const report = []

QINQI_CASES.forEach((testCase, index) => {
  const rowHtml = qinqiRows[index]
  const { issue, why, row } = { issue: testCase.row.issue, why: testCase.why, row: testCase.row }
  const slots = splitRow(rowHtml)
  const text = plain(slots.prediction)

  // 模板字符不变：槽位前缀与 `】 开 `（】 后有既有空格）
  const prefix =
    `<p style=margin:4px 0;text-align:center><span style=color:#0000FF>${issue}期</span> ` +
    `琴棋书画 【<span style=color:#2ecc71>`
  assert(rowHtml.startsWith(prefix), `${why} —— 行模板槽位必须保持原样：${rowHtml}`)
  assert(rowHtml.includes("</span>】 开 "), `${why} —— 】 与 开 之间的既有空格不得改动：${rowHtml}`)
  assert(rowHtml.endsWith("</p>"), `${why} —— 行必须以 </p> 收尾：${rowHtml}`)

  // 上屏值是艺名，顺序 = 数据原文顺序
  assert(ART_RE.test(text), `${why} —— 上屏值必须是琴棋书画艺名，实际「${text}」`)
  assert(text === testCase.arts, `${why} —— 期望「${testCase.arts}」，实际「${text}」`)

  // 回归护栏：不得再出现生肖裸列表（报障原文）
  assert(!ZODIAC_RE.test(text), `${why} —— 不得把候选生肖上屏，实际「${text}」`)
  assert(
    !rowHtml.includes(row.content),
    `${why} —— 不得原样输出 9 肖 content：${row.content}`
  )

  // 高亮：命中行恰好 1 处且等于命中艺；未命中/未开奖 0 处
  const marks = highlights(slots.prediction)
  if (testCase.hit) {
    assert(
      marks.length === 1,
      `${why} —— 命中行必须有且仅有 1 处高亮，实际 ${marks.length}：${slots.prediction}`
    )
    assert(marks[0] === testCase.hit, `${why} —— 期望高亮「${testCase.hit}」，实际「${marks[0]}」`)
  } else {
    assert(marks.length === 0, `${why} —— 未命中/未开奖必须 0 高亮，实际 ${JSON.stringify(marks)}`)
  }
  assert(
    (slots.prediction.match(/#FFFF00/g) || []).length === marks.length,
    `${why} —— 高亮标记数必须与高亮 span 数一致`
  )

  seenPrediction.add(text)
  report.push(
    `  ${issue}期 琴棋书画 【${testCase.hit ? text.replace(testCase.hit, `[${testCase.hit}]`) : text}】` +
      ` 开 ${plain(slots.result)} 高亮=${marks.length}`
  )
})

// 防 S7 恒定
assert(
  seenPrediction.size >= 4,
  `逐期展示值必须随数据变化，实际 ${seenPrediction.size} 种：${[...seenPrediction].join(" / ")}`
)

// ── 2) 其它 mode：与旧口径逐字节一致（不得被四艺逻辑劫持）──────────────────
const threeTouRows = blocks.get("稳中三头")
assert(threeTouRows, "必须渲染出「稳中三头」块")
const threeTou = splitRow(threeTouRows[0])
assert(
  plain(threeTou.prediction) === "0头.2头",
  `mode 12 落库 title 是整句标题时不得被当标签：实际「${plain(threeTou.prediction)}」`
)
assert(
  !threeTou.prediction.includes("#FFFF00"),
  `mode 12 旧口径无高亮，不得新增：${threeTou.prediction}`
)
assert(
  plain(threeTou.result).includes("45狗对"),
  `mode 12 结果槽位必须保持原样：${plain(threeTou.result)}`
)
report.push(`  2026190期 稳中三头 【${plain(threeTou.prediction)}】 开 ${plain(threeTou.result)} 高亮=0`)

const waveRows = blocks.get("双波中特")
assert(waveRows, "必须渲染出「双波中特」块")
const wave = splitRow(waveRows[0])
assert(
  plain(wave.prediction) === "红波,蓝波",
  `mode 38 标签形态但非四艺的 title 必须按旧口径原样上屏：实际「${plain(wave.prediction)}」`
)
assert(
  wave.prediction.match(/#FFFF00/g) === null,
  `mode 38 旧口径无高亮，不得新增：${wave.prediction}`
)
report.push(`  2026190期 双波中特 【${plain(wave.prediction)}】 开 ${plain(wave.result)} 高亮=0`)

console.log("twjinniu-vendor-article-block-contract: OK")
console.log(report.join("\n"))
console.log(`  逐期展示值 ${seenPrediction.size} 种：${[...seenPrediction].join(" / ")}（防 S7 恒定）`)
console.log("  其它 mode 未命中四艺分支，标签/高亮/结果槽位与旧口径一致")
