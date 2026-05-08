/**
 * 根布局 — layout.tsx
 * ---------------------------------------------------------------
 * 引入全局样式和旧站 CSS（保持与旧站视觉一致）。
 *
 * 新旧 CSS 的关系：
 *   1. globals.css          — 新架构的基础重置和补充样式
 *   2. vendor/style1.css    — 旧站核心样式（.box, .pad, .duilianpt1, .list-title 等）
 *   3. vendor/style3.css    — 旧站扩展样式（文章列表、导航等）
 *
 * 旧站 CSS 文件存放在 public/vendor/shengshi8800/static/css/ 下，
 * 通过 <link> 标签从 public 目录直接加载，确保所有旧 CSS 类名可用。
 */

import type { Metadata, Viewport } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "台湾六合彩论坛",
  description: "全网最准尽在台湾六合彩 — 提供最新开奖结果、预测号码、六合彩资料大全。",
  keywords: "六合彩, 台湾六合彩, 开奖结果, 预测号码, 六合彩论坛",
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  minimumScale: 1,
  userScalable: false,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        {/* ============ 旧站 CSS（保持与旧站 UI 完全一致） ============ */}
        {/* style1.css 包含 .box, .pad, .duilianpt1, .list-title, .zl, .riqi, .copyright 等核心样式 */}
        <link rel="stylesheet" href="/vendor/shengshi8800/static/css/style1.css" />
        {/* style3.css 包含文章列表、导航等扩展样式 */}
        <link rel="stylesheet" href="/vendor/shengshi8800/static/css/style3.css" />
      </head>
      <body>{children}</body>
    </html>
  )
}
