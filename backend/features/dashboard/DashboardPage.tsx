"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import ReactEChartsCore from "echarts-for-react/lib/core"
import * as echarts from "echarts/core"
import { BarChart, LineChart } from "echarts/charts"
import { DatasetComponent, GridComponent, LegendComponent, TooltipComponent, VisualMapComponent } from "echarts/components"
import { CanvasRenderer } from "echarts/renderers"
import type { EChartsOption } from "echarts"
import { Activity, Database, RefreshCw, Server, ShieldAlert, ShieldCheck, ShieldX, Users, RotateCw } from "lucide-react"
import { AdminShell } from "@/components/admin/admin-shell"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useTheme } from "@/components/theme-provider"
import { adminApi } from "@/lib/admin-api"

echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, VisualMapComponent, DatasetComponent, CanvasRenderer])

// ECharts draws on Canvas, where CSS variables are not resolved as colors.
const chartColors = {
  primary: "#16a34a",
  accent: "#0f766e",
  primaryDark: "#4ade80",
  accentDark: "#2dd4bf",
}

type DashboardData = {
  summary: Record<string, number | string>
  traffic: {
    today: { pv: number; uv: number; api_compat_hits: number }
    last_7_days: {
      summary: { pv: number; uv: number; api_compat_hits: number }
      sites: Array<{
        site_key: string
        web_id: number
        name: string
        domain: string
        pv: number
        uv: number
        api_compat_hits: number
      }>
      timeseries: Array<{ date: string; site_key: string; pv: number; uv: number; api_compat_hits: number }>
    }
  }
  today_draws: Array<{ lottery_type_id: number; lottery_name: string; year: number; term: number; draw_time: string; is_opened: boolean; numbers: string }>
  sites: Array<{
    site_id: number
    web_id: number
    name: string
    domain: string
    blueprint_name: string
    enabled: boolean
    lottery_name: string
    modes_count: number
    records_count: number
    prediction_modules: number
    enabled_prediction_modules: number
    latest_fetched_at: string
    latest_draw_time: string
    latest_draw_term: number
    next_time: string
  }>
  trend: {
    draw_audit_7d: Array<{ date: string; count: number }>
    error_logs_7d: Array<{ date: string; count: number }>
  }
  security: {
    current_failed_fingerprints: number
    today_success_login: number
    today_failed_login: number
    auth_error_count: number
    recent_events: Array<{ created_at: string; level: string; logger_name: string; module: string; message: string; site_id: number; web_id: number; lottery_type_id: number; request_path: string }>
  }
  fetch: {
    recent_runs: Array<{ site_id: number; status: string; message: string; modes_count: number; records_count: number; started_at: string; finished_at: string }>
  }
  draw_audit: {
    recent_events: Array<{ lottery_type_id: number; lottery_name: string; event: string; status: string; detail: string; duration_ms: number; created_at: string; operator: string }>
  }
  scheduler: {
    status_breakdown: Array<{ status: string; count: number }>
    recent_tasks: Array<{ id: number; task_key: string; task_type: string; status: string; run_at: string; attempt_count: number; max_attempts: number; last_error: string; lottery_type_id: number; site_id: number }>
  }
  worker: { status: string; active: boolean; holder_id: string }
  draw_health: { status: string; stale_lottery_type_ids: number[]; lotteries: Array<{ lottery_type_id: number; lottery_name: string; current_issue: string; next_time: string; stale: boolean }> }
  alerts: Array<{ severity: "low" | "medium" | "high"; name: string; source: string; status: string }>
  meta: {
    generated_at: string
    admin_user: { username: string; display_name: string; last_login_at: string }
    alert_recipients_configured: boolean
  }
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("zh-CN").format(value)
}

