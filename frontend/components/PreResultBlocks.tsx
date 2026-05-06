/**
 * 预测号码展示组件 — PreResultBlocks
 * ---------------------------------------------------------------
 * 本组件负责渲染前端页面中的三个核心预测结果模块：
 *   1. 两肖平特王（flat） — 蓝色背景，显示"平特王"预测
 *   2. 三期中特（three） — 白色背景，显示跨期综合预测
 *   3. 双波中特（wave）  — 白色背景，显示双波色预测
 *
 * 数据来源：
 *   - 由父组件通过 data props 传入（LotteryPageData 类型）
 *   - 实际生产数据由 getPublicSitePageData() 从后端 /api/public/site-page 获取
 *   - 目前使用的是 lotteryData.ts 中的静态 mock 数据
 *
 * 对应旧站关系：
 *   - 两肖平特王 → public/vendor/shengshi8800/027ptw.js（旧站独立 JS 文件）
 *   - 三期中特    → public/vendor/shengshi8800/023sqzt.js
 *   - 双波中特    → public/vendor/shengshi8800/012sbzt.js
 *
 * 注意：这 3 个模块仅为新 React 架构的一小部分，
 *       旧站中实际共有 43 个预测模块，通过独立 JS 文件各自发起 AJAX 请求。
 *       新架构需逐步将所有模块迁移至此。
 */

import type { LotteryPageData, PlainRow } from "@/lib/lotteryData"

type PreResultBlocksProps = {
  data: LotteryPageData
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
        {rows.map((row) => (
          <tr key={`${kind}-${row.issue}-${row.content}`}>
            <td>
              {kind === "flat" ? (
                /* ---- 两肖平特王样式（蓝色背景） ---- */
                <>
                  <span className="black-text">{row.issue}:</span>
                  <span className="sky-text">
                    {row.label}→<span className="zl">[{row.content}]</span>{" "}
                  </span>
                  开:{row.result}
                </>
              ) : kind === "three" ? (
                /* ---- 三期中特样式（白色背景） ---- */
                <>
                  <span className="black-text">{row.issue}:</span>
                  <span className="blue-text">
                    {row.label}→<span className="zl">[{row.content}]</span>
                  </span>
                  {row.result}
                </>
              ) : (
                /* ---- 双波中特样式（白色背景） ---- */
                <>
                  <span className="blue-text">{row.issue}:</span>
                  <span className="black-text">
                    {row.label}
                    <span className="zl">«</span>
                  </span>
                  <span className="zl">{row.content}</span>
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
 * @param data - LotteryPageData 类型的页面数据
 *               包含了三个模块各自的预测行数据（flatKingRows / threeIssueRows / doubleWaveRows）
 */
export function PreResultBlocks({ data }: PreResultBlocksProps) {
  return (
    <>
      {/* =============== 模块一：两肖平特王 =============== */}
      {/* id="3t1" 对应旧站 027ptw.js 中 AJAX 渲染的目标容器 */}
      <div id="3t1">
        <div className="box pad" id="yxym">
          <div className="list-title">
            台湾六合彩→<span className="legacy-red">【</span>两肖平特王
            <span className="legacy-red">】</span>→两肖在手，天下我有
          </div>
          {/* rows 数据源: LotteryPageData.flatKingRows */}
          {/* 数据结构: Array<{ issue: 期号, label: "平特王", content: 预测生肖, result: 开奖结果 }> */}
          <SourceTable kind="flat" rows={data.flatKingRows} />
        </div>
      </div>

      {/* =============== 模块二：三期中特 =============== */}
      {/* id="sqbzBox" 对应旧站 023sqzt.js 中 AJAX 渲染的目标容器 */}
      <div id="sqbzBox">
        <div className="box pad" id="yxym">
          <div className="list-title">
            台湾六合彩→<span className="legacy-red">【</span>三期中特
            <span className="legacy-red">】</span>→39821
          </div>
          {/* rows 数据源: LotteryPageData.threeIssueRows */}
          {/* 数据结构: Array<{ issue: "120-122期"（跨期）, label: "三期中特", content: 预测内容, result: 开奖结果 }> */}
          <SourceTable kind="three" rows={data.threeIssueRows} />
        </div>
      </div>

      {/* =============== 模块三：双波中特 =============== */}
      {/* id="sbztBox" 对应旧站 012sbzt.js 中 AJAX 渲染的目标容器 */}
      <div id="sbztBox">
        <div className="box pad" id="yxym">
          <div className="list-title">台湾六合彩论坛『双波中特』</div>
          {/* rows 数据源: LotteryPageData.doubleWaveRows */}
          {/* 数据结构: Array<{ issue: 期号, label: "双波中特", content: "红波+绿波" 等波色组合, result: 开奖结果 }> */}
          <SourceTable kind="wave" rows={data.doubleWaveRows} />
        </div>
      </div>
    </>
  )
}
