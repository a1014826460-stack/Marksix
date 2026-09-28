// 预测契约「准/错」真值一致性契约（frontend/lib/prediction-contract.ts）
//
// 背景：站点每行的「准/错」来自后端 `is_correct`。后端的机制判定在
// 「候选集合」与「判定口径」不一致时会虚报命中，最典型的两类：
//   1. 候选只有一个小词标签（`单` / `大`），而复合 outcome 里含 `合单` / `大数`；
//   2. 候选是一整串 `标签|号码`（如绝杀七码 `01,17,14,48,36,24,22`），
//      判定只做了子串匹配。
// 结果就是 `is_correct=true` 但候选项里根本没有真实开奖号码/生肖。
//
// 本契约要求：契约层必须用「候选集合是否命中真实开奖」交叉校验上游判定，
// 虚报命中要收敛为未命中（页面显示「错」），并保留原始判定用于追溯；
// 绝杀/排除类玩法（候选与判定反向）不得被误改。
import { buildCanonicalPredictionModules, verifyVerdictAgainstCandidates } from "@/lib/prediction-contract"

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message)
}

// ── 1. 纯函数：候选项命中校验 ─────────────────────────────────
assert(
  verifyVerdictAgainstCandidates({
    isCorrect: true,
    isOpened: true,
    code: "37",
    zodiac: "马",
    tokens: ["37", "马"],
  }) === "verified",
  "候选里含真实特码/特肖 → verified"
)

assert(
  verifyVerdictAgainstCandidates({
    isCorrect: true,
    isOpened: true,
    code: "37",
    zodiac: "马",
    tokens: ["大|25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49"],
  }) === "verified",
  "`标签|号码` 串里含真实特码 → verified（号码要被拆成原子）"
)

assert(
  verifyVerdictAgainstCandidates({
    isCorrect: true,
    isOpened: true,
    code: "46",
    zodiac: "鸡",
    tokens: ["01,17,14,48,36,24,22"],
  }) === "contradicted",
  "候选号码串不含真实特码 → contradicted（这就是虚报命中）"
)

assert(
  verifyVerdictAgainstCandidates({
    isCorrect: true,
    isOpened: true,
    code: "17",
    zodiac: "虎",
    tokens: ["龙", "猴"],
  }) === "contradicted",
  "候选生肖不含真实特肖 → contradicted"
)

assert(
  verifyVerdictAgainstCandidates({
    isCorrect: true,
    isOpened: true,
    code: "17",
    zodiac: "虎",
    tokens: ["龙", "猴"],
    mechanismHints: ["绝杀七码", "steady_kill_7_codes"],
  }) === "excluded",
  "绝杀/排除类玩法不做 contains 校验"
)

assert(
  verifyVerdictAgainstCandidates({
    isCorrect: true,
    isOpened: true,
    code: "10",
    zodiac: "鸡",
    tokens: ["1尾"],
    mechanismHints: ["pt1wei", "平特一尾"],
  }) === "flat",
  "平特类玩法要看 7 个开奖号码，不做特码交叉校验"
)

assert(
  verifyVerdictAgainstCandidates({
    isCorrect: true,
    isOpened: false,
    code: "17",
    zodiac: "虎",
    tokens: ["龙"],
  }) === "verified",
  "未开奖不参与校验"
)

assert(
  verifyVerdictAgainstCandidates({
    isCorrect: true,
    isOpened: true,
    code: "17",
    zodiac: "虎",
    tokens: [],
  }) === "unverifiable",
  "候选为空时无法校验"
)

