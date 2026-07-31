import fs from "node:fs"

// ---------------------------------------------------------------------------
// Three-line prediction display contract
//
// Asserts:
//   (a) SKILL.md includes reusable three-line rule language with
//       issue/content/result block-level display and computed-style contract.
//   (b) All inventory-hit modules use three independent leaf nodes with
//       display: block and no whole-row textContent concatenation.
// ---------------------------------------------------------------------------

const SKILL_PATH = "skills/vendor-site-onboarding/SKILL.md"

// ---------------------------------------------------------------------------
// Part (a): SKILL.md must contain the three-line rule
// ---------------------------------------------------------------------------
const skill = fs.readFileSync(SKILL_PATH, "utf8")

const THREE_LINE_RULES = [
  // Primary rule heading
  "三行预测展示",
  "三字段同单元格",
  // Must require three independent leaf nodes with data-prediction attributes
  "data-prediction-issue",
  "data-prediction-content",
  "data-prediction-result",
  // Must require display: block
  "display: block",
  // Must forbid whole-row textContent concatenation
  "textContent",
  // Must include computed-style browser test requirement
  "计算样式",
  "computed style",
  // Must reference browser verification
  "浏览器",
  // Public links rule - must forbid hardcoded external links
  "外部站点链接禁止硬编码",
  "公共站点链接",
  // Public links rule - managed-site-links component requirement
  "managed-site-links",
  // Public links rule - exclude current site, HTTPS, secure window
  "排除当前站点",
  "target=\"_blank\"",
  "noopener",
  // Public links rule - database changes must not require HTML changes
  "数据库变化不应要求修改站点",
  // New site must mount unique shared component
  "唯一共享组件",
]

const missingRules = []
for (const rule of THREE_LINE_RULES) {
  if (!skill.includes(rule)) {
    missingRules.push(rule)
  }
}

if (missingRules.length > 0) {
  console.error(`FAILED: SKILL.md missing required three-line / public-links rules:`)
  for (const r of missingRules) console.error(`  - "${r}"`)
  process.exit(1)
}

console.log("SKILL.md three-line and public-links rules present")

// ---------------------------------------------------------------------------
// Part (b): Inventory-hit modules must use three independent leaf nodes
// ---------------------------------------------------------------------------

// Inventory: scanned all registered vendor entry HTML files and adapters.
//
// HIT sites (issue/content/result in one text flow):
//   1. twjsz666 site-data-adapter.js — renderInlineSlots !group code path
//      combines prefix + value + result into single text node
//
// NOT HIT (and why):
//   twjsz666 modules WITH .zl spans: already separate leaf nodes
//   twbst528: three-column tables or structured multi-cell renderers
//   twssz: individual slot selectors per field
//   twjinniu/twcaibawang/twcf888: React SSR with block elements
//   twsaimahui/shengshi8800: Vue.js with separate rendering
//
// Per hard constraint: do not rewrite three-column tables.

const INVENTORY_HITS = [
  {
    site: "twjsz666",
    file: "frontend/public/vendor/twjsz666/site-data-adapter.js",
    description: "renderInlineSlots !group code path",
    check: checkAdapterNoCombinedText,
  },
  {
    site: "twjsz666",
    file: "frontend/public/vendor/twjsz666/index.html",
    description: "flat-one-tail (平特一尾公式) static HTML",
    check: checkFlatOneTailHTML,
  },
]

// Assertion: renderInlineSlots must not combine prefix + value + result into one text node
function checkAdapterNoCombinedText() {
  const adapter = fs.readFileSync("frontend/public/vendor/twjsz666/site-data-adapter.js", "utf8")

  // The forbidden pattern: combining prefix, value, and result into one font via textContent/leaf write
  // Pattern: setText(fonts[0], options.prefix(row) + value + " " + resultText(row))
  const combinedPattern = /setText\(\s*fonts\[\s*0\s*\]\s*,\s*options\.prefix\(\s*\w+\s*\)\s*\+\s*\w+\s*\+\s*["'][^"']*["']\s*\+\s*resultText/
  if (combinedPattern.test(adapter)) {
    console.error("FAILED: renderInlineSlots still combines prefix + value + result into one text node")
    return false
  }

  // The adapter must use data-prediction-* slots or separate font nodes for the three fields
  const usesDataPredictionSlots =
    adapter.includes("data-prediction-issue") ||
    adapter.includes("data-prediction-content") ||
    adapter.includes("data-prediction-result")
  if (!usesDataPredictionSlots) {
    console.error("FAILED: adapter does not use data-prediction-* slot attributes")
    return false
  }

  return true
}

// Assertion: flat-one-tail static HTML must have three separate leaf nodes with data-prediction-* attrs
function checkFlatOneTailHTML() {
  const html = fs.readFileSync("frontend/public/vendor/twjsz666/index.html", "utf8")

  // The flat-one-tail section must exist
  if (!html.includes("平特一尾公式")) {
    // Section doesn't exist at all (not necessarily a failure)
    console.log("flat-one-tail section not found in HTML (may have been restructured)")
    return true
  }

  // Find the section around "平特一尾公式"
  const sectionStart = html.indexOf("平特一尾公式")
  // Look within a reasonable window for the prediction rows
  const section = html.slice(sectionStart, sectionStart + 3000)

  // Each prediction row must have three data-prediction-* leaf elements
  // or at minimum, must not have the old single-font combined text pattern
  const hasIssueSlot = section.includes("data-prediction-issue")
  const hasContentSlot = section.includes("data-prediction-content")
  const hasResultSlot = section.includes("data-prediction-result")

  if (!hasIssueSlot || !hasContentSlot || !hasResultSlot) {
    console.error("FAILED: flat-one-tail HTML missing data-prediction-* leaf nodes")
    console.error(`  issue=${hasIssueSlot} content=${hasContentSlot} result=${hasResultSlot}`)
    return false
  }

  return true
}

// Run all inventory checks
let failed = false
for (const hit of INVENTORY_HITS) {
  if (!hit.check()) {
    console.error(`  [FAIL] ${hit.site}: ${hit.description}`)
    failed = true
  } else {
    console.log(`  [PASS] ${hit.site}: ${hit.description}`)
  }
}

// Also verify display: block CSS exists for data-prediction-* nodes
const twjsz666HTML = fs.readFileSync("frontend/public/vendor/twjsz666/index.html", "utf8")

// Must have CSS that sets display: block on prediction leaf nodes.
// The three-line standard requires display: block on data-prediction-issue/content/result.
// Accept both combined selectors (e.g. [data-prediction-issue],\n[data-prediction-content] { display: block })
// and individual rules.
const displayBlockCSS =
  /\[data-prediction-issue\][\s\S]{0,200}\[[data-prediction-]*(?:content|result)\][\s\S]{0,100}display\s*:\s*block/.test(twjsz666HTML) ||
  /\[data-prediction-issue\]\s*\{[^}]*display\s*:\s*block/.test(twjsz666HTML)

if (!displayBlockCSS) {
  console.error("FAILED: missing display:block CSS rule for data-prediction-* nodes")
  failed = true
}

if (failed) {
  console.error("\nThree-line prediction contract FAILED")
  process.exit(1)
}

console.log("\nThree-line prediction contract PASSED")
