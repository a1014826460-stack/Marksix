// `prediction.tokens` 对外形状回归契约。
//
// 背景：`prediction.tokens` 是站点展示契约，`site-data-adapter.js`
// （twwanli / twsyw / twssz / twjsz666 / twbst528）直接逐项渲染它。
// 任何「把 tokens 展开成原子」的改动都会让页面渲染出 `["天肖` 这类原始 JSON
// 残留（展示规范 S5 违规），并把逐肖列表退化成整串。
//
// fixture `fixtures/token-shape-live.json` 是从本地 dev（工作树）抽取的**真实**
// 兼容输入 + 期望 tokens；契约把每个模块的 tokens 形状钉死。
import fs from "node:fs"

import { buildCanonicalPredictionModules } from "@/lib/prediction-contract"

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message)
}

type Fixture = {
  tokens: string[]
  history: Array<Record<string, unknown>>
}

const fixtures = JSON.parse(
  fs.readFileSync("frontend/test/fixtures/token-shape-live.json", "utf8")
) as Record<string, Record<string, Fixture>>

function tokensFor(site: string, moduleKey: string) {
  const fixture = fixtures[site]?.[moduleKey]
  assert(fixture, `fixture 缺少 ${site}/${moduleKey}`)
  const modules = buildCanonicalPredictionModules({
    sitePageData: {
      site: {} as never,
      draw: {} as never,
      modules: [{
        id: 1,
        mechanism_key: moduleKey,
        title: moduleKey,
        default_modes_id: 0,
        default_table: "",
        sort_order: 1,
        status: true,
        history: fixture.history as never[],
      }],
    },
  })
  return { fixture, actual: modules[0]?.rows[0]?.prediction.tokens || [] }
}

let checked = 0
for (const [site, modules] of Object.entries(fixtures)) {
  for (const [moduleKey, fixture] of Object.entries(modules)) {
    const { actual } = tokensFor(site, moduleKey)

    // 1) 形状必须与真实输出逐项一致
    assert(
      JSON.stringify(actual) === JSON.stringify(fixture.tokens),
      `${site}/${moduleKey} tokens 形状被改变：期望 ${JSON.stringify(fixture.tokens)}，实际 ${JSON.stringify(actual)}`
    )

    // 2) 不得出现任何含 JSON 标点的 token（否则页面会渲染出原始 JSON 残留）
    for (const token of actual) {
      assert(
        !/[[\]"']/.test(token),
        `${site}/${moduleKey} token ${JSON.stringify(token)} 含 JSON 标点 → S5 违规`
      )
    }

    // 3) 不得把整串多元素内容塞进单个 token
    for (const token of actual) {
      assert(
        !/^\[.*\]$/.test(token),
        `${site}/${moduleKey} token ${JSON.stringify(token)} 是 JSON 数组串`
      )
    }
    checked += 1
  }
}

// 4) 逐肖列表不得退化成整串：9xzt / danshuang4xiao 必须逐项
for (const [site, modules] of Object.entries(fixtures)) {
  for (const moduleKey of ["9xzt", "danshuang4xiao"]) {
    const fixture = modules[moduleKey]
    if (!fixture) continue
    const { actual } = tokensFor(site, moduleKey)
    assert(
      actual.length === fixture.tokens.length,
      `${site}/${moduleKey} 逐肖列表项数必须保持 ${fixture.tokens.length}，实际 ${actual.length}`
    )
    for (const token of actual) {
      assert(token.length <= 2, `${site}/${moduleKey} 逐肖 token 必须是单肖，实际 ${JSON.stringify(token)}`)
    }
  }
}

console.log(`prediction token shape contract passed (${checked} 个模块)`)
