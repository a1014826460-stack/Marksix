"use client"

import { useEffect, useMemo, useState } from "react"
import type { PublicModule, PublicSitePageData } from "@/lib/site-page"
import type { VendorHomepageModule, VendorHomepageModulesResponse } from "@/lib/vendor-homepage"

type TwcaibawangHomeClientProps = {
  siteData: PublicSitePageData
  homepageModules: VendorHomepageModulesResponse
  defaultLotteryTypeId: 1 | 2 | 3
}

type LotteryTypeOption = {
  id: 1 | 2 | 3
  label: string
  iframeLabel: string
  color: string
  drawLotteryType: 1 | 2 | 3
}

type GenericModuleConfig = {
  anchor: string
  title: string
  mechanismKey: string
  face?: string
  predictionColor?: string
}

type SourceRow = {
  term: string
  prediction: string
  result: string
  isOpened: boolean
  isCorrect: boolean | null
  raw: Record<string, unknown>
}

const LOTTERY_TYPE_OPTIONS: LotteryTypeOption[] = [
  { id: 1, label: "香港彩", iframeLabel: "香港彩", color: "#00c6ff", drawLotteryType: 1 },
  { id: 2, label: "澳门彩", iframeLabel: "澳门彩", color: "#0084ff", drawLotteryType: 2 },
  { id: 3, label: "台湾彩", iframeLabel: "台湾彩", color: "#de2910", drawLotteryType: 3 },
]

const GENERIC_MODULES: GenericModuleConfig[] = [
  { anchor: "qqsh", title: "琴棋书画", mechanismKey: "qinqi", face: "微软雅黑", predictionColor: "#FF0000" },
  { anchor: "szpt", title: "四字平特", mechanismKey: "sizixuanji", face: "微软雅黑", predictionColor: "#FF0000" },
  { anchor: "yjbt", title: "一句真言", mechanismKey: "yijuzhenyan", face: "微软雅黑", predictionColor: "#008000" },
  { anchor: "bz9x", title: "9肖中特", mechanismKey: "9xzt", face: "微软雅黑", predictionColor: "#FF0000" },
  { anchor: "sxjh3", title: "三期4肖", mechanismKey: "title_197", face: "微软雅黑", predictionColor: "#0000FF" },
  { anchor: "x912m", title: "9肖12码", mechanismKey: "9xiao12ma", face: "华文中宋", predictionColor: "#FF9900" },
  { anchor: "jsyb", title: "绝杀一波", mechanismKey: "jueshabanbo", face: "微软雅黑", predictionColor: "#0000FF" },
]

function escapeHtml(value: unknown) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
}

