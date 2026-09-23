/**
 * 厂商页面静态体积契约 — 内联图片外置与开奖面板单实例
 * ---------------------------------------------------------------
 * 1. twssz 首页曾把 173 份内联 base64 图片（去重后 18 张）写在 HTML 里，
 *    单文档 1.16 MB。契约要求：HTML 不再包含内联 base64 图片，改为引用
 *    /vendor/twssz/static/**（可命中 immutable 长缓存）下的真实文件，
 *    且每个引用都必须在磁盘上存在。
 * 2. twjsz666 的开奖切换页曾内联三个面板 iframe（台/澳/港），一次访问并发
 *    拉起三个开奖面板。契约要求：只保留一个静态面板 iframe，其余彩种在首次
 *    点选时由 cur() 按需创建。
 */
import fs from "node:fs"
import path from "node:path"

const twsszIndex = "frontend/public/vendor/twssz/index.html"
const twsszHtml = fs.readFileSync(twsszIndex, "utf8")

if (twsszHtml.includes("data:image")) {
  throw new Error("twssz index.html still ships inline data:image payloads")
}
const inlineRefs = [...twsszHtml.matchAll(/\/vendor\/twssz\/static\/file\/kj-inline\/([A-Za-z0-9._-]+)/g)].map(
  (match) => match[1],
)
if (inlineRefs.length < 150) {
  throw new Error(`twssz index.html references only ${inlineRefs.length} extracted images`)
}
for (const name of new Set(inlineRefs)) {
  const full = path.join("frontend/public/vendor/twssz/static/file/kj-inline", name)
  if (!fs.existsSync(full)) throw new Error(`extracted image missing on disk: ${full}`)
  if (fs.statSync(full).size === 0) throw new Error(`extracted image is empty: ${full}`)
}
if (fs.statSync(twsszIndex).size > 700 * 1024) {
  throw new Error("twssz index.html is still larger than 700 KB after externalising inline images")
}

const kai = fs.readFileSync("frontend/public/vendor/twjsz666/kai.html", "utf8")
const eagerPanels = [
  ...kai.matchAll(/<iframe[^>]*class="KJ-IFRAME"[^>]*src="\/vendor\/shengshi8800\/kj\/local\.html/g),
].length
if (eagerPanels !== 1) {
  throw new Error(`twjsz666 kai.html must keep exactly one eager draw panel, found ${eagerPanels}`)
}
for (const lotteryType of ["3", "2", "1"]) {
  if (!kai.includes(`/vendor/shengshi8800/kj/local.html?lottery_type=${lotteryType}`)) {
    throw new Error(`twjsz666 draw tab ${lotteryType} lost its unified draw module url`)
  }
}
if (!kai.includes("if (!frame) {")) {
  throw new Error("twjsz666 kai.html no longer creates the draw panel on demand")
}
if (!/frame = document\.createElement\("iframe"\)/.test(kai) || !kai.includes("node.appendChild(frame)")) {
  throw new Error("twjsz666 kai.html on-demand panel creation does not preserve the KJ-IFRAME slot")
}
if (!/frame\.setAttribute\("src", source\)/.test(kai)) {
  throw new Error("twjsz666 kai.html no longer points the panel iframe at the tab url")
}

console.log("vendor static weight contract passed")
