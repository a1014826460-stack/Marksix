"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import ReactEChartsCore from "echarts-for-react/lib/core"
import * as echarts from "echarts/core"
import { BarChart, LineChart, PieChart } from "echarts/charts"
import { DatasetComponent, GridComponent, LegendComponent, TooltipComponent, VisualMapComponent } from "echarts/components"
import { CanvasRenderer } from "echarts/renderers"
import type { EChartsOption } from "echarts"
import { Activity, Database, RefreshCw, Server, ShieldAlert, ShieldCheck, ShieldX, Users } from "lucide-react"
import { AdminShell } from "@/components/admin/admin-shell"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useTheme } from "@/components/theme-provider"
import { adminApi } from "@/lib/admin-api"

echarts.use([BarChart, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent, VisualMapComponent, DatasetComponent, CanvasRenderer])

type DashboardData = {
  summary: Record<string, number | string>
  sites: Array<{
    site_id: number
    web_id: number
    name: string
    domain: string
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
  site_share: Array<{ site_id: number; name: string; value: number; share: number }>
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
  }
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
  const [siteId, setSiteId] = useState<number | "all">("all")
  const [data, setData] = useState<DashboardData | null>(null)
  const [message, setMessage] = useState("")

  async function load() {
    try {
      const payload = await adminApi<DashboardData>("/dashboard")
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

  const selectedSite = useMemo(
    () => (siteId === "all" ? null : data?.sites.find((item) => item.site_id === siteId) || null),
    [data, siteId],
  )

  const siteScaleOption = useMemo<EChartsOption>(() => {
    const filtered = (data?.sites || []).filter((item) => siteId === "all" || item.site_id === siteId)
    return {
      animationDuration: 300,
      tooltip: { trigger: "axis" },
      grid: { left: 36, right: 18, top: 24, bottom: 24 },
      xAxis: { type: "category", data: filtered.map((item) => item.name), axisLabel: { interval: 0 } },
      yAxis: { type: "value" },
      series: [
        {
          name: "采集记录",
          type: "bar",
          data: filtered.map((item) => item.records_count),
          itemStyle: {
            borderRadius: [8, 8, 0, 0],
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "hsl(var(--primary))" },
                { offset: 1, color: "hsl(var(--accent))" },
              ],
            },
          },
        },
      ],
    }
  }, [data, siteId])

  const shareOption = useMemo<EChartsOption>(() => ({
    animationDuration: 300,
    tooltip: { trigger: "item" },
    legend: { bottom: 0 },
    series: [
      {
        type: "pie",
        radius: ["54%", "76%"],
        data: (data?.site_share || []).map((item, index) => ({
          name: item.name,
          value: item.value,
          itemStyle: {
            color: index % 2 === 0 ? "hsl(var(--primary))" : "hsl(var(--accent))",
          },
        })),
      },
    ],
  }), [data])

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
        lineStyle: { width: 3, color: "hsl(var(--primary))" },
        areaStyle: { color: "rgba(0,0,0,0.06)" },
      },
    ],
  }), [data])

  const summaryCards = [
    { label: "启用站点", value: Number(data?.summary.enabled_sites || 0), icon: Server },
    { label: "总模式数", value: Number(data?.summary.total_modes || 0), icon: Database },
    { label: "总采集记录", value: Number(data?.summary.total_records || 0), icon: Activity },
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

        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="grid w-full grid-cols-2 md:grid-cols-5">
            <TabsTrigger value="overview">站点概览</TabsTrigger>
            <TabsTrigger value="security">安全情况</TabsTrigger>
            <TabsTrigger value="draw">开奖运行</TabsTrigger>
            <TabsTrigger value="ops">调度与异常</TabsTrigger>
            <TabsTrigger value="logs">安全事件</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <CardTitle>站点采集规模</CardTitle>
                      <CardDescription>按站点对比采集记录规模</CardDescription>
                    </div>
                    <Select value={String(siteId)} onValueChange={(value) => setSiteId(value === "all" ? "all" : Number(value))}>
                      <SelectTrigger className="w-[160px]">
                        <SelectValue placeholder="全部站点" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">全部站点</SelectItem>
                        {data?.sites.map((item) => (
                          <SelectItem key={item.site_id} value={String(item.site_id)}>
                            {item.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </CardHeader>
                <CardContent>
                  <ReactEChartsCore
                    echarts={echarts}
                    option={siteScaleOption}
                    style={{ height: 320 }}
                    notMerge
                    lazyUpdate
                    theme={theme === "dark" ? "dark" : undefined}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>站点占比</CardTitle>
                  <CardDescription>按采集记录占比</CardDescription>
                </CardHeader>
                <CardContent>
                  <ReactEChartsCore
                    echarts={echarts}
                    option={shareOption}
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
                <CardTitle>站点详情</CardTitle>
                <CardDescription>{selectedSite ? `当前查看：${selectedSite.name}` : "全部站点"}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  {(selectedSite ? [selectedSite] : data?.sites || []).map((item) => (
                    <div key={item.site_id} className="rounded-lg border bg-background p-4">
                      <div className="flex items-center justify-between">
                        <div className="font-medium">{item.name}</div>
                        <Badge variant={item.enabled ? "default" : "secondary"}>
                          {item.enabled ? "启用" : "停用"}
                        </Badge>
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <div className="text-muted-foreground">采集记录</div>
                          <div className="font-semibold">{formatNumber(item.records_count)}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">模式数</div>
                          <div className="font-semibold">{formatNumber(item.modes_count)}</div>
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
