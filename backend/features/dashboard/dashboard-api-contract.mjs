import fs from "node:fs"

const source = fs.readFileSync("features/dashboard/DashboardPage.tsx", "utf8")

for (const path of [
  'adminApi<DashboardData>("/admin/dashboard")',
  'adminApi(`/admin/dashboard/scheduler-tasks/${task.id}/retry`',
]) {
  if (!source.includes(path)) throw new Error(`dashboard must use the protected admin API path: ${path}`)
}

for (const fallback of ["data?.today_draws || []", "data?.draw_health?.lotteries || []", "data?.scheduler?.recent_tasks || []"]) {
  if (!source.includes(fallback)) throw new Error(`dashboard must tolerate an older backend payload: ${fallback}`)
}

for (const required of [
  'adminApi<DashboardData>("/admin/dashboard")',
  "const trafficToday = data?.traffic?.today",
  "<CardTitle>前端访问流量</CardTitle>",
  "今日 PV",
  "今日 UV",
  "近 7 天站点访问排行",
  "流量趋势（PV / UV）",
  "Web ID",
  "域名",
  "web_id - b.web_id",
  "name: \"PV\"",
  "name: \"UV\"",
]) {
  if (!source.includes(required)) throw new Error(`dashboard must prioritize public-site traffic: ${required}`)
}

// ECharts passes gradient stops to Canvas, which cannot resolve CSS variables.
if (source.includes("hsl(var(--primary))") || source.includes("hsl(var(--accent))")) {
  throw new Error("dashboard chart colors must be browser-parsable literal colors")
}
