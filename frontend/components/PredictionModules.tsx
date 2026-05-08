/**
 * 通用预测模块渲染器 — PredictionModules.tsx
 * ---------------------------------------------------------------
 * 职责：渲染所有预测模块，按 mechanism_key 分发到自定义渲染器，
 *       或使用通用 duilianpt1 格式渲染。
 *
 * 渲染优先级：
 *   1. LEGACY_RENDERERS[mechanism_key] — 注册表中的自定义渲染器
 *   2. MODULE_FORMATS[mechanism_key]   — 括号样式配置
 *   3. 默认 duilianpt1 通用格式
 *
 * 旧站渲染格式（匹配各 JS 文件的 HTML 模板）：
 *   ┌────────────────────────────────────────────────────┐
 *   │  .list-title 台湾六合彩论坛『模块标题』           │
 *   ├────────────────────────────────────────────────────┤
 *   │  269期: 预测内容 开:结果准                         │
 *   │  268期: 预测内容 开:结果准                         │
 *   └────────────────────────────────────────────────────┘
 */

"use client"

import type { PublicModule } from "@/lib/site-page"
import { LEGACY_RENDERERS } from "./LegacyModuleRegistry"

/** PredictionModules 组件的 Props */
type PredictionModulesProps = {
  /** 后端返回的完整模块列表 */
  modules: PublicModule[]
  /** mechanism_key 黑名单，这些模块已由其他组件（如 PreResultBlocks）渲染 */
  excludeKeys?: string[]
}

// ===================== 模块格式配置 =====================

type ModuleFormatConfig = {
  /** 内容前的标签文字（如 "必中六肖"、"灭庄三行"） */
  label?: string
  /** 开奖结果前缀（旧站统一用 "开" 或 "开:"） */
  resultPrefix?: string
  /** 是否总是显示 "准" 后缀（旧站行为） */
  alwaysZhun?: boolean
  /** 内容前的左括号样式 */
  leftBracket?: string
  /** 内容后的右括号样式 */
  rightBracket?: string
  /** 表格 CSS 类名覆盖（如 "ptyx11", "bzlx", "sqbk"） */
  tableClass?: string
  /** 是否对命中内容做黄色高亮 */
  highlight?: boolean
  /** 模块标题覆盖 */
  title?: string
  /** 是否为 bracket 格式（九肖一码用【】括起所有内容） */
  bracket?: boolean
}

const DEFAULT_FORMAT: ModuleFormatConfig = {
  leftBracket: "",
  rightBracket: "",
  resultPrefix: "开:",
  alwaysZhun: false,
}

