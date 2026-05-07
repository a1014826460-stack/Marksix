/**
 * 首页客户端交互组件 — HomePageClient.tsx
 * ---------------------------------------------------------------
 * 职责：接收服务端传来的 LotteryPageData，渲染完整的论坛页面。
 *
 * 状态管理：
 *   - activeGame   : 当前选中的游戏标签（台湾彩/澳门彩/香港彩）
 *   - currentTime  : 实时时钟（每秒更新）
 *
 * 子组件渲染顺序（与旧站 index.html 布局一致）：
 *   1. Header             — 日期、农历、时钟、头图
 *   2. NavTabs            — 导航链接（一肖一码、四肖八码等）
 *   3. PreResultBlocks    — 核心预测模块（两肖平特王、三期中特、双波中特）
 *   4. PredictionModules  — 其他所有预测模块（从 API 动态获取）
 *   5. LotteryResult      — 开奖结果（号码球展示）
 *   6. Footer             — 版权信息和返回顶部链接
 *
 * CSS 策略：
 *   所有组件使用旧站 CSS 类名（.box、.pad、.duilianpt1、.list-title 等），
 *   CSS 定义来自 public/vendor/shengshi8800/static/css/style1.css。
 *   缺失的类名在 globals.css 中补充定义。
 */

"use client"

import { useState, useEffect } from "react"
import type { LotteryGame, LotteryPageData } from "@/lib/lotteryData"
import { Header } from "@/components/Header"
import { NavTabs } from "@/components/NavTabs"
import { PreResultBlocks } from "@/components/PreResultBlocks"
import { PredictionModules } from "@/components/PredictionModules"
import { LotteryResult } from "@/components/LotteryResult"
import { Footer } from "@/components/Footer"

/** HomePageClient 的 Props */
type HomePageClientProps = {
  /** 由 page.tsx 从后端 API 转换而来的页面数据 */
  data: LotteryPageData
}

/**
 * 首页客户端组件
 * ---------------------------------------------------------------
 * 使用 "use client" 声明为客户端组件，支持 useState / useEffect
 * 等交互特性（时钟更新、游戏标签切换）。
 *
 * @param props.data - 包含站点、开奖、所有预测模块的完整页面数据
 */
export function HomePageClient({ data }: HomePageClientProps) {
  /* ========== 状态定义 ========== */

  // 当前选中的游戏标签（默认使用站点配置的游戏类型）
  const [activeGame, setActiveGame] = useState<LotteryGame>(data.game)

  // 实时时钟（使用 Date 对象每秒更新）
  const [currentTime, setCurrentTime] = useState<string>("")

  /* ========== 副作用：更新时钟 ========== */
  useEffect(() => {
    const updateClock = () => {
      const now = new Date()
      const hours = String(now.getHours()).padStart(2, "0")
      const minutes = String(now.getMinutes()).padStart(2, "0")
      const seconds = String(now.getSeconds()).padStart(2, "0")
      setCurrentTime(`${hours}:${minutes}:${seconds}`)
    }

    updateClock()             // 立即执行一次
    const timer = setInterval(updateClock, 1000)  // 每秒更新

    return () => clearInterval(timer)  // 组件卸载时清除定时器
  }, [])

  /* ========== 旧站导航链接配置 ========== */
  // 与旧站 index.html 的 #nav2 完全一致，保持锚点兼容
  const navRows = [
    // 第一行：品牌标题
    [
      { label: "台湾六合彩论坛", href: "#" },
    ],
    // 第二行：主要导航
    [
      { label: "一肖一码", href: "#7x1m" },
      { label: "四肖八码", href: "#4x8m" },
      { label: "高手资料", href: "#gsb" },
      { label: "精选图片", href: "#gsb3" },
      { label: "买啥开啥", href: "#msks" },
    ],
    // 第三行：更多预测
    [
      { label: "九肖一码", href: "#9x1m" },
      { label: "欲钱解特", href: "#yqjt" },
      { label: "六肖中特", href: "#6x" },
      { label: "三头中特", href: "#3t" },
      { label: "复式连肖", href: "#lx" },
    ],
  ]

  /* ========== 排除已由专用组件渲染的模块 ========== */
  // PreResultBlocks 渲染 flatKingRows / threeIssueRows / doubleWaveRows，
  // 这些数据来自 site-page API 的 pt2xiao / 3zxt / hllx 模块。
  // 目前 site_prediction_modules 表未配置这 3 个模块，所以 site-page API
  // 不返回它们。如果以后后端配置了，这里可以防止重复渲染。
  //
  // 注意：旧模块的 mechanism_key 以 legacy_ 开头（如 legacy_pt2xiao），
  // 当前 site-page API 不返回 pt2xiao/3zxt/hllx，因此也不需要排除 legacy_ 版本。
  // 如果 site-page API 开始返回这些模块，请同时排除 legacy_ 版本。
  const preResultKeys: string[] = []

  /* ========== 滚动监听：导航栏固定 ========== */
  const [navFixed, setNavFixed] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      const navEl = document.getElementById("nav2")
      if (navEl) {
        const offsetTop = navEl.offsetTop
        setNavFixed(window.scrollY >= offsetTop)
      }
    }

    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  /* ========== 渲染页面 ========== */
  return (
    /* 外层容器：使用与旧站 body 相同的样式约束 */
    <div style={{ maxWidth: 720, margin: "0 auto" }}>
      {/* ===== 顶部：日期 + 头图 ===== */}
      <Header currentTime={currentTime} />

      {/* ===== 导航栏 ===== */}
      <NavTabs fixed={navFixed} rows={navRows} />

      {/* ===== 预测模块区域 ===== */}

      {/* 核心模块（由 PreResultBlocks 专用渲染）：
          仅当对应的数组有数据时才渲染 */}
      {data.flatKingRows.length > 0 ||
      data.threeIssueRows.length > 0 ||
      data.doubleWaveRows.length > 0 ? (
        <PreResultBlocks data={data} />
      ) : null}

      {/* ===== 开奖结果（使用 iframe 嵌入旧站开奖页面） ===== */}
      <LotteryResult
        activeGame={activeGame}
        onGameChange={setActiveGame}
      />

      {/* 通用模块渲染器：渲染所有其他预测模块 */}
      {/* 根据当前选中的游戏类型，渲染对应彩种的预测数据 */}
      <PredictionModules
        modules={data.modulesByGame[activeGame] || data.rawModules}
        excludeKeys={preResultKeys}
      />

      {/* ===== 底部信息 ===== */}
      <Footer />
    </div>
  )
}
