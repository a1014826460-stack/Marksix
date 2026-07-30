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

const openedWithSevenBallRaw = buildCanonicalPredictionModules({
  sitePageData: {
    site: {} as never,
    draw: {} as never,
    modules: [{
      id: 2,
      mechanism_key: "yijuzhenyan",
      title: "一句中平特",
      default_modes_id: 50,
      default_table: "mode_payload_50",
      sort_order: 2,
      status: true,
      history: [{
        issue: "2026177",
        year: "2026",
        term: "177",
        prediction_text: "测试预测",
        result_text: "鸡34",
        is_opened: true,
        is_correct: false,
        source_web_id: 10,
        raw: {
          res_code: "20,37,24,28,19,48,34",
          res_sx: "猪,马,羊,兔,鼠,羊,鸡",
          res_color: "blue,blue,red,green,red,blue,red",
        },
      }],
    }],
  },
})[0]?.rows[0]

if (openedWithSevenBallRaw?.result.code !== "34" || openedWithSevenBallRaw.result.zodiac !== "鸡") {
  throw new Error(`canonical result must expose only the special ball, got ${JSON.stringify(openedWithSevenBallRaw?.result)}`)
}

const vendorWave = buildCanonicalPredictionModules({
  vendorHomepageModules: {
    ok: true,
    site: { site_id: 10, web_id: 10, site_key: "twbst528", lottery_type: 3 },
    data: [{
      module_key: "shuangbo_12ma",
      title: "双波12码",
      display_style: "wave-composite",
      history: [{
        issue: "2026178",
        year: "2026",
        term: "178",
        wave_groups: [
          { label: "红波", codes: ["01", "02"] },
          { label: "蓝波", codes: ["03", "04"] },
        ],
        result: { result_text: "41虎", res_code: "41", res_sx: "虎", res_color: "blue", is_opened: true },
        is_opened: true,
        is_correct: null,
        raw: {},
      }],
    }],
  },
})[0]?.rows[0]

if (vendorWave?.prediction.groups.map((group) => `${group.label}:${group.tokens.join(",")}`).join("|") !== "红波:01,02|蓝波:03,04") {
  throw new Error(`vendor wave groups must preserve labels and codes, got ${JSON.stringify(vendorWave?.prediction)}`)
}
if (vendorWave?.prediction.text.includes("[object Object]")) {
  throw new Error(`vendor wave text must not stringify objects, got ${vendorWave.prediction.text}`)
}
