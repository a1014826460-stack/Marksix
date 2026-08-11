import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const vendorRoot = path.join(repoRoot, "frontend", "public", "vendor")
const runtimePath = "/vendor/_shared/forced-announcement.js"
const scriptTag = `<script src="${runtimePath}"></script>`

function vendorHtmlFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    if (entry.name === "_shared") return []
    const target = path.join(directory, entry.name)
    if (entry.isDirectory()) return vendorHtmlFiles(target)
    return /\.html?$/i.test(entry.name) ? [target] : []
  })
}

function decodeUtf8(file) {
  const bytes = fs.readFileSync(file)
  const hasBom = bytes.length >= 3
    && bytes[0] === 0xef
    && bytes[1] === 0xbb
    && bytes[2] === 0xbf
  const content = hasBom ? bytes.subarray(3) : bytes
  try {
    return {
      source: new TextDecoder("utf-8", { fatal: true }).decode(content),
      hasBom,
    }
  } catch (error) {
    throw new Error(`Vendor HTML is not valid UTF-8: ${file}`, { cause: error })
  }
}

function inject(source, file) {
  const count = source.split(runtimePath).length - 1
  if (count > 1) {
    throw new Error(`Forced announcement runtime is duplicated in ${file}`)
  }
  if (count === 1) return source

  const newline = source.includes("\r\n") ? "\r\n" : "\n"
  const headLine = source.match(/^([\t ]*)<\/head\s*>/im)
  if (headLine && headLine.index != null) {
    const before = source.slice(0, headLine.index)
    return before
      + `${headLine[1]}${scriptTag}${newline}`
      + source.slice(headLine.index)
  }
  const headTag = source.match(/<\/head\s*>/i)
  if (headTag && headTag.index != null) {
    return source.slice(0, headTag.index)
      + scriptTag
      + source.slice(headTag.index)
  }
  const bodyLine = source.match(/^([\t ]*)<\/body\s*>/im)
  if (bodyLine && bodyLine.index != null) {
    const before = source.slice(0, bodyLine.index)
    return before
      + `${bodyLine[1]}${scriptTag}${newline}`
      + source.slice(bodyLine.index)
  }
  const bodyTag = source.match(/<\/body\s*>/i)
  if (bodyTag && bodyTag.index != null) {
    return source.slice(0, bodyTag.index)
      + scriptTag
      + source.slice(bodyTag.index)
  }
  return `${source}${newline}${scriptTag}${newline}`
}

let changed = 0
const files = vendorHtmlFiles(vendorRoot)
for (const file of files) {
  const { source, hasBom } = decodeUtf8(file)
  const updated = inject(source, file)
  if (updated === source) continue
  const encoded = Buffer.from(updated, "utf8")
  fs.writeFileSync(
    file,
    hasBom ? Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), encoded]) : encoded,
  )
  changed += 1
}

console.log(`Forced announcement runtime injected into ${changed}/${files.length} Vendor HTML files.`)
