import fs from "node:fs"

const source = fs.readFileSync("features/draws/DrawsPage.tsx", "utf8")
for (const token of [
  "自动填写开奖记录",
  'useState("12")',
  '"/admin/draws/auto-fill-future"',
  "setAutoFillCount",
  "setAutoFilling",
  "created_count",
  "preserved_existing_count",
]) {
  if (!source.includes(token)) throw new Error(`draw autofill UI missing ${token}`)
}
