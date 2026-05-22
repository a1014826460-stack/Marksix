export type VendorResult = {
  res_code: string
  res_sx: string
  res_color: string
  result_text: string
  is_opened: boolean
}

export type VendorHomepageModule =
  | {
      module_key: "wuxiao_wuma"
      title: string
      display_style: string
      history: Array<{
        issue: string
        year: string
        term: string
        groups: {
          xiao_5: string[]
          xiao_4: string[]
          xiao_3: string[]
          xiao_2: string[]
          code_5: string[]
          code_4: string[]
          code_3: string[]
          code_2: string[]
        }
        result: VendorResult
        is_opened: boolean
        is_correct: boolean | null
        raw: Record<string, unknown>
      }>
    }
  | {
      module_key: "public_yixiao_yima"
      title: string
      display_style: string
      history: Array<{
        issue: string
        year: string
        term: string
        xiao_groups: {
          xiao_9: string[]
          xiao_7: string[]
          xiao_5: string[]
          xiao_3: string[]
        }
        code_groups: {
          code_14: string[]
          code_8: string[]
          code_5: string[]
        }
        best_pick: {
          xiao: string
          code: string
          text: string
        }
        result: VendorResult
        is_opened: boolean
        is_correct: boolean | null
        raw: Record<string, unknown>
      }>
    }
  | {
      module_key: "shuangbo_12ma"
      title: string
      display_style: string
      history: Array<{
        issue: string
        year: string
        term: string
        wave_groups: Array<{ label: string; codes: string[] }>
        result: VendorResult
        is_opened: boolean
        is_correct: boolean | null
        raw: Record<string, unknown>
      }>
    }
  | {
      module_key: "shujinguang"
      title: string
      display_style: string
      history: Array<{
        issue: string
        year: string
        term: string
        picks: string[]
        text: string
        result: VendorResult
        result_text: string
        is_opened: boolean
        is_correct: boolean | null
        raw: Record<string, unknown>
      }>
    }
  | {
      module_key: "daxiao_2tou"
      title: string
      display_style: string
      history: Array<{
        issue: string
        year: string
        term: string
        daxiao: string
        tou_code: string
        display_text: string
        result: VendorResult
        is_opened: boolean
        is_correct: boolean | null
        raw: Record<string, unknown>
      }>
    }
  | {
      module_key: "tiandi_2xiao"
      title: string
      display_style: string
      history: Array<{
        issue: string
        year: string
        term: string
        tiandi: string
        xiao_pair: string[]
        display_text: string
        result: VendorResult
        is_opened: boolean
        is_correct: boolean | null
        raw: Record<string, unknown>
      }>
    }

export type VendorHomepageModulesResponse = {
  ok: boolean
  site: {
    site_id: number
    web_id: number
    site_key: string
    lottery_type: number
  }
  data: VendorHomepageModule[]
}
