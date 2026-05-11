// 侧边栏-菜单配置

import {
  BarChart3,
  Globe2,
  Hash,
  LayoutDashboard,
  Ticket,
  Trophy,
  Users,
  type LucideIcon,
} from "lucide-react"

export type MenuItem = {
  icon: LucideIcon
  label: string
  href: string
  /** 预留权限字段，后续可根据 user.role 过滤菜单 */
  permission?: string
}

export const menuItems: MenuItem[] = [
  { icon: LayoutDashboard, label: "控制台", href: "/" },
  { icon: Users, label: "管理员用户", href: "/users", permission: "admin" },
  { icon: Trophy, label: "彩种管理", href: "/lottery-types" },
  { icon: Ticket, label: "开奖管理", href: "/draws" },
  { icon: Globe2, label: "站点管理", href: "/sites" },
  { icon: Hash, label: "静态数据管理", href: "/numbers" },
  { icon: BarChart3, label: "预测模块", href: "/prediction-modules" },
]
