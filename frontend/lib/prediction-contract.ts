import type { PublicHistoryRow, PublicModule, PublicSitePageData } from "@/lib/site-page"
import type { VendorHomepageModule, VendorHomepageModulesResponse } from "@/lib/vendor-homepage"

export type CanonicalPredictionDisplayKind =
  | "text"
  | "tokens"
  | "groups"
  | "image"
  | "composite"
  | "unknown"

export type CanonicalPredictionStatus =
  | "pending"
  | "opened-hit"
  | "opened-miss"
  | "opened-unknown"

export type CanonicalPredictionGroup = {
  key: string
  label?: string
  tokens: string[]
}

export type CanonicalPredictionValue = {
  text: string
  tokens: string[]
  groups: CanonicalPredictionGroup[]
  imageUrl?: string
  extra: Record<string, unknown>
}

export type CanonicalPredictionResult = {
  isOpened: boolean
  isCorrect: boolean | null
  code?: string
  zodiac?: string
  color?: string
  text: string
}

export type CanonicalPredictionSource = {
  kind: "public-site-page" | "vendor-homepage-modules" | "mode-payload-legacy"
  moduleId?: number
  moduleKey: string
  mechanismKey?: string
  displayStyle?: string
  sourceWebId?: number | null
  extra: Record<string, unknown>
}

export type CanonicalPredictionRow = {
  issue: string
  year: string
  term: string
  prediction: CanonicalPredictionValue
  result: CanonicalPredictionResult
  status: CanonicalPredictionStatus
  raw: Record<string, unknown>
}

export type CanonicalPredictionModule = {
  moduleKey: string
  title: string
  displayKind: CanonicalPredictionDisplayKind
  rows: CanonicalPredictionRow[]
  source: CanonicalPredictionSource
}

export type CanonicalPredictionBuildInput = {
  sitePageData?: PublicSitePageData | null
  vendorHomepageModules?: VendorHomepageModulesResponse | null
}

