import fs from "node:fs"

// 台湾创富网（www.twcf888.com）首页「平特一肖」(mode 103) 展示契约。
// 该模块的原始素材是单个生肖，必须按原站样式渲染为三连生肖【蛇蛇蛇】，命中特码时保留
// 供应商的黄色背景。

const html = fs.readFileSync("frontend/public/vendor/twcf888.com/index.html", "utf8")

function functionBody(source, name) {
  const start = source.indexOf(`function ${name}(`)
  if (start === -1) throw new Error(`missing function ${name}`)
  const next = source.indexOf("\n    function ", start + 1)
  return source.slice(start, next === -1 ? source.length : next)
}

const formatPrediction = functionBody(html, "formatPredictionContent")
const mode103 = formatPrediction.slice(formatPrediction.indexOf("meta.modeId === 103"))
if (mode103 === formatPrediction) {
  throw new Error("formatPredictionContent must handle mode 103 (平特一肖) explicitly")
}

for (const token of [
  "flatZodiacPtyx + flatZodiacPtyx + flatZodiacPtyx",
  "【",
  "background-color:#FFFF00",
  "row.is_opened && row.is_correct === true",
]) {
  if (!mode103.includes(token)) {
    throw new Error(`平特一肖 must render the supplier triple with its hit highlight: ${token}`)
  }
}

const liveSection = functionBody(html, "buildLiveModuleSection")
if (!liveSection.includes("formatPredictionContent(meta, row)")) {
  throw new Error("the live module section must render 平特一肖 through formatPredictionContent")
}
if (!liveSection.includes("buildSsxztSection") && !liveSection.includes("meta.id ===")) {
  throw new Error("unexpected live module section structure")
}

// The prediction content must never fall back to a bare single zodiac for mode 103.
const bareSingle = /meta\.modeId === 103[\s\S]*?return\s+escapeHtml\(flatZodiacPtyx\)/
if (bareSingle.test(html)) {
  throw new Error("平特一肖 must not render a bare single-zodiac prediction")
}
