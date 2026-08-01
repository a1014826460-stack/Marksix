import fs from "node:fs"

// ---------------------------------------------------------------------------
// Manifest-driven site registry
// Each entry: [siteKey, filePath, fileType]
// All manifest sites must appear exactly once.
// ---------------------------------------------------------------------------
const REGISTERED_SITES = [
  ["shengshi8800", "frontend/public/vendor/shengshi8800/index.html", "html"],
  ["twsaimahui", "frontend/public/vendor/twsaimahui/index.html", "html"],
  ["twcaibawang", "frontend/components/twcaibawang/TwcaibawangHomeClient.tsx", "react"],
  ["twjinniu", "frontend/public/vendor/twjinniu/index.html", "html"],
  ["twcf888", "frontend/public/vendor/twcf888.com/index.html", "html"],
  ["twssz", "frontend/public/vendor/twssz/index.html", "html"],
  ["twbst528", "frontend/public/vendor/twbst528/index.html", "html"],
  ["twjsz666", "frontend/public/vendor/twjsz666/index.html", "html"],
  ["twwanli", "frontend/public/vendor/twwanli/index.html", "html"],
]

const EXPECTED_SITE_COUNT = REGISTERED_SITES.length

const SHARED_SCRIPT = "managed-site-links.js"

// ---------------------------------------------------------------------------
// Per-site assertions
// ---------------------------------------------------------------------------
const missingMounts = []
const passed = []

for (const [siteKey, filePath, fileType] of REGISTERED_SITES) {
  const source = fs.readFileSync(filePath, "utf8")

  // 1. Exactly one <managed-site-links> component instance
  const componentCount = (source.match(/<managed-site-links\b/g) || []).length
  if (componentCount !== 1) {
    missingMounts.push(`${siteKey}: expected 1 <managed-site-links> tag, found ${componentCount}`)
    continue
  }

  // 2. site-key attribute must equal the registered site key
  const siteKeyAttrPattern = new RegExp(
    `<managed-site-links\\b[^>]*\\bsite-key\\s*=\\s*["']${siteKey}["']`
  )
  if (!siteKeyAttrPattern.test(source)) {
    missingMounts.push(`${siteKey}: <managed-site-links> missing site-key="${siteKey}"`)
    continue
  }

  // 3. Exactly one shared script integration (managed-site-links.js)
  const scriptCount = (source.match(new RegExp(SHARED_SCRIPT.replace(/\./g, "\\."), "g")) || []).length
  if (scriptCount !== 1) {
    missingMounts.push(`${siteKey}: expected 1 managed-site-links.js reference, found ${scriptCount}`)
    continue
  }

  // 4. twjsz666-specific: replaced module must not contain old hardcoded table content
  if (siteKey === "twjsz666") {
    // The old section header must be gone
    if (source.includes("最快开奖（旗下网站）")) {
      missingMounts.push(`twjsz666: replaced module must not contain "最快开奖（旗下网站）" header`)
      continue
    }

    // The old table rows with hardcoded supplier names and image placeholder URLs
    // must not remain. Check for the specific row pattern with 4 cells per row.
    const oldRowPattern = /<tr\b[^>]*>\s*<td\b[^>]*>\s*<a\b[^>]*href\s*=\s*["']\/vendor\/twjsz666\/static\/picture\/c73120ca0585a192625208b7bcdfd1bd\.jpg["'][^>]*>\s*<span[^>]*>\s*(?:白小姐|金算盘|管家婆|聚彩堂|二四六|曾道人|赌侠网|开奖网|诸葛亮|铁算盘|王中王|刘伯温)/
    if (oldRowPattern.test(source)) {
      missingMounts.push(`twjsz666: old hardcoded table rows with supplier names still present`)
      continue
    }
  }

  passed.push(siteKey)
  console.log(`${siteKey}: mount contract verified (1 component, 1 script, site-key="${siteKey}")`)
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
if (missingMounts.length > 0) {
  console.error(`\nFAILED: ${missingMounts.length} site(s) missing valid mount:`)
  for (const msg of missingMounts) {
    console.error(`  - ${msg}`)
  }
  console.error(`\nPassed: ${passed.length}/${EXPECTED_SITE_COUNT}`)
  process.exit(1)
}

// All 8 sites must be present
if (passed.length !== EXPECTED_SITE_COUNT) {
  console.error(`\nFAILED: expected ${EXPECTED_SITE_COUNT} registered sites, found ${passed.length}`)
  process.exit(1)
}

console.log(`\nAll ${EXPECTED_SITE_COUNT} manifest sites have valid managed-site-links mounts`)
