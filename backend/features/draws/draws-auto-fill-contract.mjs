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
  // 未开奖期改号前必须提示“该期预测已生成，改号会使其失效”。
  "normalizeDrawNumbers",
  "该期预测资料通常已经生成",
  "修改开奖号码会使已生成的预测命中判定失效",
  "确认继续保存吗？",
]) {
  if (!source.includes(token)) throw new Error(`draw autofill UI missing ${token}`)
}

if (!/if \(editing && normalizeDrawNumbers\(numbers\)[\s\S]{0,400}confirm\([\s\S]{0,600}if \(!confirmed\) return/.test(source)) {
  throw new Error("修改未开奖期号码前必须弹出确认提示，并在取消时中止保存")
}
