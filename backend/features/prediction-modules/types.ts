export type PredictionModulePeriodRange = {
  start: number
  end: number
}

export type PredictionModulesBulkDeleteEstimate = {
  moduleCount: number
  periodCount: number
  estimatedRows: number
  limitExceeded: boolean
}

export type PredictionModulesBulkDeleteRequest = {
  moduleIds: string[]
  periodRange: PredictionModulePeriodRange
}

export type PredictionModulesBulkDeleteResponse = {
  ok: boolean
  deleted: number
  estimated: number
  modules: Array<{
    moduleId: string
    tableName: string
    deleted: number
  }>
}

export type PredictionModulesGenerateJobResult = {
  total_modules: number
  draw_count: number
  inserted: number
  updated: number
  errors: number
}
