// tw8800「八肖中特」(5xiao.js / mode 48) 显示契约。
//
// 原实现只渲染前 5 肖，而判定使用完整 8 肖，用户看不出命中原因。
// 契约要求：normalizeWxztContent 完整输出 8 肖，且页面标题不得再写「五肖中特」。
import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

const FILE = "frontend/public/vendor/shengshi8800/static/js/5xiao.js"
const source = fs.readFileSync(FILE, "utf8")

// 抽出 normalizeWxztContent 单独求值（不引入 jQuery 依赖）
const match = source.match(/function normalizeWxztContent\(content\) \{[\s\S]*?\n\}/)
assert.ok(match, `${FILE}: 未找到 normalizeWxztContent`)

const sandbox = {}
vm.createContext(sandbox)
vm.runInContext(`${match[0]}\nthis.normalize = normalizeWxztContent;`, sandbox)
const normalize = sandbox.normalize

const ZODIAC = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
const countZodiac = (text) => [...text].filter((ch) => ZODIAC.includes(ch)).length

// 真实数据形态：8 组 `生肖|配码`
const content = '["狗|09", "龙|03", "鸡|10", "猴|11", "猪|08", "虎|05", "牛|06", "马|01"]'
const rendered = normalize(content)
assert.equal(countZodiac(rendered), 8, `必须完整显示 8 肖，实际: ${rendered}`)
assert.ok(!rendered.includes("|"), `不应显示配码: ${rendered}`)
for (const ch of "狗龙鸡猴猪虎牛马") {
  assert.ok(rendered.includes(ch), `缺少 ${ch}: ${rendered}`)
}

// 数组形态同样完整
assert.equal(countZodiac(normalize(["狗|09", "龙|03", "鸡|10", "猴|11", "猪|08", "虎|05", "牛|06", "马|01"])), 8)

// 旧的 5 肖截断必须已移除
assert.ok(!/slice\(0,\s*5\)/.test(source), `${FILE}: 仍存在 slice(0,5) 截断`)

// 标题不得再声称「五肖中特」（只检查生效代码，厂商遗留注释示例不算）
const live = source
  .replace(/\/\*[\s\S]*?\*\//g, "")
  .split("\n")
  .filter((line) => !line.trim().startsWith("//"))
  .join("\n")
assert.ok(!/五肖中特/.test(live), `${FILE}: 生效代码仍显示「五肖中特」`)
assert.ok(/八肖中特/.test(live), `${FILE}: 标题应改为「八肖中特」`)

console.log("8-zodiac display contract passed")
