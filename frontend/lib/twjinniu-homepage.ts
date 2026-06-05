import "server-only"

import { backendFetchJson } from "@/lib/backend-api"
import { getSiteConfig } from "@/lib/sites"

const SITE = getSiteConfig("twjinniu")
const DEFAULT_WEB_ID = SITE?.defaultWebId ?? 7
const HISTORY_LIMIT = 8
const SANXIAO_SIWEI_SOURCE_LIMIT = 32

export type TwjinniuLotteryType = 1 | 2 | 3

type LegacyModeRow = {
  year?: string
  term?: string
  title?: string | null
  content?: string | null
  xiao?: string | null
  xiao_1?: string | null
  xiao_2?: string | null
  tou?: string | null
  wei?: string | null
  code?: string | null
  jiexi?: string | null
  image_url?: string | null
  res_code?: string | null
  res_sx?: string | null
  res_color?: string | null
  draw_is_opened?: boolean
}

type LegacyModeRowsResponse = {
  rows?: LegacyModeRow[]
}

type HomepageModuleKey =
  | "formula_ptx"
  | "yixiao_yima"
  | "sanxiao_siwei"
  | "qianhou_24ma"
  | "sanxiao_15ma"
  | "shisi_mazhong"
  | "sixiao_bama"
  | "danshuang_sixiao_bama"
  | "pingte_erma"
  | "sixiao_sima"
  | "pingte_xiao"
  | "pingte_wei"
  | "yixiao_sanma"
  | "jixian_texiao"
  | "fivea_dagongkai"
  | "qianhou_texiao"
  | "wenzhuan_baxiao"
  | "shiwu_mazhong"
  | "daxiao_yitou"
  | "danshuang_liangxiao"
  | "jiaye_liangxiao"
  | "yijuhua_zhongtema"
  | "heshu_daxiao"
  | "baxiao_shiliuma"
  | "pmtj_image"
  | "sxztu_image"

type HomepageModuleStatus = "ok" | "missing_data" | "missing_mapping"

export type TwjinniuHomepageModulePayload = {
  key: HomepageModuleKey
  title: string
  status: HomepageModuleStatus
  html: string
  mappedModeIds: number[]
  notes: string[]
}

export type TwjinniuHomepageModulesResponse = {
  ok: true
  site: {
    site_key: string
    web_id: number
    lottery_type: TwjinniuLotteryType
  }
  modules: Record<HomepageModuleKey, TwjinniuHomepageModulePayload>
  missingModules: Array<{
    key: HomepageModuleKey
    title: string
    status: HomepageModuleStatus
    mappedModeIds: number[]
  }>
}

type ParsedResult = {
  code: string
  zodiac: string
  isOpened: boolean
}

type LabelCodeEntry = {
  label: string
  codes: string[]
}

type YixiaoYimaRow = {
  year: string
  term: string
  xiao9: string[]
  xiao7: string[]
  xiao5: string[]
  xiao3: string[]
  bestXiao: string
  code14: string[]
  result: ParsedResult
  isCorrect: boolean | null
}

type SanxiaoSiweiRow = {
  row: LegacyModeRow
  xiaoEntries: LabelCodeEntry[]
  weiEntries: LabelCodeEntry[]
}

function escapeHtml(value: unknown) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;")
}

function normalizeCode(value: unknown) {
  const text = String(value ?? "").trim()
  if (!text) return ""
  return /^\d{1,2}$/.test(text) ? text.padStart(2, "0") : text
}

function cleanText(value: unknown) {
  return String(value ?? "").trim()
}

function normalizeImageUrl(value: unknown) {
  const raw = cleanText(value)
  if (!raw) return ""
  if (raw.startsWith("/uploads/") || raw.startsWith("http://") || raw.startsWith("https://")) {
    return raw
  }
  const normalized = raw.replaceAll("\\", "/")
  const marker = "/data/Images/"
  const index = normalized.indexOf(marker)
  if (index >= 0) {
    return `/uploads/${normalized.slice(index + marker.length)}`
  }
  return raw
}

function parseJsonStringArray(value: unknown) {
  const text = cleanText(value)
  if (!text) return [] as string[]
  try {
    const parsed = JSON.parse(text)
    return Array.isArray(parsed) ? parsed.map((item) => cleanText(item)).filter(Boolean) : []
  } catch {
    return []
  }
}

