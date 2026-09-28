// 五行口径契约（台湾创富网 www.twcf888.com）
//
// 覆盖栏目：精准五行（6104 / mode 53）、三行中特（6111 / mode 53）、4行4头（7623 / mode 482+483）。
//
// 回归背景：`frontend/lib/twcf888-articles.ts` 旧实现用 `pickMatchedPipeLabel`（正文里
// 每个五行标签后的**号码清单**）定位命中行，而历史落库的 mode 53/482 正文清单是按
// **生肖五行**（`public.fixed_data` sign='五行肖'）拼出来的，不是号码五行
// （= `backend/src/predict/common.py::ELEMENT_NUMBER_GROUPS` = `fixed_data` sign='五行'）。
// 两者对同一号码给出不同五行：
//   24 → 号码五行 木（生肖羊 → 生肖五行 土）
//   04 → 号码五行 金（兔 → 生肖五行 木）
//   45 → 号码五行 木（狗 → 生肖五行 土）
// 于是「号码五行命中却零黄底」或「黄底落在生肖五行那一行」。
//
// 本契约锁定：
//   1. 判定沿用接口 `is_correct`（后端 element 原子 = 号码五行）；
//   2. 高亮 = 特码**号码五行**对应的那一行，与判定同源；
//   3. 两种正文形态（号码五行清单 / 生肖五行清单）高亮一致 —— 口径不得依赖正文清单；
//   4. 反例：生肖五行 ∈ 预测行、号码五行 ∉ 预测行 → 零黄底。
//
// 运行：node frontend/test/twcf888-element-verdict-contract.mjs
import assert from "node:assert/strict"
import fs from "node:fs"
import ts from "typescript"

