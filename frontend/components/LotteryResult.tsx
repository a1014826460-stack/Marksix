/**
 * 开奖结果展示组件 — LotteryResult.tsx
 * ---------------------------------------------------------------
 * 职责：展示六合彩开奖结果，使用 iframe 嵌入旧站开奖页面，
 *       与旧站 /vendor/shengshi8800/index.html 的 kj.js 行为完全一致。
 *
 * 旧站行为（kj.js）：
 *   1. 创建三个标签页：台湾彩、澳门彩、香港彩
 *   2. 每个标签页对应一个 DIV 容器，初始为空
 *   3. 点击标签页时，向对应 DIV 注入 iframe
 *   4. iframe URL 来自标签的 data-opt 属性
 *   5. 切换标签后，旧标签的 iframe 延迟 10 秒清除
 *
 * React 实现：
 *   1. 使用相同的 KJ-TabBox CSS 类名保持视觉一致
 *   2. 通过 activeGame 控制当前显示的 iframe
 *   3. 使用与旧站相同的 iframe URL 确保开奖结果完全一致
 *
 * 旧站 CSS 定义（已迁移至 globals.css）：
 *   .KJ-TabBox, .KJ-TabBox ul, .KJ-TabBox li, .KJ-IFRAME 等
 */

"use client"

import type { LotteryGame } from "@/lib/lotteryData"
import { games } from "@/lib/lotteryData"

/** 开奖结果组件 Props */
type LotteryResultProps = {
  activeGame: LotteryGame
  onGameChange: (game: LotteryGame) => void
}

/**
 * 旧站开奖 iframe URL 映射
 * ---------------------------------------------------------------
 * 与 kj.js 中 data-opt 属性的 URL 完全一致：
 *   台湾彩 → xgkj3.html
 *   澳门彩 → amkj2.html
 *   香港彩 → xgkj2.html
 */
const IFRAME_URLS: Record<LotteryGame, string> = {
  taiwan: "https://admin.shengshi8800.com/xgkj3.html",
  macau: "https://admin.shengshi8800.com/amkj2.html",
  hongkong: "https://admin.shengshi8800.com/xgkj2.html",
}

/** iframe 高度（与旧站 data-opt 中的 height 一致） */
const IFRAME_HEIGHT = 130

export function LotteryResult({ activeGame, onGameChange }: LotteryResultProps) {
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
        {/* 每个游戏标签对应一个面板，始终挂载所有 iframe，仅隐藏非活跃的 */}
        {/* 避免 iframe 卸载重挂载导致的外部页面 scrollTo 干扰 */}
        {games.map((game) => (
          <div
            key={game.key}
            className={activeGame === game.key ? "cur" : ""}
            style={{ display: activeGame === game.key ? "" : "none" }}
          >
            <iframe
              className="KJ-IFRAME"
              src={IFRAME_URLS[game.key]}
              width="100%"
              height={IFRAME_HEIGHT}
              style={{ border: "none", overflow: "hidden" }}
              title={`${game.label}开奖结果`}
            />
          </div>
        ))}
      </div>
      {/* 旧站底部广告横幅 */}
      <div className="waibox">
        <style>{`
          .waibox { text-align: center; background: linear-gradient(to top, #9C27B0, #673AB7); line-height: 55px; margin: 0; padding: 0; list-style-type: none; border: none; }
          .waibox a:link { text-decoration: none; }
          .waibox .location_to { padding: 10px; background: beige; border-radius: 15px; color: #f44336; font-weight: 700; letter-spacing: 1px; box-shadow: 2px 2px 1px #f44336; }
        `}</style>
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