function AnimatedNumber({ value }: { value: number }) {
  const [display, setDisplay] = useState(0)
  const currentRef = useRef(0)

  useEffect(() => {
    const start = performance.now()
    const from = currentRef.current
    let raf = 0
    const step = (now: number) => {
      const progress = Math.min((now - start) / 300, 1)
      const next = Math.round(from + (value - from) * progress)
      currentRef.current = next
      setDisplay(next)
      if (progress < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [value])

  return <span className="tabular-nums">{formatNumber(display)}</span>
}

export function DashboardPage() {
  const { theme } = useTheme()
  const [data, setData] = useState<DashboardData | null>(null)
  const [message, setMessage] = useState("")
  const [retryingTaskKey, setRetryingTaskKey] = useState("")

  async function load() {
    try {
      const payload = await adminApi<DashboardData>("/admin/dashboard")
      setData(payload)
      setMessage("")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "加载失败")
    }
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 30000)
    return () => clearInterval(timer)
  }, [])

  const todayDraws = data?.today_draws || []
  const drawHealthLotteries = data?.draw_health?.lotteries || []
  const schedulerTasks = data?.scheduler?.recent_tasks || []
  const trafficToday = data?.traffic?.today || { pv: 0, uv: 0, api_compat_hits: 0 }
  const trafficLast7Days = data?.traffic?.last_7_days || { summary: { pv: 0, uv: 0, api_compat_hits: 0 }, sites: [], timeseries: [] }
  const chartPalette = theme === "dark"
    ? { primary: chartColors.primaryDark, accent: chartColors.accentDark }
    : chartColors

  async function retryFailedTask(taskKey: string) {
    const task = schedulerTasks.find((item) => item.task_key === taskKey)
    if (!task || task.status !== "failed") return
    setRetryingTaskKey(taskKey)
    try {
      await adminApi(`/admin/dashboard/scheduler-tasks/${task.id}/retry`, { method: "POST" })
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "任务重试失败")
    } finally {
      setRetryingTaskKey("")
    }
  }

  const trafficTrendOption = useMemo<EChartsOption>(() => {
    const dailyTraffic = new Map<string, { pv: number; uv: number }>()
    for (const item of trafficLast7Days.timeseries) {
      const aggregate = dailyTraffic.get(item.date) || { pv: 0, uv: 0 }
      aggregate.pv += item.pv
      aggregate.uv += item.uv
      dailyTraffic.set(item.date, aggregate)
    }
    const dates = Array.from(dailyTraffic.keys()).sort()
    return {
      animationDuration: 300,
      tooltip: { trigger: "axis" },
      grid: { left: 36, right: 18, top: 24, bottom: 24 },
      legend: { data: ["PV", "UV"] },
      xAxis: { type: "category", data: dates.map((date) => date.slice(5)) },
      yAxis: { type: "value" },
      series: [
        {
          name: "PV",
          type: "line",
          smooth: true,
          data: dates.map((date) => dailyTraffic.get(date)?.pv || 0),
          lineStyle: { width: 3, color: chartPalette.primary },
          itemStyle: { color: chartPalette.primary },
        },
        {
          name: "UV",
          type: "line",
          smooth: true,
          data: dates.map((date) => dailyTraffic.get(date)?.uv || 0),
          lineStyle: { width: 3, color: chartPalette.accent },
          itemStyle: { color: chartPalette.accent },
        },
      ],
    }
  }, [chartPalette, trafficLast7Days.timeseries])

  const siteTrafficOption = useMemo<EChartsOption>(() => {
    const sites = [...trafficLast7Days.sites].sort((a, b) => a.web_id - b.web_id)
    return {
      animationDuration: 300,
      tooltip: { trigger: "axis" },
      grid: { left: 36, right: 18, top: 24, bottom: 58 },
      legend: { data: ["PV", "UV"] },
      xAxis: {
        type: "category",
        data: sites.map((site) => `${site.web_id} · ${site.name}`),
        axisLabel: { interval: 0, rotate: 24 },
      },
      yAxis: { type: "value" },
      series: [
        {
          name: "PV",
          type: "bar",
          data: sites.map((site) => site.pv),
          itemStyle: { borderRadius: [6, 6, 0, 0], color: chartPalette.primary },
        },
        {
          name: "UV",
          type: "bar",
          data: sites.map((site) => site.uv),
          itemStyle: { borderRadius: [6, 6, 0, 0], color: chartPalette.accent },
        },
      ],
    }
  }, [chartPalette, trafficLast7Days.sites])

  const errorTrendOption = useMemo<EChartsOption>(() => ({
    animationDuration: 300,
    tooltip: { trigger: "axis" },
    grid: { left: 36, right: 18, top: 24, bottom: 24 },
    xAxis: {
      type: "category",
      data: data?.trend.error_logs_7d.map((item) => item.date.slice(5)) || [],
    },
    yAxis: { type: "value" },
    series: [
      {
        type: "line",
        smooth: true,
        showSymbol: false,
        data: data?.trend.error_logs_7d.map((item) => item.count) || [],
        lineStyle: { width: 3, color: chartPalette.primary },
        areaStyle: { color: "rgba(0,0,0,0.06)" },
      },
    ],
  }), [chartPalette, data])

  const summaryCards = [
    { label: "今日 PV", value: Number(trafficToday.pv || 0), icon: Activity },
    { label: "今日 UV", value: Number(trafficToday.uv || 0), icon: Users },
    { label: "启用站点", value: Number(data?.summary.enabled_sites || 0), icon: Server },
    { label: "异常登录指纹", value: Number(data?.security.current_failed_fingerprints || 0), icon: ShieldAlert },
    { label: "错误日志(7天)", value: Number(data?.summary.error_logs_7d || 0), icon: ShieldX },
    { label: "调度待处理", value: Number(data?.summary.scheduler_pending || 0), icon: Users },
  ]

  return (
    <AdminShell
      title="后台总览"
      description="彩票站点群真实运行概览，数据直接来自 PostgreSQL"
      actions={
        <Button variant="outline" size="sm" onClick={load}>
          <RefreshCw className="mr-1 h-4 w-4" />
          刷新
        </Button>
      }
    >
      {message ? (
        <div className="mb-3 rounded-md border border-destructive/20 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {message}
        </div>
      ) : null}

        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {summaryCards.map((item) => (
            <Card key={item.label}>
              <CardContent className="flex items-center justify-between p-4">
                <div>
                  <div className="text-xs text-muted-foreground">{item.label}</div>
                  <div className="mt-2 text-2xl font-semibold">
                    <AnimatedNumber value={item.value} />
                  </div>
                </div>
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <item.icon className="h-5 w-5" />
                </div>
              </CardContent>
            </Card>
          ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>前端访问流量</CardTitle>
              <CardDescription>五个彩票前端站点的第一方访问统计；PV 为页面访问次数，UV 为去重访客数。</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-3">
              <div className="rounded-lg border bg-background p-4">
                <div className="text-xs text-muted-foreground">今日 PV</div>
                <div className="mt-2 text-2xl font-semibold"><AnimatedNumber value={Number(trafficToday.pv || 0)} /></div>
              </div>
              <div className="rounded-lg border bg-background p-4">
                <div className="text-xs text-muted-foreground">今日 UV</div>
                <div className="mt-2 text-2xl font-semibold"><AnimatedNumber value={Number(trafficToday.uv || 0)} /></div>
              </div>
              <div className="rounded-lg border bg-background p-4">
                <div className="text-xs text-muted-foreground">近 7 天 PV / UV</div>
                <div className="mt-2 text-2xl font-semibold tabular-nums">{formatNumber(trafficLast7Days.summary.pv)} / {formatNumber(trafficLast7Days.summary.uv)}</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>近 7 天站点访问排行</CardTitle>
              <CardDescription>按 Web ID 从小到大排列；仅统计已部署追踪器的访问。</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Web ID</TableHead>
                    <TableHead>站点名</TableHead>
                    <TableHead>域名</TableHead>
                    <TableHead>PV</TableHead>
                    <TableHead>UV</TableHead>
                    <TableHead>兼容接口请求</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {trafficLast7Days.sites.length ? [...trafficLast7Days.sites].sort((a, b) => a.web_id - b.web_id).map((site) => (
                    <TableRow key={site.site_key}>
                      <TableCell className="font-medium">{site.web_id || "-"}</TableCell>
                      <TableCell>{site.name || site.site_key}</TableCell>
                      <TableCell>{site.domain || "-"}</TableCell>
                      <TableCell>{formatNumber(site.pv)}</TableCell>
                      <TableCell>{formatNumber(site.uv)}</TableCell>
                      <TableCell>{formatNumber(site.api_compat_hits)}</TableCell>
                    </TableRow>
                  )) : (
                    <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground">暂无访问数据；用户访问站点后将自动记录。</TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="grid w-full grid-cols-2 md:grid-cols-5">
            <TabsTrigger value="overview">站点概览</TabsTrigger>
            <TabsTrigger value="security">安全情况</TabsTrigger>
            <TabsTrigger value="draw">开奖运行</TabsTrigger>
            <TabsTrigger value="ops">调度与异常</TabsTrigger>
            <TabsTrigger value="logs">安全事件</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid gap-4 xl:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>流量趋势（PV / UV）</CardTitle>
                  <CardDescription>近 7 天全部前端站点的页面访问量与去重访客数。</CardDescription>
                </CardHeader>
                <CardContent>
                  <ReactEChartsCore
                    echarts={echarts}
                    option={trafficTrendOption}
                    style={{ height: 320 }}
                    notMerge
                    lazyUpdate
                    theme={theme === "dark" ? "dark" : undefined}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>站点流量对比</CardTitle>
                  <CardDescription>按 Web ID 展示近 7 天各站点的 PV 与 UV。</CardDescription>
                </CardHeader>
                <CardContent>
                  <ReactEChartsCore
                    echarts={echarts}
                    option={siteTrafficOption}
                    style={{ height: 320 }}
                    notMerge
                    lazyUpdate
                    theme={theme === "dark" ? "dark" : undefined}
                  />
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>站点配置</CardTitle>
                <CardDescription>展示受管理站点的基础配置和预测模块状态。</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  {(data?.sites || []).map((item) => (
                    <div key={item.site_id} className="rounded-lg border bg-background p-4">
                      <div className="flex items-center justify-between">
                        <div className="font-medium">{item.name}</div>
                        <Badge variant={item.enabled ? "default" : "secondary"}>
                          {item.enabled ? "启用" : "停用"}
                        </Badge>
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <div className="text-muted-foreground">Web ID</div>
                          <div className="font-semibold">{item.web_id || "-"}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">域名</div>
                          <div className="truncate font-semibold" title={item.domain}>{item.domain || "-"}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">预测模块</div>
                          <div className="font-semibold">{formatNumber(item.prediction_modules)}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">最新开奖期号</div>
                          <div className="font-semibold">{item.latest_draw_term || "-"}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="security" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              {[
                { label: "今日成功登录", value: Number(data?.security.today_success_login || 0), icon: ShieldCheck },
                { label: "今日失败登录", value: Number(data?.security.today_failed_login || 0), icon: ShieldX },
                { label: "被锁定指纹", value: Number(data?.security.current_failed_fingerprints || 0), icon: ShieldAlert },
              ].map((item) => (
                <Card key={item.label}>
                  <CardContent className="flex items-center justify-between p-4">
                    <div>
                      <div className="text-xs text-muted-foreground">{item.label}</div>
                      <div className="mt-2 text-2xl font-semibold">
                        <AnimatedNumber value={item.value} />
                      </div>
                    </div>
                    <item.icon className="h-5 w-5 text-primary" />
                  </CardContent>
                </Card>
              ))}
            </div>

            <Card>
              <CardHeader>
                <CardTitle>近7天错误趋势</CardTitle>
                <CardDescription>来自 `error_logs` 的真实错误曲线</CardDescription>
              </CardHeader>
              <CardContent>
                <ReactEChartsCore
                  echarts={echarts}
                  option={errorTrendOption}
                  style={{ height: 300 }}
                  notMerge
                  lazyUpdate
                  theme={theme === "dark" ? "dark" : undefined}
                />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="draw" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>今日开奖状态</CardTitle>
                <CardDescription>按北京时间汇总今日各彩种记录</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {todayDraws.length ? todayDraws.map((row) => (
                  <div key={`${row.lottery_type_id}-${row.term}`} className="rounded-lg border p-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{row.lottery_name}</span>
                      <Badge variant={row.is_opened ? "default" : "secondary"}>{row.is_opened ? "已开奖" : "待开奖"}</Badge>
                    </div>
                    <div className="mt-2 text-sm">{row.year} 年第 {row.term} 期</div>
                    <div className="mt-1 text-xs text-muted-foreground">{row.draw_time}</div>
                    {row.is_opened ? <div className="mt-2 text-sm tabular-nums">{row.numbers}</div> : null}
                  </div>
                )) : <div className="text-sm text-muted-foreground">今日暂无开奖记录。</div>}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>最近开奖审计</CardTitle>
                <CardDescription>真实反映开奖、补开、同步等状态</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>彩种</TableHead>
                      <TableHead>事件</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>耗时</TableHead>
                      <TableHead>时间</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data?.draw_audit.recent_events.map((row) => (
                      <TableRow key={`${row.created_at}-${row.event}`}>
                        <TableCell>{row.lottery_name || row.lottery_type_id}</TableCell>
                        <TableCell>{row.event}</TableCell>
                        <TableCell>{row.status}</TableCell>
                        <TableCell>{row.duration_ms} ms</TableCell>
                        <TableCell className="text-muted-foreground">{row.created_at}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="ops" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Worker 健康</CardTitle>
                  <CardDescription>由单实例租约实时判断</CardDescription>
                </CardHeader>
                <CardContent className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-lg font-semibold">{data?.worker.active ? "运行正常" : "需要处理"}</div>
                    <div className="mt-1 text-xs text-muted-foreground">租约状态：{data?.worker.status || "-"}</div>
                    {data?.worker.holder_id ? <div className="mt-1 text-xs text-muted-foreground">{data.worker.holder_id}</div> : null}
                  </div>
                  <Badge variant={data?.worker.active ? "default" : "destructive"}>{data?.worker.active ? "Healthy" : "Offline"}</Badge>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>逾期未开奖</CardTitle>
                  <CardDescription>下一开奖时间已过且无新已开奖数据</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {drawHealthLotteries.filter((item) => item.stale).length ? drawHealthLotteries.filter((item) => item.stale).map((item) => (
                    <div key={item.lottery_type_id} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                      <span>{item.lottery_name} · {item.current_issue || "无期号"}</span>
                      <Badge variant="destructive">逾期</Badge>
                    </div>
                  )) : <div className="text-sm text-muted-foreground">暂无逾期未开奖彩种。</div>}
                </CardContent>
              </Card>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>调度任务状态</CardTitle>
                  <CardDescription>`scheduler_tasks` 实时统计</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {data?.scheduler.status_breakdown.map((item) => (
                    <div key={item.status} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                      <span>{item.status}</span>
                      <span>{item.count}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>当前告警</CardTitle>
                  <CardDescription>从调度、采集与日志推导的未解除项</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {data?.alerts.map((item) => (
                    <div key={item.name} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                      <div>
                        <div className="font-medium">{item.name}</div>
                        <div className="text-xs text-muted-foreground">{item.source}</div>
                      </div>
                      <Badge variant={item.severity === "high" ? "destructive" : item.severity === "medium" ? "secondary" : "outline"}>
                        {item.status}
                      </Badge>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
            <Card>
              <CardHeader>
                <CardTitle>失败任务快捷处置</CardTitle>
                <CardDescription>仅将失败任务重新排入队列；实际执行仍由唯一 worker 完成。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {schedulerTasks.filter((item) => item.status === "failed").length ? schedulerTasks.filter((item) => item.status === "failed").map((item) => (
                  <div key={item.task_key} className="flex flex-col gap-2 rounded-md border p-3 md:flex-row md:items-center md:justify-between">
                    <div className="min-w-0">
                      <div className="font-medium">{item.task_type}</div>
                      <div className="text-xs text-muted-foreground break-all">{item.last_error || item.task_key}</div>
                    </div>
                    <Button size="sm" onClick={() => retryFailedTask(item.task_key)} disabled={retryingTaskKey === item.task_key}>
                      <RotateCw className="mr-1 h-4 w-4" />
                      {retryingTaskKey === item.task_key ? "处理中" : "重新排队"}
                    </Button>
                  </div>
                )) : <div className="text-sm text-muted-foreground">暂无失败任务。</div>}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="logs" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>最近安全事件</CardTitle>
                <CardDescription>来自真实错误日志与登录异常</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[420px] pr-3">
                  <div className="space-y-3">
                    {data?.security.recent_events.map((row) => (
                      <div key={`${row.created_at}-${row.message.slice(0, 18)}`} className="rounded-lg border bg-background px-4 py-3">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <Badge variant={row.level === "ERROR" ? "destructive" : row.level === "WARNING" ? "secondary" : "outline"}>
                              {row.level}
                            </Badge>
                            <span className="font-medium">{row.logger_name}</span>
                          </div>
                          <span className="text-xs text-muted-foreground">{row.created_at}</span>
                        </div>
                        <div className="mt-2 text-sm text-muted-foreground">{row.message}</div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
          <Card>
            <CardHeader>
              <CardTitle>采集运行</CardTitle>
              <CardDescription>`site_fetch_runs` 最近记录</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>站点</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>模式</TableHead>
                    <TableHead>记录</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data?.fetch.recent_runs.map((row, index) => (
                    <TableRow key={`${row.started_at}-${index}`}>
                      <TableCell>{row.site_id}</TableCell>
                      <TableCell>{row.status}</TableCell>
                      <TableCell>{row.modes_count}</TableCell>
                      <TableCell>{row.records_count}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>系统概览</CardTitle>
              <CardDescription>管理员、会话与告警配置状态</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex items-center justify-between rounded-md border px-3 py-2">
                <span>管理员</span>
                <span>{data?.meta.admin_user.display_name || data?.meta.admin_user.username || "-"}</span>
              </div>
              <div className="flex items-center justify-between rounded-md border px-3 py-2">
                <span>活跃会话</span>
                <span>{formatNumber(Number(data?.summary.active_sessions || 0))}</span>
              </div>
              <div className="flex items-center justify-between rounded-md border px-3 py-2">
                <span>告警收件人已配置</span>
                <span>{data?.meta.alert_recipients_configured ? "是" : "否"}</span>
              </div>
              <div className="flex items-center justify-between rounded-md border px-3 py-2">
                <span>最后同步</span>
                <span>{String(data?.summary.latest_sync_at || "-")}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </AdminShell>
  )
}
