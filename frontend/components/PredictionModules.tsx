/**
 * 通用预测模块渲染器 — PredictionModules.tsx
 * ---------------------------------------------------------------
 * 职责：渲染后端 /api/public/site-page 返回的所有预测模块。
 *
 * 每个模块按照旧站格式渲染：
 *   ┌──────────────────────────────────────┐
 *   │  .list-title  模块标题               │
 *   ├──────────────────────────────────────┤
 *   │  期号: 预测内容 → 开:结果            │
 *   │  期号: 预测内容 → 开:结果            │
 *   └──────────────────────────────────────┘
 *
 * 使用与旧站完全相同的 CSS 类名：
 *   - .box.pad     — 模块外层容器
 *   - .list-title  — 模块标题栏
 *   - .duilianpt1  — 预测数据表格
 *   - .zl           — 预测内容高亮
 *
 * 数据来源：
 *   - 从 page.tsx 的 transformSitePageData() 获取 rawModules
 *   - rawModules 是后端 /api/public/site-page 返回的 modules[] 数组
 *
 * 扩展方式：
 *   如需对特定 mechanism_key 使用自定义渲染，只需在此文件中
 *   添加对应的 key → 组件映射即可，无需改动其他文件。
 */

"use client"

import type { PublicModule } from "@/lib/site-page"

/** PredictionModules 组件的 Props */
type PredictionModulesProps = {
  /** 后端返回的完整模块列表 */
  modules: PublicModule[]
  /** mechanism_key 黑名单，这些模块已由其他组件（如 PreResultBlocks）渲染 */
  excludeKeys?: string[]
}

/**
 * 渲染单个模块的表格行
 * 格式：期号: 预测内容  开:结果
 *
 * @param issue     - 期号（如 "124期"）
 * @param content   - 预测内容（如 "虎羊" 或 JSON 数组）
 * @param result    - 开奖结果文本（如 "蛇14"）
 * @param isCorrect - 预测正确性：true=准, false=不准, null=待开奖
 */
function ModuleRow({ issue, content, result, isCorrect }: {
  issue: string; content: string; result: string; isCorrect: boolean | null
}) {
  // 尝试解析 JSON 数组内容（六尾中特、九肖一码等）
  let parsedItems: string[] | null = null
  try {
    const parsed = JSON.parse(content)
    if (Array.isArray(parsed)) parsedItems = parsed
  } catch { /* 不是 JSON，保持普通文本 */ }

  // 结果文字颜色：命中=红, 未命中=黑, 待开奖=灰
  const resultColor = isCorrect === null ? "#999" : isCorrect ? "#FF0000" : "#000"
  const resultSuffix = isCorrect === null ? "" : isCorrect ? "✓" : "✗"

  return (
    <tr>
      <td>
        <span className="blue-text">{issue}:</span>
        {parsedItems ? (
          /* JSON 数组格式（六尾中特、九肖一码等）分行展示 */
          <div className="legacy-json-content">
            {parsedItems.map((item, i) => (
              <span key={i} className="legacy-json-item">{item}</span>
            ))}
          </div>
        ) : (
          /* 普通文本格式 */
          <span className="zl">{content}</span>
        )}
        {" "}开:<span style={{ color: resultColor }}>{result}{resultSuffix}</span>
      </td>
    </tr>
  )
}

/**
 * 渲染单个预测模块区块
 * 视觉上与旧站完全一致：box → list-title → duilianpt1 表格
 */
function ModuleSection({ module }: { module: PublicModule }) {
  // 为空时返回 null，不渲染空区块
  if (!module.history || module.history.length === 0) return null

  return (
    <div className="box pad" id={`module-${module.mechanism_key}`}>
      <div className="list-title">
        {module.title}
      </div>
      <table
        border={1}
        width="100%"
        className={module.cssClass || "duilianpt1"}
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
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * 通用预测模块渲染器 — 主组件
 * ---------------------------------------------------------------
 * 遍历 rawModules 数组，为每个模块渲染一个区块。
 * 如果模块的 mechanism_key 在 excludeKeys 中，则跳过
 * （避免与 PreResultBlocks 等专用组件产生重复渲染）。
 *
 * @param props.modules      - 后端返回的完整模块列表
 * @param props.excludeKeys  - 跳过的 mechanism_key 列表
 *
 * 用法示例：
 *   <PredictionModules
 *     modules={pageData.rawModules}
 *     excludeKeys={["pt2xiao", "3zxt", "hllx"]}
 *   />
 */
export function PredictionModules({ modules, excludeKeys = [] }: PredictionModulesProps) {
  // 过滤掉空模块和已由其他组件渲染的模块
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