function compileModule(path) {
  return ts.transpileModule(fs.readFileSync(path, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
}

function toDataModule(source) {
  return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
}

const backendStub = toDataModule(
  "export async function getPublicSitePageData() {" +
    "  const table = globalThis.__twcf888Modules || {};" +
    "  return { modules: Object.keys(table).map((modeId) => ({" +
    "    id: Number(modeId), mechanism_key: 'm' + modeId, title: ''," +
    "    default_modes_id: Number(modeId), default_table: '', sort_order: 0, status: true," +
    "    history: (table[modeId] || []).map((row) => ({ ...row }))," +
    "  })) };" +
    "}"
)
const sitesStub = toDataModule(
  "export function getSiteConfig() { return { siteKey: 'twcf888', defaultWebId: 8, defaultLotteryTypeId: 3 } }"
)

const articlesModule = toDataModule(
  compileModule("frontend/lib/twcf888-articles.ts")
    .replace('import "server-only";', "")
    .replace(/"@\/lib\/backend-api"/g, JSON.stringify(backendStub))
    .replace(/"@\/lib\/sites"/g, JSON.stringify(sitesStub))
)

const { getTwcf888ArticleDetail } = await import(articlesModule)

function row({ term, content, resCode = "", resSx = "", opened = true, isCorrect = null }) {
  return {
    issue: `2026${term}`,
    year: "2026",
    term,
    prediction_text: content,
    result_text: "",
    is_opened: opened,
    is_correct: isCorrect,
    source_web_id: 8,
    raw: { content, res_code: resCode, res_sx: resSx, res_color: "" },
  }
}

async function render(articleId, modeRows) {
  globalThis.__twcf888Modules = modeRows
  const detail = await getTwcf888ArticleDetail(articleId, { lotteryType: 3 })
  assert(detail, `article ${articleId} must resolve`)
  assert.equal(detail.status, "ok", `article ${articleId} 必须走 live-module 路径`)
  return detail.contentHtml
}

function yellowSpans(html) {
  return [...html.matchAll(/<span style="background-color: #FFFF00">([^<]*)<\/span>/g)].map(
    (match) => match[1],
  )
}

// 未修复的 mode 53/482 正文（生肖五行清单，抄自
// backend/src/tests/unit/test_repair_mode53_element_content.py 的 LEGACY_53）。
const LEGACY_CONTENT_53 =
  '["土|03,06,09,12,15,18,21,24,27,30,33,36,39,42,45,48","木|04,05,16,17,28,29,40,41","水|07,08,19,20,31,32,43,44"]'
// 后端修复后的正文（号码五行清单，同上测试的 CANONICAL_53）。
const CANONICAL_CONTENT_53 =
  '["土|05,06,19,20,27,28,35,36,49","木|07,08,15,16,23,24,37,38,45,46","水|13,14,21,22,29,30,43,44"]'
// 四行（mode 482）：«土-木-水-金»。24 的号码五行 = 木（生肖五行土）。
const LEGACY_CONTENT_482 =
  '["土|03,06,09,12,15,18,21,24,27,30,33,36,39,42,45,48","木|04,05,16,17,28,29,40,41","水|07,08,19,20,31,32,43,44","金|10,11,22,23,34,35,46,47"]'

// ── 1. 精准五行（6104）/ 三行中特（6111）：267 期 «土木水» + 特码 24 → 只标黄「木」──
for (const articleId of ["6104", "6111"]) {
  const html = await render(articleId, {
    53: [
      row({
        term: "267",
        content: LEGACY_CONTENT_53,
        resCode: "05,11,19,31,42,07,24",
        resSx: "牛,马,狗,龙,猪,蛇,羊",
        isCorrect: true,
      }),
    ],
  })
  const line = html
  assert.deepEqual(
    yellowSpans(line),
    ["木"],
    `${articleId}: 24 的号码五行是木 → 只允许「木」黄底（生肖五行口径会点「土」）：\n${line}`,
  )
  assert.ok(line.includes("土-") && line.includes("水"), `${articleId}: 三行标签照旧上屏：\n${line}`)
  assert.ok(line.includes("24羊对"), `${articleId}: 判定沿用接口 is_correct=true → 对：\n${line}`)
}

// 同一期、后端修复后的号码五行正文：高亮必须一致（口径不依赖正文清单）。
for (const articleId of ["6104", "6111"]) {
  const html = await render(articleId, {
    53: [
      row({
        term: "267",
        content: CANONICAL_CONTENT_53,
        resCode: "05,11,19,31,42,07,24",
        resSx: "牛,马,狗,龙,猪,蛇,羊",
        isCorrect: true,
      }),
    ],
  })
  assert.deepEqual(
    yellowSpans(html),
    ["木"],
    `${articleId}: 修复后的正文同样只允许「木」黄底：\n${html}`,
  )
}

// 37（号码五行木、生肖马 → 生肖五行火）是另一类分歧：正文旧清单把 37 写在【火】。
const html37 = await render("6111", {
  53: [
    row({
      term: "270",
      content: LEGACY_CONTENT_53,
      resCode: "05,11,19,31,42,07,37",
      resSx: "牛,马,狗,龙,猪,蛇,马",
      isCorrect: true,
    }),
  ],
})
assert.deepEqual(yellowSpans(html37), ["木"], `37 的号码五行是木 → 黄底必须落在【木】：\n${html37}`)

// ── 2. 反例：生肖五行 ∈ 三行，但号码五行 ∉ 三行 → 零黄底 + 错 ──────────
// 04 的号码五行 = 金（不在«土木水»）；旧正文把它写在【木】组（兔 → 木肖）。
const htmlMiss = await render("6104", {
  53: [
    row({
      term: "266",
      content: LEGACY_CONTENT_53,
      resCode: "05,11,19,31,42,07,04",
      resSx: "牛,马,狗,龙,猪,蛇,兔",
      isCorrect: false,
    }),
  ],
})
assert.deepEqual(yellowSpans(htmlMiss), [], `接口判错 → 必须零黄底：\n${htmlMiss}`)
assert.ok(htmlMiss.includes("04兔错"), `接口判错 → 必须显示「错」：\n${htmlMiss}`)

// 即使接口误报 true（历史 false_hit 场景），也不得把黄底点在生肖五行那一行。
const htmlFalseHit = await render("6104", {
  53: [
    row({
      term: "266",
      content: LEGACY_CONTENT_53,
      resCode: "05,11,19,31,42,07,04",
      resSx: "牛,马,狗,龙,猪,蛇,兔",
      isCorrect: true,
    }),
  ],
})
assert.deepEqual(
  yellowSpans(htmlFalseHit),
  [],
  `号码五行（金）不在«土木水»里 → 不得有任何黄底（旧口径会点「木」）：\n${htmlFalseHit}`,
)

// ── 3. 未开奖：零黄底 ───────────────────────────────────────────────
const htmlPending = await render("6104", {
  53: [
    row({
      term: "268",
      content: LEGACY_CONTENT_53,
      resCode: "",
      resSx: "",
      opened: false,
      isCorrect: null,
    }),
  ],
})
assert.deepEqual(yellowSpans(htmlPending), [], `未开奖必须零黄底：\n${htmlPending}`)
assert.ok(htmlPending.includes("???????"), `未开奖必须显示占位：\n${htmlPending}`)

// ── 4. 4行4头（7623 / mode 482+483）：五行部分同样按号码五行标黄 ────────
// 头 = 2头（特码 24 的头），五行 = «土木水金»，24 的号码五行 = 木。
const html7623 = await render("7623", {
  482: [
    row({
      term: "267",
      content: LEGACY_CONTENT_482,
      resCode: "05,11,19,31,42,07,24",
      resSx: "牛,马,狗,龙,猪,蛇,羊",
      isCorrect: true,
    }),
  ],
  483: [
    row({
      term: "267",
      content: '["2头|20,21,22,23,24,25,26,27,28,29"]',
      resCode: "05,11,19,31,42,07,24",
      resSx: "牛,马,狗,龙,猪,蛇,羊",
      isCorrect: true,
    }),
  ],
})
assert.ok(html7623.includes("267期"), `7623 必须渲染本期：\n${html7623}`)
// 头与五行同时命中时沿用既有「只点一处」规则（优先头），这里只要保证不出现错行。
assert.deepEqual(
  yellowSpans(html7623),
  ["2"],
  `7623: 头命中时沿用既有单高亮规则（不得点生肖五行对应的「土」）：\n${html7623}`,
)

// 头不命中、五行命中 → 黄底必须落在号码五行对应的那一行（24 → 木，而非生肖五行的「土」）。
const html7623ElementOnly = await render("7623", {
  482: [
    row({
      term: "267",
      content: LEGACY_CONTENT_482,
      resCode: "05,11,19,31,42,07,24",
      resSx: "牛,马,狗,龙,猪,蛇,羊",
      isCorrect: true,
    }),
  ],
  483: [
    row({
      term: "267",
      content: '["0头|01,02,03,04,05,06,07,08,09"]',
      resCode: "05,11,19,31,42,07,24",
      resSx: "牛,马,狗,龙,猪,蛇,羊",
      isCorrect: false,
    }),
  ],
})
assert.deepEqual(
  yellowSpans(html7623ElementOnly),
  ["木"],
  `7623: 五行命中必须点「木」（旧口径会点生肖五行对应的「土」）：\n${html7623ElementOnly}`,
)

// ── 5. 静态不变量：不得再用正文号码清单定位五行命中行 ─────────────────
const source = fs.readFileSync("frontend/lib/twcf888-articles.ts", "utf8")
assert.ok(
  /const ELEMENT_NUMBER_GROUPS[\s\S]*?土: \["05", "06", "19", "20", "27", "28", "35", "36", "49"\]/.test(
    source,
  ),
  "必须自带与后端 predict.common.ELEMENT_NUMBER_GROUPS 一致的号码五行常量",
)
assert.ok(source.includes("elementOfCode"), "五行命中行必须由特码号码推导（elementOfCode）")
assert.ok(
  !/matchedElement\s*=\s*pickMatchedPipeLabel/.test(source),
  "mode 482 不得再用正文号码清单定位五行命中行",
)

console.log("twcf888-element-verdict-contract: OK（mode 53/482 只按特码号码五行）")