function splitCsv(value: unknown) {
  return cleanText(value)
    .split(/[,\s]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function splitPredictionTokens(value: unknown) {
  const text = cleanText(value)
  if (!text) return [] as string[]
  const jsonItems = parseJsonStringArray(text)
  if (jsonItems.length) return jsonItems

  const tokens = text
    .replace(/^[\["']+|[\]"']+$/g, "")
    .split(/[,\s.、，|+/-]+/)
    .map((item) => item.trim())
    .filter(Boolean)
  if (tokens.length > 1) return tokens

  const chars = Array.from(text).filter((char) => /[\u4e00-\u9fff]/.test(char))
  return chars.length > 1 ? chars : text ? [text] : []
}

function parseLabelCodeEntries(value: unknown) {
  const items = parseJsonStringArray(value)
  if (!items.length && cleanText(value).includes("|")) {
    items.push(cleanText(value))
  }

  return items
    .map((item) => {
      const [labelPart = "", codesPart = ""] = String(item).split("|", 2)
      const label = labelPart.trim()
      const codes = codesPart
        .split(/[,.]/)
        .map((code) => normalizeCode(code))
        .filter(Boolean)
      return label ? { label, codes } : null
    })
    .filter((item): item is LabelCodeEntry => Boolean(item))
}

function parsePlainLabelCodes(value: unknown) {
  return cleanText(value)
    .split(/[+,，、\s]+/)
    .map((item) => cleanText(item))
    .filter(Boolean)
}

function resolveResult(row: LegacyModeRow | null | undefined): ParsedResult {
  const codes = splitCsv(row?.res_code)
  const zodiacs = splitCsv(row?.res_sx)
  return {
    code: normalizeCode(codes.at(-1) || ""),
    zodiac: cleanText(zodiacs.at(-1) || ""),
    isOpened: Boolean(row?.draw_is_opened) && Boolean(codes.at(-1)),
  }
}

function sortRowsByTermDesc<T extends { year?: string; term?: string }>(rows: T[]) {
  return [...rows].sort((left, right) => {
    const leftYear = Number.parseInt(String(left.year || ""), 10)
    const rightYear = Number.parseInt(String(right.year || ""), 10)
    if (Number.isFinite(leftYear) && Number.isFinite(rightYear) && leftYear !== rightYear) {
      return rightYear - leftYear
    }

    const leftTerm = Number.parseInt(String(left.term || ""), 10)
    const rightTerm = Number.parseInt(String(right.term || ""), 10)
    if (Number.isFinite(leftTerm) && Number.isFinite(rightTerm)) {
      return rightTerm - leftTerm
    }

    return String(right.term || "").localeCompare(String(left.term || ""), "en")
  })
}

function renderResultJudge(result: ParsedResult, isCorrect: boolean | null, pending = "??????") {
  if (!result.isOpened) return pending
  const openText = `${escapeHtml(result.code)}${escapeHtml(result.zodiac)}`
  if (isCorrect === true) {
    return `<font color="#FF0000">${openText}对</font>`
  }
  return `${openText}<font color="#000">错</font>`
}

function renderResultPlain(result: ParsedResult, pending = "??????") {
  if (!result.isOpened) return pending
  return `${escapeHtml(result.code)}${escapeHtml(result.zodiac)}`
}

async function loadLegacyModeRows(modesId: number, lotteryType: TwjinniuLotteryType, limit = HISTORY_LIMIT) {
  const payload = await backendFetchJson<LegacyModeRowsResponse>("/legacy/module-rows", {
    query: {
      modes_id: modesId,
      web: DEFAULT_WEB_ID,
      type: lotteryType,
      limit,
    },
  })

  return sortRowsByTermDesc((payload.rows || []).map((row) => ({ ...row })))
}

function renderFormulaMissing() {
  return `
    <table border="1" width="100%" bgcolor="#ffffff">
      <tbody>
        <tr>
          <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">台湾通天网【公式平特肖】</font></b></p></td>
        </tr>
      </tbody>
    </table>
    <div class="dz_content08 dz_content08abd">
      <p style="text-align: center;"><span style="font-size: 13pt;"><strong>当前彩种缺少数据</strong></span></p>
    </div>
  `
}

function renderFormulaPtx(rows: LegacyModeRow[]) {
  if (!rows.length) {
    return renderFormulaMissing()
  }

  const body = rows
    .map((row) => {
      const prediction = splitPredictionTokens(row.content).at(0) || cleanText(row.content)
      const codes = splitCsv(row.res_code).map((value) => normalizeCode(value))
      const zodiacs = splitCsv(row.res_sx).map((value) => cleanText(value))
      const isOpened = Boolean(row.draw_is_opened) && codes.length >= 7
      const specialCode = codes.at(-1) || ""
      const specialZodiac = zodiacs.at(-1) || ""
      const isHit = Boolean(isOpened && prediction && prediction === specialZodiac)

      if (!isOpened) {
        return `<p style="text-align: center;"><span style="font-size: 13pt;"><strong>${escapeHtml(row.term)}期&nbsp;&nbsp;${escapeHtml(prediction || "当前彩种缺少数据")}</strong></span></p>`
      }

      const regularText = codes
        .slice(0, 6)
        .map((code, index) => {
          const zodiac = zodiacs[index] || ""
          const codeHtml = escapeHtml(code)
          return zodiac && prediction && zodiac === prediction
            ? `<span style="background-color: #FFFF00">${codeHtml}</span>`
            : codeHtml
        })
        .join("-")

      const specialText =
        specialZodiac && prediction && specialZodiac === prediction
          ? `<span style="background-color: #FFFF00">${escapeHtml(specialCode)}</span>`
          : escapeHtml(specialCode)

      return `<p style="text-align: center;"><span style="font-size: 13pt;"><strong>${escapeHtml(row.term)}期 ${regularText} T${specialText} ${escapeHtml(prediction)}${isHit ? "√" : "×"}</strong></span></p>`
    })
    .join("")

  return `
    <table border="1" width="100%" bgcolor="#ffffff">
      <tbody>
        <tr>
          <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">台湾通天网【公式平特肖】</font></b></p></td>
        </tr>
      </tbody>
    </table>
    <style>
      .dz_content08abd tr td {
        height : 35px !important;
      }
    </style>
    <div class="dz_content08 dz_content08abd">
      ${body}
    </div>
  `
}

function renderYixiaoYimaMissing() {
  return `
    <table style="border-collapse: collapse; width: 99.9412%;" border="1">
      <tbody>
        <tr style="height: 26.125px;">
          <td style="width: 99.9915%; background-color: #0c35f5; height: 26.125px; text-align: center;" colspan="2">
            <span style="font-size: 14pt; font-family: 'Helvetica Neue', Helvetica, Arial, 'Microsoft Yahei', 'Hiragino Sans GB', 'Heiti SC', 'WenQuanYi Micro Hei', sans-serif;"><strong><span style="color: #ffffff;">台湾通天网一肖一码大公开</span></strong></span>
          </td>
        </tr>
        <tr>
          <td style="width: 99.9915%; text-align: center; padding: 18px 0;" colspan="2">
            <strong><span style="font-size: 13pt; color: #000000;">当前彩种缺少数据</span></strong>
          </td>
        </tr>
      </tbody>
    </table>
  `
}

function renderSixiaoBama(rows: LegacyModeRow[]) {
  // Prefer rows with rich content (4+ label-code entries)
  const renderableRows = rows.filter((row) => parseLabelCodeEntries(row.content).length >= 4)
  // If no rich-content rows in first batch, search all rows
  const useRows = renderableRows.length >= 1 ? renderableRows : rows.filter((row) => parseLabelCodeEntries(row.content).length >= 4)

  if (!useRows.length) {
    return renderMissingTable('<font color="#FFFF00">台湾通天网</font><font color="#FFFFFF">『四肖八码』</font>')
  }

  const body = renderableRows.slice(0, 10)
    .map((row) => {
      const entries = parseLabelCodeEntries(row.content).slice(0, 4)
      const result = resolveResult(row)
      const isCorrect =
        result.isOpened &&
        entries.some((entry) => entry.label === result.zodiac || entry.codes.includes(result.code))
      const predictionText = entries
        .map((entry) => {
          const hitLabel = isCorrect && entry.label === result.zodiac
          const label = hitLabel ? `<span style="background-color: #FFFF00">${escapeHtml(entry.label)}</span>` : escapeHtml(entry.label)
          const codes = entry.codes.map((code) => (isCorrect && code === result.code ? `<span style="background-color: #FFFF00">${escapeHtml(code)}</span>` : escapeHtml(code))).join(".")
          return `【${label}${codes}】`
        })
        .join("")

      return `
        <tr>
          <td style="color:#000;font-family:微软雅黑;font-weight:700;border:1px solid #000" align="center" width="100%" height="50">
            <font style="font-weight:700" size="3" face="微软雅黑"><span style="color: #00F;">${escapeHtml(row.term)}期：</span><span style="color: #800000;">赌神</span><span style="color: #000;">四肖八码</span></font>
          </td>
        </tr>
        <tr>
          <td style="color:#000;font-family:微软雅黑;font-weight:700;border:1px solid #000" align="center" width="100%" height="50">
            <p style="line-height:200%"><span style="font-size:13pt;font-family:微软雅黑;color: #ff0000">${predictionText}<br>开:<span style="color: #F00; background-color: #FFFF00;">${renderResultJudge(result, isCorrect, "?????")}</span></span></p>
          </td>
        </tr>
      `
    })
    .join("")

  return buildSixiaoBamaTable(body)
}

function buildSixiaoBamaTable(body: string) {
  return `
    <table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%">
      <tbody>
        <tr>
          <td style="text-align:center" height="60">
            <table border="1" width="100%" bgcolor="#ffffff">
              <tbody>
                <tr>
                  <td style="border:10px double #00f" bgcolor="#0000FF" height="50"><p align="center"><b><font face="楷体" style="font-size: 20pt"><font color="#FFFF00">台湾通天网</font><font color="#FFFFFF">『四肖八码』</font></font></b></p></td>
                </tr>
              </tbody>
            </table>
          </td>
        </tr>
        ${body}
      </tbody>
    </table>
  `
}

function buildSanxiaoSiweiRows(
  xiaoRows: LegacyModeRow[],
  weiRows: LegacyModeRow[],
  limit = HISTORY_LIMIT
) {
  const weiByIssue = new Map<string, LegacyModeRow[]>()
  for (const row of sortRowsByTermDesc(weiRows)) {
    const issue = `${cleanText(row.year)}-${cleanText(row.term)}`
    const bucket = weiByIssue.get(issue)
    if (bucket) {
      bucket.push(row)
    } else {
      weiByIssue.set(issue, [row])
    }
  }

  const mergedRows: SanxiaoSiweiRow[] = []
  for (const xiaoRow of sortRowsByTermDesc(xiaoRows)) {
    const issue = `${cleanText(xiaoRow.year)}-${cleanText(xiaoRow.term)}`
    const weiCandidates = weiByIssue.get(issue)
    if (!weiCandidates?.length) {
      continue
    }

    const xiaoEntries = parseLabelCodeEntries(xiaoRow.content).slice(0, 3)
    if (!xiaoEntries.length) {
      continue
    }

    const selectedWeiRow = weiCandidates.find(
      (candidate) => parseLabelCodeEntries(candidate.content).length >= 4
    )
    if (!selectedWeiRow) {
      continue
    }

    const weiEntries = parseLabelCodeEntries(selectedWeiRow.content).slice(0, 4)
    if (weiEntries.length < 4) {
      continue
    }

    mergedRows.push({ row: xiaoRow, xiaoEntries, weiEntries })
    if (mergedRows.length >= limit) {
      break
    }
  }

  return mergedRows
}

function renderSanxiaoSiwei(rows: SanxiaoSiweiRow[]) {
  if (!rows.length) {
    return renderMissingTable('<font color="#FFFF00">台湾通天网</font><font color="#FFFFFF">『三肖四尾』</font>')
  }

  const body = rows
    .map(({ row, xiaoEntries, weiEntries }) => {
      const result = resolveResult(row)
      const hitZodiac = result.isOpened ? xiaoEntries.some((entry) => entry.label === result.zodiac) : false
      const hitTail = result.isOpened
        ? weiEntries.some((entry) => result.code.endsWith(entry.label.replace(/尾$/, "")))
        : false
      const isCorrect = result.isOpened ? hitZodiac || hitTail : null
      const xiaoHtml = xiaoEntries
        .map((entry) =>
          hitZodiac && entry.label === result.zodiac
            ? `<span style="background-color: #FFFF00">${escapeHtml(entry.label)}</span>`
            : escapeHtml(entry.label)
        )
        .join("")
      const weiHtml = weiEntries
        .map((entry) => entry.label.replace(/尾$/, ""))
        .map((digit) =>
          hitTail && result.code.endsWith(digit)
            ? `<span style="background-color: #FFFF00">${escapeHtml(digit)}</span>`
            : escapeHtml(digit)
        )
        .join("")

      return `
        <table style="border-collapse:collapse" border="1" width="100%" bgcolor="#ffffff" height="41">
          <tbody>
            <tr>
              <td width="100%" height="41"><p align="center"><font face="楷体"><b><font size="4">${escapeHtml(
                row.term
              )}期</font><font color="#FF0000" size="5">（${xiaoHtml}+${weiHtml}尾）</font><font size="4">开${renderResultJudge(
                result,
                isCorrect,
                "?????"
              )}</font></b></font></p></td>
            </tr>
          </tbody>
        </table>
      `
    })
    .join("")

  return `
    <table width="100%" cellspacing="0" cellpadding="0">
      <tbody>
        <tr>
          <td style="text-align:center" height="60">
            <table border="1" width="100%" bgcolor="#ffffff">
              <tbody>
                <tr>
                  <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 18pt">台湾通天网</font><font color="#FFFFFF" face="楷体" style="font-size: 18pt">『三肖四尾』</font></b></p></td>
                </tr>
              </tbody>
            </table>
            ${body}
          </td>
        </tr>
      </tbody>
    </table>
  `
}

function renderDanshuangSixiaoBama(rows: LegacyModeRow[]) {
  const renderable = rows.filter((row) => {
    const gA = splitCsv(row.xiao_1)
    const gB = splitCsv(row.xiao_2)
    return gA.length >= 4 && gB.length >= 4
  })
  if (!renderable.length) {
    return renderMissingTable('<font color="#FFFF00">台湾通天网</font><font color="#FFFFFF">『单双四肖八码』</font>')
  }

  const body = renderable.slice(0, HISTORY_LIMIT).map((row) => {
    const groupA = splitCsv(row.xiao_1)
    const groupB = splitCsv(row.xiao_2)
    const result = resolveResult(row)
    const hitA = result.isOpened ? groupA.includes(result.zodiac) : false
    const hitB = result.isOpened ? groupB.includes(result.zodiac) : false
    const hit = hitA || hitB
    // Determine parity from result special code (odd=单, even=双)
    const codeNum = Number.parseInt(result.code, 10)
    const parityLabel = Number.isFinite(codeNum) ? (codeNum % 2 === 1 ? '单数' : '双数') : '单数'
    // Use the group that matches as primary, or groupA by default
    const primaryGroup = hitB && !hitA ? groupB : groupA
    const renderZodiacs = (values: string[]) => values
      .map((v) => hit && v === result.zodiac
        ? `<span style="background-color: #FFFF00">${escapeHtml(v)}</span>`
        : escapeHtml(v)).join("")
    const resultDisplay = result.isOpened
      ? `${escapeHtml(result.code)}${escapeHtml(result.zodiac)}<font color="${hit ? '#FF0000' : '#000000'}">${hit ? '对' : '错'}</font>`
      : '?????'
    return `<tr><td style="padding:8px 10px;border:1px solid #ccc;font-size:13pt;font-weight:700;line-height:2.2;">
      <p style="margin:2px 0;"><span style="color:#0000FF;">${escapeHtml(row.term)}期：</span>单双四肖八码 开:${resultDisplay}</p>
      <p style="margin:2px 0;">【<span style="color:#FF0000;">${escapeHtml(parityLabel)}</span>】【${renderZodiacs(primaryGroup)}】</p>
    </td></tr>`
  }).join("")

  return `<table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%">
    <tbody><tr><td style="text-align:center" height="60">
      <table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
        <td style="border:10px double #00f" bgcolor="#0000FF" height="50"><p align="center"><b><font face="楷体" style="font-size: 20pt"><font color="#FFFF00">台湾通天网</font><font color="#FFFFFF">『单双四肖八码』</font></font></b></p></td>
      </tr></tbody></table>
    </td></tr>${body}</tbody></table>`
}

function renderMissingTable(titleHtml: string) {
  return `
    <table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%">
      <tbody>
        <tr>
          <td style="text-align:center" height="60">
            <table border="1" width="100%" bgcolor="#ffffff">
              <tbody>
                <tr>
                  <td style="border:10px double #00f" bgcolor="#0000FF" height="50"><p align="center"><b><font face="楷体" style="font-size: 20pt">${titleHtml}</font></b></p></td>
                </tr>
              </tbody>
            </table>
          </td>
        </tr>
        <tr>
          <td style="color:#000;font-family:微软雅黑;font-weight:700;border:1px solid #000" align="center" width="100%" height="50">
            <font style="font-weight:700" size="3" face="微软雅黑">当前彩种缺少数据</font>
          </td>
        </tr>
      </tbody>
    </table>
  `
}

function renderPingteXiao(rows: LegacyModeRow[]) {
  if (!rows.length) {
    return renderMissingTable('<font color="#FFFF00">www.twtongtian.com</font><font color="#FFFFFF">『平特一肖』</font>')
  }

  const body = rows
    .map((row) => {
      const entry = parseLabelCodeEntries(row.content)[0]
      const result = resolveResult(row)
      const label = entry?.label || splitPredictionTokens(row.content).at(0) || ""
      const isCorrect =
        result.isOpened && Boolean(label) && (label === result.zodiac || (entry?.codes || []).includes(result.code))
      const displayLabel = isCorrect ? `<span style="background-color: #FFFF00">${escapeHtml(label.repeat(3))}</span>` : escapeHtml(label.repeat(3))
      return `
        <tr>
          <td style="color:#000;font-family:微软雅黑;font-weight:700;border:2px solid #000" align="center" width="100%" height="50">
            <font size="3"><span style="color: #00F;">${escapeHtml(row.term)}期</span>:<span style="color: #800000;">平特一肖</span>〖<span style="color: #F00;">${displayLabel}</span>〗开：<span style="background-color: #FFFF00; color: #F00;">${renderResultJudge(result, isCorrect)}</span></font>
          </td>
        </tr>
      `
    })
    .join("")

  return `
    <table width="100%" cellspacing="0" cellpadding="0" height="150">
      <tbody>
        <tr>
          <td style="text-align:center" height="60">
            <table border="1" width="100%" bgcolor="#ffffff">
              <tbody>
                <tr>
                  <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">www.twtongtian.com</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">『平特一肖』</font></b></p></td>
                </tr>
              </tbody>
            </table>
          </td>
        </tr>
        ${body}
      </tbody>
    </table>
  `
}

function renderPingteWei(rows: LegacyModeRow[]) {
  if (!rows.length) {
    return renderMissingTable('<font color="#FFFF00">www.twtongtian.com</font><font color="#FFFFFF">『平特一尾』</font>')
  }

  const body = rows
    .map((row) => {
      const entry = parseLabelCodeEntries(row.content)[0]
      const result = resolveResult(row)
      const match = (entry?.label || "").match(/(\d)尾/)
      const digit = match?.[1] || cleanText(entry?.label)
      const triple = digit ? digit.repeat(3) : cleanText(entry?.label)
      const isCorrect = result.isOpened && Boolean(digit) && result.code.endsWith(digit)
      const displayLabel = isCorrect ? `<span style="background-color: #FFFF00">${escapeHtml(triple)}</span>` : escapeHtml(triple)
      return `
        <tr>
          <td style="color:#000;font-family:微软雅黑;font-weight:700;border:2px solid #000" align="center" width="100%" height="50">
            <font size="3"><span style="color: #00F;">${escapeHtml(row.term)}期</span>:<span style="color: #800000;">平特一尾</span>〖<span style="color: #F00;">${displayLabel}</span>〗开：<span style="background-color: #FFFF00; color: #F00;">${renderResultJudge(result, isCorrect)}</span></font>
          </td>
        </tr>
      `
    })
    .join("")

  return `
    <table width="100%" cellspacing="0" cellpadding="0" height="150">
      <tbody>
        <tr>
          <td style="text-align:center" height="60">
            <table border="1" width="100%" bgcolor="#ffffff">
              <tbody>
                <tr>
                  <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">www.twtongtian.com</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">『平特一尾』</font></b></p></td>
                </tr>
              </tbody>
            </table>
          </td>
        </tr>
        ${body}
      </tbody>
    </table>
  `
}

function renderPingteErma(rows: LegacyModeRow[]) {
  if (!rows.length) {
    return renderMissingTable('<font color="#FFFF00">钱包空了</font><font color="#FFFFFF">【平特二码】</font>')
  }

  const body = rows
    .map((row) => {
      const entries = parseLabelCodeEntries(row.content)
      if (!entries.length) return ""
      const result = resolveResult(row)
      const entry = entries[0]
      const codes = entry.codes.slice(0, 2)
      const isCorrect =
        result.isOpened &&
        (entry.label === result.zodiac || codes.includes(result.code))
      const labelHtml =
        isCorrect && entry.label === result.zodiac
          ? `<span style="background-color: #FFFF00">${escapeHtml(entry.label)}</span>`
          : escapeHtml(entry.label)
      const codeHtml = codes
        .map((code) =>
          isCorrect && code === result.code
            ? `<span style="background-color: #FFFF00">${escapeHtml(code)}</span>`
            : escapeHtml(code)
        )
        .join(".")

      return `
        <tr>
          <td height="46" bgcolor="#FFFFFF">
            <p align="center"><b><font size="3" color="#000000">${escapeHtml(row.term)}期：独平</font><font color="#FF3300" size="3">【${labelHtml}${codeHtml}】</font><font color="#000000" size="3">开${renderResultJudge(result, isCorrect, "?????")}</font><font color="#000000"></font></b></p></td>
        </tr>
      `
    })
    .filter(Boolean)
    .join("")

  if (!body) {
    return renderMissingTable('<font color="#FFFF00">钱包空了</font><font color="#FFFFFF">【平特二码】</font>')
  }

  return `
    <table border="1" width="100%" bgcolor="#ffffff">
      <tbody>
        <tr>
          <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">钱包空了</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">【平特二码】</font></b></p></td>
        </tr>
      </tbody>
    </table>
    <table border="1" width="100%" id="table400923411">
      <tbody>${body}</tbody>
    </table>
  `
}

function renderDanshuangLiangxiao(rows: LegacyModeRow[]) {
  if (!rows.length) {
    return renderMissingTable('<font color="#FFFF00">特码来迟</font><font color="#FFFFFF">『单双两肖』</font>')
  }

  const body = rows
    .map((row) => {
      const label = cleanText(row.content).startsWith("双") ? "双数" : "单数"
      const xiaos = splitCsv(row.xiao).slice(0, 2)
      if (!xiaos.length) return ""
      const result = resolveResult(row)
      const parityHit = result.isOpened
        ? Number.parseInt(result.code, 10) % 2 === (label === "双数" ? 0 : 1)
        : false
      const zodiacHit = result.isOpened ? xiaos.includes(result.zodiac) : false
      const isCorrect = result.isOpened ? parityHit || zodiacHit : null
      const labelHtml =
        parityHit ? `<span style="background-color: #FFFF00">${label}</span>` : label
      const xiaoHtml = xiaos
        .map((xiao) =>
          zodiacHit && xiao === result.zodiac
            ? `<span style="background-color: #FFFF00">${escapeHtml(xiao)}</span>`
            : escapeHtml(xiao)
        )
        .join("")

      return `
        <tr>
          <td width="100%" height="41"><p align="center"><font face="楷体"><b><font size="4"><font color="#0000FF">${escapeHtml(
            row.term
          )}期：</font>【${labelHtml}+${xiaoHtml}】开<font color="#FF0000">(${renderResultJudge(
            result,
            isCorrect,
            "??????"
          )})</font></font></b></font></p></td></tr>
      `
    })
    .filter(Boolean)
    .join("")

  return `
    <table width="100%" id="table1" cellspacing="0" cellpadding="0">
      <tbody>
        <tr><td style="text-align:center" height="60">
          <table border="1" width="100%" bgcolor="#ffffff"><tbody>
            <tr><td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 18pt">特码来迟</font><font color="#FFFFFF" face="楷体" style="font-size: 18pt">『单双两肖』</font></b></p></td></tr>
          </tbody></table>
        </td></tr>
        ${body}
      </tbody>
    </table>
  `
}

function renderJiayeLiangxiao(rows: LegacyModeRow[]) {
  if (!rows.length) {
    return renderMissingTable('<font color="#FFFF00">特码来迟</font><font color="#FFFFFF">『家野两肖』</font>')
  }

  const body = rows
    .map((row) => {
      const entry = parseLabelCodeEntries(row.content)[0]
      const groupLabel = cleanText(entry?.label || cleanText(row.content).split("|")[0] || "")
      const xiaos = splitCsv(row.xiao).slice(0, 2)
      if (!groupLabel && !xiaos.length) return ""
      const result = resolveResult(row)
      const zodiacHit = result.isOpened ? xiaos.includes(result.zodiac) : false
      const xiaoHtml = xiaos
        .map((xiao) =>
          zodiacHit && xiao === result.zodiac
            ? `<span style="background-color: #FFFF00">${escapeHtml(xiao)}</span>`
            : escapeHtml(xiao)
        )
        .join("")

      return `
        <tr>
          <td width="100%" height="41"><p align="center"><font face="楷体"><b><font size="4">${escapeHtml(
            row.term
          )}期：<font color="#0000FF">（${escapeHtml(groupLabel)}+${xiaoHtml}）</font>开<font color="#FF0000">(${renderResultJudge(
            result,
            result.isOpened ? zodiacHit : null,
            "??????"
          )})</font></font></b></font></p></td></tr>
      `
    })
    .filter(Boolean)
    .join("")

  return `
    <table width="100%" id="table1" cellspacing="0" cellpadding="0">
      <tbody>
        <tr><td style="text-align:center" height="60">
          <table border="1" width="100%" bgcolor="#ffffff"><tbody>
            <tr><td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 18pt">特码来迟</font><font color="#FFFFFF" face="楷体" style="font-size: 18pt">『家野两肖』</font></b></p></td></tr>
          </tbody></table>
        </td></tr>
        ${body}
      </tbody>
    </table>
  `
}

function renderHeShuDaxiao(rows: LegacyModeRow[]) {
  // Static intro
  const intro = `
    <table style="border-collapse:collapse" border="1" width="100%" bgcolor="#ffffff" height="41">
      <tbody><tr>
        <td width="100%" height="41"><p align="center"><font face="楷体"><b><font color="#008000" size="4"><span style="background-color: #FFFF00">合小：01-06  合大：07-13</span></font></b></font></p></td>
      </tr></tbody>
    </table>`

  if (!rows.length) {
    return `<div class="a1"><table width="100%" cellspacing="0" cellpadding="0"><tbody><tr><td style="text-align:center" height="60">
      <table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
        <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 18pt">彩彩作妖</font><font color="#FFFFFF" face="楷体" style="font-size: 18pt">『合数大小』</font></b></p></td>
      </tr></tbody></table>${intro}
      <table style="border-collapse:collapse" border="1" width="100%" bgcolor="#ffffff" height="41"><tbody><tr>
        <td width="100%" height="41"><p align="center"><font face="楷体"><b><font size="4">当前彩种缺少数据</font></b></font></p></td>
      </tr></tbody></table></td></tr></tbody></table></div>`
  }

  const body = rows.slice(0, HISTORY_LIMIT).map((row) => {
    const result = resolveResult(row)
    const entry = parseLabelCodeEntries(row.content)[0]
    const label = cleanText(entry?.label || row.content)
    const sum = result.code ? Number.parseInt(result.code.charAt(0), 10) + Number.parseInt(result.code.charAt(1), 10) : NaN
    const hitLabel = Number.isFinite(sum) ? (sum >= 7 ? "合大" : "合小") : ""
    const isCorrect = result.isOpened && Boolean(label) && (label === hitLabel || label.includes(hitLabel.replace("合","")))
    const display = isCorrect ? `<span style="background-color: #FFFF00">${escapeHtml(label)}</span>` : escapeHtml(label)
    const resultDisplay = result.isOpened
      ? `${escapeHtml(result.code)}${escapeHtml(result.zodiac)}<font color="${isCorrect ? '#FF0000' : '#000000'}">${isCorrect ? '对' : '错'}</font>`
      : '?????'
    return `<table style="border-collapse:collapse" border="1" width="100%" bgcolor="#ffffff" height="41"><tbody><tr>
      <td width="100%" height="41"><p align="center"><font face="楷体"><b><font size="4">
      <font color="#008000">${escapeHtml(row.term)}期</font>【<font color="#FF0000">${display}</font>】开(${resultDisplay})</font></b></font></p></td>
    </tr></tbody></table>`
  }).join("")

  return `<div class="a1"><table width="100%" cellspacing="0" cellpadding="0"><tbody><tr><td style="text-align:center" height="60">
    <table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
      <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 18pt">彩彩作妖</font><font color="#FFFFFF" face="楷体" style="font-size: 18pt">『合数大小』</font></b></p></td>
    </tr></tbody></table>${intro}${body}</td></tr></tbody></table></div>`
}

function renderBaXiaoShiLiuMa(rows: LegacyModeRow[]) {
  if (!rows.length) {
    return `
      <table border="1" width="100%" bgcolor="#ffffff">
        <tbody>
          <tr>
            <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">www.twtongtian.com</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">【八肖十六码】</font></b></p></td>
          </tr>
        </tbody>
      </table>
      <table width="100%" cellspacing="0" cellpadding="0" class="font1">
        <tbody>
          <tr>
            <td style="padding: 12px 2px; border: 1px solid #e5e5e5; word-break: break-all;" align="center"><span style="font-size: 14pt;"><strong>当前彩种缺少数据</strong></span></td>
          </tr>
        </tbody>
      </table>
    `
  }

  const body = rows
    .map((row) => {
      const entries = parseLabelCodeEntries(row.content).slice(0, 8)
      const result = resolveResult(row)
      const isCorrect =
        result.isOpened &&
        entries.some((entry) => entry.label === result.zodiac || entry.codes.includes(result.code))
      const zodiacs = entries
        .map((entry) =>
          isCorrect && entry.label === result.zodiac
            ? `<span style="background-color: #FFFF00">${escapeHtml(entry.label)}</span>`
            : escapeHtml(entry.label)
        )
        .join("")
      const codes = entries
        .flatMap((entry) => entry.codes.slice(0, 2))
        .slice(0, 16)
        .map((code) =>
          isCorrect && code === result.code
            ? `<span style="background-color: #FFFF00">${escapeHtml(code)}</span>`
            : escapeHtml(code)
        )
        .join(".")

      return `
        <tr style="height: 53.25px;">
          <td style="padding: 3px 2px; border: 1px solid #e5e5e5; word-break: break-all; height: 53.25px;" align="center">
            <span style="font-size: 14pt;"><strong><span style="color: #800000;">${escapeHtml(row.term)}期</span><span style="color: #339966;">（8肖16码）</span></strong><span style="color: #008000;"><br></span><span style="color: #ff0000;font-size: 13pt;">&nbsp;${zodiacs}<br>${codes}</span></span>
          </td>
        </tr>
      `
    })
    .join("")

  return `
    <table border="1" width="100%" bgcolor="#ffffff">
      <tbody>
        <tr>
          <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">www.twtongtian.com</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">【八肖十六码】</font></b></p></td>
        </tr>
      </tbody>
    </table>
    <table width="100%" cellspacing="0" cellpadding="0" class="font1">
      <tbody>${body}</tbody>
    </table>
  `
}

function renderFiveaDaGongKai(rows: LegacyModeRow[]) {
  const renderableRows = rows.filter((row) => parseLabelCodeEntries(row.content).length >= 8)
  if (!renderableRows.length) {
    return renderMissingTable('<font color="#FFFF00">站长推荐</font><font color="#FFFFFF">（5A级大公开）</font>')
  }

  return renderableRows
    .map((row) => {
      const entries = parseLabelCodeEntries(row.content).slice(0, 8)
      const result = resolveResult(row)
      const hitZodiac = result.isOpened ? result.zodiac : ""
      const hitCode = result.isOpened ? result.code : ""
      const sevenXiao = entries.slice(0, 7)
      const pingteEntry = entries[7] || entries[0]
      const fourXiao = entries.slice(0, 4)
      const threeXiao = entries.slice(0, 3)
      const twoXiao = entries.slice(0, 2)
      const orderedCodes = entries.flatMap((entry) => entry.codes)
      const tenCodes = orderedCodes.slice(0, 10)
      const eightCodes = orderedCodes.slice(0, 8)
      const fiveCodes = orderedCodes.slice(0, 5)

      const renderXiaoList = (items: LabelCodeEntry[]) =>
        items
          .map((entry) =>
            hitZodiac && entry.label === hitZodiac
              ? `<span style="background-color: #ff0000; color: #FFFF00">${escapeHtml(entry.label)}</span>`
              : `<font>${escapeHtml(entry.label)}</font>`
          )
          .join("")
      const renderCodeList = (codes: string[]) =>
        codes
          .map((code) =>
            hitCode && code === hitCode
              ? `<span style="background-color: #ff0000; color: #FFFF00">${escapeHtml(code)}</span>`
              : `<font>${escapeHtml(code)}</font>`
          )
          .join(".")
      const pingteHtml =
        hitZodiac && pingteEntry.label === hitZodiac
          ? `<span style="background-color: #ff0000; color: #FFFF00">${escapeHtml(pingteEntry.label)}</span>`
          : `<span pt>${escapeHtml(pingteEntry.label)}</span>`

      return `
        <table id="table155" style="border-collapse: collapse; width: 100%; height: 0px;" border="1px" width="100%" cellpadding="0" bgcolor="#ffffff">
          <tbody>
            <tr style="height: 52.2049px;">
              <td class="dbt1" style="background-color: #ff0000; text-align: center; font-size: 22pt; font-family: 楷体; color: #ffffff; height: 52.2049px; font-weight: bold; width: 100%;" colspan="2" height="47"><span style="font-size: 10pt;">5A级大公开</span></td>
            </tr>
            <tr style="height: 41.4757px;">
              <td class="dbt2" style="font-family: 微软雅黑; height: 41.4757px; width: 45.3376%; font-size: 16pt; font-weight: bold;" height="36"><span style="font-size: 10pt;"><span style="color: #ff0000;"><span style="color: #2cbe13;">${escapeHtml(row.term)}期</span><span style="color: #2cbe13;">七肖<span style="color: #ff0000;">${renderXiaoList(sevenXiao)}</span></span><br></span></span></td>
              <td class="dbt3" style="font-family: 微软雅黑; height: 41.4757px; width: 54.6624%; font-size: 16pt; font-weight: bold;" height="36"><span style="font-size: 10pt;"><span style="color: #2cbe13;">平特<span style="color: #ff0000;">:</span></span><span class="dbt9" style="text-align: center; color: #236fa1;">『${pingteHtml}』<span style="color: #ff0000;">开：${renderResultPlain(result, "????")}</span><br></span></span></td>
            </tr>
            <tr style="height: 40.0174px;">
              <td class="dbt2" style="font-family: 微软雅黑; height: 40.0174px; width: 45.3376%; font-size: 16pt; font-weight: bold;" height="36"><span style="font-size: 10pt;"><span style="color: #2cbe13;"><span style="color: #ff0000;"><span style="color: #2cbe13;">${escapeHtml(row.term)}期</span><span style="color: #2cbe13;">四肖<span style="color: #ff0000;">:${renderXiaoList(fourXiao)}<br></span></span></span></span></td>
              <td class="dbt3" style="font-family: 微软雅黑; height: 40.0174px; width: 54.6624%; font-size: 16pt; font-weight: bold;" height="36"><p><span style="font-size: 10pt;"><span style="color: #2cbe13;">⑩码<span style="color: #ff0000;">:</span><span style="color: #ff0000;">${renderCodeList(tenCodes)}</span></span></span></p></td>
            </tr>
            <tr style="height: 40.2257px;">
              <td class="dbt2" style="font-family: 微软雅黑; height: 40.2257px; width: 45.3376%; font-size: 16pt; font-weight: bold;"><span style="font-size: 10pt;"><span style="color: #2cbe13;">${escapeHtml(row.term)}期</span><span style="color: #2cbe13;">三肖<span style="color: #ff0000;">:${renderXiaoList(threeXiao)}</span></span></span></td>
              <td class="dbt3" style="font-family: 微软雅黑; height: 40.2257px; width: 54.6624%; font-size: 16pt; font-weight: bold;"><span style="font-size: 10pt;"><span style="color: #2cbe13;">⑧码<span style="color: #ff0000;">:</span><span style="color: #ff0000;">${renderCodeList(eightCodes)}</span></span></span></td>
            </tr>
            <tr style="height: 36.2674px;">
              <td class="dbt2" style="font-family: 微软雅黑; height: 36.2674px; width: 45.3376%; font-size: 16pt; font-weight: bold;" height="36"><span style="font-size: 10pt;"><span style="color: #2cbe13;">${escapeHtml(row.term)}期</span><span style="color: #2cbe13;">二肖<span style="color: #ff0000;">:${renderXiaoList(twoXiao)}</span></span></span></td>
              <td class="dbt3" style="font-family: 微软雅黑; height: 36.2674px; width: 54.6624%; font-size: 16pt; font-weight: bold;" height="39"><span style="font-size: 10pt;"><span style="color: #2cbe13;">⑤码</span><span style="color: #2cbe13;"><span style="color: #ff0000;">:${renderCodeList(fiveCodes)}</span></span></span></td>
            </tr>
          </tbody>
        </table>
      `
    })
    .join("")
}

function buildYixiaoYimaRows(nineXiaoRows: LegacyModeRow[], oneXiaoRows: LegacyModeRow[]) {
  const x9ByIssue = new Map(
    nineXiaoRows.map((row) => [`${cleanText(row.year)}-${cleanText(row.term)}`, row] as const)
  )
  const x1ByIssue = new Map(
    oneXiaoRows.map((row) => [`${cleanText(row.year)}-${cleanText(row.term)}`, row] as const)
  )
  const issues = [...new Set([...x9ByIssue.keys(), ...x1ByIssue.keys()])]

  return issues
    .map((issue) => {
      const x9Row = x9ByIssue.get(issue)
      const x1Row = x1ByIssue.get(issue)
      if (!x9Row || !x1Row) return null
      const x9 = splitPredictionTokens(x9Row.content).slice(0, 9)
      const entries = parseLabelCodeEntries(x1Row.content)
      if (!x9.length || !entries.length) return null
      const code14 = [...new Set(entries.flatMap((entry) => entry.codes))].slice(0, 18)
      const best = entries[0]
      const result = resolveResult(x1Row)
      const isCorrect = result.isOpened
        ? Boolean(best?.label) &&
          (best.label === result.zodiac || best.codes.includes(result.code))
        : null

      return {
        year: cleanText(x1Row.year),
        term: cleanText(x1Row.term),
        xiao9: x9,
        xiao7: x9.slice(0, 7),
        xiao5: x9.slice(0, 5),
        xiao3: x9.slice(0, 3),
        bestXiao: best?.label || "",
        code14,
        result,
        isCorrect,
      } satisfies YixiaoYimaRow
    })
    .filter((row): row is YixiaoYimaRow => Boolean(row))
    .sort((left, right) => Number.parseInt(right.term, 10) - Number.parseInt(left.term, 10))
    .slice(0, HISTORY_LIMIT)
}

function renderYixiaoYima(rows: YixiaoYimaRow[]) {
  if (!rows.length) return renderYixiaoYimaMissing()

  return rows
    .map((row) => {
      const hitZodiac = row.result.isOpened ? row.result.zodiac : ""
      const hitCode = row.result.isOpened ? row.result.code : ""
      const renderXiaoLine = (items: string[]) =>
        items
          .map((item) =>
            row.isCorrect && item === hitZodiac
              ? `<span style="background-color: #ff0000; color: #FFFF00">${escapeHtml(item)}</span>`
              : `<font>${escapeHtml(item)}</font>`
          )
          .join("")
      const renderCodeLine = () =>
        row.code14
          .map((code) =>
            row.isCorrect && code === hitCode
              ? `<span style="background-color: #ff0000; color: #FFFF00">${escapeHtml(code)}</span>`
              : `<font>${escapeHtml(code)}</font>`
          )
          .join(".")
      const bestXiao = row.isCorrect
        ? `<span style="background-color: #ff0000; color: #FFFF00">${escapeHtml(row.bestXiao)}</span>`
        : `<font>${escapeHtml(row.bestXiao)}</font>`
      const statusText = row.result.isOpened
        ? row.isCorrect
          ? "【中】"
          : "【错】"
        : ""

      return `
        <table style="border-collapse: collapse; width: 99.9412%;" border="1">
          <tbody>
            <tr style="height: 26.125px;">
              <td style="width: 99.9915%; background-color: #0c35f5; height: 26.125px; text-align: center;" colspan="2"><span style="font-size: 14pt; font-family: 'Helvetica Neue', Helvetica, Arial, 'Microsoft Yahei', 'Hiragino Sans GB', 'Heiti SC', 'WenQuanYi Micro Hei', sans-serif;"><strong><span style="color: #ffffff;">${escapeHtml(row.term)}期台湾通天网一肖一码大公开</span></strong></span></td>
            </tr>
            <tr style="height: 48.5278px;">
              <td style="width: 17.4815%; text-align: center; height: 48.5278px;"><strong><span style="font-size: 12pt; color: #0000ff; font-weight: bold; font-family: 'Helvetica Neue', Helvetica, Arial, 'Microsoft Yahei', 'Hiragino Sans GB', 'Heiti SC', 'WenQuanYi Micro Hei', sans-serif;">特码</span></strong></td>
              <td style="width: 82.51%; text-align: left; height: 48.5278px;"><p><span style="font-size: 13pt; color: #ff0000;"><strong>${renderCodeLine()}</strong></span></p></td>
            </tr>
            <tr style="height: 33.5972px;">
              <td style="width: 17.4815%; text-align: center; height: 33.5972px;"><strong><span style="font-size: 12pt; color: #0000ff; font-weight: bold; font-family: 'Helvetica Neue', Helvetica, Arial, 'Microsoft Yahei', 'Hiragino Sans GB', 'Heiti SC', 'WenQuanYi Micro Hei', sans-serif;">一肖</span></strong></td>
              <td style="width: 82.51%; text-align: left; height: 33.5972px;"><strong><span style="font-size: 18pt; color: #34495e;">${bestXiao}</span><span style="font-size: 12pt; color: #34495e;">${escapeHtml(statusText)}</span></strong></td>
            </tr>
            <tr style="height: 24.2639px;">
              <td style="width: 17.4815%; text-align: center; height: 24.2639px;"><strong><span style="font-size: 12pt; color: #0000ff; font-weight: bold; font-family: 'Helvetica Neue', Helvetica, Arial, 'Microsoft Yahei', 'Hiragino Sans GB', 'Heiti SC', 'WenQuanYi Micro Hei', sans-serif;">三肖</span></strong></td>
              <td style="width: 82.51%; text-align: left; height: 24.2639px;"><span style="font-size: 13pt;"><strong><span style="color: #34495e;">${renderXiaoLine(row.xiao3)}</span></strong></span></td>
            </tr>
            <tr style="height: 24.2639px;">
              <td style="width: 17.4815%; text-align: center; height: 24.2639px;"><strong><span style="font-size: 12pt; color: #0000ff; font-weight: bold; font-family: 'Helvetica Neue', Helvetica, Arial, 'Microsoft Yahei', 'Hiragino Sans GB', 'Heiti SC', 'WenQuanYi Micro Hei', sans-serif;">五肖</span></strong></td>
              <td style="width: 82.51%; text-align: left; height: 24.2639px;"><span style="font-size: 13pt;"><strong><span style="color: #34495e;">${renderXiaoLine(row.xiao5)}</span></strong></span></td>
            </tr>
            <tr style="height: 24.2639px;">
              <td style="width: 17.4815%; height: 24.2639px; text-align: center;"><span style="font-family: 'Helvetica Neue', Helvetica, Arial, 'Microsoft Yahei', 'Hiragino Sans GB', 'Heiti SC', 'WenQuanYi Micro Hei', sans-serif;"><strong><span style="color: #0c35f5;">七肖</span></strong></span></td>
              <td style="width: 82.51%; height: 24.2639px; text-align: left;"><span style="font-size: 13pt;"><strong><span style="color: #34495e;">${renderXiaoLine(row.xiao7)}</span></strong></span></td>
            </tr>
            <tr style="height: 24.2639px;">
              <td style="width: 17.4815%; height: 24.2639px; text-align: center;"><span style="font-family: 'Helvetica Neue', Helvetica, Arial, 'Microsoft Yahei', 'Hiragino Sans GB', 'Heiti SC', 'WenQuanYi Micro Hei', sans-serif;"><strong><span style="color: #0c35f5;">九肖</span></strong></span></td>
              <td style="width: 82.51%; height: 24.2639px; text-align: left;"><span style="font-size: 13pt;"><strong><span style="color: #34495e;">${renderXiaoLine(row.xiao9)}</span></strong></span></td>
            </tr>
            <tr style="height: 50.9583px;">
              <td style="height: 50.9583px; width: 99.9915%; text-align: center;" colspan="2"><p><span style="font-family: 'Helvetica Neue', Helvetica, Arial, 'Microsoft Yahei', 'Hiragino Sans GB', 'Heiti SC', 'WenQuanYi Micro Hei', sans-serif; font-size: 12pt;"><strong><span style="color: #0000ff;">${escapeHtml(row.term)}期</span><span style="color: #ff0000;">一肖一码</span><span style="color: #000000;">开奖【www.twtongtian.com】${row.isCorrect ? "中奖" : row.result.isOpened ? "未中" : ""}</span></strong></span></p></td>
            </tr>
          </tbody>
        </table>
      `
    })
    .join("")
}

/**
 * 首页预测模块数据加载。
 *
 * TODO (2026-06-03): 以下模块需要补全数据管道支持：
 *   [missing_data] - 数据生成后 created schema 未正确填充:
 *     - qianhou_24ma (modes_id=110) - 前后24码
 *     - sanxiao_15ma (modes_id=72) - 三肖15码中特
 *     - shisi_mazhong (modes_id=77) - 14码中特
 *     - sixiao_sima (modes_id=78) - 四肖四码
 *     - jixian_texiao (modes_id=43) - 极限特肖
 *     - yijuhua_zhongtema (modes_id=50) - 一句话中特码
 *   [missing_mapping] - 有数据但字段映射不完整:
 *     - yixiao_sanma (modes_id=484) - 一肖三码
 *     - qianhou_texiao (modes_id=219) - 前后特肖
 *     - wenzhuan_baxiao (modes_id=180) - 稳赚八肖
 *     - shiwu_mazhong (modes_id=81) - 15码中特
 *     - daxiao_yitou (modes_id=108) - 大小一头
 *   同时需要为非 type=3 彩种补齐 created schema 数据。
 */
// ===== P1-P3: NEW RENDER FUNCTIONS =====

function renderJixianTexiao(rows: LegacyModeRow[]) {
  const renderable = rows.filter((row) => {
    const zodiacs = splitPredictionTokens(row.content)
    return zodiacs.length >= 2
  })
  if (!renderable.length) {
    return renderMissingTable('<font color="#FFFF00">www.twtongtian.com</font><font color="#FFFFFF">【极限特肖】</font>')
  }
  const body = renderable.slice(0, HISTORY_LIMIT).map((row) => {
    const zodiacs = splitPredictionTokens(row.content).slice(0, 2)
    const result = resolveResult(row)
    const isCorrect = result.isOpened && zodiacs.includes(result.zodiac)
    const display = zodiacs.map((z) =>
      isCorrect && z === result.zodiac
        ? `<span style="background-color: #FFFF00">${escapeHtml(z)}</span>`
        : escapeHtml(z)
    ).join("、")
    return `<tr><td style="color:#000;font-family:微软雅黑;font-weight:700;border:1px solid #000" align="center" width="100%" height="50">
      <font size="3"><span style="color: #00F;">${escapeHtml(row.term)}期</span>:<span style="color: #800000;">极限特肖</span>〖<span style="color: #F00;">${display}</span>〗开：${renderResultJudge(result, isCorrect)}</font></td></tr>`
  }).join("")
  return `<table width="100%" cellspacing="0" cellpadding="0"><tbody><tr><td style="text-align:center" height="60">
    <table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
      <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">www.twtongtian.com</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">【极限特肖】</font></b></p></td>
    </tr></tbody></table></td></tr>${body}</tbody></table>`
}

function renderDaxiaoYitou(rows: LegacyModeRow[]) {
  const renderable = rows.filter((row) => {
    const sizeEntries = parseLabelCodeEntries(row.content)
    const touEntries = parseLabelCodeEntries(row.tou)
    return sizeEntries.length >= 1 || touEntries.length >= 1
  })
  if (!renderable.length) {
    return renderMissingTable('<font color="#FFFF00">特码来迟</font><font color="#FFFFFF">『大小一头』</font>')
  }
  const body = renderable.slice(0, HISTORY_LIMIT).map((row) => {
    const sizeEntry = parseLabelCodeEntries(row.content)[0]
    const touEntry = parseLabelCodeEntries(row.tou)[0]
    const result = resolveResult(row)
    const sizeLabel = sizeEntry?.label || cleanText(row.content)
    const touLabel = touEntry?.label || cleanText(row.tou)
    const codeNum = Number.parseInt(result.code, 10)
    const actualSize = Number.isFinite(codeNum) ? (codeNum >= 25 ? "大" : "小") : ""
    const actualHead = Number.isFinite(codeNum) ? `${Math.floor(codeNum / 10)}头` : ""
    const sizeHit = result.isOpened && (sizeLabel === actualSize || sizeEntry?.codes?.includes(result.code))
    const touHit = result.isOpened && (touLabel === actualHead || touEntry?.codes?.includes(result.code))
    const isCorrect = result.isOpened ? (sizeHit || touHit) : null
    const sizeHtml = sizeHit ? `<span style="background-color: #FFFF00">${escapeHtml(sizeLabel)}</span>` : escapeHtml(sizeLabel)
    const touHtml = touHit ? `<span style="background-color: #FFFF00">${escapeHtml(touLabel)}</span>` : escapeHtml(touLabel)
    return `<tr><td width="100%" height="41"><p align="center"><font face="楷体"><b><font size="4"><font color="#0000FF">${escapeHtml(row.term)}期：</font>【${sizeHtml}+${touHtml}】开<font color="#FF0000">(${renderResultJudge(result, isCorrect)})</font></font></b></font></p></td></tr>`
  }).filter(Boolean).join("")
  return `<table width="100%" cellspacing="0" cellpadding="0"><tbody><tr><td style="text-align:center" height="60">
    <table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
      <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 18pt">特码来迟</font><font color="#FFFFFF" face="楷体" style="font-size: 18pt">『大小一头』</font></b></p></td>
    </tr></tbody></table></td></tr>${body}</tbody></table>`
}

function renderShisiMazhong(rows: LegacyModeRow[]) {
  const renderable = rows.filter((row) => splitPredictionTokens(row.content).length >= 14)
  if (!renderable.length) {
    return renderMissingTable('<font color="#FFFF00">本站出品</font><font color="#FFFFFF">【14码中特】</font>')
  }
  const body = renderable.slice(0, HISTORY_LIMIT).map((row) => {
    const codes = splitPredictionTokens(row.content).slice(0, 14)
    const result = resolveResult(row)
    const isCorrect = result.isOpened && codes.includes(result.code)
    const codeHtml = codes.map((c) =>
      isCorrect && c === result.code
        ? `<span style="background-color: #FFFF00">${escapeHtml(c)}</span>`
        : escapeHtml(c)
    ).join(".")
    const resultDisplay = result.isOpened
      ? escapeHtml(result.code) + escapeHtml(result.zodiac)
      : '?????'
    return `<tr><td style="padding:8px 10px;border:1px solid #ccc;font-size:13pt;font-weight:700;line-height:2.2;">
      <p style="margin:2px 0;"><span style="color:#0000FF;">${escapeHtml(row.term)}期:</span>==14码中特==开${resultDisplay}</p>
      <p style="margin:2px 0;color:#FF0000;">【${codeHtml}】</p>
    </td></tr>`
  }).join("")
  return `<table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
    <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">本站出品</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">【14码中特】</font></b></p></td>
  </tr></tbody></table><table width="100%" cellspacing="0" cellpadding="0" class="font1"><tbody>${body}</tbody></table>`
}

function renderYijuhuaZhongtema(rows: LegacyModeRow[]) {
  const renderable = rows.filter((row) => cleanText(row.content).length > 0 && cleanText(row.jiexi).length > 0)
  if (!renderable.length) {
    return renderMissingTable('<font color="#FFFF00">www.twtongtian.com</font><font color="#FFFFFF">『一句话中特码』</font>')
  }
  const body = renderable.slice(0, HISTORY_LIMIT).map((row) => {
    const title = cleanText(row.title)
    const content = cleanText(row.content)
    const jiexi = cleanText(row.jiexi)
    const result = resolveResult(row)
    const resultDisplay = result.isOpened
      ? escapeHtml(result.code) + escapeHtml(result.zodiac)
      : '?00'
    return `<tr><td style="padding:8px 10px;border:1px solid #ccc;font-size:13pt;font-weight:700;line-height:2.2;">
      <p style="margin:2px 0;"><span style="color:#0000FF;">${escapeHtml(row.term)}期一句真言：</span>${escapeHtml(content)}</p>
      <p style="margin:2px 0;">真言解释：${escapeHtml(jiexi)}</p>
      <p style="margin:2px 0;">真言解肖主前：${escapeHtml(jiexi)} 開:${resultDisplay}</p>
    </td></tr>`
  }).join("")
  return `<table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
    <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">www.twtongtian.com</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">『一句话中特码』</font></b></p></td>
  </tr></tbody></table><table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%"><tbody>${body}</tbody></table>`
}

function renderQianhouTexiao(rows: LegacyModeRow[]) {
  const renderable = rows.filter((row) => {
    const entries = parseLabelCodeEntries(row.content)
    const zodiacs = splitPredictionTokens(row.xiao)
    return entries.length >= 1 || zodiacs.length >= 2
  })
  if (!renderable.length) {
    return renderMissingTable('<font color="#FFFF00">台湾通天网</font><font color="#FFFFFF">【前后特肖】</font>')
  }
  const body = renderable.slice(0, HISTORY_LIMIT).map((row) => {
    const entries = parseLabelCodeEntries(row.content)
    const zodiacs = splitPredictionTokens(row.xiao).slice(0, 2)
    const result = resolveResult(row)
    const isCorrect = result.isOpened && zodiacs.includes(result.zodiac)
    const zHtml = zodiacs.map((z) =>
      isCorrect && z === result.zodiac
        ? `<span style="background-color: #FFFF00">${escapeHtml(z)}</span>`
        : escapeHtml(z)
    ).join("、")
    const frontLabel = entries[0]?.label || "前肖"
    const frontZodiacs = entries[0]?.codes?.length ? entries[0].codes.join("、") : entries[0]?.label || ""
    return `<tr><td width="100%" height="41"><p align="center"><font face="楷体"><b><font size="4">
      <font color="#0000FF">${escapeHtml(row.term)}期：</font>${escapeHtml(frontLabel)}:${escapeHtml(frontZodiacs)}<br>
      特肖【${zHtml}】开<font color="#FF0000">(${renderResultJudge(result, isCorrect)})</font></font></b></font></p></td></tr>`
  }).filter(Boolean).join("")
  return `<table width="100%" cellspacing="0" cellpadding="0"><tbody><tr><td style="text-align:center" height="60">
    <table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
      <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 18pt">台湾通天网</font><font color="#FFFFFF" face="楷体" style="font-size: 18pt">【前后特肖】</font></b></p></td>
    </tr></tbody></table></td></tr>${body}</tbody></table>`
}

function renderQianhou24ma(rows: LegacyModeRow[]) {
  // ---- Static section: permanent fixed number mapping ----
  const staticSection = `
    <table width="100%" cellspacing="0" cellpadding="0"><tbody><tr><td style="padding:8px;background:#fff;border:1px solid #ccc;">
      <p style="text-align:center;color:#FF0000;font-weight:700;font-size:14pt;margin:6px 0;">前后落码【永久固定】</p>
      <p style="text-align:center;color:#0000FF;font-weight:700;font-size:20pt;margin:4px 0;">*************************************************</p>
      <p style="text-align:center;font-weight:700;font-size:13pt;margin:4px 0;line-height:2;">
        <span style="color:#FF0000;">前落码：</span>01 02 03 04 05 06 07 08 17 18 19 20 21 22 23<br>
        　　　　24 33 34 35 36 37 38 39 40<br>
        <span style="color:#008000;">后落码：</span>09 10 11 12 13 14 15 16 25 26 27 28 29 30 31 32<br>
        　　　　41 42 43 44 45 46 47 48 49
      </p>
      <p style="text-align:center;color:#0000FF;font-weight:700;font-size:20pt;margin:4px 0;">*************************************************</p>
    </td></tr></tbody></table>`

  // ---- Dynamic section: per-issue prediction rows ----
  const renderable = rows.filter((row) => {
    const entries = parseLabelCodeEntries(row.content)
    return entries.length >= 1 && entries[0].codes.length >= 24
  })

  if (!renderable.length) {
    return `<table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
      <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">台湾通天网</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">推荐『前后24码』的好料</font></b></p></td>
    </tr></tbody></table>${staticSection}`
  }

  const body = renderable.slice(0, HISTORY_LIMIT).map((row) => {
    const entry = parseLabelCodeEntries(row.content)[0]
    const result = resolveResult(row)
    const isCorrect = result.isOpened && entry.codes.includes(result.code)
    const label = entry.label || ''
    const direction = label.includes('前') ? '前落码' : label.includes('后') ? '后落码' : label
    const resultDisplay = result.isOpened
      ? `<font color="#FF0000">${escapeHtml(result.code)}${escapeHtml(result.zodiac)}</font><font color="${isCorrect ? '#FF0000' : '#000000'}">${isCorrect ? '准' : '错准'}</font>`
      : '?????准'
    return `<tr><td style="padding:4px 10px;border:1px solid #ccc;font-size:13pt;font-weight:700;line-height:1.6;text-align:center;">
      <p style="margin:1px 0;"><span style="color:#0000FF;">${escapeHtml(row.term)}期：</span><span style="background-color:#0000FF;color:#FFFFFF;padding:2px 8px;">【前后落码→24码中特】</span>开${resultDisplay}</p>
      <p style="margin:1px 0;"><span style="background-color:#000000;color:#FFFF00;padding:1px 8px;">↑↑ 【${escapeHtml(direction)}】</span></p>
      <p style="margin:1px 0;color:#0000FF;">*******************</p>
    </td></tr>`
  }).join("")

  return `<table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
    <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">台湾通天网</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">推荐『前后24码』的好料</font></b></p></td>
  </tr></tbody></table>${staticSection}<table width="100%" cellspacing="0" cellpadding="0" class="font1"><tbody>${body}</tbody></table>`
}

function renderSixiaoSima(rows: LegacyModeRow[]) {
  const renderable = rows.filter((row) => parseLabelCodeEntries(row.content).length >= 4)
  if (!renderable.length) {
    return renderMissingTable('<font color="#FFFF00">今日推荐</font><font color="#FFFFFF">『四肖四码』</font>')
  }
  const body = renderable.slice(0, HISTORY_LIMIT).map((row) => {
    const entries = parseLabelCodeEntries(row.content).slice(0, 4)
    const result = resolveResult(row)
    const isCorrect = result.isOpened && entries.some((e) => e.label === result.zodiac || e.codes.includes(result.code))
    const parts = entries.map((entry) => {
      const hitLabel = isCorrect && entry.label === result.zodiac
      const label = hitLabel ? `<span style="background-color: #FFFF00">${escapeHtml(entry.label)}</span>` : escapeHtml(entry.label)
      const code = entry.codes[0] || ''
      const hitCode = isCorrect && code === result.code
      const codeHtml = hitCode ? `<span style="background-color: #FFFF00">${escapeHtml(code)}</span>` : escapeHtml(code)
      return `${label}${codeHtml}`
    }).join(".")
    const resultDisplay = result.isOpened
      ? `${escapeHtml(result.code)}${escapeHtml(result.zodiac)}<font color="${isCorrect ? '#FF0000' : '#000000'}">${isCorrect ? '对' : '错'}</font>`
      : '?????'
    return `<tr><td style="padding:8px 10px;border:1px solid #ccc;font-size:13pt;font-weight:700;line-height:2.2;">
      <p style="margin:2px 0;">第<span style="color:#0000FF;">${escapeHtml(row.term)}</span>期【${parts}】 开：${resultDisplay}</p>
    </td></tr>`
  }).join("")
  return `<table style="border-collapse:collapse;color:#000;font-weight:700;border:1px solid #000" border="1" width="100%"><tbody><tr><td style="text-align:center" height="60">
    <table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
      <td style="border:10px double #00f" bgcolor="#0000FF" height="50"><p align="center"><b><font face="楷体" style="font-size: 20pt"><font color="#FFFF00">今日推荐</font><font color="#FFFFFF">『四肖四码』</font></font></b></p></td>
    </tr></tbody></table></td></tr>${body}</tbody></table>`
}

function renderSanxiao15ma(rows: LegacyModeRow[]) {
  const renderable = rows.filter((row) => {
    const zodiacs = splitPredictionTokens(row.xiao)
    const codes = splitPredictionTokens(row.code)
    return zodiacs.length >= 9 && codes.length >= 15
  })
  if (!renderable.length) {
    return renderMissingTable('<font color="#FFFF00">台湾通天网</font><font color="#FFFFFF">推荐『三肖15码中特』的好料</font>')
  }
  const body = renderable.slice(0, HISTORY_LIMIT).map((row) => {
    const zodiacs = splitPredictionTokens(row.xiao)
    const codes = splitPredictionTokens(row.code)
    const xiao3 = zodiacs.slice(0, 3)
    const xiao5 = zodiacs.slice(0, 5)
    const xiao7 = zodiacs.slice(0, 7)
    const code15 = codes.slice(0, 15)
    const result = resolveResult(row)
    const isCorrect = result.isOpened && (zodiacs.includes(result.zodiac) || code15.includes(result.code))
    const renderZ = (items: string[]) => items.map((z) => isCorrect && z === result.zodiac ? `<span style="background-color: #FFFF00">${escapeHtml(z)}</span>` : escapeHtml(z)).join("")
    const renderC = (items: string[]) => items.map((c) => isCorrect && c === result.code ? `<span style="background-color: #FFFF00">${escapeHtml(c)}</span>` : escapeHtml(c)).join(".")
    return `<tr><td style="padding:8px 10px;border:1px solid #ccc;font-size:13pt;font-weight:700;line-height:2.2;">
      <p style="margin:2px 0;color:#0000FF;">${escapeHtml(row.term)}期七肖中特：www.twtongtian.com长期跟踪</p>
      <p style="margin:2px 0;">(7.)肖特:${renderZ(xiao7)}</p>
      <p style="margin:2px 0;">(5.)肖特:${renderZ(xiao5)}</p>
      <p style="margin:2px 0;">(3.)肖特:${renderZ(xiao3)}</p>
      <p style="margin:2px 0;color:#FF0000;">稳赚特码（15码）</p>
      <p style="margin:2px 0;color:#008000;">${renderC(code15)}</p>
      ${result.isOpened ? `<p style="margin:2px 0;">开:${renderResultJudge(result, isCorrect)}</p>` : ''}
    </td></tr>`
  }).join("")
  return `<table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
    <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">台湾通天网</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">推荐『三肖15码中特』的好料</font></b></p></td>
  </tr></tbody></table><table width="100%" cellspacing="0" cellpadding="0" class="font1"><tbody>${body}</tbody></table>`
}

function renderShiwuMazhong(rows: LegacyModeRow[]) {
  const renderable = rows.filter((row) => parseLabelCodeEntries(row.content).length >= 5)
  if (!renderable.length) {
    return renderMissingTable('<font color="#FFFF00">弑神者</font><font color="#FFFFFF">（www.twtongtian.com）15码中特</font>')
  }
  const body = renderable.slice(0, HISTORY_LIMIT).map((row) => {
    const entries = parseLabelCodeEntries(row.content).slice(0, 5)
    const allCodes = entries.flatMap((e) => e.codes)
    const code15 = allCodes.slice(0, 15)
    const code9 = allCodes.slice(0, 9)
    const threeWei = entries.slice(0, 3)
    const result = resolveResult(row)
    const isCorrect = result.isOpened && allCodes.includes(result.code)
    const renderCodes = (codes: string[]) => codes.map((c) => isCorrect && c === result.code ? `<span style="background-color: #FFFF00">${escapeHtml(c)}</span>` : escapeHtml(c)).join(".")
    const threeWeiHtml = threeWei.map((e) => `${escapeHtml(e.label)}:${e.codes.map((c) => isCorrect && c === result.code ? `<span style="background-color: #FFFF00">${escapeHtml(c)}</span>` : escapeHtml(c)).join(".")}`).join(" &nbsp;")
    return `<tr><td style="padding:6px;border:1px solid #e5e5e5" align="center">
      <span style="font-size:12pt;"><strong><span style="color:#800000;">${escapeHtml(row.term)}期</span><br>
      <span style="color:#0000FF;">三尾:</span><span style="color:#ff0000;">${threeWeiHtml}</span><br>
      <span style="color:#0000FF;">15码:</span><span style="color:#ff0000;">${renderCodes(code15)}</span><br>
      <span style="color:#0000FF;">9码:</span><span style="color:#ff0000;">${renderCodes(code9)}</span><br>
      开:${renderResultJudge(result, isCorrect)}</strong></span></td></tr>`
  }).join("")
  return `<table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
    <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">弑神者</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">（www.twtongtian.com）15码中特</font></b></p></td>
  </tr></tbody></table><table width="100%" cellspacing="0" cellpadding="0" class="font1"><tbody>${body}</tbody></table>`
}

function renderYixiaoSanma(rows: LegacyModeRow[]) {
  const renderable = rows.filter((row) => {
    const zodiacs = splitPredictionTokens(row.xiao)
    const codes = splitPredictionTokens(row.code)
    return zodiacs.length >= 6 && codes.length >= 18
  })
  if (!renderable.length) {
    return renderMissingTable('<font color="#FFFF00">台湾通天网</font><font color="#FFFFFF">推荐一肖三码</font>')
  }
  const body = renderable.slice(0, HISTORY_LIMIT).map((row) => {
    const zodiacs = splitPredictionTokens(row.xiao)
    const codes = splitPredictionTokens(row.code)
    const code18 = codes.slice(0, 18)
    const code9 = codes.slice(0, 9)
    const xiao1 = zodiacs.slice(0, 1)
    const xiao3 = zodiacs.slice(0, 3)
    const xiao6 = zodiacs.slice(0, 6)
    const result = resolveResult(row)
    const isCorrect = result.isOpened && (zodiacs.includes(result.zodiac) || code18.includes(result.code))
    const renderZ = (items: string[]) => items.map((z) => isCorrect && z === result.zodiac ? `<span style="background-color: #FFFF00">${escapeHtml(z)}</span>` : escapeHtml(z)).join("")
    const renderC = (items: string[]) => items.map((c) => isCorrect && c === result.code ? `<span style="background-color: #FFFF00">${escapeHtml(c)}</span>` : escapeHtml(c)).join(".")
    return `<tr><td style="padding:6px;border:1px solid #e5e5e5" align="center">
      <span style="font-size:12pt;"><strong><span style="color:#800000;">${escapeHtml(row.term)}期</span><br>
      <span style="color:#0000FF;">18码:</span><span style="color:#ff0000;">${renderC(code18)}</span><br>
      <span style="color:#0000FF;">9码:</span><span style="color:#ff0000;">${renderC(code9)}</span><br>
      <span style="color:#0000FF;">一肖:</span><span style="color:#ff0000;">${renderZ(xiao1)}</span> &nbsp;
      <span style="color:#0000FF;">三肖:</span><span style="color:#ff0000;">${renderZ(xiao3)}</span> &nbsp;
      <span style="color:#0000FF;">六肖:</span><span style="color:#ff0000;">${renderZ(xiao6)}</span><br>
      开:${renderResultJudge(result, isCorrect)}</strong></span></td></tr>`
  }).join("")
  return `<table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
    <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">台湾通天网</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">推荐一肖三码</font></b></p></td>
  </tr></tbody></table><table width="100%" cellspacing="0" cellpadding="0" class="font1"><tbody>${body}</tbody></table>`
}

function renderWenzhuanBaxiao(rows: LegacyModeRow[]) {
  const renderable = rows.filter((row) => parseLabelCodeEntries(row.content).length >= 8)
  if (!renderable.length) {
    return renderMissingTable('<font color="#FFFFFF">多人来料【稳赚八肖】</font>')
  }
  const body = renderable.slice(0, HISTORY_LIMIT).map((row) => {
    const entries = parseLabelCodeEntries(row.content).slice(0, 8)
    const result = resolveResult(row)
    const isCorrect = result.isOpened && entries.some((e) => e.label === result.zodiac || e.codes.includes(result.code))
    // 家野四肖: first 4 entries
    const jiaYe = entries.slice(0, 4).map((e) => {
      const hit = isCorrect && (e.label === result.zodiac || e.codes.includes(result.code))
      return hit
        ? `<span style="background-color: #FFFF00">${escapeHtml(e.label)}</span>`
        : escapeHtml(e.label)
    }).join(" ")
    // 单双五肖: entries 0-4
    const danShuang = entries.slice(0, 5).map((e) => {
      const hit = isCorrect && (e.label === result.zodiac || e.codes.includes(result.code))
      return hit
        ? `<span style="background-color: #FFFF00">${escapeHtml(e.label)}</span>`
        : escapeHtml(e.label)
    }).join(" ")
    // 无错八肖: all 8
    const wuCuo = entries.map((e) => {
      const hit = isCorrect && (e.label === result.zodiac || e.codes.includes(result.code))
      return hit
        ? `<span style="background-color: #FFFF00">${escapeHtml(e.label)}</span>`
        : escapeHtml(e.label)
    }).join(" ")
    const allCodes = entries.flatMap((e) => e.codes).slice(0, 16)
    const codeHtml = allCodes.map((c) => isCorrect && c === result.code ? `<span style="background-color: #FFFF00">${escapeHtml(c)}</span>` : escapeHtml(c)).join(".")
    return `<tr><td style="padding:6px;border:1px solid #e5e5e5" align="center">
      <span style="font-size:12pt;"><strong><span style="color:#800000;">${escapeHtml(row.term)}期</span><br>
      <span style="color:#0000FF;">家野四肖:</span><span style="color:#ff0000;">${jiaYe}</span><br>
      <span style="color:#0000FF;">单双五肖:</span><span style="color:#ff0000;">${danShuang}</span><br>
      <span style="color:#0000FF;">无错八肖:</span><span style="color:#ff0000;">${wuCuo}</span><br>
      <span style="color:#0000FF;">16码:</span><span style="color:#ff0000;">${codeHtml}</span><br>
      开:${renderResultJudge(result, isCorrect)}</strong></span></td></tr>`
  }).join("")
  return `<table border="1" width="100%" bgcolor="#ffffff"><tbody><tr>
    <td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF"><p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">多人来料</font><font color="#FFFFFF" face="楷体" style="font-size: 20pt">【稳赚八肖】</font></b></p></td>
  </tr></tbody></table><table width="100%" cellspacing="0" cellpadding="0" class="font1"><tbody>${body}</tbody></table>`
}

function renderPmtjImage(rows: LegacyModeRow[]) {
  const latest = rows.find((row) => row.image_url)
  if (!latest) {
    return renderMissingTable('<font color="#FFFF00">台湾通天网</font><font color="#FFFFFF">【跑马图解】</font>')
  }
  const url = normalizeImageUrl(latest.image_url)
  if (!url) {
    return renderMissingTable('<font color="#FFFF00">台湾通天网</font><font color="#FFFFFF">【跑马图解】</font>')
  }
  return `<div class="box amplIMG"><img src="${escapeHtml(url)}" style="width: 100%" title="跑马图解" loading="lazy" decoding="async"></div>`
}

// ===== MODULE STATUS DEFINITIONS =====

const REGION_LABELS: Record<number, string> = { 1: "香港", 2: "澳门", 3: "台湾" }

export async function getTwjinniuHomepageModules(
  lotteryType: TwjinniuLotteryType
): Promise<TwjinniuHomepageModulesResponse> {
  const regionLabel = REGION_LABELS[lotteryType] || "台湾"
  const mode56Rows = await loadLegacyModeRows(56, lotteryType)
  const mode49Rows = await loadLegacyModeRows(49, lotteryType)
  const mode151Rows = await loadLegacyModeRows(151, lotteryType)
  const mode117Rows = await loadLegacyModeRows(117, lotteryType, SANXIAO_SIWEI_SOURCE_LIMIT)
  const mode123Rows = await loadLegacyModeRows(123, lotteryType, SANXIAO_SIWEI_SOURCE_LIMIT)
  const mode110Rows = await loadLegacyModeRows(110, lotteryType)
  const mode72Rows = await loadLegacyModeRows(72, lotteryType)
  const mode77Rows = await loadLegacyModeRows(77, lotteryType)
  const mode78Rows = await loadLegacyModeRows(78, lotteryType)
  const mode31Rows = await loadLegacyModeRows(31, lotteryType)
  const mode83Rows = await loadLegacyModeRows(83, lotteryType, 200)
  const mode43Rows = await loadLegacyModeRows(43, lotteryType)
  const mode79Rows = await loadLegacyModeRows(79, lotteryType)
  const mode103Rows = await loadLegacyModeRows(103, lotteryType)
  const mode173Rows = await loadLegacyModeRows(173, lotteryType)
  const mode219Rows = await loadLegacyModeRows(219, lotteryType)
  const mode81Rows = await loadLegacyModeRows(81, lotteryType)
  const mode108Rows = await loadLegacyModeRows(108, lotteryType)
  const mode15Rows = await loadLegacyModeRows(15, lotteryType)
  const mode142Rows = await loadLegacyModeRows(142, lotteryType)
  const mode50Rows = await loadLegacyModeRows(50, lotteryType)
  const mode279Rows = await loadLegacyModeRows(279, lotteryType)
  const mode180Rows = await loadLegacyModeRows(180, lotteryType)
  const mode484Rows = await loadLegacyModeRows(484, lotteryType)
  const mode476Rows = await loadLegacyModeRows(476, lotteryType, 1)
  const mode474Rows = await loadLegacyModeRows(474, lotteryType, 1)

  const yixiaoYimaRows = buildYixiaoYimaRows(mode49Rows, mode151Rows)
  const sanxiaoSiweiRows = buildSanxiaoSiweiRows(mode117Rows, mode123Rows)

  const modules: Record<HomepageModuleKey, TwjinniuHomepageModulePayload> = {
    formula_ptx: {
      key: "formula_ptx",
      title: "公式平特肖",
      status: mode56Rows.length ? "ok" : "missing_data",
      html: renderFormulaPtx(mode56Rows),
      mappedModeIds: [56],
      notes: mode56Rows.length
        ? [
            "当前按 modes_id 56（pt1xiao / 平特1肖）读取本地 PostgreSQL，并叠加真实开奖号码按原站公式平特肖样式输出。",
          ]
        : ["已按 modes_id 56 查询，本地 PostgreSQL 当前彩种无对应历史数据。"],
    },
    yixiao_yima: {
      key: "yixiao_yima",
      title: "一肖一码大公开",
      status: yixiaoYimaRows.length ? "ok" : "missing_data",
      html: yixiaoYimaRows.length ? renderYixiaoYima(yixiaoYimaRows) : renderYixiaoYimaMissing(),
      mappedModeIds: [49, 151],
      notes: yixiaoYimaRows.length ? [] : ["已按 modes_id 49/151 查询，本地 PostgreSQL 当前彩种无对应历史数据。"],
    },
    sanxiao_siwei: {
      key: "sanxiao_siwei",
      title: "三肖四尾",
      status: sanxiaoSiweiRows.length ? "ok" : "missing_data",
      html: renderSanxiaoSiwei(sanxiaoSiweiRows),
      mappedModeIds: [117, 123],
      notes:
        sanxiaoSiweiRows.length
          ? []
          : mode117Rows.length && mode123Rows.length
            ? ["已按 modes_id 117/123 查询到原始行，但当前返回窗口内没有可按期号配对渲染的记录。"]
            : ["已按 modes_id 117/123 查询，本地 PostgreSQL 当前彩种无可渲染的历史数据。"],
    },
    qianhou_24ma: {
      key: "qianhou_24ma",
      title: "前后24码",
      status: mode110Rows.some((row) => parseLabelCodeEntries(row.content).length >= 1 && parseLabelCodeEntries(row.content)[0].codes.length >= 24) ? "ok" : (mode110Rows.length ? "missing_mapping" : "missing_data"),
      html: renderQianhou24ma(mode110Rows),
      mappedModeIds: [110],
      notes: mode110Rows.length
        ? ["数据字段存在，按前后12码格式渲染。"]
        : ["已按 modes_id 110 查询，本地 PostgreSQL 当前彩种没有历史行。"],
    },
    sanxiao_15ma: {
      key: "sanxiao_15ma",
      title: "三肖15码中特",
      status: mode72Rows.some((row) => splitPredictionTokens(row.xiao).length >= 9 && splitPredictionTokens(row.code).length >= 15) ? "ok" : (mode72Rows.length ? "missing_mapping" : "missing_data"),
      html: renderSanxiao15ma(mode72Rows),
      mappedModeIds: [72],
      notes: mode72Rows.length
        ? ["数据字段存在，按三肖→五肖→七肖→九肖+15码递进展示。"]
        : ["已按 modes_id 72 查询，本地 PostgreSQL 当前彩种没有历史行。"],
    },
    shisi_mazhong: {
      key: "shisi_mazhong",
      title: "14码中特",
      status: mode77Rows.some((row) => splitPredictionTokens(row.content).length >= 14) ? "ok" : (mode77Rows.length ? "missing_mapping" : "missing_data"),
      html: renderShisiMazhong(mode77Rows),
      mappedModeIds: [77],
      notes: mode77Rows.length
        ? ["数据字段存在，按14码网格+开奖高亮展示。"]
        : ["已按 modes_id 77 查询，本地 PostgreSQL 当前彩种没有历史行。"],
    },
    sixiao_bama: {
      key: "sixiao_bama",
      title: "四肖八码",
      status: mode83Rows.some((row) => parseLabelCodeEntries(row.content).length >= 4) ? "ok" : (mode83Rows.some((row) => resolveResult(row).isOpened) ? "ok" : "missing_data"),
      html: renderSixiaoBama(mode83Rows),
      mappedModeIds: [83],
      notes: mode83Rows.some((row) => parseLabelCodeEntries(row.content).length >= 4)
        ? []
        : ["已按 modes_id 83 查询，但当前最新生成行未写入原站所需的四组『生肖|号码』历史结构。"],
    },
    danshuang_sixiao_bama: {
      key: "danshuang_sixiao_bama",
      title: "单双四肖八码",
      status: mode31Rows.some((row) => parseLabelCodeEntries(row.content).length >= 2 || (splitCsv(row.xiao_1).length >= 2 && splitCsv(row.xiao_2).length >= 2)) ? "ok" : "missing_data",
      html: renderDanshuangSixiaoBama(mode31Rows),
      mappedModeIds: [31],
      notes: mode31Rows.length
        ? ["已确认该模块对应 modes_id 31，当前首页先按表内两组四肖数据渲染；原站『八码』号码展开仍需补固定映射同源输出。"]
        : ["已按 modes_id 31 查询，该模块映射已确认，但本地 PostgreSQL 当前彩种无可渲染的历史数据。"],
    },
    pingte_erma: {
      key: "pingte_erma",
      title: "平特二码",
      status: mode79Rows.length ? "ok" : "missing_data",
      html: renderPingteErma(mode79Rows),
      mappedModeIds: [79],
      notes: mode79Rows.length ? [] : ["已确认该模块对应 modes_id 79（平特1肖2码），但当前本地 PostgreSQL 当前彩种没有历史行。"],
    },
    sixiao_sima: {
      key: "sixiao_sima",
      title: "四肖四码",
      status: mode78Rows.some((row) => parseLabelCodeEntries(row.content).length >= 4) ? "ok" : (mode78Rows.length ? "missing_mapping" : "missing_data"),
      html: renderSixiaoSima(mode78Rows),
      mappedModeIds: [78],
      notes: mode78Rows.length
        ? ["数据字段存在，按4组生肖+4码逐行展示。"]
        : ["已按 modes_id 78 查询，本地 PostgreSQL 当前彩种没有历史行。"],
    },
    pingte_xiao: {
      key: "pingte_xiao",
      title: "平特一肖",
      status: mode103Rows.length ? "ok" : "missing_data",
      html: renderPingteXiao(mode103Rows),
      mappedModeIds: [103],
      notes: mode103Rows.length ? [] : ["已按 modes_id 103 查询，本地 PostgreSQL 当前彩种无对应历史数据。"],
    },
    pingte_wei: {
      key: "pingte_wei",
      title: "平特一尾",
      status: mode173Rows.length ? "ok" : "missing_data",
      html: renderPingteWei(mode173Rows),
      mappedModeIds: [173],
      notes: mode173Rows.length ? [] : ["已按 modes_id 173 查询，本地 PostgreSQL 当前彩种无对应历史数据。"],
    },
    yixiao_sanma: {
      key: "yixiao_sanma",
      title: "一肖三码",
      status: mode484Rows.some((row) => splitPredictionTokens(row.xiao).length >= 6 && splitPredictionTokens(row.code).length >= 18) ? "ok" : (mode484Rows.length ? "missing_mapping" : "missing_data"),
      html: renderYixiaoSanma(mode484Rows),
      mappedModeIds: [484],
      notes: mode484Rows.length
        ? ["数据字段存在，按18码→9码→1肖→3肖→6肖递进展示。"]
        : ["已按 modes_id 484 查询，本地 PostgreSQL 当前彩种没有历史行。"],
    },
    jixian_texiao: {
      key: "jixian_texiao",
      title: "极限特肖",
      status: mode43Rows.some((row) => splitPredictionTokens(row.content).length >= 2) ? "ok" : (mode43Rows.length ? "missing_mapping" : "missing_data"),
      html: renderJixianTexiao(mode43Rows),
      mappedModeIds: [43],
      notes: mode43Rows.length
        ? ["数据字段存在，按2个特肖+开奖高亮展示。"]
        : ["已按 modes_id 43 查询，本地 PostgreSQL 当前彩种没有历史行。"],
    },
    fivea_dagongkai: {
      key: "fivea_dagongkai",
      title: "5A级大公开",
      status: mode151Rows.some((row) => parseLabelCodeEntries(row.content).length >= 8) ? "ok" : "missing_data",
      html: renderFiveaDaGongKai(mode151Rows),
      mappedModeIds: [151],
      notes: mode151Rows.some((row) => parseLabelCodeEntries(row.content).length >= 8)
        ? ["已按 modes_id 151 渲染 5A 区块，当前按返回顺序输出 7肖/平特/4肖10码/3肖8码/2肖5码。"]
        : ["已按 modes_id 151 查询，但当前本地 PostgreSQL 当前彩种无可渲染的历史数据。"],
    },
    qianhou_texiao: {
      key: "qianhou_texiao",
      title: "前后特肖",
      status: mode219Rows.some((row) => parseLabelCodeEntries(row.content).length >= 1 || splitPredictionTokens(row.xiao).length >= 2) ? "ok" : (mode219Rows.length ? "missing_mapping" : "missing_data"),
      html: renderQianhouTexiao(mode219Rows),
      mappedModeIds: [219],
      notes: mode219Rows.length
        ? ["数据字段存在，按前肖组+特肖展示。"]
        : ["已按 modes_id 219 查询，本地 PostgreSQL 当前彩种没有历史行。"],
    },
    wenzhuan_baxiao: {
      key: "wenzhuan_baxiao",
      title: "稳赚八肖",
      status: mode180Rows.some((row) => parseLabelCodeEntries(row.content).length >= 8) ? "ok" : (mode180Rows.length ? "missing_mapping" : "missing_data"),
      html: renderWenzhuanBaxiao(mode180Rows),
      mappedModeIds: [180],
      notes: mode180Rows.length
        ? ["数据字段存在，按家野四肖/单双五肖/无错八肖/16码多维度展示。"]
        : ["已按 modes_id 180 查询，本地 PostgreSQL 当前彩种没有历史行。"],
    },
    shiwu_mazhong: {
      key: "shiwu_mazhong",
      title: "15码中特",
      status: mode81Rows.some((row) => parseLabelCodeEntries(row.content).length >= 5) ? "ok" : (mode81Rows.length ? "missing_mapping" : "missing_data"),
      html: renderShiwuMazhong(mode81Rows),
      mappedModeIds: [81],
      notes: mode81Rows.length
        ? ["数据字段存在，按三尾/五尾/15码/9码递进展示。"]
        : ["已按 modes_id 81 查询，本地 PostgreSQL 当前彩种没有历史行。"],
    },
    daxiao_yitou: {
      key: "daxiao_yitou",
      title: "大小一头",
      status: mode108Rows.some((row) => parseLabelCodeEntries(row.content).length >= 1 || parseLabelCodeEntries(row.tou).length >= 1) ? "ok" : (mode108Rows.length ? "missing_mapping" : "missing_data"),
      html: renderDaxiaoYitou(mode108Rows),
      mappedModeIds: [108],
      notes: mode108Rows.length
        ? ["数据字段存在，按大小标记+头数预测展示。"]
        : ["已按 modes_id 108 查询，本地 PostgreSQL 当前彩种没有历史行。"],
    },
    danshuang_liangxiao: {
      key: "danshuang_liangxiao",
      title: "单双两肖",
      status: mode15Rows.length ? "ok" : "missing_data",
      html: renderDanshuangLiangxiao(mode15Rows),
      mappedModeIds: [15],
      notes: mode15Rows.length ? [] : ["已按 modes_id 15 查询，本地 PostgreSQL 当前彩种无对应历史数据。"],
    },
    jiaye_liangxiao: {
      key: "jiaye_liangxiao",
      title: "家野两肖",
      status: mode142Rows.length ? "ok" : "missing_data",
      html: renderJiayeLiangxiao(mode142Rows),
      mappedModeIds: [142],
      notes: mode142Rows.length ? [] : ["已按 modes_id 142 查询，本地 PostgreSQL 当前彩种无对应历史数据。"],
    },
    yijuhua_zhongtema: {
      key: "yijuhua_zhongtema",
      title: "一句话中特码",
      status: mode50Rows.some((row) => cleanText(row.content).length > 0 && cleanText(row.jiexi).length > 0) ? "ok" : (mode50Rows.length ? "missing_mapping" : "missing_data"),
      html: renderYijuhuaZhongtema(mode50Rows),
      mappedModeIds: [50],
      notes: mode50Rows.length
        ? ["数据字段存在，按标题+内容+解析展示。"]
        : ["已按 modes_id 50 查询，该模块映射已确认，但本地 PostgreSQL 当前彩种无可渲染的历史数据。"],
    },
    heshu_daxiao: {
      key: "heshu_daxiao",
      title: "合数大小",
      status: mode279Rows.length ? "ok" : "missing_data",
      html: renderHeShuDaxiao(mode279Rows),
      mappedModeIds: [279],
      notes: mode279Rows.length ? [] : ["已按 modes_id 279 查询，本地 PostgreSQL 当前彩种无对应历史数据。"],
    },
    baxiao_shiliuma: {
      key: "baxiao_shiliuma",
      title: "八肖十六码",
      status: mode180Rows.length ? "ok" : "missing_data",
      html: renderBaXiaoShiLiuMa(mode180Rows),
      mappedModeIds: [180],
      notes: mode180Rows.length ? [] : ["已按 modes_id 180 查询，本地 PostgreSQL 当前彩种无对应历史数据。"],
    },
    pmtj_image: {
      key: "pmtj_image",
      title: "跑马图解",
      status: mode476Rows.some((row) => row.image_url) ? "ok" : "missing_data",
      html: renderPmtjImage(mode476Rows),
      mappedModeIds: [476],
      notes: mode476Rows.some((row) => row.image_url) ? [] : ["已按 modes_id 476 查询，本地 PostgreSQL 当前彩种无对应图片数据。"],
    },
    sxztu_image: {
      key: "sxztu_image",
      title: "四不像图",
      status: mode474Rows.some((row) => row.image_url) ? "ok" : "missing_data",
      html: renderPmtjImage(mode474Rows),
      mappedModeIds: [474],
      notes: mode474Rows.some((row) => row.image_url) ? [] : ["已按 modes_id 474 查询，本地 PostgreSQL 当前彩种无对应图片数据。"],
    },
  }

  // Post-process: add region prefix to all module titles in HTML
  const regionPrefix = `${REGION_LABELS[lotteryType] || "台湾"}`
  const siteName = "台湾通天网"
  const regionHeader = `<p align="center"><b><font color="#FFFF00" face="楷体" style="font-size: 20pt">${siteName} ${regionPrefix}</font></b></p>`
  for (const key of Object.keys(modules)) {
    const mod = modules[key as HomepageModuleKey]
    if (mod.html.includes(siteName)) {
      mod.html = mod.html.replace(new RegExp(siteName, "g"), `${siteName} ${regionPrefix}`)
    } else if (mod.html.includes('border:10px double #00f')) {
      // Standard blue header
      mod.html = mod.html.replace(
        /(<td style="border:10px double #00f[^"]*"[^>]*>)/,
        `$1${regionHeader}`
      )
    } else if (mod.html.includes('background-color: #ff0000')) {
      // fivea_dagongkai red header
      mod.html = mod.html.replace(
        /(<td class="dbt1"[^>]*>)/,
        `$1${regionHeader}`
      )
    } else {
      // Image modules or others: prepend header
      mod.html = `<table border="1" width="100%" bgcolor="#ffffff"><tbody><tr><td style="border:10px double #00f; height: 50px;" bgcolor="#0000FF">${regionHeader}</td></tr></tbody></table>${mod.html}`
    }
  }

  return {
    ok: true,
    site: {
      site_key: SITE?.siteKey || "twjinniu",
      web_id: DEFAULT_WEB_ID,
      lottery_type: lotteryType,
    },
    modules,
    missingModules: Object.values(modules)
      .filter((module) => module.status !== "ok")
      .map((module) => ({
        key: module.key,
        title: module.title,
        status: module.status,
        mappedModeIds: module.mappedModeIds,
      })),
  }
}
