import fs from "node:fs"
import path from "node:path"

const vendorRoot = path.resolve("frontend/public/vendor")
const scriptPath = "/vendor/_shared/forced-announcement.js"

function htmlFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    if (entry.name === "_shared") return []
    const target = path.join(directory, entry.name)
    if (entry.isDirectory()) return htmlFiles(target)
    return /\.html?$/i.test(entry.name) ? [target] : []
  })
}

const failures = []
const files = htmlFiles(vendorRoot)
for (const file of files) {
  const source = fs.readFileSync(file, "utf8")
  const count = source.split(scriptPath).length - 1
  if (count !== 1) {
    failures.push(`${path.relative(vendorRoot, file)}: expected 1 script, found ${count}`)
  }
}

if (failures.length) {
  throw new Error(
    `${failures.length}/${files.length} Vendor HTML files violate forced announcement injection:\n`
      + failures.slice(0, 20).join("\n"),
  )
}

const layout = fs.readFileSync("frontend/app/layout.tsx", "utf8")
if ((layout.split(scriptPath).length - 1) !== 1 || !layout.includes("beforeInteractive")) {
  throw new Error("Next root layout must load the forced announcement runtime exactly once before interactive")
}

const injector = fs.readFileSync("scripts/inject-forced-announcement.mjs", "utf8")
for (const token of ["frontend/public/vendor", scriptPath, "head\\s*>"]) {
  if (!injector.includes(token)) throw new Error(`injector contract missing: ${token}`)
}

const dockerfile = fs.readFileSync("Dockerfile.frontend", "utf8")
if (!dockerfile.includes("inject-forced-announcement.mjs")) {
  throw new Error("frontend Docker build must run the forced announcement injector")
}

console.log(`forced announcement injection verified for ${files.length} Vendor HTML files`)
