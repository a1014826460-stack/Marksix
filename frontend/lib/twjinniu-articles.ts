import "server-only"

import { promises as fs } from "fs"
import path from "path"

import { backendFetchJson, getPublicSitePageData } from "@/lib/backend-api"
import type { DrawHistoryBall, DrawHistoryResponse } from "@/lib/draw-history"
import { splitPredictionTokens } from "@/lib/prediction-contract"
import { getSiteConfig } from "@/lib/sites"
import type { PublicHistoryRow } from "@/lib/site-page"

type SourceKind = "live-module" | "vendor-snapshot" | "missing-live-data"

type ArticleDefinition = {
  id: string
  title: string
  modeId: number
}

type SpecialDrawInfo = DrawHistoryBall

export type TwjinniuArticleRow = {
  issue: string
  predictionHtml: string
  resultHtml: string
  isOpened: boolean
  isCorrect: boolean | null
  lineHtml: string
}

export type TwjinniuArticleDetail = {
  id: string
  title: string
  author: string
  sourceKind: SourceKind
  modeId: number | null
  status: "ok" | "fallback_snapshot" | "missing_live_data"
  missingMapping: boolean
  notes: string[]
  contentHtml: string
  rows: TwjinniuArticleRow[]
  requestedLotteryType: number
}

const SITE = getSiteConfig("twjinniu")
const AUTHOR = "本站推荐"
const INTRO_HTML =
  '<p><b><font face="楷体" size="4"><font color="#FFFFFF"><span style="background-color: #FF0000">站长宣言：</span></font><font color="#0000FF">本网站绝不带一丝参假！如遇改料，假料，马后炮资料，一经查实，直接封号封IP。大神无处不在，真金不怕火炼，实力万人见证！</font></font></b><br></p>'
const SNAPSHOT_DIR = path.join(process.cwd(), "public", "vendor", "twjinniu", "amgst")
const HIGHLIGHT_OPEN = '<span style="background-color: #FFFF00">'
const HIGHLIGHT_CLOSE = "</span>"
const ZODIAC_PATTERN = /[鼠牛虎兔龙蛇马羊猴鸡狗猪龍馬雞豬免]/g
const ZODIAC_ALIAS: Record<string, string> = {
  龍: "龙",
  馬: "马",
  雞: "鸡",
  豬: "猪",
  // `public.fixed_data` 的「文武肖」沿用了厂商写法「免」，实际就是「兔」。
  // 不归一化会让「兔」判定永远匹配不上，列表里也会出现错别字。
  免: "兔",
}

const LIVE_ARTICLE_DEFINITIONS: Record<string, ArticleDefinition> = {
  "7701": { id: "7701", title: "四段中特", modeId: 479 },
  "7702": { id: "7702", title: "稳中三头", modeId: 12 },
  "7703": { id: "7703", title: "稳杀10码", modeId: 481 },
  "7704": { id: "7704", title: "必杀一肖", modeId: 472 },
  "7705": { id: "7705", title: "必杀一尾", modeId: 20 },
  "7706": { id: "7706", title: "四行中特", modeId: 482 },
  "7707": { id: "7707", title: "逢买必中", modeId: 198 },
  "7708": { id: "7708", title: "无错八肖", modeId: 48 },
  "7709": { id: "7709", title: "文武中特", modeId: 144 },
  "7710": { id: "7710", title: "四头必中", modeId: 483 },
  "7711": { id: "7711", title: "家禽野兽", modeId: 14 },
  "7712": { id: "7712", title: "天地生肖", modeId: 5 },
  "7713": { id: "7713", title: "精选4肖", modeId: 47 },
  "7714": { id: "7714", title: "合数大小", modeId: 279 },
  "7715": { id: "7715", title: "5尾中特", modeId: 66 },
  "7716": { id: "7716", title: "一波中特", modeId: 143 },
  "7717": { id: "7717", title: "精准五行", modeId: 53 },
  "7718": { id: "7718", title: "双波中特", modeId: 38 },
  "7719": { id: "7719", title: "合数单双", modeId: 132 },
  "7720": { id: "7720", title: "琴棋书画", modeId: 26 },
  "7721": { id: "7721", title: "吉凶六肖", modeId: 480 },
  "7722": { id: "7722", title: "7尾中特", modeId: 74 },
}

