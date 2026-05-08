/**
 * 开奖结果展示组件 — LotteryResult.tsx
 * ---------------------------------------------------------------
 * 职责：从数据库 lottery_draws 表读取开奖数据，展示六合彩开奖号码球。
 *
 * 数据流：
 *   1. 用户切换游戏标签（台湾彩/澳门彩/香港彩）
 *   2. 组件自动请求 /api/latest-draw?lottery_type=X
 *   3. Next.js API 代理转发到 Python 后端 /api/public/latest-draw
 *   4. 后端从 lottery_draws 表查询，用 fixed_data 映射生肖/波色
 *   5. 返回开奖号码球数组，组件用 draw-ball CSS 类渲染
 */

"use client"

import type { LotteryGame } from "@/lib/lotteryData"
import { games } from "@/lib/lotteryData"

/** LotteryResult 组件的 Props */
type LotteryResultProps = {
  activeGame: LotteryGame
  onGameChange: (game: LotteryGame) => void
}

/**
 * 开奖结果展示组件
 * ---------------------------------------------------------------
 * 使用 iframe 嵌入旧站开奖页面，与旧 kj.js 行为完全一致。
 * 每个游戏标签对应一个外部开奖页面 URL：
 *   台湾彩 → https://admin.shengshi8800.com/xgkj3.html
 *   澳门彩 → https://admin.shengshi8800.com/amkj2.html
 *   香港彩 → https://admin.shengshi8800.com/xgkj2.html
 *
 * 包含：
 *   1. KJ-TabBox 游戏切换标签（台湾彩/澳门彩/香港彩）
 *   2. iframe 嵌入外部开奖结果页面
 *   3. waibox 广告横幅
 */
export function LotteryResult({ activeGame, onGameChange }: LotteryResultProps) {
  // iframe URL 配置（与旧站 kj.js 完全一致）
  const IFRAME_URLS: Record<LotteryGame, { url: string; height: number }> = {
    taiwan: { url: "https://admin.shengshi8800.com/xgkj3.html", height: 130 },
    macau: { url: "https://admin.shengshi8800.com/amkj2.html", height: 130 },
    hongkong: { url: "https://admin.shengshi8800.com/xgkj2.html", height: 130 },
  }

  return (
    <div className="box pad" id="yxym">
      <div className="KJ-TabBox">
        <ul>
          {games.map((game) => (
            <li
              className={activeGame === game.key ? "cur" : ""}
              key={game.key}
              onClick={() => onGameChange(game.key)}
            >
              {game.label}
            </li>
          ))}
        </ul>
        {games.map((game) => {
          const iframeCfg = IFRAME_URLS[game.key]
          const isActive = activeGame === game.key
          return (
            <div
              key={game.key}
              className={isActive ? "cur" : ""}
              style={{ display: isActive ? "" : "none" }}
            >
              {isActive && (
                <iframe
                  className="KJ-IFRAME"
                  src={iframeCfg.url}
                  width="100%"
                  height={iframeCfg.height}
                  style={{ border: 0, overflow: "hidden" }}
                  title={`${game.label}开奖结果`}
                />
              )}
            </div>
          )
        })}
      </div>
      {/* 旧站底部广告横幅 */}
      <div className="waibox">
        <a
          className="location_to"
          href="http://shengshi8800.com"
          target="_blank"
          rel="noopener noreferrer"
        >
          点击进入台湾彩报码直播开奖
        </a>
      </div>
    </div>
  )
}
