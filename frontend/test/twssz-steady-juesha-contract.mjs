import fs from "node:fs";

const html = fs.readFileSync(new URL("../public/vendor/twssz/index.html", import.meta.url), "utf8");
const adapter = fs.readFileSync(new URL("../public/vendor/twssz/site-data-adapter.js", import.meta.url), "utf8");

if (!html.includes('data-prediction-section="juesha2xiao-steady"')) {
  throw new Error("稳杀二肖区块必须声明稳定 section 锚点");
}
const section = html.match(/data-prediction-section="juesha2xiao-steady"[\s\S]*?(?=<div id="top_2")/);
if (!section) throw new Error("稳杀二肖 section 结构缺失");
for (const slot of ["data-prediction-issue", "data-prediction-content", "data-prediction-result"]) {
  const count = (section[0].match(new RegExp(slot, "g")) || []).length;
  if (count !== 8) throw new Error(`${slot} 必须恰好枚举 8 个槽位，实际 ${count}`);
}
if (!adapter.includes("renderSteadyJueshaTwoXiaoHistory")) {
  throw new Error("adapter 缺少稳杀二肖专用 renderer");
}
if (!adapter.includes('key: "juesha2xiao-steady"')) {
  throw new Error("adapter 缺少稳杀二肖 section 映射");
}
console.log("twssz steady juesha contract passed");
