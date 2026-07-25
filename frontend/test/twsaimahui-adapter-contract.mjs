import fs from "node:fs"

const adapter = fs.readFileSync(
  "frontend/public/vendor/twsaimahui/site-data-adapter.js",
  "utf8"
)

for (const token of [
  "createElement",
  "appendChild",
  "replaceChildren",
  "innerHTML",
  "document.write",
  "<style",
]) {
  if (adapter.includes(token)) throw new Error(`adapter must not mutate UI: ${token}`)
}

if (!adapter.includes("LotterySiteDataClient")) {
  throw new Error("adapter must use shared client")
}

if (!adapter.includes("site-data:ready")) {
  throw new Error("adapter must publish a non-visual readiness event")
}
