import fs from "node:fs"
import ts from "typescript"

// 台湾通天网（www.twtongtian.com / site key `twjinniu`）【琴棋书画】(mode 26) 展示契约。
//
// 缺陷（用户报障）：线上把 3 个「艺」展开成了 9 个生肖显示，例如
//   `2026271期 琴棋书画 【羊,猴,猪,兔,蛇,鸡,虎,龙,马】 开 35猴对`
// 要求的上屏值是**艺名**（琴/棋/书/画，如 `画琴书`），而不是 9 个候选生肖；并且只把
// 特肖命中的那一个艺高亮。
//
// 真实 payload 形状（取自真实 `/api/public/site-page` 抓取，见
// `.codex-temp/site-page/twjinniu.json`，与后端
// `predict/categories/structured_mapping.py::format_qinqi_content` 一致）：
//   raw.title           = 艺名 CSV，按本期数据原文顺序，如 `画,琴,书` / `画,琴,棋`
//   raw.content         = 同一顺序展开的 9 个候选生肖，如 `羊,猴,猪,兔,蛇,鸡,虎,龙,马`
//   raw.qinqi_reference = `琴:兔蛇鸡　棋:鼠牛狗\n书:虎龙马　画:羊猴猪`（fixed_data 展示串）
//   prediction_text     = 9 个候选生肖（= content），**不是**艺名
//
// 本契约驱动真实导出入口 `getTwjinniuArticleDetail("7720")`（文章页渲染被复用的路径），
// 而不是断言源码文本。`splitPredictionTokens` 直接使用**真实**的
// `frontend/lib/prediction-contract.ts` 转译结果，避免手写 stub 与线上切片口径漂移。
//
// 反向验证：设置环境变量 `TWJINNIU_ARTICLES_FILE` 指向改动前的版本，
// 本契约必须 FAIL（见 twjinniu-qinqi-arts-contract 报告）。

