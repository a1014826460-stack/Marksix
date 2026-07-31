import fs from "node:fs"

const designPath = "docs/vendor-sites/twjsz666-frontend-prediction-modules.md"
const skillPath = "skills/vendor-site-onboarding/SKILL.md"

if (!fs.existsSync(designPath)) throw new Error("missing twjsz666 prediction-module design document")
const design = fs.readFileSync(designPath, "utf8")
const skill = fs.readFileSync(skillPath, "utf8")

for (const heading of ["预测模块清单", "后端 API 设计", "前端展示数据格式", "SKILL.md 新增内容"]) {
  if (!design.includes(heading)) throw new Error(`design document missing ${heading}`)
}
const mappedModules = [
  "单双各四肖", "发财⑨肖", "三头四尾", "平特一肖", "四字解平特肖", "精准台湾高手",
  "双波中特", "家禽VS野兽", "平特③肖", "④肖⑧码", "大小中特", "七尾中特",
  "平特一尾", "精选22码", "绝杀二肖", "绝杀①波", "绝杀①尾", "稳杀⑦码", "一句话中特网码",
]
for (const moduleName of mappedModules) {
  if (!design.includes(`### ${moduleName}：原始 HTML 基线`)) {
    throw new Error(`design document missing HTML baseline heading for ${moduleName}`)
  }
}
for (const snippet of ["<tr>", 'class="bizhong1-l"', 'class="bizhong1-r"', 'background-color: #FFFF00']) {
  if (!design.includes(snippet)) throw new Error(`design document missing required HTML baseline ${snippet}`)
}
if (!skill.includes("前端预测模块开发规范")) throw new Error("SKILL.md missing frontend prediction-module standard")
for (const requirement of ["模块设计文档", "接口约定", "DOM 槽位", "固定期号"]) {
  if (!skill.includes(requirement)) throw new Error(`SKILL.md missing reusable requirement ${requirement}`)
}
if (!skill.includes("每一个可用预测模块")) throw new Error("SKILL.md does not require baselines for every mapped module")

console.log("twjsz666 prediction-module design contract passed")
