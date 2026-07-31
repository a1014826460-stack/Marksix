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
  "平特一尾", "精选22码", "绝杀二肖", "绝杀①半波", "绝杀①尾", "稳杀⑦码", "一句话中特网码",
]
for (const moduleName of mappedModules) {
  if (!design.includes(`### ${moduleName}：原始 HTML 基线`)) {
    throw new Error(`design document missing HTML baseline heading for ${moduleName}`)
  }
}
for (const heading of ["一头一码（www.twjsz666.com）24码中特", "买码之前先上", "小康早到来"]) {
  if (!design.includes(`### ${heading}：原始 HTML 基线`)) throw new Error(`design document missing composite baseline heading for ${heading}`)
}
for (const snippet of ["<tr>", 'class="bizhong1-l"', 'class="bizhong1-r"', 'background-color: #FFFF00']) {
  if (!design.includes(snippet)) throw new Error(`design document missing required HTML baseline ${snippet}`)
}
if (!skill.includes("前端预测模块开发规范")) throw new Error("SKILL.md missing frontend prediction-module standard")
for (const requirement of ["模块设计文档", "接口约定", "DOM 槽位", "固定期号"]) {
  if (!skill.includes(requirement)) throw new Error(`SKILL.md missing reusable requirement ${requirement}`)
}
if (!skill.includes("每一个可用预测模块")) throw new Error("SKILL.md does not require baselines for every mapped module")
for (const requirement of [
  "标题仅作为 DOM 定位锚点",
  "字段结构、数据类型、容量",
  "composite",
  "逐槽声明",
  "标题与字段冲突时",
]) {
  if (!skill.includes(requirement)) throw new Error(`SKILL.md missing semantic mapping rule ${requirement}`)
}
for (const requirement of [
  "授权记录或 module 对象存在不等于资料可用",
  "seed_pool",
  "不得只检查通用页脚容器",
  "naturalWidth > 0",
  "#legacy-attribute-anchor",
]) {
  if (!skill.includes(requirement)) throw new Error(`SKILL.md missing onboarding regression rule ${requirement}`)
}

console.log("twjsz666 prediction-module design contract passed")
