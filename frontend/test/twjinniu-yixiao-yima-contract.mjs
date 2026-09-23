import fs from "node:fs"
import ts from "typescript"

// 台湾通天网（www.twtongtian.com）「九肖18码 / 一肖一码大公开」渲染契约。
// 规则：卡片上展示的任一肖（一肖/三肖/五肖/七肖/九肖）或任一码（18码）命中特码即算“中”；
// 未命中只显示开奖号码，绝不显示“错”或“未中”。

function compileModule(path) {
  return ts.transpileModule(fs.readFileSync(path, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
}

function toDataModule(source) {
  return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
}

const backendStub = toDataModule(
  "export async function backendFetchJson(path, options) {" +
    "  const modesId = Number(options && options.query ? options.query.modes_id : 0);" +
    "  const table = globalThis.__twjinniuRows || {};" +
    "  return { rows: (table[modesId] || []).map((row) => ({ ...row })) };" +
    "}"
)
const sitesStub = toDataModule(
  "export function getSiteConfig() { return { siteKey: 'twjinniu', defaultWebId: 7 } }"
)

const homepageModule = toDataModule(
  compileModule("frontend/lib/twjinniu-homepage.ts")
    .replace('import "server-only";', "")
    .replace(/"@\/lib\/backend-api"/g, JSON.stringify(backendStub))
    .replace(/"@\/lib\/sites"/g, JSON.stringify(sitesStub))
)

const { getTwjinniuHomepageModules } = await import(homepageModule)

const NINE_XIAO = "鸡兔猪狗牛羊龙鼠蛇"
const EIGHTEEN_CODES = "05,17,29,41,03,15,27,39,08,20,32,44,11,23,35,47,12,24"

function mode151Row(entry, issue) {
  return {
    year: "2026",
    term: issue,
    content: JSON.stringify([entry]),
    res_code: "",
    res_sx: "",
    draw_is_opened: 0,
  }
}

function scenario({ issue, nineXiao, entry, specialCode, specialZodiac, opened = true }) {
  return {
    rows: {
      49: [
        {
          year: "2026",
          term: issue,
          content: nineXiao,
          res_code: opened ? specialCode : "",
          res_sx: opened ? specialZodiac : "",
          draw_is_opened: opened ? 1 : 0,
        },
      ],
      151: [
        {
          ...mode151Row(entry, issue),
          res_code: opened ? specialCode : "",
          res_sx: opened ? specialZodiac : "",
          draw_is_opened: opened ? 1 : 0,
        },
      ],
    },
  }
}

async function render(fixture) {
  globalThis.__twjinniuRows = fixture.rows
  const payload = await getTwjinniuHomepageModules(3)
  return payload.modules.yixiao_yima.html
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function assertNoMissLabels(html, label) {
  assert(!html.includes("【错】"), `${label}: 九肖18码不得显示【错】`)
  assert(!html.includes("未中"), `${label}: 九肖18码不得显示“未中”`)
  assert(!html.includes("错<"), `${label}: 九肖18码不得输出“错”`)
}

// 1) 265 期：一肖=虎（未中特码），但九肖含特码生肖“猪”、18码含特码号码 08 → 必须判“中”
const hitByNineXiao = await render(
  scenario({
    issue: "265",
    nineXiao: NINE_XIAO,
    entry: `虎|${EIGHTEEN_CODES}`,
    specialCode: "05,17,29,41,03,15,27,39,08",
    specialZodiac: "鸡,兔,猪,狗,牛,羊,龙,鼠,猪",
  })
)
assert(hitByNineXiao.includes("【中】"), "九肖或18码命中特码时必须显示【中】")
assert(hitByNineXiao.includes("中奖"), "九肖或18码命中时底部必须显示“中奖”")
assert(
  hitByNineXiao.includes('<span style="background-color: #ff0000; color: #FFFF00">猪</span>'),
  "命中的特码生肖必须高亮"
)
assert(
  hitByNineXiao.includes('<span style="background-color: #ff0000; color: #FFFF00">08</span>'),
  "命中的特码号码必须高亮"
)
assertNoMissLabels(hitByNineXiao, "265期")

// 2) 一肖命中（特码生肖等于一肖、但不在九肖列表内）也必须判“中”
const hitByBestXiao = await render(
  scenario({
    issue: "264",
    nineXiao: "鸡猴猪牛蛇狗虎羊龙",
    entry: `兔|${EIGHTEEN_CODES}`,
    specialCode: "19,06,09,27,24,32,04",
    specialZodiac: "鼠,牛,狗,龙,羊,猪,兔",
  })
)
assert(hitByBestXiao.includes("【中】"), "一肖命中特码生肖时必须显示【中】")
assert(
  hitByBestXiao.includes('<span style="background-color: #ff0000; color: #FFFF00">兔</span>'),
  "一肖命中时该生肖必须高亮"
)
assertNoMissLabels(hitByBestXiao, "264期")

// 3) 264 期真实资料：九肖不含“兔”、18码不含 04 → 不显示“错/未中”，也不显示【中】
const miss = await render(
  scenario({
    issue: "264",
    nineXiao: "鸡猴猪牛蛇狗虎羊龙",
    entry: `鸡|${EIGHTEEN_CODES}`,
    specialCode: "19,06,09,27,24,32,04",
    specialZodiac: "鼠,牛,狗,龙,羊,猪,兔",
  })
)
assert(!miss.includes("【中】"), "未命中时不得显示【中】")
assert(miss.includes("264期"), "未命中时仍要显示期号与开奖号码")
assertNoMissLabels(miss, "264期未命中")

// 4) 未开奖期：既无【中】也无【错】/未中
const pending = await render(
  scenario({
    issue: "266",
    nineXiao: NINE_XIAO,
    entry: `鼠|${EIGHTEEN_CODES}`,
    specialCode: "",
    specialZodiac: "",
    opened: false,
  })
)
assert(!pending.includes("【中】"), "未开奖期不得显示【中】")
assertNoMissLabels(pending, "266期未开奖")