const LIVE_ARTICLE_DEFINITIONS_BY_TITLE: Record<string, ArticleDefinition> = Object.values(
  LIVE_ARTICLE_DEFINITIONS
).reduce<Record<string, ArticleDefinition>>((result, definition) => {
  result[definition.title] = definition
  return result
}, {})

const LIVE_ARTICLE_ID_ALIASES: Record<string, string> = {
  "7679": "7701",
  "7680": "7702",
  "7681": "7703",
  "7682": "7704",
  "7683": "7705",
  "7684": "7706",
  "7685": "7707",
  "7686": "7708",
  "7687": "7709",
  "7688": "7710",
}

const LIVE_ARTICLE_TITLE_ALIASES: Record<string, string> = {
  准杀十码: "7703",
}

const PENDING_RESULT_BY_ARTICLE: Record<string, string> = {
  "7702": "???????",
  "7707": "???????",
  "7711": "?????",
  "7714": "?????",
  "7716": "?????",
  "7717": "?????",
  "7719": "?????",
  "7721": "",
}

const FULL_WRAP_MISS_ARTICLES = new Set(["7702", "7711"])

function escapeHtml(value: string) {
  return value
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

function normalizeZodiac(value: unknown) {
  const text = String(value ?? "").trim()
  return ZODIAC_ALIAS[text] || text
}

function splitCsv(value: unknown) {
  return String(value ?? "")
    .split(/[,\s]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function parseJsonArray(value: unknown) {
  const text = String(value ?? "").trim()
  if (!text) return [] as unknown[]
  try {
    const parsed = JSON.parse(text)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function parsePipeItems(value: unknown) {
  const text = String(value ?? "").trim()
  const parsed = parseJsonArray(text)
  const items = parsed.length ? parsed : text ? [text] : []

  return items
    .map((item) => {
      const raw = String(item ?? "").trim()
      if (!raw) return null
      if (!raw.includes("|")) {
        return {
          label: raw,
          values: [] as string[],
        }
      }
      const [label, valuesRaw = ""] = raw.split("|", 2)
      return {
        label: label.trim(),
        values: splitCsv(valuesRaw),
      }
    })
    .filter((item): item is { label: string; values: string[] } => Boolean(item?.label))
}

function parseZodiacs(value: unknown) {
  const text = String(value ?? "").trim()
  if (!text) return [] as string[]
  const pieces = text
    .split(/[,\s]+/)
    .map((item) => normalizeZodiac(item))
    .filter(Boolean)
  if (pieces.length > 1) return pieces
  return Array.from(text.match(ZODIAC_PATTERN) || []).map((item) => normalizeZodiac(item))
}

function resolveSpecialCode(row: PublicHistoryRow, draw?: SpecialDrawInfo) {
  if (draw?.value) return normalizeCode(draw.value)
  const raw = row.raw || {}
  const codes = splitCsv(raw.res_code || raw.code)
  return normalizeCode(codes.at(-1) || "")
}

function resolveSpecialZodiac(row: PublicHistoryRow, draw?: SpecialDrawInfo) {
  if (draw?.zodiac) return normalizeZodiac(draw.zodiac)
  const raw = row.raw || {}
  const zodiacs = splitCsv(raw.res_sx || raw.zodiac || raw.sx)
  return normalizeZodiac(zodiacs.at(-1) || "")
}

function resolveSpecialWave(row: PublicHistoryRow, draw?: SpecialDrawInfo) {
  if (draw?.wave) {
    return draw.wave.endsWith("波") ? draw.wave : `${draw.wave}波`
  }
  const raw = row.raw || {}
  const colors = splitCsv(raw.res_color)
  const last = colors.at(-1) || ""
  if (last === "red") return "红波"
  if (last === "blue") return "蓝波"
  if (last === "green") return "绿波"
  return ""
}

function resolveSpecialElement(draw?: SpecialDrawInfo) {
  return String(draw?.element || "").trim()
}

function resolveSpecialHead(row: PublicHistoryRow, draw?: SpecialDrawInfo) {
  const code = resolveSpecialCode(row, draw)
  const value = Number(code)
  if (!Number.isFinite(value)) return ""
  return String(Math.floor(value / 10))
}

function resolveSpecialTail(row: PublicHistoryRow, draw?: SpecialDrawInfo) {
  const code = resolveSpecialCode(row, draw)
  const value = Number(code)
  if (!Number.isFinite(value)) return ""
  return String(value % 10)
}

function resolveCombinedOddEven(row: PublicHistoryRow, draw?: SpecialDrawInfo) {
  if (draw?.combinedOddEven) return String(draw.combinedOddEven).trim()
  const code = Number(resolveSpecialCode(row, draw))
  if (!Number.isFinite(code)) return ""
  const sum = Math.floor(code / 10) + (code % 10)
  return sum % 2 === 1 ? "合单" : "合双"
}

function resolveCombinedSize(row: PublicHistoryRow, draw?: SpecialDrawInfo) {
  const code = Number(resolveSpecialCode(row, draw))
  if (!Number.isFinite(code)) return ""
  const sum = Math.floor(code / 10) + (code % 10)
  return sum >= 7 ? "合数大" : "合数小"
}

function resolveOddEvenLabel(row: PublicHistoryRow, draw?: SpecialDrawInfo) {
  if (draw?.oddEven === "单") return "单数"
  if (draw?.oddEven === "双") return "双数"
  const code = Number(resolveSpecialCode(row, draw))
  if (!Number.isFinite(code)) return ""
  return code % 2 === 1 ? "单数" : "双数"
}

function resolveSizeLabel(row: PublicHistoryRow, draw?: SpecialDrawInfo) {
  if (draw?.size === "大") return "大数"
  if (draw?.size === "小") return "小数"
  const code = Number(resolveSpecialCode(row, draw))
  if (!Number.isFinite(code)) return ""
  return code >= 25 ? "大数" : "小数"
}

function resolveAnimalType(draw?: SpecialDrawInfo) {
  return String(draw?.animalType || "").trim()
}

function highlightText(text: string, match: string) {
  if (!match) return escapeHtml(text)
  const index = text.indexOf(match)
  if (index < 0) return escapeHtml(text)
  return [
    escapeHtml(text.slice(0, index)),
    HIGHLIGHT_OPEN,
    escapeHtml(match),
    HIGHLIGHT_CLOSE,
    escapeHtml(text.slice(index + match.length)),
  ].join("")
}

function renderJoinedTokens(tokens: string[], separator = "", match = "") {
  return tokens.map((token) => (token === match ? highlightText(token, match) : escapeHtml(token))).join(separator)
}

function firstPredictionLabel(row: PublicHistoryRow) {
  const raw = row.raw || {}
  const pipeLabel = parsePipeItems(raw.content).at(0)?.label
  if (pipeLabel) return pipeLabel
  return splitPredictionTokens(row.prediction_text || raw.content).at(0) || ""
}

function tailOrHeadLabels(row: PublicHistoryRow) {
  const raw = row.raw || {}
  const pipeLabels = parsePipeItems(raw.content).map((item) => item.label.replace(/[^\d]/g, "")).filter(Boolean)
  if (pipeLabels.length) return pipeLabels
  return splitPredictionTokens(row.prediction_text || raw.content)
    .map((item) => item.replace(/[^\d]/g, "") || item)
    .filter(Boolean)
}

function zodiacLabels(row: PublicHistoryRow) {
  const raw = row.raw || {}
  const pipeLabels = parsePipeItems(raw.content).map((item) => normalizeZodiac(item.label)).filter(Boolean)
  if (pipeLabels.length) return pipeLabels
  return splitPredictionTokens(row.prediction_text || raw.content).map((item) => normalizeZodiac(item)).filter(Boolean)
}

function waveLabels(row: PublicHistoryRow) {
  const raw = row.raw || {}
  const pipeLabels = parsePipeItems(raw.content).map((item) => item.label).filter(Boolean)
  if (pipeLabels.length) return pipeLabels
  return splitPredictionTokens(row.prediction_text || raw.content).filter(Boolean)
}

function elementLabels(row: PublicHistoryRow) {
  const raw = row.raw || {}
  const pipeLabels = parsePipeItems(raw.content).map((item) => item.label).filter(Boolean)
  if (pipeLabels.length) return pipeLabels
  return splitPredictionTokens(row.prediction_text || raw.content).filter(Boolean)
}

/**
 * 琴棋书画（mode 26）的四艺固定分组：琴、棋、书、画各占 3 个生肖。
 *
 * 唯一权威来源是 `public.fixed_data` sign='四艺生肖'，三处口径必须一致：后端
 * `public/api.py::_QQSH_ZODIAC_MAP`、各站同口径渲染（twwanli / twbst528 / twjsz666 /
 * twcaibawang），以及这里的兜底常量：琴=兔蛇鸡、棋=鼠牛狗、书=虎龙马、画=羊猴猪。
 * 线上每行还带 `raw.qinqi_reference`（同一份 fixed_data 的展示串），存在时优先用它
 * 反查，避免库内分组与常量表漂移。
 */
const QINQI_ART_FALLBACK: Record<string, string> = {
  兔: "琴",
  蛇: "琴",
  鸡: "琴",
  鼠: "棋",
  牛: "棋",
  狗: "棋",
  虎: "书",
  龙: "书",
  马: "书",
  羊: "画",
  猴: "画",
  猪: "画",
}

const QINQI_ARTS = new Set(["琴", "棋", "书", "画"])

/** 解析 `raw.qinqi_reference`（`琴:兔蛇鸡　棋:鼠牛狗\n书:虎龙马　画:羊猴猪`）为 生肖→艺。 */
function parseQinqiReference(value: unknown) {
  const mapping: Record<string, string> = {}
  for (const part of String(value ?? "").split(/[\s　]+/)) {
    const [labelRaw = "", valuesRaw = ""] = part.split(/[:：]/, 2)
    const label = labelRaw.trim()
    if (!QINQI_ARTS.has(label)) continue
    for (const zodiac of Array.from(valuesRaw.trim())) {
      const normalized = normalizeZodiac(zodiac)
      if (normalized) mapping[normalized] = label
    }
  }
  return mapping
}

/** 本期行的 生肖→艺 映射：优先用行自带 fixed_data 说明，缺失时退回站点同口径常量表。 */
function qinqiZodiacArtMap(row: PublicHistoryRow) {
  const reference = parseQinqiReference((row.raw || {}).qinqi_reference)
  return Object.keys(reference).length ? reference : QINQI_ART_FALLBACK
}

/**
 * mode 26 的上屏值必须是**艺名**（琴 / 棋 / 书 / 画），不能把 `content` 里的 9 个
 * 候选生肖直接展示给用户。
 *
 * `raw.title` 存的就是按本期顺序排列的艺名（如 `画,琴,书`），`raw.content` 是同一
 * 顺序展开的 9 个候选生肖。少数历史/厂商行的 `title` 可能为空（此时
 * `prediction_text` 只剩 9 个生肖），因此做两级兜底：
 * 1. `raw.title` 能解析出艺名 → 直接用（保持数据原文顺序，不自己排序）；
 * 2. 否则按 生肖→艺 分组反查，取每个艺首次出现的顺序。
 */
function qinqiArtLabels(row: PublicHistoryRow) {
  const raw = row.raw || {}
  const fromTitle = splitPredictionTokens(raw.title).flatMap((token) =>
    QINQI_ARTS.has(token) ? [token] : Array.from(token).filter((char) => QINQI_ARTS.has(char))
  )
  if (fromTitle.length) return fromTitle

  const artByZodiac = qinqiZodiacArtMap(row)
  const contentTokens = splitPredictionTokens(raw.content)
  const source = contentTokens.length ? contentTokens : splitPredictionTokens(row.prediction_text)
  const arts: string[] = []
  for (const token of source) {
    const art = artByZodiac[normalizeZodiac(token)]
    if (art && !arts.includes(art)) arts.push(art)
  }
  return arts
}

/**
 * 「二选一」生肖分组模块：候选组只有一组，另一组的信息必须来自静态说明。
 *
 * 144 文武中特（文肖 / 武肖）与 480 吉凶六肖（凶丑 / 吉美）在 `created.mode_payload_*`
 * 里每期只落**一个**组标签（如 `["文肖|免,猪,羊,鸡,鼠,龙"]`），而展示规范 S6 要求
 * 两组固定分组说明都要显示。因此从该模块自己的历史行里收集全部出现过的分组，
 * 合成一条与期号无关的分组说明；某一期恰好抽到的那组加下划线。
 */
const TWO_CHOICE_GROUP_MODE_IDS = new Set([144, 480])

type GroupDefinition = {
  label: string
  values: string[]
}

/** 收集该模块历史行里出现过的全部「组|成员」定义，按首次出现顺序去重。 */
export function collectGroupDefinitions(rows: PublicHistoryRow[]): GroupDefinition[] {
  const definitions: GroupDefinition[] = []
  const seen = new Set<string>()
  for (const row of rows) {
    for (const item of parsePipeItems((row.raw || {}).content ?? row.prediction_text)) {
      if (!item.label || seen.has(item.label)) continue
      const values = item.values.map((value) => normalizeZodiac(value)).filter(Boolean)
      if (!values.length) continue
      seen.add(item.label)
      definitions.push({ label: item.label, values })
    }
  }
  return definitions
}

function renderGroupLegend(rows: PublicHistoryRow[], modeId: number) {
  if (!TWO_CHOICE_GROUP_MODE_IDS.has(modeId)) return ""
  if (!rows.length) return ""

  const definitions = collectGroupDefinitions(rows)
  if (definitions.length < 2) return ""

  const currentLabel = firstPredictionLabel(rows[0])
  const parts = definitions.map((definition) => {
    const shown = definition.values.join("")
    const isCurrent = definition.label === currentLabel
    const text = `${escapeHtml(definition.label)}：${escapeHtml(shown)}`
    return isCurrent
      ? `<span style="text-decoration: underline;">${text}</span> <font color="#FF0000">（本期）</font>`
      : text
  })

  return `<p style="font-weight:700;color:#000080;margin:2px 0;">【${escapeHtml(
    definitions.map((definition) => definition.label).join(" / ")
  )} 固定分组】${parts.join("　")}</p>`
}

/** 该模块本轮用于展示的分组说明（S6）；非二选一模块返回空串。 */
export function buildGroupLegendHtml(rows: PublicHistoryRow[], modeId: number) {
  return renderGroupLegend(rows, modeId)
}

function buildLiveContentHtml(rows: TwjinniuArticleRow[], groupLegendHtml = "") {
  return `${INTRO_HTML}${groupLegendHtml}${rows.map((row) => row.lineHtml).join("")}`
}

function domesticWildPrediction(row: PublicHistoryRow) {
  const raw = row.raw || {}
  const jia = parseZodiacs(raw.jia)
  const ye = parseZodiacs(raw.ye)
  if (jia.length || ye.length) return { jia, ye }

  const groups = parsePipeItems(raw.content)
  const byLabel = new Map(groups.map((item) => [item.label, item.values.map((value) => normalizeZodiac(value))]))
  return {
    jia: byLabel.get("家禽") || byLabel.get("家") || [],
    ye: byLabel.get("野兽") || byLabel.get("野") || [],
  }
}

function renderPredictionInner(article: ArticleDefinition, row: PublicHistoryRow, draw?: SpecialDrawInfo) {
  switch (article.modeId) {
    case 12:
      return renderJoinedTokens(tailOrHeadLabels(row), "-", row.is_correct === true ? resolveSpecialHead(row, draw) : "")
    case 14: {
      const prediction = domesticWildPrediction(row)
      const hit = row.is_correct === true ? resolveSpecialZodiac(row, draw) : ""
      return {
        jiaHtml: renderJoinedTokens(prediction.jia, "", hit),
        yeHtml: renderJoinedTokens(prediction.ye, "", hit),
      }
    }
    case 20:
    case 66:
    case 74:
      return renderJoinedTokens(tailOrHeadLabels(row), "-", row.is_correct === true ? resolveSpecialTail(row, draw) : "")
    case 38:
    case 143:
      return renderJoinedTokens(waveLabels(row), "", row.is_correct === true ? resolveSpecialWave(row, draw) : "")
    case 47:
    case 144:
    case 472:
      return renderJoinedTokens(zodiacLabels(row), "", row.is_correct === true ? resolveSpecialZodiac(row, draw) : "")
    case 48: {
      const items = parsePipeItems((row.raw || {}).content || row.prediction_text)
      if (items.length) {
        const hit = row.is_correct === true ? resolveSpecialZodiac(row, draw) : ""
        return items
          .map((item) => {
            const code = normalizeCode(item.values[0] || "")
            const text = `${normalizeZodiac(item.label)}${code}`
            return hit && text.includes(hit) ? highlightText(text, hit) : escapeHtml(text)
          })
          .join("")
      }
      return escapeHtml(row.prediction_text || "")
    }
    case 53:
    case 482:
      return renderJoinedTokens(elementLabels(row), "-", row.is_correct === true ? resolveSpecialElement(draw) : "")
    case 198: {
      const label = firstPredictionLabel(row)
      const hitOptions = [resolveOddEvenLabel(row, draw), resolveSizeLabel(row, draw), resolveAnimalType(draw)]
      const shouldHighlight = row.is_correct === true && hitOptions.includes(label)
      return shouldHighlight ? highlightText(label, label) : escapeHtml(label)
    }
    case 279: {
      const label = firstPredictionLabel(row)
      const hit = row.is_correct === true ? resolveCombinedSize(row, draw) : ""
      return hit === label ? highlightText(label, label) : escapeHtml(label)
    }
    case 132: {
      const label = firstPredictionLabel(row)
      const hit = row.is_correct === true ? resolveCombinedOddEven(row, draw) : ""
      return hit === label ? highlightText(label, label) : escapeHtml(label)
    }
    case 26: {
      // 上屏艺名（如 画琴书），只把特肖命中的那个艺高亮；未开奖 / 未命中一律零高亮
      // （未开奖时 is_correct 为 null，不参与高亮，与本站其它模块口径一致）。
      const arts = qinqiArtLabels(row)
      const special = row.is_correct === true ? resolveSpecialZodiac(row, draw) : ""
      const hitArt = special ? qinqiZodiacArtMap(row)[special] || "" : ""
      return renderJoinedTokens(arts, "", hitArt)
    }
    case 480: {
      // 吉凶六肖的正文是 `吉美|兔,龙,蛇,马,羊,鸡`。原实现只上屏组名「吉美」，
      // 把 6 个候选肖整个丢掉，用户看不到任何预测内容（违反 S6）。
      const group = parsePipeItems((row.raw || {}).content).at(0)
      if (!group) return escapeHtml(firstPredictionLabel(row))
      const zodiacs = group.values.map((value) => normalizeZodiac(value)).filter(Boolean)
      const special = row.is_opened ? resolveSpecialZodiac(row, draw) : ""
      const list = renderJoinedTokens(zodiacs, "", special)
      return `${escapeHtml(group.label)}：${list}`
    }
    default:
      return escapeHtml(String(row.prediction_text || "").trim())
  }
}

function buildResultHtml(article: ArticleDefinition, row: PublicHistoryRow, draw?: SpecialDrawInfo) {
  if (article.modeId === 480) {
    return ""
  }

  if (!row.is_opened) {
    return PENDING_RESULT_BY_ARTICLE[article.id] ?? "???????"
  }

  const code = resolveSpecialCode(row, draw)
  const zodiac = resolveSpecialZodiac(row, draw)
  const text = `${code}${zodiac}`.trim()
  if (!text) {
    return '<font color="#FF0000">已开奖</font>'
  }

  if (row.is_correct === true) {
    return `<font color="#FF0000">${escapeHtml(text)}对</font>`
  }

  if (row.is_correct === false) {
    if (FULL_WRAP_MISS_ARTICLES.has(article.id)) {
      return `<font color="#000000">${escapeHtml(text)}错</font>`
    }
    return `${escapeHtml(text)}<font color="#000">错</font>`
  }

  return `<font color="#FF0000">${escapeHtml(text)}</font>`
}

function buildRowHtml(article: ArticleDefinition, row: PublicHistoryRow, draw?: SpecialDrawInfo): TwjinniuArticleRow {
  const rendered = renderPredictionInner(article, row, draw)
  const resultHtml = buildResultHtml(article, row, draw)

  if (article.modeId === 14 && rendered && typeof rendered === "object") {
    const lineHtml =
      `<p>${escapeHtml(row.issue)}期 家: 【<span style="color: #2ecc71">${rendered.jiaHtml}</span>】开 ;` +
      `野: 【<span style="color: #2ecc71">${rendered.yeHtml}</span>】开 ${resultHtml} </p>`
    return {
      issue: row.issue,
      predictionHtml: `${rendered.jiaHtml} / ${rendered.yeHtml}`,
      resultHtml,
      isOpened: row.is_opened,
      isCorrect: row.is_correct,
      lineHtml,
    }
  }

  const predictionHtml = typeof rendered === "string" ? rendered : ""
  const lineHtml =
    article.modeId === 480
      ? `<p>${escapeHtml(row.issue)}期 ${escapeHtml(article.title)} 【<span style="color: #2ecc71">${predictionHtml}</span>】 </p>`
      : `<p>${escapeHtml(row.issue)}期 ${escapeHtml(article.title)} 【<span style="color: #2ecc71">${predictionHtml}</span>】开 ${resultHtml} </p>`

  return {
    issue: row.issue,
    predictionHtml,
    resultHtml,
    isOpened: row.is_opened,
    isCorrect: row.is_correct,
    lineHtml,
  }
}

async function readSnapshotHtml(articleId: string) {
  const filePath = path.join(SNAPSHOT_DIR, `${articleId}.html`)
  try {
    return await fs.readFile(filePath, "utf-8")
  } catch {
    return null
  }
}

function extractSnapshotMeta(articleId: string, html: string) {
  const titleMatch = html.match(/<title>([^|<]+)\|/i)
  const authorMatch = html.match(/作者:([^<]+)/i)
  const contentMatch = html.match(/<div class="topic-content">([\s\S]*?)<\/div><font/i)
  const definition = LIVE_ARTICLE_DEFINITIONS[articleId]
  const title = (titleMatch?.[1] || definition?.title || articleId).trim()

  return {
    title,
    author: (authorMatch?.[1] || AUTHOR).trim(),
    contentHtml: (contentMatch?.[1] || INTRO_HTML).trim(),
    definition,
  }
}

function extractSnapshotDetail(articleId: string, html: string): TwjinniuArticleDetail {
  const meta = extractSnapshotMeta(articleId, html)

  return {
    id: articleId,
    title: meta.title,
    author: meta.author,
    sourceKind: "vendor-snapshot",
    modeId: meta.definition?.modeId ?? null,
    status: "fallback_snapshot",
    missingMapping: !meta.definition?.modeId,
    notes: meta.definition?.modeId
      ? ["当前后端未返回该模块历史数据，暂时回退到内置静态快照。"]
      : ["该文章的预测模块映射仍未确认，当前使用内置静态快照。"],
    contentHtml: meta.contentHtml,
    rows: [],
    requestedLotteryType: SITE?.defaultLotteryTypeId || 3,
  }
}

async function loadDrawIssueMap(lotteryType: number) {
  try {
    const response = await backendFetchJson<DrawHistoryResponse>("/public/draw-history", {
      query: {
        lottery_type: lotteryType,
        year: new Date().getFullYear(),
        page: 1,
        page_size: 200,
      },
    })

    return new Map(
      (response.items || [])
        .filter((item) => item.specialBall)
        .map((item) => [`${response.year}${item.issue}`, item.specialBall as SpecialDrawInfo])
    )
  } catch {
    return new Map<string, SpecialDrawInfo>()
  }
}

function buildMissingLiveArticleDetail(
  article: ArticleDefinition,
  lotteryType: number
): TwjinniuArticleDetail {
  return {
    id: article.id,
    title: article.title,
    author: AUTHOR,
    sourceKind: "missing-live-data",
    modeId: article.modeId,
    status: "missing_live_data",
    missingMapping: false,
    notes: [
      `当前彩种 lottery_type=${lotteryType} 在本地 PostgreSQL 中缺少模块 ${article.title}（mode_id=${article.modeId}）的预测数据，页面不再回退旧静态快照。`,
    ],
    contentHtml: `${INTRO_HTML}<p><b><font color="#FF0000">当前彩种数据库暂无该模块的实时预测数据，请先补齐对应 PostgreSQL 记录。</font></b></p>`,
    rows: [],
    requestedLotteryType: lotteryType,
  }
}

async function loadLiveArticle(
  article: ArticleDefinition,
  lotteryType: number
): Promise<TwjinniuArticleDetail | null> {
  if (!SITE) {
    return null
  }

  const [sitePage, drawMap] = await Promise.all([
    getPublicSitePageData({
      siteId: SITE.defaultWebId,
      lotteryType,
      historyLimit: 10,
    }),
    loadDrawIssueMap(lotteryType),
  ])

  const module = sitePage.modules.find((item) => Number(item.default_modes_id) === article.modeId)
  if (!module || !module.history.length) {
    return buildMissingLiveArticleDetail(article, lotteryType)
  }

  const history = module.history.slice(0, 10)
  const rows = history.map((row) => buildRowHtml(article, row, drawMap.get(row.issue)))

  return {
    id: article.id,
    title: article.title,
    author: AUTHOR,
    sourceKind: "live-module",
    modeId: article.modeId,
    status: "ok",
    missingMapping: false,
    notes: [],
    contentHtml: buildLiveContentHtml(rows, renderGroupLegend(history, article.modeId)),
    rows,
    requestedLotteryType: lotteryType,
  }
}

async function loadLiveArticleOrFailureDetail(
  article: ArticleDefinition,
  lotteryType: number
) {
  try {
    return await loadLiveArticle(article, lotteryType)
  } catch (error) {
    return {
      id: article.id,
      title: article.title,
      author: AUTHOR,
      sourceKind: "missing-live-data" as const,
      modeId: article.modeId,
      status: "missing_live_data" as const,
      missingMapping: false,
      notes: [
        `读取本地 PostgreSQL 中的 ${article.title}（mode_id=${article.modeId}）失败：${error instanceof Error ? error.message : "未知错误"}`,
      ],
      contentHtml: `${INTRO_HTML}<p><b><font color="#FF0000">当前无法从本地 PostgreSQL 读取该模块数据，请检查数据库连接或对应 mode_payload_* 记录。</font></b></p>`,
      rows: [],
      requestedLotteryType: lotteryType,
    } satisfies TwjinniuArticleDetail
  }
}

export async function getTwjinniuArticleDetail(
  articleId: string,
  options?: {
    lotteryType?: number
  }
) {
  const normalizedId = String(articleId || "").trim()
  if (!normalizedId) {
    return null
  }
  const lotteryType = Number(options?.lotteryType) || SITE?.defaultLotteryTypeId || 3

  const aliasedArticleId = LIVE_ARTICLE_ID_ALIASES[normalizedId]
  const definition =
    LIVE_ARTICLE_DEFINITIONS[normalizedId] ||
    LIVE_ARTICLE_DEFINITIONS[aliasedArticleId || ""]
  if (definition) {
    const live = await loadLiveArticleOrFailureDetail(definition, lotteryType)
    if (live) {
      if (aliasedArticleId) {
        return {
          ...live,
          id: normalizedId,
          notes: [
            `旧历史文章 ID ${normalizedId} 已直接映射到当前 PostgreSQL 实时模块《${definition.title}》。`,
            ...live.notes,
          ],
        }
      }
      return live
    }
  }

  const snapshot = await readSnapshotHtml(normalizedId)
  if (!snapshot) {
    return null
  }

  const snapshotMeta = extractSnapshotMeta(normalizedId, snapshot)
  const aliasedDefinition =
    LIVE_ARTICLE_DEFINITIONS_BY_TITLE[snapshotMeta.title] ||
    LIVE_ARTICLE_DEFINITIONS[LIVE_ARTICLE_TITLE_ALIASES[snapshotMeta.title] || ""]
  if (aliasedDefinition) {
    const live = await loadLiveArticleOrFailureDetail(aliasedDefinition, lotteryType)
    if (live) {
      return {
        ...live,
        id: normalizedId,
        notes: [
          `旧历史文章 ID ${normalizedId} 已按标题《${snapshotMeta.title}》映射到当前 PostgreSQL 实时模块。`,
          ...live.notes,
        ],
      }
    }
  }

  return extractSnapshotDetail(normalizedId, snapshot)
}

export function getTwjinniuArticleDefinition(articleId: string) {
  const normalizedId = String(articleId || "").trim()
  return (
    LIVE_ARTICLE_DEFINITIONS[normalizedId] ||
    LIVE_ARTICLE_DEFINITIONS[LIVE_ARTICLE_ID_ALIASES[normalizedId] || ""] ||
    null
  )
}

export function getTwjinniuSiteRequestDefaults(lotteryType?: number) {
  return SITE
    ? {
        site_key: SITE.siteKey,
        site_id: SITE.defaultWebId,
        web_id: SITE.defaultWebId,
        lottery_type: Number(lotteryType) || SITE.defaultLotteryTypeId,
        domain: SITE.domains[0] || null,
      }
    : null
}