function escapeAttr(value: unknown) {
  return escapeHtml(value).replace(/`/g, "&#96;")
}

function resolveModule(modules: PublicModule[], mechanismKey: string) {
  return modules.find((item) => item.mechanism_key === mechanismKey) || null
}

function buildKjIframeUrl(option: LotteryTypeOption) {
  const params = new URLSearchParams({
    lottery_type: String(option.drawLotteryType),
    label: option.iframeLabel,
  })
  return `/vendor/shengshi8800/kj/local.html?${params.toString()}`
}

function normalizePredictionText(value: string) {
  return value.replace(/^\[/, "").replace(/\]$/, "").replace(/"/g, "")
}

function parseJsonStringArray(value: string) {
  const trimmed = String(value || "").trim()
  if (!trimmed) return [] as string[]
  try {
    const parsed = JSON.parse(trimmed)
    if (Array.isArray(parsed)) {
      return parsed.map((item) => String(item || "").trim()).filter(Boolean)
    }
  } catch {
    // Fall through to the plain-text fallback.
  }
  return [trimmed]
}

function chunkArray<T>(items: T[], size: number) {
  const chunks: T[][] = []
  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size))
  }
  return chunks
}

function toSourceRows(module: PublicModule | null): SourceRow[] {
  if (!module) return []
  return module.history.map((row) => ({
    term: row.term || "",
    prediction: normalizePredictionText(String(row.prediction_text || "")),
    result: String(row.result_text || ""),
    isOpened: !!row.is_opened,
    isCorrect: row.is_correct ?? null,
    raw: row.raw || {},
  }))
}

function getRowContent(row: SourceRow) {
  return String(row.raw?.content || row.prediction || "").trim()
}

function getLatestImage(module: PublicModule | null) {
  if (!module) return ""
  const latest = [...module.history]
    .sort((a, b) => String(b.issue || "").localeCompare(String(a.issue || ""), "en"))
    .find((row) => String(row.image_url || "").trim())
  return String(latest?.image_url || "").trim()
}

function stripLeadingKai(resultText: string) {
  return resultText.replace(/^开/, "")
}

function parseResultParts(resultText: string) {
  const raw = stripLeadingKai(resultText).trim()
  const sxCode = raw.match(/^([\u4e00-\u9fa5]+)(\d{2})$/)
  if (sxCode) {
    return { code: sxCode[2], sx: sxCode[1], raw }
  }
  const codeSx = raw.match(/^(\d{2})([\u4e00-\u9fa5]+)$/)
  if (codeSx) {
    return { code: codeSx[1], sx: codeSx[2], raw }
  }
  return { code: "", sx: "", raw }
}

function formatOpenResult(resultText: string) {
  const parts = parseResultParts(resultText)
  if (parts.code && parts.sx) {
    return `${parts.code}${parts.sx}`
  }
  return parts.raw
}

function renderPlainResult(resultText: string, isOpened: boolean, isCorrect: boolean | null, pending = "???????") {
  if (!isOpened) return pending
  const text = escapeHtml(formatOpenResult(resultText))
  if (isCorrect === false) {
    return `${text}<font color="#000">错</font>`
  }
  return `<font color="#FF0000">${text}对</font>`
}

function renderOpenResultWithJudge(resultText: string, isOpened: boolean, isCorrect: boolean | null, pending = "???????") {
  if (!isOpened) return pending
  const text = escapeHtml(formatOpenResult(resultText))
  return isCorrect === true ? `<font color="#FF0000">${text}对</font>` : `${text}<font color="#000">错</font>`
}

function renderOpenResultCodeOnly(resultText: string, isOpened: boolean, pending = "?????") {
  if (!isOpened) return pending
  return escapeHtml(formatOpenResult(resultText))
}

function renderTwcaibawangResultSuffix(
  resultText: string,
  isOpened: boolean,
  isCorrect: boolean | null,
  pending = "???????"
) {
  if (!isOpened) return pending
  const text = escapeHtml(formatOpenResult(resultText))
  const judgeColor = isCorrect === true ? "#FF0000" : "#000000"
  const judgeText = isCorrect === true ? "对" : "错"
  return `${text}<font color="${judgeColor}">${judgeText}</font>`
}

function normalizeDaxiaoLabel(label: string) {
  const text = label.trim()
  if (text.includes("大")) return "大数"
  if (text.includes("小")) return "小数"
  return text
}

function extractTouDigitLabel(value: string) {
  const match = value.match(/\d+/)
  return match ? match[0] : value.trim()
}

function formatMa24Codes(content: string) {
  return content
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => item.padStart(2, "0"))
}

function renderSxCodeResult(resultText: string, isOpened: boolean, pending = "？00") {
  if (!isOpened) return pending
  const { code, sx, raw } = parseResultParts(resultText)
  if (sx || code) {
    return `${escapeHtml(sx || "？")}${escapeHtml(code || "00")}`
  }
  return escapeHtml(raw || pending)
}

function ensureSentence(text: string) {
  const trimmed = text.trim()
  if (!trimmed) return ""
  return /[。！？!?]$/.test(trimmed) ? trimmed : `${trimmed}。`
}

function highlightZodiacChars(text: string, hitSx: string) {
  return Array.from(text || "")
    .map((char) =>
      hitSx && char === hitSx ? `<span style="background-color: #FFFF00">${escapeHtml(char)}</span>` : escapeHtml(char)
    )
    .join("")
}

function parseLabelCodeEntries(content: string) {
  const text = String(content || "").trim()
  const normalized = text.replace(/^\[+|\]+$/g, "").replace(/"/g, "").replace(/\./g, ",")
  const entries = [...normalized.matchAll(/([^,|]+)\|((?:\d{1,2})(?:,\d{1,2})*)/g)].map((match) => ({
    label: String(match[1] || "")
      .replace(/^[\[,]+|[\],]+$/g, "")
      .trim(),
    codes: String(match[2] || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
      .map((item) => item.padStart(2, "0")),
  }))

  if (entries.length) return entries

  return parseJsonStringArray(text)
    .map((item) => {
      const [label, codesRaw = ""] = String(item).split("|", 2)
      return {
        label: label.replace(/^[\[,"]+|[\],"]+$/g, "").trim(),
        codes: codesRaw
          .split(/[,.]/)
          .map((code) => code.trim())
          .filter(Boolean)
          .map((code) => code.padStart(2, "0")),
      }
    })
    .filter((item) => item.label)
}

function getLotteryDisplayName(lotteryTypeId: 1 | 2 | 3) {
  if (lotteryTypeId === 1) return "香港天下彩"
  if (lotteryTypeId === 2) return "澳门天下彩"
  return "台湾天下彩"
}

function renderModuleTitle(lotteryTypeId: 1 | 2 | 3, title: string) {
  return `<font color="#FFFF00">${escapeHtml(getLotteryDisplayName(lotteryTypeId))}</font><font color="#FFFFFF">${escapeHtml(title)}</font>`
}

function renderLotteryTitleTable(lotteryTypeId: 1 | 2 | 3, titleHtml: string) {
  return renderTitleTable(renderModuleTitle(lotteryTypeId, titleHtml))
}

function repeatPrediction(value: string) {
  return `${value}${value}${value}`
}

function highlightIf(content: string, condition: boolean) {
  return condition ? `<span style="background-color: #FFFF00">${content}</span>` : content
}

function mapColorToWave(color: string) {
  if (color === "red") return "红波"
  if (color === "blue") return "蓝波"
  if (color === "green") return "绿波"
  return ""
}

function parsePt1WeiTriple(prediction: string) {
  const match = prediction.match(/(\d)尾/)
  return match ? match[1].repeat(3) : prediction
}

function renderTitleTable(titleHtml: string) {
  return `<table border="1" width="100%" bgcolor="#ffffff">
                <tbody>
                <tr>
                    <td style="border:10px double #CC0000; height: 50px;" bgcolor="#CC0000">
                        <p align="center">
                            <b>
                                <font face="楷体" style="font-size: 18pt">${titleHtml}</font>
                            </b>
                        </p>
                    </td>
                </tr>
                </tbody>
            </table>`
}

function renderFontList(items: string[], highlighted?: string) {
  return items
    .map((item) => {
      const content = escapeHtml(item)
      return highlighted && item === highlighted
        ? `<span style="background-color: #FFFF00">${content}</span>`
        : `<font>${content}</font>`
    })
    .join("")
}

function renderDottedCodes(items: string[], highlighted?: string) {
  return items
    .map((item, index) => {
      const prefix = index > 0 ? "." : ""
      const content = escapeHtml(item)
      return highlighted && item === highlighted
        ? `${prefix}<span style="background-color: #FFFF00">${content}</span>`
        : `${prefix}<font>${content}</font>`
    })
    .join("")
}

function renderDashCodes(items: string[], highlighted?: string) {
  return items
    .map((item, index) => {
      const prefix = index > 0 ? "-" : ""
      const content = escapeHtml(item)
      return highlighted && item === highlighted
        ? `${prefix}<span style="background-color: #FFFF00">${content}</span>`
        : `${prefix}<font>${content}</font>`
    })
    .join("")
}

function renderWuxiaoWuma(
  module: Extract<VendorHomepageModule, { module_key: "wuxiao_wuma" }> | undefined,
  lotteryTypeId: 1 | 2 | 3
) {
  if (!module?.history?.length) return ""
  const rows = module.history
    .map((row) => {
      const hitSx = row.result.is_opened ? row.result.res_sx : ""
      const hitCode = row.result.is_opened ? row.result.res_code : ""
      return `<tr>
    <td align="left" height="40" bgcolor="#FFFFFF">
        <b><font face="华文中宋"><font color="#990033">${escapeHtml(row.term)}期五肖</font>:<span style="font-size: 13pt">${renderFontList(row.groups.xiao_5, hitSx)}</span></font></b>
        <p><b><font face="华文中宋"><font color="#990033">${escapeHtml(row.term)}期四肖</font>:<span style="font-size: 14pt">${renderFontList(row.groups.xiao_4, hitSx)}</span></font></b></p>
        <p><b><font face="华文中宋"><font color="#990033">${escapeHtml(row.term)}期三肖</font>:<span style="font-size: 14pt">${renderFontList(row.groups.xiao_3, hitSx)}</span></font></b></p>
        <p><b><font face="华文中宋"><font color="#990033">${escapeHtml(row.term)}期二肖</font>:<span style="font-size: 14pt">${renderFontList(row.groups.xiao_2, hitSx)}</span></font></b></p>
    </td>
    <td align="left" height="40" bgcolor="#FFFFFF">
        <b><font face="华文中宋"><font color="#990033">${escapeHtml(row.term)}期五码</font>:<span style="font-size: 13pt">${renderDottedCodes(row.groups.code_5, hitCode)}</span></font></b>
        <p><b><font face="华文中宋"><font color="#990033">${escapeHtml(row.term)}期四码</font>:<span style="font-size: 14pt">${renderDottedCodes(row.groups.code_4, hitCode)}</span></font></b></p>
        <p><b><font face="华文中宋"><font color="#990033">${escapeHtml(row.term)}期三码</font>:<span style="font-size: 14pt">${renderDottedCodes(row.groups.code_3, hitCode)}</span></font></b></p>
        <p><b><font face="华文中宋"><font color="#990033">${escapeHtml(row.term)}期二码</font>:<span style="font-size: 14pt">${renderDottedCodes(row.groups.code_2, hitCode)}</span></font></b></p>
    </td>
</tr>`
    })
    .join("")

  return `<div class="box pad">
            ${renderLotteryTitleTable(lotteryTypeId, "五肖五码")}
            <table border="1" width="100%" id="table400923411">
                <tbody>${rows}</tbody>
            </table>
        </div>`
}

function renderPublicYixiaoYima(
  module: Extract<VendorHomepageModule, { module_key: "public_yixiao_yima" }> | undefined,
  lotteryTypeId: 1 | 2 | 3
) {
  if (!module?.history?.length) return ""
  const rows = module.history
    .map((row) => {
      const isHit =
        row.result.is_opened && row.result.res_sx === row.best_pick.xiao && row.result.res_code === row.best_pick.code
      const finalText = row.result.is_opened ? (isHit ? "100%,中！" : "未中") : "待开"
      return `<div class="neimu">
                <table width="100%" border="1">
    <thead>
    <tr>
        <th align="left" style="background-color: #CC0000">
            <p align="center">
                <font face="微软雅黑"><font size="4" style="color: #fff">${escapeHtml(getLotteryDisplayName(lotteryTypeId))}（公开一肖一码）</font></font>
            </p>
        </th>
    </tr>
    </thead>
    <tbody>
    <tr>
        <td style="text-align: left" bgcolor="#FFFFFF">
            <font face="微软雅黑">
                <font color="#000000">${escapeHtml(row.term)}期推荐九肖:</font>
                <font color="#FF0000">${renderFontList(row.xiao_groups.xiao_9)}</font>
                <font color="#0000FF">~~稳准狠</font>
            </font>
        </td>
    </tr>
    <tr>
        <td style="text-align: left" bgcolor="#FFFFFF">
            <font face="微软雅黑">
                <font color="#000000">${escapeHtml(row.term)}期推荐七肖:</font>
                <font color="#FF0000">${renderFontList(row.xiao_groups.xiao_7)}</font>
                <font color="#0000FF">~~稳准狠</font>
            </font>
        </td>
    </tr>
    <tr>
        <td style="text-align: left; height: 37px;" bgcolor="#FFFFFF">
            <font face="微软雅黑">
                <font color="#000000">${escapeHtml(row.term)}期推荐五肖:</font>
                <font color="#FF0000">${renderFontList(row.xiao_groups.xiao_5)}</font>
                <font color="#0000FF">~~稳准狠</font></font>
        </td>
    </tr>
    <tr>
        <td style="text-align: left; height: 37px;" bgcolor="#FFFFFF">
            <font face="微软雅黑">
                <font color="#000000">${escapeHtml(row.term)}期推荐三肖:</font>
                <font color="#FF0000">${renderFontList(row.xiao_groups.xiao_3)}</font>
                <font color="#0000FF">~~稳准狠</font></font>
        </td>
    </tr>
    <tr>
        <td style="text-align: left" bgcolor="#FFFFFF">
            <font face="微软雅黑" style="font-size: 11pt">
                <font color="#000000">精选14码:</font>
                <font color="#FF0000">${renderDottedCodes(row.code_groups.code_14)}</font></font>
        </td>
    </tr>
    <tr>
        <td style="text-align: left" bgcolor="#FFFFFF">
            <font face="微软雅黑">
                <font color="#000000">精选8码:</font>
                <font color="#FF0000">${renderDottedCodes(row.code_groups.code_8)}</font>
                <font color="#0000FF">~已确定100%</font>
            </font>
        </td>
    </tr>
    <tr>
        <td style="text-align: left" bgcolor="#FFFFFF">
            <font face="微软雅黑">
                <font color="#000000">精选5码:</font>
                <font color="#FF0000">${renderDottedCodes(row.code_groups.code_5)}</font>
                <font color="#0000FF">~已确定100%</font></font>
        </td>
    </tr>
    <tr>
        <td align="center" style="text-align: left" bgcolor="#FFFFFF">
            <p style="text-align: center">
                <font color="#000000" face="微软雅黑">本期推荐一肖一码(</font>
                <font color="#FF0000" face="微软雅黑">
                    <span style="font-size: 1.5em"><font>${escapeHtml(row.best_pick.xiao)}</font><font>${escapeHtml(row.best_pick.code)}</font></span></font>
                <font color="#000000" face="微软雅黑">)${finalText}</font></p>
        </td>
    </tr>
    </tbody>
</table>            </div>`
    })
    .join("")

  return `<div class="box pad" id="ayxym" style="margin:0px;">
            <div id="db1x"></div>
            <style>.neimu { line-height: 1.5; font-size: 18px; font-weight: bold;} .neimu table { color: #000; background: #fff;} .neimu table thead th { padding: 5px 10px; font-size: 24px; color: #fff; background: #CC0000;} .neimu table td { padding: 5px 10px; background: #fff;} @media screen and (max-width:800px){ .neimu { font-size: 16px;} .neimu table thead th { font-size: 20px;} }</style>
            ${rows}
        </div>`
}

function renderShujinguang(
  module: Extract<VendorHomepageModule, { module_key: "shujinguang" }> | undefined,
  lotteryTypeId: 1 | 2 | 3
) {
  if (!module?.history?.length) return ""
  const rows = module.history
    .map((row) => {
      const picks = row.picks.map((item) => escapeHtml(item)).join(".")
      const result = row.is_opened
        ? row.is_correct === false
          ? `<font color="#000000">${escapeHtml(row.result.res_code + row.result.res_sx)}错</font>`
          : `<font color="#FF0000">${escapeHtml(row.result.res_code + row.result.res_sx)}对</font>`
        : "??????"
      return `<tr>
                    <td width="100%" height="40">
                        <p align="center"><b><font face="楷体" style="font-size: 14pt">${escapeHtml(row.term)}期本期<font color="#FF0000" size="5" face="楷体">【${picks}】</font>输尽光（${result}）</font></b></p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="sjg" style="margin:0px;">
            ${renderLotteryTitleTable(lotteryTypeId, "本期输尽光")}
            <table style="border-collapse:collapse" border="1" width="100%" bgcolor="#ffffff">
                <tbody>${rows}</tbody>
            </table>
        </div>`
}

function renderTiandi2Xiao(
  module: Extract<VendorHomepageModule, { module_key: "tiandi_2xiao" }> | undefined,
  lotteryTypeId: 1 | 2 | 3
) {
  if (!module?.history?.length) return ""
  const rows = module.history
    .map((row) => {
      const hitSx = row.result.res_sx
      const tiandi = row.is_correct && !row.xiao_pair.includes(hitSx)
        ? `<span style="background-color: #FFFF00">${escapeHtml(row.tiandi)}</span>`
        : escapeHtml(row.tiandi)
      const xiaoPair = row.xiao_pair
        .map((item) =>
          row.is_correct && item === hitSx
            ? `<span style="background-color: #FFFF00">${escapeHtml(item)}</span>`
            : escapeHtml(item)
        )
        .join("")
      const result = renderPlainResult(row.result.result_text, row.result.is_opened, row.is_correct)

      return `<tr>
                    <td height="40" bgcolor="#FFFFFF">
                        <p align="center">
                            <b>
                                <font face="微软雅黑" size="4">${escapeHtml(row.term)}期天地肖</font>
                                <font color="#0000FF" face="微软雅黑" size="4">【${tiandi}+${xiaoPair}】</font>
                                <font face="微软雅黑" size="4">开
                                    <font color="#FF00FF">${result}</font></font>
                            </b>
                        </p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="tdzt" style="margin:0px;">
            <table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%" height="98">
                <tbody>
                <tr>
                    <td style="text-align:center" height="60">
                        ${renderLotteryTitleTable(lotteryTypeId, "天地两肖")}
                    </td>
                </tr>
                ${rows}
                </tbody>
            </table>
        </div>`
}

function highlightTouCode(touCode: string, resultCode: string, isCorrect: boolean | null) {
  if (!isCorrect) return escapeHtml(touCode)
  const hitDigits = new Set(resultCode.split(""))
  return touCode
    .split("")
    .map((digit) =>
      hitDigits.has(digit)
        ? `<span style="background-color: #FFFF00">${escapeHtml(digit)}</span>`
        : escapeHtml(digit)
    )
    .join("")
}

function renderDaxiao2Tou(
  module: Extract<VendorHomepageModule, { module_key: "daxiao_2tou" }> | undefined,
  lotteryTypeId: 1 | 2 | 3
) {
  if (!module?.history?.length) return ""
  const rows = module.history
    .map((row) => {
      const hitIsBig = Number.parseInt(row.result.res_code || "0", 10) >= 25
      const hitDx = hitIsBig ? "大" : "小"
      const daxiao = row.daxiao === hitDx
        ? `<span style="background-color: #FFFF00">${escapeHtml(row.daxiao)}数</span>`
        : `${escapeHtml(row.daxiao)}数`
      const touCode = highlightTouCode(row.tou_code, row.result.res_code, row.is_correct)
      const result = renderPlainResult(row.result.result_text, row.result.is_opened, row.is_correct)

      return `<tr>
                        <td height="38" bgcolor="#FFFFFF">
                            <p align="center">
                                <b>
                                    <font face="微软雅黑" size="4">${escapeHtml(row.term)}期</font>
                                    <font color="#0000FF" face="微软雅黑" size="4">【${daxiao}+${touCode}】</font>
                                    <font face="微软雅黑" size="4">开
                                        <font color="#FF00FF">${result}</font></font>
                                </b>
                            </p>
                        </td>
                    </tr>`
    })
    .join("")

  return `<div class="box pad" style="margin:0px;">
                ${renderLotteryTitleTable(lotteryTypeId, "大小+2头")}
                <table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%">
                    <tbody>${rows}</tbody>
                </table>
            </div>`
}

function renderShuangbo12Ma(
  module: Extract<VendorHomepageModule, { module_key: "shuangbo_12ma" }> | undefined,
  lotteryTypeId: 1 | 2 | 3
) {
  if (!module?.history?.length) return ""
  const rows = module.history
    .map((row) => {
      const hitWave = mapColorToWave(row.result.res_color)
      const hitCode = row.result.res_code
      const groups = row.wave_groups
        .map((group, index) => {
          const color = group.label === "红波" ? "red" : group.label === "蓝波" ? "blue" : "green"
          const label =
            row.result.is_opened && group.label === hitWave
              ? `<span style="background-color: #FFFF00">${escapeHtml(group.label)}</span>`
              : escapeHtml(group.label)
          const codes = group.codes
            .map((code, codeIndex) => {
              const prefix = codeIndex > 0 ? "." : ""
              return row.result.is_opened && code === hitCode
                ? `${prefix}<span style="background-color: #FFFF00">${escapeHtml(code)}</span>`
                : `${prefix}<font>${escapeHtml(code)}</font>`
            })
            .join("")
          return `${index > 0 ? `<font color="#FF0000"><br></font>` : ""}<font color="${color}">${label}:<font>${codes}</font></font>`
        })
        .join("")

      return `<tr>
                    <td height="40" bgcolor="#FFFFFF">
                        <p align="center">
                            <b>
                                <font face="微软雅黑" size="4" color="#000000">${escapeHtml(row.term)}期</font>
                                <font face="微软雅黑" size="4" color="#800000">【双波10码】</font>
                                <font face="微软雅黑" size="4" color="#000000">开</font>
                                <font face="微软雅黑" size="4" color="#FF0000">${row.is_opened ? escapeHtml(row.result.res_code + row.result.res_sx) : "?????"}</font>
                                <font face="微软雅黑" style="font-size: 14pt"><br>${groups}</font>
                            </b>
                        </p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="sb10m" style="margin:0px;">
            ${renderLotteryTitleTable(lotteryTypeId, "双波12码")}
            <table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%" height="100">
                <tbody>${rows}</tbody>
            </table>
        </div>`
}

function renderPt1Xiao(module: PublicModule | null, lotteryTypeId: 1 | 2 | 3) {
  const rows = toSourceRows(module)
  if (!rows.length) return ""
  const body = rows
    .map((row) => {
      const triple = repeatPrediction(row.prediction)
      const highlighted = highlightIf(escapeHtml(triple), row.isCorrect === true)
      return `<tr>
                    <td height="38">
                        <p align="center"><b><font face="微软雅黑" size="4">${escapeHtml(row.term)}期平特<font color="#FF0000">【${highlighted}】</font>开${renderPlainResult(row.result, row.isOpened, row.isCorrect)}</font></b></p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="ptyx" style="margin:0px;">
            ${renderLotteryTitleTable(lotteryTypeId, "平特一肖")}
            <table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%" height="50" bgcolor="#ffffff">
                <tbody>${body}</tbody>
            </table>
        </div>`
}

function renderPt1Wei(module: PublicModule | null, lotteryTypeId: 1 | 2 | 3) {
  const rows = toSourceRows(module)
  if (!rows.length) return ""
  const body = rows
    .map((row) => {
      const triple = parsePt1WeiTriple(row.prediction)
      const highlighted = highlightIf(escapeHtml(triple), row.isCorrect === true)
      return `<tr>
                    <td width="100%" height="40">
                        <p align="center">
                            <font face="楷体" style="font-size: 14pt">
                                <b>${escapeHtml(row.term)}期 平特一尾 <font color="#FF6600">【${highlighted}】</font>开${renderPlainResult(row.result, row.isOpened, row.isCorrect, "??????")}</b></font>
                        </p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="ptyw" style="margin:0px;">
            ${renderLotteryTitleTable(lotteryTypeId, "平特一尾")}
            <table style="border-collapse:collapse" border="1" width="100%" bgcolor="#ffffff">
                <tbody>${body}</tbody>
            </table>
        </div>`
}

function renderShuangbo(module: PublicModule | null, lotteryTypeId: 1 | 2 | 3) {
  const rows = toSourceRows(module)
  if (!rows.length) return ""
  const body = rows
    .map((row) => {
      const parts = row.prediction
        .split(/[,+，]/)
        .map((part) => part.trim())
        .filter(Boolean)
      const resColor = String(row.raw?.res_color || "")
      const hitWave = row.isOpened ? mapColorToWave(resColor.split(",").pop() || resColor) : ""
      const display = parts
        .map((part) => highlightIf(escapeHtml(part), part === hitWave && row.isCorrect === true))
        .join("+")
      return `<tr>
                    <td width="100%" height="40">
                        <p align="center">
                            <font face="楷体" style="font-size: 14pt">
                                <b>${escapeHtml(row.term)}期  <font color="#0000FF">【${display}】</font>开${renderPlainResult(row.result, row.isOpened, row.isCorrect, "??????")}</b></font>
                        </p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="sbzt" style="margin:0px;">
            ${renderLotteryTitleTable(lotteryTypeId, "双波")}
            <table style="border-collapse:collapse" border="1" width="100%" bgcolor="#ffffff">
                <tbody>${body}</tbody>
            </table>
        </div>`
}

function renderJuesha1Xiao(module: PublicModule | null, lotteryTypeId: 1 | 2 | 3) {
  const rows = toSourceRows(module)
  if (!rows.length) return ""
  const body = rows
    .map((row) => {
      const triple = repeatPrediction(row.prediction)
      const isKillSuccess = row.isOpened && parseResultParts(row.result).sx !== row.prediction
      const result = row.isOpened
        ? isKillSuccess
          ? `<font color="#FF0000">${escapeHtml(formatOpenResult(row.result))}对</font>`
          : `${escapeHtml(formatOpenResult(row.result))}<font color="#000">错</font>`
        : "?????"
      return `<tr>
                    <td height="39" bgcolor="#FFFFFF">
                        <p align="center">
                            <b>
                                <font face="隶书" size="4">${escapeHtml(row.term)}期：</font>
                                <font color="#008000" size="3" face="隶书">必杀一肖</font>
                                <font color="#FF00FF" size="3" face="隶书">『${escapeHtml(triple)}』</font>
                                <font face="隶书" size="4">开${result}</font></b>
                        </p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="bs1x" style="margin:0px;">
            <table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%" height="98">
                <tbody>
                <tr>
                    <td style="text-align:center" height="60">
                        ${renderLotteryTitleTable(lotteryTypeId, "必杀一肖")}
                    </td>
                </tr>
                ${body}
                </tbody>
            </table>
        </div>`
}

function renderDaxiao(module: PublicModule | null, lotteryTypeId: 1 | 2 | 3) {
  const rows = toSourceRows(module)
  if (!rows.length) return ""
  const body = rows
    .map((row) => {
      const content = getRowContent(row)
      const label = normalizeDaxiaoLabel(parseJsonStringArray(content)[0]?.split("|")[0]?.trim() || row.prediction)
      return `<p align="center" style="background-color: #FFFFFF; margin: 0; padding: 6px 0;">
                        <b>
                            <font face="微软雅黑" size="4">${escapeHtml(String(row.term).padStart(3, "0"))}期 </font>
                            <font color="#0000FF" face="微软雅黑" size="4">【${escapeHtml(label)}】</font>
                            <font face="微软雅黑" size="4">开
                                <font color="#FF00FF">${renderTwcaibawangResultSuffix(row.result, row.isOpened, row.isCorrect)}</font></font>
                        </b>
                    </p>`
    })
    .join("")

  return `<div class="box pad" id="dxzt" style="margin:0px;">
            ${renderLotteryTitleTable(lotteryTypeId, "大小中特")}
            ${body}
        </div>`
}

function render3Tou(module: PublicModule | null, lotteryTypeId: 1 | 2 | 3) {
  const rows = toSourceRows(module)
  if (!rows.length) return ""
  const body = rows
    .map((row) => {
      const content = getRowContent(row)
      const heads = parseJsonStringArray(content)
        .map((item) => extractTouDigitLabel(item.split("|")[0] || ""))
        .filter(Boolean)
      const hitDigit = row.isOpened ? parseResultParts(row.result).code.charAt(0) : ""
      const display = heads
        .map((head) =>
          row.isCorrect === true && head === hitDigit
            ? `<span style="background-color: #FFFF00">${escapeHtml(head)}</span>`
            : escapeHtml(head)
        )
        .join("-")
      return `<tr>
                    <td width="100%" height="40" align="center">
                        <b><font size="4" face="华文楷体">${escapeHtml(String(row.term).padStart(3, "0"))}期:三头必中<font color="#000080">【${display}】</font>开<font color="#FF0000">${renderTwcaibawangResultSuffix(row.result, row.isOpened, row.isCorrect)}</font></font></b>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="stzt" style="margin:0px;">
            ${renderLotteryTitleTable(lotteryTypeId, "三头中特")}
            <table style="border-collapse:collapse" border="1" width="100%" bgcolor="#ffffff">
                <tbody>${body}</tbody>
            </table>
        </div>`
}

function renderMa24(module: PublicModule | null, lotteryTypeId: 1 | 2 | 3) {
  const rows = toSourceRows(module)
  if (!rows.length) return ""
  const body = rows
    .map((row) => {
      const content = getRowContent(row)
      const codes = formatMa24Codes(content)
      const hitCode = row.isOpened ? parseResultParts(row.result).code : ""
      const lines = chunkArray(codes, 8)
        .slice(0, 3)
        .map((line) =>
          line
            .map((code) =>
              row.isCorrect === true && code === hitCode
                ? `<span style="background-color: #FFFF00">${escapeHtml(code)}</span>`
                : `<font>${escapeHtml(code)}</font>`
            )
            .join(".")
        )
        .join("<br>")

      return `<tr>
                    <td width="100%" height="40">
                        <p align="center"><b><font face="华文中宋" size="4" color="#CC3300"><span style="background-color: #FFFF00">${escapeHtml(String(row.term).padStart(3, "0"))}期香港六合彩24码开:${renderOpenResultCodeOnly(row.result, row.isOpened)}</span></font></b></p>
                        <p style="text-align: center"><span style="color: #0066FF; font-family: &quot;Microsoft YaHei&quot;, Arial, Helvetica, sans-serif; font-size: 18.3333px; font-weight: 700; text-align: center; background-color: #FFFFFF;">${lines}</span></p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="m24" style="margin:0px;">
            ${renderLotteryTitleTable(lotteryTypeId, "24码")}
            <table style="border-collapse:collapse" border="1" width="100%" bgcolor="#ffffff">
                <tbody>${body}</tbody>
            </table>
        </div>`
}

function renderYijuzhenyan(module: PublicModule | null, lotteryTypeId: 1 | 2 | 3) {
  const rows = toSourceRows(module)
  if (!rows.length) return ""
  const body = rows
    .map((row) => {
      const title = String(row.raw?.title || "").trim() || row.prediction
      const explanation = ensureSentence(String(row.raw?.content || row.prediction || ""))
      const jiexi = String(row.raw?.jiexi || "").trim()
      const hitSx = row.isOpened ? parseResultParts(row.result).sx : ""
      return `<tr style="background: #FFFF00;">
                    <td style="background-color: #CCFFCC; text-align: left">
                        <span class="zl"><font color="#000000">${escapeHtml(String(row.term).padStart(3, "0"))}期一句真言：${escapeHtml(title)}</font></span>
                    </td>
                </tr>
                <tr>
                    <td style="text-align: left; background-color: #FFFFFF">
                        <font color="#008000">真言解释：${escapeHtml(explanation)}</font><br>
                        <span class="zl"><font color="#000000">真言解肖主前：</font>${highlightZodiacChars(jiexi, hitSx)} 開:${renderSxCodeResult(row.result, row.isOpened)}</span>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="yjbt" style="margin:0px;">
            ${renderLotteryTitleTable(lotteryTypeId, "一句真言")}
            <table border="1" width="100%" class="duilianpt1" bgcolor="#ffffff" cellspacing="0" bordercolor="#FFFFFF" bordercolorlight="#FFFFFF" bordercolordark="#FFFFFF" cellpadding="2">
                <tbody>${body}</tbody>
            </table>
        </div>`
}

function renderSxjh3(module: PublicModule | null, lotteryTypeId: 1 | 2 | 3) {
  const rows = toSourceRows(module)
  if (!rows.length) return ""
  const groups: Array<{
    startTerm: string
    endTerm: string
    labels: string[]
    hitCount: number
  }> = []

  for (let index = 0; index < rows.length; index += 3) {
    const windowRows = rows.slice(index, index + 3)
    if (windowRows.length < 3) continue
    const latestRow = windowRows[0]
    const entries = parseLabelCodeEntries(getRowContent(latestRow)).slice(0, 4)
    const labels = entries.map((entry) => entry.label).filter(Boolean)
    if (!labels.length) continue
    const hitCount = windowRows.reduce((count, row) => {
      const hit = parseResultParts(row.result).sx
      return count + (row.isOpened && hit && labels.includes(hit) ? 1 : 0)
    }, 0)
    groups.push({
      startTerm: String(windowRows[windowRows.length - 1]?.term || "").padStart(3, "0"),
      endTerm: String(windowRows[0]?.term || "").padStart(3, "0"),
      labels,
      hitCount,
    })
  }

  const body = groups
    .map((group) => {
      const hitLabel = group.hitCount > 0 ? `中${group.hitCount}期` : "中几期"
      return `<tr>
                    <td bgcolor="#FFFFFF" style="text-align: left; padding: 8px 10px;">
                        <font color="#000000">${escapeHtml(group.startTerm)}-${escapeHtml(group.endTerm)}期: 三期中特→ [${escapeHtml(group.labels.join(""))}]开:${escapeHtml(hitLabel)}</font>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="sxjh3" style="margin:0px;">
            ${renderLotteryTitleTable(lotteryTypeId, "三期4肖")}
            <table border="1" width="100%" class="duilianpt1" bgcolor="#ffffff" cellspacing="0" bordercolor="#FFFFFF" bordercolorlight="#FFFFFF" bordercolordark="#FFFFFF" cellpadding="2">
                <tbody>${body}</tbody>
            </table>
        </div>`
}

function renderImageModule(module: PublicModule | null, anchor: string, title: string) {
  const url = getLatestImage(module)
  if (!url) return ""
  return `<div class="box amplIMG" id="${escapeAttr(anchor)}">
            <img src="${escapeAttr(url)}" style="width: 100%" title="${escapeAttr(title)}" alt="${escapeAttr(title)}">
        </div>`
}

function renderAttributeFooter(siteDomain: string) {
  const img1 = `/uploads/image/20250322/1742580086567063.png`
  const img2 = `/uploads/image/20250322/1742580119746508.jpg`
  const img3 = `/uploads/image/20250322/1742580130762983.jpg`
  const footerDomain = siteDomain || "twcaibawang.com"

  return `<div class="box pad" id="legacy-attribute-anchor">
			<div class="list-title">属性知识</div>
			<div id="legacy-attribute-gallery">
				<img src="${escapeAttr(img1)}" width="100%"/>
				<img src="${escapeAttr(img2)}" width="100%"/>
				<img src="${escapeAttr(img3)}" width="100%"/>
			</div>
		</div>
		<div class="box pad">
			<div class="foot-img">
				<p class="copyright">说明：本论坛所提供的内容、资料、图片和资讯，只应用在合法的资料探讨，暂不适用于其它，外围和使用。特此声明！</p>
				<p class="copyright">论坛免责声明：以上所有广告内容均为赞助商提供，本站不对其经营行为负责。浏览或使用者须自行承担有关责任，本网站恕不负责。</p>
				<p class="copyright">【香港天天彩官网】域名：${escapeHtml(footerDomain)}
					<br>長期收集各類最新、最準確的每期文字資料大全，最快開獎，公式規律盡在香港天天彩論壇
					<br>
				</p>
			</div>
		</div>`
}

function renderGenericModule(config: GenericModuleConfig, module: PublicModule | null, lotteryTypeId: 1 | 2 | 3) {
  if (config.mechanismKey === "yijuzhenyan") {
    return renderYijuzhenyan(module, lotteryTypeId)
  }
  if (config.mechanismKey === "title_197") {
    return renderSxjh3(module, lotteryTypeId)
  }
  const rows = toSourceRows(module)
  if (!rows.length) return ""
  const face = config.face || "微软雅黑"
  const body = rows
    .map((row) => {
      const prediction = highlightIf(escapeHtml(row.prediction), row.isCorrect === true)
      return `<tr>
                    <td height="39">
                        <p align="center">
                            <b>
                                <font face="${escapeAttr(face)}" size="4">${escapeHtml(row.term)}期</font>
                                <font color="${escapeAttr(config.predictionColor || "#0000FF")}" size="4" face="${escapeAttr(face)}">【${prediction}】</font>
                                <font face="${escapeAttr(face)}" size="4">开${renderPlainResult(row.result, row.isOpened, row.isCorrect)}</font>
                            </b>
                        </p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="${escapeAttr(config.anchor)}" style="margin:0px;">
            ${renderLotteryTitleTable(lotteryTypeId, config.title)}
            <table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%" bgcolor="#ffffff">
                <tbody>${body}</tbody>
            </table>
        </div>`
}

function buildKjSection(defaultLotteryTypeId: 1 | 2 | 3) {
  const activeOption =
    LOTTERY_TYPE_OPTIONS.find((item) => item.id === defaultLotteryTypeId) || LOTTERY_TYPE_OPTIONS[0]

  const tabItems = LOTTERY_TYPE_OPTIONS.map((item) => {
    const isActive = item.id === activeOption.id
    return `<li
        data-lottery-type-id="${item.id}"
        data-color="${escapeAttr(item.color)}"
        data-url="${escapeAttr(buildKjIframeUrl(item))}"
        class="${isActive ? "cur" : ""}"
      >${escapeHtml(item.label)}</li>`
  }).join("")

  return `<div class="box pad" style="margin:0px; padding: 0 8px">
            <div class="KJ-TabBox">
                <ul>${tabItems}</ul>
                <div></div>
                <div class="cur KJ-Panel" style="border-color:${escapeAttr(activeOption.color)}">
                    <iframe id="twcaibawang-kj-iframe" class="KJ-IFRAME" src="${escapeAttr(buildKjIframeUrl(activeOption))}" width="100%" height="180" frameborder="0" scrolling="no"></iframe>
                </div>
                <div></div>
                <div></div>
                <div></div>
                <div></div>
                <div></div>
                <div></div>
                <div></div>
            </div>
        </div>`
}

function buildPageHtml(
  siteData: PublicSitePageData,
  homepageModules: VendorHomepageModulesResponse,
  defaultLotteryTypeId: 1 | 2 | 3
) {
  const modules = siteData.modules || []
  const vendorModules = homepageModules.data || []
  const findVendor = <T extends VendorHomepageModule["module_key"]>(key: T) =>
    vendorModules.find((item) => item.module_key === key) as Extract<VendorHomepageModule, { module_key: T }> | undefined

  return [
    `<a name="fhdb"></a>`,
    `<div class="page-inner">`,
    `<div style="margin:0px;border:3px solid #CC0000">`,
    `<img src="/vendor/twcaibawang.com/static/picture/2a9a358904487e3d801e2df8d85e4344.png" width="100%" alt="香港天下彩">`,
    `<div id="nav2" class="nav2" data-fixed="">
    <ul>
        <li><a href="#ayxym">一肖一码</a></li>
        <li><a href="#gslist">高手资料</a></li>
        <li><a href="#ptyx">平特一肖</a></li>
        <li><a href="#sjg">输尽光</a></li>
        <li><a href="#bs1x">必杀一肖</a></li>
        <li><a href="/index/index/history.html">历史记录</a></li>
    </ul>
</div>`,
    `<div class="box"></div>`,
    `<div class="white-box">
            <p><img src="/vendor/twcaibawang.com/static/picture/1d607f54b7065f875c81355226df5c68.gif" alt="805.gif"></p>
        </div>`,
    buildKjSection(defaultLotteryTypeId),
    `<div class="box news-box" style="font-size:16px; font-weight:bold">
    <div class="news-title">最新消息：</div>
    <div class="txtMarquee-left"><marquee scrollamount="3" scrolldelay="50" direction="left" onmouseover="this.stop();" onmouseout="this.start();" style="color:red">${escapeHtml(siteData.site.announcement || "香港天下彩资料已接入当前项目后台 API，首页预测模块按源站结构动态渲染。")}</marquee></div>
</div>`,
    `<div class="box">
            <p><img src="/vendor/twcaibawang.com/static/picture/9dc46b1cf36b41503755bad0477ab6c5.gif" alt="2.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/2a1141c5b7e73b93c353596e0224e956.gif" alt="1.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/7d9fe06ba7056ee3cc989657e3e1968b.gif" alt="8.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/1789fd79ba4c317a694919c97a6c79d1.gif" alt="3.gif"></p>
        </div>`,
    // `<div class="box amplIMG">
    //         <img src="/vendor/twcaibawang.com/static/picture/chiahla_1086_125_1146.png" style="width: 100%" title="" alt="">
    //     </div>`,
    renderImageModule(resolveModule(modules, "sxztu"), "sxztu", "四不像图"),
    renderWuxiaoWuma(findVendor("wuxiao_wuma"), defaultLotteryTypeId),
    `<div class="box amplIMG">
            <p><img src="/vendor/twcaibawang.com/static/picture/2765121603ed96e8e483970e2ddb8b5a.gif" alt="2765121603ed96e8e483970e2ddb8b5a.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/986d680d994f83b45386956911f934fd.gif" alt="986d680d994f83b45386956911f934fd.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/90bdc09a6a9709d8c50c9d56e0655ac4.jpg" alt="80.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/d0a4a366207f221cb3c04f0aae87b6ec.jpg" alt="tuhua32.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/5c04963e886993e13f526d1b81a96177.gif" alt=""></p><p><img src="/vendor/twcaibawang.com/static/picture/98edfdac8ec8f851bc12cc9c962bdd33.gif" alt=""></p>
        </div>`,
    renderPt1Xiao(resolveModule(modules, "pt1xiao"), defaultLotteryTypeId),
    renderPt1Wei(resolveModule(modules, "pt1wei"), defaultLotteryTypeId),
    // `<div class="box amplIMG">
    //         <img src="/vendor/twcaibawang.com/static/picture/chiahla_1067_125_1105.jpg" style="width: 100%" title="" alt="">
    //     </div>`,
    renderImageModule(resolveModule(modules, "brainteaser"), "brainteaser", "脑筋急转弯"),
    
    `<div class="box">
            <p><img src="/vendor/twcaibawang.com/static/picture/bdd6df8c288d350b2f8190262f8cdc4d.gif" alt="5.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/9c0dc53ff1f382fae3a80e13236b4c4a.gif" alt="6.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/1789fd79ba4c317a694919c97a6c79d1.gif" alt="3.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/8e4351209fcbaedf6de64212d5c079bf.gif" alt="7.gif"></p>
        </div>`,
    renderShuangbo(resolveModule(modules, "shuangbo"), defaultLotteryTypeId),
    `<div class="box">
            <p><img src="/vendor/twcaibawang.com/static/picture/8e4351209fcbaedf6de64212d5c079bf.gif" alt="7.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/2a1141c5b7e73b93c353596e0224e956.gif" alt="1.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/7d9fe06ba7056ee3cc989657e3e1968b.gif" alt="8.gif"></p>
        </div>`,
    // `<div class="box amplIMG">
    //         <img src="/vendor/twcaibawang.com/static/picture/chiahla_1053_125_1127.png" style="width: 100%" title="" alt="">
    //     </div>`,
    renderImageModule(resolveModule(modules, "pmtj_image"), "pmtj-image", "跑马图解"),
    
    renderTiandi2Xiao(findVendor("tiandi_2xiao"), defaultLotteryTypeId),
    // `<div class="box amplIMG">
    //         <img src="/vendor/twcaibawang.com/static/picture/chiahla_1035_125_1104.png" style="width: 100%" title="" alt="">
    //     </div>`,
    renderImageModule(resolveModule(modules, "tw_pmt_image"), "tw-pmt-image", "台湾跑马图"),
    
    `<div class="box amplIMG">
            <p><img src="/vendor/twcaibawang.com/static/picture/8d8e0c09a5cb36948161cb7c9ff72553.jpg" alt=""><img src="/vendor/twcaibawang.com/static/picture/2765121603ed96e8e483970e2ddb8b5a.gif" alt=""></p><p><img src="/vendor/twcaibawang.com/static/picture/8d45ce25e17db9940efc4ec9b26911c8.gif" alt=""></p>
        </div>`,
    renderDaxiao2Tou(findVendor("daxiao_2tou"), defaultLotteryTypeId),
    renderPublicYixiaoYima(findVendor("public_yixiao_yima"), defaultLotteryTypeId),
   `<div class="box amplIMG">
            <p><img src="/vendor/twcaibawang.com/static/picture/201c1ae2c49d4e2bf0debe240baad433.jpg" alt=""><img src="/vendor/twcaibawang.com/static/picture/90bdc09a6a9709d8c50c9d56e0655ac4.gif" alt=""></p><p><img src="/vendor/twcaibawang.com/static/picture/17f9be2108da031fe3ad2d75ae33ede7.jpg" alt=""></p>
        </div>`,
    renderShujinguang(findVendor("shujinguang"), defaultLotteryTypeId),
    renderJuesha1Xiao(resolveModule(modules, "juesha1xiao"), defaultLotteryTypeId),
    `<div class="box amplIMG">
            <p><img src="/vendor/twcaibawang.com/static/picture/bdd6df8c288d350b2f8190262f8cdc4d.gif" alt=""><img src="/vendor/twcaibawang.com/static/picture/9c0dc53ff1f382fae3a80e13236b4c4a.gif" alt=""></p>
        </div>`,
    renderShuangbo12Ma(findVendor("shuangbo_12ma"), defaultLotteryTypeId),
    renderMa24(resolveModule(modules, "ma24"), defaultLotteryTypeId),
    render3Tou(resolveModule(modules, "3tou"), defaultLotteryTypeId),
    renderDaxiao(resolveModule(modules, "daxiao"), defaultLotteryTypeId),
    ...GENERIC_MODULES.map((config) => renderGenericModule(config, resolveModule(modules, config.mechanismKey), defaultLotteryTypeId)),
    renderAttributeFooter(siteData.site.domain),
    `</div>`,
    `<a href="#fhdb" class="return-top">
        <p align="center">
            <span style="font-weight: 500; ">
                <font size="6" face="微软雅黑">返回顶部</font>
            </span>
        </p>
    </a>`,
    `</div>`,
  ].join("")
}

export function TwcaibawangHomeClient({
  siteData,
  homepageModules,
  defaultLotteryTypeId,
}: TwcaibawangHomeClientProps) {
  const [activeLotteryTypeId, setActiveLotteryTypeId] = useState<1 | 2 | 3>(defaultLotteryTypeId)
  const [currentSiteData, setCurrentSiteData] = useState(siteData)
  const [currentHomepageModules, setCurrentHomepageModules] = useState(homepageModules)

  useEffect(() => {
    setActiveLotteryTypeId(defaultLotteryTypeId)
    setCurrentSiteData(siteData)
    setCurrentHomepageModules(homepageModules)
  }, [defaultLotteryTypeId, homepageModules, siteData])

  const html = useMemo(
    () => buildPageHtml(currentSiteData, currentHomepageModules, activeLotteryTypeId),
    [activeLotteryTypeId, currentHomepageModules, currentSiteData]
  )

  useEffect(() => {
    document.body.style.background = "#f7f0dc"

    const nav = document.getElementById("nav2")
    const tabList = document.querySelector(".KJ-TabBox ul")
    const getTabs = () => Array.from(document.querySelectorAll<HTMLLIElement>(".KJ-TabBox ul li"))
    const panels = Array.from(document.querySelectorAll<HTMLElement>(".KJ-TabBox > div"))
    const iframe = document.getElementById("twcaibawang-kj-iframe") as HTMLIFrameElement | null
    const navTop = nav?.offsetTop ?? 0

    const onScroll = () => {
      if (!nav) return
      const scrollTop = document.documentElement.scrollTop || document.body.scrollTop
      nav.setAttribute("data-fixed", scrollTop >= navTop ? "fixed" : "")
    }

    const onTabClick = async (target: HTMLLIElement) => {
      if (!iframe) return
      const url = target.dataset.url || iframe.src
      const color = target.dataset.color || "#de2910"
      const lotteryTypeId = (() => {
        const direct = Number.parseInt(target.dataset.lotteryTypeId || "", 10)
        if (Number.isInteger(direct)) return direct as 1 | 2 | 3
        const match = url.match(/[?&]lottery_type=(\d+)/)
        const fallback = Number.parseInt(match?.[1] || "", 10)
        return (Number.isInteger(fallback) ? fallback : activeLotteryTypeId) as 1 | 2 | 3
      })()

      const tabs = getTabs()
      tabs.forEach((item) => item.classList.remove("cur"))
      tabs.forEach((item) => item.setAttribute("aria-pressed", "false"))
      panels.forEach((panel) => {
        panel.classList.remove("cur")
        panel.style.borderColor = ""
      })

      target.classList.add("cur")
      target.setAttribute("aria-pressed", "true")
      if (panels[1]) {
        panels[1].classList.add("cur")
        panels[1].style.borderColor = color
      }
      iframe.src = url
      iframe.height = "180"
      if (!Number.isInteger(lotteryTypeId) || lotteryTypeId === activeLotteryTypeId) return

      setActiveLotteryTypeId(lotteryTypeId)
      try {
        const [siteResp, vendorResp] = await Promise.all([
          fetch(
            `/api/public/site-page?site_id=${encodeURIComponent(String(currentSiteData.site.id))}&history_limit=8&lottery_type=${encodeURIComponent(String(lotteryTypeId))}`,
            { cache: "no-store" }
          ),
          fetch(
            `/api/vendor/homepage-modules?site_id=${encodeURIComponent(String(currentSiteData.site.id))}&history_limit=8&lottery_type=${encodeURIComponent(String(lotteryTypeId))}&modules=${encodeURIComponent("wuxiao_wuma,public_yixiao_yima,shuangbo_12ma,shujinguang,daxiao_2tou,tiandi_2xiao")}`,
            { cache: "no-store" }
          ),
        ])
        if (siteResp.ok) {
          const nextSiteData = (await siteResp.json()) as PublicSitePageData
          setCurrentSiteData(nextSiteData)
        }
        if (vendorResp.ok) {
          const nextVendorData = (await vendorResp.json()) as VendorHomepageModulesResponse
          setCurrentHomepageModules(nextVendorData)
        }
      } catch {
        // Keep the current view if the lottery-specific refresh fails.
      }
    }

    const onTabListClick = (event: Event) => {
      const target = event.target as HTMLElement | null
      const li = target?.closest("li")
      if (!li || !(li instanceof HTMLLIElement)) return
      void onTabClick(li)
    }

    tabList?.addEventListener("click", onTabListClick)
    window.addEventListener("scroll", onScroll, { passive: true })
    onScroll()

    return () => {
      tabList?.removeEventListener("click", onTabListClick)
      window.removeEventListener("scroll", onScroll)
      document.body.style.background = ""
    }
  }, [activeLotteryTypeId, currentSiteData.site.id, html])

  return (
    <div className="page">
      <style jsx global>{`
        img {
          max-width: 100%;
        }
        .page {
          position: relative;
          padding: 0 0 70px 0;
          width: 800px;
          min-height: 100%;
          margin: 0 auto;
          background-color: white;
          overflow: hidden;
        }
        .page-inner {
          width: 100%;
        }
        .box {
          width: 100%;
        }
        .nav2 {
          width: 100%;
          max-width: 800px;
          margin: 0 auto;
          box-sizing: border-box;
          padding: 2px;
          font-size: 13px;
          background: #fff;
        }
        .nav2 ul {
          padding: 2px 0;
          display: flex;
          justify-content: space-between;
          margin: 0;
        }
        .nav2 ul li {
          width: 100%;
          box-sizing: border-box;
          padding: 0;
          list-style: none;
        }
        .nav2 ul li a {
          display: block;
          line-height: 33px;
          text-align: center;
          color: #fff;
          background: #ac0000;
          text-decoration: none;
        }
        .nav2 ul li a:hover {
          background: #da183b;
        }
        #nav2[data-fixed="fixed"] {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          margin: auto;
          z-index: 1;
          box-shadow: 0 5px 10px rgba(0, 0, 0, 0.1);
        }
        .white-box table {
          border-collapse: collapse;
        }
        .white-box table td {
          border-collapse: collapse;
          border: 1px solid #f5f5f5;
        }
        .KJ-TabBox ul {
          display: flex;
          gap: 0;
          width: 100%;
          border: 1px solid #1e3a8a;
          border-bottom: 0;
          background: #1e3a8a;
        }
        .KJ-TabBox ul,
        .KJ-TabBox li {
          margin: 0;
          list-style: none;
          padding: 0;
          border: 0;
          font-size: 16px;
        }
        .KJ-TabBox li {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 42px;
          padding: 0 12px;
          color: #ffffff;
          cursor: pointer;
          text-align: center;
          flex: 1;
          font-weight: 700;
          background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%);
          box-sizing: border-box;
          border-right: 1px solid rgba(255, 255, 255, 0.26);
          user-select: none;
          transition:
            background-color 120ms ease,
            color 120ms ease,
            box-shadow 120ms ease,
            transform 120ms ease;
        }
        .KJ-TabBox li:last-child {
          border-right: 0;
        }
        .KJ-TabBox li:hover {
          background: linear-gradient(180deg, #1d4ed8 0%, #1e40af 100%);
        }
        .KJ-TabBox li:active {
          background: linear-gradient(180deg, #1e40af 0%, #1e3a8a 100%);
          transform: translateY(1px);
        }
        .KJ-TabBox li.cur {
          color: #ffffff;
          background: linear-gradient(180deg, #dc2626 0%, #b91c1c 100%);
          cursor: default;
          box-shadow: inset 0 -2px 0 rgba(0, 0, 0, 0.15);
        }
        .KJ-TabBox > div {
          border-top: 1px solid #b91c1c;
          margin-top: -1px;
          display: none;
        }
        .KJ-TabBox > div.cur {
          display: block !important;
          border-color: #b91c1c;
        }
        .KJ-TabBox .KJ-Panel {
          border: 1px solid #b91c1c;
          background: #ffffff;
        }
        .KJ-TabBox .KJ-IFRAME {
          background: white;
          display: block;
        }
        .news-title {
          float: left;
          height: 35px;
          line-height: 35px;
          padding-left: 5px;
          border-top-left-radius: 4px;
          border-bottom-left-radius: 4px;
        }
        .txtMarquee-left {
          padding: 0 5px;
          width: auto;
          position: relative;
          height: 35px;
          line-height: 35px;
          overflow: hidden;
        }
        .return-top {
          color: blue;
          text-decoration: none;
        }
        .return-top:hover {
          color: red;
          cursor: pointer;
        }
        .list-title {
          line-height: 38px;
          text-align: center;
          color: #ffffff;
          background: #cc0000;
          border: 1px solid #b30000;
          font-size: 18px;
          font-weight: 700;
        }
        #legacy-attribute-gallery img {
          display: block;
          width: 100%;
        }
        .foot-img {
          padding: 10px 8px 2px;
          text-align: center;
          background: #ffffff;
        }
        .copyright {
          margin: 0 0 8px;
          color: #000000;
          font-family: "Microsoft YaHei", sans-serif;
          font-size: 12px;
          line-height: 1.7;
        }
        html {
          scroll-padding-top: 200px;
        }
        @media screen and (max-width: 800px) {
          .page {
            width: 100%;
            margin: 0;
          }
          .nav2 {
            padding: 4px;
            font-size: 16px;
          }
          .nav2 ul {
            padding: 4px 0;
          }
          .nav2 ul li {
            padding: 0 1px;
          }
          .nav2 ul li a {
            padding: 5px 0;
            cursor: pointer;
          }
          .KJ-TabBox ul,
          .KJ-TabBox li {
            font-size: 15px;
          }
          .KJ-TabBox li {
            min-height: 40px;
            padding: 0 8px;
          }
        }
        @media screen and (max-width: 420px) {
          .box.pad td * {
            font-size: 15px;
          }
          .nav2 ul li a {
            font-weight: bold;
          }
          .KJ-TabBox ul,
          .KJ-TabBox li {
            font-size: 14px;
          }
        }
      `}</style>
      <div dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  )
}
