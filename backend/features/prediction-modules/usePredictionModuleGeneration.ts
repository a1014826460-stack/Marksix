"use client"

import { useEffect, useMemo, useState } from "react"
import { adminApi } from "@/lib/admin-api"
import type {
  LotteryType,
  Site,
  SitePredictionModule,
} from "@/features/shared/types"
import type { PredictionModulesGenerateJobResult } from "@/features/prediction-modules/types"

type SiteModulesResponse = {
  site: Site
  modules: SitePredictionModule[]
}

export function usePredictionModuleGeneration() {
  const [sites, setSites] = useState<Site[]>([])
  const [lotteryTypes, setLotteryTypes] = useState<LotteryType[]>([])
  const [selectedSiteId, setSelectedSiteId] = useState("")
  const [siteModules, setSiteModules] = useState<SitePredictionModule[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [siteData, lotteryData] = await Promise.all([
          adminApi<{ sites: Site[] }>("/admin/sites"),
          adminApi<{ lottery_types: LotteryType[] }>("/admin/lottery-types"),
        ])
        setSites(siteData.sites.filter((item) => item.enabled))
        setLotteryTypes(lotteryData.lottery_types.filter((item) => item.status))
        setSelectedSiteId((prev) => prev || String(siteData.sites.find((item) => item.enabled)?.id || ""))
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  useEffect(() => {
    async function loadSiteModules() {
      if (!selectedSiteId) {
        setSiteModules([])
        return
      }
      const data = await adminApi<SiteModulesResponse>(
        `/admin/sites/${selectedSiteId}/prediction-modules`,
      )
      setSiteModules(data.modules.filter((item) => item.status))
    }

    loadSiteModules()
  }, [selectedSiteId])

  const selectedSite = useMemo(
    () => sites.find((item) => String(item.id) === selectedSiteId) || null,
    [selectedSiteId, sites],
  )

  const availableLotteryTypes = useMemo(() => {
    return lotteryTypes.length > 0
      ? lotteryTypes
      : [
          { id: 1, name: "香港", draw_time: "", collect_url: "", status: true },
          { id: 2, name: "澳门", draw_time: "", collect_url: "", status: true },
          { id: 3, name: "台湾", draw_time: "", collect_url: "", status: true },
        ]
  }, [lotteryTypes])

  async function submitGenerate(params: {
    siteId: number
    lotteryType: string
    startIssue: string
    endIssue: string
    mechanismKeys: string[]
    futureOnly: boolean
  }) {
    const { job_id } = await adminApi<{
      ok: boolean
      job_id: string
    }>(`/admin/sites/${params.siteId}/prediction-modules/generate-all`, {
      method: "POST",
      body: JSON.stringify({
        lottery_type: params.lotteryType,
        start_issue: params.startIssue,
        end_issue: params.endIssue,
        mechanism_keys: params.mechanismKeys,
        future_periods: 1,
        future_only: params.futureOnly,
      }),
    })

    for (let index = 0; index < 120; index += 1) {
      await new Promise((resolve) => setTimeout(resolve, 3000))
      try {
        const job = await adminApi<{
          status: string
          result?: PredictionModulesGenerateJobResult
          error?: string
        }>(`/admin/jobs/${job_id}`)
        if (job.status === "done" && job.result) {
          return job.result
        }
        if (job.status === "error") {
          throw new Error(job.error || "未知错误")
        }
      } catch (error) {
        if (index === 119) throw error
      }
    }

    throw new Error("批量生成超时，请稍后刷新页面查看结果")
  }

  return {
    sites,
    lotteryTypes: availableLotteryTypes,
    selectedSiteId,
    selectedSite,
    siteModules,
    loading,
    setSelectedSiteId,
    submitGenerate,
  }
}
