import fs from "node:fs"

const adapter = fs.readFileSync("frontend/public/vendor/twjsz666/site-data-adapter.js", "utf8")
const html = fs.readFileSync("frontend/public/vendor/twjsz666/index.html", "utf8")

function text(value) {
  return value.replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").replace(/\s+/g, " ").trim()
}

function visibleListTitles(source) {
  const titles = []
  const pattern = /<div\b([^>]*)class=["'][^"']*\blist-title\b[^"']*["'][^>]*>([\s\S]*?)<\/div>/gi
  let match
  while ((match = pattern.exec(source))) {
    const before = source.slice(Math.max(0, match.index - 800), match.index)
    if (/style=["'][^"']*display\s*:\s*none/i.test(before.slice(before.lastIndexOf("<div")))) continue
    titles.push({ title: text(match[2]), container: /id=["']([^"']+)/i.exec(match[1])?.[1] || "list-title-parent" })
  }
  return titles
}

const visibleTitles = visibleListTitles(html)
const publicCards = [...html.matchAll(/<table\b[^>]*class=["'][^"']*\bqxtable\b[^"']*["'][^>]*>[\s\S]*?<\/table>/gi)]
  .filter((match) => match[0].includes("买码之前先上：这里期期大公开"))

if (visibleTitles.length !== 24) throw new Error(`expected 24 visible list titles, found ${visibleTitles.length}`)
if (publicCards.length !== 9) throw new Error(`expected nine 买码之前先上 cards, found ${publicCards.length}`)
if (!adapter.includes("SECTION_CONTRACTS")) throw new Error("adapter lacks explicit SECTION_CONTRACTS")
if (adapter.includes("function renderUnavailableSection")) throw new Error("adapter still has generic renderUnavailableSection fallback")
if (!adapter.includes("Object.freeze(contract)")) throw new Error("SECTION_CONTRACTS entries are not immutable")
if (!adapter.includes('querySelectorAll("table.qxtable")')) throw new Error("public prediction cards are not cleared before API rendering")

const requiredFields = ["id", "titlePattern", "containerSelector", "classification", "moduleKeys", "rendererName", "issueGroups", "supplierSentinels"]
for (const field of requiredFields) {
  if (!adapter.includes(`${field}:`)) throw new Error(`SECTION_CONTRACTS missing ${field}`)
}

const classifications = ["mapped", "composite", "unavailable", "static"]
for (const classification of classifications) {
  if (!adapter.includes(`classification: \"${classification}\"`)) throw new Error(`missing ${classification} classification`)
}

const contractIds = [...adapter.matchAll(/id:\s*["']([^"']+)["']/g)].map((match) => match[1])
const expectedInventorySize = visibleTitles.length + publicCards.length
if (new Set(contractIds).size !== expectedInventorySize) {
  throw new Error(`inventory closure failed: expected ${expectedInventorySize} contracts, found ${new Set(contractIds).size}`)
}

console.log(`twjsz666 section inventory contract passed (${expectedInventorySize} visible sections)`)