// ── 2. 站点页行（public site-page）：虚报命中必须改判 ──────────
// 大小中特：候选只有「小」一个标签（01-24），真实特码 46 是「大」；
// 上游却给了 is_correct=true（`小` 被当成 `大数`/`小数` 的子串匹配）。
const contradictedSitePage = buildCanonicalPredictionModules({
  sitePageData: {
    site: {} as never,
    draw: {} as never,
    modules: [{
      id: 10,
      mechanism_key: "daxiao",
      title: "大小中特",
      default_modes_id: 57,
      default_table: "mode_payload_57",
      sort_order: 1,
      status: true,
      history: [{
        issue: "2026269",
        year: "2026",
        term: "269",
        prediction_text: "[\"小|01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24\"]",
        result_text: "鸡46",
        is_opened: true,
        is_correct: true,
        source_web_id: 11,
        raw: {
          content: "[\"小|01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24\"]",
          res_code: "39,21,36,20,03,19,46",
          res_sx: "马,蛇,猴,龙,牛,蛇,鸡",
        },
      }],
    }],
  },
})[0]?.rows[0]

assert(
  contradictedSitePage?.result.isCorrect === false,
  `站点页虚报命中必须改判为未命中，got ${JSON.stringify(contradictedSitePage?.result)}`
)
assert(
  contradictedSitePage?.status === "opened-miss",
  `改判后 status 必须是 opened-miss，got ${contradictedSitePage?.status}`
)
assert(
  contradictedSitePage?.raw.is_correct === true,
  "原始 is_correct 必须保留在 raw 里用于追溯"
)

// 真实命中必须保持 true：候选「大」包含真实特码 37
const verifiedSitePage = buildCanonicalPredictionModules({
  sitePageData: {
    site: {} as never,
    draw: {} as never,
    modules: [{
      id: 11,
      mechanism_key: "daxiao",
      title: "大小中特",
      default_modes_id: 57,
      default_table: "mode_payload_57",
      sort_order: 1,
      status: true,
      history: [{
        issue: "2026270",
        year: "2026",
        term: "270",
        prediction_text: "[\"大|25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49\"]",
        result_text: "马37",
        is_opened: true,
        is_correct: true,
        source_web_id: 11,
        raw: {
          content: "[\"大|25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49\"]",
          res_code: "28,23,26,17,30,04,37",
          res_sx: "兔,猴,蛇,虎,牛,兔,马",
        },
      }],
    }],
  },
})[0]?.rows[0]

assert(
  verifiedSitePage?.result.isCorrect === true,
  `真实命中不得被改判，got ${JSON.stringify(verifiedSitePage?.result)}`
)

// ── 2b. 候选列不在 `content` 的玩法不得被误改判 ─────────────────
// 三肖15码中特（mode 72）：候选生肖在 `xiao` 列、候选号码在 `code` 列，`content` 为空；
// `prediction_text` 只有号码串。特肖 马 落在 `xiao` 里，后端判定 true。
// 只拿 `content`/号码串构造候选集合会把它误判成 contradicted，把「对」改写成「错」。
const xiaoColumnSitePage = buildCanonicalPredictionModules({
  sitePageData: {
    site: {} as never,
    draw: {} as never,
    modules: [{
      id: 72,
      mechanism_key: "sanxiao15ma",
      title: "三肖15码中特",
      default_modes_id: 72,
      default_table: "mode_payload_72",
      sort_order: 1,
      status: true,
      history: [{
        issue: "2026270",
        year: "2026",
        term: "270",
        prediction_text: "05,01,03,07,08,06,11,10,04,17,13,15,19,20,18",
        result_text: "马37",
        is_opened: true,
        is_correct: true,
        source_web_id: 7,
        raw: {
          content: null,
          xiao: "虎,马,龙,鼠,猪,牛,猴,鸡,兔",
          code: "05,01,03,07,08,06,11,10,04,17,13,15,19,20,18",
          res_code: "28,23,26,17,30,04,37",
          res_sx: "兔,猴,蛇,虎,牛,兔,马",
        },
      }],
    }],
  },
})[0]?.rows[0]

assert(
  xiaoColumnSitePage?.result.isCorrect === true,
  `候选在 xiao 列的真实命中不得被改判，got ${JSON.stringify(xiaoColumnSitePage?.result)}`
)