// ★ 关键配置：所有使用通用 duilianpt1 渲染的模块在此定义括号和标签
const MODULE_FORMATS: Record<string, ModuleFormatConfig> = {
  // ==================== Category A: 简单 duilianpt1 + 括号 ====================

  // 六肖中特 → 旧站 007lxzt.js
  legacy_lxzt: {
    label: "必中六肖",
    leftBracket: "«",
    rightBracket: "»",
    resultPrefix: "开",
    alwaysZhun: true,
  },

  // 三头中特 → 旧站 009stzt.js
  legacy_3tou: {
    label: "台湾三头",
    leftBracket: "«",
    rightBracket: "»",
    resultPrefix: "开",
    alwaysZhun: true,
  },

  // 心特（三行中特）→ 旧站 013shzt.js
  legacy_xingte: {
    label: "灭庄三行",
    leftBracket: "«",
    rightBracket: "»",
    resultPrefix: "开:",
    alwaysZhun: true,
  },

  // 平特一肖 → 旧站 002ptyx.js
  legacy_ptyx: {
    label: "平特一肖",
    leftBracket: "««",
    rightBracket: "»»",
    resultPrefix: "开",
    alwaysZhun: true,
  },

  // 平特尾 → 旧站 006ptyw.js
  legacy_ptyw: {
    label: "平特一尾",
    leftBracket: "《",
    rightBracket: "》",
    resultPrefix: "开",
    alwaysZhun: true,
  },

  // 绝杀一尾 → 旧站 024jsyw.js
  legacy_shawei: {
    label: "绝杀一尾",
    leftBracket: "→[",
    rightBracket: "]",
    resultPrefix: "开:",
    alwaysZhun: true,
  },

  // ★ 新增：大小中特 → 旧站 003dxzt.js — 〔〔内容〕〕 括号
  legacy_dxzt: {
    label: "精准大小",
    leftBracket: "〔〔",
    rightBracket: "〕〕",
    resultPrefix: "开:",
    alwaysZhun: true,
  },

  // ★ 新增：家野中特 → 旧站 004jyzt.js — 〈〈内容〉〉 括号
  legacy_jyzt: {
    label: "火爆家野",
    leftBracket: "〈〈",
    rightBracket: "〉〉",
    resultPrefix: "开:",
    alwaysZhun: true,
  },

  // ★ 新增：双波中特 → 旧站 012sbzt.js（已在 PreResultBlocks 渲染，此处作后备）
  legacy_hllx: {
    label: "双波中特",
    leftBracket: "«",
    rightBracket: "»",
    resultPrefix: "开:",
    alwaysZhun: true,
  },

  // ==================== Category F: 特殊格式 ====================

  // ★ 新增：特段 → 旧站 016teduan.js
  legacy_teduan: {
    label: "开特码段",
    leftBracket: "【",
    rightBracket: "】",
    resultPrefix: "开:",
    alwaysZhun: true,
  },

  // ★ 新增：单双四肖 → 旧站 031dssx.js — [单：4肖][双：4肖]
  legacy_dssx: {
    label: "",
    leftBracket: "[",
    rightBracket: "]",
    resultPrefix: "开:",
    alwaysZhun: true,
  },

  // ★ 新增：九肖一码（精选九肖暂用通用格式，后续用自定义渲染器替换）
  legacy_9x1m: {
    bracket: true,
    resultPrefix: "开:",
  },

  // ==================== Category E: 文本模块（legacy-module-text） ====================

  // 一句真言、欲钱买特码等通过 tableClass 在 legacy-modules.ts 中指定
  // 这些模块的 cssClass 已在定义中设为 "duilianpt1 legacy-module-text"
}

// ===================== 渲染子组件 =====================

/**
 * 获取命中高亮 HTML
 * 对预测内容中匹配开奖生肖的字符添加黄色背景
 */
function getHighlightedContent(content: string, resSx: string, isCorrect: boolean | null): string {
  if (!isCorrect || !resSx) return content
  const sxList = resSx.split(",").filter(Boolean).map(s => s.trim())
  const matching = new Set(sxList)
  const ZODIAC_SET = new Set(["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"])

  return content.split("").map(char => {
    if (ZODIAC_SET.has(char) && matching.has(char)) {
      return `<span class="highlight">${char}</span>`
    }
    return char
  }).join("")
}

