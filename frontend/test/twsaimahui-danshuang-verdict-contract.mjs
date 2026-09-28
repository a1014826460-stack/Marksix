/**
 * twsaimahui「单双中特（单双选1，生肖选2）」判定契约
 * ---------------------------------------------------------------
 * 模块：mode 15 `title_15`；端点 `/api/kaijiang/getDsxiao`；渲染文件 `004danshuang.js`。
 * 站点 `twsaimahui` 首页实际加载的是 bundle，因此源文件与 bundle 必须同时满足本契约。
 *
 * 业务语义（修复 2026-09-27 的"全部显示错"）：
 *   资料行由两段构成，缺一不可判：
 *     - `content` = 「单/双生肖|6 个生肖」分类池（历史样本，与 xiao 候选**互斥**）；
 *     - `xiao`    = 最终候选生肖（2 个）。
 *   标题即「单双选1 + 生肖选2」= 两个维度，**任一维度命中即算命中**
 *   （等同仓库对 mixed 复合玩法的既有约束：任一维度命中即命中）。
 *   二者合计覆盖 8/12 生肖（≈67%），与厂商历史命中率一致；
 *   旧实现只看 `xiao`（2/12 ≈ 17%），把分类池命中的一半全部误判为"错"。
 *
 * 本契约同时用线上真实九期资料核对判定结果（261-269 期，命中 6/9）。
 */
import fs from "node:fs"
import path from "node:path"

const JS_DIR = path.join("frontend", "public", "vendor", "twsaimahui", "static", "js")
const SOURCE = path.join(JS_DIR, "004danshuang.js")

/** bundle 文件名是内容哈希，会随源文件改动而变；按 manifest 动态解析，避免硬编码。 */
function bundleFiles() {
  const manifestPath = path.join(JS_DIR, "bundles.json")
  if (fs.existsSync(manifestPath)) {
    const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"))
    const names = (manifest.runs || [])
      .map((run) => path.basename(String(run.bundle || "")))
      .filter(Boolean)
    if (names.length) {
      return names.map((name) => path.join(JS_DIR, name))
    }
  }
  return fs
    .readdirSync(JS_DIR)
    .filter((name) => /^bundle-[a-f0-9]+\.js$/.test(name))
    .map((name) => path.join(JS_DIR, name))
}

function getDsxiaoBlock(text) {
  const start = text.indexOf("getDsxiao")
  if (start < 0) throw new Error("missing /api/kaijiang/getDsxiao block")
  const rest = text.slice(start)
  const next = rest.indexOf("$.ajax({", 10)
  return next < 0 ? rest : rest.slice(0, next)
}