// 天地生肖（mode 5）：候选生肖同样在 `xiao`，`content` 只是静态的天地分组定义。
const tiandiSitePage = buildCanonicalPredictionModules({
  sitePageData: {
    site: {} as never,
    draw: {} as never,
    modules: [{
      id: 5,
      mechanism_key: "title_5",
      title: "天地生肖（天地选1，生肖选2）",
      default_modes_id: 5,
      default_table: "mode_payload_5",
      sort_order: 1,
      status: true,
      history: [{
        issue: "2026265",
        year: "2026",
        term: "265",
        prediction_text: "[\"天肖|兔,马,猴,猪,牛,龙\"]",
        result_text: "猪08",
        is_opened: true,
        is_correct: true,
        source_web_id: 13,
        raw: {
          content: "[\"天肖|兔,马,猴,猪,牛,龙\"]",
          xiao: "猪,蛇",
          res_code: "21,39,42,02,18,17,08",
          res_sx: "狗,龙,牛,蛇,牛,虎,猪",
        },
      }],
    }],
  },
})[0]?.rows[0]

assert(
  tiandiSitePage?.result.isCorrect === true,
  `天地生肖候选在 xiao 列，真实命中不得被改判，got ${JSON.stringify(tiandiSitePage?.result)}`
)

// 反向保护：候选列里确实没有真实开奖时仍必须改判（不能因为补了白名单就失去拦截能力）。
const stillContradicted = buildCanonicalPredictionModules({
  sitePageData: {
    site: {} as never,
    draw: {} as never,
    modules: [{
      id: 73,
      mechanism_key: "daxiao",
      title: "大小中特",
      default_modes_id: 57,
      default_table: "mode_payload_57",
      sort_order: 1,
      status: true,
      history: [{
        issue: "2026269",
        year: "2026",
        term: "269",
        prediction_text: "[\"小|01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24\"]",
        result_text: "鸡46",
        is_opened: true,
        is_correct: true,
        source_web_id: 7,
        raw: {
          content: "[\"小|01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24\"]",
          xiao: "龙,猴",
          code: "01,02",
          res_code: "39,21,36,20,03,19,46",
          res_sx: "马,蛇,猴,龙,牛,蛇,鸡",
        },
      }],
    }],
  },
})[0]?.rows[0]

assert(
  stillContradicted?.result.isCorrect === false,
  `候选列仍不含真实开奖时必须改判为未命中，got ${JSON.stringify(stillContradicted?.result)}`
)

// ── 3. vendor 模块行：虚报命中同样必须改判 ────────────────────
const contradictedVendor = buildCanonicalPredictionModules({
  vendorHomepageModules: {
    ok: true,
    site: { site_id: 11, web_id: 11, site_key: "twjsz666", lottery_type: 3 },
    data: [{
      module_key: "public_yixiao_yima",
      title: "公开一肖一码",
      display_style: "card-composite",
      history: [{
        issue: "2026269",
        year: "2026",
        term: "269",
        xiao_groups: { xiao_9: ["兔", "牛", "猴"], xiao_7: [], xiao_5: [], xiao_3: [] },
        code_groups: { code_14: ["03", "15", "27", "39"], code_8: [], code_5: [] },
        best_pick: { xiao: "兔", code: "03", text: "本期推荐一肖一码:(兔03)" },
        result: { res_code: "46", res_sx: "鸡", res_color: "red", result_text: "开46鸡", is_opened: true },
        is_opened: true,
        is_correct: true,
        raw: {},
      }],
    }],
  },
})[0]?.rows[0]

assert(
  contradictedVendor?.result.isCorrect === false,
  `vendor 虚报命中必须改判为未命中，got ${JSON.stringify(contradictedVendor?.result)}`
)

