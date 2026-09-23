/**
 * twsaimahui 模块脚本合并契约
 * ---------------------------------------------------------------
 * 首页原本按文档位置散落 59 个启用模块脚本（另有 41 个在注释里、必须保持停用）。
 * `scripts/bundle-twsaimahui-modules.py` 只合并**连续区间**（区间之间夹着其它脚本时
 * 不合并，保证执行顺序不变），合并结果由本契约固定：
 *   1. bundles.json 存在，且每个 bundle 的正文按顺序包含其全部源文件（逐字节核对）；
 *   2. index.html 里不再有启用的 `static/js/0NN….js` 模块脚本标签；
 *   3. 仍然出现的模块脚本引用必须位于 HTML 注释中（被刻意停用的那些，不得激活）;
 *   4. 原始模块文件必须保留在磁盘上（api-audit 契约按文件名引用它们）。
 */
import fs from "node:fs"
import path from "node:path"

const ROOT = "frontend/public/vendor/twsaimahui"
const INDEX = path.join(ROOT, "index.html")
const MANIFEST = path.join(ROOT, "static/js/bundles.json")

if (!fs.existsSync(MANIFEST)) throw new Error("missing static/js/bundles.json")
const manifest = JSON.parse(fs.readFileSync(MANIFEST, "utf8"))
if (!Array.isArray(manifest.runs) || manifest.runs.length === 0) {
  throw new Error("bundles.json has no runs")
}

function commentSpans(text) {
  const spans = []
  const pattern = /<!--[\s\S]*?-->/g
  let match
  while ((match = pattern.exec(text)) !== null) spans.push([match.index, match.index + match[0].length])
  return spans
}

function insideComment(index, spans) {
  return spans.some(([start, end]) => start <= index && index < end)
}

const indexHtml = fs.readFileSync(INDEX, "utf8")
const hidden = commentSpans(indexHtml)

for (const run of manifest.runs) {
  const bundlePath = path.join(ROOT, run.bundle.replace(/^static\//, "static/"))
  if (!fs.existsSync(bundlePath)) throw new Error(`bundle missing on disk: ${run.bundle}`)
  const bundle = fs.readFileSync(bundlePath, "utf8")
  let cursor = 0
  for (const source of run.sources) {
    const sourcePath = path.join(ROOT, source)
    if (!fs.existsSync(sourcePath)) throw new Error(`original module script missing: ${source}`)
    const body = fs.readFileSync(sourcePath, "utf8").trim()
    const found = bundle.indexOf(body, cursor)
    if (found < 0) throw new Error(`${run.bundle} does not contain ${source} in document order`)
    cursor = found + body.length
  }
  if (!indexHtml.includes(`src="${run.bundle}"`) && !indexHtml.includes(`src='${run.bundle}'`)) {
    throw new Error(`index.html no longer loads ${run.bundle}`)
  }
}

// 3 + 4. 仍被引用的模块脚本必须处于停用（注释）状态，且文件仍在磁盘上
const moduleRefs = [...indexHtml.matchAll(/static\/js\/0\d{2}[A-Za-z0-9_]*\.js/g)]
const active = moduleRefs.filter((match) => !insideComment(match.index, hidden))
if (active.length > 0) {
  throw new Error(`active module script tags remain: ${active.map((match) => match[0]).join(", ")}`)
}
for (const match of moduleRefs) {
  const referenced = path.join(ROOT, match[0])
  if (!fs.existsSync(referenced)) throw new Error(`commented module script is missing: ${match[0]}`)
}

const bundleTags = [...indexHtml.matchAll(/static\/js\/bundle-[0-9a-f]{16}\.js/g)]
if (bundleTags.length !== manifest.runs.length) {
  throw new Error(`expected ${manifest.runs.length} bundle tags, found ${bundleTags.length}`)
}

console.log(
  `twsaimahui bundle contract passed (${manifest.module_scripts_before} module scripts -> ` +
    `${manifest.bundles_after} bundles, ${moduleRefs.length} commented refs kept inert)`,
)
