"use client"

import { useEffect, useMemo } from "react"
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
  headerText?: string
  face?: string
  titleColor?: string
  predictionColor?: string
}

type SourceRow = {
  issue: string
  term: string
  prediction: string
  result: string
  isOpened: boolean
  isCorrect: boolean | null
}

const LOTTERY_TYPE_OPTIONS: LotteryTypeOption[] = [
  { id: 1, label: "香港天天彩", iframeLabel: "香港天天彩", color: "#00c6ff", drawLotteryType: 1 },
  { id: 2, label: "新澳门六合彩", iframeLabel: "新澳门六合彩", color: "#0084ff", drawLotteryType: 2 },
  { id: 3, label: "香港六合彩", iframeLabel: "香港六合彩", color: "#de2910", drawLotteryType: 3 },
]

const GENERIC_MODULES: GenericModuleConfig[] = [
  { anchor: "qqsh", title: "琴棋书画", mechanismKey: "qinqi", face: "微软雅黑", predictionColor: "#FF0000" },
  { anchor: "szpt", title: "四字平特", mechanismKey: "sizixuanji", face: "微软雅黑", predictionColor: "#FF0000" },
  { anchor: "yjbt", title: "一句真言", mechanismKey: "yijuzhenyan", face: "微软雅黑", predictionColor: "#008000" },
  { anchor: "bz9x", title: "9肖中特", mechanismKey: "9xzt", face: "微软雅黑", predictionColor: "#FF0000" },
  { anchor: "m24", title: "24码", mechanismKey: "ma24", face: "微软雅黑", predictionColor: "#0000FF" },
  { anchor: "sxjh3", title: "三期4肖", mechanismKey: "title_197", face: "微软雅黑", predictionColor: "#0000FF" },
  { anchor: "stzt", title: "3头中特", mechanismKey: "3tou", face: "微软雅黑", predictionColor: "#0000FF" },
  { anchor: "x912m", title: "9肖12码", mechanismKey: "9xiao12ma", face: "微软雅黑", predictionColor: "#0000FF" },
  { anchor: "dxzt", title: "大小中特", mechanismKey: "daxiao", face: "微软雅黑", predictionColor: "#0000FF" },
  { anchor: "jsyb", title: "绝杀半波", mechanismKey: "jueshabanbo", face: "微软雅黑", predictionColor: "#0000FF" },
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
  return value
    .replace(/^\[/, "")
    .replace(/\]$/, "")
    .replace(/"/g, "")
    .replace(/,/g, "")
}

function toSourceRows(module: PublicModule | null): SourceRow[] {
  if (!module) return []
  return module.history.map((row) => ({
    issue: row.issue || `${row.year || ""}${row.term || ""}`.trim(),
    term: row.term || "",
    prediction: normalizePredictionText(String(row.prediction_text || "")),
    result: String(row.result_text || ""),
    isOpened: !!row.is_opened,
    isCorrect: row.is_correct ?? null,
  }))
}

function getLatestImage(module: PublicModule | null) {
  if (!module) return ""
  const latest = module.history.find((row) => String(row.image_url || "").trim())
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

function renderResult(resultText: string, isOpened: boolean, isCorrect: boolean | null) {
  if (!isOpened) return `<font color="#FF00FF">???????</font>`
  const text = escapeHtml(formatOpenResult(resultText))
  if (isCorrect === false) {
    return `${text}<font color="#000">错</font>`
  }
  return `<font color="#FF0000">${text}对</font>`
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

function renderWuxiaoWuma(module: Extract<VendorHomepageModule, { module_key: "wuxiao_wuma" }> | undefined) {
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
            <table border="1" width="100%" bgcolor="#ffffff">
                <tbody>
                    <tr>
                        <td style="border:10px double #CC0000; height: 50px" bgcolor="#CC0000">
                            <p align="center">
                                <b>
                                    <font face="楷体" style="font-size: 18pt">
                                        <font color="#FFFF00">香港天天彩</font>
                                        <font color="#FFFF00" size="5" face="华文中宋">五肖五码</font>
                                    </font>
                                </b>
                            </p>
                        </td>
                    </tr>
                </tbody>
            </table>
            <table border="1" width="100%" id="table400923411">
                <tbody>${rows}</tbody>
            </table>
        </div>`
}

function renderPublicYixiaoYima(module: Extract<VendorHomepageModule, { module_key: "public_yixiao_yima" }> | undefined) {
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
                <font face="微软雅黑"><font size="4" style="color: #fff">香港天天彩（公开一肖一码）</font></font>
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
                <font color="#000000" face="微软雅黑">本期推荐一肖一码:(</font>
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
            <style>.neimu { line-height: 1.5; font-size: 18px; font-weight: bold;} .neimu table { color: #0F0; background: #000;} .neimu table thead th { padding: 5px 10px; font-size: 24px; color: #f00; background: #ff0;} .neimu table td { padding: 5px 10px;} @media screen and (max-width:800px){ .neimu { font-size: 16px;} .neimu table thead th { font-size: 20px;} }</style>
            ${rows}
        </div>`
}

function renderShujinguang(module: Extract<VendorHomepageModule, { module_key: "shujinguang" }> | undefined) {
  if (!module?.history?.length) return ""
  const rows = module.history
    .map((row) => {
      const picks = row.picks.map((item) => escapeHtml(item)).join(".")
      const result = row.is_opened
        ? row.is_correct === false
          ? `<font color="#000000">${escapeHtml(row.result.res_code + row.result.res_sx)}错</font>`
          : `<font color="#FF0000">${escapeHtml(row.result.res_code + row.result.res_sx)}对</font>`
        : `??????`
      return `<tr>
                    <td width="100%" height="40">
                        <p align="center"><b><font face="楷体" style="font-size: 14pt">${escapeHtml(row.term)}期本期<font color="#FF0000" size="5" face="楷体">【${picks}】</font>输尽光（${result}）</font></b></p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="sjg" style="margin:0px;">
            <table border="1" width="100%" bgcolor="#ffffff">
                <tbody>
                <tr>
                    <td style="border:10px double #CC0000; height: 50px;" bgcolor="#CC0000">
                        <p align="center">
                            <b>
                                <font face="楷体" style="font-size: 18pt">
                                    <font color="#FFFF00">香港天天彩</font>
                                    <font color="#FFFFFF">『本期输尽光』</font></font>
                            </b>
                        </p>
                    </td>
                </tr>
                </tbody>
            </table>
            <table style="border-collapse:collapse" border="1" width="100%" bgcolor="#ffffff">
                <tbody>${rows}</tbody>
            </table>
        </div>`
}

function renderTiandi2Xiao(module: Extract<VendorHomepageModule, { module_key: "tiandi_2xiao" }> | undefined) {
  if (!module?.history?.length) return ""
  const rows = module.history
    .map((row) => {
      const hitSx = row.result.res_sx
      const shouldHighlightTiandi = !!row.is_correct && !row.xiao_pair.includes(hitSx)
      const tiandi = shouldHighlightTiandi
        ? `<span style="background-color: #FFFF00">${escapeHtml(row.tiandi)}</span>`
        : escapeHtml(row.tiandi)
      const xiaoPair = row.xiao_pair
        .map((item) =>
          row.is_correct && item === hitSx
            ? `<span style="background-color: #FFFF00">${escapeHtml(item)}</span>`
            : escapeHtml(item)
        )
        .join("")

      return `<tr>
                    <td height="40">
                        <p align="center">
                            <b>
                                <font face="微软雅黑" size="4">${escapeHtml(row.term)}期天地肖</font>
                                <font color="#0000FF" face="微软雅黑" size="4">【${tiandi}+${xiaoPair}】</font>
                                <font face="微软雅黑" size="4">开
                                    <font color="#FF00FF">${renderResult(row.result.result_text, row.result.is_opened, row.is_correct)}</font></font>
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
                        <table border="1" width="100%" bgcolor="#ffffff">
                            <tbody>
                            <tr>
                                <td style="border:10px double #CC0000; height: 50px;" bgcolor="#CC0000">
                                    <p align="center">
                                        <b>
                                            <font face="楷体" style="font-size: 18pt">
                                                <font color="#FFFF00">香港天天彩</font>
                                                <font color="#FFFFFF">『天地两肖』</font></font>
                                        </b>
                                    </p>
                                </td>
                            </tr>
                            </tbody>
                        </table>
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

function renderDaxiao2Tou(module: Extract<VendorHomepageModule, { module_key: "daxiao_2tou" }> | undefined) {
  if (!module?.history?.length) return ""
  const rows = module.history
    .map((row) => {
      const hitIsBig = Number.parseInt(row.result.res_code || "0", 10) >= 25
      const hitDx = hitIsBig ? "大" : "小"
      const daxiao = row.daxiao === hitDx
        ? `<span style="background-color: #FFFF00">${escapeHtml(row.daxiao)}数</span>`
        : `${escapeHtml(row.daxiao)}数`
      const touCode = highlightTouCode(row.tou_code, row.result.res_code, row.result.res_code.startsWith(row.tou_code[0]))
      return `<tr>
                        <td height="38">
                            <p align="center">
                                <b>
                                    <font face="微软雅黑" size="4">${escapeHtml(row.term)}期</font>
                                    <font color="#0000FF" face="微软雅黑" size="4">【${daxiao}+${touCode}】</font>
                                    <font face="微软雅黑" size="4">开
                                        <font color="#FF00FF">${renderResult(row.result.result_text, row.result.is_opened, row.is_correct)}</font></font>
                                </b>
                            </p>
                        </td>
                    </tr>`
    })
    .join("")

  return `<div class="box pad" style="margin:0px;">
                <table border="1" width="100%" bgcolor="#ffffff">
                    <tbody>
                    <tr>
                        <td style="border:10px double #CC0000; height: 50px;" bgcolor="#CC0000">
                            <p align="center">
                                <b>
                                    <font face="楷体" style="font-size: 18pt">
                                        <font color="#FFFF00">香港天天彩</font>
                                        <font color="#FFFFFF">『大小+2头』</font></font>
                                </b>
                            </p>
                        </td>
                    </tr>
                    </tbody>
                </table>
                <table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%">
                    <tbody>${rows}</tbody>
                </table>
            </div>`
}

function renderShuangbo12Ma(module: Extract<VendorHomepageModule, { module_key: "shuangbo_12ma" }> | undefined) {
  if (!module?.history?.length) return ""
  const rows = module.history
    .map((row) => {
      const hitColor = row.result.res_color
      const hitCode = row.result.res_code
      const groups = row.wave_groups
        .map((group, index) => {
          const color = group.label === "红波" ? "red" : group.label === "蓝波" ? "blue" : "green"
          const label =
            row.result.is_opened && group.label === hitColor
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
          return `${index > 0 ? `<font color="#FF0000"><br></font>` : ""}<font color="${color}">${label}:` +
            `<font>${codes}</font></font>`
        })
        .join("")

      return `<tr>
                    <td height="40">
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
            <table border="1" width="100%" bgcolor="#ffffff">
                <tbody>
                <tr>
                    <td style="border:10px double #CC0000; height: 50px;" bgcolor="#CC0000">
                        <p align="center">
                            <b>
                                <font face="楷体" style="font-size: 18pt">
                                    <font color="#FFFF00">香港天天彩</font>
                                    <font color="#FFFFFF">『双波12码』</font></font>
                            </b>
                        </p>
                    </td>
                </tr>
                </tbody>
            </table>
            <table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%" height="100">
                <tbody>${rows}</tbody>
            </table>
        </div>`
}

function renderPt1Xiao(module: PublicModule | null) {
  const rows = toSourceRows(module)
  if (!rows.length) return ""
  const body = rows
    .map((row) => {
      const triple = repeatPrediction(row.prediction)
      const highlighted = highlightIf(escapeHtml(triple), row.isCorrect === true)
      return `<tr>
                    <td height="38">
                        <p align="center"><b><font face="微软雅黑" size="4">${escapeHtml(row.term)}期平特<font color="#FF0000">【${highlighted}】</font>开${renderResult(row.result, row.isOpened, row.isCorrect)}</font></b></p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="ptyx" style="margin:0px;">
            ${renderTitleTable(`<font color="#FFFF00">香港天天彩</font><font color="#FFFFFF">『平特一肖』</font>`)}
            <table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%" height="50">
                <tbody>${body}</tbody>
            </table>
        </div>`
}

function renderPt1Wei(module: PublicModule | null) {
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
                                <b>${escapeHtml(row.term)}期 平特一尾 <font color="#FF6600">【${highlighted}】</font>开${renderResult(row.result, row.isOpened, row.isCorrect)}</b></font>
                        </p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="ptyw" style="margin:0px;">
            ${renderTitleTable(`<font color="#FFFF00">香港天天彩『平特一尾』</font>`)}
            <table style="border-collapse:collapse" border="1" width="100%" bgcolor="#ffffff">
                <tbody>${body}</tbody>
            </table>
        </div>`
}

function renderShuangbo(module: PublicModule | null) {
  const rows = toSourceRows(module)
  if (!rows.length) return ""
  const body = rows
    .map((row) => {
      const parts = row.prediction
        .split(/[,+，]/)
        .map((part) => part.trim())
        .filter(Boolean)
      const hitWave = row.isOpened ? mapColorToWave(parseResultParts(row.result).raw ? ((module?.history.find((item) => item.term === row.term)?.raw?.res_color as string) || "") : "") : ""
      const isHit = row.isOpened && parts.some((part) => part === hitWave)
      const display = parts
        .map((part) => highlightIf(escapeHtml(part), part === hitWave && isHit))
        .join("+")
      return `<tr>
                    <td width="100%" height="40">
                        <p align="center">
                            <font face="楷体" style="font-size: 14pt">
                                <b>${escapeHtml(row.term)}期  <font color="#0000FF">【${display}】</font>开${renderResult(row.result, row.isOpened, isHit)}</b></font>
                        </p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="sbzt" style="margin:0px;">
            ${renderTitleTable(`<font color="#FFFF00">香港天天彩『双波』</font>`)}
            <table style="border-collapse:collapse" border="1" width="100%" bgcolor="#ffffff">
                <tbody>${body}</tbody>
            </table>
        </div>`
}

function renderJuesha1Xiao(module: PublicModule | null) {
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
        : `?????`
      return `<tr>
                    <td height="39">
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
                        <table border="1" width="100%" bgcolor="#ffffff">
                            <tbody>
                            <tr>
                                <td style="border:10px double #CC0000; height: 50px;" bgcolor="#CC0000">
                                    <p align="center">
                                        <b>
                                            <font face="楷体" style="font-size: 18pt">
                                                <font color="#FFFF00">香港天天彩</font>
                                                <font color="#FFFFFF">『必杀一肖』</font></font>
                                        </b>
                                    </p>
                                </td>
                            </tr>
                            </tbody>
                        </table>
                    </td>
                </tr>
                ${body}
                </tbody>
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

function renderGenericModule(config: GenericModuleConfig, module: PublicModule | null) {
  const rows = toSourceRows(module)
  if (!rows.length) return ""
  const face = config.face || "微软雅黑"
  const headerText = config.headerText || `香港天天彩『${config.title}』`
  const body = rows
    .map((row) => {
      const prediction = escapeHtml(row.prediction)
      return `<tr>
                    <td height="39">
                        <p align="center">
                            <b>
                                <font face="${escapeAttr(face)}" size="4">${escapeHtml(row.term)}期${config.face === "隶书" ? "：" : " "}</font>
                                <font color="${escapeAttr(config.titleColor || "#008000")}" size="3" face="${escapeAttr(face)}">${escapeHtml(config.title)}</font>
                                <font color="${escapeAttr(config.predictionColor || "#0000FF")}" size="3" face="${escapeAttr(face)}">『${prediction}』</font>
                                <font face="${escapeAttr(face)}" size="4">开${renderResult(row.result, row.isOpened, row.isCorrect)}</font>
                            </b>
                        </p>
                    </td>
                </tr>`
    })
    .join("")

  return `<div class="box pad" id="${escapeAttr(config.anchor)}" style="margin:0px;">
            <table ${config.anchor === "bs1x" ? `style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" ` : ""}border="1" width="100%" bgcolor="#ffffff">
                <tbody>
                <tr>
                    <td style="border:10px double #CC0000; height: 50px;" bgcolor="#CC0000">
                        <p align="center">
                            <b>
                                <font face="楷体" style="font-size: 18pt">
                                    <font color="${config.headerText ? "#FFFF00" : "#FFFF00"}">${escapeHtml(headerText)}</font></font>
                            </b>
                        </p>
                    </td>
                </tr>
                </tbody>
            </table>
            <table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%">
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
                <div class="cur" style="border-color:${escapeAttr(activeOption.color)}">
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
    `<img src="/vendor/twcaibawang.com/static/picture/2a9a358904487e3d801e2df8d85e4344.png" width="100%" alt="香港天天彩">`,
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
    <div class="txtMarquee-left"><marquee scrollamount="3" scrolldelay="50" direction="left" onmouseover="this.stop();" onmouseout="this.start();" style="color:red">${escapeHtml(siteData.site.announcement || "香港天天彩资料已接入当前项目后台 API，首页预测模块按源站结构动态渲染。")}</marquee></div>
</div>`,
    `<div class="box">
            <p style="text-wrap-mode: wrap;"><img src="/vendor/twcaibawang.com/static/picture/815ea6d729ec11d96502aaa43765e3d1.gif" alt="log.gif"><img src="/vendor/twcaibawang.com/static/picture/9dc46b1cf36b41503755bad0477ab6c5.gif" alt="2.gif"></p><p style="text-wrap-mode: wrap;"><img src="/vendor/twcaibawang.com/static/picture/bdd6df8c288d350b2f8190262f8cdc4d.gif" alt="5.gif"></p>
        </div>`,
    renderWuxiaoWuma(findVendor("wuxiao_wuma")),
    renderPt1Xiao(resolveModule(modules, "pt1xiao")),
    renderPt1Wei(resolveModule(modules, "pt1wei")),
    renderShuangbo(resolveModule(modules, "shuangbo")),
    renderImageModule(resolveModule(modules, "sxztu"), "sxztu", "四不像肖中特图"),
    renderImageModule(resolveModule(modules, "brainteaser"), "brainteaser", "脑筋急转弯"),
    renderImageModule(resolveModule(modules, "pmtj_image"), "pmtj-image", "跑马图解"),
    renderImageModule(resolveModule(modules, "tw_pmt_image"), "tw-pmt-image", "台湾跑马图"),
    renderTiandi2Xiao(findVendor("tiandi_2xiao")),
    `<div class="box amplIMG">
            <p><img src="/vendor/twcaibawang.com/static/picture/8d8e0c09a5cb36948161cb7c9ff72553.jpg" alt="8d8e0c09a5cb36948161cb7c9ff72553.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/2765121603ed96e8e483970e2ddb8b5a.gif" alt="2765121603ed96e8e483970e2ddb8b5a.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/8d45ce25e17db9940efc4ec9b26911c8.gif" alt="8d45ce25e17db9940efc4ec9b26911c8.gif"></p>
        </div>`,
    renderDaxiao2Tou(findVendor("daxiao_2tou")),
    renderPublicYixiaoYima(findVendor("public_yixiao_yima")),
    `<div class="box amplIMG">
            <p><img src="/vendor/twcaibawang.com/static/picture/201c1ae2c49d4e2bf0debe240baad433.jpg" alt="gytm80.gif"><img src="/vendor/twcaibawang.com/static/picture/90bdc09a6a9709d8c50c9d56e0655ac4.gif" alt="80.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/17f9be2108da031fe3ad2d75ae33ede7.jpg" alt="c999e7ef3b66eaebed23f7a6c6b2c858_17f9be2108da031fe3ad2d75ae33ede7.jpg"></p>
        </div>`,
    renderShujinguang(findVendor("shujinguang")),
    renderJuesha1Xiao(resolveModule(modules, "juesha1xiao")),
    `<div class="box amplIMG">
            <p><img src="/vendor/twcaibawang.com/static/picture/8d8e0c09a5cb36948161cb7c9ff72553.jpg" alt="8d8e0c09a5cb36948161cb7c9ff72553.gif"><img src="/vendor/twcaibawang.com/static/picture/2765121603ed96e8e483970e2ddb8b5a.jpg" alt="2765121603ed96e8e483970e2ddb8b5a.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/42ce9a26360f319a1e46203fda6a5e68.jpg" alt="46c5b99157e4b07f4ad1a7b070bd13a5.gif"><img src="/vendor/twcaibawang.com/static/picture/201c1ae2c49d4e2bf0debe240baad433.jpg" alt="gytm80.gif"></p><p><img src="/vendor/twcaibawang.com/static/picture/be31c7596d2c1fab4ffa07fe9cc603c0.gif" alt="301980.gif"></p>
        </div>`,
    renderShuangbo12Ma(findVendor("shuangbo_12ma")),
    ...GENERIC_MODULES.map((config) => renderGenericModule(config, resolveModule(modules, config.mechanismKey))),
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
  const html = useMemo(
    () => buildPageHtml(siteData, homepageModules, defaultLotteryTypeId),
    [defaultLotteryTypeId, homepageModules, siteData]
  )

  useEffect(() => {
    document.body.style.background = "#f7f0dc"

    const nav = document.getElementById("nav2")
    const tabs = Array.from(document.querySelectorAll<HTMLLIElement>(".KJ-TabBox ul li"))
    const panels = Array.from(document.querySelectorAll<HTMLElement>(".KJ-TabBox > div"))
    const iframe = document.getElementById("twcaibawang-kj-iframe") as HTMLIFrameElement | null
    const navTop = nav?.offsetTop ?? 0

    const onScroll = () => {
      if (!nav) return
      const scrollTop = document.documentElement.scrollTop || document.body.scrollTop
      nav.setAttribute("data-fixed", scrollTop >= navTop ? "fixed" : "")
    }

    const onTabClick = (event: Event) => {
      const target = event.currentTarget as HTMLLIElement
      if (!iframe) return
      const url = target.dataset.url || iframe.src
      const color = target.dataset.color || "#de2910"

      tabs.forEach((item) => item.classList.remove("cur"))
      panels.forEach((panel) => {
        panel.classList.remove("cur")
        panel.style.borderColor = ""
      })

      target.classList.add("cur")
      if (panels[1]) {
        panels[1].classList.add("cur")
        panels[1].style.borderColor = color
      }
      iframe.src = url
      iframe.height = "180"
    }

    tabs.forEach((tab) => tab.addEventListener("click", onTabClick))
    window.addEventListener("scroll", onScroll, { passive: true })
    onScroll()

    return () => {
      tabs.forEach((tab) => tab.removeEventListener("click", onTabClick))
      window.removeEventListener("scroll", onScroll)
      document.body.style.background = ""
    }
  }, [html])

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
        }
        .KJ-TabBox ul,
        .KJ-TabBox li {
          margin: 0;
          list-style: none;
          padding: 0;
          border: 0;
          font-size: 14px;
        }
        .KJ-TabBox li {
          display: inline-block;
          border: 1px solid darkgrey;
          padding: 5px;
          border-bottom: 0;
          color: darkgrey;
          cursor: pointer;
          text-align: center;
          border-left: none;
          flex: 1;
        }
        .KJ-TabBox li:first-child {
          border-left: solid 1px;
        }
        .KJ-TabBox li.cur {
          color: #de2910;
          font-weight: bold;
          background-color: white;
          cursor: default;
          border-color: #de2910;
          border-left: solid 1px;
          border-right: solid 1px;
        }
        .KJ-TabBox > div {
          border-top: 1px solid gainsboro;
          margin-top: -1px;
          display: none;
        }
        .KJ-TabBox > div.cur {
          display: block !important;
          border-color: #de2910;
        }
        .KJ-TabBox .KJ-IFRAME {
          background: white;
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
        }
        @media screen and (max-width: 420px) {
          .box.pad td * {
            font-size: 15px;
          }
          .nav2 ul li a {
            font-weight: bold;
          }
        }
      `}</style>
      <div dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  )
}