// 绝杀类 vendor 行（输尽光）不得被改判
const excludedVendor = buildCanonicalPredictionModules({
  vendorHomepageModules: {
    ok: true,
    site: { site_id: 11, web_id: 11, site_key: "twjsz666", lottery_type: 3 },
    data: [{
      module_key: "shujinguang",
      title: "输尽光",
      display_style: "single-line",
      history: [{
        issue: "2026270",
        year: "2026",
        term: "270",
        picks: ["兔", "猴"],
        text: "270期本期【兔.猴】输尽光",
        result: { res_code: "37", res_sx: "马", res_color: "blue", result_text: "开37马", is_opened: true },
        is_opened: true,
        is_correct: true,
        raw: {},
      }],
    }],
  },
})[0]?.rows[0]

assert(
  excludedVendor?.result.isCorrect === true,
  `绝杀/排除类玩法的判定不得被 contains 校验改掉，got ${JSON.stringify(excludedVendor?.result)}`
)

// ── 4. 三头四尾（mode 492）：候选是两个维度，任一维度命中即算命中 ──────
// 线上缺陷：twjsz666 `#yxym` 的「三头四尾」候选是 `头:2头` / `尾:6尾` 这种带维度前缀的
// 标签，走通用「号码/生肖原子」校验时永远命中不了，`reconcileVerdict` 于是把后端算出的
// 「对」全部改写成「错」（连续 8 期全错）。
// 口径：MIXED（头/尾双维度）任一维度命中即算命中，与后端
// `predict.mechanisms.three_head_four_tail_hit`、供应商样本一致。
const HEAD_TAIL_CONTENT = '{"heads":["4头","0头","3头"],"tails":["5尾","2尾","9尾","0尾"]}'

assert(
  verifyVerdictAgainstCandidates({
    isCorrect: true,
    isOpened: true,
    code: "45",
    zodiac: "狗",
    tokens: [HEAD_TAIL_CONTENT],
    mechanismHints: ["three_head_four_tail", "三头四尾"],
  }) === "verified",
  "三头四尾：头（4头）与尾（5尾）都命中 → verified"
)

assert(
  verifyVerdictAgainstCandidates({
    isCorrect: true,
    isOpened: true,
    code: "45",
    zodiac: "狗",
    tokens: ['{"heads":["4头","0头","3头"],"tails":["1尾","2尾","9尾","0尾"]}'],
    mechanismHints: ["three_head_four_tail", "三头四尾"],
  }) === "verified",
  "三头四尾：只有头命中（4头）也算命中 → verified"
)

assert(
  verifyVerdictAgainstCandidates({
    isCorrect: true,
    isOpened: true,
    code: "45",
    zodiac: "狗",
    tokens: ['{"heads":["1头","0头","3头"],"tails":["5尾","2尾","9尾","0尾"]}'],
    mechanismHints: ["three_head_four_tail", "三头四尾"],
  }) === "verified",
  "三头四尾：只有尾命中（5尾）也算命中 → verified"
)

assert(
  verifyVerdictAgainstCandidates({
    isCorrect: true,
    isOpened: true,
    code: "45",
    zodiac: "狗",
    tokens: ['{"heads":["1头","0头","2头"],"tails":["1尾","2尾","9尾","0尾"]}'],
    mechanismHints: ["three_head_four_tail", "三头四尾"],
  }) === "contradicted",
  "三头四尾：头（4头）与尾（5尾）都没命中 → contradicted（虚报命中必须收敛）"
)

const headTailHit = buildCanonicalPredictionModules({
  sitePageData: {
    site: {} as never,
    draw: {} as never,
    modules: [{
      id: 20,
      mechanism_key: "three_head_four_tail",
      title: "三头四尾",
      default_modes_id: 492,
      default_table: "mode_payload_492",
      sort_order: 1,
      status: true,
      history: [{
        issue: "2026190",
        year: "2026",
        term: "190",
        prediction_text: HEAD_TAIL_CONTENT,
        result_text: "狗45",
        is_opened: true,
        is_correct: true,
        source_web_id: 11,
        raw: {
          content: HEAD_TAIL_CONTENT,
          res_code: "20,19,38,35,23,42,45",
          res_sx: "猪,鼠,蛇,猴,猴,牛,狗",
        },
      }],
    }],
  },
})[0]?.rows[0]