function ModuleRow({ issue, content, result, isCorrect, format, resSx }: {
  issue: string; content: string; result: string; isCorrect: boolean | null; format?: ModuleFormatConfig; resSx?: string
}) {
  const fmt = format || DEFAULT_FORMAT

  // 尝试解析 JSON 数组内容（六尾中特、九肖一码等）
  let parsedItems: string[] | null = null
  try {
    const parsed = JSON.parse(content)
    if (Array.isArray(parsed)) parsedItems = parsed
  } catch { /* not JSON */ }

  const resultClass = isCorrect === null ? "result-pending" : isCorrect ? "result-hit" : "result-miss"
  const resultText = result === "待开奖" ? "？00" : result

  let resultSuffix = ""
  if (fmt.alwaysZhun) {
    resultSuffix = isCorrect !== null ? "准" : ""
  } else {
    resultSuffix = isCorrect === null ? "" : isCorrect ? " 准" : " 错"
  }

  // bracket 模式（九肖一码）
  if (fmt.bracket && parsedItems) {
    const bracketContent = `【${parsedItems.join("")}】`
    return (
      <tr>
        <td>
          <span className="blue-text">{issue}:</span>
          <span className="zl">{bracketContent}</span>
          {" "}{fmt.resultPrefix || "开:"}<span className={resultClass}>{resultText}{resultSuffix}</span>
        </td>
      </tr>
    )
  }

  // JSON 数组格式
  if (parsedItems) {
    return (
      <tr>
        <td>
          <span className="blue-text">{issue}:</span>
          <div className="legacy-json-content">
            {parsedItems.map((item, i) => (
              <span key={i} className="legacy-json-item">{item}</span>
            ))}
          </div>
          {" "}{fmt.resultPrefix || "开:"}<span className={resultClass}>{resultText}{resultSuffix}</span>
        </td>
      </tr>
    )
  }

  // 普通文本格式
  return (
    <tr>
      <td>
        <span className="blue-text">{issue}:</span>
        {fmt.label ? (
          <>
            <span className="black-text">{fmt.label}</span>
            {fmt.leftBracket && <span className="zl">{fmt.leftBracket}</span>}
            <span className="zl" dangerouslySetInnerHTML={{
              __html: fmt.highlight
                ? getHighlightedContent(content, resSx || "", isCorrect || false)
                : content
            }} />
            {fmt.rightBracket && <span className="black-text">{fmt.rightBracket}</span>}
          </>
        ) : (
          <>
            {fmt.leftBracket && <span className="zl">{fmt.leftBracket}</span>}
            <span className="zl" dangerouslySetInnerHTML={{
              __html: fmt.highlight
                ? getHighlightedContent(content, resSx || "", isCorrect || false)
                : content
            }} />
            {fmt.rightBracket && <span className="black-text">{fmt.rightBracket}</span>}
          </>
        )}
        {" "}{fmt.resultPrefix || "开:"}<span className={resultClass}>{resultText}{resultSuffix}</span>
      </td>
    </tr>
  )
}

// ===================== 主渲染器 =====================

function ModuleSection({ module }: { module: PublicModule }) {
  if (!module.history || module.history.length === 0) return null

  // 优先级 1: 自定义渲染器（注册表中查找）
  const CustomRenderer = LEGACY_RENDERERS[module.mechanism_key]
  if (CustomRenderer) {
    return <CustomRenderer module={module} />
  }

  // 优先级 2: MODULE_FORMATS 配置
  const format = MODULE_FORMATS[module.mechanism_key] || DEFAULT_FORMAT

  // ★ 重要：如果模块的 tableClass 包含 ptyx11/bzlx/sqbk，应使用自定义渲染器
  // 目前这些模块暂用通用格式，后续迁移到注册表

  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">
        {format.title || module.title}
      </div>
      <table
        border={1}
        width="100%"
        className={module.cssClass || format.tableClass || "duilianpt1"}
        bgcolor="#ffffff"
        cellSpacing={0}
        cellPadding={2}
      >
        <tbody>
          {module.history.map((row, idx) => (
            <ModuleRow
              key={`${module.mechanism_key}-${row.issue}-${row.prediction_text}-${idx}`}
              issue={row.issue}
              content={row.prediction_text}
              result={row.result_text}
              isCorrect={row.is_correct}
              resSx={String(row.raw?.res_sx || "")}
              format={format}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * 通用预测模块渲染器 — 主组件
 */
export function PredictionModules({ modules, excludeKeys = [] }: PredictionModulesProps) {
  const visibleModules = modules.filter(
    (m) => m.history && m.history.length > 0 && !excludeKeys.includes(m.mechanism_key)
  )

  if (visibleModules.length === 0) {
    return null
  }

  return (
    <>
      {visibleModules.map((module) => (
        <ModuleSection key={module.mechanism_key} module={module} />
      ))}
    </>
  )
}
