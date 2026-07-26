import { buildCanonicalPredictionModules } from "@/lib/prediction-contract"

const history = [
  { issue: "175", year: "2026", term: "175", prediction_text: "8尾", result_text: "待开奖", is_opened: false, is_correct: null, source_web_id: 9, raw: {} },
  { issue: "175", year: "2026", term: "175", prediction_text: "7尾", result_text: "待开奖", is_opened: false, is_correct: null, source_web_id: 9, raw: {} },
  { issue: "174", year: "2026", term: "174", prediction_text: "6尾", result_text: "兔16", is_opened: true, is_correct: true, source_web_id: 9, raw: {} },
  { issue: "174", year: "2026", term: "174", prediction_text: "7尾", result_text: "兔16", is_opened: true, is_correct: false, source_web_id: 9, raw: {} },
]

const modules = buildCanonicalPredictionModules({
  sitePageData: {
    site: {} as never,
    draw: {} as never,
    modules: [{ id: 1, mechanism_key: "pt1wei", title: "平特一尾", default_modes_id: 1, default_table: "mode_payload_1", sort_order: 1, status: true, history }],
  },
})

const rows = modules[0]?.rows || []
if (rows.map((row) => row.term).join(",") !== "175,174") {
  throw new Error(`canonical prediction rows must retain one latest row per term, got ${rows.map((row) => row.term).join(",")}`)
}
if (rows[0]?.prediction.tokens.join(",") !== "8尾") {
  throw new Error("deduplication must preserve the first (latest) row for a term")
}
