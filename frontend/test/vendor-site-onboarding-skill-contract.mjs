import fs from "node:fs"

const skill = fs.readFileSync("skills/vendor-site-onboarding/SKILL.md", "utf8")

for (const requirement of [
  "静态合同枚举每个 `[data-prediction-section]`",
  "`writeRow(issue, content, result)`",
  "缺少 `content` 或 `result` 槽位时静态合同必须直接失败",
  "getComputedStyle",
  "text-align",
]) {
  if (!skill.includes(requirement)) throw new Error(`onboarding SKILL is missing mandatory requirement: ${requirement}`)
}

if (!/issue.*content.*content-secondary.*result/s.test(skill)) {
  throw new Error("onboarding SKILL must enumerate every prediction-section slot count")
}

console.log("vendor onboarding SKILL contract passed")