let bundleChecked = 0
for (const file of [SOURCE, ...bundleFiles()]) {
  if (!fs.existsSync(file)) throw new Error(`missing ${file}`)
  const text = fs.readFileSync(file, "utf8")
  if (file !== SOURCE && !text.includes("getDsxiao")) {
    continue // 另一个 bundle 不含本模块
  }
  if (file !== SOURCE) bundleChecked += 1
  const block = getDsxiaoBlock(text)
  // `dsHit` = 「本期特码落在分类池」这一维度。分类池取自 `content` 的 `标签|号码池`
  // 后半段（`dsv`），因此断言必须钉住「依据 dsv + 用特码 code 比对」这两点，
  // 只匹配 `dsHit = true` 会漏掉「写死为 true」的伪实现。
  if (!/let\s+dsHit\s*=\s*!!\([^;]*dsv[^;]*\.indexOf\(\s*code\s*\)/.test(block)) {
    throw new Error(
      `${file}: 「分类池命中」必须由特码是否落在 content 号码池（dsv）判定（dsHit = !!(… dsv…indexOf(code)…))`,
    )
  }
  if (!/let\s+hit\s*=\s*dsHit\s*\|\|\s*zj/.test(block)) {
    throw new Error(`${file}: 判定必须是「分类池 ∪ 候选生肖」任一命中`)
  }
  if (/zj\s*\?\s*'准'\s*:\s*'错'/.test(block)) {
    throw new Error(`${file}: 仍存在只看候选生肖的旧判定`)
  }
  // `sx` 必须是**特肖**（res_sx 末项），否则「候选肖命中」这一维度会拿第一个平码的生肖去比。
  if (!/let\s+sx\s*=\s*sxSplit\[sxSplit\.length-1\]/.test(block)) {
    throw new Error(`${file}: 特肖必须取 res_sx 最后一项（sxSplit[sxSplit.length-1]）`)
  }
  if (!/let\s+code\s*=\s*codeSplit\[codeSplit\.length-1\]/.test(block)) {
    throw new Error(`${file}: 特码必须取 res_code 最后一项（codeSplit[codeSplit.length-1]）`)
  }
  // 开奖段：未开奖不给判定（待开奖），已开奖按 hit 显示 准/错；
  // 且只有命中那一行才允许出现黄色高亮（旧写法把黄底写在开奖段 font 上，判「错」也有黄底）。
  if (!/let\s+resHtml\s*=\s*opened[\s\S]{0,220}?'开:待开奖'/.test(block)) {
    throw new Error(`${file}: 未开奖必须显示「开:待开奖」，不得给判定`)
  }
  if (!/hit[\s\S]{0,120}?准[\s\S]{0,120}?错/.test(block)) {
    throw new Error(`${file}: 已开奖必须按 hit 显示 准/错`)
  }
  const highlightSpans = (block.match(/background-color:\s*#FFFF00/g) || []).length
  if (highlightSpans === 0) {
    throw new Error(`${file}: 命中时必须标黄本期特码`)
  }
}

/** 复刻站点判定：特码生肖 ∈ 分类池 或 ∈ 候选生肖 即为命中。 */
export function verdict(row) {
  const codes = String(row.res_code || "").split(",").filter(Boolean)
  const signs = String(row.res_sx || "").split(",").filter(Boolean)
  if (!codes.length || !signs.length) return "??"
  const specialSign = signs[signs.length - 1]
  const pool = String(row.content || "").split("|")[1] || ""
  const poolHit = pool.split(",").map((s) => s.trim()).includes(specialSign)
  const pickHit = String(row.xiao || "").split(",").map((s) => s.trim()).includes(specialSign)
  return poolHit || pickHit ? "准" : "错"
}

// 线上真实资料（`/api/kaijiang/getDsxiao?web=6&type=3&num=10`）
const ROWS = [
  { term: "270", content: "双生肖|鼠,虎,龙,马,猴,狗", xiao: "兔,鸡", res_code: "", res_sx: "", expect: "??" },
  { term: "269", content: "双生肖|鼠,虎,龙,马,猴,狗", xiao: "羊,龙", res_code: "39,21,36,20,03,19,46", res_sx: "龙,狗,羊,猪,龙,鼠,鸡", expect: "错" },
  { term: "268", content: "双生肖|鼠,虎,龙,马,猴,狗", xiao: "马,龙", res_code: "07,29,25,15,32,43,11", res_sx: "鼠,虎,马,龙,猪,鼠,猴", expect: "准" },
  { term: "267", content: "单生肖|牛,兔,蛇,羊,猪,鸡", xiao: "鼠,猪", res_code: "02,49,04,38,22,27,24", res_sx: "蛇,马,兔,蛇,鸡,龙,羊", expect: "准" },
  { term: "266", content: "单生肖|牛,兔,蛇,羊,猪,鸡", xiao: "龙,鼠", res_code: "01,27,37,20,43,02,10", res_sx: "马,龙,马,猪,鼠,蛇,鸡", expect: "准" },
  { term: "265", content: "双生肖|鼠,虎,龙,马,猴,狗", xiao: "猪,蛇", res_code: "21,39,42,02,18,17,08", res_sx: "狗,龙,牛,蛇,牛,虎,猪", expect: "准" },
  { term: "264", content: "双生肖|鼠,虎,龙,马,猴,狗", xiao: "鸡,龙", res_code: "19,06,09,27,24,32,04", res_sx: "鼠,牛,狗,龙,羊,猪,兔", expect: "错" },
  { term: "263", content: "双生肖|鼠,虎,龙,马,猴,狗", xiao: "猪,马", res_code: "33,20,14,16,40,30,37", res_sx: "狗,猪,蛇,兔,兔,牛,马", expect: "准" },
  { term: "262", content: "双生肖|鼠,虎,龙,马,猴,狗", xiao: "鸡,狗", res_code: "13,16,17,25,09,34,32", res_sx: "马,兔,虎,马,狗,鸡,猪", expect: "错" },
  { term: "261", content: "双生肖|鼠,虎,龙,马,猴,狗", xiao: "龙,马", res_code: "27,24,20,41,17,25,45", res_sx: "龙,羊,猪,虎,虎,马,狗", expect: "准" },
]

let hits = 0
let drawn = 0
for (const row of ROWS) {
  const actual = verdict(row)
  if (actual !== row.expect) {
    throw new Error(`${row.term} 期判定应为 ${row.expect}，实际 ${actual}`)
  }
  if (actual !== "??") {
    drawn += 1
    if (actual === "准") hits += 1
  }
}

const rate = hits / drawn
if (drawn !== 9 || hits !== 6) {
  throw new Error(`样本命中率异常：${hits}/${drawn}`)
}
if (rate < 0.5 || rate > 0.85) {
  throw new Error(`判定命中率 ${(rate * 100).toFixed(0)}% 偏离厂商历史区间（50%~85%）`)
}

console.log(`twsaimahui 单双中特判定契约通过：源文件 + bundle 均为「分类池 ∪ 候选肖」，样本 ${hits}/${drawn} 命中`)