const GROUP_LABELS: Record<string, string> = {
  xiao_9: "九肖",
  xiao_7: "七肖",
  xiao_5: "五肖",
  xiao_4: "四肖",
  xiao_3: "三肖",
  xiao_2: "二肖",
  code_14: "14码",
  code_12: "12码",
  code_8: "8码",
  code_5: "五码",
  code_4: "四码",
  code_3: "三码",
  code_2: "二码",
  wave_groups: "波色",
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

function cleanText(value: unknown) {
  return String(value ?? "").trim()
}

function uniqueStrings(items: unknown[]) {
  return [...new Set(items.map((item) => cleanText(item)).filter(Boolean))]
}

function normalizeCode(value: unknown) {
  const text = cleanText(value)
  if (!text) return ""
  return /^\d{1,2}$/.test(text) ? text.padStart(2, "0") : text
}

function lastLegacyResultToken(value: unknown) {
  const values = cleanText(value)
    .split(/[,，、|]+/)
    .map((item) => item.trim())
    .filter(Boolean)
  return values.at(-1) || ""
}

export function splitPredictionTokens(value: unknown): string[] {
  const text = cleanText(value)
  if (!text) return []

  try {
    const parsed = JSON.parse(text)
    if (Array.isArray(parsed)) {
      return uniqueStrings(parsed)
    }
  } catch {
    // Plain text is common for legacy mode_payload rows.
  }

  const stripped = text.replace(/^[\["']+|[\]"']+$/g, "")
  const split = stripped
    .split(/[,\s.、，|+/-]+/)
    .map((item) => item.trim())
    .filter(Boolean)
  if (split.length > 1) return uniqueStrings(split)

  const chineseChars = Array.from(stripped).filter((item) => /[\u4e00-\u9fff]/.test(item))
  return chineseChars.length > 1 ? uniqueStrings(chineseChars) : [stripped].filter(Boolean)
}

function collectGroupsFromValue(value: unknown, prefix = ""): CanonicalPredictionGroup[] {
  if (Array.isArray(value)) {
    const objectItems = value.filter((item) => item && typeof item === "object")
    if (objectItems.length === value.length && objectItems.length > 0) {
      return objectItems.flatMap((item, index) => {
        const itemRecord = asRecord(item)
        const label = cleanText(itemRecord.label) || `${GROUP_LABELS[prefix] || prefix || "分组"}${index + 1}`
        const tokens = uniqueStrings([
          ...(Array.isArray(itemRecord.codes) ? itemRecord.codes : []),
          ...(Array.isArray(itemRecord.items) ? itemRecord.items : []),
        ])
        return tokens.length ? [{ key: `${prefix || "items"}.${index}`, label, tokens }] : []
      })
    }
    const tokens = uniqueStrings(value)
    return tokens.length
      ? [
          {
            key: prefix || "items",
            label: GROUP_LABELS[prefix],
            tokens,
          },
        ]
      : []
  }

  if (!value || typeof value !== "object") return []

  const groups: CanonicalPredictionGroup[] = []
  for (const [key, nested] of Object.entries(value as Record<string, unknown>)) {
    const groupKey = prefix ? `${prefix}.${key}` : key
    if (Array.isArray(nested)) {
      const objectItems = nested.filter((item) => item && typeof item === "object")
      if (objectItems.length === nested.length && objectItems.length > 0) {
        for (const [index, item] of objectItems.entries()) {
          const itemRecord = asRecord(item)
          const label = cleanText(itemRecord.label) || `${GROUP_LABELS[key] || key}${index + 1}`
          const tokens = uniqueStrings([
            ...("codes" in itemRecord && Array.isArray(itemRecord.codes) ? itemRecord.codes : []),
            ...("items" in itemRecord && Array.isArray(itemRecord.items) ? itemRecord.items : []),
          ])
          if (tokens.length) groups.push({ key: `${groupKey}.${index}`, label, tokens })
        }
        continue
      }

      const tokens = uniqueStrings(nested)
      if (tokens.length) {
        groups.push({ key: groupKey, label: GROUP_LABELS[key], tokens })
      }
      continue
    }

    groups.push(...collectGroupsFromValue(nested, groupKey))
  }
  return groups
}

function collectGroups(...values: unknown[]) {
  const groups = values.flatMap((value) => collectGroupsFromValue(value))
  const seen = new Set<string>()
  return groups.filter((group) => {
    const id = `${group.key}:${group.tokens.join(",")}`
    if (seen.has(id)) return false
    seen.add(id)
    return true
  })
}

/**
 * 判定专用的候选原子集合（**不参与 `prediction.tokens` 的构造**）。
 *
 * `prediction.tokens` 是对外契约，多个站点的 `site-data-adapter.js` 直接消费它
 * 并逐项渲染，形状不能改。因此这里另建一份「判定用候选集合」：把 `标签|号码`
 * 条目展开成号码 / 生肖原子，只用于「候选项是否命中真实开奖」的交叉校验。
 */
/**
 * 站点页判定交叉校验专用的「候选列」白名单。
 *
 * 后端各玩法的候选集合**并不总落在 `content`**：
 *   - 天地生肖（mode 5）/ 三肖15码（mode 72）的候选在 `xiao`；
 *   - 单双公式（mode 15）/ 四字玄机 的候选在 `title` / `jiexi`；
 *   - 单双四肖一类把候选拆成 `xiao_1` / `xiao_2` 两列；
 *   - 家禽野兽在 `jia` / `ye`，黑白肖在 `hei` / `bai`，波色在 `wave`。
 * `canonicalRowFromPublicHistory` 过去只把 `content` 交给 `candidateAtomsForVerdict`，
 * 于是这些玩法的真实命中被判成 `contradicted`，`reconcileVerdict` 再把「对」强制改写成
 * 「错」（线上实测 31 个模块实例受影响，例如 twjinniu `sanxiao15ma` 20 期里 8 期被改判、
 * 四站 `title_5` 天地生肖全部受影响）。vendor 分支本来就带这些列，这里补齐站点页分支。
 *
 * 白名单**刻意不含** `res_code` / `res_sx` / `res_color` / `result_text` / `is_correct`：
 * 一旦把开奖结果列混进候选集合，交叉校验会自动通过，就再也拦不住虚报命中了。
 */
const VERDICT_CANDIDATE_COLUMNS = [
  "content",
  "xiao",
  "code",
  "xiao_1",
  "xiao_2",
  "hei",
  "bai",
  "jia",
  "ye",
  "jiexi",
  "title",
  "wave",
  "tail",
  "tou",
  "wei",
  "dx",
  "ds",
] as const

export function verdictCandidateColumns(raw: Record<string, unknown>): Record<string, unknown> {
  const picked: Record<string, unknown> = {}
  for (const column of VERDICT_CANDIDATE_COLUMNS) {
    const value = raw[column]
    if (value === null || value === undefined) continue
    if (typeof value === "string" && !value.trim()) continue
    picked[column] = value
  }
  return picked
}

export function candidateAtomsForVerdict(input: {
  tokens: unknown[]
  groups?: CanonicalPredictionGroup[]
  extra?: Record<string, unknown>
}): unknown[] {
  const items: unknown[] = [...input.tokens]
  for (const group of input.groups || []) {
    items.push(cleanText(group.label), ...group.tokens)
  }
  const extra = input.extra || {}
  for (const value of Object.values(extra)) {
    if (value === null || value === undefined) continue
    if (typeof value === "string" || typeof value === "number") items.push(value)
    else if (Array.isArray(value)) items.push(...value)
    else if (typeof value === "object") {
      for (const nested of Object.values(value as Record<string, unknown>)) {
        if (typeof nested === "string" || typeof nested === "number") items.push(nested)
      }
    }
  }
  return items
}

function resultFromLegacyFields(input: {
  resultText?: unknown
  isOpened?: unknown
  isCorrect?: unknown
  raw?: Record<string, unknown>
  result?: Record<string, unknown>
}): CanonicalPredictionResult {
  const raw = input.raw || {}
  const result = input.result || {}
  const text =
    cleanText(input.resultText) ||
    cleanText(result.result_text) ||
    cleanText(raw.result_text) ||
    cleanText(raw.res_text)
  const code = normalizeCode(lastLegacyResultToken(result.res_code || raw.res_code || raw.code))
  const zodiac = lastLegacyResultToken(result.res_sx || raw.res_sx || raw.zodiac || raw.sx)
  const color = lastLegacyResultToken(result.res_color || raw.res_color || raw.color)
  const isOpened = Boolean(input.isOpened ?? result.is_opened ?? raw.is_opened)
  const isCorrectValue = input.isCorrect ?? raw.is_correct
  const isCorrect = typeof isCorrectValue === "boolean" ? isCorrectValue : null

  return {
    isOpened,
    isCorrect,
    code: code || undefined,
    zodiac: zodiac || undefined,
    color: color || undefined,
    text,
  }
}

/**
 * 绝杀 / 排除类玩法：候选集合是「排除集」，开奖目标**不在**候选内才算命中。
 * 这类玩法的 `is_correct` 与候选集合是反向关系，不能按「候选命中开奖」校验。
 */
const EXCLUDE_MECHANISM_HINTS = ["杀", "绝杀", "不中", "输尽", "排除", "kill", "exclude"]

/**
 * 平特类玩法（平特一肖 / 平特一尾 / 平特 N 肖…）：命中要看开奖**全部 7 个号码**的
 * 生肖或尾数，而契约层拿到的是后端只按特码口径算出的 `isCandid`。
 * 只拿特码去比对会误判成「候选没命中」，因此这类玩法不在这里做交叉校验。
 */
const FLAT_MECHANISM_HINTS = ["平特", "pt1", "pt2", "pt3", "flat"]

export function isExcludePredictionMechanism(...hints: unknown[]) {
  const haystack = hints.map((item) => cleanText(item)).join(" ")
  if (!haystack) return false
  return EXCLUDE_MECHANISM_HINTS.some((hint) => haystack.includes(hint))
}

export function isFlatPredictionMechanism(...hints: unknown[]) {
  const haystack = hints.map((item) => cleanText(item)).join(" ").toLowerCase()
  if (!haystack) return false
  return FLAT_MECHANISM_HINTS.some((hint) => haystack.includes(hint))
}

/**
 * 头尾组合玩法（`三头四尾` / mode 492）。候选集合由 `N头` 与 `N尾` 两组标签组成，
 * 真实命中目标是「特码头 ∈ 候选头 **或** 特码尾 ∈ 候选尾」任一维度命中即算命中
 * （该玩法在 `backend/src/domains/prediction/category_service.py` 下分类为 MIXED，
 * 按 `backend/CLAUDE.md`「MIXED 的业务命中语义为任一维度命中即算命中」，
 * 与后端 `predict.mechanisms.three_head_four_tail_hit` 同口径）。
 * 候选里的数字是标签的一部分（`2头`）而不是号码原子，所以这类行不能走号码/生肖交叉校验：
 * 否则命中行会被判成 `contradicted`，`reconcileVerdict` 再把上游的「对」强制改写成「错」。
 */
const HEAD_TAIL_MECHANISM_HINTS = ["three_head_four_tail", "三头四尾", "头尾"]

export function isHeadTailPredictionMechanism(...hints: unknown[]) {
  const haystack = hints.map((item) => cleanText(item)).join(" ")
  if (!haystack) return false
  return HEAD_TAIL_MECHANISM_HINTS.some((hint) => haystack.includes(hint))
}

/** 头尾组合玩法的候选：`{"heads":["2头",…],"tails":["6尾",…]}` 或 `2头.4头.1头` 形态。 */
export function candidateHeadTailAtoms(items: unknown[]) {
  const heads = new Set<string>()
  const tails = new Set<string>()
  for (const item of items) {
    for (const part of cleanText(item).split(/[,，、|\s"'[\]{}:：.]+/)) {
      const head = /(\d)\s*头/.exec(part)
      if (head) heads.add(head[1])
      const tail = /(\d)\s*尾/.exec(part)
      if (tail) tails.add(tail[1])
    }
  }
  return { heads: [...heads], tails: [...tails] }
}

/** 候选项里的号码原子（`大|25,26` → `25`、`26`；`37` → `37`）。 */
export function candidateCodeAtoms(items: unknown[]) {
  const atoms: string[] = []
  for (const item of items) {
    for (const part of cleanText(item).split(/[,，、|\s]+/)) {
      const digits = part.replace(/[^\d]/g, "")
      if (digits && digits.length <= 2) atoms.push(String(Number(digits)).padStart(2, "0"))
    }
  }
  return [...new Set(atoms)]
}

/** 候选项里的生肖原子（`鸡|10,22` → `鸡`；`马37` → `马`）。 */
export function candidateZodiacAtoms(items: unknown[]) {
  const atoms: string[] = []
  for (const item of items) {
    for (const char of cleanText(item)) {
      if ("鼠牛虎兔龙蛇马羊猴鸡狗猪".includes(char)) atoms.push(char)
    }
  }
  return [...new Set(atoms)]
}

/**
 * 用「候选集合是否命中真实开奖」交叉校验上游给的 `is_correct`。
 *
 * 上游（后端 `public/api.py` 的机制判定、vendor 聚合模块）在候选集合与判定口径
 * 不一致时会虚报命中：典型是候选只有某个标签（`单` / `大`），或候选是一整串
 * `标签|号码`（如绝杀七码的号码串），而特码/特肖并不在候选集合里，
 * `is_correct` 仍然是 true。
 *
 * 只有「真实开奖目标确实出现在候选集合里」才认为上游的命中可信；否则判为矛盾。
 * 绝杀/排除类与平特类玩法的候选口径与特码不同，返回 `excluded` / `flat`，
 * 交由各自的展示层按自己的规则判定。头尾组合玩法（三头四尾）按「头与尾同时命中」
 * 交叉校验，理由见 `isHeadTailPredictionMechanism`。
 *
 * 返回：
 *   - `"verified"`：候选集合里能找到真实特码或特肖
 *   - `"excluded"`：绝杀/排除类玩法，不做 contains 交叉校验
 *   - `"flat"`：平特类玩法（需要全部 7 个开奖号码），不做特码交叉校验
 *   - `"unverifiable"`：缺少开奖号码或候选项为空
 *   - `"contradicted"`：上游 `is_correct === true`，但候选集合没有命中真实开奖
 */
export type VerdictVerification =
  | "verified"
  | "excluded"
  | "flat"
  | "unverifiable"
  | "contradicted"

export function verifyVerdictAgainstCandidates(input: {
  isCorrect: boolean | null
  isOpened: boolean
  code?: string
  zodiac?: string
  tokens: unknown[]
  groups?: CanonicalPredictionGroup[]
  mechanismHints?: unknown[]
}): VerdictVerification {
  if (input.isCorrect !== true || !input.isOpened) return "verified"
  const hints = input.mechanismHints || []
  if (isExcludePredictionMechanism(...hints)) return "excluded"
  if (isFlatPredictionMechanism(...hints)) return "flat"
  const code = cleanText(input.code)
  const zodiac = cleanText(input.zodiac)
  if (!code && !zodiac) return "unverifiable"

  const items = [
    ...input.tokens,
    ...(input.groups || []).flatMap((group) => [...group.tokens, cleanText(group.label)]),
  ]

  // 三头四尾：头与尾任一维度命中即算命中（见本文件 isHeadTailPredictionMechanism）。
  if (isHeadTailPredictionMechanism(...hints)) {
    const { heads, tails } = candidateHeadTailAtoms(items)
    const special = normalizeCode(code)
    if (!heads.length || !tails.length || !/^\d{2}$/.test(special)) return "unverifiable"
    return heads.includes(special.charAt(0)) || tails.includes(special.charAt(1))
      ? "verified"
      : "contradicted"
  }

  const codes = candidateCodeAtoms(items)
  const zodiacs = candidateZodiacAtoms(items)
  if (!codes.length && !zodiacs.length) return "unverifiable"

  if (code && codes.includes(normalizeCode(code))) return "verified"
  if (zodiac && zodiacs.includes(zodiac)) return "verified"
  return "contradicted"
}

function statusFromResult(result: CanonicalPredictionResult): CanonicalPredictionStatus {
  if (!result.isOpened) return "pending"
  if (result.isCorrect === true) return "opened-hit"
  if (result.isCorrect === false) return "opened-miss"
  return "opened-unknown"
}

/**
 * 把上游 `is_correct` 收敛成「与展示候选集合一致」的判定。
 *
 * 直接透传上游判定会让虚报命中（候选里根本没有真实开奖号码/生肖）继续显示「准」，
 * 因此这里对非绝杀类玩法做交叉校验：候选集合没命中真实开奖时改判为未命中，
 * 并把原始判定与校验结果留在 `raw` 里，便于审计脚本与页面调试追溯。
 */
function reconcileVerdict(input: {
  result: CanonicalPredictionResult
  candidateAtoms: unknown[]
  mechanismHints: unknown[]
}): CanonicalPredictionResult {
  const verification = verifyVerdictAgainstCandidates({
    isCorrect: input.result.isCorrect,
    isOpened: input.result.isOpened,
    code: input.result.code,
    zodiac: input.result.zodiac,
    tokens: input.candidateAtoms,
    mechanismHints: input.mechanismHints,
  })
  if (verification !== "contradicted") return input.result
  return { ...input.result, isCorrect: false }
}

function inferDisplayKind(row: CanonicalPredictionRow): CanonicalPredictionDisplayKind {
  if (row.prediction.imageUrl) return "image"
  if (row.prediction.groups.length > 0) return "groups"
  if (row.prediction.tokens.length > 1) return "tokens"
  if (row.prediction.text) return "text"
  return "unknown"
}

function mergeDisplayKind(kinds: CanonicalPredictionDisplayKind[]): CanonicalPredictionDisplayKind {
  if (kinds.includes("composite")) return "composite"
  if (kinds.includes("groups")) return "groups"
  if (kinds.includes("image")) return "image"
  if (kinds.includes("tokens")) return "tokens"
  if (kinds.includes("text")) return "text"
  return "unknown"
}

function canonicalRowFromPublicHistory(row: PublicHistoryRow, mechanismHints: unknown[] = []): CanonicalPredictionRow {
  const raw = asRecord(row.raw)
  const text = cleanText(row.prediction_text || raw.content || raw.prediction)
  const groups = collectGroups(raw.groups, raw.xiao_groups, raw.code_groups, raw.wave_groups)
  // `tokens` 保持 HEAD 的对外形状（多个站点的 site-data-adapter.js 直接逐项渲染它）。
  const tokens = groups.length ? uniqueStrings(groups.flatMap((group) => group.tokens)) : splitPredictionTokens(text)
  const prediction: CanonicalPredictionValue = {
    text,
    tokens,
    groups,
    imageUrl: cleanText(row.image_url) || undefined,
    extra: {
      content: raw.content,
    },
  }
  const result = reconcileVerdict({
    result: resultFromLegacyFields({
      resultText: row.result_text,
      isOpened: row.is_opened,
      isCorrect: row.is_correct,
      raw,
    }),
    // 判定用候选集合另外构造，不进 `tokens`（`tokens` 是对外契约，形状不能改）。
    // 候选列白名单见 `VERDICT_CANDIDATE_COLUMNS`：只补候选列、绝不补开奖结果列。
    candidateAtoms: candidateAtomsForVerdict({
      tokens,
      groups,
      extra: { ...verdictCandidateColumns(raw) },
    }),
    mechanismHints,
  })

  return {
    issue: cleanText(row.issue),
    year: cleanText(row.year),
    term: cleanText(row.term),
    prediction,
    result,
    status: statusFromResult(result),
    raw: {
      ...raw,
      source_web_id: row.source_web_id,
      prediction_text: row.prediction_text,
      image_url: row.image_url,
      result_text: row.result_text,
      is_opened: row.is_opened,
      is_correct: row.is_correct,
    },
  }
}

export function canonicalizePublicSitePageData(data: PublicSitePageData | null | undefined) {
  if (!data?.modules?.length) return [] as CanonicalPredictionModule[]

  return data.modules.map((module) => {
    const mechanismHints = [
      module.mechanism_key,
      module.title,
      module.cssClass,
      module.default_table,
    ]
    const rows = (module.history || []).map((row) =>
      canonicalRowFromPublicHistory(row, mechanismHints)
    )
    return {
      moduleKey: module.mechanism_key,
      title: module.title,
      displayKind: mergeDisplayKind(rows.map(inferDisplayKind)),
      rows,
      source: {
        kind: "public-site-page",
        moduleId: module.id,
        moduleKey: module.mechanism_key,
        mechanismKey: module.mechanism_key,
        displayStyle: module.cssClass,
        extra: {
          default_modes_id: module.default_modes_id,
          default_table: module.default_table,
          sort_order: module.sort_order,
          status: module.status,
          cssClass: module.cssClass,
        },
      },
    } satisfies CanonicalPredictionModule
  })
}

function vendorResult(row: Record<string, unknown>) {
  return resultFromLegacyFields({
    result: asRecord(row.result),
    isOpened: row.is_opened,
    isCorrect: row.is_correct,
    raw: row,
  })
}

function canonicalRowFromVendorHistory(
  row: Record<string, unknown>,
  mechanismHints: unknown[] = []
): CanonicalPredictionRow {
  const groups = collectGroups(row.groups, row.xiao_groups, row.code_groups, row.wave_groups)
  const text =
    cleanText(row.display_text) ||
    cleanText(row.text) ||
    cleanText(asRecord(row.best_pick).text) ||
    uniqueStrings([
      ...groups.flatMap((group) => group.tokens),
      ...(Array.isArray(row.picks) ? row.picks : []),
      ...(Array.isArray(row.xiao_pair) ? row.xiao_pair : []),
    ]).join(" ")
  // `tokens` 保持 HEAD 的对外形状（twwanli / twsyw / twssz / twjsz666 / twbst528
  // 的 site-data-adapter.js 直接逐项渲染它）。
  const tokens = uniqueStrings([
    ...splitPredictionTokens(text),
    ...groups.flatMap((group) => group.tokens),
    ...(Array.isArray(row.picks) ? row.picks : []),
    ...(Array.isArray(row.xiao_pair) ? row.xiao_pair : []),
  ])
  const vendorExtra = {
    best_pick: row.best_pick,
    daxiao: row.daxiao,
    tou_code: row.tou_code,
    tiandi: row.tiandi,
    xiao_pair: row.xiao_pair,
    picks: row.picks,
    wave_groups: row.wave_groups,
    xiao: row.xiao,
    code: row.code,
    hei: row.hei,
    bai: row.bai,
    formula: row.formula,
    content: row.content,
    heads: row.heads,
    tails: row.tails,
    publications: row.publications,
  }
  const result = reconcileVerdict({
    result: vendorResult(row),
    // 判定用候选集合另外构造（含 best_pick / picks 等展示字段），不进 `tokens`。
    candidateAtoms: candidateAtomsForVerdict({ tokens, groups, extra: vendorExtra }),
    mechanismHints,
  })

  return {
    issue: cleanText(row.issue),
    year: cleanText(row.year),
    term: cleanText(row.term),
    prediction: {
      text,
      tokens,
      groups,
      imageUrl: cleanText(row.image_url) || undefined,
      extra: vendorExtra,
    },
    result,
    status: statusFromResult(result),
    raw: row,
  }
}

export function canonicalizeVendorHomepageModules(data: VendorHomepageModulesResponse | null | undefined) {
  if (!data?.data?.length) return [] as CanonicalPredictionModule[]

  return data.data.map((module: VendorHomepageModule) => {
    const moduleRecord = module as unknown as Record<string, unknown>
    const mechanismHints = [
      moduleRecord.module_key,
      moduleRecord.title,
      moduleRecord.display_style,
    ]
    const rows = (Array.isArray(moduleRecord.history) ? moduleRecord.history : []).map((row) =>
      canonicalRowFromVendorHistory(asRecord(row), mechanismHints)
    )
    return {
      moduleKey: cleanText(moduleRecord.module_key),
      title: cleanText(moduleRecord.title),
      displayKind: "composite",
      rows,
      source: {
        kind: "vendor-homepage-modules",
        moduleKey: cleanText(moduleRecord.module_key),
        displayStyle: cleanText(moduleRecord.display_style),
        sourceWebId: data.site.web_id,
        extra: {
          site: data.site,
          display_style: moduleRecord.display_style,
        },
      },
    } satisfies CanonicalPredictionModule
  })
}

function canonicalRowIssueKey(row: CanonicalPredictionRow) {
  return cleanText(row.issue) || [cleanText(row.year), cleanText(row.term)].filter(Boolean).join("-")
}

function deduplicateCanonicalRows(rows: CanonicalPredictionRow[]) {
  const seen = new Set<string>()
  return rows.filter((row) => {
    const issue = canonicalRowIssueKey(row)
    if (!issue) return true
    if (seen.has(issue)) return false
    seen.add(issue)
    return true
  })
}

function deduplicateCanonicalModuleRows(module: CanonicalPredictionModule): CanonicalPredictionModule {
  return { ...module, rows: deduplicateCanonicalRows(module.rows) }
}

export function buildCanonicalPredictionModules(input: CanonicalPredictionBuildInput) {
  return [
    ...canonicalizePublicSitePageData(input.sitePageData),
    ...canonicalizeVendorHomepageModules(input.vendorHomepageModules),
  ].map(deduplicateCanonicalModuleRows)
}

export function findCanonicalPredictionModule(
  modules: CanonicalPredictionModule[],
  moduleKey: string
) {
  return modules.find(
    (module) =>
      module.moduleKey === moduleKey ||
      module.source.mechanismKey === moduleKey ||
      module.moduleKey === `legacy_${moduleKey}` ||
      module.source.mechanismKey === `legacy_${moduleKey}`
  )
}