const ARTICLES_FILE =
  process.env.TWJINNIU_ARTICLES_FILE || "frontend/lib/twjinniu-articles.ts"

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function compileModule(path) {
  return ts.transpileModule(fs.readFileSync(path, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
}

function toDataModule(source) {
  return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
}

// 真实的 `@/lib/prediction-contract`：只有 `import type`，转译后无外部依赖。
const contractStub = toDataModule(compileModule("frontend/lib/prediction-contract.ts"))

const sitesStub = toDataModule(
  "export function getSiteConfig() {" +
    "  return { siteKey: 'twjinniu', defaultWebId: 7, defaultLotteryTypeId: 3, domains: ['www.twtongtian.com'] }" +
    "}"
)

// 文章页只从 `getPublicSitePageData` 拿模块历史；开奖号 overlay 走
// `backendFetchJson('/public/draw-history')`，返回空即可（判定/特肖由行内 res_sx 提供）。
const backendStub = toDataModule(
  "export async function backendFetchJson() { return {} }" +
    "export async function getPublicSitePageData() {" +
    "  return { site: {}, draw: {}, modules: [{ default_modes_id: 26, history: globalThis.__qinqiRows || [] }] }" +
    "}"
)

const articlesModule = toDataModule(
  compileModule(ARTICLES_FILE)
    .replace('import "server-only";', "")
    .replace(/"@\/lib\/backend-api"/g, JSON.stringify(backendStub))
    .replace(/"@\/lib\/prediction-contract"/g, JSON.stringify(contractStub))
    .replace(/"@\/lib\/sites"/g, JSON.stringify(sitesStub))
)

const { getTwjinniuArticleDetail } = await import(articlesModule)

const QINQI_REFERENCE = "琴:兔蛇鸡　棋:鼠牛狗\n书:虎龙马　画:羊猴猪"
const ZODIAC_RE = /[鼠牛虎兔龙蛇马羊鸡狗豬龍馬雞免]/
const ART_RE = /^[琴棋书画]+$/
const HIGHLIGHT_RE = /<span style="background-color: #FFFF00">([\s\S]*?)<\/span>/g

function plain(html) {
  return String(html).replace(/<[^>]*>/g, "")
}

function highlights(html) {
  return Array.from(String(html).matchAll(HIGHLIGHT_RE), (match) => match[1])
}

function qinqiRow({ issue, title, content, resSx = "", resCode = "", opened, correct, reference = QINQI_REFERENCE }) {
  return {
    issue,
    year: "2026",
    term: issue.slice(4),
    prediction_text: content,
    result_text: "",
    image_url: "",
    is_opened: opened,
    is_correct: correct,
    source_web_id: 7,
    raw: { title, content, res_sx: resSx, res_code: resCode, qinqi_reference: reference },
  }
}

// ── 真实线上数据（4 期报障样本 + 2 期兜底/漂移保护样本）────────────────────
const CASES = [
  {
    // 报障原文第 1 期：未开奖，9 肖 {羊猴猪}{兔蛇鸡}{虎龙马} = 画+琴+书
    row: qinqiRow({
      issue: "2026271",
      title: "画,琴,书",
      content: "羊,猴,猪,兔,蛇,鸡,虎,龙,马",
      opened: false,
      correct: null,
    }),
    arts: "画琴书",
    hit: "",
    why: "2026271 未开奖：只上屏艺名 画琴书，零高亮",
  },
  {
    // 画,琴,棋；特肖=狗(棋) 命中
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
    why: "2026190 命中：特肖狗落在「棋」→ 只高亮棋",
  },
  {
    // 棋,琴,书；特肖=狗(棋) 命中，且「棋」在首位（顺序必须按数据原文，不得排序）
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
    why: "2026189 命中：顺序保持数据原文 棋琴书（不得重排成 琴棋书）",
  },
  {
    // 画,书,棋；特肖=蛇(琴) 不在本期三个艺里 → 未命中，零高亮
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
    // 兜底：title 缺失（历史/厂商行），只能从 9 肖反查艺名，仍不得上屏生肖
    row: qinqiRow({
      issue: "2026170",
      title: "",
      content: "羊,猴,猪,兔,蛇,鸡,虎,龙,马",
      opened: false,
      correct: null,
    }),
    arts: "画琴书",
    hit: "",
    why: "2026170 title 为空：按 fixed_data 分组反查仍得上屏 画琴书（不是 9 肖）",
  },
  {
    // 漂移保护：行自带 qinqi_reference 与常量表不同 → 以行自带说明为准
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

globalThis.__qinqiRows = CASES.map((item) => item.row)
const detail = await getTwjinniuArticleDetail("7720", { lotteryType: 3 })

assert(detail, "mode 26 文章页必须能取到详情")
assert(detail.status === "ok", `mode 26 详情状态应为 ok：${detail.status}`)
assert(detail.modeId === 26, `文章 7720 必须映射到 mode 26：${detail.modeId}`)
assert(
  detail.rows.length === CASES.length,
  `必须逐期渲染 ${CASES.length} 行：${detail.rows.length}`
)

const seenPrediction = new Set()
const report = []

CASES.forEach((testCase, index) => {
  const rendered = detail.rows[index]
  const { issue, why } = { issue: testCase.row.issue, why: testCase.why }
  const text = plain(rendered.predictionHtml)

  // 1) 上屏值必须是艺名，且顺序 = 数据原文顺序
  assert(ART_RE.test(text), `${why} —— 上屏值必须是琴棋书画艺名，实际「${text}」`)
  assert(text === testCase.arts, `${why} —— 期望「${testCase.arts}」，实际「${text}」`)
  assert(text.length === 3, `${why} —— 必须是 3 个艺：${text}`)

  // 2) 回归护栏：9 个生肖的裸列表不得再出现（报障原文）
  assert(
    !ZODIAC_RE.test(text),
    `${why} —— 不得把候选生肖上屏，实际「${text}」`
  )
  assert(
    !rendered.predictionHtml.includes(testCase.row.raw.content),
    `${why} —— 不得原样输出 {艺展开的 9 肖}：${testCase.row.raw.content}`
  )

  // 3) 高亮：只高亮命中的那一个艺；未命中/未开奖零高亮
  const marks = highlights(rendered.predictionHtml)
  if (testCase.hit) {
    assert(
      marks.length === 1,
      `${why} —— 命中时必须有且仅有一个高亮，实际 ${marks.length} 个：${rendered.predictionHtml}`
    )
    assert(marks[0] === testCase.hit, `${why} —— 期望高亮「${testCase.hit}」，实际「${marks[0]}」`)
    assert(
      text.includes(testCase.hit),
      `${why} —— 高亮的艺必须来自本期上屏值：${text}`
    )
  } else {
    assert(
      marks.length === 0,
      `${why} —— 未命中/未开奖必须零高亮，实际 ${JSON.stringify(marks)}`
    )
  }

  // 4) DOM/文本槽位拓扑不变：仍然只有一对【】，仍是 `NNN期 琴棋书画 【…】开 …`
  assert(
    (rendered.lineHtml.match(/【/g) || []).length === 1,
    `${why} —— 不得新增第二个【】槽位：${rendered.lineHtml}`
  )
  assert(
    (rendered.lineHtml.match(/】/g) || []).length === 1,
    `${why} —— 不得新增第二个【】槽位：${rendered.lineHtml}`
  )
  assert(
    new RegExp(
      `^<p>${issue}期 琴棋书画 【<span style="color: #2ecc71">`
    ).test(rendered.lineHtml),
    `${why} —— 行模板槽位必须保持原样：${rendered.lineHtml}`
  )

  seenPrediction.add(text)
  const shown = testCase.hit ? text.replace(testCase.hit, `[${testCase.hit}]`) : text
  report.push(`  ${issue}期 琴棋书画 【${shown}】 开 ${plain(rendered.resultHtml)} 高亮=${marks.length}`)
})

// 5) 防 S7 恒定：逐期展示值必须随数据变化（报障原文 271/270/269 三期完全相同就是恒定）
assert(
  seenPrediction.size >= 4,
  `逐期展示值必须随数据变化，实际只有 ${seenPrediction.size} 种：${[...seenPrediction].join(" / ")}`
)

// 6) 页面级：不得新增固定分组说明块（既有拓扑不动），也不得外泄原始 reference 串
assert(
  !detail.contentHtml.includes("qinqi_reference"),
  "正文不得外泄原始 qinqi_reference 字段"
)
assert(
  !detail.contentHtml.includes("琴:兔蛇鸡"),
  `mode 26 既有拓扑没有四艺分组说明块，不得新增：${detail.contentHtml.slice(0, 300)}`
)
assert(
  detail.contentHtml.includes("2026190期 琴棋书画 【<span"),
  "正文行仍必须嵌在既有槽位里"
)

// 7) 反向验证：改回旧口径（只上屏 title 且永不传 match）必须 FAIL —— 由
//    TWJINNIU_ARTICLES_FILE 指向旧版本时本文件即失败；这里额外断言旧口径确实不同。
assert(
  highlights(detail.rows[1].predictionHtml).length === 1,
  "旧口径（renderJoinedTokens(labels, \"\", \"\")）会让命中行零高亮，本契约必须能抓到"
)

console.log("twjinniu-qinqi-arts-contract: OK")
console.log(report.join("\n"))
console.log(
  `  逐期展示值 ${seenPrediction.size} 种：${[...seenPrediction].join(" / ")}（防 S7 恒定）`
)
