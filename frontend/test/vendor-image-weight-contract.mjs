/**
 * 厂商站点图片体积契约 — 不允许再出现 MB 级图片
 * ---------------------------------------------------------------
 * 背景：十个站点首页曾一次性拉取 43 MB 图片（单张最大 3.3 MB），是首屏卡顿的主要
 * 组成部分。本轮做了两步：
 *   1. 原地重压（scripts/compress-vendor-images.py）：静态 JPEG/PNG/GIF 重编码，
 *      不改文件名、不改容器格式；
 *   2. 大图转 WebP（scripts/convert-vendor-images-to-webp.py）：动画 GIF 与个别
 *      照片 PNG 换成 WebP（宽度 <= 800、帧率 <= 8），并全仓改写引用。
 * 契约固定结果，避免以后又塞回大图：
 *   - 单张图片 <= 400 KB；
 *   - vendor 图片总量 <= 18 MB；
 *   - 已转换的素材不得残留旧扩展名引用，且新 `.webp` 必须存在。
 */
import fs from "node:fs"
import path from "node:path"

const VENDOR_ROOT = "frontend/public/vendor"
const IMAGE_EXTENSIONS = new Set([".jpg", ".jpeg", ".png", ".gif", ".webp"])
const MAX_FILE_BYTES = 400 * 1024
const MAX_TOTAL_BYTES = 18 * 1024 * 1024
const TEXT_EXTENSIONS = new Set([".html", ".htm", ".js", ".mjs", ".cjs", ".css", ".ts", ".tsx", ".jsx", ".json"])
const SKIP_DIRS = new Set([".git", "node_modules", ".next", "__pycache__", ".deploy-backups"])

function walk(dir, predicate, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name)) continue
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) walk(full, predicate, out)
    else if (predicate(full)) out.push(full)
  }
  return out
}

const images = walk(VENDOR_ROOT, (file) => IMAGE_EXTENSIONS.has(path.extname(file).toLowerCase()))
if (images.length === 0) throw new Error("no vendor images found")

let total = 0
const oversized = []
for (const file of images) {
  const size = fs.statSync(file).size
  total += size
  if (size > MAX_FILE_BYTES) oversized.push(`${(size / 1024).toFixed(0)} KB ${file}`)
}
if (oversized.length) {
  throw new Error(`vendor images over ${MAX_FILE_BYTES / 1024} KB:\n  ${oversized.join("\n  ")}`)
}
if (total > MAX_TOTAL_BYTES) {
  throw new Error(
    `vendor image payload is ${(total / 1048576).toFixed(2)} MB, over the ${MAX_TOTAL_BYTES / 1048576} MB budget`,
  )
}

// 已转换为 WebP 的素材：不能再残留旧扩展名引用，且新文件必须存在。
const CONVERTED_STEMS = [
  "twcaibawang.com/static/picture/42ce9a26360f319a1e46203fda6a5e68",
  "twcaibawang.com/static/picture/274a8eaf95467d47aad835c203efe440",
  "twcaibawang.com/static/picture/5b98f9f1845b2a2edc2a4795a94b3d75",
  "twcaibawang.com/static/picture/815ea6d729ec11d96502aaa43765e3d1",
  "twcaibawang.com/static/picture/986d680d994f83b45386956911f934fd",
  "twcaibawang.com/static/picture/98edfdac8ec8f851bc12cc9c962bdd33",
  "twcaibawang.com/static/picture/b8c0c040981d4d1589a131d4657b4d94",
  "twcaibawang.com/static/picture/be31c7596d2c1fab4ffa07fe9cc603c0",
  "twbst528/static/picture/3089.80",
  "twsaimahui/static/picture/log2",
  "twsaimahui/static/picture/log3",
  "admin-history/static/image/zoopic",
  "twjinniu/static/file/kingsjpz_1051_502_0231",
]

for (const stem of CONVERTED_STEMS) {
  if (!fs.existsSync(path.join(VENDOR_ROOT, `${stem}.webp`))) {
    throw new Error(`converted webp is missing: ${stem}.webp`)
  }
}

const textFiles = walk(".", (file) => TEXT_EXTENSIONS.has(path.extname(file).toLowerCase()))
const stale = []
for (const file of textFiles) {
  const data = fs.readFileSync(file, "utf8")
  for (const stem of CONVERTED_STEMS) {
    const base = stem.split("/").pop()
    for (const extension of [".gif", ".jpg", ".jpeg", ".png"]) {
      if (data.includes(`${base}${extension}`)) stale.push(`${file} -> ${base}${extension}`)
    }
  }
}
if (stale.length) {
  throw new Error(`stale references to converted images:\n  ${stale.slice(0, 20).join("\n  ")}`)
}

console.log(
  `vendor image weight contract passed (${images.length} images, ${(total / 1048576).toFixed(2)} MB, ` +
    `max ${(Math.max(...images.map((file) => fs.statSync(file).size)) / 1024).toFixed(0)} KB)`,
)