assert(
  headTailHit?.result.isCorrect === true,
  `三头四尾真实命中不得被改判，got ${JSON.stringify(headTailHit?.result)}`
)
assert(
  headTailHit?.status === "opened-hit",
  `三头四尾命中行的 status 必须是 opened-hit，got ${headTailHit?.status}`
)

// 头命中、尾不命中：MIXED 任一维度命中口径下仍然是「对」，不得被改判
const headTailHeadOnly = buildCanonicalPredictionModules({
  sitePageData: {
    site: {} as never,
    draw: {} as never,
    modules: [{
      id: 21,
      mechanism_key: "three_head_four_tail",
      title: "三头四尾",
      default_modes_id: 492,
      default_table: "mode_payload_492",
      sort_order: 1,
      status: true,
      history: [{
        issue: "2026185",
        year: "2026",
        term: "185",
        prediction_text: '{"heads":["4头","0头","2头"],"tails":["2尾","7尾","8尾","0尾"]}',
        result_text: "猪20",
        is_opened: true,
        is_correct: true,
        source_web_id: 11,
        raw: {
          content: '{"heads":["4头","0头","2头"],"tails":["2尾","7尾","8尾","0尾"]}',
          res_code: "04,35,48,22,01,36,20",
          res_sx: "兔,猴,羊,鸡,马,羊,猪",
        },
      }],
    }],
  },
})[0]?.rows[0]

assert(
  headTailHeadOnly?.result.isCorrect === true,
  `三头四尾只有头命中仍是「对」，不得改判，got ${JSON.stringify(headTailHeadOnly?.result)}`
)

const headTailMissed = buildCanonicalPredictionModules({
  sitePageData: {
    site: {} as never,
    draw: {} as never,
    modules: [{
      id: 22,
      mechanism_key: "three_head_four_tail",
      title: "三头四尾",
      default_modes_id: 492,
      default_table: "mode_payload_492",
      sort_order: 1,
      status: true,
      history: [{
        issue: "2026184",
        year: "2026",
        term: "184",
        prediction_text: '{"heads":["1头","0头","3头"],"tails":["6尾","2尾","0尾","4尾"]}',
        result_text: "狗21",
        is_opened: true,
        is_correct: true,
        source_web_id: 11,
        raw: {
          content: '{"heads":["1头","0头","3头"],"tails":["6尾","2尾","0尾","4尾"]}',
          res_code: "24,41,05,09,35,20,21",
          res_sx: "羊,虎,虎,狗,猴,猪,狗",
        },
      }],
    }],
  },
})[0]?.rows[0]

assert(
  headTailMissed?.result.isCorrect === false,
  `三头四尾两个维度都没命中必须改判为未命中，got ${JSON.stringify(headTailMissed?.result)}`
)

const headTailPending = buildCanonicalPredictionModules({
  sitePageData: {
    site: {} as never,
    draw: {} as never,
    modules: [{
      id: 23,
      mechanism_key: "three_head_four_tail",
      title: "三头四尾",
      default_modes_id: 492,
      default_table: "mode_payload_492",
      sort_order: 1,
      status: true,
      history: [{
        issue: "2026191",
        year: "2026",
        term: "191",
        prediction_text: HEAD_TAIL_CONTENT,
        result_text: "待开奖",
        is_opened: false,
        is_correct: null,
        source_web_id: 11,
        raw: { content: HEAD_TAIL_CONTENT, res_code: "", res_sx: "" },
      }],
    }],
  },
})[0]?.rows[0]

assert(
  headTailPending?.result.isCorrect === null,
  `未开奖不得有判定，got ${JSON.stringify(headTailPending?.result)}`
)
assert(
  headTailPending?.status === "pending",
  `未开奖行 status 必须是 pending，got ${headTailPending?.status}`
)

console.log("prediction verdict truth contract passed")
