/**
 * 预测号码展示组件 — PreResultBlocks
 * ---------------------------------------------------------------
 * 本组件负责渲染前端页面中的三个核心预测结果模块：
 *   1. 两肖平特王（flat） — 蓝色背景，显示"平特王"预测
 *   2. 三期中特（three） — 白色背景，显示跨期综合预测
 *   3. 双波中特（wave）  — 白色背景，显示双波色预测
 *
 * 数据来源：
 *   - 根据当前 activeGame 从 modulesByGame 中提取对应模块数据
 *   - 也支持从 data.rawModules 中搜索 site-page 配置的模块
 *   - 向下兼容接收静态 rows（data.flatKingRows 等，用于 mock 数据）
 *
 * 对应旧站关系：
 *   - 两肖平特王 → public/vendor/shengshi8800/027ptw.js（旧站独立 JS 文件）
 *   - 三期中特    → public/vendor/shengshi8800/023sqzt.js
 *   - 双波中特    → public/vendor/shengshi8800/012sbzt.js
 */

import type { LotteryPageData, PlainRow, LotteryGame } from "@/lib/lotteryData"
import type { PublicModule } from "@/lib/site-page"

type PreResultBlocksProps = {
  data: LotteryPageData
  /** 按游戏类型分组的模块列表（来自 page.tsx 的 legacy 模块合并结果） */
  modulesByGame?: Record<LotteryGame, PublicModule[]>
  /** 当前选中的游戏类型，用于动态提取对应模块数据 */
  activeGame?: LotteryGame
}

const ZODIAC_SET = new Set(["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"])

/** 对内容中的生肖做黄色高亮，基于结果文本中出现的生肖 */
function hl(content: string, result: string): string {
  // Extract zodiacs from result text (format: "羊09" or "马01")
  const resultZodiacs = [...result].filter(c => ZODIAC_SET.has(c))
  if (resultZodiacs.length === 0) return content
  const matchSet = new Set(resultZodiacs)
  return content.split("").map(c =>
    ZODIAC_SET.has(c) && matchSet.has(c)
      ? `<span class="highlight">${c}</span>` : c
  ).join("")
}

/**
 * 从模块列表中提取指定 mechanism_key 的数据行
 * 支持检索 legacy_ 前缀的键
 */
function extractModuleRows(modules: PublicModule[], key: string): PlainRow[] {
  let mod = modules.find(m => m.mechanism_key === key)
  if (!mod) mod = modules.find(m => m.mechanism_key === `legacy_${key}`)
  if (!mod) return []
  return mod.history.map((row) => ({
    issue: row.issue,
    label: mod.title,
    content: hl(row.prediction_text, row.result_text),
    result: row.result_text,
  }))
}

/**
 * 内部子组件：预测数据表格
 * ---------------------------------------------------------------
 * 根据 kind 参数渲染不同样式的预测数据行表格。
 *
 * @param rows - 预测行数据数组，每行包含期号、标签、预测内容和开奖结果
 * @param kind - 表格样式类型：
 *   - "flat"  ：两肖平特王样式，蓝色背景（bgcolor=3ea7d7），标签为天蓝色文字
 *   - "three" ：三期中特样式，白色背景，标签为蓝色文字
 *   - "wave"  ：双波中特样式，白色背景，内容用 «» 包裹，标签为黑色文字
 *
 * 每个预测行的显示格式为：期号: 标签→[预测内容] 开:结果
 */
