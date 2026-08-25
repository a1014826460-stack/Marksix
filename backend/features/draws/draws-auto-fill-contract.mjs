import fs from "node:fs"

const source = fs.readFileSync("features/draws/DrawsPage.tsx", "utf8")
for (const token of [
  "自动填写开奖记录",
  "确认补齐台湾彩未来记录至",
  "已补齐至",
  'useState("12")',
  '"/admin/draws/auto-fill-future"',
  "setAutoFillCount",
  "setAutoFilling",
  "created_count",
  "preserved_existing_count",
  '"/admin/draws/auto-fill-future/settings"',
  "台湾彩自动填写设置",
  "启用自动填写",
  "每日执行时间（北京时间 UTC+8）",
  'timeZone: "Asia/Shanghai"',
  "formatBeijingDateTime",
  "保存自动填写设置",
  "setAutoFillSettings",
]) {
  if (!source.includes(token)) throw new Error(`draw autofill UI missing ${token}`)
}
