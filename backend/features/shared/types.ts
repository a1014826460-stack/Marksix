export type JsonPrimitive = string | number | boolean | null
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue }
export type AnyRecord = Record<string, JsonValue | undefined> & {
  id?: string | number
  data_source?: string
}

export type ApiSummary = {
  summary: Record<string, string | number>
}

export type User = {
  id: number
  username: string
  display_name: string
  role: string
  status: boolean
  last_login_at?: string
}

export type LotteryType = {
  id: number
  name: string
  draw_time: string
  collect_url: string
  next_time?: string
  status: boolean
}

export function formatNextTime(ts: string | undefined) {
  if (!ts) return ""
  try {
    let n = Number(ts)
    if (n <= 0) return ""
    if (n <= 9999999999) n = n * 1000
    return new Date(n).toLocaleString("zh-CN")
  } catch {
    /* ignore */
  }
  return ts
}

export type Draw = {
  id: number
  lottery_type_id: number
  lottery_name: string
  year: number
  term: number
  numbers: string
  draw_time: string
  next_time?: string
  status: boolean
  is_opened: boolean
  next_term: number
}

export type Site = {
  id: number
  web_id: number
  name: string
  domain: string
  lottery_type_id: number
  lottery_name?: string
  enabled: boolean
  blueprint_name?: string
  announcement?: string
  notes?: string
  created_at?: string
  updated_at?: string
}

export type ForcedAnnouncementScope = "all_sites" | "selected_sites"

export type ForcedAnnouncement = {
  id: number
  version: string
  title: string
  html: string
  scope: ForcedAnnouncementScope
  site_ids: number[]
  starts_at: string
  ends_at: string | null
  enabled: boolean
  created_at: string
  updated_at: string
}

export type NumberRow = {
  id: number
  name: string
  code: string
  category_key: string
  year: string
  status: boolean
  type: number
}

export type Mechanism = {
  key: string
  title: string
  mode_id?: number
  default_modes_id: number
  default_table: string
  configured?: boolean
  status?: number
}

export type SitePredictionModule = {
  id: number
  mechanism_key: string
  mode_id?: number
  title?: string
  tables_title?: string
  display_title?: string
  resolved_mode_id?: number
  default_modes_id?: number
  default_table?: string
  status: boolean
  sort_order: number
}

export function getSitePredictionModuleName(
  module: SitePredictionModule | null | undefined,
) {
  if (!module) return ""
  return (
    module.tables_title ||
    module.display_title ||
    module.title ||
    module.mechanism_key
  )
}

export type LogEntry = {
  id: number
  created_at: string
  level: string
  logger_name: string
  module: string
  func_name: string
  file_path: string
  line_number: number
  message: string
  exc_type?: string
  exc_message?: string
  stack_trace?: string
  user_id?: string
  site_id?: number
  web_id?: number
  lottery_type_id?: number
  year?: number
  term?: number
  task_key?: string
  task_type?: string
  request_path?: string
  request_method?: string
  duration_ms?: number
  request_params?: string
  extra_data?: string
}

export function formatLogTime(ts: string) {
  if (!ts) return ""
  try { return ts.replace("T", " ").slice(0, 19) } catch { return ts }
}

export function levelBadgeClass(level: string) {
  const map: Record<string, string> = {
    ERROR: "bg-red-100 text-red-800 border-red-300",
    WARNING: "bg-yellow-100 text-yellow-800 border-yellow-300",
    INFO: "bg-blue-100 text-blue-800 border-blue-300",
    DEBUG: "bg-gray-100 text-gray-600 border-gray-300",
    CRITICAL: "bg-purple-100 text-purple-800 border-purple-300",
  }
  return map[level] || "bg-gray-100 text-gray-600 border-gray-300"
}

export type ConfigEntry = {
  key: string
  value: JsonValue
  raw_value?: JsonValue
  default_value: JsonValue
  effective_value: JsonValue
  value_type: string
  group: string
  source: string
  description: string
  editable: boolean
  requires_restart: boolean
  sensitive: boolean
  updated_at: string
}

export type ConfigGroup = {
  key: string
  label: string
  prefix: string
  description: string
}

export type ConfigHistoryEntry = {
  id: number
  config_key: string
  old_value: string
  new_value: string
  changed_by: string
  changed_at: string
  change_reason: string
}

export function configSourceBadgeClass(source: string) {
  const map: Record<string, string> = {
    database: "bg-green-100 text-green-800",
    "config.yaml": "bg-blue-100 text-blue-800",
    environment: "bg-purple-100 text-purple-800",
    computed: "bg-gray-100 text-gray-600",
  }
  return map[source] || "bg-gray-100 text-gray-600"
}

export type BulkGenerateResult = {
  site_id: number
  site_name: string
  lottery_type: number
  start_issue: string
  end_issue: string
  web_id: number
  total_modules: number
  draw_count: number
  inserted: number
  updated: number
  errors: number
  modules: Array<{
    module_id: number
    mechanism_key: string
    mode_id: number
    table_name: string
    draw_count: number
    inserted: number
    updated: number
    errors: number
    error_message: string
  }>
}