function SourceTable({ rows, kind }: { rows: PlainRow[]; kind: "flat" | "three" | "wave" }) {
  return (
    <table
      border={1}
      width="100%"
      className="duilianpt1"
      bgcolor={kind === "flat" ? "3ea7d7" : "#ffffff"}
      cellSpacing={0}
      cellPadding={2}
    >
      <tbody>
        {rows.map((row, idx) => (
          <tr key={`${kind}-${row.issue}-${row.content}-${idx}`}>
            <td>
              {kind === "flat" ? (
                /* ---- 两肖平特王样式（蓝色背景） ---- */
                <>
                  <span className="black-text">{row.issue}:</span>
                  <span className="sky-text">
                    {row.label}→<span className="zl" dangerouslySetInnerHTML={{ __html: `[${row.content}]` }} /></span>{" "}
                  开:{row.result.replace(/^开:/, "")}
                </>
              ) : kind === "three" ? (
                /* ---- 三期中特样式（白色背景） ---- */
                <>
                  <span className="black-text">{row.issue}:</span>
                  <span className="blue-text">
                    {row.label}→<span className="zl" dangerouslySetInnerHTML={{ __html: `[${row.content}]` }} /></span>
                  开:{row.result.replace(/^开:/, "")}
                </>
              ) : (
                /* ---- 双波中特样式（白色背景） ---- */
                <>
                  <span className="blue-text">{row.issue}:</span>
                  <span className="black-text">
                    {row.label}
                    <span className="zl">«</span>
                  </span>
                  <span className="zl" dangerouslySetInnerHTML={{ __html: row.content }} />
                  <span className="black-text">»开:</span>
                  {row.result.replace("开:", "")}
                </>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/**
 * 主组件：预测结果区块容器
 * ---------------------------------------------------------------
 * 渲染三个预测模块的外层容器。
 * 每个模块包含：
 *   - 一个标题栏（.list-title），显示模块名称和标语
 *   - 一个 SourceTable 子组件，显示该模块的具体预测数据行
 *
 * 数据来源优先级：
 *   1. 如果传入了 modulesByGame + activeGame，从对应彩种的 legacy 模块中提取
 *   2. 否则使用 data.flatKingRows / .threeIssueRows / .doubleWaveRows（静态数据）
 *
 * @param props.data          - LotteryPageData 全量数据（含静态行）
 * @param props.modulesByGame - 按游戏类型分组的模块列表
 * @param props.activeGame    - 当前选中的游戏类型
 */
export function PreResultBlocks({ data, modulesByGame, activeGame }: PreResultBlocksProps) {
  // 动态计算三个模块的行数据
  let flatRows: PlainRow[]
  let threeRows: PlainRow[]
  let waveRows: PlainRow[]

  if (modulesByGame && activeGame) {
    // 从当前游戏类型的模块中提取核心模块
    const currentModules = modulesByGame[activeGame]
    flatRows = extractModuleRows(currentModules, "pt2xiao")
    threeRows = extractModuleRows(currentModules, "3zxt")
    waveRows = extractModuleRows(currentModules, "hllx")
  } else {
    // 回退到静态数据
    flatRows = data.flatKingRows
    threeRows = data.threeIssueRows
    waveRows = data.doubleWaveRows
  }

  return (
    <>
      {/* =============== 模块一：两肖平特王 =============== */}
      {flatRows.length > 0 && (
        <div id="3t1">
          <div className="box pad" id="yxym">
            <div className="list-title">
              台湾六合彩→<span className="legacy-red">【</span>两肖平特王
              <span className="legacy-red">】</span>→两肖在手，天下我有
            </div>
            <SourceTable kind="flat" rows={flatRows} />
          </div>
        </div>
      )}

      {/* =============== 模块二：三期中特 =============== */}
      {threeRows.length > 0 && (
        <div id="sqbzBox">
          <div className="box pad" id="yxym">
            <div className="list-title">
              台湾六合彩→<span className="legacy-red">【</span>三期中特
              <span className="legacy-red">】</span>→39821
            </div>
            <SourceTable kind="three" rows={threeRows} />
          </div>
        </div>
      )}

      {/* =============== 模块三：双波中特 =============== */}
      {waveRows.length > 0 && (
        <div id="sbztBox">
          <div className="box pad" id="yxym">
            <div className="list-title">台湾六合彩论坛『双波中特』</div>
            <SourceTable kind="wave" rows={waveRows} />
          </div>
        </div>
      )}
    </>
  )
}
